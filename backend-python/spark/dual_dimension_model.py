"""
情感-热度双维度排序模型 (Sentiment-Heat Dual Dimension Ranking Model)

创新点说明：
1. 传统舆情分析只关注情感极性或热度单一维度
2. 本模型融合情感强度和传播热度两个维度
3. 使用加权综合评分算法，支持动态权重调整
4. 引入时间衰减因子，体现舆情时效性

技术特点：
- 基于Spark的分布式计算
- 支持实时和批量两种模式
- 可配置的权重参数（支持JSON文件/MySQL动态配置）
- 时间衰减函数

作者：毕业设计
"""

import os
import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DualDimensionModel')

# Spark相关导入
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType, TimestampType
    from pyspark.sql.window import Window
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False


class SentimentLevel(Enum):
    """情感等级枚举"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


@dataclass
class WeiboItem:
    """微博数据项"""
    id: str
    text: str
    user_id: str
    user_name: str
    created_at: datetime
    reposts_count: int = 0
    comments_count: int = 0
    attitudes_count: int = 0  # 点赞数
    sentiment_score: float = 0.0  # 情感得分 [-1, 1]
    sentiment_label: str = "neutral"
    keywords: List[str] = field(default_factory=list)
    
    # 计算得分
    heat_score: float = 0.0
    dual_score: float = 0.0
    rank: int = 0


class ConfigSource(Enum):
    """配置来源枚举"""
    DEFAULT = "default"
    JSON_FILE = "json_file"
    MYSQL = "mysql"


@dataclass
class DualDimensionConfig:
    """
    双维度模型配置
    
    支持从以下来源加载配置：
    1. 默认值（硬编码）
    2. JSON配置文件
    3. MySQL数据库
    
    加载优先级：MySQL > JSON文件 > 默认值
    """
    # 情感权重
    sentiment_weight: float = 0.4
    # 热度权重
    heat_weight: float = 0.4
    # 时效性权重
    timeliness_weight: float = 0.2
    
    # 热度计算参数
    repost_factor: float = 1.0  # 转发权重 λ_r
    comment_factor: float = 2.0  # 评论权重
    like_factor: float = 1.0  # 点赞权重
    
    # 时间衰减参数
    decay_half_life_hours: float = 24.0  # 半衰期（小时）
    
    # 情感强度放大因子
    sentiment_amplify: float = 1.5
    
    # 是否考虑负面情感的特殊处理
    negative_boost: bool = True
    negative_boost_factor: float = 1.2
    
    # 配置元信息
    config_version: str = "1.0.0"
    config_source: str = "default"
    loaded_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.dirname(__file__), 'conf', 'dual_dimension_config.json'
    )
    
    @classmethod
    def load(cls, 
             json_path: Optional[str] = None,
             mysql_config: Optional[Dict[str, Any]] = None,
             fallback_to_default: bool = True) -> 'DualDimensionConfig':
        """
        动态加载配置
        
        Args:
            json_path: JSON配置文件路径，None则使用默认路径
            mysql_config: MySQL连接配置 {'host', 'port', 'user', 'password', 'database'}
            fallback_to_default: 加载失败时是否回退到默认配置
            
        Returns:
            DualDimensionConfig实例
        """
        config = None
        source = ConfigSource.DEFAULT
        
        # 1. 尝试从MySQL加载
        if mysql_config:
            config = cls._load_from_mysql(mysql_config)
            if config:
                source = ConfigSource.MYSQL
                logger.info(f"配置已从MySQL加载 [版本: {config.config_version}]")
        
        # 2. 尝试从JSON文件加载
        if config is None:
            config_path = json_path or cls.DEFAULT_CONFIG_PATH
            config = cls._load_from_json(config_path)
            if config:
                source = ConfigSource.JSON_FILE
                logger.info(f"配置已从JSON文件加载: {config_path} [版本: {config.config_version}]")
        
        # 3. 回退到默认配置
        if config is None:
            if fallback_to_default:
                config = cls()
                source = ConfigSource.DEFAULT
                logger.warning("使用默认配置（JSON和MySQL均不可用）")
            else:
                raise RuntimeError("无法加载配置，且不允许回退到默认配置")
        
        config.config_source = source.value
        config.loaded_at = datetime.now().isoformat()
        
        # 记录使用的权重
        logger.info(
            f"当前权重配置 - 情感:{config.sentiment_weight:.2f}, "
            f"热度:{config.heat_weight:.2f}, 时效性:{config.timeliness_weight:.2f} "
            f"[来源: {source.value}, 版本: {config.config_version}]"
        )
        
        return config
    
    @classmethod
    def _load_from_json(cls, json_path: str) -> Optional['DualDimensionConfig']:
        """从JSON文件加载配置"""
        try:
            if not os.path.exists(json_path):
                logger.debug(f"配置文件不存在: {json_path}")
                return None
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取权重配置
            config = cls(
                sentiment_weight=data.get('sentiment_weight', 0.4),
                heat_weight=data.get('heat_weight', 0.4),
                timeliness_weight=data.get('timeliness_weight', 0.2),
                repost_factor=data.get('repost_factor', 1.0),
                comment_factor=data.get('comment_factor', 2.0),
                like_factor=data.get('like_factor', 1.0),
                decay_half_life_hours=data.get('decay_half_life_hours', 24.0),
                sentiment_amplify=data.get('sentiment_amplify', 1.5),
                negative_boost=data.get('negative_boost', True),
                negative_boost_factor=data.get('negative_boost_factor', 1.2),
                config_version=data.get('version', '1.0.0'),
            )
            
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            logger.error(f"加载JSON配置失败: {e}")
            return None
    
    @classmethod
    def _load_from_mysql(cls, mysql_config: Dict[str, Any]) -> Optional['DualDimensionConfig']:
        """从MySQL数据库加载配置"""
        try:
            import pymysql
            
            conn = pymysql.connect(
                host=mysql_config.get('host', 'localhost'),
                port=mysql_config.get('port', 3306),
                user=mysql_config.get('user', 'root'),
                password=mysql_config.get('password', ''),
                database=mysql_config.get('database', 'weibo_sentiment_graduation'),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            try:
                with conn.cursor() as cursor:
                    # 查询最新的配置
                    sql = """
                        SELECT config_key, config_value 
                        FROM system_configs 
                        WHERE config_group = 'dual_dimension' 
                        AND status = 1
                        ORDER BY updated_at DESC
                    """
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    
                    if not rows:
                        logger.debug("MySQL中无双维度配置")
                        return None
                    
                    # 构建配置字典
                    config_dict = {}
                    for row in rows:
                        key = row['config_key']
                        value = row['config_value']
                        # 尝试解析数值
                        try:
                            if '.' in value:
                                config_dict[key] = float(value)
                            elif value.lower() in ('true', 'false'):
                                config_dict[key] = value.lower() == 'true'
                            else:
                                config_dict[key] = int(value)
                        except ValueError:
                            config_dict[key] = value
                    
                    # 获取版本号
                    version_sql = """
                        SELECT config_value FROM system_configs 
                        WHERE config_group = 'dual_dimension' 
                        AND config_key = 'version'
                    """
                    cursor.execute(version_sql)
                    version_row = cursor.fetchone()
                    version = version_row['config_value'] if version_row else '1.0.0'
                    
                    config = cls(
                        sentiment_weight=config_dict.get('sentiment_weight', 0.4),
                        heat_weight=config_dict.get('heat_weight', 0.4),
                        timeliness_weight=config_dict.get('timeliness_weight', 0.2),
                        repost_factor=config_dict.get('repost_factor', 1.0),
                        comment_factor=config_dict.get('comment_factor', 2.0),
                        like_factor=config_dict.get('like_factor', 1.0),
                        decay_half_life_hours=config_dict.get('decay_half_life_hours', 24.0),
                        sentiment_amplify=config_dict.get('sentiment_amplify', 1.5),
                        negative_boost=config_dict.get('negative_boost', True),
                        negative_boost_factor=config_dict.get('negative_boost_factor', 1.2),
                        config_version=version,
                    )
                    
                    return config
                    
            finally:
                conn.close()
                
        except ImportError:
            logger.debug("pymysql未安装，跳过MySQL配置加载")
            return None
        except Exception as e:
            logger.error(f"从MySQL加载配置失败: {e}")
            return None
    
    def save_to_json(self, json_path: Optional[str] = None) -> bool:
        """保存配置到JSON文件"""
        try:
            path = json_path or self.DEFAULT_CONFIG_PATH
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            data = {
                'version': self.config_version,
                'sentiment_weight': self.sentiment_weight,
                'heat_weight': self.heat_weight,
                'timeliness_weight': self.timeliness_weight,
                'repost_factor': self.repost_factor,
                'comment_factor': self.comment_factor,
                'like_factor': self.like_factor,
                'decay_half_life_hours': self.decay_half_life_hours,
                'sentiment_amplify': self.sentiment_amplify,
                'negative_boost': self.negative_boost,
                'negative_boost_factor': self.negative_boost_factor,
                'updated_at': datetime.now().isoformat(),
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已保存到: {path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'sentiment_weight': self.sentiment_weight,
            'heat_weight': self.heat_weight,
            'timeliness_weight': self.timeliness_weight,
            'repost_factor': self.repost_factor,
            'comment_factor': self.comment_factor,
            'like_factor': self.like_factor,
            'decay_half_life_hours': self.decay_half_life_hours,
            'sentiment_amplify': self.sentiment_amplify,
            'negative_boost': self.negative_boost,
            'negative_boost_factor': self.negative_boost_factor,
            'config_version': self.config_version,
            'config_source': self.config_source,
            'loaded_at': self.loaded_at,
        }


class DualDimensionRankingModel:
    """
    情感-热度双维度排序模型
    
    核心算法：
    DualScore = α * SentimentScore + β * HeatScore + γ * TimelinessScore
    
    其中：
    - SentimentScore: 情感强度得分，经过归一化和放大处理
    - HeatScore: 热度得分，基于转发、评论、点赞的加权计算
    - TimelinessScore: 时效性得分，基于指数衰减函数
    - α, β, γ: 可配置的权重参数，满足 α + β + γ = 1
    
    配置加载优先级：MySQL > JSON文件 > 默认值
    """
    
    def __init__(self, config: Optional[DualDimensionConfig] = None,
                 load_dynamic: bool = False,
                 json_path: Optional[str] = None,
                 mysql_config: Optional[Dict[str, Any]] = None):
        """
        初始化排序模型
        
        Args:
            config: 直接传入的配置对象
            load_dynamic: 是否动态加载配置（从JSON/MySQL）
            json_path: JSON配置文件路径
            mysql_config: MySQL连接配置
        """
        if config:
            self.config = config
            logger.info(f"使用传入的配置 [版本: {config.config_version}]")
        elif load_dynamic:
            self.config = DualDimensionConfig.load(
                json_path=json_path,
                mysql_config=mysql_config,
                fallback_to_default=True
            )
        else:
            self.config = DualDimensionConfig()
            logger.info("使用默认配置")
        
        self._validate_config()
        self._log_config_info()
        
    def _validate_config(self):
        """验证配置参数"""
        total_weight = (
            self.config.sentiment_weight + 
            self.config.heat_weight + 
            self.config.timeliness_weight
        )
        if abs(total_weight - 1.0) > 0.001:
            # 自动归一化
            logger.warning(
                f"权重总和为 {total_weight:.3f}，自动归一化到 1.0"
            )
            self.config.sentiment_weight /= total_weight
            self.config.heat_weight /= total_weight
            self.config.timeliness_weight /= total_weight
    
    def _log_config_info(self):
        """记录配置信息"""
        logger.info(
            f"双维度排序模型初始化完成 | "
            f"权重: 情感={self.config.sentiment_weight:.2f}, "
            f"热度={self.config.heat_weight:.2f}, "
            f"时效={self.config.timeliness_weight:.2f} | "
            f"来源: {self.config.config_source} | "
            f"版本: {self.config.config_version}"
        )
    
    def calculate_heat_score(self, item: WeiboItem) -> float:
        """
        计算热度得分
        
        公式：HeatScore = log(1 + α*转发 + β*评论 + γ*点赞)
        使用对数函数平滑极端值
        """
        raw_heat = (
            self.config.repost_factor * item.reposts_count +
            self.config.comment_factor * item.comments_count +
            self.config.like_factor * item.attitudes_count
        )
        # 使用对数函数平滑，避免极端值影响
        heat_score = math.log(1 + raw_heat)
        return heat_score
    
    def calculate_timeliness_score(self, item: WeiboItem, 
                                    reference_time: Optional[datetime] = None) -> float:
        """
        计算时效性得分
        
        使用指数衰减函数：TimelinessScore = exp(-λ * Δt)
        其中 λ = ln(2) / 半衰期
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        # 计算时间差（小时）
        time_diff = (reference_time - item.created_at).total_seconds() / 3600
        
        # 指数衰减
        decay_constant = math.log(2) / self.config.decay_half_life_hours
        timeliness_score = math.exp(-decay_constant * max(0, time_diff))
        
        return timeliness_score
    
    def calculate_sentiment_score(self, item: WeiboItem) -> float:
        """
        计算情感强度得分
        
        对原始情感得分进行处理：
        1. 取绝对值（关注强度而非极性）
        2. 应用放大因子
        3. 对负面情感可选择性增强
        """
        raw_score = item.sentiment_score
        
        # 计算情感强度（绝对值）
        intensity = abs(raw_score)
        
        # 应用放大因子
        amplified = intensity * self.config.sentiment_amplify
        
        # 负面情感增强（负面舆情通常更需要关注）
        if self.config.negative_boost and raw_score < 0:
            amplified *= self.config.negative_boost_factor
        
        # 归一化到 [0, 1]
        normalized = min(1.0, amplified)
        
        return normalized
    
    def calculate_dual_score(self, item: WeiboItem,
                             reference_time: Optional[datetime] = None) -> float:
        """
        计算双维度综合得分
        
        DualScore = α * SentimentScore + β * HeatScore + γ * TimelinessScore
        """
        # 计算各维度得分
        sentiment_score = self.calculate_sentiment_score(item)
        heat_score = self.calculate_heat_score(item)
        timeliness_score = self.calculate_timeliness_score(item, reference_time)
        
        # 热度得分归一化（假设最大热度对应 log(1+100000) ≈ 11.5）
        normalized_heat = min(1.0, heat_score / 11.5)
        
        # 加权求和
        dual_score = (
            self.config.sentiment_weight * sentiment_score +
            self.config.heat_weight * normalized_heat +
            self.config.timeliness_weight * timeliness_score
        )
        
        return dual_score
    
    def rank_items(self, items: List[WeiboItem],
                   reference_time: Optional[datetime] = None,
                   top_k: Optional[int] = None) -> List[WeiboItem]:
        """
        对微博列表进行双维度排序
        
        Args:
            items: 微博数据列表
            reference_time: 参考时间点
            top_k: 返回前k个结果
            
        Returns:
            排序后的微博列表
        """
        # 计算每个item的得分
        for item in items:
            item.heat_score = self.calculate_heat_score(item)
            item.dual_score = self.calculate_dual_score(item, reference_time)
        
        # 按双维度得分降序排序
        sorted_items = sorted(items, key=lambda x: x.dual_score, reverse=True)
        
        # 分配排名
        for i, item in enumerate(sorted_items):
            item.rank = i + 1
        
        if top_k:
            return sorted_items[:top_k]
        return sorted_items
    
    def get_score_breakdown(self, item: WeiboItem,
                            reference_time: Optional[datetime] = None) -> Dict[str, float]:
        """获取得分分解详情"""
        sentiment_score = self.calculate_sentiment_score(item)
        heat_score = self.calculate_heat_score(item)
        timeliness_score = self.calculate_timeliness_score(item, reference_time)
        normalized_heat = min(1.0, heat_score / 11.5)
        
        return {
            "sentiment_score": round(sentiment_score, 4),
            "sentiment_contribution": round(self.config.sentiment_weight * sentiment_score, 4),
            "heat_score": round(heat_score, 4),
            "heat_normalized": round(normalized_heat, 4),
            "heat_contribution": round(self.config.heat_weight * normalized_heat, 4),
            "timeliness_score": round(timeliness_score, 4),
            "timeliness_contribution": round(self.config.timeliness_weight * timeliness_score, 4),
            "dual_score": round(self.calculate_dual_score(item, reference_time), 4),
        }


