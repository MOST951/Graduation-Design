"""
统一情感分析服务
================

整合多种情感分析方法，提供统一的API接口：
1. 词典方法 - 快速、可解释
2. ChineseBERT - 高准确率
3. 混合方法 - 综合优势

作者：毕业设计
日期：2026-01
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AnalysisMethod(Enum):
    """分析方法枚举"""
    LEXICON = "lexicon"      # 词典方法
    BERT = "bert"            # BERT深度学习
    HYBRID = "hybrid"        # 混合方法（默认）


@dataclass
class SentimentResult:
    """情感分析结果"""
    text: str
    sentiment: str           # positive/negative/neutral
    score: float             # -1.0 到 1.0
    confidence: float        # 0.0 到 1.0
    method: str              # 使用的分析方法
    details: Optional[Dict] = None


class BaseSentimentAnalyzer(ABC):
    """情感分析器基类"""
    
    @abstractmethod
    def analyze(self, text: str) -> SentimentResult:
        """分析单条文本"""
        pass
    
    @abstractmethod
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """批量分析"""
        pass


class LexiconAnalyzer(BaseSentimentAnalyzer):
    """词典情感分析器"""
    
    def __init__(self):
        self.positive_words = set()
        self.negative_words = set()
        self.degree_words = {}
        self.negation_words = set()
        self._load_lexicons()
    
    def _load_lexicons(self):
        """加载情感词典"""
        lexicon_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'resources', 'lexicons'
        )
        
        # 加载正面词
        pos_file = os.path.join(lexicon_dir, 'positive.txt')
        if os.path.exists(pos_file):
            with open(pos_file, 'r', encoding='utf-8') as f:
                self.positive_words = set(line.strip() for line in f if line.strip())
        
        # 加载负面词
        neg_file = os.path.join(lexicon_dir, 'negative.txt')
        if os.path.exists(neg_file):
            with open(neg_file, 'r', encoding='utf-8') as f:
                self.negative_words = set(line.strip() for line in f if line.strip())
        
        # 默认词典（如果文件不存在）
        if not self.positive_words:
            self.positive_words = {
                '好', '棒', '赞', '喜欢', '开心', '高兴', '满意', '优秀', '精彩',
                '感谢', '支持', '推荐', '期待', '成功', '幸福', '美好', '完美'
            }
        if not self.negative_words:
            self.negative_words = {
                '差', '烂', '糟', '讨厌', '失望', '难过', '生气', '垃圾', '坑',
                '骗', '假', '差评', '退款', '投诉', '问题', '失败', '难受'
            }
        
        self.negation_words = {'不', '没', '无', '非', '别', '未', '莫'}
        self.degree_words = {
            '很': 1.5, '非常': 2.0, '特别': 2.0, '太': 2.0,
            '极其': 2.5, '超级': 2.0, '有点': 0.5, '稍微': 0.5
        }
        
        logger.info(f"词典加载完成: 正面词{len(self.positive_words)}个, 负面词{len(self.negative_words)}个")
    
    def analyze(self, text: str) -> SentimentResult:
        """词典方法分析"""
        if not text or not text.strip():
            return SentimentResult(
                text=text, sentiment='neutral', score=0.0,
                confidence=0.5, method='lexicon'
            )
        
        pos_count = sum(1 for word in self.positive_words if word in text)
        neg_count = sum(1 for word in self.negative_words if word in text)
        
        # 检查否定词
        has_negation = any(neg in text for neg in self.negation_words)
        
        # 计算得分
        total = pos_count + neg_count
        if total == 0:
            score = 0.0
            sentiment = 'neutral'
            confidence = 0.5
        else:
            raw_score = (pos_count - neg_count) / total
            if has_negation:
                raw_score = -raw_score * 0.8
            
            score = max(-1.0, min(1.0, raw_score))
            confidence = min(1.0, 0.5 + total * 0.1)
            
            if score > 0.2:
                sentiment = 'positive'
            elif score < -0.2:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            score=round(score, 3),
            confidence=round(confidence, 3),
            method='lexicon',
            details={'pos_count': pos_count, 'neg_count': neg_count}
        )
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """批量分析"""
        return [self.analyze(text) for text in texts]


class BertAnalyzer(BaseSentimentAnalyzer):
    """BERT情感分析器"""
    
    def __init__(self, model_name: str = "bert-base-chinese"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.device = None
        self._initialized = False
    
    def initialize(self):
        """初始化模型（延迟加载）"""
        if self._initialized:
            return
        
        try:
            import torch
            from transformers import BertTokenizer, BertForSequenceClassification
            
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
            self.model = BertForSequenceClassification.from_pretrained(
                self.model_name, num_labels=3
            )
            self.model.to(self.device)
            self.model.eval()
            self._initialized = True
            logger.info(f"BERT模型加载成功: {self.model_name}, 设备: {self.device}")
        except Exception as e:
            logger.error(f"BERT模型加载失败: {e}")
            self._initialized = False
    
    def analyze(self, text: str) -> SentimentResult:
        """BERT分析"""
        if not self._initialized:
            self.initialize()
        
        if not self._initialized or not text:
            # 降级到词典方法
            return LexiconAnalyzer().analyze(text)
        
        try:
            import torch
            import torch.nn.functional as F
            
            inputs = self.tokenizer(
                text, return_tensors='pt', truncation=True,
                max_length=128, padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1)
                pred = torch.argmax(probs, dim=-1).item()
                confidence = probs[0][pred].item()
            
            sentiment_map = {0: 'negative', 1: 'neutral', 2: 'positive'}
            score_map = {0: -0.8, 1: 0.0, 2: 0.8}
            
            return SentimentResult(
                text=text,
                sentiment=sentiment_map[pred],
                score=score_map[pred],
                confidence=round(confidence, 3),
                method='bert',
                details={'probs': probs[0].tolist()}
            )
        except Exception as e:
            logger.error(f"BERT分析失败: {e}")
            return LexiconAnalyzer().analyze(text)
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """批量分析"""
        return [self.analyze(text) for text in texts]


class HybridAnalyzer(BaseSentimentAnalyzer):
    """混合情感分析器（推荐使用）"""
    
    def __init__(self, bert_weight: float = 0.7):
        self.lexicon = LexiconAnalyzer()
        self.bert = BertAnalyzer()
        self.bert_weight = bert_weight
        self.lexicon_weight = 1 - bert_weight
    
    def analyze(self, text: str) -> SentimentResult:
        """混合分析"""
        lexicon_result = self.lexicon.analyze(text)
        
        # 简单文本使用词典方法
        if len(text) < 10 or lexicon_result.confidence > 0.8:
            return lexicon_result
        
        # 复杂文本尝试BERT
        try:
            bert_result = self.bert.analyze(text)
            
            # 加权融合
            combined_score = (
                self.bert_weight * bert_result.score +
                self.lexicon_weight * lexicon_result.score
            )
            combined_confidence = (
                self.bert_weight * bert_result.confidence +
                self.lexicon_weight * lexicon_result.confidence
            )
            
            if combined_score > 0.2:
                sentiment = 'positive'
            elif combined_score < -0.2:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            return SentimentResult(
                text=text,
                sentiment=sentiment,
                score=round(combined_score, 3),
                confidence=round(combined_confidence, 3),
                method='hybrid',
                details={
                    'lexicon': lexicon_result.score,
                    'bert': bert_result.score
                }
            )
        except Exception:
            return lexicon_result
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """批量分析"""
        return [self.analyze(text) for text in texts]


class UnifiedSentimentService:
    """统一情感分析服务"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.analyzers = {
            AnalysisMethod.LEXICON: LexiconAnalyzer(),
            AnalysisMethod.HYBRID: HybridAnalyzer(),
        }
        self._initialized = True
        logger.info("统一情感分析服务初始化完成")
    
    def analyze(
        self,
        text: str,
        method: AnalysisMethod = AnalysisMethod.HYBRID
    ) -> SentimentResult:
        """分析单条文本"""
        analyzer = self.analyzers.get(method, self.analyzers[AnalysisMethod.HYBRID])
        return analyzer.analyze(text)
    
    def analyze_batch(
        self,
        texts: List[str],
        method: AnalysisMethod = AnalysisMethod.HYBRID
    ) -> List[SentimentResult]:
        """批量分析"""
        analyzer = self.analyzers.get(method, self.analyzers[AnalysisMethod.HYBRID])
        return analyzer.analyze_batch(texts)
    
    def get_sentiment_distribution(
        self,
        results: List[SentimentResult]
    ) -> Dict[str, int]:
        """统计情感分布"""
        distribution = {'positive': 0, 'negative': 0, 'neutral': 0}
        for result in results:
            distribution[result.sentiment] += 1
        return distribution


# 便捷函数
def analyze_text(text: str, method: str = 'hybrid') -> Dict[str, Any]:
    """分析单条文本（便捷函数）"""
    service = UnifiedSentimentService()
    method_enum = AnalysisMethod(method) if method in [m.value for m in AnalysisMethod] else AnalysisMethod.HYBRID
    result = service.analyze(text, method_enum)
    return {
        'text': result.text,
        'sentiment': result.sentiment,
        'score': result.score,
        'confidence': result.confidence,
        'method': result.method
    }


def analyze_texts_batch(texts: List[str], method: str = 'hybrid') -> List[Dict[str, Any]]:
    """批量分析（便捷函数）"""
    service = UnifiedSentimentService()
    method_enum = AnalysisMethod(method) if method in [m.value for m in AnalysisMethod] else AnalysisMethod.HYBRID
    results = service.analyze_batch(texts, method_enum)
    return [
        {
            'text': r.text,
            'sentiment': r.sentiment,
            'score': r.score,
            'confidence': r.confidence,
            'method': r.method
        }
        for r in results
    ]
