"""
数据流水线服务 - 串联全流程
============================
采集(MySQL) → 情感分析 → 双维度排序 → 结果入库

实现公式体系:
- 公式4-3: 级联策略 S_final = S_dict if |S_dict| > θ else S_bert
- 公式4-4: 情感强度归一化 N(S) = (|S| + 1) / 2
- 公式4-5: 热度得分 H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)
- 公式4-6: 时间衰减 γ(t) = 2^(-Δt / H), H=12
- 公式4-7: Score_rank = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)
"""

import math
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 导入数据库服务
from services.database_service import get_db_service

# 导入词典情感分析
from spark.sentiment_analyzer import SentimentLexicon

# 尝试导入BERT
try:
    from spark.chinese_bert_sentiment import ChineseBertSentimentAnalyzer
    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False
    logger.warning("ChineseBERT模块不可用，级联策略将仅使用词典方法")


# ==================== 配置 ====================

class PipelineConfig:
    """流水线配置"""
    # 级联策略阈值 θ (公式4-3)
    confidence_threshold: float = 0.7

    # 热度权重 (公式4-5)
    repost_factor: float = 1.0
    comment_factor: float = 2.0
    like_factor: float = 1.0
    max_heat_reference: float = 100000.0  # 归一化参考最大值

    # 半衰期 (公式4-6)
    decay_half_life_hours: float = 12.0

    # 最终排序权重 (公式4-7)
    sentiment_weight: float = 0.4   # ω₁
    heat_weight: float = 0.4        # ω₂
    timeliness_weight: float = 0.2  # ω₃


# ==================== 情感分析阶段 ====================

