"""
Spark Streaming 实时情感分析模块
================================

基于 Spark Structured Streaming 实现微博实时情感分析

功能特性：
1. 实时数据流处理 - 支持 Kafka、Socket、文件流等数据源
2. 微批处理 - 可配置批处理间隔
3. 实时情感分析 - 集成混合情感分析模型
4. 实时统计聚合 - 滑动窗口统计
5. 多输出端 - 控制台、文件、数据库、Kafka

使用示例:
    from backend.spark.streaming_analyzer import StreamingSentimentAnalyzer
    
    # 创建流分析器
    analyzer = StreamingSentimentAnalyzer()
    
    # 启动 Socket 流处理
    analyzer.start_socket_stream('localhost', 9999)
    
    # 启动 Kafka 流处理
    analyzer.start_kafka_stream('localhost:9092', 'weibo_topic')
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
from queue import Queue
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('StreamingAnalyzer')

# 尝试导入 PySpark
SPARK_AVAILABLE = False
STREAMING_AVAILABLE = False

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.functions import (
        col, udf, when, lit, count, avg, sum as spark_sum,
        from_json, to_json, struct, window, current_timestamp,
        explode, split, lower, trim, regexp_replace,
        expr, broadcast, coalesce, first, last,
        date_format, hour, minute, dayofweek,
        collect_list, collect_set, approx_count_distinct
    )
    from pyspark.sql.types import (
        StructType, StructField, StringType, IntegerType,
        FloatType, DoubleType, ArrayType, TimestampType,
        BooleanType, LongType, MapType
    )
    SPARK_AVAILABLE = True
    
    try:
        from pyspark.sql.streaming import StreamingQuery
        STREAMING_AVAILABLE = True
    except ImportError:
        pass
        
except ImportError as e:
    logger.warning(f"PySpark 未安装: {e}")


# ==================== 配置类 ====================

@dataclass
class StreamingConfig:
    """流处理配置"""
    # Spark 配置
    app_name: str = "WeiboStreamingSentiment"
    master: str = os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077')
    
    # 内存配置
    driver_memory: str = "2g"
    executor_memory: str = "2g"
    
    # 流处理配置
    trigger_interval: str = "10 seconds"  # 微批处理间隔
    checkpoint_location: str = "./checkpoints/streaming"
    
    # 窗口配置
    window_duration: str = "5 minutes"    # 窗口大小
    slide_duration: str = "1 minute"      # 滑动间隔
    watermark_delay: str = "2 minutes"    # 水印延迟
    
    # Kafka 配置
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "weibo_raw"
    kafka_output_topic: str = "weibo_sentiment"
    kafka_group_id: str = "weibo_sentiment_group"
    
    # 输出配置
    output_mode: str = "append"  # append, complete, update
    output_format: str = "console"  # console, kafka, jdbc, parquet
    
    # 性能配置
    shuffle_partitions: int = 4
    max_offsets_per_trigger: int = 10000
    
    # 数据库配置（可选）
    jdbc_url: str = ""
    jdbc_table: str = "streaming_results"
    jdbc_user: str = ""
    jdbc_password: str = ""


@dataclass
class StreamingStats:
    """流处理统计"""
    start_time: datetime = None
    total_processed: int = 0
    total_positive: int = 0
    total_negative: int = 0
    total_neutral: int = 0
    batches_processed: int = 0
    avg_batch_time_ms: float = 0.0
    current_rate: float = 0.0  # 条/秒
    errors: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'total_processed': self.total_processed,
            'total_positive': self.total_positive,
            'total_negative': self.total_negative,
            'total_neutral': self.total_neutral,
            'batches_processed': self.batches_processed,
            'avg_batch_time_ms': round(self.avg_batch_time_ms, 2),
            'current_rate': round(self.current_rate, 2),
            'errors': self.errors,
            'positive_ratio': round(self.total_positive / max(1, self.total_processed) * 100, 2),
            'negative_ratio': round(self.total_negative / max(1, self.total_processed) * 100, 2),
        }


# ==================== 情感分析 UDF ====================

class SentimentAnalyzerUDF:
    """情感分析 UDF 封装"""
    
    # 简化的情感词典（用于 Spark UDF）
    POSITIVE_WORDS = {
        '好', '棒', '赞', '优秀', '喜欢', '爱', '开心', '高兴', '快乐', '幸福',
        '美好', '精彩', '厉害', '牛', '强', '帅', '美', '漂亮', '可爱', '温暖',
        '感动', '支持', '期待', '希望', '成功', '胜利', '加油', '努力', '进步',
        '满意', '舒服', '惊喜', '感谢', '祝福', '恭喜', '点赞', '推荐', '值得',
        '完美', '出色', '太棒了', '真好', '不错', '很好', '哈哈', '嘻嘻',
        'yyds', '绝绝子', '太可了', '爱了', '冲冲冲', '奥利给',
    }
    
    NEGATIVE_WORDS = {
        '差', '烂', '垃圾', '讨厌', '恨', '愤怒', '生气', '难过', '伤心', '失望',
        '糟糕', '恶心', '无语', '崩溃', '绝望', '痛苦', '悲伤', '郁闷', '烦躁',
        '可怕', '恐怖', '害怕', '担心', '焦虑', '失败', '问题', '错误', '故障',
        '骗', '假', '坑', '黑', '喷', '骂', '太差了', '真烂', '不行', '很差',
        '呵呵', '滚', '傻', '蠢', '破防', '裂开', '麻了', 'emo', '无语子',
    }
    
    NEGATION_WORDS = {'不', '没', '没有', '无', '别', '未', '难以', '不是', '不会', '不能'}
    
    DEGREE_WORDS = {
        '很': 1.5, '非常': 2.0, '特别': 2.0, '极其': 2.5, '超级': 2.0,
        '太': 1.8, '真': 1.5, '好': 1.3, '挺': 1.2, '有点': 0.5, '稍微': 0.5,
    }
    
    @classmethod
    def analyze(cls, text: str) -> Tuple[str, float, float]:
        """
        分析文本情感
        
        Returns:
            (sentiment, score, confidence)
        """
        if not text:
            return ('neutral', 0.0, 0.5)
        
        text = text.lower()
        
        # 检查否定
        has_negation = any(neg in text for neg in cls.NEGATION_WORDS)
        
        # 检查程度词
        degree = 1.0
        for word, deg in cls.DEGREE_WORDS.items():
            if word in text:
                degree = max(degree, deg)
        
        # 计算得分
        pos_count = sum(1 for w in cls.POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in cls.NEGATIVE_WORDS if w in text)
        
        pos_score = pos_count * degree
        neg_score = neg_count * degree
        
        # 否定词反转
        if has_negation:
            pos_score, neg_score = neg_score * 0.8, pos_score * 0.8
        
        # 计算最终得分
        total = pos_score + neg_score
        if total == 0:
            return ('neutral', 0.0, 0.5)
        
        score = (pos_score - neg_score) / max(total, 1)
        score = max(-1.0, min(1.0, score))
        
        # 确定极性和置信度
        if score > 0.2:
            sentiment = 'positive'
            confidence = min(0.5 + abs(score) * 0.5, 1.0)
        elif score < -0.2:
            sentiment = 'negative'
            confidence = min(0.5 + abs(score) * 0.5, 1.0)
        else:
            sentiment = 'neutral'
            confidence = 0.5 + (1 - abs(score)) * 0.3
        
        return (sentiment, round(score, 4), round(confidence, 4))


# ==================== 实时结果处理器 ====================

class RealtimeResultHandler:
    """实时结果处理器"""
    
    def __init__(self, max_buffer: int = 1000):
        self.results_buffer: deque = deque(maxlen=max_buffer)
        self.stats = StreamingStats(start_time=datetime.now())
        self.callbacks: List[Callable] = []
        self._lock = threading.Lock()
    
    def add_callback(self, callback: Callable):
        """添加结果回调"""
        self.callbacks.append(callback)
    
    def process_batch(self, batch_df, batch_id: int):
        """处理一个批次的结果"""
        start_time = time.time()
        
        try:
            # 收集结果
            rows = batch_df.collect()
            
            with self._lock:
                for row in rows:
                    result = row.asDict()
                    self.results_buffer.append(result)
                    
                    # 更新统计
                    self.stats.total_processed += 1
                    sentiment = result.get('sentiment', 'neutral')
                    if sentiment == 'positive':
                        self.stats.total_positive += 1
                    elif sentiment == 'negative':
                        self.stats.total_negative += 1
                    else:
                        self.stats.total_neutral += 1
                
                self.stats.batches_processed += 1
                batch_time = (time.time() - start_time) * 1000
                self.stats.avg_batch_time_ms = (
                    (self.stats.avg_batch_time_ms * (self.stats.batches_processed - 1) + batch_time)
                    / self.stats.batches_processed
                )
                
                # 计算处理速率
                elapsed = (datetime.now() - self.stats.start_time).total_seconds()
                self.stats.current_rate = self.stats.total_processed / max(1, elapsed)
            
            # 触发回调
            for callback in self.callbacks:
                try:
                    callback(rows, batch_id, self.stats)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
                    
        except Exception as e:
            logger.error(f"批次处理失败: {e}")
            with self._lock:
                self.stats.errors += 1
    
    def get_recent_results(self, n: int = 100) -> List[Dict]:
        """获取最近的结果"""
        with self._lock:
            return list(self.results_buffer)[-n:]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return self.stats.to_dict()


# ==================== 主流处理器 ====================

class StreamingSentimentAnalyzer:
    """
    Spark Streaming 实时情感分析器
    
    支持多种数据源和输出端的实时情感分析
    """
    
    def __init__(self, config: StreamingConfig = None):
        """
        初始化流分析器
        
        Args:
            config: 流处理配置
        """
        self.config = config or StreamingConfig()
        self.spark: SparkSession = None
        self.active_queries: Dict[str, Any] = {}
        self.result_handler = RealtimeResultHandler()
        self._running = False
        
        # 初始化 Spark
        if SPARK_AVAILABLE:
            self._init_spark()
        else:
            logger.error("PySpark 未安装，无法使用流处理功能")
    
    def _init_spark(self):
        """初始化 SparkSession"""
        try:
            from .spark_config import _resolve_master
            resolved_master = _resolve_master(self.config.master)
            builder = SparkSession.builder \
                .appName(self.config.app_name) \
                .master(resolved_master) \
                .config("spark.driver.memory", self.config.driver_memory) \
                .config("spark.executor.memory", self.config.executor_memory) \
                .config("spark.sql.shuffle.partitions", str(self.config.shuffle_partitions)) \
                .config("spark.sql.streaming.checkpointLocation", self.config.checkpoint_location) \
                .config("spark.ui.showConsoleProgress", "false")
            
            # Kafka 配置（如果需要）
            # builder = builder.config("spark.jars.packages", 
            #     "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
            
            self.spark = builder.getOrCreate()
            self.spark.sparkContext.setLogLevel("WARN")
            
            logger.info(f"Spark Streaming 初始化成功: {resolved_master}")
            
        except Exception as e:
            logger.error(f"Spark 初始化失败: {e}")
            self.spark = None
    
    def _get_schema(self) -> StructType:
        """获取微博数据 Schema"""
        return StructType([
            StructField("id", StringType(), True),
            StructField("text", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("user_name", StringType(), True),
            StructField("created_at", StringType(), True),
            StructField("reposts_count", IntegerType(), True),
            StructField("comments_count", IntegerType(), True),
            StructField("likes_count", IntegerType(), True),
            StructField("keyword", StringType(), True),
            StructField("source", StringType(), True),
        ])
    
    def _register_udfs(self):
        """注册情感分析 UDF"""
        if not self.spark:
            return
        
        # 情感标签 UDF
        @udf(StringType())
        def sentiment_udf(text):
            return SentimentAnalyzerUDF.analyze(text)[0]
        
        # 情感得分 UDF
        @udf(FloatType())
        def score_udf(text):
            return float(SentimentAnalyzerUDF.analyze(text)[1])
        
        # 置信度 UDF
        @udf(FloatType())
        def confidence_udf(text):
            return float(SentimentAnalyzerUDF.analyze(text)[2])
        
        return sentiment_udf, score_udf, confidence_udf
    
    def _apply_sentiment_analysis(self, df: DataFrame) -> DataFrame:
        """应用情感分析"""
        sentiment_udf, score_udf, confidence_udf = self._register_udfs()
        
        return df \
            .withColumn("sentiment", sentiment_udf(col("text"))) \
            .withColumn("sentiment_score", score_udf(col("text"))) \
            .withColumn("confidence", confidence_udf(col("text"))) \
            .withColumn("processed_at", current_timestamp())
    
    # ==================== Socket 流 ====================
    
    def start_socket_stream(self, host: str = "localhost", port: int = 9999,
                           output_mode: str = None) -> str:
        """
        启动 Socket 流处理
        
        Args:
            host: Socket 主机
            port: Socket 端口
            output_mode: 输出模式
            
        Returns:
            查询ID
        """
        if not self.spark:
            raise RuntimeError("Spark 未初始化")
        
        logger.info(f"启动 Socket 流: {host}:{port}")
        
        # 读取 Socket 流
        lines = self.spark.readStream \
            .format("socket") \
            .option("host", host) \
            .option("port", port) \
            .load()
        
        # 解析 JSON
        schema = self._get_schema()
        df = lines.select(
            from_json(col("value"), schema).alias("data")
        ).select("data.*")
        
        # 应用情感分析
        result_df = self._apply_sentiment_analysis(df)
        
        # 启动查询
        query_id = f"socket_{host}_{port}"
        query = self._start_query(result_df, query_id, output_mode)
        
        return query_id
    
    # ==================== Kafka 流 ====================
    
    def start_kafka_stream(self, bootstrap_servers: str = None,
                          topic: str = None,
                          output_mode: str = None) -> str:
        """
        启动 Kafka 流处理
        
        Args:
            bootstrap_servers: Kafka 服务器地址
            topic: 输入 Topic
            output_mode: 输出模式
            
        Returns:
            查询ID
        """
        if not self.spark:
            raise RuntimeError("Spark 未初始化")
        
        bootstrap_servers = bootstrap_servers or self.config.kafka_bootstrap_servers
        topic = topic or self.config.kafka_topic
        
        logger.info(f"启动 Kafka 流: {bootstrap_servers} / {topic}")
        
        # 读取 Kafka 流
        df = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .option("maxOffsetsPerTrigger", self.config.max_offsets_per_trigger) \
            .load()
        
        # 解析消息
        schema = self._get_schema()
        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data")
        ).select("data.*")
        
        # 应用情感分析
        result_df = self._apply_sentiment_analysis(parsed_df)
        
        # 启动查询
        query_id = f"kafka_{topic}"
        query = self._start_query(result_df, query_id, output_mode)
        
        return query_id
    
    # ==================== 文件流 ====================
    
    def start_file_stream(self, path: str, file_format: str = "json",
                         output_mode: str = None) -> str:
        """
        启动文件流处理
        
        Args:
            path: 监控目录路径
            file_format: 文件格式 (json, csv, parquet)
            output_mode: 输出模式
            
        Returns:
            查询ID
        """
        if not self.spark:
            raise RuntimeError("Spark 未初始化")
        
        logger.info(f"启动文件流: {path} ({file_format})")
        
        schema = self._get_schema()
        
        # 读取文件流
        df = self.spark.readStream \
            .format(file_format) \
            .schema(schema) \
            .option("maxFilesPerTrigger", 10) \
            .load(path)
        
        # 应用情感分析
        result_df = self._apply_sentiment_analysis(df)
        
        # 启动查询
        query_id = f"file_{hashlib.md5(path.encode()).hexdigest()[:8]}"
        query = self._start_query(result_df, query_id, output_mode)
        
        return query_id
    
    # ==================== Rate 流（测试用）====================
    
    def start_rate_stream(self, rows_per_second: int = 10,
                         output_mode: str = None) -> str:
        """
        启动 Rate 流（用于测试）
        
        Args:
            rows_per_second: 每秒生成的行数
            output_mode: 输出模式
            
        Returns:
            查询ID
        """
        if not self.spark:
            raise RuntimeError("Spark 未初始化")
        
        logger.info(f"启动 Rate 流: {rows_per_second} rows/sec")
        
        # 生成测试数据流
        df = self.spark.readStream \
            .format("rate") \
            .option("rowsPerSecond", rows_per_second) \
            .load()
        
        # 模拟微博数据
        test_texts = [
            "这个产品太棒了，非常喜欢！",
            "服务态度很差，再也不来了",
            "今天天气不错，心情很好",
            "真的很失望，完全不值这个价",
            "一般般吧，没什么特别的",
            "哈哈哈太好笑了，笑死我了",
            "无语了，这是什么操作",
            "强烈推荐，值得购买！",
            "yyds！绝绝子！太可了！",
            "破防了，裂开了，麻了",
        ]
        
        # 添加模拟字段
        from pyspark.sql.functions import concat, lit, expr
        
        result_df = df \
            .withColumn("id", concat(lit("weibo_"), col("value").cast("string"))) \
            .withColumn("text", expr(f"element_at(array({','.join([repr(t) for t in test_texts])}), (value % 10) + 1)")) \
            .withColumn("user_id", concat(lit("user_"), (col("value") % 100).cast("string"))) \
            .withColumn("user_name", concat(lit("测试用户"), (col("value") % 100).cast("string"))) \
            .withColumn("keyword", lit("测试"))
        
        # 应用情感分析
        result_df = self._apply_sentiment_analysis(result_df)
        
        # 启动查询
        query_id = "rate_test"
        query = self._start_query(result_df, query_id, output_mode)
        
        return query_id
    
    # ==================== 窗口聚合 ====================
    
    def start_windowed_aggregation(self, source_df: DataFrame,
                                   output_mode: str = "complete") -> str:
        """
        启动窗口聚合统计
        
        Args:
            source_df: 源数据流
            output_mode: 输出模式
            
        Returns:
            查询ID
        """
        if not self.spark:
            raise RuntimeError("Spark 未初始化")
        
        logger.info("启动窗口聚合统计")
        
        # 添加水印和窗口聚合
        windowed_df = source_df \
            .withWatermark("processed_at", self.config.watermark_delay) \
            .groupBy(
                window(col("processed_at"), 
                       self.config.window_duration, 
                       self.config.slide_duration),
                col("keyword")
            ) \
            .agg(
                count("*").alias("total_count"),
                spark_sum(when(col("sentiment") == "positive", 1).otherwise(0)).alias("positive_count"),
                spark_sum(when(col("sentiment") == "negative", 1).otherwise(0)).alias("negative_count"),
                spark_sum(when(col("sentiment") == "neutral", 1).otherwise(0)).alias("neutral_count"),
                avg("sentiment_score").alias("avg_score"),
                avg("confidence").alias("avg_confidence")
            )
        
        # 启动查询
        query_id = "windowed_aggregation"
        query = self._start_query(windowed_df, query_id, output_mode)
        
        return query_id
    
    # ==================== 查询管理 ====================
    
    def _start_query(self, df: DataFrame, query_id: str, 
                     output_mode: str = None) -> Any:
        """启动流查询"""
        output_mode = output_mode or self.config.output_mode
        output_format = self.config.output_format
        
        writer = df.writeStream \
            .queryName(query_id) \
            .outputMode(output_mode) \
            .trigger(processingTime=self.config.trigger_interval)
        
        # 根据输出格式配置
        if output_format == "console":
            query = writer \
                .format("console") \
                .option("truncate", False) \
                .option("numRows", 20) \
                .start()
                
        elif output_format == "memory":
            query = writer \
                .format("memory") \
                .start()
                
        elif output_format == "kafka":
            query = writer \
                .format("kafka") \
                .option("kafka.bootstrap.servers", self.config.kafka_bootstrap_servers) \
                .option("topic", self.config.kafka_output_topic) \
                .option("checkpointLocation", f"{self.config.checkpoint_location}/{query_id}") \
                .start()
                
        elif output_format == "parquet":
            query = writer \
                .format("parquet") \
                .option("path", f"./output/{query_id}") \
                .option("checkpointLocation", f"{self.config.checkpoint_location}/{query_id}") \
                .start()
                
        elif output_format == "foreach":
            # 使用自定义处理器
            query = writer \
                .foreachBatch(self.result_handler.process_batch) \
                .start()
        else:
            # 默认控制台
            query = writer \
                .format("console") \
                .start()
        
        self.active_queries[query_id] = query
        self._running = True
        
        logger.info(f"查询已启动: {query_id} (output={output_format}, mode={output_mode})")
        
        return query
    
    def stop_query(self, query_id: str):
        """停止指定查询"""
        if query_id in self.active_queries:
            self.active_queries[query_id].stop()
            del self.active_queries[query_id]
            logger.info(f"查询已停止: {query_id}")
    
    def stop_all(self):
        """停止所有查询"""
        for query_id in list(self.active_queries.keys()):
            self.stop_query(query_id)
        self._running = False
        logger.info("所有查询已停止")
    
    def await_termination(self, timeout: int = None):
        """等待查询终止"""
        for query in self.active_queries.values():
            query.awaitTermination(timeout)
    
    def get_query_status(self, query_id: str = None) -> Dict:
        """获取查询状态"""
        if query_id:
            if query_id in self.active_queries:
                query = self.active_queries[query_id]
                return {
                    'id': query_id,
                    'is_active': query.isActive,
                    'status': query.status,
                    'recent_progress': query.recentProgress[-1] if query.recentProgress else None
                }
            return {'error': f'查询不存在: {query_id}'}
        
        # 返回所有查询状态
        return {
            qid: {
                'is_active': q.isActive,
                'status': q.status
            }
            for qid, q in self.active_queries.items()
        }
    
    def get_stats(self) -> Dict:
        """获取处理统计"""
        return self.result_handler.get_stats()
    
    def get_recent_results(self, n: int = 100) -> List[Dict]:
        """获取最近的处理结果"""
        return self.result_handler.get_recent_results(n)
    
    def add_result_callback(self, callback: Callable):
        """添加结果回调函数"""
        self.result_handler.add_callback(callback)


# ==================== 数据生成器（从爬虫数据加载）====================

class MockDataGenerator:
    """数据生成器（从爬虫数据加载真实数据）"""
    
    def __init__(self, output_queue: Queue = None):
        self.output_queue = output_queue or Queue()
        self._running = False
        self._thread = None
        self._weibo_data = []
        self._data_index = 0
        self._load_weibo_data()
    
    def _load_weibo_data(self):
        """从爬虫数据目录或演示数据目录加载微博数据"""
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        project_root = os.path.dirname(backend_dir)
        
        # Search paths: crawler data first, then demo data
        search_dirs = [
            os.path.join(backend_dir, 'data'),
            os.path.join(project_root, 'scripts', 'demo_data'),
        ]
        
        for data_dir in search_dirs:
            if not os.path.isdir(data_dir):
                continue
            try:
                for filename in os.listdir(data_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(data_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    self._weibo_data.extend(data)
                        except Exception as e:
                            logger.warning(f"加载文件 {filename} 失败: {e}")
            except Exception as e:
                logger.error(f"加载目录 {data_dir} 失败: {e}")
        
        if self._weibo_data:
            logger.info(f"已加载 {len(self._weibo_data)} 条微博数据用于流式处理")
        else:
            logger.warning("未找到数据，请先执行爬虫采集或 python scripts/generate_demo_data.py")
    
    def generate_one(self) -> Dict:
        """获取一条真实微博数据"""
        import random
        
        if self._weibo_data:
            # 循环使用真实数据
            item = self._weibo_data[self._data_index % len(self._weibo_data)]
            self._data_index += 1
            
            return {
                'id': item.get('id', f"weibo_{int(time.time() * 1000)}"),
                'text': item.get('text', ''),
                'user_id': item.get('user', {}).get('id', ''),
                'user_name': item.get('user', {}).get('screen_name', ''),
                'created_at': item.get('created_at', datetime.now().isoformat()),
                'reposts_count': item.get('reposts_count', 0),
                'comments_count': item.get('comments_count', 0),
                'likes_count': item.get('attitudes_count', 0),
                'keyword': '',
                'source': 'weibo_crawler'
            }
        else:
            # 如果没有爬虫数据，返回空数据提示用户
            return {
                'id': f"empty_{int(time.time() * 1000)}",
                'text': '暂无数据，请先执行微博采集任务',
                'user_id': '',
                'user_name': '系统提示',
                'created_at': datetime.now().isoformat(),
                'reposts_count': 0,
                'comments_count': 0,
                'likes_count': 0,
                'keyword': '',
                'source': 'system'
            }
    
    def start(self, rate: float = 1.0):
        """开始推送数据"""
        self._running = True
        
        def _generate():
            while self._running:
                data = self.generate_one()
                self.output_queue.put(data)
                time.sleep(1.0 / rate)
        
        self._thread = threading.Thread(target=_generate, daemon=True)
        self._thread.start()
        logger.info(f"数据生成器已启动: {rate} 条/秒")
    
    def stop(self):
        """停止推送"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("数据生成器已停止")
    
    def reload_data(self):
        """重新加载爬虫数据"""
        self._weibo_data = []
        self._data_index = 0
        self._load_weibo_data()


