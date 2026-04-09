"""
基于Spark的分布式数据存储与处理架构
=====================================

实现功能：
1. Spark集群管理与配置优化
2. 分布式数据存储（支持HDFS、本地文件）
3. 批量数据处理流水线
4. 实时流处理（Structured Streaming）
5. 情感分析UDF
6. 双维度排序分布式计算

技术特点：
- 自适应资源分配
- 动态分区优化
- 广播变量优化
- 结果缓存机制

作者：毕业设计
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from functools import lru_cache
import math

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SparkEngine')

# Spark相关导入
SPARK_AVAILABLE = False
try:
    from pyspark.sql import SparkSession, DataFrame, Row
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, IntegerType, 
        FloatType, TimestampType, ArrayType, BooleanType,
        DoubleType
    )
    from pyspark.sql.window import Window
    from pyspark.ml.feature import HashingTF, IDF, Tokenizer
    from pyspark.ml.clustering import KMeans
    from pyspark.broadcast import Broadcast
    SPARK_AVAILABLE = True
    logger.info("PySpark已加载")
except ImportError as e:
    logger.warning(f"PySpark未安装: {e}")

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入情感词典
try:
    from spark.sentiment_analyzer import SentimentLexicon
    LEXICON_AVAILABLE = True
except ImportError:
    LEXICON_AVAILABLE = False


# ==================== 配置类 ====================

@dataclass
class SparkConfig:
    """Spark配置"""
    app_name: str = "WeiboSentimentAnalysis"
    master: str = "local[*]"
    
    # 内存配置
    driver_memory: str = "4g"
    executor_memory: str = "4g"
    executor_cores: int = 4
    
    # 并行度配置
    default_parallelism: int = 8
    shuffle_partitions: int = 8
    
    # 优化配置
    enable_adaptive: bool = True
    adaptive_coalesce_partitions: bool = True
    broadcast_threshold: int = 10 * 1024 * 1024  # 10MB
    
    # 序列化配置
    serializer: str = "org.apache.spark.serializer.KryoSerializer"
    
    # 检查点配置
    checkpoint_dir: str = "./spark_checkpoint"
    
    # 日志级别
    log_level: str = "WARN"


@dataclass 
class DualDimensionSparkConfig:
    """双维度模型Spark配置"""
    # 权重配置
    sentiment_weight: float = 0.4
    heat_weight: float = 0.4
    timeliness_weight: float = 0.2
    
    # 热度计算参数
    repost_factor: float = 1.0
    comment_factor: float = 2.0
    like_factor: float = 1.0
    
    # 时间衰减参数
    decay_half_life_hours: float = 24.0
    
    # 情感放大参数
    sentiment_amplify: float = 1.5
    negative_boost: bool = True
    negative_boost_factor: float = 1.2


# ==================== Schema定义 ====================

# 原始微博数据Schema
WEIBO_RAW_SCHEMA = None
WEIBO_PROCESSED_SCHEMA = None
SENTIMENT_RESULT_SCHEMA = None

if SPARK_AVAILABLE:
    WEIBO_RAW_SCHEMA = StructType([
        StructField("id", StringType(), True),
        StructField("mid", StringType(), True),
        StructField("text", StringType(), True),
        StructField("source", StringType(), True),
        StructField("created_at", StringType(), True),
        StructField("user_id", StringType(), True),
        StructField("user_name", StringType(), True),
        StructField("user_followers", IntegerType(), True),
        StructField("user_verified", BooleanType(), True),
        StructField("reposts_count", IntegerType(), True),
        StructField("comments_count", IntegerType(), True),
        StructField("attitudes_count", IntegerType(), True),
        StructField("keyword", StringType(), True),
        StructField("crawl_time", StringType(), True),
    ])
    
    WEIBO_PROCESSED_SCHEMA = StructType([
        StructField("id", StringType(), True),
        StructField("text_raw", StringType(), True),
        StructField("text_clean", StringType(), True),
        StructField("user_id", StringType(), True),
        StructField("user_name", StringType(), True),
        StructField("reposts_count", IntegerType(), True),
        StructField("comments_count", IntegerType(), True),
        StructField("attitudes_count", IntegerType(), True),
        StructField("created_at", TimestampType(), True),
        StructField("sentiment", StringType(), True),
        StructField("sentiment_score", FloatType(), True),
        StructField("sentiment_confidence", FloatType(), True),
        StructField("heat_score", FloatType(), True),
        StructField("dual_score", FloatType(), True),
        StructField("rank", IntegerType(), True),
    ])


# ==================== Spark会话管理 ====================

class SparkSessionManager:
    """
    Spark会话管理器
    
    功能：
    1. 单例模式管理SparkSession
    2. 自动配置优化
    3. 资源监控
    """
    
    _instance = None
    _spark: 'SparkSession' = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_or_create(self, config: SparkConfig = None) -> 'SparkSession':
        """获取或创建SparkSession"""
        if not SPARK_AVAILABLE:
            raise RuntimeError("PySpark未安装")
        
        if self._spark is not None and not self._spark._jvm.SparkSession.getActiveSession().isEmpty():
            return self._spark
        
        config = config or SparkConfig()
        
        builder = SparkSession.builder \
            .appName(config.app_name) \
            .master(config.master)
        
        # 内存配置
        builder = builder \
            .config("spark.driver.memory", config.driver_memory) \
            .config("spark.executor.memory", config.executor_memory) \
            .config("spark.executor.cores", config.executor_cores)
        
        # 并行度配置
        builder = builder \
            .config("spark.default.parallelism", config.default_parallelism) \
            .config("spark.sql.shuffle.partitions", config.shuffle_partitions)
        
        # 自适应执行
        if config.enable_adaptive:
            builder = builder \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", 
                       str(config.adaptive_coalesce_partitions).lower())
        
        # 广播阈值
        builder = builder \
            .config("spark.sql.autoBroadcastJoinThreshold", config.broadcast_threshold)
        
        # 序列化
        builder = builder \
            .config("spark.serializer", config.serializer)
        
        # 创建Session
        self._spark = builder.getOrCreate()
        self._spark.sparkContext.setLogLevel(config.log_level)
        
        # 设置检查点目录
        checkpoint_path = os.path.abspath(config.checkpoint_dir)
        os.makedirs(checkpoint_path, exist_ok=True)
        self._spark.sparkContext.setCheckpointDir(checkpoint_path)
        
        logger.info(f"SparkSession已创建: {config.app_name}")
        return self._spark
    
    def stop(self):
        """停止SparkSession"""
        if self._spark:
            self._spark.stop()
            self._spark = None
            logger.info("SparkSession已停止")
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息"""
        if not self._spark:
            return {"status": "not_started"}
        
        sc = self._spark.sparkContext
        
        return {
            "app_name": sc.appName,
            "master": sc.master,
            "spark_version": sc.version,
            "default_parallelism": sc.defaultParallelism,
            "web_ui_url": sc.uiWebUrl,
            "status": "running"
        }