class SentimentStage:
    """
    情感分析阶段 — 级联策略 (公式4-3)
    
    先用词典快速分析，|score| > θ 则直接采用；
    否则调用ChineseBERT精确分析。
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._bert = None
        if BERT_AVAILABLE:
            try:
                self._bert = ChineseBertSentimentAnalyzer()
                self._bert.initialize()
                logger.info("ChineseBERT模型加载成功，级联策略就绪")
            except Exception as e:
                logger.warning(f"ChineseBERT初始化失败: {e}，回退为纯词典模式")
                self._bert = None

    def analyze(self, text: str) -> Dict:
        """
        级联策略分析单条文本
        
        Returns:
            {score, sentiment_class, confidence, method, 
             dict_score, bert_score, processing_time_ms}
        """
        start = time.time()

        # Step 1: 词典快速分析
        dict_label, dict_score = SentimentLexicon.analyze(text)
        dict_confidence = abs(dict_score)

        # Step 2: 级联决策
        if dict_confidence > self.config.confidence_threshold or self._bert is None:
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                'score': dict_score,
                'sentiment_class': dict_label,
                'confidence': dict_confidence,
                'method': 'cascade-lexicon',
                'dict_score': dict_score,
                'bert_score': None,
                'processing_time_ms': elapsed_ms,
            }

        # Step 3: 词典置信度低，调用BERT
        try:
            bert_result = self._bert.predict(text)
            bert_score = bert_result.get('score', 0.0)
            bert_confidence = bert_result.get('confidence', 0.5)
            if bert_score > 0.2:
                bert_label = 'positive'
            elif bert_score < -0.2:
                bert_label = 'negative'
            else:
                bert_label = 'neutral'

            elapsed_ms = int((time.time() - start) * 1000)
            return {
                'score': bert_score,
                'sentiment_class': bert_label,
                'confidence': bert_confidence,
                'method': 'cascade-bert',
                'dict_score': dict_score,
                'bert_score': bert_score,
                'processing_time_ms': elapsed_ms,
            }
        except Exception as e:
            logger.warning(f"BERT分析失败, 回退词典结果: {e}")
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                'score': dict_score,
                'sentiment_class': dict_label,
                'confidence': dict_confidence,
                'method': 'cascade-lexicon-fallback',
                'dict_score': dict_score,
                'bert_score': None,
                'processing_time_ms': elapsed_ms,
            }

    def analyze_batch(self, weibos: List[Dict]) -> List[Dict]:
        """批量情感分析，返回包含 weibo_id + 情感结果的列表"""
        results = []
        for w in weibos:
            text = w.get('content', '')
            result = self.analyze(text)
            result['weibo_id'] = w['weibo_id']
            result['hybrid_score'] = result['score']  # 兼容 DatabaseService
            result['analysis_method'] = result.pop('method')  # DatabaseService 用 analysis_method
            result['model_version'] = 'v2.0.0'
            results.append(result)
        return results


# ==================== 双维度排序阶段 ====================

class RankingStage:
    """
    双维度排序阶段
    
    公式4-4: N(S) = (|S| + 1) / 2
    公式4-5: H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L), H_norm = H_raw / max_H
    公式4-6: γ(t) = 2^(-Δt / H)
    公式4-7: Score = ω₁·N(S) + ω₂·H_norm + ω₃·γ(t)
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._max_heat_log = math.log10(1 + config.max_heat_reference)

    def _sentiment_normalized(self, score: float) -> float:
        """公式4-4: N(S) = (|S| + 1) / 2"""
        return (abs(score) + 1) / 2

    def _heat_raw(self, reposts: int, comments: int, likes: int) -> float:
        """公式4-5 上半: H_raw = log₁₀(1 + λ_r·R + λ_c·C + λ_l·L)"""
        raw = (self.config.repost_factor * reposts +
               self.config.comment_factor * comments +
               self.config.like_factor * likes)
        return math.log10(1 + raw)

    def _heat_normalized(self, h_raw: float) -> float:
        """公式4-5 下半: H_norm = H_raw / max(H_raw)"""
        return min(h_raw / self._max_heat_log, 1.0)

    def _time_decay(self, created_at: datetime, now: datetime) -> float:
        """公式4-6: γ(t) = 2^(-Δt / H)"""
        if created_at is None:
            return 0.5  # 缺失时间给默认值
        delta_hours = (now - created_at).total_seconds() / 3600
        delta_hours = max(0, delta_hours)
        return 2 ** (-delta_hours / self.config.decay_half_life_hours)

    def rank(self, weibos_with_sentiment: List[Dict]) -> List[Dict]:
        """
        对已完成情感分析的微博进行双维度排序
        
        输入每条需要: weibo_id, sentiment_score(hybrid_score), 
                      reposts_count, comments_count, attitudes_count, created_at
        输出增加: sentiment_normalized, raw_popularity, popularity_score,
                  time_decay, composite_score, ranking_position
        """
        now = datetime.now()
        scored = []

        for w in weibos_with_sentiment:
            sentiment_score = float(w.get('hybrid_score', w.get('sentiment_score', 0)))
            reposts = int(w.get('reposts_count', 0))
            comments = int(w.get('comments_count', 0))
            likes = int(w.get('attitudes_count', 0))
            created_at = w.get('created_at')
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except:
                    created_at = None

            n_s = self._sentiment_normalized(sentiment_score)
            h_raw = self._heat_raw(reposts, comments, likes)
            h_norm = self._heat_normalized(h_raw)
            gamma = self._time_decay(created_at, now)

            composite = (self.config.sentiment_weight * n_s +
                         self.config.heat_weight * h_norm +
                         self.config.timeliness_weight * gamma)

            # 热度分类
            if h_norm >= 0.7:
                pop_class = 'high'
            elif h_norm >= 0.3:
                pop_class = 'medium'
            else:
                pop_class = 'low'

            # 情感分类
            if sentiment_score > 0.2:
                sent_cat = 'positive'
            elif sentiment_score < -0.2:
                sent_cat = 'negative'
            else:
                sent_cat = 'neutral'

            scored.append({
                'weibo_id': w['weibo_id'],
                'sentiment_score': sentiment_score,
                'sentiment_category': sent_cat,
                'reposts_count': reposts,
                'comments_count': comments,
                'attitudes_count': likes,
                'raw_popularity': round(h_raw, 4),
                'popularity_score': round(h_norm, 4),
                'popularity_class': pop_class,
                'time_decay': round(gamma, 4),
                'alpha_weight': self.config.sentiment_weight,
                'beta_weight': self.config.heat_weight,
                'composite_score': round(composite, 4),
                'algorithm_version': 'v2.0.0',
            })

        # 按综合得分降序排序
        scored.sort(key=lambda x: x['composite_score'], reverse=True)
        for i, item in enumerate(scored):
            item['ranking_position'] = i + 1

        return scored


# ==================== 流水线编排 ====================

