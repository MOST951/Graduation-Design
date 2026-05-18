"""
Spark分布式舆情分析流水线

技术特点：
1. 完整的ETL流水线设计
2. 支持批处理和流处理两种模式
3. 数据质量检查和异常处理
4. 性能监控和优化

流水线阶段：
1. Extract: 数据抽取（从文件/数据库/API）
2. Transform: 数据转换（清洗、分词、特征提取、情感分析）
3. Load: 数据加载（存储结果、更新索引）

作者：毕业设计
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# Spark导入
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, FloatType, 
        IntegerType, TimestampType, ArrayType, MapType
    )
    from pyspark.sql.window import Window
    from pyspark.ml.feature import HashingTF, IDF, Tokenizer, StopWordsRemover
    from pyspark.ml import Pipeline
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False
    logging.warning("PySpark未安装")

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """流水线阶段"""
    EXTRACT = "extract"
    CLEAN = "clean"
    TOKENIZE = "tokenize"
    FEATURE = "feature"
    SENTIMENT = "sentiment"
    RANK = "rank"
    LOAD = "load"


@dataclass
class PipelineConfig:
    """流水线配置"""
    # Spark配置
    app_name: str = "WeiboSentimentPipeline"
    master: str = os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077')
    driver_memory: str = "2g"
    executor_memory: str = "2g"
    shuffle_partitions: int = 4
    
    # 数据路径
    input_path: str = ""
    output_path: str = ""
    checkpoint_path: str = ""
    
    # 处理配置
    batch_size: int = 1000
    enable_cache: bool = True
    enable_checkpoint: bool = False
    
    # 特征配置
    num_features: int = 10000
    min_doc_freq: int = 2


@dataclass
class PipelineMetrics:
    """流水线指标"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    stage_times: Dict[str, float] = field(default_factory=dict)
    
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds(),
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "failed_records": self.failed_records,
            "success_rate": self.processed_records / max(1, self.total_records),
            "stage_times": self.stage_times,
        }


class SparkSessionManager:
    """
    Spark会话管理器
    
    单例模式，确保全局只有一个SparkSession
    """
    _instance = None
    _spark = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_or_create(self, config: PipelineConfig = None) -> 'SparkSession':
        """获取或创建SparkSession"""
        if not SPARK_AVAILABLE:
            raise RuntimeError("PySpark未安装")
        
        if self._spark is None or self._spark._jsc is None:
            config = config or PipelineConfig()
            
            builder = SparkSession.builder \
                .appName(config.app_name) \
                .master(config.master) \
                .config("spark.driver.memory", config.driver_memory) \
                .config("spark.executor.memory", config.executor_memory) \
                .config("spark.sql.shuffle.partitions", str(config.shuffle_partitions)) \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            
            if config.checkpoint_path:
                builder = builder.config("spark.sql.streaming.checkpointLocation", config.checkpoint_path)
            
            self._spark = builder.getOrCreate()
            
            # 设置日志级别
            self._spark.sparkContext.setLogLevel("WARN")
            
            logger.info(f"SparkSession创建成功: {config.app_name}")
        
        return self._spark
    
    def stop(self):
        """停止SparkSession"""
        if self._spark:
            self._spark.stop()
            self._spark = None
            logger.info("SparkSession已停止")


