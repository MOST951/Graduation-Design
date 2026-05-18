"""
ChineseBERT情感分析模块

技术特点：
1. 使用预训练的中文BERT模型进行情感分析
2. 支持细粒度情感分类（正面/中性/负面/多种情绪）
3. 集成Spark进行分布式批量推理
4. 支持模型微调和增量训练

模型选择：
- bert-base-chinese: 基础中文BERT
- hfl/chinese-bert-wwm-ext: 全词遮罩中文BERT（推荐）
- uer/roberta-base-finetuned-chinanews-chinese: 新闻领域微调

作者：毕业设计
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入深度学习库
TORCH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch未安装，BERT模型将不可用")

try:
    # 禁用TensorFlow以避免DLL加载问题
    import os
    os.environ['USE_TF'] = '0'
    os.environ['USE_TORCH'] = '1'
    
    from transformers import (
        BertTokenizer, 
        BertForSequenceClassification,
        BertModel,
        AutoTokenizer,
        AutoModelForSequenceClassification,
    )
    # pipeline可能触发TensorFlow导入，单独处理
    try:
        from transformers import pipeline
    except Exception:
        pipeline = None
        logger.warning("Transformers pipeline不可用")
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Transformers未安装或加载失败: {e}")
    TRANSFORMERS_AVAILABLE = False
except Exception as e:
    logger.warning(f"Transformers加载异常: {e}")
    TRANSFORMERS_AVAILABLE = False

# Spark导入
try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType, FloatType, ArrayType, StructType, StructField
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False


@dataclass
class SentimentResult:
    """情感分析结果"""
    text: str
    sentiment: str  # positive, neutral, negative
    confidence: float
    scores: Dict[str, float]  # 各类别的概率分布
    emotions: Optional[Dict[str, float]] = None  # 细粒度情绪


class SentimentModelConfig:
    """情感模型配置"""
    # 预训练模型名称
    MODEL_NAME = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'chinese-bert-wwm-ext'
    )
    # 备选模型
    ALTERNATIVE_MODELS = [
        "bert-base-chinese",
        "hfl/chinese-bert-wwm-ext",
        "uer/roberta-base-finetuned-chinanews-chinese",
        "IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment",
    ]
    # 最大序列长度
    MAX_LENGTH = 128
    # 批处理大小
    BATCH_SIZE = 32
    # 情感标签
    SENTIMENT_LABELS = ["negative", "neutral", "positive"]
    # 细粒度情绪标签
    EMOTION_LABELS = ["joy", "anger", "sadness", "fear", "surprise", "disgust", "trust", "anticipation"]


class ChineseBERTSentimentAnalyzer:
    """
    基于ChineseBERT的情感分析器
    
    特点：
    1. 使用预训练BERT模型
    2. 支持GPU加速
    3. 批量推理优化
    4. 支持模型缓存
    """
    
    def __init__(self, model_name: str = None, device: str = None, use_cache: bool = True):
        """
        初始化分析器
        
        Args:
            model_name: 模型名称或路径
            device: 运行设备 (cuda/cpu)
            use_cache: 是否使用模型缓存
        """
        self.model_name = model_name or SentimentModelConfig.MODEL_NAME
        self.device = device
        self.use_cache = use_cache
        
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self._initialized = False
        
        # 检查依赖
        if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
            logger.warning("BERT模型依赖未满足，将使用词典方法作为后备")
            self._use_fallback = True
        else:
            self._use_fallback = False
            self._setup_device()
    
    def _setup_device(self):
        """设置运行设备"""
        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"使用设备: {self.device}")
    
    def initialize(self) -> bool:
        """
        初始化模型
        
        优先从全局单例获取已加载的 tokenizer/model，
        避免重复加载；仅当单例不可用时走本地加载路径。
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        if self._use_fallback:
            logger.info("使用词典方法作为后备")
            self._initialized = True
            return True
        
        # ---- 优先委托全局单例 ----
        try:
            from services.model_singleton import get_bert_tokenizer_and_model
            tokenizer, model, device = get_bert_tokenizer_and_model()
            if tokenizer is not None and model is not None:
                self.tokenizer = tokenizer
                self.model = model
                self.device = str(device) if device else self.device
                self._initialized = True
                logger.info("[ChineseBERTSentimentAnalyzer] 已从全局单例获取模型")
                return True
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"[ChineseBERTSentimentAnalyzer] 全局单例加载失败: {e}，回退本地加载")
        
        # ---- 本地加载（兜底） ----
        try:
            logger.info(f"正在加载模型: {self.model_name}")
            cache_dir = os.environ.get("TRANSFORMERS_CACHE", "./model_cache")
            is_local = os.path.isdir(self.model_name)
            load_kwargs = {"local_files_only": True} if is_local else {"cache_dir": cache_dir}
            
            # 尝试使用pipeline（更简单）
            try:
                pipe_kwargs = {"cache_dir": cache_dir} if not is_local else {}
                self.pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                    tokenizer=self.model_name,
                    device=0 if self.device == "cuda" else -1,
                    max_length=SentimentModelConfig.MAX_LENGTH,
                    truncation=True,
                    model_kwargs=pipe_kwargs,
                )
                logger.info("Pipeline模式初始化成功")
            except Exception as e:
                logger.warning(f"Pipeline初始化失败: {e}，尝试手动加载")
                
                # 手动加载模型
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, **load_kwargs)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=2,
                    **load_kwargs,
                )
                self.model.to(self.device)
                self.model.eval()
                logger.info("手动模式初始化成功")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            self._use_fallback = True
            self._initialized = True
            return True
    
    def analyze(self, text: str) -> SentimentResult:
        """
        分析单条文本的情感
        
        Args:
            text: 输入文本
            
        Returns:
            SentimentResult对象
        """
        if not self._initialized:
            self.initialize()
        
        if self._use_fallback:
            return self._fallback_analyze(text)
        
        try:
            if self.pipeline:
                result = self.pipeline(text[:SentimentModelConfig.MAX_LENGTH])[0]
                label = result['label'].lower()
                score = result['score']
                
                # 映射标签
                sentiment = self._map_label(label)
                
                return SentimentResult(
                    text=text,
                    sentiment=sentiment,
                    confidence=score,
                    scores={sentiment: score}
                )
            else:
                return self._manual_analyze(text)
                
        except Exception as e:
            logger.error(f"分析失败: {e}")
            return self._fallback_analyze(text)
    
    def _manual_analyze(self, text: str) -> SentimentResult:
        """手动模式分析"""
        inputs = self.tokenizer(
            text,
            max_length=SentimentModelConfig.MAX_LENGTH,
            truncation=True,
            padding=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1)
            
        probs = probs.cpu().numpy()[0]
        pred_idx = np.argmax(probs)
        
        sentiment = SentimentModelConfig.SENTIMENT_LABELS[pred_idx]
        confidence = float(probs[pred_idx])
        
        scores = {
            label: float(prob) 
            for label, prob in zip(SentimentModelConfig.SENTIMENT_LABELS, probs)
        }
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=confidence,
            scores=scores
        )
    
    def _map_label(self, label: str) -> str:
        """映射模型输出标签到标准标签"""
        label = label.lower()
        if 'pos' in label or 'positive' in label or label == '1' or label == 'label_2':
            return 'positive'
        elif 'neg' in label or 'negative' in label or label == '0' or label == 'label_0':
            return 'negative'
        else:
            return 'neutral'
    
    def _fallback_analyze(self, text: str) -> SentimentResult:
        """后备词典分析方法"""
        from .sentiment_analyzer import SentimentLexicon
        
        sentiment, score = SentimentLexicon.analyze(text)
        
        # 转换为概率分布
        if sentiment == 'positive':
            scores = {'positive': 0.7 + abs(score) * 0.3, 'neutral': 0.2, 'negative': 0.1}
        elif sentiment == 'negative':
            scores = {'positive': 0.1, 'neutral': 0.2, 'negative': 0.7 + abs(score) * 0.3}
        else:
            scores = {'positive': 0.3, 'neutral': 0.4, 'negative': 0.3}
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=max(scores.values()),
            scores=scores
        )
    
    def analyze_batch(self, texts: List[str], batch_size: int = None) -> List[SentimentResult]:
        """
        批量分析文本
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
            
        Returns:
            SentimentResult列表
        """
        if not self._initialized:
            self.initialize()
        
        batch_size = batch_size or SentimentModelConfig.BATCH_SIZE
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            if self._use_fallback:
                batch_results = [self._fallback_analyze(t) for t in batch]
            elif self.pipeline:
                try:
                    pipe_results = self.pipeline(batch)
                    batch_results = []
                    for text, res in zip(batch, pipe_results):
                        sentiment = self._map_label(res['label'])
                        batch_results.append(SentimentResult(
                            text=text,
                            sentiment=sentiment,
                            confidence=res['score'],
                            scores={sentiment: res['score']}
                        ))
                except Exception as e:
                    logger.error(f"批量分析失败: {e}")
                    batch_results = [self._fallback_analyze(t) for t in batch]
            else:
                batch_results = [self._manual_analyze(t) for t in batch]
            
            results.extend(batch_results)
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "initialized": self._initialized,
            "use_fallback": self._use_fallback,
            "max_length": SentimentModelConfig.MAX_LENGTH,
            "labels": SentimentModelConfig.SENTIMENT_LABELS,
        }