class SparkDualDimensionProcessor:
    """
    基于Spark的双维度排序处理器
    
    支持大规模数据的分布式处理
    """
    
    def __init__(self, spark: Optional['SparkSession'] = None,
                 config: Optional[DualDimensionConfig] = None):
        self.config = config or DualDimensionConfig()
        
        if spark:
            self.spark = spark
        elif SPARK_AVAILABLE:
            self.spark = SparkSession.builder \
                .appName("DualDimensionRanking") \
                .master("local[*]") \
                .config("spark.driver.memory", "2g") \
                .config("spark.sql.shuffle.partitions", "4") \
                .getOrCreate()
        else:
            self.spark = None
    
    def process_dataframe(self, df: 'DataFrame', 
                          reference_time: Optional[datetime] = None) -> 'DataFrame':
        """
        使用Spark DataFrame处理大规模数据
        
        Args:
            df: 包含微博数据的DataFrame
            reference_time: 参考时间
            
        Returns:
            添加了排序得分的DataFrame
        """
        if not SPARK_AVAILABLE or self.spark is None:
            raise RuntimeError("Spark不可用")
        
        if reference_time is None:
            reference_time = datetime.now()
        
        ref_timestamp = reference_time.timestamp()
        
        # 配置参数广播
        config = self.config
        
        # 计算热度得分
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
            F.least(F.lit(1.0), F.col("heat_score") / 11.5)
        )
        
        # 计算时效性得分
        decay_constant = math.log(2) / config.decay_half_life_hours
        df = df.withColumn(
            "time_diff_hours",
            (F.lit(ref_timestamp) - F.unix_timestamp("created_at")) / 3600
        ).withColumn(
            "timeliness_score",
            F.exp(-decay_constant * F.greatest(F.lit(0), F.col("time_diff_hours")))
        )
        
        # 计算情感强度得分
        df = df.withColumn(
            "sentiment_intensity",
            F.abs(F.col("sentiment_score")) * config.sentiment_amplify
        )
        
        if config.negative_boost:
            df = df.withColumn(
                "sentiment_intensity",
                F.when(
                    F.col("sentiment_score") < 0,
                    F.col("sentiment_intensity") * config.negative_boost_factor
                ).otherwise(F.col("sentiment_intensity"))
            )
        
        df = df.withColumn(
            "sentiment_normalized",
            F.least(F.lit(1.0), F.col("sentiment_intensity"))
        )
        
        # 计算双维度综合得分
        df = df.withColumn(
            "dual_score",
            config.sentiment_weight * F.col("sentiment_normalized") +
            config.heat_weight * F.col("heat_normalized") +
            config.timeliness_weight * F.col("timeliness_score")
        )
        
        # 添加排名
        window = Window.orderBy(F.desc("dual_score"))
        df = df.withColumn("rank", F.row_number().over(window))
        
        return df
    
    def get_top_k(self, df: 'DataFrame', k: int = 100) -> 'DataFrame':
        """获取Top-K结果"""
        return df.orderBy(F.desc("dual_score")).limit(k)
    
    def get_statistics(self, df: 'DataFrame') -> Dict[str, Any]:
        """获取统计信息"""
        stats = df.agg(
            F.count("*").alias("total_count"),
            F.avg("dual_score").alias("avg_dual_score"),
            F.max("dual_score").alias("max_dual_score"),
            F.min("dual_score").alias("min_dual_score"),
            F.avg("heat_score").alias("avg_heat_score"),
            F.avg("sentiment_score").alias("avg_sentiment_score"),
            F.sum(F.when(F.col("sentiment_score") > 0, 1).otherwise(0)).alias("positive_count"),
            F.sum(F.when(F.col("sentiment_score") < 0, 1).otherwise(0)).alias("negative_count"),
            F.sum(F.when(F.col("sentiment_score") == 0, 1).otherwise(0)).alias("neutral_count"),
        ).collect()[0]
        
        return {
            "total_count": stats["total_count"],
            "avg_dual_score": round(stats["avg_dual_score"], 4) if stats["avg_dual_score"] else 0,
            "max_dual_score": round(stats["max_dual_score"], 4) if stats["max_dual_score"] else 0,
            "min_dual_score": round(stats["min_dual_score"], 4) if stats["min_dual_score"] else 0,
            "avg_heat_score": round(stats["avg_heat_score"], 4) if stats["avg_heat_score"] else 0,
            "avg_sentiment_score": round(stats["avg_sentiment_score"], 4) if stats["avg_sentiment_score"] else 0,
            "sentiment_distribution": {
                "positive": stats["positive_count"] or 0,
                "negative": stats["negative_count"] or 0,
                "neutral": stats["neutral_count"] or 0,
            }
        }


