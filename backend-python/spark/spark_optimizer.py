"""
Spark性能优化模块

优化策略：
1. 数据分区策略 - 合理分区减少数据倾斜
2. 广播变量 - 减少shuffle，优化join操作
3. 缓存策略 - persist/cache优化迭代计算
4. 序列化优化 - Kryo序列化提升性能
5. 内存管理 - 合理配置executor资源

作者：毕业设计
日期：2024-12
"""

import os
import sys
import time
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps

# Spark导入
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, FloatType,
        IntegerType, TimestampType, ArrayType, MapType
    )
    from pyspark.sql.window import Window
    from pyspark.broadcast import Broadcast
    from pyspark.storagelevel import StorageLevel
    from pyspark import SparkConf
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 配置类 ====================

@dataclass
class SparkOptimizationConfig:
    """Spark优化配置"""
    
    # 应用配置
    app_name: str = "WeiboSentimentOptimized"
    master: str = "local[*]"
    
    # 内存配置
    driver_memory: str = "2g"
    executor_memory: str = "2g"
    executor_cores: int = 2
    executor_instances: int = 2
    
    # 内存分配比例
    memory_fraction: float = 0.6          # 执行和存储内存占比
    memory_storage_fraction: float = 0.5  # 存储内存在上述中的占比
    
    # 分区配置
    shuffle_partitions: int = 200         # shuffle后的分区数
    default_parallelism: int = 8          # 默认并行度
    max_partition_bytes: str = "128m"     # 单分区最大字节数
    
    # 序列化配置
    serializer: str = "org.apache.spark.serializer.KryoSerializer"
    kryo_buffer_max: str = "512m"
    kryo_registration_required: bool = False
    
    # 广播配置
    broadcast_timeout: int = 300
    auto_broadcast_join_threshold: str = "10m"
    
    # 自适应查询执行(AQE)
    adaptive_enabled: bool = True
    adaptive_coalesce_partitions: bool = True
    adaptive_skew_join: bool = True
    
    # 动态资源分配
    dynamic_allocation_enabled: bool = False
    dynamic_allocation_min_executors: int = 1
    dynamic_allocation_max_executors: int = 10
    
    # 推测执行
    speculation_enabled: bool = False
    speculation_multiplier: float = 1.5
    
    # 压缩
    compress_broadcast: bool = True
    compress_shuffle: bool = True
    
    def to_spark_conf(self) -> Dict[str, str]:
        """转换为Spark配置字典"""
        conf = {
            # 基础配置
            "spark.app.name": self.app_name,
            "spark.master": self.master,
            
            # 内存配置
            "spark.driver.memory": self.driver_memory,
            "spark.executor.memory": self.executor_memory,
            "spark.executor.cores": str(self.executor_cores),
            "spark.executor.instances": str(self.executor_instances),
            "spark.memory.fraction": str(self.memory_fraction),
            "spark.memory.storageFraction": str(self.memory_storage_fraction),
            
            # 分区配置
            "spark.sql.shuffle.partitions": str(self.shuffle_partitions),
            "spark.default.parallelism": str(self.default_parallelism),
            "spark.sql.files.maxPartitionBytes": self.max_partition_bytes,
            
            # 序列化配置
            "spark.serializer": self.serializer,
            "spark.kryoserializer.buffer.max": self.kryo_buffer_max,
            "spark.kryo.registrationRequired": str(self.kryo_registration_required).lower(),
            
            # 广播配置
            "spark.sql.broadcastTimeout": str(self.broadcast_timeout),
            "spark.sql.autoBroadcastJoinThreshold": self.auto_broadcast_join_threshold,
            
            # 自适应查询执行
            "spark.sql.adaptive.enabled": str(self.adaptive_enabled).lower(),
            "spark.sql.adaptive.coalescePartitions.enabled": str(self.adaptive_coalesce_partitions).lower(),
            "spark.sql.adaptive.skewJoin.enabled": str(self.adaptive_skew_join).lower(),
            
            # 压缩
            "spark.broadcast.compress": str(self.compress_broadcast).lower(),
            "spark.shuffle.compress": str(self.compress_shuffle).lower(),
            
            # 其他优化
            "spark.sql.inMemoryColumnarStorage.compressed": "true",
            "spark.sql.inMemoryColumnarStorage.batchSize": "10000",
            "spark.sql.parquet.compression.codec": "snappy",
        }
        
        # 动态资源分配
        if self.dynamic_allocation_enabled:
            conf.update({
                "spark.dynamicAllocation.enabled": "true",
                "spark.dynamicAllocation.minExecutors": str(self.dynamic_allocation_min_executors),
                "spark.dynamicAllocation.maxExecutors": str(self.dynamic_allocation_max_executors),
            })
        
        # 推测执行
        if self.speculation_enabled:
            conf.update({
                "spark.speculation": "true",
                "spark.speculation.multiplier": str(self.speculation_multiplier),
            })
        
        return conf