class DataCleaner:
    """
    数据清洗器
    
    功能：
    1. 去除HTML标签
    2. 去除特殊字符、URL、@用户
    3. 表情符号→文字描述（保留情感特征）
    4. 繁体→简体转换
    5. 全角→半角转换
    6. 去除重复数据
    """
    
    # 微博表情→文字映射（内联以便在Spark UDF中序列化）
    _EMOJI_MAP = {
        '[笑cry]': '笑哭', '[哈哈]': '大笑', '[嘻嘻]': '嘻嘻笑',
        '[偷笑]': '偷笑', '[太开心]': '非常开心', '[开心]': '开心',
        '[赞]': '点赞', '[good]': '点赞', '[鼓掌]': '鼓掌',
        '[心]': '喜爱', '[爱你]': '爱你', '[给力]': '给力',
        '[怒]': '愤怒', '[生气]': '生气', '[悲伤]': '悲伤',
        '[泪]': '流泪', '[失望]': '失望', '[委屈]': '委屈',
        '[可怜]': '可怜', '[黑线]': '无语', '[汗]': '尴尬',
        '[思考]': '思考', '[疑问]': '疑问', '[吃惊]': '吃惊',
        '[doge]': '滑稽', '[允悲]': '苦笑', '[微笑]': '微笑',
        '[摊手]': '无奈', '[加油]': '加油', '[吃瓜]': '吃瓜围观',
        '[裂开]': '裂开崩溃', '[酸]': '酸了羡慕',
    }

    # 高频繁简映射
    _T2S_MAP = {
        '國': '国', '東': '东', '車': '车', '學': '学', '開': '开',
        '長': '长', '門': '门', '時': '时', '萬': '万', '電': '电',
        '書': '书', '見': '见', '飛': '飞', '機': '机', '數': '数',
        '點': '点', '問': '问', '頭': '头', '風': '风', '動': '动',
        '對': '对', '說': '说', '話': '话', '買': '买', '賣': '卖',
        '寫': '写', '讓': '让', '認': '认', '識': '识', '義': '义',
        '經': '经', '過': '过', '從': '从', '進': '进', '遠': '远',
        '運': '运', '關': '关', '連': '连', '邊': '边', '還': '还',
        '這': '这', '裡': '里', '後': '后', '樂': '乐', '覺': '觉',
        '發': '发', '現': '现', '報': '报', '廣': '广', '熱': '热',
        '愛': '爱', '個': '个', '優': '优', '網': '网', '傳': '传',
        '體': '体', '統': '统', '雙': '双', '離': '离', '難': '难',
    }

    # 表情极性分类，用于 'tag' 模式
    _POS_EMOJIS = {
        '[笑cry]', '[哈哈]', '[嘻嘻]', '[偷笑]', '[太开心]', '[开心]',
        '[赞]', '[good]', '[鼓掌]', '[心]', '[爱你]', '[给力]', '[加油]',
    }
    _NEG_EMOJIS = {
        '[怒]', '[生气]', '[悲伤]', '[泪]', '[失望]', '[委屈]',
        '[可怜]', '[黑线]', '[汗]', '[裂开]',
    }

    @staticmethod
    def clean_text_udf(emoji_mode: str = 'text'):
        """
        创建文本清洗UDF

        Args:
            emoji_mode: 表情处理模式
                - 'text': 替换为情感文字描述（默认，与旧版行为一致）
                - 'tag':  替换为极性标签 _EMO_POS_ / _EMO_NEG_ / _EMO_NEU_，
                          避免将描述性文字注入正文造成情感强度失真
                - 'remove': 直接删除所有 [表情]
                - 'keep': 保留原始 [表情] 不做任何处理
        """
        import re
        emoji_map = DataCleaner._EMOJI_MAP
        pos_emojis = DataCleaner._POS_EMOJIS
        neg_emojis = DataCleaner._NEG_EMOJIS
        t2s_map = DataCleaner._T2S_MAP
        _emoji_mode = emoji_mode
        
        def clean_text(text: str) -> str:
            if not text:
                return ""
            
            # 去除HTML标签
            text = re.sub(r'<[^>]+>', '', text)
            
            # 去除URL
            text = re.sub(r'http[s]?://\S+', '', text)
            
            # 去除@用户
            text = re.sub(r'@[\w\u4e00-\u9fff]+', '', text)
            
            # 去除话题标签但保留内容
            text = re.sub(r'#([^#]+)#', r'\1', text)
            
            # 表情符号处理（根据 emoji_mode 选择策略）
            if _emoji_mode == 'remove':
                text = re.sub(r'\[[\w\u4e00-\u9fff]+\]', '', text)
            elif _emoji_mode == 'tag':
                def _tag_emoji(m):
                    e = m.group(0)
                    if e in pos_emojis:
                        return '_EMO_POS_'
                    elif e in neg_emojis:
                        return '_EMO_NEG_'
                    elif e in emoji_map:
                        return '_EMO_NEU_'
                    return e
                text = re.sub(r'\[[\w\u4e00-\u9fff]+\]', _tag_emoji, text)
            elif _emoji_mode == 'keep':
                pass  # 保留原始表情
            else:
                # 默认 'text' 模式：替换为中文描述
                def _replace_emoji(m):
                    return emoji_map.get(m.group(0), m.group(0))
                text = re.sub(r'\[[\w\u4e00-\u9fff]+\]', _replace_emoji, text)
            
            # 繁体→简体
            text = ''.join(t2s_map.get(c, c) for c in text)
            
            # 全角→半角
            chars = []
            for ch in text:
                code = ord(ch)
                if code == 0x3000:
                    chars.append(' ')
                elif 0xFF01 <= code <= 0xFF5E:
                    chars.append(chr(code - 0xFEE0))
                else:
                    chars.append(ch)
            text = ''.join(chars)
            
            # 去除多余空白
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        
        return F.udf(clean_text, StringType())
    
    @staticmethod
    def clean_dataframe(df: 'DataFrame', text_column: str = "text") -> 'DataFrame':
        """清洗DataFrame"""
        clean_udf = DataCleaner.clean_text_udf()
        
        # 添加清洗后的文本列
        df = df.withColumn("cleaned_text", clean_udf(F.col(text_column)))
        
        # 过滤空文本
        df = df.filter(F.length(F.col("cleaned_text")) > 0)
        
        # 去重（基于文本内容的MD5哈希）
        df = df.withColumn(
            "text_hash",
            F.md5(F.col("cleaned_text"))
        ).dropDuplicates(["text_hash"])
        
        return df


