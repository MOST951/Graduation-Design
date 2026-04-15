"""
ChineseBERT情感分析模块 - 完整实现

技术特点：
1. 使用transformers库加载预训练中文BERT模型
2. 支持GPU/CPU自动检测和资源分配
3. 批量推理优化（batch processing）
4. 与词典方法融合的混合分析
5. Spark集成（UDF和pandas_udf）

支持的预训练模型：
- bert-base-chinese: 基础中文BERT
- hfl/chinese-bert-wwm-ext: 全词遮罩中文BERT（推荐）
- IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment: 情感微调模型

作者：毕业设计
日期：2024-12
"""
from __future__ import annotations

import os
import sys
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from functools import lru_cache
import threading

# 全局单例模型加载器
try:
    from services.model_singleton import (
        get_bert_tokenizer_and_model as _singleton_load,
        is_bert_available as _singleton_available,
    )
    _SINGLETON_AVAILABLE = True
except ImportError:
    _SINGLETON_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 依赖检查 ====================

TORCH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False
SPARK_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, Dataset
    TORCH_AVAILABLE = True
    logger.info(f"PyTorch版本: {torch.__version__}")
    logger.info(f"CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU设备: {torch.cuda.get_device_name(0)}")
except ImportError as e:
    logger.warning(f"PyTorch未安装: {e}")
    # 占位桩：使类定义（注解 + @torch.no_grad() 装饰器）不报错
    class _NoGrad:
        def __call__(self, fn): return fn
        def __enter__(self): return self
        def __exit__(self, *a): pass
    class _TorchStub:
        no_grad = _NoGrad
    torch = _TorchStub()  # type: ignore
    nn = None
    F = None
    class Dataset:
        pass
    class DataLoader:
        pass

try:
    from transformers import (
        BertTokenizer,
        BertForSequenceClassification,
        BertModel,
        BertConfig,
        AutoTokenizer,
        AutoModelForSequenceClassification,
        AutoConfig,
    )
    TRANSFORMERS_AVAILABLE = True
    logger.info("Transformers库已加载")
except ImportError as e:
    logger.warning(f"Transformers未安装: {e}")

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F_spark
    from pyspark.sql.types import StringType, FloatType, ArrayType, StructType, StructField
    SPARK_AVAILABLE = True
except ImportError:
    logger.warning("PySpark未安装")


# ==================== 配置类 ====================

@dataclass
class BertModelConfig:
    """BERT模型配置"""
    # 模型选择
    model_name: str = "bert-base-chinese"
    
    # 备选模型列表
    AVAILABLE_MODELS = [
        "bert-base-chinese",
        "hfl/chinese-bert-wwm-ext",
        "hfl/chinese-roberta-wwm-ext",
        "IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment",
        "uer/roberta-base-finetuned-chinanews-chinese",
    ]
    
    # 推理配置
    max_length: int = 128
    batch_size: int = 32
    num_labels: int = 3  # positive, neutral, negative
    
    # 设备配置
    device: str = "auto"  # auto, cuda, cpu
    use_fp16: bool = True  # 半精度推理（GPU加速）
    
    # 缓存配置
    cache_dir: str = "./model_cache"
    use_cache: bool = True
    
    # 标签映射
    label_map: Dict[int, str] = field(default_factory=lambda: {
        0: "negative",
        1: "neutral", 
        2: "positive"
    })
    
    # 性能配置
    num_workers: int = 4
    prefetch_factor: int = 2


@dataclass
class SentimentResult:
    """情感分析结果"""
    text: str
    label: str                    # positive/neutral/negative
    score: float                  # 情感得分 [-1, 1]
    confidence: float             # 置信度 [0, 1]
    probabilities: Dict[str, float]  # 各类别概率
    processing_time: float = 0.0  # 处理时间(ms)


# ==================== 文本预处理 ====================

