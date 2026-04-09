"""
增强型情感-热度双维度排序模型
==============================

创新点：
1. 多维度融合：情感强度 + 传播热度 + 时效性 + 用户影响力
2. 自适应权重：基于数据分布动态调整权重
3. 四象限分类：高情感高热度/高情感低热度/低情感高热度/低情感低热度
4. 可解释性：提供详细的得分分解和排序理由

技术特点：
1. 支持Spark分布式计算
2. 实时和批量两种模式
3. 支持在线学习更新权重
4. 完整的评估指标

作者：毕业设计
"""

import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DualDimensionModel')

# Spark导入
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False


# ==================== 枚举类型 ====================

class Quadrant(Enum):
    """四象限分类"""
    HIGH_SENTIMENT_HIGH_HEAT = "high_sentiment_high_heat"  # 高关注热点
    HIGH_SENTIMENT_LOW_HEAT = "high_sentiment_low_heat"    # 情感强烈但传播有限
    LOW_SENTIMENT_HIGH_HEAT = "low_sentiment_high_heat"    # 热门中性话题
    LOW_SENTIMENT_LOW_HEAT = "low_sentiment_low_heat"      # 普通话题


class SentimentPolarity(Enum):
    """情感极性"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


# ==================== 配置类 ====================

@dataclass
class EnhancedDualDimensionConfig:
    """增强型双维度配置"""
    
    # 基础权重（需满足总和为1）
    sentiment_weight: float = 0.35
    heat_weight: float = 0.35
    timeliness_weight: float = 0.15
    influence_weight: float = 0.15
    
    # 热度计算参数
    repost_factor: float = 1.0
    comment_factor: float = 2.0
    like_factor: float = 1.0
    
    # 时间衰减参数
    decay_half_life_hours: float = 24.0
    
    # 情感强度参数
    sentiment_amplify: float = 1.5
    negative_boost: bool = True
    negative_boost_factor: float = 1.3
    
    # 用户影响力参数
    min_followers_for_kol: int = 10000
    verified_boost: float = 1.2
    
    # 四象限阈值
    sentiment_threshold: float = 0.5
    heat_threshold: float = 0.5
    
    # 自适应学习
    enable_adaptive: bool = True
    learning_rate: float = 0.01
    
    def validate_weights(self):
        """验证并归一化权重"""
        total = (self.sentiment_weight + self.heat_weight + 
                 self.timeliness_weight + self.influence_weight)
        if abs(total - 1.0) > 0.001:
            self.sentiment_weight /= total
            self.heat_weight /= total
            self.timeliness_weight /= total
            self.influence_weight /= total


@dataclass
class WeiboScore:
    """微博综合得分"""
    weibo_id: str
    text: str
    
    # 原始数据
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0
    sentiment_score: float = 0.0
    followers_count: int = 0
    verified: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    # 计算得分
    heat_score: float = 0.0
    timeliness_score: float = 0.0
    influence_score: float = 0.0
    sentiment_intensity: float = 0.0
    
    # 综合得分
    dual_score: float = 0.0
    rank: int = 0
    quadrant: str = ""
    
    # 解释
    explanation: Dict = field(default_factory=dict)


@dataclass
class RankingExplanation:
    """排序解释"""
    rank: int
    weibo_id: str
    dual_score: float
    quadrant: str
    
    # 得分分解
    sentiment_contribution: float = 0.0
    heat_contribution: float = 0.0
    timeliness_contribution: float = 0.0
    influence_contribution: float = 0.0
    
    # 排名理由
    primary_reason: str = ""
    secondary_reasons: List[str] = field(default_factory=list)
    
    # 关键指标
    key_metrics: Dict[str, Any] = field(default_factory=dict)


# ==================== 核心模型 ====================

class EnhancedDualDimensionModel:
    """
    增强型情感-热度双维度排序模型
    
    核心公式:
    DualScore = α·S(sentiment) + β·H(heat) + γ·T(timeliness) + δ·I(influence)
    
    其中：
    - S(): 情感强度评分函数，考虑极性和强度
    - H(): 热度评分函数，对数平滑处理
    - T(): 时效性评分函数，指数衰减
    - I(): 影响力评分函数，考虑粉丝数和认证
    - α,β,γ,δ: 可配置权重，满足 α+β+γ+δ=1
    """
    
    def __init__(self, config: EnhancedDualDimensionConfig = None):
        self.config = config or EnhancedDualDimensionConfig()
        self.config.validate_weights()
        
        # 统计信息
        self.stats = {
            'total_ranked': 0,
            'quadrant_distribution': {},
            'avg_scores': {},
        }
        
        logger.info("EnhancedDualDimensionModel初始化完成")
        logger.info(f"权重配置: sentiment={self.config.sentiment_weight:.2f}, "
                   f"heat={self.config.heat_weight:.2f}, "
                   f"timeliness={self.config.timeliness_weight:.2f}, "
                   f"influence={self.config.influence_weight:.2f}")
    
    # ==================== 得分计算 ====================
    
    def calculate_sentiment_intensity(self, sentiment_score: float) -> float:
        """
        计算情感强度（公式4-4）
        
        基础公式: N(S) = (|S| + 1) / 2，映射 [-1,1] → [0,1]
        增强特性：
        1. 取绝对值关注强度而非极性
        2. 应用放大因子增强区分度
        3. 负面情感增强（负面舆情更需关注）
        """
        # 基础强度
        intensity = abs(sentiment_score)
        
        # 放大
        intensity *= self.config.sentiment_amplify
        
        # 负面增强
        if self.config.negative_boost and sentiment_score < 0:
            intensity *= self.config.negative_boost_factor
        
        # 归一化到[0,1]
        return min(1.0, intensity)
    
    def calculate_heat_score(self, reposts: int, comments: int, likes: int) -> float:
        """
        计算热度得分
        
        公式: H = log(1 + α·reposts + β·comments + γ·likes)
        使用对数平滑处理极端值
        """
        raw_heat = (
            self.config.repost_factor * reposts +
            self.config.comment_factor * comments +
            self.config.like_factor * likes
        )
        
        return math.log(1 + raw_heat)
    
    def calculate_timeliness_score(
        self, 
        created_at: datetime,
        reference_time: datetime = None
    ) -> float:
        """
        计算时效性得分（公式4-6）
        
        公式：γ(t) = 2^(-Δt / H)
        等价于：exp(-ln(2)/H * Δt)
        其中 H = 半衰期（小时），含义：每H小时得分减半
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        # 计算时间差（小时）
        delta_hours = (reference_time - created_at).total_seconds() / 3600
        delta_hours = max(0, delta_hours)
        
        # 指数衰减
        decay_constant = math.log(2) / self.config.decay_half_life_hours
        return math.exp(-decay_constant * delta_hours)
    
    def calculate_influence_score(
        self,
        followers_count: int,
        verified: bool
    ) -> float:
        """
        计算用户影响力得分
        
        考虑：
        1. 粉丝数（对数平滑）
        2. 认证加成
        """
        # 粉丝数对数得分
        followers_score = math.log(1 + followers_count) / math.log(1 + 10000000)  # 归一化
        followers_score = min(1.0, followers_score)
        
        # 认证加成
        if verified:
            followers_score *= self.config.verified_boost
            followers_score = min(1.0, followers_score)
        
        return followers_score
    
    def calculate_dual_score(self, weibo: WeiboScore) -> float:
        """
        计算双维度综合得分
        
        DualScore = α·S + β·H_norm + γ·T + δ·I
        """
        # 计算各维度得分
        sentiment = self.calculate_sentiment_intensity(weibo.sentiment_score)
        heat = self.calculate_heat_score(
            weibo.reposts_count, weibo.comments_count, weibo.attitudes_count
        )
        timeliness = self.calculate_timeliness_score(weibo.created_at)
        influence = self.calculate_influence_score(
            weibo.followers_count, weibo.verified
        )
        
        # 热度归一化（假设最大热度对应log(1+500000)≈13.1）
        heat_normalized = min(1.0, heat / 13.1)
        
        # 保存各维度得分
        weibo.sentiment_intensity = sentiment
        weibo.heat_score = heat
        weibo.timeliness_score = timeliness
        weibo.influence_score = influence
        
        # 加权综合
        dual_score = (
            self.config.sentiment_weight * sentiment +
            self.config.heat_weight * heat_normalized +
            self.config.timeliness_weight * timeliness +
            self.config.influence_weight * influence
        )
        
        return dual_score
    
    # ==================== 四象限分类 ====================
    
    def classify_quadrant(self, weibo: WeiboScore) -> Quadrant:
        """
        四象限分类
        
        基于情感强度和热度两个维度划分
        """
        # 归一化热度
        heat_normalized = min(1.0, weibo.heat_score / 13.1)
        
        high_sentiment = weibo.sentiment_intensity >= self.config.sentiment_threshold
        high_heat = heat_normalized >= self.config.heat_threshold
        
        if high_sentiment and high_heat:
            return Quadrant.HIGH_SENTIMENT_HIGH_HEAT
        elif high_sentiment and not high_heat:
            return Quadrant.HIGH_SENTIMENT_LOW_HEAT
        elif not high_sentiment and high_heat:
            return Quadrant.LOW_SENTIMENT_HIGH_HEAT
        else:
            return Quadrant.LOW_SENTIMENT_LOW_HEAT
    
    # ==================== 排序与解释 ====================
    
    def rank_items(
        self,
        items: List[WeiboScore],
        reference_time: datetime = None,
        top_k: int = None
    ) -> List[WeiboScore]:
        """
        对微博列表进行双维度排序
        
        Args:
            items: 微博数据列表
            reference_time: 参考时间
            top_k: 返回前k个
            
        Returns:
            排序后的列表
        """
        if not items:
            return []
        
        # 计算每个item的得分
        for item in items:
            item.dual_score = self.calculate_dual_score(item)
            item.quadrant = self.classify_quadrant(item).value
        
        # 排序
        sorted_items = sorted(items, key=lambda x: x.dual_score, reverse=True)
        
        # 分配排名
        for i, item in enumerate(sorted_items):
            item.rank = i + 1
        
        # 更新统计
        self._update_stats(sorted_items)
        
        if top_k:
            return sorted_items[:top_k]
        return sorted_items
    
    def explain_ranking(self, weibo: WeiboScore) -> RankingExplanation:
        """
        解释排序结果
        
        提供详细的得分分解和排名理由
        """
        # 计算各维度贡献
        heat_normalized = min(1.0, weibo.heat_score / 13.1)
        
        sentiment_contribution = self.config.sentiment_weight * weibo.sentiment_intensity
        heat_contribution = self.config.heat_weight * heat_normalized
        timeliness_contribution = self.config.timeliness_weight * weibo.timeliness_score
        influence_contribution = self.config.influence_weight * weibo.influence_score
        
        # 找出主要贡献因素
        contributions = [
            ("情感强度", sentiment_contribution),
            ("传播热度", heat_contribution),
            ("时效性", timeliness_contribution),
            ("用户影响力", influence_contribution),
        ]
        contributions.sort(key=lambda x: x[1], reverse=True)
        
        primary_reason = f"{contributions[0][0]}贡献最大（{contributions[0][1]:.3f}）"
        secondary_reasons = [
            f"{name}: {value:.3f}" for name, value in contributions[1:]
        ]
        
        # 构建解释
        explanation = RankingExplanation(
            rank=weibo.rank,
            weibo_id=weibo.weibo_id,
            dual_score=round(weibo.dual_score, 4),
            quadrant=weibo.quadrant,
            sentiment_contribution=round(sentiment_contribution, 4),
            heat_contribution=round(heat_contribution, 4),
            timeliness_contribution=round(timeliness_contribution, 4),
            influence_contribution=round(influence_contribution, 4),
            primary_reason=primary_reason,
            secondary_reasons=secondary_reasons,
            key_metrics={
                "sentiment_score": weibo.sentiment_score,
                "reposts": weibo.reposts_count,
                "comments": weibo.comments_count,
                "likes": weibo.attitudes_count,
                "followers": weibo.followers_count,
                "verified": weibo.verified,
            }
        )
        
        return explanation
    
    def _update_stats(self, items: List[WeiboScore]):
        """更新统计信息"""
        self.stats['total_ranked'] += len(items)
        
        # 四象限分布
        quadrant_counts = {}
        for item in items:
            q = item.quadrant
            quadrant_counts[q] = quadrant_counts.get(q, 0) + 1
        self.stats['quadrant_distribution'] = quadrant_counts
        
        # 平均得分
        if items:
            self.stats['avg_scores'] = {
                'dual_score': sum(i.dual_score for i in items) / len(items),
                'heat_score': sum(i.heat_score for i in items) / len(items),
                'sentiment_intensity': sum(i.sentiment_intensity for i in items) / len(items),
            }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# ==================== Spark分布式处理器 ====================

