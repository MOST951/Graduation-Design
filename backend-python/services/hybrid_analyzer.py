"""
混合情感分析器
==============

融合词典规则和深度学习模型的混合情感分析系统

功能特性：
1. 模型融合策略：加权投票、Stacking集成、动态权重
2. 规则增强：规则特征输入、置信度权重、一致性检查
3. 上下文感知：前后文语境、话题调整、用户历史
4. 实时优化：在线学习、动态权重、用户反馈

使用示例:
    from backend.services.hybrid_analyzer import HybridSentimentAnalyzer
    
    analyzer = HybridSentimentAnalyzer()
    result = analyzer.analyze("这部电影真的太好看了！")
    
    # 带上下文分析
    result = analyzer.analyze(
        "这部电影真的太好看了！",
        context={'topic': '电影', 'user_id': '123'}
    )
"""

import os
import json
import time
import logging
import hashlib
import threading
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import lru_cache
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HybridAnalyzer')

# 导入规则分析器
try:
    from .rule_based_analyzer import RuleBasedSentimentAnalyzer, analyze_sentiment as rule_analyze
    RULE_AVAILABLE = True
except ImportError:
    try:
        from backend.services.rule_based_analyzer import RuleBasedSentimentAnalyzer
        RULE_AVAILABLE = True
    except ImportError:
        RULE_AVAILABLE = False
        logger.warning("规则分析器不可用")

# 导入BERT分析器
BERT_AVAILABLE = False
try:
    from ..models.chinese_bert_sentiment import ChineseBertSentimentModel
    BERT_AVAILABLE = True
except ImportError:
    try:
        from backend.models.chinese_bert_sentiment import ChineseBertSentimentModel
        BERT_AVAILABLE = True
    except ImportError:
        logger.warning("BERT分析器不可用")

# 全局单例模型加载器
_SINGLETON_AVAILABLE = False
try:
    from services.model_singleton import (
        get_bert_tokenizer_and_model as _singleton_load,
        is_bert_available as _singleton_bert_available,
    )
    _SINGLETON_AVAILABLE = True
except ImportError:
    try:
        from .model_singleton import (
            get_bert_tokenizer_and_model as _singleton_load,
            is_bert_available as _singleton_bert_available,
        )
        _SINGLETON_AVAILABLE = True
    except ImportError:
        pass


# ==================== 配置类 ====================

@dataclass
class HybridConfig:
    """混合分析器配置"""
    # 融合策略
    fusion_method: str = 'adaptive'  # weighted, stacking, adaptive
    
    # 默认权重
    default_rule_weight: float = 0.4
    default_bert_weight: float = 0.6
    
    # 动态权重参数
    min_rule_weight: float = 0.2
    max_rule_weight: float = 0.8
    
    # 规则优先条件
    rule_only_confidence_threshold: float = 0.9  # 规则置信度高时仅用规则
    rule_only_match_count_threshold: int = 3     # 匹配词数多时仅用规则
    
    # BERT优先条件
    bert_only_text_length_threshold: int = 50    # 长文本优先BERT
    bert_only_complexity_threshold: float = 0.7  # 复杂度高时优先BERT
    
    # 一致性检查
    consistency_bonus: float = 0.1    # 一致时置信度加成
    inconsistency_penalty: float = 0.1  # 不一致时置信度惩罚
    
    # 上下文配置
    context_weight: float = 0.1       # 上下文调整权重
    user_history_weight: float = 0.05  # 用户历史权重
    topic_weight: float = 0.05        # 话题权重
    
    # 在线学习
    enable_online_learning: bool = True
    feedback_buffer_size: int = 1000
    learning_rate: float = 0.01
    
    # 缓存配置
    enable_cache: bool = True
    cache_size: int = 10000
    cache_ttl: int = 3600  # 秒
    
    # 流式处理配置
    enable_streaming: bool = False
    checkpoint_dir: str = './checkpoints'
    streaming_window_size: int = 3600  # 1小时（秒）
    batch_size: int = 100
    streaming_interval: int = 5  # 秒


@dataclass
class AnalysisContext:
    """分析上下文"""
    topic: str = ''                    # 话题
    user_id: str = ''                  # 用户ID
    previous_texts: List[str] = None   # 前文
    following_texts: List[str] = None  # 后文
    metadata: Dict = None              # 其他元数据
    
    def __post_init__(self):
        self.previous_texts = self.previous_texts or []
        self.following_texts = self.following_texts or []
        self.metadata = self.metadata or {}


@dataclass
class HybridResult:
    """混合分析结果"""
    text: str
    score: float                       # 情感得分 [-1, 1]
    polarity: str                      # positive/negative/neutral
    label: str                         # 中文标签
    confidence: float                  # 置信度 [0, 1]
    
    # 各模型结果
    rule_result: Dict = None
    bert_result: Dict = None
    
    # 融合信息
    fusion_method: str = ''
    rule_weight: float = 0.0
    bert_weight: float = 0.0
    consistency: bool = True
    
    # 上下文调整
    context_adjustment: float = 0.0
    
    # 处理信息
    processing_time_ms: float = 0.0
    cache_hit: bool = False