# 便捷函数
def create_ranking_model(sentiment_weight: float = None,
                         heat_weight: float = None,
                         timeliness_weight: float = None,
                         load_dynamic: bool = True,
                         json_path: Optional[str] = None,
                         mysql_config: Optional[Dict[str, Any]] = None) -> DualDimensionRankingModel:
    """
    创建排序模型的便捷函数
    
    Args:
        sentiment_weight: 情感权重（指定则覆盖动态配置）
        heat_weight: 热度权重（指定则覆盖动态配置）
        timeliness_weight: 时效性权重（指定则覆盖动态配置）
        load_dynamic: 是否动态加载配置（从JSON/MySQL）
        json_path: JSON配置文件路径
        mysql_config: MySQL连接配置
        
    Returns:
        DualDimensionRankingModel实例
    """
    # 如果指定了权重参数，则使用指定的配置
    if sentiment_weight is not None or heat_weight is not None or timeliness_weight is not None:
        config = DualDimensionConfig(
            sentiment_weight=sentiment_weight or 0.4,
            heat_weight=heat_weight or 0.4,
            timeliness_weight=timeliness_weight or 0.2
        )
        return DualDimensionRankingModel(config)
    
    # 否则使用动态加载
    return DualDimensionRankingModel(
        load_dynamic=load_dynamic,
        json_path=json_path,
        mysql_config=mysql_config
    )