class TextPreprocessor:
    """
    文本预处理器
    
    功能：
    1. 文本清洗
    2. 长度截断
    3. 特殊字符处理
    """
    
    # 需要移除的模式
    REMOVE_PATTERNS = [
        r'http[s]?://\S+',           # URL
        r'@[\w\u4e00-\u9fff]+',      # @用户
        r'#[^#]+#',                   # 话题标签
        r'\[[\w\u4e00-\u9fff]+\]',   # 表情符号
        r'<[^>]+>',                   # HTML标签
    ]
    
    def __init__(self, max_length: int = 128):
        self.max_length = max_length
        import re
        self.patterns = [re.compile(p) for p in self.REMOVE_PATTERNS]
    
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        
        # 移除特殊模式
        for pattern in self.patterns:
            text = pattern.sub('', text)
        
        # 移除多余空白
        import re
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def truncate(self, text: str) -> str:
        """截断文本"""
        if len(text) > self.max_length * 2:  # 粗略截断（tokenizer会精确处理）
            text = text[:self.max_length * 2]
        return text
    
    def preprocess(self, text: str) -> str:
        """完整预处理"""
        text = self.clean_text(text)
        text = self.truncate(text)
        return text
    
    def preprocess_batch(self, texts: List[str]) -> List[str]:
        """批量预处理"""
        return [self.preprocess(t) for t in texts]


# ==================== 数据集类 ====================