# ==================== Socket 服务器（测试用）====================

class SocketDataServer:
    """Socket 数据服务器（用于测试）"""
    
    def __init__(self, host: str = "localhost", port: int = 9999):
        self.host = host
        self.port = port
        self.generator = MockDataGenerator()
        self._running = False
        self._server = None
    
    def start(self, rate: float = 1.0):
        """启动 Socket 服务器"""
        import socket
        
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(5)
        self._running = True
        
        logger.info(f"Socket 服务器已启动: {self.host}:{self.port}")
        
        def _serve():
            while self._running:
                try:
                    self._server.settimeout(1.0)
                    conn, addr = self._server.accept()
                    logger.info(f"客户端连接: {addr}")
                    
                    # 发送数据
                    while self._running:
                        data = self.generator.generate_one()
                        message = json.dumps(data, ensure_ascii=False) + "\n"
                        try:
                            conn.send(message.encode('utf-8'))
                            time.sleep(1.0 / rate)
                        except:
                            break
                    
                    conn.close()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        logger.error(f"Socket 错误: {e}")
        
        self._thread = threading.Thread(target=_serve, daemon=True)
        self._thread.start()
    
    def stop(self):
        """停止服务器"""
        self._running = False
        if self._server:
            self._server.close()
        logger.info("Socket 服务器已停止")