# ==================== 性能监控 ====================

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: List[Dict] = []
        self.start_time: Optional[float] = None
    
    def start(self, operation: str):
        """开始计时"""
        self.start_time = time.time()
        return self
    
    def stop(self, operation: str, records: int = 0):
        """停止计时并记录"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.metrics.append({
                "operation": operation,
                "duration_seconds": round(elapsed, 3),
                "records": records,
                "throughput": round(records / elapsed, 1) if elapsed > 0 else 0,
                "timestamp": datetime.now().isoformat(),
            })
            self.start_time = None
            return elapsed
        return 0
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics:
            return {}
        
        total_time = sum(m["duration_seconds"] for m in self.metrics)
        total_records = sum(m["records"] for m in self.metrics)
        
        return {
            "total_operations": len(self.metrics),
            "total_time_seconds": round(total_time, 3),
            "total_records": total_records,
            "avg_throughput": round(total_records / total_time, 1) if total_time > 0 else 0,
            "operations": self.metrics,
        }


def timed_operation(operation_name: str):
    """计时装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"[{operation_name}] 耗时: {elapsed:.3f}秒")
            return result
        return wrapper
    return decorator


# ==================== 优化的SparkSession ====================

class OptimizedSparkSession:
    """
    优化的SparkSession管理器
    
    特点：
    1. 单例模式
    2. 自动配置优化参数
    3. 性能监控集成
    """
    
    _instance = None
    _spark = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.config = SparkOptimizationConfig()
        self.monitor = PerformanceMonitor()
    
    def get_or_create(self, config: SparkOptimizationConfig = None) -> 'SparkSession':
        """获取或创建优化的SparkSession"""
        if not SPARK_AVAILABLE:
            raise RuntimeError("PySpark未安装")
        
        if self._spark is None or self._spark._jsc is None:
            config = config or self.config
            spark_conf = config.to_spark_conf()
            
            builder = SparkSession.builder
            for key, value in spark_conf.items():
                builder = builder.config(key, value)
            
            self._spark = builder.getOrCreate()
            self._spark.sparkContext.setLogLevel("WARN")
            
            logger.info(f"SparkSession创建成功: {config.app_name}")
            logger.info(f"配置: driver_memory={config.driver_memory}, "
                       f"executor_memory={config.executor_memory}, "
                       f"shuffle_partitions={config.shuffle_partitions}")
        
        return self._spark
    
    def stop(self):
        """停止SparkSession"""
        if self._spark:
            self._spark.stop()
            self._spark = None


# ==================== 广播变量管理 ====================

class BroadcastManager:
    """
    广播变量管理器
    
    用于管理情感词典、停用词等小数据集的广播
    """
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        self._broadcasts: Dict[str, Broadcast] = {}
    
    def broadcast_dict(self, name: str, data: Dict) -> Broadcast:
        """广播字典数据"""
        if name in self._broadcasts:
            return self._broadcasts[name]
        
        bc = self.spark.sparkContext.broadcast(data)
        self._broadcasts[name] = bc
        logger.info(f"广播变量 [{name}] 创建成功，大小: {sys.getsizeof(data)} bytes")
        return bc
    
    def broadcast_list(self, name: str, data: List) -> Broadcast:
        """广播列表数据"""
        if name in self._broadcasts:
            return self._broadcasts[name]
        
        bc = self.spark.sparkContext.broadcast(data)
        self._broadcasts[name] = bc
        logger.info(f"广播变量 [{name}] 创建成功，元素数: {len(data)}")
        return bc
    
    def get(self, name: str) -> Optional[Broadcast]:
        """获取广播变量"""
        return self._broadcasts.get(name)
    
    def unpersist(self, name: str):
        """释放广播变量"""
        if name in self._broadcasts:
            self._broadcasts[name].unpersist()
            del self._broadcasts[name]
            logger.info(f"广播变量 [{name}] 已释放")
    
    def unpersist_all(self):
        """释放所有广播变量"""
        for name in list(self._broadcasts.keys()):
            self.unpersist(name)


