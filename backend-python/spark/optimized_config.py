"""
优化的Spark分布式配置
======================

针对微博情感分析场景的Spark优化配置

优化策略：
1. 内存管理优化
2. 并行度调优
3. 数据序列化优化
4. Shuffle优化
5. 缓存策略

作者：毕业设计
"""

import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SparkConfig')

try:
    from pyspark import SparkConf
    from pyspark.sql import SparkSession
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False
    logger.warning("PySpark未安装")


@dataclass
class SparkOptimizedConfig:
    """优化的Spark配置"""
    
    # 基础配置
    app_name: str = "WeiboSentimentAnalysis"
    master: str = os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077')
    
    # 内存配置
    driver_memory: str = "4g"
    executor_memory: str = "4g"
    memory_fraction: float = 0.6
    memory_storage_fraction: float = 0.5
    
    # 并行度配置
    shuffle_partitions: int = 200
    default_parallelism: int = 8
    
    # 序列化配置
    serializer: str = "org.apache.spark.serializer.KryoSerializer"
    kryo_buffer_max: str = "512m"
    
    # Shuffle配置
    shuffle_compress: bool = True
    shuffle_spill_compress: bool = True
    
    # 自适应执行
    adaptive_enabled: bool = True
    adaptive_coalesce: bool = True
    adaptive_skew_join: bool = True
    
    # SQL优化
    broadcast_threshold: int = 10485760  # 10MB
    auto_broadcast_join: bool = True
    
    # 缓存配置
    cache_serializer: str = "org.apache.spark.serializer.KryoSerializer"
    
    def to_spark_conf(self) -> Dict[str, str]:
        """转换为Spark配置字典"""
        return {
            # 基础
            "spark.app.name": self.app_name,
            "spark.master": self.master,
            
            # 内存
            "spark.driver.memory": self.driver_memory,
            "spark.executor.memory": self.executor_memory,
            "spark.memory.fraction": str(self.memory_fraction),
            "spark.memory.storageFraction": str(self.memory_storage_fraction),
            
            # 并行度
            "spark.sql.shuffle.partitions": str(self.shuffle_partitions),
            "spark.default.parallelism": str(self.default_parallelism),
            
            # 序列化
            "spark.serializer": self.serializer,
            "spark.kryoserializer.buffer.max": self.kryo_buffer_max,
            
            # Shuffle
            "spark.shuffle.compress": str(self.shuffle_compress).lower(),
            "spark.shuffle.spill.compress": str(self.shuffle_spill_compress).lower(),
            
            # 自适应执行
            "spark.sql.adaptive.enabled": str(self.adaptive_enabled).lower(),
            "spark.sql.adaptive.coalescePartitions.enabled": str(self.adaptive_coalesce).lower(),
            "spark.sql.adaptive.skewJoin.enabled": str(self.adaptive_skew_join).lower(),
            
            # SQL优化
            "spark.sql.autoBroadcastJoinThreshold": str(self.broadcast_threshold),
            
            # 额外优化
            "spark.sql.parquet.compression.codec": "snappy",
            "spark.sql.files.maxPartitionBytes": "134217728",  # 128MB
            "spark.sql.files.openCostInBytes": "4194304",  # 4MB
            "spark.speculation": "false",
            
            # 日志
            "spark.eventLog.enabled": "false",
        }