if TORCH_AVAILABLE:
    class TextDataset(Dataset):
        """文本数据集"""
        
        def __init__(self, texts: List[str], tokenizer, max_length: int = 128):
            self.texts = texts
            self.tokenizer = tokenizer
            self.max_length = max_length
        
        def __len__(self):
            return len(self.texts)
        
        def __getitem__(self, idx):
            text = self.texts[idx]
            encoding = self.tokenizer(
                text,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            return {
                'input_ids': encoding['input_ids'].squeeze(),
                'attention_mask': encoding['attention_mask'].squeeze(),
                'text': text,
                'idx': idx
            }


# ==================== BERT情感分析器 ====================

class ChineseBertSentimentAnalyzer:
    """
    ChineseBERT情感分析器
    
    特点：
    1. 自动设备检测（GPU/CPU）
    2. 批量推理优化
    3. 半精度推理支持
    4. 模型缓存
    5. 线程安全
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[BertModelConfig] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.config = config or BertModelConfig()
        self.tokenizer = None
        self.model = None
        self.device = None
        self.preprocessor = TextPreprocessor(self.config.max_length)
        self._initialized = False
        self._use_fallback = False
        
        # 检查依赖
        if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
            logger.warning("深度学习依赖未满足，将使用词典方法作为后备")
            self._use_fallback = True
    
    def _setup_device(self) -> torch.device:
        """设置计算设备"""
        if self.config.device == "auto":
            if torch.cuda.is_available():
                device = torch.device("cuda")
                logger.info(f"使用GPU: {torch.cuda.get_device_name(0)}")
                logger.info(f"GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            else:
                device = torch.device("cpu")
                logger.info("使用CPU")
        else:
            device = torch.device(self.config.device)
        
        return device
    
    def initialize(self) -> bool:
        """
        初始化模型
        
        优先从全局单例 model_singleton 获取已加载的 tokenizer/model，
        避免重复加载；仅当单例不可用时才走本地加载路径。
        
        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True
        
        if self._use_fallback:
            self._initialized = True
            return True
        
        # ---- 优先委托给全局单例 ----
        if _SINGLETON_AVAILABLE:
            try:
                tokenizer, model, device = _singleton_load()
                if tokenizer is not None and model is not None:
                    self.tokenizer = tokenizer
                    self.model = model
                    self.device = device
                    self._initialized = True
                    logger.info("[ChineseBertSentimentAnalyzer] 已从全局单例获取模型")
                    return True
                else:
                    logger.warning("[ChineseBertSentimentAnalyzer] 全局单例返回空，回退本地加载")
            except Exception as e:
                logger.warning(f"[ChineseBertSentimentAnalyzer] 全局单例加载失败: {e}，回退本地加载")
        
        # ---- 本地加载（兜底） ----
        try:
            logger.info(f"正在加载模型: {self.config.model_name}")
            start_time = time.time()
            
            # 设置设备
            self.device = self._setup_device()
            
            # 创建缓存目录
            cache_dir = os.environ.get("TRANSFORMERS_CACHE", self.config.cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            
            # 加载tokenizer
            logger.info("加载Tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                cache_dir=cache_dir,
            )
            
            # 加载模型
            logger.info("加载模型...")
            try:
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.config.model_name,
                    num_labels=self.config.num_labels,
                    cache_dir=cache_dir,
                )
            except Exception as e:
                logger.warning(f"加载分类模型失败: {e}，尝试加载基础模型")
                base_model = BertModel.from_pretrained(
                    self.config.model_name,
                    cache_dir=cache_dir,
                )
                self.model = BertForSequenceClassificationCustom(
                    base_model, 
                    self.config.num_labels
                )
            
            self.model.to(self.device)
            self.model.eval()
            
            if self.config.use_fp16 and self.device.type == 'cuda':
                self.model.half()
                logger.info("已启用FP16半精度推理")
            
            elapsed = time.time() - start_time
            logger.info(f"模型加载完成，耗时: {elapsed:.2f}秒")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            self._use_fallback = True
            self._initialized = True
            return True
    
    def _tokenize_batch(self, texts: List[str]) -> Dict[str, torch.Tensor]:
        """
        批量tokenize
        
        Args:
            texts: 文本列表
            
        Returns:
            tokenized结果
        """
        # 预处理
        processed_texts = self.preprocessor.preprocess_batch(texts)
        
        # Tokenize
        encodings = self.tokenizer(
            processed_texts,
            max_length=self.config.max_length,
            padding=True,
            truncation=True,
            return_tensors='pt'
        )
        
        return encodings
    
    @torch.no_grad()
    def _inference_batch(self, encodings: Dict[str, torch.Tensor]) -> np.ndarray:
        """
        批量推理
        
        Args:
            encodings: tokenized结果
            
        Returns:
            概率分布 (batch_size, num_labels)
        """
        # 移动到设备
        input_ids = encodings['input_ids'].to(self.device)
        attention_mask = encodings['attention_mask'].to(self.device)
        
        # 半精度
        if self.config.use_fp16 and self.device.type == 'cuda':
            with torch.cuda.amp.autocast():
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
        else:
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
        
        # Softmax得到概率
        logits = outputs.logits
        probabilities = F.softmax(logits, dim=-1)
        
        return probabilities.cpu().numpy()
    
    def _postprocess(self, text: str, probabilities: np.ndarray, 
                     processing_time: float) -> SentimentResult:
        """
        后处理：概率转情感得分
        
        Args:
            text: 原始文本
            probabilities: 概率分布 [negative, neutral, positive]
            processing_time: 处理时间
            
        Returns:
            SentimentResult
        """
        # 获取预测标签
        pred_idx = np.argmax(probabilities)
        label = self.config.label_map[pred_idx]
        confidence = float(probabilities[pred_idx])
        
        # 计算情感得分 [-1, 1]
        # 公式: score = P(positive) - P(negative)
        # 或者: score = P(positive) * 1 + P(neutral) * 0 + P(negative) * (-1)
        if len(probabilities) == 3:
            score = float(probabilities[2] - probabilities[0])  # positive - negative
        else:
            # 二分类
            score = float(probabilities[1] - probabilities[0]) if len(probabilities) == 2 else 0.0
        
        # 构建概率字典
        prob_dict = {
            self.config.label_map[i]: float(probabilities[i])
            for i in range(len(probabilities))
        }
        
        return SentimentResult(
            text=text,
            label=label,
            score=score,
            confidence=confidence,
            probabilities=prob_dict,
            processing_time=processing_time
        )
    
    def analyze(self, text: str) -> SentimentResult:
        """
        分析单条文本
        
        Args:
            text: 输入文本
            
        Returns:
            SentimentResult
        """
        results = self.analyze_batch([text])
        return results[0]
    
    def analyze_batch(self, texts: List[str], 
                      batch_size: Optional[int] = None) -> List[SentimentResult]:
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
        
        if self._use_fallback:
            return self._fallback_analyze_batch(texts)
        
        batch_size = batch_size or self.config.batch_size
        results = []
        
        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            start_time = time.time()
            
            try:
                # Tokenize
                encodings = self._tokenize_batch(batch_texts)
                
                # 推理
                probabilities = self._inference_batch(encodings)
                
                # 计算处理时间
                elapsed = (time.time() - start_time) * 1000 / len(batch_texts)
                
                # 后处理
                for j, text in enumerate(batch_texts):
                    result = self._postprocess(text, probabilities[j], elapsed)
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"批量分析失败: {e}")
                # 降级到词典方法
                fallback_results = self._fallback_analyze_batch(batch_texts)
                results.extend(fallback_results)
        
        return results
    
    def _fallback_analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        后备词典分析方法
        """
        from .sentiment_analyzer import SentimentLexicon
        
        results = []
        for text in texts:
            start_time = time.time()
            
            sentiment, score = SentimentLexicon.analyze(text)
            elapsed = (time.time() - start_time) * 1000
            
            # 构建概率分布
            if sentiment == 'positive':
                probs = {'negative': 0.1, 'neutral': 0.2, 'positive': 0.7}
            elif sentiment == 'negative':
                probs = {'negative': 0.7, 'neutral': 0.2, 'positive': 0.1}
            else:
                probs = {'negative': 0.25, 'neutral': 0.5, 'positive': 0.25}
            
            results.append(SentimentResult(
                text=text,
                label=sentiment,
                score=score,
                confidence=max(probs.values()),
                probabilities=probs,
                processing_time=elapsed
            ))
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            "model_name": self.config.model_name,
            "max_length": self.config.max_length,
            "batch_size": self.config.batch_size,
            "num_labels": self.config.num_labels,
            "initialized": self._initialized,
            "use_fallback": self._use_fallback,
        }
        
        if self._initialized and not self._use_fallback:
            info.update({
                "device": str(self.device),
                "use_fp16": self.config.use_fp16 and self.device.type == 'cuda',
            })
            
            if self.device.type == 'cuda':
                info["gpu_memory_allocated"] = f"{torch.cuda.memory_allocated() / 1024**2:.1f} MB"
        
        return info


# ==================== 自定义分类模型 ====================

if TORCH_AVAILABLE:
    class BertForSequenceClassificationCustom(nn.Module):
        """自定义BERT分类模型"""
        
        def __init__(self, bert_model, num_labels: int = 3, dropout: float = 0.1):
            super().__init__()
            self.bert = bert_model
            self.dropout = nn.Dropout(dropout)
            self.classifier = nn.Linear(bert_model.config.hidden_size, num_labels)
        
        def forward(self, input_ids, attention_mask=None, token_type_ids=None):
            outputs = self.bert(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids
            )
            
            # 使用[CLS] token的输出
            pooled_output = outputs.last_hidden_state[:, 0, :]
            pooled_output = self.dropout(pooled_output)
            logits = self.classifier(pooled_output)
            
            return type('Output', (), {'logits': logits})()


# ==================== 混合分析器 ====================

class HybridSentimentAnalyzer:
    """
    混合情感分析器
    
    融合词典方法和BERT模型的优势：
    - 词典方法：速度快，可解释性强
    - BERT方法：准确率高，上下文理解能力强
    
    融合策略：
    1. weighted: 加权平均
    2. confidence: 置信度选择
    3. cascade: 级联判断
    4. voting: 投票机制
    """
    
    def __init__(self, 
                 bert_weight: float = 0.6,
                 lexicon_weight: float = 0.4,
                 strategy: str = "weighted"):
        """
        Args:
            bert_weight: BERT结果权重
            lexicon_weight: 词典结果权重
            strategy: 融合策略
        """
        self.bert_weight = bert_weight
        self.lexicon_weight = lexicon_weight
        self.strategy = strategy
        
        self.bert_analyzer = ChineseBertSentimentAnalyzer()
        self._initialized = False
    
    def initialize(self):
        """初始化"""
        self.bert_analyzer.initialize()
        self._initialized = True
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        混合分析
        
        Args:
            text: 输入文本
            
        Returns:
            分析结果
        """
        if not self._initialized:
            self.initialize()
        
        start_time = time.time()
        
        # 词典分析
        from .sentiment_analyzer import SentimentLexicon
        lex_sentiment, lex_score = SentimentLexicon.analyze(text)
        lex_confidence = min(1.0, abs(lex_score) + 0.3)
        
        # BERT分析
        bert_result = self.bert_analyzer.analyze(text)
        
        # 融合
        if self.strategy == "weighted":
            final_score, final_label = self._weighted_fusion(
                lex_score, lex_confidence,
                bert_result.score, bert_result.confidence
            )
        elif self.strategy == "confidence":
            final_score, final_label = self._confidence_fusion(
                lex_score, lex_sentiment, lex_confidence,
                bert_result.score, bert_result.label, bert_result.confidence
            )
        elif self.strategy == "cascade":
            final_score, final_label = self._cascade_fusion(
                lex_score, lex_sentiment, lex_confidence,
                bert_result.score, bert_result.label, bert_result.confidence
            )
        else:  # voting
            final_score, final_label = self._voting_fusion(
                lex_sentiment, bert_result.label
            )
        
        elapsed = (time.time() - start_time) * 1000
        
        return {
            "text": text,
            "sentiment": final_label,
            "score": round(final_score, 4),
            "confidence": round(max(lex_confidence, bert_result.confidence), 4),
            "strategy": self.strategy,
            "processing_time_ms": round(elapsed, 2),
            "details": {
                "lexicon": {
                    "sentiment": lex_sentiment,
                    "score": round(lex_score, 4),
                    "confidence": round(lex_confidence, 4),
                },
                "bert": {
                    "sentiment": bert_result.label,
                    "score": round(bert_result.score, 4),
                    "confidence": round(bert_result.confidence, 4),
                    "probabilities": {k: round(v, 4) for k, v in bert_result.probabilities.items()},
                }
            }
        }
    
    def _weighted_fusion(self, lex_score: float, lex_conf: float,
                         bert_score: float, bert_conf: float) -> Tuple[float, str]:
        """加权融合"""
        # 根据置信度动态调整权重
        total_conf = lex_conf + bert_conf
        if total_conf > 0:
            lex_w = self.lexicon_weight * lex_conf / total_conf
            bert_w = self.bert_weight * bert_conf / total_conf
        else:
            lex_w = self.lexicon_weight
            bert_w = self.bert_weight
        
        # 归一化权重
        total_w = lex_w + bert_w
        lex_w /= total_w
        bert_w /= total_w
        
        final_score = lex_w * lex_score + bert_w * bert_score
        
        if final_score > 0.2:
            label = "positive"
        elif final_score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        return final_score, label
    
    def _confidence_fusion(self, lex_score: float, lex_label: str, lex_conf: float,
                           bert_score: float, bert_label: str, bert_conf: float) -> Tuple[float, str]:
        """置信度选择"""
        if bert_conf > lex_conf:
            return bert_score, bert_label
        else:
            return lex_score, lex_label
    
    def _cascade_fusion(self, lex_score: float, lex_label: str, lex_conf: float,
                        bert_score: float, bert_label: str, bert_conf: float) -> Tuple[float, str]:
        """级联判断"""
        # 如果词典结果明确，直接使用
        if abs(lex_score) > 0.6:
            return lex_score, lex_label
        # 否则使用BERT
        return bert_score, bert_label
    
    def _voting_fusion(self, lex_label: str, bert_label: str) -> Tuple[float, str]:
        """投票机制"""
        if lex_label == bert_label:
            label = lex_label
            score = 0.8 if label == "positive" else (-0.8 if label == "negative" else 0.0)
        else:
            # 不一致时倾向于BERT
            label = bert_label
            score = 0.5 if label == "positive" else (-0.5 if label == "negative" else 0.0)
        
        return score, label
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """批量混合分析"""
        return [self.analyze(text) for text in texts]


