"""
数据流水线服务 - 串联全流程
============================
采集(MySQL) → 情感分析 → 三维度排序 → 结果入库

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
import json
import os
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

# 全局单例模型加载器
_SINGLETON_AVAILABLE = False
try:
    from services.model_singleton import (
        get_bert_tokenizer_and_model as _singleton_load,
        is_bert_available as _singleton_bert_available,
    )
    _SINGLETON_AVAILABLE = True
except ImportError:
    pass


# ==================== 配置 ==================== 

class CheckpointManager:
    """ """
    
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save_checkpoint(self, batch_id: str, stage: str, processed_ids: List[str], 
                       config: Dict, metadata: Dict = None):
        """ """
        checkpoint_data = {
            'batch_id': batch_id,
            'stage': stage,
            'processed_ids': processed_ids,
            'config': config,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'min_id': min(processed_ids) if processed_ids else None,
            'max_id': max(processed_ids) if processed_ids else None,
            'count': len(processed_ids)
        }
        
        checkpoint_file = os.path.join(self.checkpoint_dir, f"{batch_id}_{stage}.json")
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Checkpoint saved: {checkpoint_file} (processed {len(processed_ids)} records)")
    
    def load_checkpoint(self, batch_id: str, stage: str) -> Optional[Dict]:
        """ """
        checkpoint_file = os.path.join(self.checkpoint_dir, f"{batch_id}_{stage}.json")
        if not os.path.exists(checkpoint_file):
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_file}: {e}")
            return None
    
    def get_resume_range(self, batch_id: str, stage: str) -> Optional[Tuple[str, str]]:
        """ """
        checkpoint = self.load_checkpoint(batch_id, stage)
        if not checkpoint:
            return None
        
        if checkpoint.get('max_id'):
            return (checkpoint['max_id'], None)  # 
        return None
    
    def delete_checkpoint(self, batch_id: str, stage: str = None):
        """ """
        if stage:
            checkpoint_file = os.path.join(self.checkpoint_dir, f"{batch_id}_{stage}.json")
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
                logger.info(f"Checkpoint deleted: {checkpoint_file}")
        else:
            # 
            for filename in os.listdir(self.checkpoint_dir):
                if filename.startswith(f"{batch_id}_"):
                    os.remove(os.path.join(self.checkpoint_dir, filename))
            logger.info(f"All checkpoints for batch {batch_id} deleted")


class PipelineConfig:
    """ """
    # 
    confidence_threshold: float = 0.7

    # 
    repost_factor: float = 1.0
    comment_factor: float = 2.0
    like_factor: float = 1.0
    max_heat_reference: float = 100000.0  # 

    # 
    decay_half_life_hours: float = 12.0

    # 
    sentiment_weight: float = 0.4   # 
    heat_weight: float = 0.4        # 
    timeliness_weight: float = 0.2  # 
    
    # 
    spark_config: Dict = {}
    cleaning_rules: Dict = {}
    custom_params: Dict = {}
    
    # 
    schedule_cron: str = ""
    dependencies: List[str] = []
    
    def to_dict(self) -> Dict:
        """ """
        return {
            'confidence_threshold': self.confidence_threshold,
            'repost_factor': self.repost_factor,
            'comment_factor': self.comment_factor,
            'like_factor': self.like_factor,
            'max_heat_reference': self.max_heat_reference,
            'decay_half_life_hours': self.decay_half_life_hours,
            'sentiment_weight': self.sentiment_weight,
            'heat_weight': self.heat_weight,
            'timeliness_weight': self.timeliness_weight,
            'spark_config': self.spark_config,
            'cleaning_rules': self.cleaning_rules,
            'custom_params': self.custom_params,
            'schedule_cron': self.schedule_cron,
            'dependencies': self.dependencies
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'PipelineConfig':
        """ """
        config = cls()
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config
    
    def validate(self) -> List[str]:
        """ """
        errors = []
        
        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            errors.append("confidence_threshold must be between 0 and 1")
        
        if self.decay_half_life_hours <= 0:
            errors.append("decay_half_life_hours must be positive")
        
        total_weight = self.sentiment_weight + self.heat_weight + self.timeliness_weight
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"Weights must sum to 1.0 (current: {total_weight})")
        
        if self.schedule_cron and not self._validate_cron(self.schedule_cron):
            errors.append("Invalid cron expression")
        
        return errors
    
    def _validate_cron(self, cron_expr: str) -> bool:
        """ """
        try:
            import croniter
            croniter.croniter(cron_expr)
            return True
        except ImportError:
            # 
            parts = cron_expr.split()
            return len(parts) == 5
        except:
            return False 


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
        
        # 优先从全局单例获取已加载的 ChineseBERT
        if _SINGLETON_AVAILABLE:
            try:
                tokenizer, model, device = _singleton_load()
                if tokenizer is not None and model is not None:
                    # 复用 ChineseBertSentimentAnalyzer 单例（它内部也会从 singleton 获取）
                    if BERT_AVAILABLE:
                        self._bert = ChineseBertSentimentAnalyzer()
                        self._bert.initialize()
                    logger.info("[SentimentStage] ChineseBERT已从全局单例加载，级联策略就绪")
            except Exception as e:
                logger.warning(f"[SentimentStage] 全局单例加载失败: {e}，回退本地加载")
        
        # 回退：本地加载
        if self._bert is None and BERT_AVAILABLE:
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


# ==================== 三维度排序阶段 ====================

class RankingStage:
    """
    三维度排序阶段
    
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
        对已完成情感分析的微博进行三维度排序
        
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
                'gamma_weight': self.config.timeliness_weight,
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
    
    采集(MySQL) → 情感分析 → 三维度排序 → 结果入库
    
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
        self.checkpoint_manager = CheckpointManager()
        self._running = False
        self._last_result: Optional[Dict] = None
        # 历史记录（内存存储，最近50条）
        self._history: List[Dict] = []
        # 断点续跑：保存上一次失败的状态
        self._checkpoint: Optional[Dict] = None
        # 
        self._scheduler = None
        self._websocket_clients = set()

    def run_pipeline(self, limit: int = 500) -> Dict:
        """
        执行完整流水线:
        1. 从MySQL读取未处理微博
        2. 运行情感分析 (级联策略)
        3. 从MySQL读取待排序微博 (已有情感结果)
        4. 运行三维度排序
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

            # ====== Stage 2: 三维度排序 ======
            stage2_start = time.time()
            unranked = db.get_unranked_weibos(limit=limit)
            result['stages']['ranking'] = {
                'input_count': len(unranked),
            }

            if unranked:
                logger.info(f"[Pipeline] 三维度排序阶段: 排序 {len(unranked)} 条微博")
                ranked = self.ranking_stage.rank(unranked)

                # 写入MySQL
                batch_id = f"rank_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                save_result = db.save_tri_dimension_results(ranked, batch_id)
                result['stages']['ranking']['saved'] = save_result['saved']
                result['stages']['ranking']['errors'] = save_result['errors']
                result['stages']['ranking']['batch_id'] = batch_id

                # 返回Top 10排序结果供前端展示
                result['top_ranked'] = ranked[:10]
            else:
                logger.info("[Pipeline] 无待排序微博，跳过三维度排序阶段")
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
                    'ranking_count': stats.get('tri_dimension_ranking', 0),
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
        finally:
            self._running = False

    def run_pipeline_async(self, limit: int = 500, resume_from: str = None, batch_id: str = None) -> Dict:
        """异步执行流水线"""
        if self._running:
            return {'status': 'error', 'message': '流水线正在运行中'}

        thread = threading.Thread(target=self.run_pipeline, args=(limit, resume_from, batch_id), daemon=True)
        thread.start()
        return {'status': 'started', 'message': '流水线已在后台启动'}

    def get_status(self) -> Dict:
        """ """
        return {
            'running': self._running,
            'last_result': self._last_result,
            'bert_available': BERT_AVAILABLE and self.sentiment_stage._bert is not None,
        }
    
    def _run_sentiment_stage_with_checkpoint(self, limit: int, batch_id: str, resume_range: Tuple[str, str] = None) -> Dict:
        """ """
        db = get_db_service()
        
        # 
        where_clause = "sentiment_score IS NULL"
        if resume_range and resume_range[0]:
            where_clause += f" AND weibo_id > '{resume_range[0]}'"
        
        weibo_data = db.fetch_unprocessed_weibo(limit=limit, where_clause=where_clause)
        processed_ids = []
        
        if not weibo_data:
            logger.info("No unprocessed weibo data found for sentiment analysis")
            return {'processed_ids': processed_ids, 'count': 0}
        
        logger.info(f"Processing {len(weibo_data)} weibo for sentiment analysis")
        
        for weibo in weibo_data:
            try:
                # 
                sentiment_result = self.sentiment_stage.analyze(weibo['content'])
                
                # 
                db.update_sentiment_result(weibo['weibo_id'], sentiment_result)
                processed_ids.append(weibo['weibo_id'])
                
                # 
                if len(processed_ids) % 100 == 0:
                    logger.info(f"Processed {len(processed_ids)}/{len(weibo_data)} sentiment analyses")
                    
            except Exception as e:
                logger.error(f"Failed to process sentiment for weibo {weibo['weibo_id']}: {e}")
                continue
        
        return {'processed_ids': processed_ids, 'count': len(processed_ids)}
    
    def _run_ranking_stage_with_checkpoint(self, limit: int, batch_id: str) -> Dict:
        """ """
        db = get_db_service()
        
        # 
        weibo_data = db.fetch_weibo_for_ranking(limit=limit)
        processed_ids = []
        
        if not weibo_data:
            logger.info("No weibo data found for ranking")
            return {'processed_ids': processed_ids, 'count': 0}
        
        logger.info(f"Processing {len(weibo_data)} weibo for ranking")
        
        # 
        ranked_results = self.ranking_stage.rank(weibo_data)
        
        # 
        for result in ranked_results:
            try:
                db.update_ranking_result(result['weibo_id'], result)
                processed_ids.append(result['weibo_id'])
            except Exception as e:
                logger.error(f"Failed to update ranking for weibo {result['weibo_id']}: {e}")
                continue
        
        return {'processed_ids': processed_ids, 'count': len(processed_ids)}
    
    def _broadcast_status(self, status: Dict):
        """ """
        import json
        message = json.dumps(status, ensure_ascii=False)
        
        # 
        for client in self._websocket_clients.copy():
            try:
                client.send(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                self._websocket_clients.discard(client)
    
    def add_websocket_client(self, client):
        """ """
        self._websocket_clients.add(client)
    
    def remove_websocket_client(self, client):
        """ """
        self._websocket_clients.discard(client)
    
    def _trigger_dependencies(self, completed_batch_id: str):
        """ """
        if not self.config.dependencies:
            return
        
        logger.info(f"Checking dependencies for completed batch {completed_batch_id}")
        
        # 
        for dependency_pipeline_id in self.config.dependencies:
            try:
                # 
                dependency_service = self._get_dependency_service(dependency_pipeline_id)
                if dependency_service:
                    logger.info(f"Triggering dependent pipeline: {dependency_pipeline_id}")
                    dependency_service.run_pipeline_async()
            except Exception as e:
                logger.error(f"Failed to trigger dependency {dependency_pipeline_id}: {e}")
    
    def _get_dependency_service(self, pipeline_id: str):
        """ """
        # 
        # 
        return None
    
    def schedule_pipeline(self, cron_expression: str):
        """ """
        try:
            import croniter
            from datetime import datetime
            
            self.config.schedule_cron = cron_expression
            cron = croniter.croniter(cron_expression)
            
            # 
            next_run = cron.get_next(datetime)
            logger.info(f"Pipeline scheduled with cron '{cron_expression}', next run: {next_run}")
            
            # 
            if self._scheduler:
                self._scheduler.cancel()
            
            # 
            self._scheduler = threading.Timer(
                (next_run - datetime.now()).total_seconds(),
                self._scheduled_run
            )
            self._scheduler.start()
            
        except ImportError:
            logger.error("croniter package not available for scheduling")
        except Exception as e:
            logger.error(f"Failed to schedule pipeline: {e}")
    
    def _scheduled_run(self):
        """ """
        logger.info("Executing scheduled pipeline run")
        self.run_pipeline_async()
        
        # 
        if self.config.schedule_cron:
            self.schedule_pipeline(self.config.schedule_cron)
    
    def get_checkpoints(self, batch_id: str) -> Dict:
        """ """
        checkpoints = {}
        for stage in self.STAGES:
            checkpoint = self.checkpoint_manager.load_checkpoint(batch_id, stage)
            if checkpoint:
                checkpoints[stage] = checkpoint
        return checkpoints
    
    def resume_from_checkpoint(self, batch_id: str, stage: str) -> Dict:
        """ """
        checkpoint = self.checkpoint_manager.load_checkpoint(batch_id, stage)
        if not checkpoint:
            return {'status': 'error', 'message': f'No checkpoint found for batch {batch_id}, stage {stage}'}
        
        return self.run_pipeline(
            limit=checkpoint.get('metadata', {}).get('limit', 500),
            resume_from=stage,
            batch_id=batch_id
        )


# ==================== 单例 ====================

_pipeline_instance: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    """获取流水线服务单例"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = PipelineService()
    return _pipeline_instance