# ==================== 缓存管理 ====================

class CacheManager:
    """
    缓存管理器
    
    管理DataFrame的缓存策略
    """
    
    # 存储级别说明（兼容不同PySpark版本）
    @staticmethod
    def _get_storage_levels():
        levels = {
            "memory_only": StorageLevel.MEMORY_ONLY,
            "memory_and_disk": StorageLevel.MEMORY_AND_DISK,
            "disk_only": StorageLevel.DISK_ONLY,
        }
        # 某些版本可能没有这些属性
        if hasattr(StorageLevel, 'MEMORY_ONLY_SER'):
            levels["memory_only_ser"] = StorageLevel.MEMORY_ONLY_SER
        if hasattr(StorageLevel, 'MEMORY_AND_DISK_SER'):
            levels["memory_and_disk_ser"] = StorageLevel.MEMORY_AND_DISK_SER
        if hasattr(StorageLevel, 'OFF_HEAP'):
            levels["off_heap"] = StorageLevel.OFF_HEAP
        return levels
    
    STORAGE_LEVELS = None  # 延迟初始化
    
    def __init__(self):
        self._cached_dfs: Dict[str, DataFrame] = {}
    
    def cache(self, df: DataFrame, name: str, 
              level: str = "memory_and_disk") -> DataFrame:
        """
        缓存DataFrame
        
        Args:
            df: 要缓存的DataFrame
            name: 缓存名称
            level: 存储级别
        """
        if self.STORAGE_LEVELS is None:
            CacheManager.STORAGE_LEVELS = self._get_storage_levels()
        storage_level = self.STORAGE_LEVELS.get(level, StorageLevel.MEMORY_AND_DISK)
        cached_df = df.persist(storage_level)
        self._cached_dfs[name] = cached_df
        
        # 触发缓存
        count = cached_df.count()
        logger.info(f"DataFrame [{name}] 已缓存，记录数: {count}，级别: {level}")
        
        return cached_df
    
    def unpersist(self, name: str):
        """释放缓存"""
        if name in self._cached_dfs:
            self._cached_dfs[name].unpersist()
            del self._cached_dfs[name]
            logger.info(f"DataFrame [{name}] 缓存已释放")
    
    def unpersist_all(self):
        """释放所有缓存"""
        for name in list(self._cached_dfs.keys()):
            self.unpersist(name)
    
    @staticmethod
    def get_cache_info(spark: SparkSession) -> Dict[str, Any]:
        """获取缓存信息"""
        sc = spark.sparkContext
        
        # 获取存储信息
        storage_info = []
        for rdd_info in sc._jsc.sc().getRDDStorageInfo():
            storage_info.append({
                "name": rdd_info.name(),
                "partitions": rdd_info.numPartitions(),
                "cached_partitions": rdd_info.numCachedPartitions(),
                "memory_size": rdd_info.memSize(),
                "disk_size": rdd_info.diskSize(),
            })
        
        return {
            "cached_rdds": len(storage_info),
            "details": storage_info,
        }


# ==================== 分区优化 ====================