# ==================== Spark集成 ====================

class SparkBertIntegration:
    """
    Spark与BERT集成
    
    提供两种集成方式：
    1. UDF函数：简单易用
    2. pandas_udf：高性能批处理
    """
    
    def __init__(self, spark: Optional['SparkSession'] = None):
        if spark:
            self.spark = spark
        elif SPARK_AVAILABLE:
            self.spark = SparkSession.builder \
                .appName("BertSentimentAnalysis") \
                .master("local[*]") \
                .config("spark.driver.memory", "4g") \
                .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
                .getOrCreate()
        else:
            self.spark = None
        
        self._analyzer = None
    
    def _get_analyzer(self) -> ChineseBertSentimentAnalyzer:
        """获取分析器（延迟初始化）"""
        if self._analyzer is None:
            self._analyzer = ChineseBertSentimentAnalyzer()
            self._analyzer.initialize()
        return self._analyzer
    
    def create_sentiment_udf(self):
        """
        创建情感分析UDF
        
        Returns:
            Spark UDF函数
        """
        if not SPARK_AVAILABLE:
            raise RuntimeError("Spark不可用")
        
        from pyspark.sql.functions import udf
        
        def analyze_sentiment(text: str) -> str:
            if not text:
                return "neutral"
            
            analyzer = ChineseBertSentimentAnalyzer()
            analyzer.initialize()
            result = analyzer.analyze(text)
            return result.label
        
        return udf(analyze_sentiment, StringType())
    
    def create_sentiment_score_udf(self):
        """创建情感得分UDF"""
        if not SPARK_AVAILABLE:
            raise RuntimeError("Spark不可用")
        
        from pyspark.sql.functions import udf
        
        def get_sentiment_score(text: str) -> float:
            if not text:
                return 0.0
            
            analyzer = ChineseBertSentimentAnalyzer()
            analyzer.initialize()
            result = analyzer.analyze(text)
            return float(result.score)
        
        return udf(get_sentiment_score, FloatType())
    
    def create_pandas_udf(self, batch_size: int = 32):
        """
        创建高性能pandas_udf
        
        使用Arrow进行高效数据传输
        """
        if not SPARK_AVAILABLE:
            raise RuntimeError("Spark不可用")
        
        from pyspark.sql.functions import pandas_udf
        import pandas as pd
        
        @pandas_udf(StringType())
        def bert_sentiment_pandas_udf(texts: pd.Series) -> pd.Series:
            """批量情感分析pandas_udf"""
            analyzer = ChineseBertSentimentAnalyzer()
            analyzer.initialize()
            
            results = analyzer.analyze_batch(texts.tolist(), batch_size=batch_size)
            return pd.Series([r.label for r in results])
        
        return bert_sentiment_pandas_udf
    
    def create_score_pandas_udf(self, batch_size: int = 32):
        """创建得分pandas_udf"""
        if not SPARK_AVAILABLE:
            raise RuntimeError("Spark不可用")
        
        from pyspark.sql.functions import pandas_udf
        import pandas as pd
        
        @pandas_udf(FloatType())
        def bert_score_pandas_udf(texts: pd.Series) -> pd.Series:
            """批量情感得分pandas_udf"""
            analyzer = ChineseBertSentimentAnalyzer()
            analyzer.initialize()
            
            results = analyzer.analyze_batch(texts.tolist(), batch_size=batch_size)
            return pd.Series([r.score for r in results])
        
        return bert_score_pandas_udf
    
    def analyze_dataframe(self, df: 'DataFrame', 
                          text_column: str = "text",
                          use_pandas_udf: bool = True,
                          batch_size: int = 32) -> 'DataFrame':
        """
        分析DataFrame
        
        Args:
            df: 输入DataFrame
            text_column: 文本列名
            use_pandas_udf: 是否使用pandas_udf（推荐）
            batch_size: 批处理大小
            
        Returns:
            添加了情感分析结果的DataFrame
        """
        if use_pandas_udf:
            sentiment_udf = self.create_pandas_udf(batch_size)
            score_udf = self.create_score_pandas_udf(batch_size)
        else:
            sentiment_udf = self.create_sentiment_udf()
            score_udf = self.create_sentiment_score_udf()
        
        df = df.withColumn("bert_sentiment", sentiment_udf(F_spark.col(text_column)))
        df = df.withColumn("bert_score", score_udf(F_spark.col(text_column)))
        
        return df