class ChineseTokenizer:
    """
    中文分词器
    
    使用jieba进行中文分词，支持：
    1. 精确模式分词
    2. 自定义词典
    3. 停用词过滤
    """
    
    # 停用词列表
    STOP_WORDS = set([
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '什么', '他', '她', '它', '们', '这个', '那个', '哪', '为',
        '吗', '呢', '吧', '啊', '哦', '嗯', '呀', '哈', '嘿', '喂', '哎', '唉',
    ])
    
    @staticmethod
    def tokenize_udf():
        """创建分词UDF"""
        try:
            import jieba
            jieba.setLogLevel(logging.WARNING)
        except ImportError:
            logger.warning("jieba未安装，使用简单分词")
            jieba = None
        
        stop_words = ChineseTokenizer.STOP_WORDS
        
        def tokenize(text: str) -> List[str]:
            if not text:
                return []
            
            if jieba:
                words = jieba.lcut(text)
            else:
                # 简单按字符分割
                words = list(text)
            
            # 过滤停用词和单字符
            words = [w for w in words if len(w) > 1 and w not in stop_words]
            
            return words
        
        return F.udf(tokenize, ArrayType(StringType()))
    
    @staticmethod
    def tokenize_dataframe(df: 'DataFrame', 
                           text_column: str = "cleaned_text") -> 'DataFrame':
        """对DataFrame进行分词"""
        tokenize_udf = ChineseTokenizer.tokenize_udf()
        
        df = df.withColumn("tokens", tokenize_udf(F.col(text_column)))
        df = df.withColumn("token_count", F.size(F.col("tokens")))
        
        return df


class FeatureExtractor:
    """
    特征提取器
    
    支持多种特征提取方法：
    1. TF-IDF
    2. 词频统计
    3. 关键词提取

    注：TF-IDF 和词频统计特征主要用于 Spark MLlib 辅助分析场景，
    如热点话题挖掘、关键词排名和词云生成等，不直接作为 ChineseBERT
    情感分析模型的输入。ChineseBERT 使用其内置 tokenizer 和
    embedding 层，无需外部 TF-IDF/Word2Vec 特征。
    """
    
    @staticmethod
    def extract_tfidf(df: 'DataFrame', 
                      tokens_column: str = "tokens",
                      num_features: int = 10000) -> 'DataFrame':
        """提取TF-IDF特征"""
        # 将tokens数组转为字符串（Spark ML需要）
        df = df.withColumn(
            "tokens_str",
            F.concat_ws(" ", F.col(tokens_column))
        )
        
        # 使用Spark ML的TF-IDF
        tokenizer = Tokenizer(inputCol="tokens_str", outputCol="words")
        hashingTF = HashingTF(inputCol="words", outputCol="raw_features", numFeatures=num_features)
        idf = IDF(inputCol="raw_features", outputCol="tfidf_features")
        
        pipeline = Pipeline(stages=[tokenizer, hashingTF, idf])
        model = pipeline.fit(df)
        df = model.transform(df)
        
        return df
    
    @staticmethod
    def extract_keywords(df: 'DataFrame',
                         tokens_column: str = "tokens",
                         top_k: int = 5) -> 'DataFrame':
        """提取关键词（基于词频）"""
        # 展开tokens并统计词频
        words_df = df.select(
            F.explode(F.col(tokens_column)).alias("word")
        ).groupBy("word").count().orderBy(F.desc("count"))
        
        # 获取高频词作为关键词
        top_words = [row.word for row in words_df.limit(100).collect()]
        top_words_broadcast = set(top_words)
        
        def extract_top_keywords(tokens: List[str]) -> List[str]:
            if not tokens:
                return []
            # 保留高频词
            keywords = [t for t in tokens if t in top_words_broadcast]
            # 按出现顺序返回前k个
            seen = set()
            result = []
            for kw in keywords:
                if kw not in seen:
                    seen.add(kw)
                    result.append(kw)
                    if len(result) >= top_k:
                        break
            return result
        
        extract_udf = F.udf(extract_top_keywords, ArrayType(StringType()))
        df = df.withColumn("keywords", extract_udf(F.col(tokens_column)))
        
        return df