# ==================== 情感分析UDF ====================

class SentimentUDFFactory:
    """
    情感分析UDF工厂
    
    创建可在Spark中使用的情感分析函数
    """
    
    def __init__(self, spark: 'SparkSession'):
        self.spark = spark
        self._lexicon_broadcast = None
    
    def _broadcast_lexicon(self):
        """广播情感词典"""
        if self._lexicon_broadcast is not None:
            return
        
        if not LEXICON_AVAILABLE:
            return
        
        # 收集词典数据
        lexicon_data = {
            'positive_words': list(SentimentLexicon.POSITIVE_WORDS),
            'negative_words': list(SentimentLexicon.NEGATIVE_WORDS),
            'negation_words': list(SentimentLexicon.NEGATION_WORDS),
            'degree_words': dict(SentimentLexicon.DEGREE_WORDS),
        }
        
        self._lexicon_broadcast = self.spark.sparkContext.broadcast(lexicon_data)
        logger.info("情感词典已广播到集群")
    
    def create_sentiment_udf(self):
        """创建情感分析UDF"""
        from pyspark.sql.functions import udf
        from pyspark.sql.types import StructType, StructField, StringType, FloatType
        
        self._broadcast_lexicon()
        lexicon_bc = self._lexicon_broadcast
        
        result_schema = StructType([
            StructField("sentiment", StringType(), True),
            StructField("score", FloatType(), True),
            StructField("confidence", FloatType(), True),
        ])
        
        def analyze_sentiment(text):
            """情感分析函数"""
            if not text:
                return ("neutral", 0.0, 0.5)
            
            try:
                # 使用广播的词典
                if lexicon_bc is None:
                    return ("neutral", 0.0, 0.5)
                
                lexicon = lexicon_bc.value
                positive_words = set(lexicon['positive_words'])
                negative_words = set(lexicon['negative_words'])
                negation_words = set(lexicon['negation_words'])
                degree_words = lexicon['degree_words']
                
                # 简单分词
                import re
                words = re.findall(r'[\u4e00-\u9fa5]+', text)
                
                # 计算情感得分
                positive_score = 0
                negative_score = 0
                negation = False
                degree = 1.0
                
                for i, word in enumerate(words):
                    # 检查否定词
                    if word in negation_words:
                        negation = True
                        continue
                    
                    # 检查程度词
                    if word in degree_words:
                        degree = degree_words[word]
                        continue
                    
                    # 计算情感
                    if word in positive_words:
                        score = 1 * degree
                        if negation:
                            negative_score += score
                            negation = False
                        else:
                            positive_score += score
                    elif word in negative_words:
                        score = 1 * degree
                        if negation:
                            positive_score += score
                            negation = False
                        else:
                            negative_score += score
                    
                    # 重置程度词
                    degree = 1.0
                
                # 计算最终得分
                total = positive_score + negative_score
                if total == 0:
                    return ("neutral", 0.0, 0.5)
                
                score = (positive_score - negative_score) / max(1, total) * 0.5
                score = max(-1.0, min(1.0, score))
                
                # 确定情感极性
                if score > 0.1:
                    sentiment = "positive"
                elif score < -0.1:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"
                
                confidence = min(1.0, abs(score) + 0.3)
                
                return (sentiment, float(score), float(confidence))
                
            except Exception as e:
                return ("neutral", 0.0, 0.5)
        
        return udf(analyze_sentiment, result_schema)
    
    def create_batch_sentiment_udf(self):
        """创建批量情感分析UDF（使用pandas_udf优化）"""
        try:
            from pyspark.sql.functions import pandas_udf
            import pandas as pd
            
            self._broadcast_lexicon()
            lexicon_bc = self._lexicon_broadcast
            
            @pandas_udf("struct<sentiment:string, score:float, confidence:float>")
            def batch_analyze(texts: pd.Series) -> pd.DataFrame:
                results = []
                
                lexicon = lexicon_bc.value if lexicon_bc else None
                
                for text in texts:
                    if not text or lexicon is None:
                        results.append({"sentiment": "neutral", "score": 0.0, "confidence": 0.5})
                        continue
                    
                    # 简化分析逻辑
                    positive_words = set(lexicon['positive_words'])
                    negative_words = set(lexicon['negative_words'])
                    
                    import re
                    words = re.findall(r'[\u4e00-\u9fa5]+', text)
                    
                    pos_count = sum(1 for w in words if w in positive_words)
                    neg_count = sum(1 for w in words if w in negative_words)
                    
                    total = pos_count + neg_count
                    if total == 0:
                        results.append({"sentiment": "neutral", "score": 0.0, "confidence": 0.5})
                    else:
                        score = (pos_count - neg_count) / total
                        sentiment = "positive" if score > 0.1 else ("negative" if score < -0.1 else "neutral")
                        results.append({
                            "sentiment": sentiment,
                            "score": float(score),
                            "confidence": float(min(1.0, abs(score) + 0.3))
                        })
                
                return pd.DataFrame(results)
            
            return batch_analyze
            
        except Exception as e:
            logger.warning(f"pandas_udf创建失败，使用普通UDF: {e}")
            return self.create_sentiment_udf()