# ==================== 便捷函数 ====================

def analyze_text(text: str, use_bert: bool = True) -> Dict[str, Any]:
    """
    分析单条文本
    
    Args:
        text: 输入文本
        use_bert: 是否使用BERT
        
    Returns:
        分析结果
    """
    if use_bert:
        analyzer = ChineseBertSentimentAnalyzer()
        analyzer.initialize()
        result = analyzer.analyze(text)
        return {
            "text": result.text,
            "sentiment": result.label,
            "score": round(result.score, 4),
            "confidence": round(result.confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in result.probabilities.items()},
            "processing_time_ms": round(result.processing_time, 2),
        }
    else:
        from .sentiment_analyzer import SentimentLexicon
        sentiment, score = SentimentLexicon.analyze(text)
        return {
            "text": text,
            "sentiment": sentiment,
            "score": round(score, 4),
        }


def analyze_texts_batch(texts: List[str], 
                        batch_size: int = 32,
                        use_hybrid: bool = False) -> List[Dict[str, Any]]:
    """
    批量分析文本
    
    Args:
        texts: 文本列表
        batch_size: 批处理大小
        use_hybrid: 是否使用混合方法
        
    Returns:
        分析结果列表
    """
    if use_hybrid:
        analyzer = HybridSentimentAnalyzer()
        return analyzer.analyze_batch(texts)
    else:
        analyzer = ChineseBertSentimentAnalyzer()
        analyzer.initialize()
        results = analyzer.analyze_batch(texts, batch_size)
        return [
            {
                "text": r.text,
                "sentiment": r.label,
                "score": round(r.score, 4),
                "confidence": round(r.confidence, 4),
            }
            for r in results
        ]


