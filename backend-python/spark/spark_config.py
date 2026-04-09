"""
Spark伪集群配置
用于配置本地Spark环境
"""
import os

# Spark配置
SPARK_CONFIG = {
    # 基础配置
    'spark.app.name': 'WeiboSentimentAnalysis',
    'spark.master': 'local[*]',  # 本地模式，使用所有CPU核心
    
    # 内存配置
    'spark.driver.memory': '2g',
    'spark.executor.memory': '2g',
    
    # 并行度配置
    'spark.sql.shuffle.partitions': '4',
    'spark.default.parallelism': '4',
    
    # UI配置
    'spark.ui.enabled': 'true',
    'spark.ui.port': '4040',
    
    # 日志配置
    'spark.ui.showConsoleProgress': 'false',
    
    # 序列化配置
    'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
    
    # 其他优化
    'spark.sql.adaptive.enabled': 'true',
    'spark.sql.adaptive.coalescePartitions.enabled': 'true',
}

# 数据路径配置
DATA_PATHS = {
    'raw_data': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'weibo_raw'),
    'processed_data': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'processed'),
    'model_data': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'models'),
    'output_data': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'output'),
}

# 确保目录存在
for path in DATA_PATHS.values():
    os.makedirs(path, exist_ok=True)

# 情感分析配置
SENTIMENT_CONFIG = {
    # 分析模式
    'mode': 'lexicon',  # lexicon: 词典方法, ml: 机器学习方法
    
    # 词典配置
    'lexicon': {
        'positive_threshold': 0.2,
        'negative_threshold': -0.2,
    },
    
    # 批处理配置
    'batch_size': 1000,
    
    # 输出配置
    'output_format': 'json',  # json, parquet, csv
}


def get_spark_session(app_name: str = None, master: str = None):
    """
    获取配置好的SparkSession
    
    Args:
        app_name: 应用名称（可选）
        master: Spark master URL（可选）
        
    Returns:
        SparkSession实例
    """
    try:
        from pyspark.sql import SparkSession
        
        builder = SparkSession.builder
        
        # 应用配置
        for key, value in SPARK_CONFIG.items():
            builder = builder.config(key, value)
            
        # 覆盖配置
        if app_name:
            builder = builder.appName(app_name)
        if master:
            builder = builder.master(master)
            
        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        
        return spark
        
    except ImportError:
        raise RuntimeError("PySpark未安装，请运行: pip install pyspark")