class PartitionOptimizer:
    """
    分区优化器
    
    策略：
    1. 根据数据量自动计算最优分区数
    2. 处理数据倾斜
    3. 合并小分区
    """
    
    # 推荐的每分区记录数
    RECORDS_PER_PARTITION = 100000
    
    # 推荐的每分区大小(MB)
    MB_PER_PARTITION = 128
    
    @staticmethod
    def calculate_optimal_partitions(record_count: int, 
                                     avg_record_size_bytes: int = 1000) -> int:
        """
        计算最优分区数
        
        Args:
            record_count: 记录数
            avg_record_size_bytes: 平均记录大小(字节)
        """
        # 基于记录数计算
        partitions_by_count = max(1, record_count // PartitionOptimizer.RECORDS_PER_PARTITION)
        
        # 基于数据大小计算
        total_size_mb = (record_count * avg_record_size_bytes) / (1024 * 1024)
        partitions_by_size = max(1, int(total_size_mb / PartitionOptimizer.MB_PER_PARTITION))
        
        # 取较大值，但不超过1000
        optimal = min(1000, max(partitions_by_count, partitions_by_size))
        
        logger.info(f"最优分区数计算: 记录数={record_count}, "
                   f"按记录={partitions_by_count}, 按大小={partitions_by_size}, "
                   f"最终={optimal}")
        
        return optimal
    
    @staticmethod
    def repartition_by_key(df: DataFrame, key_column: str, 
                           num_partitions: int = None) -> DataFrame:
        """
        按键重分区
        
        Args:
            df: DataFrame
            key_column: 分区键列
            num_partitions: 分区数
        """
        if num_partitions is None:
            num_partitions = PartitionOptimizer.calculate_optimal_partitions(df.count())
        
        return df.repartition(num_partitions, F.col(key_column))
    
    @staticmethod
    def coalesce_small_partitions(df: DataFrame, 
                                  target_partitions: int = None) -> DataFrame:
        """
        合并小分区
        
        Args:
            df: DataFrame
            target_partitions: 目标分区数
        """
        current_partitions = df.rdd.getNumPartitions()
        
        if target_partitions is None:
            # 自动计算目标分区数
            target_partitions = max(1, current_partitions // 2)
        
        if target_partitions < current_partitions:
            df = df.coalesce(target_partitions)
            logger.info(f"分区合并: {current_partitions} -> {target_partitions}")
        
        return df
    
    @staticmethod
    def handle_data_skew(df: DataFrame, skew_column: str, 
                         salt_buckets: int = 10) -> DataFrame:
        """
        处理数据倾斜（加盐法）
        
        Args:
            df: DataFrame
            skew_column: 倾斜列
            salt_buckets: 盐桶数
        """
        # 添加随机盐值
        df = df.withColumn(
            "_salt",
            (F.rand() * salt_buckets).cast("int")
        )
        
        # 创建复合键
        df = df.withColumn(
            "_salted_key",
            F.concat(F.col(skew_column).cast("string"), F.lit("_"), F.col("_salt"))
        )
        
        logger.info(f"数据倾斜处理: 列={skew_column}, 盐桶数={salt_buckets}")
        
        return df


# ==================== 优化的数据处理器 ====================

class OptimizedDataProcessor:
    """
    优化的数据处理器
    
    集成所有优化策略
    """
    
    def __init__(self, spark: SparkSession = None, 
                 config: SparkOptimizationConfig = None):
        self.config = config or SparkOptimizationConfig()
        
        if spark:
            self.spark = spark
        else:
            session_manager = OptimizedSparkSession()
            self.spark = session_manager.get_or_create(self.config)
        
        self.broadcast_manager = BroadcastManager(self.spark)
        self.cache_manager = CacheManager()
        self.monitor = PerformanceMonitor()
    
    def setup_broadcast_variables(self):
        """设置广播变量"""
        # 广播情感词典
        from .sentiment_analyzer import SentimentLexicon
        
        self.broadcast_manager.broadcast_dict(
            "positive_words",
            dict(SentimentLexicon.POSITIVE_WORDS)
        )
        self.broadcast_manager.broadcast_dict(
            "negative_words", 
            dict(SentimentLexicon.NEGATIVE_WORDS)
        )
        self.broadcast_manager.broadcast_dict(
            "degree_words",
            dict(SentimentLexicon.DEGREE_WORDS)
        )
        self.broadcast_manager.broadcast_list(
            "negation_words",
            list(SentimentLexicon.NEGATION_WORDS)
        )
        
        logger.info("情感词典广播变量设置完成")
    
    @timed_operation("数据清洗")
    def clean_data(self, df: DataFrame, text_column: str = "text") -> DataFrame:
        """
        优化的数据清洗
        
        优化点：
        1. 使用内置函数替代UDF
        2. 链式操作减少中间结果
        3. 提前过滤无效数据
        """
        # 提前过滤空值（减少后续处理量）
        df = df.filter(F.col(text_column).isNotNull())
        df = df.filter(F.length(F.col(text_column)) > 0)
        
        # 使用内置函数进行清洗（比UDF快）
        cleaned_df = df.withColumn(
            "cleaned_text",
            # 去除URL
            F.regexp_replace(F.col(text_column), r"http[s]?://\S+", "")
        ).withColumn(
            "cleaned_text",
            # 去除@用户
            F.regexp_replace(F.col("cleaned_text"), r"@[\w\u4e00-\u9fff]+", "")
        ).withColumn(
            "cleaned_text",
            # 去除话题标签
            F.regexp_replace(F.col("cleaned_text"), r"#[^#]+#", "")
        ).withColumn(
            "cleaned_text",
            # 去除表情
            F.regexp_replace(F.col("cleaned_text"), r"\[[\w\u4e00-\u9fff]+\]", "")
        ).withColumn(
            "cleaned_text",
            # 去除多余空白
            F.regexp_replace(F.col("cleaned_text"), r"\s+", " ")
        ).withColumn(
            "cleaned_text",
            F.trim(F.col("cleaned_text"))
        )
        
        # 过滤清洗后的空文本
        cleaned_df = cleaned_df.filter(F.length(F.col("cleaned_text")) > 0)
        
        # 添加文本哈希用于去重
        cleaned_df = cleaned_df.withColumn(
            "text_hash",
            F.md5(F.col("cleaned_text"))
        )
        
        # 去重
        cleaned_df = cleaned_df.dropDuplicates(["text_hash"])
        
        return cleaned_df
    
    @timed_operation("特征提取")
    def extract_features(self, df: DataFrame, 
                         text_column: str = "cleaned_text") -> DataFrame:
        """
        优化的特征提取
        
        优化点：
        1. 使用广播变量
        2. 批量处理
        3. 向量化操作
        """
        # 获取广播变量
        positive_bc = self.broadcast_manager.get("positive_words")
        negative_bc = self.broadcast_manager.get("negative_words")
        
        if positive_bc is None:
            self.setup_broadcast_variables()
            positive_bc = self.broadcast_manager.get("positive_words")
            negative_bc = self.broadcast_manager.get("negative_words")
        
        # 使用广播变量的UDF
        @F.udf(FloatType())
        def sentiment_score_udf(text):
            if not text:
                return 0.0
            
            positive_words = positive_bc.value
            negative_words = negative_bc.value
            
            score = 0.0
            for word, weight in positive_words.items():
                if word in text:
                    score += weight
            for word, weight in negative_words.items():
                if word in text:
                    score += weight
            
            return float(max(-1.0, min(1.0, score / 3.0)))
        
        # 计算特征
        df = df.withColumn("sentiment_score", sentiment_score_udf(F.col(text_column)))
        
        # 文本长度特征
        df = df.withColumn("text_length", F.length(F.col(text_column)))
        
        # 词数特征（简单按空格分割）
        df = df.withColumn("word_count", F.size(F.split(F.col(text_column), r"\s+")))
        
        return df
    
    @timed_operation("情感分析")
    def analyze_sentiment(self, df: DataFrame) -> DataFrame:
        """
        优化的情感分析
        
        优化点：
        1. 使用广播变量
        2. 批量处理
        3. 避免Python UDF（尽量用内置函数）
        """
        # 情感分类
        df = df.withColumn(
            "sentiment",
            F.when(F.col("sentiment_score") > 0.2, "positive")
            .when(F.col("sentiment_score") < -0.2, "negative")
            .otherwise("neutral")
        )
        
        # 情感强度
        df = df.withColumn(
            "sentiment_intensity",
            F.abs(F.col("sentiment_score")) * 100
        )
        
        return df
    
    def process_pipeline(self, df: DataFrame, 
                         cache_intermediate: bool = True) -> DataFrame:
        """
        完整处理流水线
        
        Args:
            df: 输入DataFrame
            cache_intermediate: 是否缓存中间结果
        """
        self.monitor.start("total")
        
        # 1. 数据清洗
        self.monitor.start("clean")
        df = self.clean_data(df)
        if cache_intermediate:
            df = self.cache_manager.cache(df, "cleaned_data", "memory_and_disk")
        clean_count = df.count()
        self.monitor.stop("clean", clean_count)
        
        # 2. 特征提取
        self.monitor.start("feature")
        df = self.extract_features(df)
        self.monitor.stop("feature", clean_count)
        
        # 3. 情感分析
        self.monitor.start("sentiment")
        df = self.analyze_sentiment(df)
        self.monitor.stop("sentiment", clean_count)
        
        self.monitor.stop("total", clean_count)
        
        return df
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "metrics": self.monitor.get_summary(),
            "cache_info": CacheManager.get_cache_info(self.spark),
            "spark_config": self.config.to_spark_conf(),
        }
    
    def cleanup(self):
        """清理资源"""
        self.broadcast_manager.unpersist_all()
        self.cache_manager.unpersist_all()


# ==================== Spark提交配置生成器 ====================

class SparkSubmitConfigGenerator:
    """
    spark-submit配置生成器
    """
    
    @staticmethod
    def generate_local_config(config: SparkOptimizationConfig = None) -> str:
        """生成本地模式配置"""
        config = config or SparkOptimizationConfig()
        
        cmd = f"""spark-submit \\
    --master local[*] \\
    --driver-memory {config.driver_memory} \\
    --conf spark.serializer={config.serializer} \\
    --conf spark.kryoserializer.buffer.max={config.kryo_buffer_max} \\
    --conf spark.sql.shuffle.partitions={config.shuffle_partitions} \\
    --conf spark.sql.adaptive.enabled={str(config.adaptive_enabled).lower()} \\
    --conf spark.sql.adaptive.coalescePartitions.enabled=true \\
    --conf spark.sql.adaptive.skewJoin.enabled=true \\
    --conf spark.memory.fraction={config.memory_fraction} \\
    --conf spark.memory.storageFraction={config.memory_storage_fraction} \\
    your_script.py"""
        
        return cmd
    
    @staticmethod
    def generate_cluster_config(config: SparkOptimizationConfig = None) -> str:
        """生成集群模式配置"""
        config = config or SparkOptimizationConfig()
        
        cmd = f"""spark-submit \\
    --master yarn \\
    --deploy-mode cluster \\
    --driver-memory {config.driver_memory} \\
    --executor-memory {config.executor_memory} \\
    --executor-cores {config.executor_cores} \\
    --num-executors {config.executor_instances} \\
    --conf spark.serializer={config.serializer} \\
    --conf spark.kryoserializer.buffer.max={config.kryo_buffer_max} \\
    --conf spark.sql.shuffle.partitions={config.shuffle_partitions} \\
    --conf spark.sql.adaptive.enabled={str(config.adaptive_enabled).lower()} \\
    --conf spark.sql.adaptive.coalescePartitions.enabled=true \\
    --conf spark.sql.adaptive.skewJoin.enabled=true \\
    --conf spark.dynamicAllocation.enabled={str(config.dynamic_allocation_enabled).lower()} \\
    --conf spark.dynamicAllocation.minExecutors={config.dynamic_allocation_min_executors} \\
    --conf spark.dynamicAllocation.maxExecutors={config.dynamic_allocation_max_executors} \\
    --conf spark.memory.fraction={config.memory_fraction} \\
    --conf spark.memory.storageFraction={config.memory_storage_fraction} \\
    --conf spark.shuffle.compress=true \\
    --conf spark.broadcast.compress=true \\
    your_script.py"""
        
        return cmd
    
    @staticmethod
    def generate_config_file(config: SparkOptimizationConfig = None,
                             output_path: str = "spark-defaults.conf") -> str:
        """生成配置文件"""
        config = config or SparkOptimizationConfig()
        spark_conf = config.to_spark_conf()
        
        lines = ["# Spark优化配置文件", f"# 生成时间: {datetime.now().isoformat()}", ""]
        
        for key, value in spark_conf.items():
            lines.append(f"{key}={value}")
        
        content = "\n".join(lines)
        
        with open(output_path, "w") as f:
            f.write(content)
        
        logger.info(f"配置文件已生成: {output_path}")
        return content


# ==================== 性能测试 ====================

class PerformanceTester:
    """
    性能测试器
    """
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
    
    def generate_test_data(self, num_records: int = 10000) -> DataFrame:
        """生成测试数据"""
        import random
        
        data = []
        sentiments = ["好评", "差评", "一般"]
        
        for i in range(num_records):
            sentiment = random.choice(sentiments)
            text = f"这是第{i}条测试微博，{sentiment}！" + "测试内容" * random.randint(1, 10)
            data.append({
                "id": str(i),
                "text": text,
                "reposts_count": random.randint(0, 10000),
                "comments_count": random.randint(0, 5000),
                "attitudes_count": random.randint(0, 20000),
            })
        
        return self.spark.createDataFrame(data)
    
    def run_benchmark(self, num_records: int = 10000) -> Dict[str, Any]:
        """运行基准测试"""
        logger.info(f"开始性能测试，数据量: {num_records}")
        
        results = {
            "num_records": num_records,
            "tests": [],
        }
        
        # 生成测试数据
        start = time.time()
        df = self.generate_test_data(num_records)
        df = df.cache()
        df.count()  # 触发缓存
        data_gen_time = time.time() - start
        results["data_generation_time"] = round(data_gen_time, 3)
        
        # 创建处理器
        processor = OptimizedDataProcessor(self.spark)
        processor.setup_broadcast_variables()
        
        # 测试数据清洗
        start = time.time()
        cleaned_df = processor.clean_data(df)
        cleaned_df.count()
        clean_time = time.time() - start
        results["tests"].append({
            "name": "数据清洗",
            "time_seconds": round(clean_time, 3),
            "throughput": round(num_records / clean_time, 1),
        })
        
        # 测试特征提取
        start = time.time()
        feature_df = processor.extract_features(cleaned_df)
        feature_df.count()
        feature_time = time.time() - start
        results["tests"].append({
            "name": "特征提取",
            "time_seconds": round(feature_time, 3),
            "throughput": round(num_records / feature_time, 1),
        })
        
        # 测试情感分析
        start = time.time()
        sentiment_df = processor.analyze_sentiment(feature_df)
        sentiment_df.count()
        sentiment_time = time.time() - start
        results["tests"].append({
            "name": "情感分析",
            "time_seconds": round(sentiment_time, 3),
            "throughput": round(num_records / sentiment_time, 1),
        })
        
        # 总时间
        total_time = clean_time + feature_time + sentiment_time
        results["total_time_seconds"] = round(total_time, 3)
        results["total_throughput"] = round(num_records / total_time, 1)
        
        # 清理
        processor.cleanup()
        df.unpersist()
        
        return results


# ==================== 便捷函数 ====================

def create_optimized_spark(config: SparkOptimizationConfig = None) -> SparkSession:
    """创建优化的SparkSession"""
    manager = OptimizedSparkSession()
    return manager.get_or_create(config)


def get_spark_ui_metrics(spark: SparkSession) -> Dict[str, Any]:
    """
    获取Spark UI监控指标
    
    注意：需要Spark UI运行在4040端口
    """
    import requests
    
    try:
        # 获取应用信息
        app_response = requests.get("http://localhost:4040/api/v1/applications", timeout=5)
        apps = app_response.json()
        
        if not apps:
            return {"error": "No applications found"}
        
        app_id = apps[0]["id"]
        
        # 获取作业信息
        jobs_response = requests.get(f"http://localhost:4040/api/v1/applications/{app_id}/jobs", timeout=5)
        jobs = jobs_response.json()
        
        # 获取阶段信息
        stages_response = requests.get(f"http://localhost:4040/api/v1/applications/{app_id}/stages", timeout=5)
        stages = stages_response.json()
        
        # 获取执行器信息
        executors_response = requests.get(f"http://localhost:4040/api/v1/applications/{app_id}/executors", timeout=5)
        executors = executors_response.json()
        
        return {
            "app_id": app_id,
            "jobs_count": len(jobs),
            "stages_count": len(stages),
            "executors_count": len(executors),
            "completed_jobs": sum(1 for j in jobs if j.get("status") == "SUCCEEDED"),
            "failed_jobs": sum(1 for j in jobs if j.get("status") == "FAILED"),
            "total_input_bytes": sum(e.get("totalInputBytes", 0) for e in executors),
            "total_shuffle_read": sum(e.get("totalShuffleRead", 0) for e in executors),
            "total_shuffle_write": sum(e.get("totalShuffleWrite", 0) for e in executors),
        }
    except Exception as e:
        return {"error": str(e), "message": "请确保Spark UI运行在localhost:4040"}


# ==================== 主函数 ====================

if __name__ == "__main__":
    print("=" * 70)
    print("Spark性能优化模块测试")
    print("=" * 70)
    
    # 1. 生成配置
    print("\n1. spark-submit配置:")
    print("-" * 50)
    config = SparkOptimizationConfig(
        driver_memory="4g",
        executor_memory="4g",
        executor_cores=4,
        shuffle_partitions=100,
    )
    print(SparkSubmitConfigGenerator.generate_local_config(config))
    
    # 2. 创建优化的SparkSession
    print("\n2. 创建优化的SparkSession:")
    print("-" * 50)
    spark = create_optimized_spark(config)
    
    # 3. 运行性能测试
    print("\n3. 运行性能测试:")
    print("-" * 50)
    tester = PerformanceTester(spark)
    results = tester.run_benchmark(num_records=5000)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # 4. 获取Spark UI指标
    print("\n4. Spark UI指标:")
    print("-" * 50)
    metrics = get_spark_ui_metrics(spark)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    
    # 5. 清理
    spark.stop()
    print("\n测试完成！")