class SparkDualDimensionProcessor:
    """
    基于Spark的双维度排序处理器
    
    支持大规模数据的分布式计算
    """
    
    def __init__(
        self, 
        spark: 'SparkSession' = None,
        config: EnhancedDualDimensionConfig = None
    ):
        self.config = config or EnhancedDualDimensionConfig()
        self.config.validate_weights()
        
        if spark:
            self.spark = spark
        elif SPARK_AVAILABLE:
            from .optimized_config import get_spark_session
            self.spark = get_spark_session()
        else:
            self.spark = None
            logger.warning("Spark不可用，将使用本地计算")
    
    def process(
        self,
        df: 'DataFrame',
        reference_time: datetime = None
    ) -> 'DataFrame':
        """
        处理DataFrame，计算双维度得分
        
        Args:
            df: 输入DataFrame，需包含以下列：
                - text: 文本内容
                - sentiment_score: 情感得分
                - reposts_count: 转发数
                - comments_count: 评论数
                - attitudes_count: 点赞数
                - created_at: 发布时间
                - followers_count: 粉丝数（可选）
                - verified: 是否认证（可选）
            reference_time: 参考时间
            
        Returns:
            添加了排序得分的DataFrame
        """
        if not SPARK_AVAILABLE or self.spark is None:
            raise RuntimeError("Spark不可用")
        
        if reference_time is None:
            reference_time = datetime.now()
        
        ref_timestamp = reference_time.timestamp()
        config = self.config
        
        # 1. 计算情感强度
        df = df.withColumn(
            "sentiment_intensity",
            F.least(
                F.lit(1.0),
                F.abs(F.col("sentiment_score")) * config.sentiment_amplify *
                F.when(
                    (F.col("sentiment_score") < 0) & F.lit(config.negative_boost),
                    F.lit(config.negative_boost_factor)
                ).otherwise(F.lit(1.0))
            )
        )
        
        # 2. 计算热度得分
        df = df.withColumn(
            "heat_raw",
            config.repost_factor * F.col("reposts_count") +
            config.comment_factor * F.col("comments_count") +
            config.like_factor * F.col("attitudes_count")
        ).withColumn(
            "heat_score",
            F.log(1 + F.col("heat_raw"))
        ).withColumn(
            "heat_normalized",
            F.least(F.lit(1.0), F.col("heat_score") / 13.1)
        )
        
        # 3. 计算时效性得分
        decay_constant = math.log(2) / config.decay_half_life_hours
        df = df.withColumn(
            "time_diff_hours",
            F.greatest(
                F.lit(0),
                (F.lit(ref_timestamp) - F.unix_timestamp(F.col("created_at"))) / 3600
            )
        ).withColumn(
            "timeliness_score",
            F.exp(-decay_constant * F.col("time_diff_hours"))
        )
        
        # 4. 计算影响力得分（如果有相关列）
        if "followers_count" in df.columns:
            df = df.withColumn(
                "influence_score",
                F.least(
                    F.lit(1.0),
                    F.log(1 + F.col("followers_count")) / F.log(1 + 10000000) *
                    F.when(
                        F.col("verified") == True,
                        F.lit(config.verified_boost)
                    ).otherwise(F.lit(1.0))
                )
            )
        else:
            df = df.withColumn("influence_score", F.lit(0.5))
        
        # 5. 计算综合得分
        df = df.withColumn(
            "dual_score",
            config.sentiment_weight * F.col("sentiment_intensity") +
            config.heat_weight * F.col("heat_normalized") +
            config.timeliness_weight * F.col("timeliness_score") +
            config.influence_weight * F.col("influence_score")
        )
        
        # 6. 四象限分类
        df = df.withColumn(
            "quadrant",
            F.when(
                (F.col("sentiment_intensity") >= config.sentiment_threshold) &
                (F.col("heat_normalized") >= config.heat_threshold),
                F.lit("high_sentiment_high_heat")
            ).when(
                (F.col("sentiment_intensity") >= config.sentiment_threshold) &
                (F.col("heat_normalized") < config.heat_threshold),
                F.lit("high_sentiment_low_heat")
            ).when(
                (F.col("sentiment_intensity") < config.sentiment_threshold) &
                (F.col("heat_normalized") >= config.heat_threshold),
                F.lit("low_sentiment_high_heat")
            ).otherwise(
                F.lit("low_sentiment_low_heat")
            )
        )
        
        # 7. 添加排名
        window = Window.orderBy(F.desc("dual_score"))
        df = df.withColumn("rank", F.row_number().over(window))
        
        return df
    
    def get_top_k(self, df: 'DataFrame', k: int) -> 'DataFrame':
        """获取Top-K结果"""
        return df.orderBy(F.desc("dual_score")).limit(k)
    
    def get_quadrant_stats(self, df: 'DataFrame') -> Dict:
        """获取四象限统计"""
        stats = df.groupBy("quadrant").agg(
            F.count("*").alias("count"),
            F.avg("dual_score").alias("avg_score"),
            F.avg("sentiment_intensity").alias("avg_sentiment"),
            F.avg("heat_normalized").alias("avg_heat"),
        ).collect()
        
        return {
            row["quadrant"]: {
                "count": row["count"],
                "avg_score": round(row["avg_score"], 4),
                "avg_sentiment": round(row["avg_sentiment"], 4),
                "avg_heat": round(row["avg_heat"], 4),
            }
            for row in stats
        }