def rank_weibo_data(data: List[Dict], 
                    sentiment_weight: float = None,
                    heat_weight: float = None,
                    load_dynamic: bool = True,
                    mysql_config: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """
    对微博数据进行双维度排序
    
    Args:
        data: 微博数据列表（字典格式）
        sentiment_weight: 情感权重（可选，指定则覆盖动态配置）
        heat_weight: 热度权重（可选，指定则覆盖动态配置）
        load_dynamic: 是否动态加载配置
        mysql_config: MySQL连接配置
        
    Returns:
        排序后的数据列表
    """
    # 计算时效性权重
    timeliness_weight = None
    if sentiment_weight is not None and heat_weight is not None:
        timeliness_weight = 1 - sentiment_weight - heat_weight
    
    model = create_ranking_model(
        sentiment_weight=sentiment_weight,
        heat_weight=heat_weight,
        timeliness_weight=timeliness_weight,
        load_dynamic=load_dynamic,
        mysql_config=mysql_config
    )
    
    # 转换为WeiboItem
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
            
        item = WeiboItem(
            id=str(d.get('id', '')),
            text=d.get('text', ''),
            user_id=str(d.get('user_id', '')),
            user_name=d.get('user_name', ''),
            created_at=created_at,
            reposts_count=d.get('reposts_count', 0),
            comments_count=d.get('comments_count', 0),
            attitudes_count=d.get('attitudes_count', 0),
            sentiment_score=d.get('sentiment_score', 0.0),
            sentiment_label=d.get('sentiment_label', 'neutral'),
        )
        items.append(item)
    
    # 排序
    ranked_items = model.rank_items(items)
    
    # 转换回字典
    result = []
    for item in ranked_items:
        result.append({
            'id': item.id,
            'text': item.text,
            'user_id': item.user_id,
            'user_name': item.user_name,
            'created_at': item.created_at.isoformat(),
            'reposts_count': item.reposts_count,
            'comments_count': item.comments_count,
            'attitudes_count': item.attitudes_count,
            'sentiment_score': item.sentiment_score,
            'sentiment_label': item.sentiment_label,
            'heat_score': round(item.heat_score, 4),
            'dual_score': round(item.dual_score, 4),
            'rank': item.rank,
            'score_breakdown': model.get_score_breakdown(item),
        })
    
    return result


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("情感-热度双维度排序模型测试")
    print("=" * 60)
    
    # 创建测试数据
    test_data = [
        {
            'id': '1',
            'text': '这个产品太棒了，强烈推荐！',
            'user_id': 'u1',
            'user_name': '用户A',
            'created_at': datetime.now() - timedelta(hours=2),
            'reposts_count': 1000,
            'comments_count': 500,
            'attitudes_count': 5000,
            'sentiment_score': 0.9,
            'sentiment_label': 'positive',
        },
        {
            'id': '2',
            'text': '服务态度太差了，再也不来了！',
            'user_id': 'u2',
            'user_name': '用户B',
            'created_at': datetime.now() - timedelta(hours=1),
            'reposts_count': 2000,
            'comments_count': 1000,
            'attitudes_count': 3000,
            'sentiment_score': -0.85,
            'sentiment_label': 'negative',
        },
        {
            'id': '3',
            'text': '今天天气不错',
            'user_id': 'u3',
            'user_name': '用户C',
            'created_at': datetime.now() - timedelta(hours=12),
            'reposts_count': 10,
            'comments_count': 5,
            'attitudes_count': 50,
            'sentiment_score': 0.1,
            'sentiment_label': 'neutral',
        },
        {
            'id': '4',
            'text': '紧急！发现重大安全隐患！',
            'user_id': 'u4',
            'user_name': '用户D',
            'created_at': datetime.now() - timedelta(minutes=30),
            'reposts_count': 5000,
            'comments_count': 2000,
            'attitudes_count': 1000,
            'sentiment_score': -0.95,
            'sentiment_label': 'negative',
        },
    ]
    
    # 排序
    ranked = rank_weibo_data(test_data)
    
    print("\n排序结果：")
    print("-" * 60)
    for item in ranked:
        print(f"排名 {item['rank']}: {item['text'][:20]}...")
        print(f"  情感: {item['sentiment_label']} ({item['sentiment_score']})")
        print(f"  热度得分: {item['heat_score']}")
        print(f"  双维度得分: {item['dual_score']}")
        print(f"  得分分解: {item['score_breakdown']}")
        print()