# ==================== 用户历史管理 ====================

class UserHistoryManager:
    """用户历史情感管理"""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.user_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.Lock()
    
    def add_record(self, user_id: str, score: float, polarity: str):
        """添加用户情感记录"""
        with self._lock:
            self.user_history[user_id].append({
                'score': score,
                'polarity': polarity,
                'timestamp': time.time()
            })
    
    def get_user_tendency(self, user_id: str) -> Dict:
        """获取用户情感倾向"""
        with self._lock:
            history = list(self.user_history.get(user_id, []))
        
        if not history:
            return {'tendency': 'neutral', 'avg_score': 0.0, 'count': 0}
        
        # 计算平均得分（时间衰减）
        now = time.time()
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for record in history:
            age = now - record['timestamp']
            weight = np.exp(-age / 86400)  # 24小时半衰期
            weighted_sum += record['score'] * weight
            weight_sum += weight
        
        avg_score = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        # 确定倾向
        if avg_score > 0.2:
            tendency = 'positive'
        elif avg_score < -0.2:
            tendency = 'negative'
        else:
            tendency = 'neutral'
        
        return {
            'tendency': tendency,
            'avg_score': avg_score,
            'count': len(history)
        }


# ==================== 话题情感管理 ====================

class TopicSentimentManager:
    """话题情感管理"""
    
    # 预定义话题情感基调
    TOPIC_BASELINES = {
        # 正面话题
        '节日': 0.3, '庆祝': 0.4, '婚礼': 0.4, '生日': 0.3,
        '旅游': 0.2, '美食': 0.2, '音乐': 0.1, '电影': 0.0,
        '运动': 0.1, '健康': 0.1, '科技': 0.0, '教育': 0.0,
        
        # 负面话题
        '疫情': -0.2, '灾难': -0.4, '事故': -0.3, '犯罪': -0.3,
        '战争': -0.4, '污染': -0.2, '失业': -0.2, '通胀': -0.1,
        
        # 中性话题
        '政治': 0.0, '经济': 0.0, '社会': 0.0, '天气': 0.0,
    }
    
    def __init__(self):
        self.topic_stats: Dict[str, Dict] = defaultdict(lambda: {
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'total_score': 0.0,
            'count': 0
        })
        self._lock = threading.Lock()
    
    def update_topic(self, topic: str, score: float, polarity: str):
        """更新话题统计"""
        with self._lock:
            stats = self.topic_stats[topic]
            stats['count'] += 1
            stats['total_score'] += score
            stats[f'{polarity}_count'] += 1
    
    def get_topic_baseline(self, topic: str) -> float:
        """获取话题情感基调"""
        # 优先使用预定义基调
        if topic in self.TOPIC_BASELINES:
            return self.TOPIC_BASELINES[topic]
        
        # 使用统计数据
        with self._lock:
            stats = self.topic_stats.get(topic)
        
        if stats and stats['count'] > 10:
            return stats['total_score'] / stats['count']
        
        return 0.0


# ==================== 在线学习管理 ====================

class OnlineLearningManager:
    """在线学习管理器"""
    
    def __init__(self, config: HybridConfig):
        self.config = config
        self.feedback_buffer: deque = deque(maxlen=config.feedback_buffer_size)
        self.word_adjustments: Dict[str, float] = {}  # 词汇权重调整
        self.weight_history: List[Dict] = []          # 权重历史
        self._lock = threading.Lock()
        
        # 当前权重
        self.current_rule_weight = config.default_rule_weight
        self.current_bert_weight = config.default_bert_weight
    
    def add_feedback(self, text: str, predicted: str, actual: str, 
                     rule_result: Dict, bert_result: Dict):
        """添加用户反馈"""
        with self._lock:
            self.feedback_buffer.append({
                'text': text,
                'predicted': predicted,
                'actual': actual,
                'rule_result': rule_result,
                'bert_result': bert_result,
                'timestamp': time.time()
            })
        
        # 触发学习
        if len(self.feedback_buffer) >= 10:
            self._update_weights()
    
    def _update_weights(self):
        """更新权重"""
        with self._lock:
            if len(self.feedback_buffer) < 10:
                return
            
            # 统计各模型准确率
            rule_correct = 0
            bert_correct = 0
            total = 0
            
            for feedback in list(self.feedback_buffer)[-100:]:
                actual = feedback['actual']
                rule_pred = feedback['rule_result'].get('polarity', '')
                bert_pred = feedback['bert_result'].get('label', '')
                
                if rule_pred == actual:
                    rule_correct += 1
                if bert_pred == actual:
                    bert_correct += 1
                total += 1
            
            if total == 0:
                return
            
            rule_acc = rule_correct / total
            bert_acc = bert_correct / total
            
            # 根据准确率调整权重
            total_acc = rule_acc + bert_acc
            if total_acc > 0:
                new_rule_weight = rule_acc / total_acc
                new_bert_weight = bert_acc / total_acc
                
                # 平滑更新
                lr = self.config.learning_rate
                self.current_rule_weight = (1 - lr) * self.current_rule_weight + lr * new_rule_weight
                self.current_bert_weight = (1 - lr) * self.current_bert_weight + lr * new_bert_weight
                
                # 限制范围
                self.current_rule_weight = max(self.config.min_rule_weight, 
                                               min(self.config.max_rule_weight, self.current_rule_weight))
                self.current_bert_weight = 1 - self.current_rule_weight
                
                # 记录历史
                self.weight_history.append({
                    'timestamp': time.time(),
                    'rule_weight': self.current_rule_weight,
                    'bert_weight': self.current_bert_weight,
                    'rule_acc': rule_acc,
                    'bert_acc': bert_acc
                })
                
                logger.info(f"权重更新: rule={self.current_rule_weight:.3f}, bert={self.current_bert_weight:.3f}")
    
    def learn_new_word(self, word: str, polarity: str, intensity: float):
        """学习新词汇"""
        with self._lock:
            # 记录词汇调整
            if polarity == 'positive':
                self.word_adjustments[word] = intensity
            elif polarity == 'negative':
                self.word_adjustments[word] = -intensity
            else:
                self.word_adjustments[word] = 0.0
    
    def get_word_adjustment(self, word: str) -> float:
        """获取词汇调整值"""
        return self.word_adjustments.get(word, 0.0)
    
    def get_current_weights(self) -> Tuple[float, float]:
        """获取当前权重"""
        return self.current_rule_weight, self.current_bert_weight