class PipelineService:
    """
    端到端流水线服务
    
    采集(MySQL) → 情感分析 → 双维度排序 → 结果入库
    
    支持:
    - 同步/异步执行
    - 断点续跑: 某阶段失败后可从该阶段重试
    - 历史记录: 每次运行生成唯一batch_id并记录
    """

    # 阶段定义（有序）
    STAGES = ['sentiment', 'ranking']

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.sentiment_stage = SentimentStage(self.config)
        self.ranking_stage = RankingStage(self.config)
        self._running = False
        self._last_result: Optional[Dict] = None
        # 历史记录（内存存储，最近50条）
        self._history: List[Dict] = []
        # 断点续跑：保存上一次失败的状态
        self._checkpoint: Optional[Dict] = None

    def run_pipeline(self, limit: int = 500) -> Dict:
        """
        执行完整流水线:
        1. 从MySQL读取未处理微博
        2. 运行情感分析 (级联策略)
        3. 从MySQL读取待排序微博 (已有情感结果)
        4. 运行双维度排序
        5. 结果写回MySQL
        
        Returns:
            流水线执行结果统计
        """
        if self._running:
            return {'status': 'error', 'message': '流水线正在运行中'}

        self._running = True
        pipeline_start = time.time()
        result = {
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'stages': {}
        }

        try:
            db = get_db_service()

            # ====== Stage 1: 情感分析 ======
            stage1_start = time.time()
            unprocessed = db.get_unprocessed_weibos(limit=limit)
            result['stages']['sentiment'] = {
                'input_count': len(unprocessed),
            }

            if unprocessed:
                logger.info(f"[Pipeline] 情感分析阶段: 处理 {len(unprocessed)} 条微博")
                sentiment_results = self.sentiment_stage.analyze_batch(unprocessed)

                # 写入MySQL
                save_result = db.save_sentiment_results(sentiment_results)
                result['stages']['sentiment']['saved'] = save_result['saved']
                result['stages']['sentiment']['errors'] = save_result['errors']
            else:
                logger.info("[Pipeline] 无未处理微博，跳过情感分析阶段")
                result['stages']['sentiment']['saved'] = 0

            result['stages']['sentiment']['duration_s'] = round(time.time() - stage1_start, 2)

            # ====== Stage 2: 双维度排序 ======
            stage2_start = time.time()
            unranked = db.get_unranked_weibos(limit=limit)
            result['stages']['ranking'] = {
                'input_count': len(unranked),
            }

            if unranked:
                logger.info(f"[Pipeline] 双维度排序阶段: 排序 {len(unranked)} 条微博")
                ranked = self.ranking_stage.rank(unranked)

                # 写入MySQL
                batch_id = f"rank_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                save_result = db.save_dual_dimension_results(ranked, batch_id)
                result['stages']['ranking']['saved'] = save_result['saved']
                result['stages']['ranking']['errors'] = save_result['errors']
                result['stages']['ranking']['batch_id'] = batch_id

                # 返回Top 10排序结果供前端展示
                result['top_ranked'] = ranked[:10]
            else:
                logger.info("[Pipeline] 无待排序微博，跳过双维度排序阶段")
                result['stages']['ranking']['saved'] = 0

            result['stages']['ranking']['duration_s'] = round(time.time() - stage2_start, 2)

            # ====== 汇总 ======
            result['status'] = 'completed'
            result['total_duration_s'] = round(time.time() - pipeline_start, 2)
            result['finished_at'] = datetime.now().isoformat()

            # 获取统计
            try:
                stats = db.get_graduation_statistics()
                result['database_stats'] = {
                    'weibo_count': stats.get('weibo_core_data', 0),
                    'sentiment_count': stats.get('sentiment_analysis_results', 0),
                    'ranking_count': stats.get('dual_dimension_ranking', 0),
                    'sentiment_distribution': stats.get('sentiment_distribution', []),
                }
            except Exception:
                pass

            logger.info(f"[Pipeline] 流水线完成，耗时 {result['total_duration_s']}s")
            self._last_result = result
            return result

        except Exception as e:
            logger.error(f"[Pipeline] 流水线执行失败: {e}", exc_info=True)
            result['status'] = 'failed'
            result['error'] = str(e)
            result['total_duration_s'] = round(time.time() - pipeline_start, 2)
            self._last_result = result
            return result
        finally:
            self._running = False

    def run_pipeline_async(self, limit: int = 500) -> Dict:
        """异步执行流水线"""
        if self._running:
            return {'status': 'error', 'message': '流水线正在运行中'}

        thread = threading.Thread(target=self.run_pipeline, args=(limit,), daemon=True)
        thread.start()
        return {'status': 'started', 'message': '流水线已在后台启动'}

    def get_status(self) -> Dict:
        """获取流水线状态"""
        return {
            'running': self._running,
            'last_result': self._last_result,
            'bert_available': BERT_AVAILABLE and self.sentiment_stage._bert is not None,
        }


# ==================== 单例 ====================

_pipeline_instance: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    """获取流水线服务单例"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = PipelineService()
    return _pipeline_instance