# ==================== 性能测试 ====================

def benchmark(num_samples: int = 100, batch_size: int = 32):
    """
    性能基准测试
    
    Args:
        num_samples: 测试样本数
        batch_size: 批处理大小
    """
    print("=" * 60)
    print("ChineseBERT情感分析 性能基准测试")
    print("=" * 60)
    
    # 生成测试数据
    test_texts = [
        f"这是第{i}条测试文本，用于评估模型性能。" + 
        ("非常好！" if i % 3 == 0 else "太差了！" if i % 3 == 1 else "一般般。")
        for i in range(num_samples)
    ]
    
    analyzer = ChineseBertSentimentAnalyzer()
    
    # 初始化
    print("\n1. 模型初始化...")
    start = time.time()
    analyzer.initialize()
    init_time = time.time() - start
    print(f"   初始化耗时: {init_time:.2f}秒")
    
    # 单条推理
    print("\n2. 单条推理测试...")
    start = time.time()
    for text in test_texts[:10]:
        analyzer.analyze(text)
    single_time = (time.time() - start) / 10 * 1000
    print(f"   平均单条耗时: {single_time:.2f}ms")
    
    # 批量推理
    print(f"\n3. 批量推理测试 (batch_size={batch_size})...")
    start = time.time()
    results = analyzer.analyze_batch(test_texts, batch_size)
    batch_time = time.time() - start
    throughput = num_samples / batch_time
    print(f"   总耗时: {batch_time:.2f}秒")
    print(f"   吞吐量: {throughput:.1f} 条/秒")
    print(f"   平均每条: {batch_time/num_samples*1000:.2f}ms")
    
    # 模型信息
    print("\n4. 模型信息:")
    info = analyzer.get_model_info()
    for k, v in info.items():
        print(f"   {k}: {v}")
    
    # 结果统计
    print("\n5. 结果统计:")
    labels = [r.label for r in results]
    for label in ['positive', 'neutral', 'negative']:
        count = labels.count(label)
        print(f"   {label}: {count} ({count/len(labels)*100:.1f}%)")