# ==================== 结果缓存 ====================

class ResultCache:
    """结果缓存"""
    
    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
    
    def _get_key(self, text: str, context: AnalysisContext = None) -> str:
        """生成缓存键"""
        key_parts = [text]
        if context:
            key_parts.append(context.topic)
            key_parts.append(context.user_id)
        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()
    
    def get(self, text: str, context: AnalysisContext = None) -> Optional[Any]:
        """获取缓存"""
        key = self._get_key(text, context)
        
        with self._lock:
            if key in self.cache:
                result, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return result
                else:
                    del self.cache[key]
        
        return None
    
    def set(self, text: str, result: Any, context: AnalysisContext = None):
        """设置缓存"""
        key = self._get_key(text, context)
        
        with self._lock:
            # 清理过期缓存
            if len(self.cache) >= self.max_size:
                self._cleanup()
            
            self.cache[key] = (result, time.time())
    
    def _cleanup(self):
        """清理过期缓存"""
        now = time.time()
        expired_keys = [k for k, (_, t) in self.cache.items() if now - t >= self.ttl]
        for key in expired_keys:
            del self.cache[key]
        
        # 如果还是太多，删除最旧的
        if len(self.cache) >= self.max_size:
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:len(self.cache) - self.max_size // 2]:
                del self.cache[key]


# ==================== 主混合分析器 ====================