# ==================== 双维度排序处理器 ====================

class DualDimensionProcessor:
    """
    双维度排序Spark处理器
    
    实现情感-热度双维度排序的分布式计算
    """
    
    def __init__(self, spark: 'SparkSession', config: DualDimensionSparkConfig = None):
        self.spark = spark
        self.config = config or DualDimensionSparkConfig()
        self._sentiment_udf_factory = SentimentUDFFactory(spark)
    
    def process(self, df: 'DataFrame', 
                reference_time: datetime = None) -> 'DataFrame':
        """
        处理DataFrame，添加双维度排序
        
        Args:
            df: 输入DataFrame，需要包含以下列：
                - text: 文本内容
                - reposts_count: 转发数
                - comments_count: 评论数
                - attitudes_count: 点赞数
                - created_at: 创建时间
            reference_time: 参考时间点
            
        Returns:
            添加了情感分析和双维度得分的DataFrame
        """
        if reference_time is None:
            reference_time = datetime.now()
        
        ref_timestamp = reference_time.timestamp()
        config = self.config
        
        # 1. 情感分析
        if "sentiment_score" not in df.columns:
            sentiment_udf = self._sentiment_udf_factory.create_sentiment_udf()
            df = df.withColumn("_sentiment_result", sentiment_udf(F.col("text")))
            df = df.withColumn("sentiment", F.col("_sentiment_result.sentiment"))
            df = df.withColumn("sentiment_score", F.col("_sentiment_result.score"))
            df = df.withColumn("sentiment_confidence", F.col("_sentiment_result.confidence"))
            df = df.drop("_sentiment_result")
        
        # 2. 计算热度得分
        # HeatScore = log(1 + α*转发 + β*评论 + γ*点赞)
        df = df.withColumn(
            "heat_raw",
            config.repost_factor * F.coalesce(F.col("reposts_count"), F.lit(0)) +
            config.comment_factor * F.coalesce(F.col("comments_count"), F.lit(0)) +
            config.like_factor * F.coalesce(F.col("attitudes_count"), F.lit(0))
        )
        df = df.withColumn("heat_score", F.log1p(F.col("heat_raw")))
        df = df.withColumn("heat_normalized", F.least(F.lit(1.0), F.col("heat_score") / 11.5))
        
        # 3. 计算时效性得分
        # TimelinessScore = exp(-λ * Δt)
        decay_constant = math.log(2) / config.decay_half_life_hours
        
        # 处理时间列
        df = df.withColumn(
            "_created_timestamp",
            F.coalesce(
                F.unix_timestamp(F.col("created_at")),
                F.lit(ref_timestamp)
            )
        )
        df = df.withColumn(
            "time_diff_hours",
            (F.lit(ref_timestamp) - F.col("_created_timestamp")) / 3600
        )
        df = df.withColumn(
            "timeliness_score",
            F.exp(-decay_constant * F.greatest(F.lit(0.0), F.col("time_diff_hours")))
        )
        
        # 4. 计算情感强度得分
        df = df.withColumn(
            "sentiment_intensity",
            F.abs(F.col("sentiment_score")) * config.sentiment_amplify
        )
        
        # 负面情感增强
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
        
        # 5. 计算双维度综合得分
        # DualScore = α * SentimentScore + β * HeatScore + γ * TimelinessScore
        df = df.withColumn(
            "dual_score",
            config.sentiment_weight * F.col("sentiment_normalized") +
            config.heat_weight * F.col("heat_normalized") +
            config.timeliness_weight * F.col("timeliness_score")
        )
        
        # 6. 添加排名
        window = Window.orderBy(F.desc("dual_score"))
        df = df.withColumn("rank", F.row_number().over(window))
        
        # 7. 清理临时列
        df = df.drop("heat_raw", "_created_timestamp", "time_diff_hours", 
                    "sentiment_intensity")
        
        return df
    
    def get_top_k(self, df: 'DataFrame', k: int = 100) -> 'DataFrame':
        """获取Top-K结果"""
        return df.orderBy(F.desc("dual_score")).limit(k)
    
    def get_quadrant_distribution(self, df: 'DataFrame') -> Dict[str, int]:
        """
        获取四象限分布
        
        四象限定义：
        - 高情感高热度
        - 高情感低热度
        - 低情感高热度
        - 低情感低热度
        """
        # 计算阈值（使用中位数）
        stats = df.select(
            F.percentile_approx("sentiment_normalized", 0.5).alias("sentiment_median"),
            F.percentile_approx("heat_normalized", 0.5).alias("heat_median")
        ).collect()[0]
        
        sentiment_threshold = stats["sentiment_median"] or 0.5
        heat_threshold = stats["heat_median"] or 0.5
        
        # 分类统计
        result = df.withColumn(
            "quadrant",
            F.when(
                (F.col("sentiment_normalized") >= sentiment_threshold) & 
                (F.col("heat_normalized") >= heat_threshold),
                "high_sentiment_high_heat"
            ).when(
                (F.col("sentiment_normalized") >= sentiment_threshold) & 
                (F.col("heat_normalized") < heat_threshold),
                "high_sentiment_low_heat"
            ).when(
                (F.col("sentiment_normalized") < sentiment_threshold) & 
                (F.col("heat_normalized") >= heat_threshold),
                "low_sentiment_high_heat"
            ).otherwise("low_sentiment_low_heat")
        ).groupBy("quadrant").count().collect()
        
        distribution = {
            "high_sentiment_high_heat": 0,
            "high_sentiment_low_heat": 0,
            "low_sentiment_high_heat": 0,
            "low_sentiment_low_heat": 0
        }
        
        for row in result:
            distribution[row["quadrant"]] = row["count"]
        
        return distribution
    
    def get_statistics(self, df: 'DataFrame') -> Dict[str, Any]:
        """获取统计信息"""
        stats = df.agg(
            F.count("*").alias("total_count"),
            F.avg("dual_score").alias("avg_dual_score"),
            F.max("dual_score").alias("max_dual_score"),
            F.min("dual_score").alias("min_dual_score"),
            F.stddev("dual_score").alias("stddev_dual_score"),
            F.avg("heat_normalized").alias("avg_heat"),
            F.avg("sentiment_score").alias("avg_sentiment"),
            F.sum(F.when(F.col("sentiment") == "positive", 1).otherwise(0)).alias("positive_count"),
            F.sum(F.when(F.col("sentiment") == "negative", 1).otherwise(0)).alias("negative_count"),
            F.sum(F.when(F.col("sentiment") == "neutral", 1).otherwise(0)).alias("neutral_count"),
        ).collect()[0]
        
        total = stats["total_count"] or 1
        
        return {
            "total_count": total,
            "avg_dual_score": round(stats["avg_dual_score"] or 0, 4),
            "max_dual_score": round(stats["max_dual_score"] or 0, 4),
            "min_dual_score": round(stats["min_dual_score"] or 0, 4),
            "stddev_dual_score": round(stats["stddev_dual_score"] or 0, 4),
            "avg_heat": round(stats["avg_heat"] or 0, 4),
            "avg_sentiment": round(stats["avg_sentiment"] or 0, 4),
            "sentiment_distribution": {
                "positive": stats["positive_count"] or 0,
                "negative": stats["negative_count"] or 0,
                "neutral": stats["neutral_count"] or 0,
            },
            "sentiment_percentage": {
                "positive": round((stats["positive_count"] or 0) / total * 100, 2),
                "negative": round((stats["negative_count"] or 0) / total * 100, 2),
                "neutral": round((stats["neutral_count"] or 0) / total * 100, 2),
            }
        }