# ==================== 主函数 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("ChineseBERT情感分析模块测试")
    print("=" * 60)
    
    # 测试文本
    test_texts = [
        "这个产品太棒了，强烈推荐给大家！",
        "服务态度很差，再也不来了",
        "今天天气不错，适合出门",
        "非常失望，完全不值这个价格",
        "哈哈哈太好笑了，笑死我了",
        "质量一般，没有想象中那么好",
    ]
    
    print("\n1. BERT分析测试:")
    print("-" * 40)
    for text in test_texts:
        result = analyze_text(text, use_bert=True)
        print(f"文本: {text}")
        print(f"情感: {result['sentiment']}, 得分: {result['score']}, 置信度: {result['confidence']}")
        print()
    
    print("\n2. 混合分析测试:")
    print("-" * 40)
    analyzer = HybridSentimentAnalyzer(strategy="weighted")
    for text in test_texts[:3]:
        result = analyzer.analyze(text)
        print(f"文本: {text}")
        print(f"最终: {result['sentiment']}, 得分: {result['score']}")
        print(f"词典: {result['details']['lexicon']}")
        print(f"BERT: {result['details']['bert']}")
        print()
    
    # 性能测试
    print("\n3. 性能基准测试:")
    benchmark(num_samples=50, batch_size=16)