class SentimentProcessor:
    """
    情感处理器
    
    集成多种情感分析方法
    """
    
    @staticmethod
    def analyze_sentiment_udf():
        """创建情感分析UDF"""
        from .sentiment_analyzer import SentimentLexicon
        
        def analyze(text: str) -> Dict[str, Any]:
            if not text:
                return {"sentiment": "neutral", "score": 0.0}
            
            sentiment, score = SentimentLexicon.analyze(text)
            return {"sentiment": sentiment, "score": float(score)}
        
        schema = StructType([
            StructField("sentiment", StringType(), True),
            StructField("score", FloatType(), True)
        ])
        
        return F.udf(analyze, schema)
    
    @staticmethod
    def process_sentiment(df: 'DataFrame',
                          text_column: str = "cleaned_text") -> 'DataFrame':
        """处理情感分析"""
        sentiment_udf = SentimentProcessor.analyze_sentiment_udf()
        
        df = df.withColumn("sentiment_result", sentiment_udf(F.col(text_column)))
        df = df.withColumn("sentiment", F.col("sentiment_result.sentiment"))
        df = df.withColumn("sentiment_score", F.col("sentiment_result.score"))
        df = df.drop("sentiment_result")
        
        return df


class SentimentPipeline:
    """
    完整的舆情分析流水线
    
    整合所有处理阶段
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.session_manager = SparkSessionManager()
        self.metrics = PipelineMetrics()
        self._spark = None
    
    def get_spark(self) -> 'SparkSession':
        """获取SparkSession"""
        if self._spark is None:
            self._spark = self.session_manager.get_or_create(self.config)
        return self._spark
    
    def _log_stage(self, stage: PipelineStage, start_time: float):
        """记录阶段耗时"""
        elapsed = time.time() - start_time
        self.metrics.stage_times[stage.value] = elapsed
        logger.info(f"阶段 [{stage.value}] 完成，耗时: {elapsed:.2f}秒")
    
    def run(self, input_data: Any, 
            stages: List[PipelineStage] = None) -> 'DataFrame':
        """
        运行流水线
        
        Args:
            input_data: 输入数据（DataFrame/路径/列表）
            stages: 要执行的阶段列表
            
        Returns:
            处理后的DataFrame
        """
        if stages is None:
            stages = [
                PipelineStage.CLEAN,
                PipelineStage.TOKENIZE,
                PipelineStage.FEATURE,
                PipelineStage.SENTIMENT,
                PipelineStage.RANK,
            ]
        
        self.metrics = PipelineMetrics()
        spark = self.get_spark()
        
        # 1. 数据加载
        stage_start = time.time()
        if isinstance(input_data, str):
            # 从文件加载
            if input_data.endswith('.json'):
                df = spark.read.json(input_data)
            elif input_data.endswith('.parquet'):
                df = spark.read.parquet(input_data)
            elif input_data.endswith('.csv'):
                df = spark.read.csv(input_data, header=True, inferSchema=True)
            else:
                raise ValueError(f"不支持的文件格式: {input_data}")
        elif isinstance(input_data, list):
            # 从列表创建
            df = spark.createDataFrame(input_data)
        elif hasattr(input_data, 'toPandas'):
            # 已经是DataFrame
            df = input_data
        else:
            raise ValueError(f"不支持的输入类型: {type(input_data)}")
        
        self.metrics.total_records = df.count()
        self._log_stage(PipelineStage.EXTRACT, stage_start)
        
        # 缓存数据
        if self.config.enable_cache:
            df = df.cache()
        
        # 2. 数据清洗
        if PipelineStage.CLEAN in stages:
            stage_start = time.time()
            df = DataCleaner.clean_dataframe(df)
            self._log_stage(PipelineStage.CLEAN, stage_start)
        
        # 3. 分词
        if PipelineStage.TOKENIZE in stages:
            stage_start = time.time()
            df = ChineseTokenizer.tokenize_dataframe(df)
            self._log_stage(PipelineStage.TOKENIZE, stage_start)
        
        # 4. 特征提取
        if PipelineStage.FEATURE in stages:
            stage_start = time.time()
            df = FeatureExtractor.extract_keywords(df)
            self._log_stage(PipelineStage.FEATURE, stage_start)
        
        # 5. 情感分析
        if PipelineStage.SENTIMENT in stages:
            stage_start = time.time()
            df = SentimentProcessor.process_sentiment(df)
            self._log_stage(PipelineStage.SENTIMENT, stage_start)
        
        # 6. 三维度排序
        if PipelineStage.RANK in stages:
            stage_start = time.time()
            from .tri_dimension_model import SparkTriDimensionProcessor, TriDimensionConfig
            
            rank_config = TriDimensionConfig()
            processor = SparkTriDimensionProcessor(spark, rank_config)
            df = processor.process_dataframe(df)
            self._log_stage(PipelineStage.RANK, stage_start)
        
        self.metrics.processed_records = df.count()
        self.metrics.end_time = datetime.now()
        
        logger.info(f"流水线完成，总耗时: {self.metrics.duration_seconds():.2f}秒")
        logger.info(f"处理记录数: {self.metrics.processed_records}/{self.metrics.total_records}")
        
        return df
    
    def save_results(self, df: 'DataFrame', 
                     output_path: str = None,
                     format: str = "parquet"):
        """保存结果"""
        output_path = output_path or self.config.output_path
        
        if format == "parquet":
            df.write.mode("overwrite").parquet(output_path)
        elif format == "json":
            df.write.mode("overwrite").json(output_path)
        elif format == "csv":
            df.write.mode("overwrite").csv(output_path, header=True)
        
        logger.info(f"结果已保存到: {output_path}")
    
    def get_statistics(self, df: 'DataFrame') -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_records": df.count(),
            "sentiment_distribution": {},
            "avg_sentiment_score": 0,
            "top_keywords": [],
        }
        
        # 情感分布
        if "sentiment" in df.columns:
            sentiment_counts = df.groupBy("sentiment").count().collect()
            stats["sentiment_distribution"] = {
                row.sentiment: row["count"] for row in sentiment_counts
            }
        
        # 平均情感得分
        if "sentiment_score" in df.columns:
            avg_score = df.agg(F.avg("sentiment_score")).collect()[0][0]
            stats["avg_sentiment_score"] = round(avg_score, 4) if avg_score else 0
        
        # 热门关键词
        if "keywords" in df.columns:
            keywords_df = df.select(F.explode("keywords").alias("keyword"))
            top_keywords = keywords_df.groupBy("keyword").count() \
                .orderBy(F.desc("count")).limit(20).collect()
            stats["top_keywords"] = [
                {"word": row.keyword, "count": row["count"]} 
                for row in top_keywords
            ]
        
        return stats
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取流水线指标"""
        return self.metrics.to_dict()