# ==================== 便捷函数 ====================

_streaming_analyzer = None

def get_streaming_analyzer() -> StreamingSentimentAnalyzer:
    """获取流分析器单例"""
    global _streaming_analyzer
    if _streaming_analyzer is None:
        _streaming_analyzer = StreamingSentimentAnalyzer()
    return _streaming_analyzer


def start_realtime_analysis(source: str = "rate", **kwargs) -> str:
    """
    快速启动实时分析
    
    Args:
        source: 数据源类型 (rate, socket, kafka, file)
        **kwargs: 数据源参数
        
    Returns:
        查询ID
    """
    analyzer = get_streaming_analyzer()
    
    if source == "rate":
        return analyzer.start_rate_stream(
            rows_per_second=kwargs.get('rows_per_second', 10)
        )
    elif source == "socket":
        return analyzer.start_socket_stream(
            host=kwargs.get('host', 'localhost'),
            port=kwargs.get('port', 9999)
        )
    elif source == "kafka":
        return analyzer.start_kafka_stream(
            bootstrap_servers=kwargs.get('bootstrap_servers'),
            topic=kwargs.get('topic')
        )
    elif source == "file":
        return analyzer.start_file_stream(
            path=kwargs.get('path'),
            file_format=kwargs.get('format', 'json')
        )
    else:
        raise ValueError(f"不支持的数据源: {source}")


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Spark Streaming 实时情感分析')
    parser.add_argument('--source', type=str, default='rate',
                       choices=['rate', 'socket', 'kafka', 'file'],
                       help='数据源类型')
    parser.add_argument('--host', type=str, default='localhost',
                       help='Socket 主机')
    parser.add_argument('--port', type=int, default=9999,
                       help='Socket 端口')
    parser.add_argument('--kafka-servers', type=str, default='localhost:9092',
                       help='Kafka 服务器')
    parser.add_argument('--kafka-topic', type=str, default='weibo_raw',
                       help='Kafka Topic')
    parser.add_argument('--rate', type=int, default=10,
                       help='Rate 流每秒行数')
    parser.add_argument('--output', type=str, default='console',
                       choices=['console', 'memory', 'kafka', 'parquet', 'foreach'],
                       help='输出格式')
    parser.add_argument('--trigger', type=str, default='10 seconds',
                       help='触发间隔')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Spark Streaming 实时情感分析")
    print("=" * 60)
    
    if not SPARK_AVAILABLE:
        print("❌ PySpark 未安装，请先安装: pip install pyspark")
        sys.exit(1)
    
    # 创建配置
    config = StreamingConfig(
        trigger_interval=args.trigger,
        output_format=args.output
    )
    
    # 创建分析器
    analyzer = StreamingSentimentAnalyzer(config)
    
    # 添加结果回调
    def print_stats(rows, batch_id, stats):
        print(f"\n[Batch {batch_id}] 处理 {len(rows)} 条")
        print(f"  总计: {stats.total_processed} | "
              f"正面: {stats.total_positive} | "
              f"负面: {stats.total_negative} | "
              f"中性: {stats.total_neutral}")
        print(f"  速率: {stats.current_rate:.1f} 条/秒")
    
    if args.output == 'foreach':
        analyzer.add_result_callback(print_stats)
    
    try:
        # 启动流处理
        if args.source == 'rate':
            print(f"\n启动 Rate 测试流: {args.rate} 条/秒")
            query_id = analyzer.start_rate_stream(rows_per_second=args.rate)
            
        elif args.source == 'socket':
            print(f"\n启动 Socket 流: {args.host}:{args.port}")
            print("提示: 请先启动 Socket 数据服务器")
            query_id = analyzer.start_socket_stream(args.host, args.port)
            
        elif args.source == 'kafka':
            print(f"\n启动 Kafka 流: {args.kafka_servers} / {args.kafka_topic}")
            query_id = analyzer.start_kafka_stream(args.kafka_servers, args.kafka_topic)
            
        print(f"\n✅ 流处理已启动: {query_id}")
        print("按 Ctrl+C 停止...")
        
        # 等待终止
        analyzer.await_termination()
        
    except KeyboardInterrupt:
        print("\n\n正在停止...")
        analyzer.stop_all()
        print("✅ 已停止")
        
        # 打印最终统计
        stats = analyzer.get_stats()
        print("\n最终统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