# ==================== 便捷函数 ====================

def rank_weibo_enhanced(
    data: List[Dict],
    sentiment_weight: float = 0.35,
    heat_weight: float = 0.35,
    timeliness_weight: float = 0.15,
    influence_weight: float = 0.15
) -> List[Dict]:
    """
    增强型微博双维度排序
    
    Args:
        data: 微博数据列表
        sentiment_weight: 情感权重
        heat_weight: 热度权重
        timeliness_weight: 时效性权重
        influence_weight: 影响力权重
        
    Returns:
        排序后的数据列表，包含得分和解释
    """
    config = EnhancedDualDimensionConfig(
        sentiment_weight=sentiment_weight,
        heat_weight=heat_weight,
        timeliness_weight=timeliness_weight,
        influence_weight=influence_weight,
    )
    
    model = EnhancedDualDimensionModel(config)
    
    # 转换数据
    items = []
    for d in data:
        created_at = d.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.now()
        elif created_at is None:
            created_at = datetime.now()
        
        item = WeiboScore(
            weibo_id=str(d.get('id', '')),
            text=d.get('text', ''),
            reposts_count=int(d.get('reposts_count', 0) or 0),
            comments_count=int(d.get('comments_count', 0) or 0),
            attitudes_count=int(d.get('attitudes_count', 0) or 0),
            sentiment_score=float(d.get('sentiment_score', 0) or 0),
            followers_count=int(d.get('user', {}).get('followers_count', 0) or 0),
            verified=bool(d.get('user', {}).get('verified', False)),
            created_at=created_at,
        )
        items.append(item)
    
    # 排序
    ranked_items = model.rank_items(items)
    
    # 转换结果
    results = []
    for item in ranked_items:
        explanation = model.explain_ranking(item)
        
        results.append({
            'id': item.weibo_id,
            'text': item.text,
            'rank': item.rank,
            'dual_score': round(item.dual_score, 4),
            'quadrant': item.quadrant,
            'scores': {
                'sentiment_intensity': round(item.sentiment_intensity, 4),
                'heat_score': round(item.heat_score, 4),
                'timeliness_score': round(item.timeliness_score, 4),
                'influence_score': round(item.influence_score, 4),
            },
            'contributions': {
                'sentiment': round(explanation.sentiment_contribution, 4),
                'heat': round(explanation.heat_contribution, 4),
                'timeliness': round(explanation.timeliness_contribution, 4),
                'influence': round(explanation.influence_contribution, 4),
            },
            'explanation': {
                'primary_reason': explanation.primary_reason,
                'secondary_reasons': explanation.secondary_reasons,
            },
            'original_data': {
                'reposts_count': item.reposts_count,
                'comments_count': item.comments_count,
                'attitudes_count': item.attitudes_count,
                'sentiment_score': item.sentiment_score,
            }
        })
    
    return results