class HybridSentimentAnalyzer:
    """
    混合情感分析器
    
    融合词典规则和深度学习模型，提供高精度情感分析
    """
    
    def __init__(self, config: HybridConfig = None):
        """
        初始化混合分析器
        
        Args:
            config: 混合分析器配置
        """
        self.config = config or HybridConfig()
        
        # 初始化规则分析器
        self.rule_analyzer = None
        if RULE_AVAILABLE:
            self.rule_analyzer = RuleBasedSentimentAnalyzer()
            logger.info("规则分析器已加载")
        
        # 初始化BERT分析器（延迟加载）
        self.bert_analyzer = None
        self._bert_loaded = False
        
        # 初始化管理器
        self.user_history = UserHistoryManager()
        self.topic_manager = TopicSentimentManager()
        self.online_learner = OnlineLearningManager(self.config)
        self.cache = ResultCache(
            max_size=self.config.cache_size,
            ttl=self.config.cache_ttl
        ) if self.config.enable_cache else None
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'rule_only': 0,
            'bert_only': 0,
            'hybrid': 0,
            'cache_hits': 0,
            'avg_processing_time': 0.0
        }
        
        logger.info("HybridSentimentAnalyzer initialization complete")
        
        # Model warmup
        self._warmup_models()
    
    def _warmup_models(self):
        """Model warmup to reduce first analysis delay"""
        logger.info("Starting model warmup...")
        
        # Warmup rule analyzer
        if self.rule_analyzer:
            try:
                warmup_text = "This is a warmup text."
                self.rule_analyzer.analyze(warmup_text)
                logger.info("Rule analyzer warmup completed")
            except Exception as e:
                logger.warning(f"Rule analyzer warmup failed: {e}")
        
        # Warmup BERT analyzer
        if BERT_AVAILABLE and not self._bert_loaded:
            try:
                self._load_bert()
                if self.bert_analyzer:
                    warmup_text = "This is a warmup text."
                    self.bert_analyzer.predict(warmup_text)
                    logger.info("BERT analyzer warmup completed")
            except Exception as e:
                logger.warning(f"BERT analyzer warmup failed: {e}")
        
        logger.info("Model warmup completed")
    
    def _load_bert(self):
        """Delay load BERT model, 优先从全局单例获取"""
        if self._bert_loaded:
            return
        
        # 优先使用全局单例
        if _SINGLETON_AVAILABLE:
            try:
                tokenizer, model, device = _singleton_load()
                if tokenizer is not None and model is not None:
                    # 包装为兼容接口
                    self.bert_analyzer = _SingletonBertWrapper(tokenizer, model, device)
                    self._bert_loaded = True
                    logger.info("[HybridAnalyzer] BERT已从全局单例获取")
                    return
            except Exception as e:
                logger.warning(f"[HybridAnalyzer] 全局单例加载失败: {e}，回退本地加载")
        
        # 回退：本地加载
        if BERT_AVAILABLE:
            try:
                self.bert_analyzer = ChineseBertSentimentModel()
                self._bert_loaded = True
                logger.info("BERT analyzer loaded (local)")
            except Exception as e:
                logger.error(f"BERT loading failed: {e}")
                self._bert_loaded = True  # Mark as attempted
    
    def analyze(self, text: str, 
                context: Union[Dict, AnalysisContext] = None) -> HybridResult:
        """
        混合情感分析
        
        Args:
            text: 输入文本
            context: 分析上下文
            
        Returns:
            HybridResult对象
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        # 处理上下文
        if isinstance(context, dict):
            context = AnalysisContext(**context)
        elif context is None:
            context = AnalysisContext()
        
        # 检查缓存
        if self.cache:
            cached = self.cache.get(text, context)
            if cached:
                self.stats['cache_hits'] += 1
                cached.cache_hit = True
                return cached
        
        # 1. 规则分析
        rule_result = self._analyze_with_rules(text)
        
        # 2. 判断是否需要BERT
        use_bert = self._should_use_bert(text, rule_result)
        
        # 3. BERT分析（如果需要）
        bert_result = None
        if use_bert:
            bert_result = self._analyze_with_bert(text)
        
        # 4. 融合结果
        if bert_result is None:
            # 仅使用规则
            self.stats['rule_only'] += 1
            result = self._create_result_from_rule(text, rule_result)
            result.fusion_method = 'rule_only'
        elif rule_result is None or not rule_result.get('matches'):
            # 仅使用BERT
            self.stats['bert_only'] += 1
            result = self._create_result_from_bert(text, bert_result)
            result.fusion_method = 'bert_only'
        else:
            # 混合融合
            self.stats['hybrid'] += 1
            result = self._fuse_results(text, rule_result, bert_result)
        
        # 5. 上下文调整
        if context.topic or context.user_id or context.previous_texts:
            result = self._adjust_by_context(result, context)
        
        # 6. 更新统计
        processing_time = (time.time() - start_time) * 1000
        result.processing_time_ms = processing_time
        self._update_stats(processing_time)
        
        # 7. 更新历史
        if context.user_id:
            self.user_history.add_record(context.user_id, result.score, result.polarity)
        if context.topic:
            self.topic_manager.update_topic(context.topic, result.score, result.polarity)
        
        # 8. 缓存结果
        if self.cache:
            self.cache.set(text, result, context)
        
        return result
    
    def _analyze_with_rules(self, text: str) -> Optional[Dict]:
        """使用规则分析"""
        if not self.rule_analyzer:
            return None
        
        try:
            return self.rule_analyzer.analyze(text)
        except Exception as e:
            logger.error(f"规则分析失败: {e}")
            return None
    
    def _analyze_with_bert(self, text: str) -> Optional[Dict]:
        """使用BERT分析"""
        self._load_bert()
        
        if not self.bert_analyzer:
            return None
        
        try:
            results = self.bert_analyzer.predict([text])
            return results[0] if results else None
        except Exception as e:
            logger.error(f"BERT分析失败: {e}")
            return None
    
    def _should_use_bert(self, text: str, rule_result: Dict) -> bool:
        """判断是否需要使用BERT"""
        if not BERT_AVAILABLE:
            return False
        
        # 规则置信度很高时不需要BERT
        if rule_result:
            confidence = rule_result.get('confidence', 0)
            match_count = len(rule_result.get('matches', []))
            
            if confidence >= self.config.rule_only_confidence_threshold:
                return False
            if match_count >= self.config.rule_only_match_count_threshold:
                return False
        
        # 长文本或复杂文本需要BERT
        if len(text) >= self.config.bert_only_text_length_threshold:
            return True
        
        # 计算文本复杂度
        complexity = self._calculate_complexity(text)
        if complexity >= self.config.bert_only_complexity_threshold:
            return True
        
        # 默认使用混合
        return True
    
    def _calculate_complexity(self, text: str) -> float:
        """计算文本复杂度"""
        # 基于多个因素计算复杂度
        factors = []
        
        # 1. 长度因素
        length_factor = min(1.0, len(text) / 100)
        factors.append(length_factor)
        
        # 2. 标点符号密度
        punctuation = sum(1 for c in text if c in '，。！？、；：""''（）【】')
        punct_factor = min(1.0, punctuation / max(1, len(text)) * 10)
        factors.append(punct_factor)
        
        # 3. 特殊字符（表情等）
        special = sum(1 for c in text if ord(c) > 0x1F600)
        special_factor = min(1.0, special / 5)
        factors.append(special_factor)
        
        # 4. 否定词和转折词
        negation_words = ['不', '没', '无', '但', '却', '然而', '虽然']
        negation_count = sum(1 for w in negation_words if w in text)
        negation_factor = min(1.0, negation_count / 3)
        factors.append(negation_factor)
        
        return sum(factors) / len(factors)
    
    def _fuse_results(self, text: str, 
                      rule_result: Dict, 
                      bert_result: Dict) -> HybridResult:
        """融合规则和BERT结果"""
        # 获取权重
        if self.config.fusion_method == 'adaptive':
            rule_weight, bert_weight = self._calculate_adaptive_weights(
                text, rule_result, bert_result
            )
        else:
            rule_weight, bert_weight = self.online_learner.get_current_weights()
        
        # 提取分数
        rule_score = rule_result.get('score', 0.0)
        bert_score = bert_result.get('score', 0.0)
        
        # 检查一致性
        rule_polarity = rule_result.get('polarity', 'neutral')
        bert_polarity = bert_result.get('label', 'neutral')
        consistency = (rule_polarity == bert_polarity)
        
        # 加权融合
        if self.config.fusion_method == 'stacking':
            # Stacking: 使用规则特征增强
            final_score = self._stacking_fusion(rule_result, bert_result)
        else:
            # 加权平均
            final_score = rule_weight * rule_score + bert_weight * bert_score
        
        # 一致性调整
        rule_confidence = rule_result.get('confidence', 0.5)
        bert_confidence = bert_result.get('confidence', 0.5)
        base_confidence = rule_weight * rule_confidence + bert_weight * bert_confidence
        
        if consistency:
            confidence = min(1.0, base_confidence + self.config.consistency_bonus)
        else:
            confidence = max(0.0, base_confidence - self.config.inconsistency_penalty)
        
        # 确定极性
        polarity, label = self._determine_polarity(final_score)
        
        return HybridResult(
            text=text,
            score=round(final_score, 4),
            polarity=polarity,
            label=label,
            confidence=round(confidence, 4),
            rule_result=rule_result,
            bert_result=bert_result,
            fusion_method='hybrid',
            rule_weight=round(rule_weight, 4),
            bert_weight=round(bert_weight, 4),
            consistency=consistency
        )
    
    def _calculate_adaptive_weights(self, text: str,
                                    rule_result: Dict,
                                    bert_result: Dict) -> Tuple[float, float]:
        """计算自适应权重"""
        # 基础权重
        rule_weight = self.config.default_rule_weight
        bert_weight = self.config.default_bert_weight
        
        # 根据规则置信度调整
        rule_confidence = rule_result.get('confidence', 0.5)
        if rule_confidence > 0.8:
            rule_weight += 0.1
        elif rule_confidence < 0.4:
            rule_weight -= 0.1
        
        # 根据匹配数量调整
        match_count = len(rule_result.get('matches', []))
        if match_count >= 5:
            rule_weight += 0.1
        elif match_count <= 1:
            rule_weight -= 0.1
        
        # 根据文本长度调整
        text_length = len(text)
        if text_length > 100:
            bert_weight += 0.1
        elif text_length < 20:
            rule_weight += 0.1
        
        # 根据BERT置信度调整
        bert_confidence = bert_result.get('confidence', 0.5)
        if bert_confidence > 0.9:
            bert_weight += 0.1
        elif bert_confidence < 0.5:
            bert_weight -= 0.1
        
        # 归一化
        total = rule_weight + bert_weight
        rule_weight = max(self.config.min_rule_weight, 
                         min(self.config.max_rule_weight, rule_weight / total))
        bert_weight = 1 - rule_weight
        
        return rule_weight, bert_weight
    
    def _stacking_fusion(self, rule_result: Dict, bert_result: Dict) -> float:
        """Stacking融合"""
        # 提取特征
        features = []
        
        # 规则特征
        features.append(rule_result.get('score', 0.0))
        features.append(rule_result.get('confidence', 0.0))
        features.append(rule_result.get('positive_score', 0.0))
        features.append(rule_result.get('negative_score', 0.0))
        features.append(len(rule_result.get('matches', [])) / 10)
        
        # BERT特征
        features.append(bert_result.get('score', 0.0))
        features.append(bert_result.get('confidence', 0.0))
        
        probs = bert_result.get('probabilities', {})
        features.append(probs.get('positive', 0.0))
        features.append(probs.get('negative', 0.0))
        features.append(probs.get('neutral', 0.0))
        
        # 简单线性组合（可以替换为训练好的模型）
        weights = [0.2, 0.1, 0.1, -0.1, 0.05, 0.3, 0.1, 0.1, -0.1, 0.0]
        
        score = sum(f * w for f, w in zip(features, weights))
        return max(-1.0, min(1.0, score))
    
    def _create_result_from_rule(self, text: str, rule_result: Dict) -> HybridResult:
        """从规则结果创建HybridResult"""
        return HybridResult(
            text=text,
            score=rule_result.get('score', 0.0),
            polarity=rule_result.get('polarity', 'neutral'),
            label=rule_result.get('label', '中性'),
            confidence=rule_result.get('confidence', 0.5),
            rule_result=rule_result,
            bert_result=None,
            rule_weight=1.0,
            bert_weight=0.0
        )
    
    def _create_result_from_bert(self, text: str, bert_result: Dict) -> HybridResult:
        """从BERT结果创建HybridResult"""
        polarity = bert_result.get('label', 'neutral')
        label = {'positive': '正面', 'negative': '负面', 'neutral': '中性'}.get(polarity, '中性')
        
        return HybridResult(
            text=text,
            score=bert_result.get('score', 0.0),
            polarity=polarity,
            label=label,
            confidence=bert_result.get('confidence', 0.5),
            rule_result=None,
            bert_result=bert_result,
            rule_weight=0.0,
            bert_weight=1.0
        )
    
    def _determine_polarity(self, score: float) -> Tuple[str, str]:
        """确定极性和标签"""
        if score >= 0.6:
            return 'positive', '强烈正面'
        elif score >= 0.2:
            return 'positive', '正面'
        elif score <= -0.6:
            return 'negative', '强烈负面'
        elif score <= -0.2:
            return 'negative', '负面'
        else:
            return 'neutral', '中性'
    
    def _adjust_by_context(self, result: HybridResult, 
                           context: AnalysisContext) -> HybridResult:
        """根据上下文调整结果"""
        adjustment = 0.0
        
        # 1. 话题调整
        if context.topic:
            topic_baseline = self.topic_manager.get_topic_baseline(context.topic)
            adjustment += topic_baseline * self.config.topic_weight
        
        # 2. 用户历史调整
        if context.user_id:
            user_tendency = self.user_history.get_user_tendency(context.user_id)
            adjustment += user_tendency['avg_score'] * self.config.user_history_weight
        
        # 3. 前后文调整
        if context.previous_texts:
            prev_scores = []
            for prev_text in context.previous_texts[-3:]:  # 最近3条
                prev_result = self._analyze_with_rules(prev_text)
                if prev_result:
                    prev_scores.append(prev_result.get('score', 0.0))
            
            if prev_scores:
                avg_prev = sum(prev_scores) / len(prev_scores)
                adjustment += avg_prev * self.config.context_weight * 0.5
        
        # 应用调整
        if adjustment != 0:
            new_score = result.score + adjustment
            new_score = max(-1.0, min(1.0, new_score))
            
            # 更新结果
            result.score = round(new_score, 4)
            result.context_adjustment = round(adjustment, 4)
            result.polarity, result.label = self._determine_polarity(new_score)
        
        return result
    
    def _update_stats(self, processing_time: float):
        """更新统计信息"""
        n = self.stats['total_requests']
        old_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = (old_avg * (n - 1) + processing_time) / n
    
    # ==================== 批量分析 ====================
    
    def analyze_batch(self, texts: List[str], 
                      contexts: List[Union[Dict, AnalysisContext]] = None) -> List[HybridResult]:
        """
        批量分析
        
        Args:
            texts: 文本列表
            contexts: 上下文列表
            
        Returns:
            结果列表
        """
        if contexts is None:
            contexts = [None] * len(texts)
        
        results = []
        for text, context in zip(texts, contexts):
            result = self.analyze(text, context)
            results.append(result)
        
        return results
    
    # ==================== 反馈学习 ====================
    
    def feedback(self, text: str, predicted: str, actual: str):
        """
        用户反馈
        
        Args:
            text: 原始文本
            predicted: 预测结果
            actual: 实际结果
        """
        if not self.config.enable_online_learning:
            return
        
        # 获取各模型结果
        rule_result = self._analyze_with_rules(text) or {}
        bert_result = self._analyze_with_bert(text) or {}
        
        # 添加反馈
        self.online_learner.add_feedback(text, predicted, actual, rule_result, bert_result)
        
        logger.info(f"收到反馈: predicted={predicted}, actual={actual}")
    
    def learn_word(self, word: str, polarity: str, intensity: float = 0.5):
        """
        学习新词汇
        
        Args:
            word: 词汇
            polarity: 极性 (positive/negative/neutral)
            intensity: 强度 (0-1)
        """
        self.online_learner.learn_new_word(word, polarity, intensity)
        logger.info(f"学习新词: {word} -> {polarity} ({intensity})")
    
    # ==================== 统计和管理 ====================
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'rule_available': RULE_AVAILABLE,
            'bert_available': BERT_AVAILABLE,
            'bert_loaded': self._bert_loaded,
            'current_weights': self.online_learner.get_current_weights(),
            'cache_enabled': self.cache is not None
        }
    
    def reset_stats(self):
        """重置统计"""
        self.stats = {
            'total_requests': 0,
            'rule_only': 0,
            'bert_only': 0,
            'hybrid': 0,
            'cache_hits': 0,
            'avg_processing_time': 0.0
        }
    
    def save_state(self, path: str):
        """保存状态"""
        state = {
            'config': asdict(self.config),
            'stats': self.stats,
            'weight_history': self.online_learner.weight_history,
            'word_adjustments': self.online_learner.word_adjustments,
            'current_weights': self.online_learner.get_current_weights()
        }
        
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"状态已保存到: {path}")
    
    def load_state(self, path: str):
        """Load state"""
        if not os.path.exists(path):
            logger.warning(f"State file not found: {path}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Restore configuration
            if 'config' in state:
                config_dict = state['config']
                for key, value in config_dict.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            
            # Restore statistics
            if 'stats' in state:
                self.stats.update(state['stats'])
            
            # Restore learning state
            if 'weight_history' in state:
                self.online_learner.weight_history = state['weight_history']
            if 'word_adjustments' in state:
                self.online_learner.word_adjustments = state['word_adjustments']
            if 'current_weights' in state:
                weights = state['current_weights']
                self.online_learner.current_rule_weight = weights[0]
                self.online_learner.current_bert_weight = weights[1]
            
            logger.info(f"State loaded from: {path}")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    
    # ==================== Streaming Analysis ====================
    
    def start_streaming_analysis(self, data_stream, output_callback=None):
        """
        Start streaming sentiment analysis
        
        Args:
            data_stream: Iterable of text data
            output_callback: Callback function for results
        """
        if not self.config.enable_streaming:
            logger.error("Streaming is not enabled in configuration")
            return
        
        # Create checkpoint directory
        os.makedirs(self.config.checkpoint_dir, exist_ok=True)
        
        # Initialize streaming state
        self._streaming_active = True
        self._streaming_buffer = deque(maxlen=self.config.batch_size)
        self._last_checkpoint_time = time.time()
        
        logger.info("Starting streaming analysis...")
        
        try:
            for text in data_stream:
                if not self._streaming_active:
                    break
                
                # Check for global stop flag
                if hasattr(self, '_global_stop_flag') and self._global_stop_flag:
                    logger.info("Global stop flag detected, stopping streaming...")
                    break
                
                # Add to buffer
                self._streaming_buffer.append({
                    'text': text,
                    'timestamp': time.time()
                })
                
                # Process batch when buffer is full or time interval reached
                if (len(self._streaming_buffer) >= self.config.batch_size or 
                    time.time() - self._last_checkpoint_time >= self.config.streaming_interval):
                    
                    self._process_streaming_batch(output_callback)
                    self._last_checkpoint_time = time.time()
            
            # Process remaining buffer
            if self._streaming_buffer:
                self._process_streaming_batch(output_callback)
                
        except Exception as e:
            logger.error(f"Streaming analysis error: {e}")
        finally:
            self._streaming_active = False
            logger.info("Streaming analysis completed")
    
    def stop_streaming_analysis(self):
        """Stop streaming analysis"""
        self._streaming_active = False
        logger.info("Streaming analysis stopped")
    
    def _process_streaming_batch(self, output_callback=None):
        """Process a batch of streaming data"""
        if not self._streaming_buffer:
            return
        
        # Filter data within window size (1 hour)
        current_time = time.time()
        window_start = current_time - self.config.streaming_window_size
        
        filtered_data = [
            item for item in self._streaming_buffer
            if item['timestamp'] >= window_start
        ]
        
        if not filtered_data:
            return
        
        # Process texts
        texts = [item['text'] for item in filtered_data]
        results = self.batch_analyze(texts)
        
        # Add timestamps back to results
        for i, (item, result) in enumerate(zip(filtered_data, results)):
            result.timestamp = item['timestamp']
        
        # Save checkpoint
        self._save_streaming_checkpoint(filtered_data, results)
        
        # Call output callback
        if output_callback:
            output_callback(results)
        
        # Clear processed data from buffer
        for item in filtered_data:
            try:
                self._streaming_buffer.remove(item)
            except ValueError:
                pass
    
    def _save_streaming_checkpoint(self, data_items, results):
        """Save streaming checkpoint"""
        checkpoint_file = os.path.join(
            self.config.checkpoint_dir,
            f"checkpoint_{int(time.time())}.json"
        )
        
        checkpoint_data = {
            'timestamp': time.time(),
            'data_count': len(data_items),
            'results': [asdict(result) for result in results],
            'window_size': self.config.streaming_window_size
        }
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # Clean old checkpoints (keep only last 10)
            self._cleanup_old_checkpoints()
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def _cleanup_old_checkpoints(self):
        """Clean old checkpoint files"""
        try:
            checkpoint_files = [
                f for f in os.listdir(self.config.checkpoint_dir)
                if f.startswith('checkpoint_') and f.endswith('.json')
            ]
            
            # Sort by timestamp and keep only last 10
            checkpoint_files.sort()
            if len(checkpoint_files) > 10:
                for old_file in checkpoint_files[:-10]:
                    old_path = os.path.join(self.config.checkpoint_dir, old_file)
                    os.remove(old_path)
                    logger.debug(f"Removed old checkpoint: {old_file}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints: {e}")
    
    def set_global_stop_flag(self, stop_flag: bool):
        """Set global stop flag for streaming"""
        self._global_stop_flag = stop_flag
        if stop_flag:
            logger.info("Global stop flag set")
        else:
            logger.info("Global stop flag cleared")

    def batch_analyze(self, texts: List[str]) -> List[HybridResult]:
        """
        批量分析
        
        Args:
            texts: 文本列表
        
        Returns:
            结果列表
        """
        results = []
        for text in texts:
            result = self.analyze(text)
            results.append(result)
        
        return results

class _SingletonBertWrapper:
    """
    将全局单例的 (tokenizer, model, device) 包装为
    HybridSentimentAnalyzer._analyze_with_bert 期望的 predict() 接口
    """

    def __init__(self, tokenizer, model, device):
        self._tokenizer = tokenizer
        self._model = model
        self._device = device

    def predict(self, texts):
        """兼容 ChineseBertSentimentModel.predict 接口"""
        import torch

        if isinstance(texts, str):
            texts = [texts]

        inputs = self._tokenizer(
            texts, padding=True, truncation=True,
            max_length=128, return_tensors="pt"
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

        results = []
        label_map = {0: 'negative', 1: 'neutral', 2: 'positive'}
        for i, text in enumerate(texts):
            p = probs[i].cpu().numpy()
            pred_idx = int(p.argmax())
            results.append({
                'text': text,
                'label': label_map.get(pred_idx, 'neutral'),
                'score': float(p[2]) - float(p[0]),  # positive - negative
                'confidence': float(p[pred_idx]),
                'probabilities': {
                    'positive': float(p[2]),
                    'neutral': float(p[1]),
                    'negative': float(p[0]),
                },
            })
        return results


_analyzer_instance: Optional[HybridSentimentAnalyzer] = None


def get_hybrid_analyzer() -> HybridSentimentAnalyzer:
    """获取混合分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = HybridSentimentAnalyzer()
    return _analyzer_instance