# ==================== 数据存储管理 ====================

class SparkDataStore:
    """
    Spark数据存储管理
    
    支持多种存储格式：
    - JSON
    - Parquet（推荐，高效列式存储）
    - CSV
    """
    
    def __init__(self, spark: 'SparkSession', base_path: str = "./spark_data"):
        self.spark = spark
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
    
    def save_dataframe(self, df: 'DataFrame', name: str, 
                       format: str = "parquet", mode: str = "overwrite",
                       partition_by: List[str] = None) -> str:
        """
        保存DataFrame
        
        Args:
            df: 要保存的DataFrame
            name: 数据集名称
            format: 存储格式 (parquet/json/csv)
            mode: 写入模式 (overwrite/append)
            partition_by: 分区列
            
        Returns:
            保存路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.base_path, f"{name}_{timestamp}")
        
        writer = df.write.mode(mode)
        
        if partition_by:
            writer = writer.partitionBy(*partition_by)
        
        if format == "parquet":
            writer.parquet(path)
        elif format == "json":
            writer.json(path)
        elif format == "csv":
            writer.option("header", "true").csv(path)
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        logger.info(f"数据已保存: {path}")
        return path
    
    def load_dataframe(self, path: str, format: str = "parquet",
                       schema: StructType = None) -> 'DataFrame':
        """
        加载DataFrame
        
        Args:
            path: 数据路径
            format: 存储格式
            schema: 数据Schema
            
        Returns:
            加载的DataFrame
        """
        reader = self.spark.read
        
        if schema:
            reader = reader.schema(schema)
        
        if format == "parquet":
            return reader.parquet(path)
        elif format == "json":
            return reader.json(path)
        elif format == "csv":
            return reader.option("header", "true").csv(path)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def load_json_files(self, pattern: str, schema: StructType = None) -> 'DataFrame':
        """加载JSON文件"""
        reader = self.spark.read
        if schema:
            reader = reader.schema(schema)
        return reader.json(pattern)
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """列出所有数据集"""
        datasets = []
        
        for item in os.listdir(self.base_path):
            item_path = os.path.join(self.base_path, item)
            if os.path.isdir(item_path):
                # 获取目录大小
                size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(item_path)
                    for filename in filenames
                )
                
                datasets.append({
                    "name": item,
                    "path": item_path,
                    "size_mb": round(size / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(item_path)
                    ).isoformat()
                })
        
        return sorted(datasets, key=lambda x: x["modified"], reverse=True)


# ==================== Spark引擎主类 ====================

class SparkEngine:
    """
    Spark分析引擎
    
    整合所有Spark功能的统一入口
    """
    
    def __init__(self, config: SparkConfig = None):
        """
        初始化Spark引擎
        
        Args:
            config: Spark配置
        """
        if not SPARK_AVAILABLE:
            raise RuntimeError("PySpark未安装，无法使用SparkEngine")
        
        self.config = config or SparkConfig()
        self._session_manager = SparkSessionManager()
        self._spark = None
        self._dual_processor = None
        self._data_store = None
        
        # 统计信息
        self.stats = {
            "jobs_completed": 0,
            "total_records_processed": 0,
            "start_time": datetime.now().isoformat(),
        }
    
    def start(self) -> 'SparkSession':
        """启动Spark引擎"""
        self._spark = self._session_manager.get_or_create(self.config)
        self._dual_processor = DualDimensionProcessor(self._spark)
        self._data_store = SparkDataStore(self._spark)
        
        logger.info("SparkEngine已启动")
        return self._spark
    
    def stop(self):
        """停止Spark引擎"""
        self._session_manager.stop()
        self._spark = None
        logger.info("SparkEngine已停止")
    
    @property
    def spark(self) -> 'SparkSession':
        """获取SparkSession"""
        if self._spark is None:
            self.start()
        return self._spark
    
    def load_weibo_data(self, data_dir: str = None) -> 'DataFrame':
        """
        加载微博数据
        
        Args:
            data_dir: 数据目录
            
        Returns:
            微博数据DataFrame
        """
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data'
            )
        
        # 查找所有爬取结果文件
        json_files = []
        for filename in os.listdir(data_dir):
            if filename.startswith('crawl_result_') and filename.endswith('.json'):
                json_files.append(os.path.join(data_dir, filename))
        
        if not json_files:
            logger.warning("未找到微博数据文件")
            return None
        
        # 加载数据
        df = self.spark.read.json(json_files)
        logger.info(f"加载了 {df.count()} 条微博数据")
        
        return df
    
    def analyze_sentiment_distributed(self, df: 'DataFrame') -> 'DataFrame':
        """
        分布式情感分析
        
        Args:
            df: 输入DataFrame
            
        Returns:
            添加情感分析结果的DataFrame
        """
        udf_factory = SentimentUDFFactory(self.spark)
        sentiment_udf = udf_factory.create_sentiment_udf()
        
        result_df = df.withColumn(
            "_sentiment_result", 
            sentiment_udf(F.col("text"))
        )
        result_df = result_df.withColumn("sentiment", F.col("_sentiment_result.sentiment"))
        result_df = result_df.withColumn("sentiment_score", F.col("_sentiment_result.score"))
        result_df = result_df.withColumn("sentiment_confidence", F.col("_sentiment_result.confidence"))
        result_df = result_df.drop("_sentiment_result")
        
        self.stats["jobs_completed"] += 1
        
        return result_df
    
    def rank_dual_dimension(self, df: 'DataFrame', 
                           config: DualDimensionSparkConfig = None) -> 'DataFrame':
        """
        双维度排序
        
        Args:
            df: 输入DataFrame
            config: 双维度配置
            
        Returns:
            排序后的DataFrame
        """
        if config:
            processor = DualDimensionProcessor(self.spark, config)
        else:
            processor = self._dual_processor
        
        result_df = processor.process(df)
        self.stats["jobs_completed"] += 1
        self.stats["total_records_processed"] += result_df.count()
        
        return result_df
    
    def run_full_analysis(self, data_dir: str = None,
                          top_k: int = 100) -> Dict[str, Any]:
        """
        运行完整分析流程
        
        Args:
            data_dir: 数据目录
            top_k: 返回Top-K结果
            
        Returns:
            分析结果
        """
        logger.info("开始运行完整分析流程...")
        
        # 1. 加载数据
        df = self.load_weibo_data(data_dir)
        if df is None:
            return {"error": "未找到数据"}
        
        total_count = df.count()
        logger.info(f"共加载 {total_count} 条数据")
        
        # 2. 双维度分析（包含情感分析）
        result_df = self.rank_dual_dimension(df)
        
        # 3. 获取统计信息
        statistics = self._dual_processor.get_statistics(result_df)
        quadrant_dist = self._dual_processor.get_quadrant_distribution(result_df)
        
        # 4. 获取Top-K结果
        top_df = self._dual_processor.get_top_k(result_df, top_k)
        top_results = [row.asDict() for row in top_df.collect()]
        
        # 5. 保存结果
        save_path = self._data_store.save_dataframe(result_df, "analysis_result")
        
        logger.info("分析流程完成")
        
        return {
            "total_count": total_count,
            "statistics": statistics,
            "quadrant_distribution": quadrant_dist,
            "top_k": top_k,
            "top_results": top_results[:10],  # 只返回前10条详情
            "save_path": save_path,
            "engine_stats": self.stats
        }
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息"""
        return self._session_manager.get_cluster_info()


# ==================== 便捷函数 ====================

_engine_instance = None

def get_spark_engine() -> SparkEngine:
    """获取SparkEngine单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SparkEngine()
        _engine_instance.start()
    return _engine_instance


def run_spark_analysis(data_dir: str = None, top_k: int = 100) -> Dict[str, Any]:
    """运行Spark分析"""
    engine = get_spark_engine()
    return engine.run_full_analysis(data_dir, top_k)


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Spark分析引擎')
    parser.add_argument('--data-dir', '-d', help='数据目录')
    parser.add_argument('--top-k', '-k', type=int, default=100, help='Top-K数量')
    parser.add_argument('--info', action='store_true', help='显示集群信息')
    
    args = parser.parse_args()
    
    if not SPARK_AVAILABLE:
        print("错误: PySpark未安装")
        sys.exit(1)
    
    engine = SparkEngine()
    engine.start()
    
    try:
        if args.info:
            info = engine.get_cluster_info()
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            result = engine.run_full_analysis(args.data_dir, args.top_k)
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    finally:
        engine.stop()