# 便捷函数
def run_sentiment_pipeline(data: Any, 
                           output_path: str = None) -> Dict[str, Any]:
    """
    运行情感分析流水线
    
    Args:
        data: 输入数据
        output_path: 输出路径
        
    Returns:
        统计结果
    """
    config = PipelineConfig(output_path=output_path or "")
    pipeline = SentimentPipeline(config)
    
    df = pipeline.run(data)
    stats = pipeline.get_statistics(df)
    metrics = pipeline.get_metrics()
    
    if output_path:
        pipeline.save_results(df, output_path)
    
    return {
        "statistics": stats,
        "metrics": metrics,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Spark舆情分析流水线测试")
    print("=" * 60)
    
    # 测试数据
    test_data = [
        {"id": "1", "text": "这个产品太棒了，强烈推荐！", "reposts_count": 100, "comments_count": 50, "attitudes_count": 500, "created_at": "2024-12-10 08:00:00"},
        {"id": "2", "text": "服务态度很差，再也不来了", "reposts_count": 200, "comments_count": 100, "attitudes_count": 300, "created_at": "2024-12-10 09:00:00"},
        {"id": "3", "text": "今天天气不错，适合出门", "reposts_count": 10, "comments_count": 5, "attitudes_count": 50, "created_at": "2024-12-10 10:00:00"},
    ]
    
    try:
        result = run_sentiment_pipeline(test_data)
        print("\n流水线执行结果：")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"执行失败: {e}")
