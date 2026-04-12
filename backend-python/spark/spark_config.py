"""
Spark伪集群配置
用于配置本地Spark环境

配置加载优先级：
  1. 环境变量 / .env 文件 （通过 config.py 统一管理）
  2. 本文件硬编码默认值

伪集群自动检测：
  如果 SPARK_MASTER_URL 指向 spark://host:port，会先尝试连接，
  失败则自动回退到 local[*]。
"""
import os
import sys
import logging
import socket

logger = logging.getLogger(__name__)


def _load_from_config():
    """Try to load config from the centralized config.py"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from config import config
        return config.spark
    except Exception:
        return None


def _is_master_reachable(master_url: str, timeout: float = 2.0) -> bool:
    """
    Check if a Spark master (spark://host:port) is reachable.
    Returns True for local[*] or local[N] masters without checking.
    """
    if not master_url or master_url.startswith('local'):
        return True
    try:
        # Parse spark://host:port
        addr = master_url.replace('spark://', '')
        host, port = addr.split(':')
        port = int(port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _resolve_master(configured_master: str) -> str:
    """
    Resolve Spark master URL with auto-fallback.
    If pseudo-cluster master is unreachable, fall back to local[*].
    """
    if _is_master_reachable(configured_master):
        logger.info(f"Spark master reachable: {configured_master}")
        return configured_master
    else:
        logger.warning(
            f"Spark master {configured_master} unreachable, "
            f"falling back to local[*]"
        )
        return 'local[*]'


# Load centralized config
_cfg = _load_from_config()

_master = _cfg.master_url if _cfg else os.getenv('SPARK_MASTER_URL', 'local[*]')
_app_name = _cfg.app_name if _cfg else os.getenv('SPARK_APP_NAME', 'WeiboSentimentAnalysis')
_driver_mem = _cfg.driver_memory if _cfg else os.getenv('SPARK_DRIVER_MEMORY', '2g')
_executor_mem = _cfg.executor_memory if _cfg else os.getenv('SPARK_EXECUTOR_MEMORY', '2g')
_parallelism = str(_cfg.default_parallelism) if _cfg else os.getenv('SPARK_DEFAULT_PARALLELISM', '4')
_adaptive = str(_cfg.sql_adaptive_enabled).lower() if _cfg else 'true'
_coalesce = str(_cfg.sql_adaptive_coalesce_partitions_enabled).lower() if _cfg else 'true'

# Auto-detect pseudo-cluster availability
_resolved_master = _resolve_master(_master)

SPARK_CONFIG = {
    # Basic
    'spark.app.name': _app_name,
    'spark.master': _resolved_master,
    
    # Memory
    'spark.driver.memory': _driver_mem,
    'spark.executor.memory': _executor_mem,
    
    # Parallelism
    'spark.sql.shuffle.partitions': _parallelism,
    'spark.default.parallelism': _parallelism,
    
    # UI
    'spark.ui.enabled': 'true',
    'spark.ui.port': '4040',
    
    # Logging
    'spark.ui.showConsoleProgress': 'false',
    
    # Serialization
    'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
    
    # Adaptive Query Execution
    'spark.sql.adaptive.enabled': _adaptive,
    'spark.sql.adaptive.coalescePartitions.enabled': _coalesce,
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
