"""
情感-热度三维度排序模型 V2.0

增强功能：
1. 情感维度：极性 + 强度 + 词典/深度学习混合
2. 热度维度：互动加权 + 时间衰减 + 用户影响力
3. 三维度融合：加权公式 + 动态权重 + 四象限分类

作者：毕业设计
日期：2024-12
"""

import math
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import threading
try:
    import schedule
except ImportError:
    schedule = None

# Spark导入
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, FloatType, 
        IntegerType, TimestampType, BooleanType
    )
    from pyspark.sql.window import Window
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 枚举和数据类 ====================

class SentimentPolarity(Enum):
    """情感极性"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


class Quadrant(Enum):
    """四象限分类"""
    HIGH_SENTIMENT_HIGH_HEAT = "high_sentiment_high_heat"  # 高情感-高热度：重点关注
    HIGH_SENTIMENT_LOW_HEAT = "high_sentiment_low_heat"    # 高情感-低热度：潜在风险
    LOW_SENTIMENT_HIGH_HEAT = "low_sentiment_high_heat"    # 低情感-高热度：热门中性
    LOW_SENTIMENT_LOW_HEAT = "low_sentiment_low_heat"      # 低情感-低热度：一般内容


@dataclass
class UserInfo:
    """用户信息"""
    user_id: str
    followers_count: int = 0          # 粉丝数
    friends_count: int = 0            # 关注数
    statuses_count: int = 0           # 微博数
    verified: bool = False            # 是否认证
    verified_type: int = -1           # 认证类型 (-1:未认证, 0:个人, 1:企业, 2:政府, 3:媒体)
    influence_score: float = 0.0      # 影响力得分


@dataclass
class WeiboPost:
    """微博帖子数据"""
    id: str
    text: str
    user: UserInfo
    created_at: datetime
    
    # 互动数据
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0
    
    # 情感数据
    sentiment_polarity: str = "neutral"   # 情感极性
    sentiment_score: float = 0.0          # 情感得分 [-1, 1]
    sentiment_intensity: float = 0.0      # 情感强度 [0, 100]
    
    # 计算得分
    heat_score: float = 0.0               # 热度得分
    influence_factor: float = 0.0         # 影响力因子
    time_decay_factor: float = 0.0        # 时间衰减因子
    tri_score: float = 0.0               # 三维度综合得分
    quadrant: str = ""                    # 四象限分类
    rank: int = 0


@dataclass 
class TriDimensionConfigV2:
    """三维度模型配置V2"""
    
    # ===== 情感维度配置 =====
    sentiment_weight: float = 0.4         # 情感权重 ω₁ - 论文4.2.2
    use_deep_learning: bool = True        # 是否使用深度学习
    lexicon_weight: float = 0.4           # 词典方法权重
    dl_weight: float = 0.6                # 深度学习权重
    
    # ===== 热度维度配置 =====
    heat_weight: float = 0.4              # 热度权重 ω₂ - 论文4.2.2
    
    # 互动权重
    repost_weight: float = 1.0            # 转发权重 λ_r
    comment_weight: float = 2.0           # 评论权重
    like_weight: float = 1.0              # 点赞权重
    
    # 时效性维度
    timeliness_weight: float = 0.2        # 时效性权重 ω₃ - 论文4.2.2
    time_decay_enabled: bool = True
    decay_half_life_hours: float = 12.0   # 半衰期H=12小时 - 论文4.2.2
    
    # 用户影响力
    influence_enabled: bool = True
    follower_log_base: float = 10.0       # 粉丝数对数底数
    verified_bonus: float = 1.5           # 认证用户加成
    verified_type_weights: Dict[int, float] = field(default_factory=lambda: {
        -1: 1.0,   # 未认证
        0: 1.2,    # 个人认证
        1: 1.5,    # 企业认证
        2: 1.8,    # 政府认证
        3: 1.6,    # 媒体认证
    })
    
    # ===== 四象限分类阈值 =====
    sentiment_threshold: float = 0.5      # 情感阈值（高/低分界）
    heat_threshold: float = 0.5           # 热度阈值（高/低分界）
    
    # ===== 归一化配置 =====
    max_heat_value: float = 100000.0      # 热度归一化最大值
    
    def validate(self):
        """验证配置"""
        total = self.sentiment_weight + self.heat_weight + self.timeliness_weight
        if abs(total - 1.0) > 0.001:
            self.sentiment_weight /= total
            self.heat_weight /= total
            self.timeliness_weight /= total
        
        if self.use_deep_learning:
            dl_total = self.lexicon_weight + self.dl_weight
            self.lexicon_weight /= dl_total
            self.dl_weight /= dl_total


# ==================== 情感分析器 ====================

class SentimentAnalyzerV2:
    """
    情感分析器V2
    
    支持词典方法和深度学习混合
    """
    
    # 扩展的情感词典
    POSITIVE_WORDS = {
        '好': 1.0, '棒': 1.2, '赞': 1.0, '优秀': 1.3, '喜欢': 1.0, '爱': 1.2,
        '开心': 1.1, '高兴': 1.0, '快乐': 1.1, '幸福': 1.3, '满意': 1.0,
        '精彩': 1.2, '完美': 1.4, '出色': 1.2, '厉害': 1.1, '牛': 1.0,
        '强': 1.0, '美': 1.0, '漂亮': 1.1, '帅': 1.0, '酷': 1.0,
        '感谢': 1.0, '谢谢': 0.9, '支持': 0.8, '期待': 0.9, '推荐': 1.0,
        '值得': 1.0, '惊喜': 1.2, '感动': 1.1, '温暖': 1.0, '贴心': 1.1,
        '专业': 1.0, '靠谱': 1.0, '给力': 1.1, '神': 1.3, '绝': 1.2,
        '哈哈': 0.8, '嘻嘻': 0.7, '太好了': 1.3, '真棒': 1.2, '不错': 0.8,
    }
    
    NEGATIVE_WORDS = {
        '差': -1.0, '烂': -1.2, '垃圾': -1.4, '糟糕': -1.1, '讨厌': -1.0,
        '恨': -1.3, '难过': -1.0, '伤心': -1.1, '失望': -1.2, '生气': -1.1,
        '愤怒': -1.3, '恶心': -1.2, '无聊': -0.8, '烦': -0.9, '累': -0.7,
        '坑': -1.1, '骗': -1.3, '假': -1.2, '黑': -1.0, '渣': -1.2,
        '废': -1.1, '蠢': -1.0, '傻': -0.9, '丑': -0.8, '臭': -0.9,
        '慢': -0.7, '贵': -0.8, '难': -0.6, '苦': -0.8, '痛': -0.9,
        '怕': -0.8, '担心': -0.7, '焦虑': -0.9, '崩溃': -1.2, '绝望': -1.4,
        '可怜': -0.8, '悲哀': -1.0, '悲剧': -1.1, '惨': -1.0, '倒霉': -0.9,
        '不好': -1.0, '不行': -0.9, '太差': -1.2, '真烂': -1.3, '没用': -1.0,
    }
    
    NEGATION_WORDS = {'不', '没', '没有', '无', '别', '莫', '未', '勿', '难以', '不是', '不会', '不能', '不要'}
    
    DEGREE_WORDS = {
        '很': 1.5, '非常': 1.8, '特别': 1.7, '太': 1.8, '极': 2.0,
        '超': 1.6, '真': 1.4, '好': 1.3, '最': 2.0, '更': 1.3,
        '有点': 0.7, '稍微': 0.6, '略': 0.5, '比较': 1.2, '相当': 1.5,
    }
    
    @classmethod
    def analyze_lexicon(cls, text: str) -> Tuple[str, float, float]:
        """
        词典方法分析
        
        Returns:
            (极性, 得分[-1,1], 强度[0,100])
        """
        if not text:
            return "neutral", 0.0, 0.0
        
        score = 0.0
        word_count = 0
        degree_multiplier = 1.0
        has_negation = False
        
        # 检查否定模式
        negation_patterns = ['不好', '不行', '不喜欢', '不满', '不开心', '没用', '不值', '不推荐']
        for pattern in negation_patterns:
            if pattern in text:
                has_negation = True
                score -= 0.8
                word_count += 1
                break
        
        # 检查程度词
        for word, degree in cls.DEGREE_WORDS.items():
            if word in text:
                degree_multiplier = max(degree_multiplier, degree)
        
        # 检查否定词
        if not has_negation:
            for neg in cls.NEGATION_WORDS:
                if neg in text:
                    idx = text.find(neg)
                    after_neg = text[idx + len(neg):idx + len(neg) + 4]
                    for pos_word in cls.POSITIVE_WORDS:
                        if pos_word in after_neg:
                            has_negation = True
                            break
                    if has_negation:
                        break
        
        # 计算正面词得分
        for word, weight in cls.POSITIVE_WORDS.items():
            if word in text:
                word_score = weight * degree_multiplier
                if has_negation:
                    word_score = -word_score * 0.8
                score += word_score
                word_count += 1
        
        # 计算负面词得分
        for word, weight in cls.NEGATIVE_WORDS.items():
            if word in text:
                word_score = weight * degree_multiplier
                if has_negation:
                    word_score = -word_score * 0.5
                score += word_score
                word_count += 1
        
        # 归一化得分到 [-1, 1]
        if word_count > 0:
            score = max(-1.0, min(1.0, score / max(1, word_count)))
        
        # 计算强度 [0, 100]
        intensity = abs(score) * 100 * min(2.0, degree_multiplier)
        intensity = min(100.0, intensity)
        
        # 确定极性
        if score > 0.2:
            polarity = "positive"
        elif score < -0.2:
            polarity = "negative"
        else:
            polarity = "neutral"
        
        return polarity, score, intensity
    
    @classmethod
    def analyze_hybrid(cls, text: str, dl_result: Optional[Dict] = None,
                       confidence_threshold: float = 0.7) -> Tuple[str, float, float]:
        """
        级联策略分析（Cascade Strategy）
        
        公式4-3: S_final = S_dict if |S_dict| > θ, else S_bert
        先用词典快速分析，置信度高（|score| > θ）则直接采用；
        否则调用深度学习模型精确分析。
        
        Args:
            text: 文本
            dl_result: 深度学习结果 {"polarity": str, "score": float, "confidence": float}
            confidence_threshold: 级联阈值 θ，默认0.7
        """
        # Step 1: 词典快速分析
        lex_polarity, lex_score, lex_intensity = cls.analyze_lexicon(text)
        
        # Step 2: 级联决策 —— 词典置信度高于阈值，直接返回
        if abs(lex_score) > confidence_threshold or dl_result is None:
            return lex_polarity, lex_score, lex_intensity
        
        # Step 3: 词典置信度低，采用深度学习结果
        dl_score = dl_result.get('score', 0.0)
        dl_intensity = abs(dl_score) * 100
        
        if dl_score > 0.2:
            polarity = "positive"
        elif dl_score < -0.2:
            polarity = "negative"
        else:
            polarity = "neutral"
        
        return polarity, dl_score, dl_intensity


# ==================== 热度计算器 ====================

class HeatCalculator:
    """热度计算器"""
    
    @staticmethod
    def calculate_interaction_score(reposts: int, comments: int, likes: int,
                                    config: TriDimensionConfigV2) -> float:
        """
        计算互动得分
        
        公式：InteractionScore = w1*转发 + w2*评论 + w3*点赞
        使用对数平滑处理极端值
        """
        raw_score = (
            config.repost_weight * reposts +
            config.comment_weight * comments +
            config.like_weight * likes
        )
        # 对数平滑
        smoothed = math.log(1 + raw_score)
        return smoothed
    
    @staticmethod
    def calculate_time_decay(created_at: datetime, 
                             reference_time: datetime,
                             config: TriDimensionConfigV2) -> float:
        """
        计算时间衰减因子（公式4-6）
        
        公式：γ(t) = 2^(-Δt / H)
        等价于：exp(-ln(2)/H * Δt)
        其中 H = 半衰期（小时），含义：每H小时得分减半
        """
        if not config.time_decay_enabled:
            return 1.0
        
        time_diff_hours = (reference_time - created_at).total_seconds() / 3600
        decay_constant = math.log(2) / config.decay_half_life_hours
        decay_factor = math.exp(-decay_constant * max(0, time_diff_hours))
        
        return decay_factor
    
    @staticmethod
    def calculate_influence_factor(user: UserInfo, 
                                   config: TriDimensionConfigV2) -> float:
        """
        计算用户影响力因子
        
        公式：Influence = log_base(1 + followers) * verified_bonus * type_weight
        """
        if not config.influence_enabled:
            return 1.0
        
        # 粉丝数对数
        follower_score = math.log(1 + user.followers_count) / math.log(config.follower_log_base)
        
        # 认证加成
        verified_bonus = config.verified_bonus if user.verified else 1.0
        
        # 认证类型权重
        type_weight = config.verified_type_weights.get(user.verified_type, 1.0)
        
        influence = follower_score * verified_bonus * type_weight
        
        # 归一化到 [0.5, 3.0] 范围
        influence = max(0.5, min(3.0, influence / 5.0 + 0.5))
        
        return influence
    
    @staticmethod
    def calculate_heat_score(post: WeiboPost, 
                             reference_time: datetime,
                             config: TriDimensionConfigV2) -> Tuple[float, float, float]:
        """
        计算综合热度得分
        
        Returns:
            (热度得分, 时间衰减因子, 影响力因子)
        """
        # 互动得分
        interaction = HeatCalculator.calculate_interaction_score(
            post.reposts_count, post.comments_count, post.attitudes_count, config
        )
        
        # 时间衰减
        time_decay = HeatCalculator.calculate_time_decay(
            post.created_at, reference_time, config
        )
        
        # 影响力因子
        influence = HeatCalculator.calculate_influence_factor(post.user, config)
        
        # 综合热度 = 互动 × 时间衰减 × 影响力
        heat_score = interaction * time_decay * influence
        
        return heat_score, time_decay, influence


# ==================== 三维度排序模型 ====================

class TriDimensionModelV2:
    """
    情感-热度三维度排序模型V2
    
    核心公式：
    TriScore = α × NormalizedSentiment + β × NormalizedHeat
    
    四象限分类：
    - 高情感-高热度：重点关注的热门情绪内容
    - 高情感-低热度：潜在风险，需要监控
    - 低情感-高热度：热门但情绪平淡的内容
    - 低情感-低热度：一般性内容
    """
    
    def __init__(self, config: Optional[TriDimensionConfigV2] = None):
        self.config = config or TriDimensionConfigV2()
        self.config.validate()
    
    def analyze_sentiment(self, text: str, dl_result: Optional[Dict] = None) -> Tuple[str, float, float]:
        """分析情感"""
        return SentimentAnalyzerV2.analyze_hybrid(text, dl_result)
    
    def calculate_heat(self, post: WeiboPost, 
                       reference_time: Optional[datetime] = None) -> Tuple[float, float, float]:
        """计算热度"""
        ref_time = reference_time or datetime.now()
        return HeatCalculator.calculate_heat_score(post, ref_time, self.config)
    
    def normalize_sentiment(self, score: float, intensity: float) -> float:
        """
        归一化情感强度到 [0, 1]（公式4-4）
        
        公式: N(S) = (|S| + 1) / 2
        取绝对值：关注情感强度而非极性（强烈正面和强烈负面同样具有舆情价值）
        """
        return (abs(score) + 1) / 2
    
    def normalize_heat(self, heat_score: float) -> float:
        """
        归一化热度得分到 [0, 1]（公式4-5）
        
        公式: H_norm = H_raw / max(H_raw)
        使用配置的最大参考值进行最大-最小归一化
        """
        max_heat = math.log(1 + self.config.max_heat_value)
        normalized = heat_score / max_heat
        return max(0, min(1, normalized))
    
    def classify_quadrant(self, sentiment_normalized: float, 
                          heat_normalized: float) -> Quadrant:
        """
        四象限分类
        """
        high_sentiment = sentiment_normalized >= self.config.sentiment_threshold
        high_heat = heat_normalized >= self.config.heat_threshold
        
        if high_sentiment and high_heat:
            return Quadrant.HIGH_SENTIMENT_HIGH_HEAT
        elif high_sentiment and not high_heat:
            return Quadrant.HIGH_SENTIMENT_LOW_HEAT
        elif not high_sentiment and high_heat:
            return Quadrant.LOW_SENTIMENT_HIGH_HEAT
        else:
            return Quadrant.LOW_SENTIMENT_LOW_HEAT
    
    def calculate_tri_score(self, sentiment_normalized: float,
                             heat_normalized: float,
                             time_decay_factor: float = 1.0) -> float:
        """
        计算三维度综合得分
        
        公式(4-3): Score = ω₁×Intensity + ω₂×H_norm + ω₃×γ(Δt)
        """
        return (
            self.config.sentiment_weight * sentiment_normalized +
            self.config.heat_weight * heat_normalized +
            self.config.timeliness_weight * time_decay_factor
        )
    
    def process_post(self, post: WeiboPost,
                     reference_time: Optional[datetime] = None,
                     dl_result: Optional[Dict] = None) -> WeiboPost:
        """
        处理单条微博
        """
        ref_time = reference_time or datetime.now()
        
        # 1. 情感分析
        polarity, score, intensity = self.analyze_sentiment(post.text, dl_result)
        post.sentiment_polarity = polarity
        post.sentiment_score = score
        post.sentiment_intensity = intensity
        
        # 2. 热度计算
        heat, time_decay, influence = self.calculate_heat(post, ref_time)
        post.heat_score = heat
        post.time_decay_factor = time_decay
        post.influence_factor = influence
        
        # 3. 归一化
        sentiment_norm = self.normalize_sentiment(score, intensity)
        heat_norm = self.normalize_heat(heat)
        
        # 4. 四象限分类
        quadrant = self.classify_quadrant(sentiment_norm, heat_norm)
        post.quadrant = quadrant.value
        
        # 5. 三维度得分
        post.tri_score = self.calculate_tri_score(sentiment_norm, heat_norm, time_decay)
        
        return post
    
    def rank_posts(self, posts: List[WeiboPost],
                   reference_time: Optional[datetime] = None,
                   top_k: Optional[int] = None) -> List[WeiboPost]:
        """
        对微博列表进行三维度排序
        """
        ref_time = reference_time or datetime.now()
        
        # 处理每条微博
        for post in posts:
            self.process_post(post, ref_time)
        
        # 按三维度得分排序
        sorted_posts = sorted(posts, key=lambda x: x.tri_score, reverse=True)
        
        # 分配排名
        for i, post in enumerate(sorted_posts):
            post.rank = i + 1
        
        if top_k:
            return sorted_posts[:top_k]
        return sorted_posts
    
    def get_quadrant_statistics(self, posts: List[WeiboPost]) -> Dict[str, Any]:
        """
        获取四象限统计
        """
        stats = {q.value: {"count": 0, "posts": []} for q in Quadrant}
        
        for post in posts:
            if post.quadrant in stats:
                stats[post.quadrant]["count"] += 1
                stats[post.quadrant]["posts"].append(post.id)
        
        total = len(posts)
        for q in stats:
            stats[q]["ratio"] = stats[q]["count"] / total if total > 0 else 0
        
        return stats
    
    def to_scatter_data(self, posts: List[WeiboPost]) -> List[Dict]:
        """
        转换为散点图数据格式
        """
        scatter_data = []
        for post in posts:
            sentiment_norm = self.normalize_sentiment(post.sentiment_score, post.sentiment_intensity)
            heat_norm = self.normalize_heat(post.heat_score)
            
            scatter_data.append({
                "id": post.id,
                "x": round(heat_norm * 100, 2),           # X轴：热度
                "y": round(sentiment_norm * 100, 2),      # Y轴：情感
                "value": round(post.tri_score * 100, 2), # 气泡大小
                "quadrant": post.quadrant,
                "text": post.text[:50] + "..." if len(post.text) > 50 else post.text,
                "sentiment_polarity": post.sentiment_polarity,
                "heat_score": round(post.heat_score, 2),
            })
        
        return scatter_data


# ==================== Spark处理器 ====================

class SparkTriDimensionProcessorV2:
    """
    基于Spark的三维度处理器V2
    """
    
    def __init__(self, spark: Optional['SparkSession'] = None,
                 config: Optional[TriDimensionConfigV2] = None):
        self.config = config or TriDimensionConfigV2()
        self.config.validate()
        
        if spark:
            self.spark = spark
        elif SPARK_AVAILABLE:
            self.spark = SparkSession.builder \
                .appName("TriDimensionModelV2") \
                .master("local[*]") \
                .config("spark.driver.memory", "2g") \
                .config("spark.sql.shuffle.partitions", "4") \
                .getOrCreate()
        else:
            self.spark = None
    
    def process_dataframe(self, df: 'DataFrame',
                          reference_time: Optional[datetime] = None) -> 'DataFrame':
        """
        使用Spark处理DataFrame
        """
        if not SPARK_AVAILABLE or self.spark is None:
            raise RuntimeError("Spark不可用")
        
        ref_time = reference_time or datetime.now()
        ref_timestamp = ref_time.timestamp()
        config = self.config
        
        # 1. 计算互动得分
        df = df.withColumn(
            "interaction_raw",
            config.repost_weight * F.col("reposts_count") +
            config.comment_weight * F.col("comments_count") +
            config.like_weight * F.col("attitudes_count")
        ).withColumn(
            "interaction_score",
            F.log(1 + F.col("interaction_raw"))
        )
        
        # 2. 计算时间衰减
        decay_constant = math.log(2) / config.decay_half_life_hours
        df = df.withColumn(
            "time_diff_hours",
            (F.lit(ref_timestamp) - F.unix_timestamp("created_at")) / 3600
        ).withColumn(
            "time_decay_factor",
            F.when(
                F.lit(config.time_decay_enabled),
                F.exp(-decay_constant * F.greatest(F.lit(0), F.col("time_diff_hours")))
            ).otherwise(F.lit(1.0))
        )
        
        # 3. 计算影响力因子
        df = df.withColumn(
            "influence_factor",
            F.when(
                F.lit(config.influence_enabled),
                F.log(1 + F.col("followers_count")) / math.log(config.follower_log_base) *
                F.when(F.col("verified") == True, config.verified_bonus).otherwise(1.0)
            ).otherwise(F.lit(1.0))
        ).withColumn(
            "influence_factor",
            F.greatest(F.lit(0.5), F.least(F.lit(3.0), F.col("influence_factor") / 5.0 + 0.5))
        )
        
        # 4. 计算热度得分
        df = df.withColumn(
            "heat_score",
            F.col("interaction_score") * F.col("time_decay_factor") * F.col("influence_factor")
        )
        
        # 5. 归一化热度
        max_heat = math.log(1 + config.max_heat_value)
        df = df.withColumn(
            "heat_normalized",
            F.least(F.lit(1.0), F.col("heat_score") / max_heat)
        )
        
        # 6. 情感归一化（假设已有sentiment_score列）
        df = df.withColumn(
            "sentiment_normalized",
            (F.col("sentiment_score") + 1) / 2
        )
        
        # 7. 计算三维度得分
        df = df.withColumn(
            "tri_score",
            config.sentiment_weight * F.col("sentiment_normalized") +
            config.heat_weight * F.col("heat_normalized")
        )
        
        # 8. 四象限分类
        df = df.withColumn(
            "quadrant",
            F.when(
                (F.col("sentiment_normalized") >= config.sentiment_threshold) &
                (F.col("heat_normalized") >= config.heat_threshold),
                F.lit("high_sentiment_high_heat")
            ).when(
                (F.col("sentiment_normalized") >= config.sentiment_threshold) &
                (F.col("heat_normalized") < config.heat_threshold),
                F.lit("high_sentiment_low_heat")
            ).when(
                (F.col("sentiment_normalized") < config.sentiment_threshold) &
                (F.col("heat_normalized") >= config.heat_threshold),
                F.lit("low_sentiment_high_heat")
            ).otherwise(F.lit("low_sentiment_low_heat"))
        )
        
        # 9. 添加排名
        window = Window.orderBy(F.desc("tri_score"))
        df = df.withColumn("rank", F.row_number().over(window))
        
        return df
    
    def get_quadrant_stats(self, df: 'DataFrame') -> Dict[str, Any]:
        """获取四象限统计"""
        stats = df.groupBy("quadrant").agg(
            F.count("*").alias("count"),
            F.avg("tri_score").alias("avg_score"),
            F.avg("heat_score").alias("avg_heat"),
            F.avg("sentiment_score").alias("avg_sentiment")
        ).collect()
        
        total = df.count()
        result = {}
        for row in stats:
            result[row.quadrant] = {
                "count": row["count"],
                "ratio": round(row["count"] / total, 4) if total > 0 else 0,
                "avg_score": round(row["avg_score"], 4) if row["avg_score"] else 0,
                "avg_heat": round(row["avg_heat"], 4) if row["avg_heat"] else 0,
                "avg_sentiment": round(row["avg_sentiment"], 4) if row["avg_sentiment"] else 0,
            }
        
        return result


# ==================== 便捷函数 ====================

def process_weibo_tri_dimension(data: List[Dict],
                                  config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    处理微博数据的便捷函数
    
    Args:
        data: 微博数据列表
        config: 配置参数
        
    Returns:
        处理结果
    """
    # 创建配置
    model_config = TriDimensionConfigV2()
    if config:
        for key, value in config.items():
            if hasattr(model_config, key):
                setattr(model_config, key, value)
    model_config.validate()
    
    # 创建模型
    model = TriDimensionModelV2(model_config)
    
    # 转换数据
    posts = []
    for d in data:
        created_at = d.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.now()
        elif created_at is None:
            created_at = datetime.now()
        
        user = UserInfo(
            user_id=str(d.get('user_id', '')),
            followers_count=d.get('followers_count', 0),
            verified=d.get('verified', False),
            verified_type=d.get('verified_type', -1),
        )
        
        post = WeiboPost(
            id=str(d.get('id', '')),
            text=d.get('text', ''),
            user=user,
            created_at=created_at,
            reposts_count=d.get('reposts_count', 0),
            comments_count=d.get('comments_count', 0),
            attitudes_count=d.get('attitudes_count', 0),
        )
        posts.append(post)
    
    # 处理排序
    ranked_posts = model.rank_posts(posts)
    
    # 获取统计
    quadrant_stats = model.get_quadrant_statistics(ranked_posts)
    scatter_data = model.to_scatter_data(ranked_posts)
    
    # 转换结果
    results = []
    for post in ranked_posts:
        results.append({
            'id': post.id,
            'text': post.text,
            'rank': post.rank,
            'tri_score': round(post.tri_score, 4),
            'sentiment': {
                'polarity': post.sentiment_polarity,
                'score': round(post.sentiment_score, 4),
                'intensity': round(post.sentiment_intensity, 2),
            },
            'heat': {
                'score': round(post.heat_score, 4),
                'time_decay': round(post.time_decay_factor, 4),
                'influence': round(post.influence_factor, 4),
            },
            'quadrant': post.quadrant,
            'interactions': {
                'reposts': post.reposts_count,
                'comments': post.comments_count,
                'likes': post.attitudes_count,
            },
        })
    
    return {
        'ranked_posts': results,
        'quadrant_statistics': quadrant_stats,
        'scatter_data': scatter_data,
        'config': {
            'sentiment_weight': model_config.sentiment_weight,
            'heat_weight': model_config.heat_weight,
            'sentiment_threshold': model_config.sentiment_threshold,
            'heat_threshold': model_config.heat_threshold,
        },
        'total': len(results),
    }