class SparkSessionFactory:
    """
    Spark会话工厂
    
    单例模式，支持配置热更新
    """
    
    _instance: Optional['SparkSession'] = None
    _config: Optional[SparkOptimizedConfig] = None
    
    @classmethod
    def get_or_create(
        cls, 
        config: SparkOptimizedConfig = None,
        force_new: bool = False
    ) -> 'SparkSession':
        """
        获取或创建SparkSession
        
        Args:
            config: Spark配置
            force_new: 是否强制创建新会话
            
        Returns:
            SparkSession实例
        """
        if not SPARK_AVAILABLE:
            raise RuntimeError("PySpark未安装，请执行: pip install pyspark")
        
        if force_new and cls._instance is not None:
            cls._instance.stop()
            cls._instance = None
        
        if cls._instance is None or cls._instance._jsc is None:
            cls._config = config or SparkOptimizedConfig()
            cls._instance = cls._create_session(cls._config)
        
        return cls._instance
    
    @classmethod
    def _create_session(cls, config: SparkOptimizedConfig) -> 'SparkSession':
        """创建新的SparkSession"""
        conf_dict = config.to_spark_conf()
        
        builder = SparkSession.builder
        for key, value in conf_dict.items():
            builder = builder.config(key, value)
        
        spark = builder.getOrCreate()
        
        # 设置日志级别
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info(f"SparkSession创建成功: {config.app_name}")
        logger.info(f"  Master: {config.master}")
        logger.info(f"  Driver Memory: {config.driver_memory}")
        logger.info(f"  Executor Memory: {config.executor_memory}")
        
        return spark
    
    @classmethod
    def stop(cls):
        """停止SparkSession"""
        if cls._instance is not None:
            cls._instance.stop()
            cls._instance = None
            logger.info("SparkSession已停止")
    
    @classmethod
    def get_config(cls) -> Optional[SparkOptimizedConfig]:
        """获取当前配置"""
        return cls._config


# 配置预设
class ConfigPresets:
    """配置预设"""
    
    @staticmethod
    def development() -> SparkOptimizedConfig:
        """开发环境配置"""
        return SparkOptimizedConfig(
            app_name="WeiboSentiment-Dev",
            master=os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077'),
            driver_memory="2g",
            executor_memory="2g",
            shuffle_partitions=4,
            default_parallelism=4,
        )
    
    @staticmethod
    def production() -> SparkOptimizedConfig:
        """生产环境配置"""
        return SparkOptimizedConfig(
            app_name="WeiboSentiment-Prod",
            master="yarn",
            driver_memory="8g",
            executor_memory="8g",
            shuffle_partitions=200,
            default_parallelism=100,
            memory_fraction=0.7,
        )
    
    @staticmethod
    def pseudo_cluster() -> SparkOptimizedConfig:
        """伪集群配置 — 从 .env 读取 SPARK_MASTER_URL"""
        master = os.getenv('SPARK_MASTER_URL', 'spark://localhost:7077')
        return SparkOptimizedConfig(
            app_name="WeiboSentiment-PseudoCluster",
            master=master,
            driver_memory=os.getenv('SPARK_DRIVER_MEMORY', '4g'),
            executor_memory=os.getenv('SPARK_EXECUTOR_MEMORY', '4g'),
            shuffle_partitions=int(os.getenv('SPARK_SQL_SHUFFLE_PARTITIONS', '200')),
            default_parallelism=int(os.getenv('SPARK_DEFAULT_PARALLELISM', '8')),
            memory_fraction=0.6,
        )

    @staticmethod
    def testing() -> SparkOptimizedConfig:
        """测试环境配置"""
        return SparkOptimizedConfig(
            app_name="WeiboSentiment-Test",
            master="local[2]",
            driver_memory="1g",
            executor_memory="1g",
            shuffle_partitions=2,
            default_parallelism=2,
        )


# 便捷函数
def get_spark_session(
    preset: str = "development",
    custom_config: Dict = None
) -> 'SparkSession':
    """
    获取SparkSession
    
    Args:
        preset: 预设配置 (development/production/testing)
        custom_config: 自定义配置覆盖
        
    Returns:
        SparkSession
    """
    # 获取预设配置
    if preset == "production":
        config = ConfigPresets.production()
    elif preset == "pseudo_cluster":
        config = ConfigPresets.pseudo_cluster()
    elif preset == "testing":
        config = ConfigPresets.testing()
    else:
        config = ConfigPresets.development()
    
    # 应用自定义配置
    if custom_config:
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    return SparkSessionFactory.get_or_create(config)


def stop_spark():
    """停止Spark"""
    SparkSessionFactory.stop()


# 测试
if __name__ == '__main__':
    print("=" * 50)
    print("Spark配置测试")
    print("=" * 50)
    
    # 测试开发配置
    config = ConfigPresets.development()
    print("\n开发环境配置:")
    for key, value in config.to_spark_conf().items():
        print(f"  {key}: {value}")
    
    # 创建会话
    if SPARK_AVAILABLE:
        spark = get_spark_session("development")
        print(f"\nSpark版本: {spark.version}")
        print(f"应用名称: {spark.sparkContext.appName}")
        stop_spark()