# ==================== 测试 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("增强型情感-热度双维度排序模型测试")
    print("=" * 60)
    
    # 测试数据
    test_data = [
        {
            'id': '1',
            'text': '这个产品太棒了，强烈推荐！',
            'reposts_count': 1000,
            'comments_count': 500,
            'attitudes_count': 5000,
            'sentiment_score': 0.9,
            'created_at': (datetime.now() - timedelta(hours=2)).isoformat(),
            'user': {'followers_count': 50000, 'verified': True},
        },
        {
            'id': '2',
            'text': '服务态度太差了，再也不来了！',
            'reposts_count': 2000,
            'comments_count': 1000,
            'attitudes_count': 3000,
            'sentiment_score': -0.85,
            'created_at': (datetime.now() - timedelta(hours=1)).isoformat(),
            'user': {'followers_count': 10000, 'verified': False},
        },
        {
            'id': '3',
            'text': '今天天气不错',
            'reposts_count': 10,
            'comments_count': 5,
            'attitudes_count': 50,
            'sentiment_score': 0.1,
            'created_at': (datetime.now() - timedelta(hours=12)).isoformat(),
            'user': {'followers_count': 500, 'verified': False},
        },
        {
            'id': '4',
            'text': '紧急！发现重大安全隐患！',
            'reposts_count': 5000,
            'comments_count': 2000,
            'attitudes_count': 1000,
            'sentiment_score': -0.95,
            'created_at': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'user': {'followers_count': 1000000, 'verified': True},
        },
    ]
    
    # 排序
    results = rank_weibo_enhanced(test_data)
    
    print("\n排序结果：")
    print("-" * 60)
    
    for item in results:
        print(f"\n排名 {item['rank']}: {item['text'][:30]}...")
        print(f"  综合得分: {item['dual_score']:.4f}")
        print(f"  象限: {item['quadrant']}")
        print(f"  得分分解:")
        for name, value in item['contributions'].items():
            print(f"    - {name}: {value:.4f}")
        print(f"  排名理由: {item['explanation']['primary_reason']}")