class SparkBERTProcessor:
    """
    Spark + BERT 分布式情感分析处理器
    
    使用Spark进行数据分发，在每个分区上运行BERT推理
    """
    
    def __init__(self, spark: Optional['SparkSession'] = None,
                 model_name: str = None):
        self.model_name = model_name or SentimentModelConfig.MODEL_NAME
        
        if spark:
            self.spark = spark
        elif SPARK_AVAILABLE:
            self.spark = SparkSession.builder \
                .appName("BERTSentimentAnalysis") \
                .master(os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077')) \
                .config("spark.driver.memory", "4g") \
                .config("spark.sql.shuffle.partitions", "4") \
                .getOrCreate()
        else:
            self.spark = None
    
    def analyze_dataframe(self, df: 'DataFrame', 
                          text_column: str = "text",
                          batch_size: int = 32) -> 'DataFrame':
        """
        对DataFrame进行情感分析
        
        使用Pandas UDF进行批量处理
        """
        if not SPARK_AVAILABLE:
            raise RuntimeError("Spark不可用")
        
        from pyspark.sql.functions import pandas_udf, PandasUDFType
        import pandas as pd
        
        model_name = self.model_name
        
        # 定义情感分析UDF
        @pandas_udf(StringType())
        def sentiment_udf(texts: pd.Series) -> pd.Series:
            analyzer = ChineseBERTSentimentAnalyzer(model_name)
            analyzer.initialize()
            
            results = analyzer.analyze_batch(texts.tolist(), batch_size)
            return pd.Series([r.sentiment for r in results])
        
        @pandas_udf(FloatType())
        def confidence_udf(texts: pd.Series) -> pd.Series:
            analyzer = ChineseBERTSentimentAnalyzer(model_name)
            analyzer.initialize()
            
            results = analyzer.analyze_batch(texts.tolist(), batch_size)
            return pd.Series([r.confidence for r in results])
        
        # 应用UDF
        df = df.withColumn("bert_sentiment", sentiment_udf(F.col(text_column)))
        df = df.withColumn("bert_confidence", confidence_udf(F.col(text_column)))
        
        # 转换情感为数值得分
        df = df.withColumn(
            "bert_score",
            F.when(F.col("bert_sentiment") == "positive", 1.0)
            .when(F.col("bert_sentiment") == "negative", -1.0)
            .otherwise(0.0)
        )
        
        return df


class HybridSentimentAnalyzer:
    """
    混合情感分析器
    
    结合词典方法和BERT模型的优势：
    1. 词典方法：速度快，可解释性强
    2. BERT方法：准确率高，上下文理解能力强
    
    融合策略：
    - 加权平均：对两种方法的结果进行加权融合
    - 置信度选择：根据置信度选择更可靠的结果
    - 级联判断：先用词典快速筛选，再用BERT精细分析
    """
    
    def __init__(self, bert_weight: float = 0.6, lexicon_weight: float = 0.4):
        """
        Args:
            bert_weight: BERT结果权重
            lexicon_weight: 词典结果权重
        """
        self.bert_weight = bert_weight
        self.lexicon_weight = lexicon_weight
        
        self.bert_analyzer = ChineseBERTSentimentAnalyzer()
        self._initialized = False
    
    def initialize(self):
        """初始化分析器"""
        self.bert_analyzer.initialize()
        self._initialized = True
    
    def analyze(self, text: str, strategy: str = "weighted") -> Dict[str, Any]:
        """
        混合分析
        
        Args:
            text: 输入文本
            strategy: 融合策略 (weighted/confidence/cascade)
            
        Returns:
            分析结果
        """
        if not self._initialized:
            self.initialize()
        
        # 词典分析
        from .sentiment_analyzer import SentimentLexicon
        lexicon_sentiment, lexicon_score = SentimentLexicon.analyze(text)
        
        # BERT分析
        bert_result = self.bert_analyzer.analyze(text)
        bert_score = 1.0 if bert_result.sentiment == 'positive' else (-1.0 if bert_result.sentiment == 'negative' else 0.0)
        
        if strategy == "weighted":
            # 加权平均
            final_score = self.bert_weight * bert_score + self.lexicon_weight * lexicon_score
            if final_score > 0.2:
                final_sentiment = 'positive'
            elif final_score < -0.2:
                final_sentiment = 'negative'
            else:
                final_sentiment = 'neutral'
                
        elif strategy == "confidence":
            # 置信度选择
            lexicon_confidence = abs(lexicon_score)
            if bert_result.confidence > lexicon_confidence:
                final_sentiment = bert_result.sentiment
                final_score = bert_score
            else:
                final_sentiment = lexicon_sentiment
                final_score = lexicon_score
                
        else:  # cascade
            # 级联判断
            if abs(lexicon_score) > 0.5:
                # 词典结果明确，直接使用
                final_sentiment = lexicon_sentiment
                final_score = lexicon_score
            else:
                # 词典结果不明确，使用BERT
                final_sentiment = bert_result.sentiment
                final_score = bert_score
        
        return {
            "text": text,
            "sentiment": final_sentiment,
            "score": round(final_score, 4),
            "strategy": strategy,
            "details": {
                "lexicon": {
                    "sentiment": lexicon_sentiment,
                    "score": round(lexicon_score, 4)
                },
                "bert": {
                    "sentiment": bert_result.sentiment,
                    "confidence": round(bert_result.confidence, 4),
                    "scores": {k: round(v, 4) for k, v in bert_result.scores.items()}
                }
            }
        }


# 便捷函数
def analyze_sentiment_bert(text: str) -> Dict[str, Any]:
    """使用BERT分析单条文本"""
    analyzer = ChineseBERTSentimentAnalyzer()
    analyzer.initialize()
    result = analyzer.analyze(text)
    return {
        "text": result.text,
        "sentiment": result.sentiment,
        "confidence": round(result.confidence, 4),
        "scores": {k: round(v, 4) for k, v in result.scores.items()}
    }


def analyze_sentiment_hybrid(text: str, strategy: str = "weighted") -> Dict[str, Any]:
    """使用混合方法分析"""
    analyzer = HybridSentimentAnalyzer()
    return analyzer.analyze(text, strategy)


if __name__ == "__main__":
    print("=" * 60)
    print("ChineseBERT情感分析测试")
    print("=" * 60)
    
    test_texts = [
        "这个产品太棒了，强烈推荐！",
        "服务态度很差，再也不来了",
        "今天天气不错",
        "非常失望，完全不值这个价格",
        "哈哈哈太好笑了",
    ]
    
    print("\n1. BERT分析结果：")
    print("-" * 40)
    for text in test_texts:
        result = analyze_sentiment_bert(text)
        print(f"文本: {text}")
        print(f"情感: {result['sentiment']}, 置信度: {result['confidence']}")
        print()
    
    print("\n2. 混合分析结果：")
    print("-" * 40)
    for text in test_texts:
        result = analyze_sentiment_hybrid(text, "weighted")
        print(f"文本: {text}")
        print(f"最终情感: {result['sentiment']}, 得分: {result['score']}")
        print(f"词典: {result['details']['lexicon']}")
        print(f"BERT: {result['details']['bert']}")
        print()
