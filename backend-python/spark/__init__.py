# Spark 情感分析模块
"""
Spark分布式处理模块
==================

模块列表：
- DataCleaner: 数据清洗器
- spark_config: Spark配置
- sentiment_analyzer: 情感分析器
- streaming_analyzer: 实时流处理
- spark_pipeline: 处理流水线

使用示例:
    from backend.spark import DataCleaner, get_spark_session
    
    spark = get_spark_session()
    cleaner = DataCleaner(spark)
    cleaned_df = cleaner.clean_weibo_data(raw_df)
    
    # 实时流处理
    from backend.spark import StreamingSentimentAnalyzer
    streaming = StreamingSentimentAnalyzer()
    streaming.start_rate_stream(rows_per_second=10)
"""

from .spark_config import get_spark_session, SPARK_CONFIG, DATA_PATHS
from .data_cleaner import (
    DataCleaner,
    SimHash,
    StopWordsManager,
    create_cleaner,
    quick_clean,
)
from .sentiment_analyzer import (
    SparkSentimentAnalyzer,
    SentimentLexicon,
    SparkClusterManager,
    analyze_weibo_sentiment,
)
from .streaming_analyzer import (
    StreamingSentimentAnalyzer,
    StreamingConfig,
    StreamingStats,
    RealtimeResultHandler,
    MockDataGenerator,
    SocketDataServer,
    get_streaming_analyzer,
    start_realtime_analysis,
)

__all__ = [
    # 配置
    'get_spark_session',
    'SPARK_CONFIG',
    'DATA_PATHS',
    # 数据清洗
    'DataCleaner',
    'SimHash',
    'StopWordsManager',
    'create_cleaner',
    'quick_clean',
    # 批处理情感分析
    'SparkSentimentAnalyzer',
    'SentimentLexicon',
    'SparkClusterManager',
    'analyze_weibo_sentiment',
    # 实时流处理
    'StreamingSentimentAnalyzer',
    'StreamingConfig',
    'StreamingStats',
    'RealtimeResultHandler',
    'MockDataGenerator',
    'SocketDataServer',
    'get_streaming_analyzer',
    'start_realtime_analysis',
]