if __name__ == "__main__":
    print("=" * 70)
    print("情感-热度三维度排序模型V2 测试")
    print("=" * 70)
    
    # 测试数据
    test_data = [
        {
            'id': '1',
            'text': '这个产品太棒了，强烈推荐给大家！非常满意！',
            'reposts_count': 5000,
            'comments_count': 2000,
            'attitudes_count': 10000,
            'followers_count': 1000000,
            'verified': True,
            'verified_type': 3,
            'created_at': datetime.now() - timedelta(hours=2),
        },
        {
            'id': '2',
            'text': '服务态度太差了，再也不来了，非常失望！',
            'reposts_count': 8000,
            'comments_count': 5000,
            'attitudes_count': 3000,
            'followers_count': 500000,
            'verified': True,
            'verified_type': 0,
            'created_at': datetime.now() - timedelta(hours=1),
        },
        {
            'id': '3',
            'text': '今天天气不错，适合出门散步',
            'reposts_count': 10,
            'comments_count': 5,
            'attitudes_count': 50,
            'followers_count': 1000,
            'verified': False,
            'verified_type': -1,
            'created_at': datetime.now() - timedelta(hours=12),
        },
        {
            'id': '4',
            'text': '紧急通知！发现重大安全隐患，请大家注意！',
            'reposts_count': 20000,
            'comments_count': 10000,
            'attitudes_count': 5000,
            'followers_count': 5000000,
            'verified': True,
            'verified_type': 2,
            'created_at': datetime.now() - timedelta(minutes=30),
        },
    ]
    
    # 处理
    result = process_weibo_tri_dimension(test_data, {
        'sentiment_weight': 0.4,
        'heat_weight': 0.4,
        'timeliness_weight': 0.2,
        'decay_half_life_hours': 12.0,
    })
    
    print("\n排序结果：")
    print("-" * 70)
    for post in result['ranked_posts']:
        print(f"排名 {post['rank']}: {post['text'][:30]}...")
        print(f"  三维度得分: {post['tri_score']}")
        print(f"  情感: {post['sentiment']}")
        print(f"  热度: {post['heat']}")
        print(f"  四象限: {post['quadrant']}")
        print()
    
    print("\n四象限统计：")
    print("-" * 70)
    for quadrant, stats in result['quadrant_statistics'].items():
        print(f"{quadrant}: {stats}")
    
    print("\n散点图数据（前3条）：")
    print("-" * 70)
    for item in result['scatter_data'][:3]:
        print(item)