def analyze_sentiment(text: str, context: Dict = None) -> Dict:
    """便捷情感分析函数"""
    result = get_hybrid_analyzer().analyze(text, context)
    return asdict(result)


def analyze_batch(texts: List[str], contexts: List[Dict] = None) -> List[Dict]:
    """批量情感分析"""
    results = get_hybrid_analyzer().analyze_batch(texts, contexts)
    return [asdict(r) for r in results]


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    # 测试用例
    test_texts = [
        "这部电影真的太好看了！强烈推荐！😍",
        "服务态度太差了，非常失望",
        "还可以吧，一般般",
        "虽然有点贵，但是质量真的很好",
        "不是很喜欢，感觉不太行",
        "yyds！绝绝子！太可了！",
        "破防了😭裂开了麻了",
        "这个产品不好用，但是客服态度很好",
    ]
    
    print("=" * 70)
    print("混合情感分析器测试")
    print("=" * 70)
    
    analyzer = HybridSentimentAnalyzer()
    
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\n文本: {text}")
        print(f"极性: {result.polarity} ({result.label})")
        print(f"得分: {result.score:.4f}")
        print(f"置信度: {result.confidence:.4f}")
        print(f"融合方法: {result.fusion_method}")
        if result.fusion_method == 'hybrid':
            print(f"权重: rule={result.rule_weight:.2f}, bert={result.bert_weight:.2f}")
            print(f"一致性: {'是' if result.consistency else '否'}")
        print(f"处理时间: {result.processing_time_ms:.2f}ms")
        print("-" * 50)
    
    # 带上下文分析
    print("\n\n带上下文分析:")
    context = AnalysisContext(
        topic='电影',
        user_id='user_001',
        previous_texts=["昨天看了一部好电影", "今天心情不错"]
    )
    
    result = analyzer.analyze("这部也还行吧", context)
    print(f"文本: 这部也还行吧")
    print(f"极性: {result.polarity} ({result.label})")
    print(f"得分: {result.score:.4f}")
    print(f"上下文调整: {result.context_adjustment:.4f}")
    
    # 统计信息
    print("\n\n统计信息:")
    stats = analyzer.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
