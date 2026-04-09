"""
模型评估模块

提供完整的模型效果验证指标：
1. 情感分析评估：准确率、召回率、F1、混淆矩阵
2. 热度预测评估：MAE、RMSE、相关系数
3. 排序模型评估：NDCG、MAP、MRR
4. 四象限分类评估：多分类指标
5. 综合评估报告生成

作者：毕业设计
日期：2024-12
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import math
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 数据类定义 ====================

@dataclass
class SentimentMetrics:
    """情感分析评估指标"""
    accuracy: float = 0.0
    precision: Dict[str, float] = field(default_factory=dict)
    recall: Dict[str, float] = field(default_factory=dict)
    f1_score: Dict[str, float] = field(default_factory=dict)
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    weighted_f1: float = 0.0
    confusion_matrix: List[List[int]] = field(default_factory=list)
    classification_report: str = ""


@dataclass
class RankingMetrics:
    """排序模型评估指标"""
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)
    map_score: float = 0.0  # Mean Average Precision
    mrr: float = 0.0  # Mean Reciprocal Rank
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    spearman_correlation: float = 0.0
    kendall_tau: float = 0.0


@dataclass
class RegressionMetrics:
    """回归评估指标（热度预测）"""
    mae: float = 0.0  # Mean Absolute Error
    mse: float = 0.0  # Mean Squared Error
    rmse: float = 0.0  # Root Mean Squared Error
    mape: float = 0.0  # Mean Absolute Percentage Error
    r2_score: float = 0.0  # R² 决定系数
    pearson_correlation: float = 0.0
    spearman_correlation: float = 0.0


@dataclass
class QuadrantMetrics:
    """四象限分类评估指标"""
    accuracy: float = 0.0
    per_quadrant_precision: Dict[str, float] = field(default_factory=dict)
    per_quadrant_recall: Dict[str, float] = field(default_factory=dict)
    per_quadrant_f1: Dict[str, float] = field(default_factory=dict)
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)
    cohen_kappa: float = 0.0  # 评估者一致性


@dataclass
class EvaluationReport:
    """综合评估报告"""
    sentiment_metrics: SentimentMetrics = field(default_factory=SentimentMetrics)
    ranking_metrics: RankingMetrics = field(default_factory=RankingMetrics)
    heat_metrics: RegressionMetrics = field(default_factory=RegressionMetrics)
    quadrant_metrics: QuadrantMetrics = field(default_factory=QuadrantMetrics)
    timestamp: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)


# ==================== 情感分析评估 ====================

class SentimentEvaluator:
    """
    情感分析模型评估器
    
    支持二分类和多分类评估
    """
    
    LABELS = ['positive', 'neutral', 'negative']
    
    @staticmethod
    def calculate_accuracy(y_true: List[str], y_pred: List[str]) -> float:
        """计算准确率"""
        if len(y_true) != len(y_pred) or len(y_true) == 0:
            return 0.0
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        return correct / len(y_true)
    
    @staticmethod
    def calculate_precision_recall_f1(
        y_true: List[str], 
        y_pred: List[str],
        labels: List[str] = None
    ) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        """
        计算每个类别的精确率、召回率、F1
        
        Precision = TP / (TP + FP)
        Recall = TP / (TP + FN)
        F1 = 2 * Precision * Recall / (Precision + Recall)
        """
        labels = labels or SentimentEvaluator.LABELS
        
        precision = {}
        recall = {}
        f1 = {}
        
        for label in labels:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
            
            precision[label] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall[label] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            
            if precision[label] + recall[label] > 0:
                f1[label] = 2 * precision[label] * recall[label] / (precision[label] + recall[label])
            else:
                f1[label] = 0.0
        
        return precision, recall, f1
    
    @staticmethod
    def calculate_confusion_matrix(
        y_true: List[str], 
        y_pred: List[str],
        labels: List[str] = None
    ) -> List[List[int]]:
        """
        计算混淆矩阵
        
        返回格式：matrix[i][j] = 真实类别i被预测为类别j的数量
        """
        labels = labels or SentimentEvaluator.LABELS
        label_to_idx = {label: idx for idx, label in enumerate(labels)}
        
        n = len(labels)
        matrix = [[0] * n for _ in range(n)]
        
        for t, p in zip(y_true, y_pred):
            if t in label_to_idx and p in label_to_idx:
                matrix[label_to_idx[t]][label_to_idx[p]] += 1
        
        return matrix
    
    @staticmethod
    def calculate_macro_metrics(
        precision: Dict[str, float],
        recall: Dict[str, float],
        f1: Dict[str, float]
    ) -> Tuple[float, float, float]:
        """计算宏平均指标"""
        macro_p = np.mean(list(precision.values()))
        macro_r = np.mean(list(recall.values()))
        macro_f1 = np.mean(list(f1.values()))
        return macro_p, macro_r, macro_f1
    
    @staticmethod
    def calculate_weighted_f1(
        y_true: List[str],
        f1: Dict[str, float],
        labels: List[str] = None
    ) -> float:
        """计算加权F1（按类别样本数加权）"""
        labels = labels or SentimentEvaluator.LABELS
        
        # 计算每个类别的样本数
        class_counts = defaultdict(int)
        for t in y_true:
            class_counts[t] += 1
        
        total = len(y_true)
        weighted_f1 = sum(
            f1.get(label, 0) * class_counts[label] / total
            for label in labels
        )
        
        return weighted_f1
    
    @classmethod
    def evaluate(cls, y_true: List[str], y_pred: List[str]) -> SentimentMetrics:
        """
        完整评估情感分析模型
        
        Args:
            y_true: 真实标签列表
            y_pred: 预测标签列表
            
        Returns:
            SentimentMetrics: 评估指标
        """
        metrics = SentimentMetrics()
        
        # 准确率
        metrics.accuracy = cls.calculate_accuracy(y_true, y_pred)
        
        # 精确率、召回率、F1
        metrics.precision, metrics.recall, metrics.f1_score = \
            cls.calculate_precision_recall_f1(y_true, y_pred)
        
        # 宏平均
        metrics.macro_precision, metrics.macro_recall, metrics.macro_f1 = \
            cls.calculate_macro_metrics(metrics.precision, metrics.recall, metrics.f1_score)
        
        # 加权F1
        metrics.weighted_f1 = cls.calculate_weighted_f1(y_true, metrics.f1_score)
        
        # 混淆矩阵
        metrics.confusion_matrix = cls.calculate_confusion_matrix(y_true, y_pred)
        
        # 生成分类报告
        metrics.classification_report = cls._generate_report(metrics)
        
        return metrics
    
    @staticmethod
    def _generate_report(metrics: SentimentMetrics) -> str:
        """生成分类报告字符串"""
        lines = [
            "=" * 60,
            "情感分析评估报告",
            "=" * 60,
            f"{'类别':<12} {'精确率':<12} {'召回率':<12} {'F1分数':<12}",
            "-" * 60,
        ]
        
        for label in SentimentEvaluator.LABELS:
            p = metrics.precision.get(label, 0)
            r = metrics.recall.get(label, 0)
            f = metrics.f1_score.get(label, 0)
            lines.append(f"{label:<12} {p:<12.4f} {r:<12.4f} {f:<12.4f}")
        
        lines.extend([
            "-" * 60,
            f"{'宏平均':<12} {metrics.macro_precision:<12.4f} "
            f"{metrics.macro_recall:<12.4f} {metrics.macro_f1:<12.4f}",
            f"{'加权F1':<12} {'':<12} {'':<12} {metrics.weighted_f1:<12.4f}",
            "-" * 60,
            f"准确率: {metrics.accuracy:.4f}",
            "=" * 60,
        ])
        
        return "\n".join(lines)


# ==================== 排序模型评估 ====================

class RankingEvaluator:
    """
    排序模型评估器
    
    评估双维度排序模型的排序质量
    """
    
    @staticmethod
    def calculate_dcg(relevances: List[float], k: int = None) -> float:
        """
        计算DCG (Discounted Cumulative Gain)
        
        DCG@k = Σ(i=1 to k) (2^rel_i - 1) / log2(i + 1)
        
        Args:
            relevances: 相关性得分列表（按预测排序）
            k: 截断位置
        """
        if k is None:
            k = len(relevances)
        k = min(k, len(relevances))
        
        dcg = 0.0
        for i in range(k):
            rel = relevances[i]
            # 使用 log2(i + 2) 因为位置从0开始
            dcg += (2 ** rel - 1) / math.log2(i + 2)
        
        return dcg
    
    @staticmethod
    def calculate_ndcg(
        predicted_ranking: List[Any],
        relevance_scores: Dict[Any, float],
        k: int = None
    ) -> float:
        """
        计算NDCG (Normalized Discounted Cumulative Gain)
        
        NDCG@k = DCG@k / IDCG@k
        
        Args:
            predicted_ranking: 预测的排序列表（item IDs）
            relevance_scores: 每个item的真实相关性得分
            k: 截断位置
            
        Returns:
            NDCG分数 (0-1)
        """
        if not predicted_ranking or not relevance_scores:
            return 0.0
        
        if k is None:
            k = len(predicted_ranking)
        k = min(k, len(predicted_ranking))
        
        # 获取预测排序的相关性得分
        pred_relevances = [
            relevance_scores.get(item, 0.0) 
            for item in predicted_ranking[:k]
        ]
        
        # 计算DCG
        dcg = RankingEvaluator.calculate_dcg(pred_relevances, k)
        
        # 计算理想排序的IDCG
        ideal_relevances = sorted(relevance_scores.values(), reverse=True)[:k]
        idcg = RankingEvaluator.calculate_dcg(ideal_relevances, k)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    @staticmethod
    def calculate_map(
        predicted_rankings: List[List[Any]],
        relevant_items: List[set]
    ) -> float:
        """
        计算MAP (Mean Average Precision)
        
        MAP = (1/Q) * Σ(q=1 to Q) AP(q)
        AP = (1/|R|) * Σ(k=1 to n) P(k) * rel(k)
        
        Args:
            predicted_rankings: 多个查询的预测排序列表
            relevant_items: 每个查询的相关项集合
        """
        if not predicted_rankings or not relevant_items:
            return 0.0
        
        average_precisions = []
        
        for ranking, relevant in zip(predicted_rankings, relevant_items):
            if not relevant:
                continue
            
            hits = 0
            precision_sum = 0.0
            
            for i, item in enumerate(ranking):
                if item in relevant:
                    hits += 1
                    precision_at_i = hits / (i + 1)
                    precision_sum += precision_at_i
            
            ap = precision_sum / len(relevant) if relevant else 0.0
            average_precisions.append(ap)
        
        return np.mean(average_precisions) if average_precisions else 0.0
    
    @staticmethod
    def calculate_mrr(
        predicted_rankings: List[List[Any]],
        relevant_items: List[set]
    ) -> float:
        """
        计算MRR (Mean Reciprocal Rank)
        
        MRR = (1/Q) * Σ(q=1 to Q) (1/rank_q)
        
        Args:
            predicted_rankings: 多个查询的预测排序列表
            relevant_items: 每个查询的相关项集合
        """
        if not predicted_rankings or not relevant_items:
            return 0.0
        
        reciprocal_ranks = []
        
        for ranking, relevant in zip(predicted_rankings, relevant_items):
            for i, item in enumerate(ranking):
                if item in relevant:
                    reciprocal_ranks.append(1.0 / (i + 1))
                    break
            else:
                reciprocal_ranks.append(0.0)
        
        return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    
    @staticmethod
    def calculate_precision_at_k(
        predicted_ranking: List[Any],
        relevant_items: set,
        k: int
    ) -> float:
        """计算Precision@K"""
        if not predicted_ranking or not relevant_items:
            return 0.0
        
        k = min(k, len(predicted_ranking))
        hits = sum(1 for item in predicted_ranking[:k] if item in relevant_items)
        return hits / k
    
    @staticmethod
    def calculate_recall_at_k(
        predicted_ranking: List[Any],
        relevant_items: set,
        k: int
    ) -> float:
        """计算Recall@K"""
        if not predicted_ranking or not relevant_items:
            return 0.0
        
        k = min(k, len(predicted_ranking))
        hits = sum(1 for item in predicted_ranking[:k] if item in relevant_items)
        return hits / len(relevant_items) if relevant_items else 0.0
    
    @staticmethod
    def calculate_spearman_correlation(
        ranking1: List[Any],
        ranking2: List[Any]
    ) -> float:
        """
        计算Spearman等级相关系数
        
        评估两个排序的相关性
        """
        if len(ranking1) != len(ranking2) or len(ranking1) == 0:
            return 0.0
        
        n = len(ranking1)
        
        # 创建排名映射
        rank1 = {item: i for i, item in enumerate(ranking1)}
        rank2 = {item: i for i, item in enumerate(ranking2)}
        
        # 计算排名差的平方和
        d_squared_sum = sum(
            (rank1.get(item, n) - rank2.get(item, n)) ** 2
            for item in set(ranking1) | set(ranking2)
        )
        
        # Spearman公式
        rho = 1 - (6 * d_squared_sum) / (n * (n ** 2 - 1))
        
        return rho
    
    @classmethod
    def evaluate(
        cls,
        predicted_ranking: List[Any],
        relevance_scores: Dict[Any, float],
        relevant_items: set = None,
        k_values: List[int] = None
    ) -> RankingMetrics:
        """
        完整评估排序模型
        
        Args:
            predicted_ranking: 预测的排序列表
            relevance_scores: 真实相关性得分
            relevant_items: 相关项集合（用于P@K, R@K）
            k_values: 要计算的K值列表
        """
        metrics = RankingMetrics()
        k_values = k_values or [5, 10, 20]
        
        # NDCG@K
        for k in k_values:
            metrics.ndcg_at_k[k] = cls.calculate_ndcg(
                predicted_ranking, relevance_scores, k
            )
        
        # 如果提供了相关项集合
        if relevant_items:
            # Precision@K 和 Recall@K
            for k in k_values:
                metrics.precision_at_k[k] = cls.calculate_precision_at_k(
                    predicted_ranking, relevant_items, k
                )
                metrics.recall_at_k[k] = cls.calculate_recall_at_k(
                    predicted_ranking, relevant_items, k
                )
        
        # Spearman相关系数
        ideal_ranking = sorted(
            relevance_scores.keys(),
            key=lambda x: relevance_scores[x],
            reverse=True
        )
        metrics.spearman_correlation = cls.calculate_spearman_correlation(
            predicted_ranking, ideal_ranking
        )
        
        return metrics


# ==================== 回归评估（热度预测）====================

class RegressionEvaluator:
    """
    回归模型评估器
    
    用于评估热度预测的准确性
    """
    
    @staticmethod
    def calculate_mae(y_true: List[float], y_pred: List[float]) -> float:
        """
        计算MAE (Mean Absolute Error)
        
        MAE = (1/n) * Σ|y_true - y_pred|
        """
        if len(y_true) != len(y_pred) or len(y_true) == 0:
            return 0.0
        return np.mean(np.abs(np.array(y_true) - np.array(y_pred)))
    
    @staticmethod
    def calculate_mse(y_true: List[float], y_pred: List[float]) -> float:
        """
        计算MSE (Mean Squared Error)
        
        MSE = (1/n) * Σ(y_true - y_pred)²
        """
        if len(y_true) != len(y_pred) or len(y_true) == 0:
            return 0.0
        return np.mean((np.array(y_true) - np.array(y_pred)) ** 2)
    
    @staticmethod
    def calculate_rmse(y_true: List[float], y_pred: List[float]) -> float:
        """
        计算RMSE (Root Mean Squared Error)
        
        RMSE = √MSE
        """
        return np.sqrt(RegressionEvaluator.calculate_mse(y_true, y_pred))
    
    @staticmethod
    def calculate_mape(y_true: List[float], y_pred: List[float]) -> float:
        """
        计算MAPE (Mean Absolute Percentage Error)
        
        MAPE = (1/n) * Σ|y_true - y_pred| / |y_true| * 100
        """
        if len(y_true) != len(y_pred) or len(y_true) == 0:
            return 0.0
        
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # 避免除零
        mask = y_true != 0
        if not np.any(mask):
            return 0.0
        
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    
    @staticmethod
    def calculate_r2(y_true: List[float], y_pred: List[float]) -> float:
        """
        计算R² (决定系数)
        
        R² = 1 - SS_res / SS_tot
        SS_res = Σ(y_true - y_pred)²
        SS_tot = Σ(y_true - y_mean)²
        """
        if len(y_true) != len(y_pred) or len(y_true) == 0:
            return 0.0
        
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        
        if ss_tot == 0:
            return 0.0
        
        return 1 - (ss_res / ss_tot)
    
    @staticmethod
    def calculate_pearson_correlation(
        y_true: List[float], 
        y_pred: List[float]
    ) -> float:
        """计算Pearson相关系数"""
        if len(y_true) != len(y_pred) or len(y_true) < 2:
            return 0.0
        
        return np.corrcoef(y_true, y_pred)[0, 1]
    
    @classmethod
    def evaluate(cls, y_true: List[float], y_pred: List[float]) -> RegressionMetrics:
        """完整评估回归模型"""
        metrics = RegressionMetrics()
        
        metrics.mae = cls.calculate_mae(y_true, y_pred)
        metrics.mse = cls.calculate_mse(y_true, y_pred)
        metrics.rmse = cls.calculate_rmse(y_true, y_pred)
        metrics.mape = cls.calculate_mape(y_true, y_pred)
        metrics.r2_score = cls.calculate_r2(y_true, y_pred)
        metrics.pearson_correlation = cls.calculate_pearson_correlation(y_true, y_pred)
        
        return metrics


# ==================== 四象限分类评估 ====================

class QuadrantEvaluator:
    """
    四象限分类评估器
    
    评估双维度模型的四象限分类效果
    """
    
    QUADRANTS = [
        'high_sentiment_high_heat',
        'high_sentiment_low_heat',
        'low_sentiment_high_heat',
        'low_sentiment_low_heat'
    ]
    
    QUADRANT_NAMES = {
        'high_sentiment_high_heat': '重点关注',
        'high_sentiment_low_heat': '潜在风险',
        'low_sentiment_high_heat': '热门中性',
        'low_sentiment_low_heat': '一般内容'
    }
    
    @staticmethod
    def calculate_cohen_kappa(y_true: List[str], y_pred: List[str]) -> float:
        """
        计算Cohen's Kappa系数
        
        评估分类一致性，考虑随机一致性
        κ = (p_o - p_e) / (1 - p_e)
        """
        if len(y_true) != len(y_pred) or len(y_true) == 0:
            return 0.0
        
        n = len(y_true)
        labels = list(set(y_true) | set(y_pred))
        
        # 计算观察一致性 p_o
        p_o = sum(1 for t, p in zip(y_true, y_pred) if t == p) / n
        
        # 计算期望一致性 p_e
        p_e = 0.0
        for label in labels:
            true_count = sum(1 for t in y_true if t == label)
            pred_count = sum(1 for p in y_pred if p == label)
            p_e += (true_count / n) * (pred_count / n)
        
        if p_e == 1:
            return 1.0
        
        return (p_o - p_e) / (1 - p_e)
    
    @classmethod
    def evaluate(cls, y_true: List[str], y_pred: List[str]) -> QuadrantMetrics:
        """完整评估四象限分类"""
        metrics = QuadrantMetrics()
        
        # 准确率
        metrics.accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
        
        # 每个象限的指标
        for quadrant in cls.QUADRANTS:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == quadrant and p == quadrant)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != quadrant and p == quadrant)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == quadrant and p != quadrant)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            metrics.per_quadrant_precision[quadrant] = precision
            metrics.per_quadrant_recall[quadrant] = recall
            metrics.per_quadrant_f1[quadrant] = f1
        
        # 混淆矩阵
        for true_q in cls.QUADRANTS:
            metrics.confusion_matrix[true_q] = {}
            for pred_q in cls.QUADRANTS:
                count = sum(1 for t, p in zip(y_true, y_pred) if t == true_q and p == pred_q)
                metrics.confusion_matrix[true_q][pred_q] = count
        
        # Cohen's Kappa
        metrics.cohen_kappa = cls.calculate_cohen_kappa(y_true, y_pred)
        
        return metrics


# ==================== 综合评估模块 ====================

class ModelEvaluation:
    """
    模型综合评估模块
    
    整合所有评估指标，生成完整评估报告
    """
    
    def __init__(self):
        self.sentiment_evaluator = SentimentEvaluator()
        self.ranking_evaluator = RankingEvaluator()
        self.regression_evaluator = RegressionEvaluator()
        self.quadrant_evaluator = QuadrantEvaluator()
    
    def evaluate_sentiment_model(
        self,
        y_true: List[str],
        y_pred: List[str]
    ) -> SentimentMetrics:
        """评估情感分析模型"""
        return SentimentEvaluator.evaluate(y_true, y_pred)
    
    def evaluate_dual_dimension_model(
        self,
        predictions: List[Dict],
        ground_truth: List[Dict]
    ) -> EvaluationReport:
        """
        评估双维度模型效果
        
        Args:
            predictions: 预测结果列表，每项包含:
                - id: 数据ID
                - sentiment: 情感标签
                - sentiment_score: 情感得分
                - heat_score: 热度得分
                - dual_score: 双维度得分
                - quadrant: 四象限分类
                - rank: 排名
            ground_truth: 真实标签列表，格式同上
            
        Returns:
            EvaluationReport: 完整评估报告
        """
        report = EvaluationReport()
        report.timestamp = datetime.now().isoformat()
        
        # 1. 情感分析评估
        y_true_sentiment = [gt['sentiment'] for gt in ground_truth]
        y_pred_sentiment = [pred['sentiment'] for pred in predictions]
        report.sentiment_metrics = SentimentEvaluator.evaluate(
            y_true_sentiment, y_pred_sentiment
        )
        
        # 2. 热度预测评估
        y_true_heat = [gt['heat_score'] for gt in ground_truth]
        y_pred_heat = [pred['heat_score'] for pred in predictions]
        report.heat_metrics = RegressionEvaluator.evaluate(y_true_heat, y_pred_heat)
        
        # 3. 排序模型评估
        predicted_ranking = [pred['id'] for pred in sorted(
            predictions, key=lambda x: x['dual_score'], reverse=True
        )]
        relevance_scores = {gt['id']: gt['dual_score'] for gt in ground_truth}
        
        # 定义相关项（如双维度得分 > 0.7 的项）
        relevant_items = {
            gt['id'] for gt in ground_truth 
            if gt['dual_score'] > 0.7
        }
        
        report.ranking_metrics = RankingEvaluator.evaluate(
            predicted_ranking, relevance_scores, relevant_items
        )
        
        # 4. 四象限分类评估
        y_true_quadrant = [gt['quadrant'] for gt in ground_truth]
        y_pred_quadrant = [pred['quadrant'] for pred in predictions]
        report.quadrant_metrics = QuadrantEvaluator.evaluate(
            y_true_quadrant, y_pred_quadrant
        )
        
        # 5. 生成摘要
        report.summary = self._generate_summary(report)
        
        return report
    
    def calculate_ndcg(
        self,
        predicted_ranking: List[Any],
        ideal_ranking: List[Any],
        k: int = 10
    ) -> float:
        """
        计算NDCG - 评估排序质量
        
        Args:
            predicted_ranking: 预测排序（item IDs）
            ideal_ranking: 理想排序（item IDs）
            k: 截断位置
            
        Returns:
            NDCG@k 分数
        """
        # 将理想排序转换为相关性得分
        relevance_scores = {
            item: len(ideal_ranking) - i 
            for i, item in enumerate(ideal_ranking)
        }
        
        return RankingEvaluator.calculate_ndcg(
            predicted_ranking, relevance_scores, k
        )
    
    def _generate_summary(self, report: EvaluationReport) -> Dict[str, Any]:
        """生成评估摘要"""
        return {
            'overall_score': self._calculate_overall_score(report),
            'sentiment_accuracy': report.sentiment_metrics.accuracy,
            'sentiment_macro_f1': report.sentiment_metrics.macro_f1,
            'heat_r2': report.heat_metrics.r2_score,
            'heat_correlation': report.heat_metrics.pearson_correlation,
            'ranking_ndcg_10': report.ranking_metrics.ndcg_at_k.get(10, 0),
            'ranking_spearman': report.ranking_metrics.spearman_correlation,
            'quadrant_accuracy': report.quadrant_metrics.accuracy,
            'quadrant_kappa': report.quadrant_metrics.cohen_kappa,
            'recommendations': self._generate_recommendations(report),
        }
    
    def _calculate_overall_score(self, report: EvaluationReport) -> float:
        """计算综合评分（0-100）"""
        weights = {
            'sentiment': 0.3,
            'heat': 0.2,
            'ranking': 0.3,
            'quadrant': 0.2,
        }
        
        sentiment_score = report.sentiment_metrics.macro_f1 * 100
        heat_score = max(0, report.heat_metrics.r2_score) * 100
        ranking_score = report.ranking_metrics.ndcg_at_k.get(10, 0) * 100
        quadrant_score = report.quadrant_metrics.accuracy * 100
        
        overall = (
            weights['sentiment'] * sentiment_score +
            weights['heat'] * heat_score +
            weights['ranking'] * ranking_score +
            weights['quadrant'] * quadrant_score
        )
        
        return round(overall, 2)
    
    def _generate_recommendations(self, report: EvaluationReport) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 情感分析建议
        if report.sentiment_metrics.macro_f1 < 0.7:
            recommendations.append("情感分析F1较低，建议增加训练数据或调整模型参数")
        
        # 热度预测建议
        if report.heat_metrics.r2_score < 0.5:
            recommendations.append("热度预测R²较低，建议增加特征或使用更复杂的模型")
        
        # 排序建议
        if report.ranking_metrics.ndcg_at_k.get(10, 0) < 0.7:
            recommendations.append("排序NDCG@10较低，建议调整双维度权重参数")
        
        # 四象限分类建议
        if report.quadrant_metrics.accuracy < 0.7:
            recommendations.append("四象限分类准确率较低，建议调整阈值参数")
        
        if not recommendations:
            recommendations.append("模型表现良好，可以进行部署")
        
        return recommendations
    
    def export_report(
        self,
        report: EvaluationReport,
        output_path: str = None
    ) -> str:
        """
        导出评估报告
        
        Args:
            report: 评估报告
            output_path: 输出路径（可选）
            
        Returns:
            JSON格式的报告字符串
        """
        report_dict = {
            'timestamp': report.timestamp,
            'summary': report.summary,
            'sentiment_metrics': {
                'accuracy': report.sentiment_metrics.accuracy,
                'precision': report.sentiment_metrics.precision,
                'recall': report.sentiment_metrics.recall,
                'f1_score': report.sentiment_metrics.f1_score,
                'macro_f1': report.sentiment_metrics.macro_f1,
                'weighted_f1': report.sentiment_metrics.weighted_f1,
                'confusion_matrix': report.sentiment_metrics.confusion_matrix,
            },
            'heat_metrics': {
                'mae': report.heat_metrics.mae,
                'rmse': report.heat_metrics.rmse,
                'mape': report.heat_metrics.mape,
                'r2_score': report.heat_metrics.r2_score,
                'pearson_correlation': report.heat_metrics.pearson_correlation,
            },
            'ranking_metrics': {
                'ndcg_at_k': report.ranking_metrics.ndcg_at_k,
                'precision_at_k': report.ranking_metrics.precision_at_k,
                'recall_at_k': report.ranking_metrics.recall_at_k,
                'spearman_correlation': report.ranking_metrics.spearman_correlation,
            },
            'quadrant_metrics': {
                'accuracy': report.quadrant_metrics.accuracy,
                'per_quadrant_f1': report.quadrant_metrics.per_quadrant_f1,
                'cohen_kappa': report.quadrant_metrics.cohen_kappa,
                'confusion_matrix': report.quadrant_metrics.confusion_matrix,
            },
        }
        
        json_str = json.dumps(report_dict, indent=2, ensure_ascii=False)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"评估报告已导出: {output_path}")
        
        return json_str


# ==================== 便捷函数 ====================

def evaluate_sentiment(y_true: List[str], y_pred: List[str]) -> SentimentMetrics:
    """快速评估情感分析"""
    return SentimentEvaluator.evaluate(y_true, y_pred)


def evaluate_ranking(
    predicted_ranking: List[Any],
    relevance_scores: Dict[Any, float],
    k: int = 10
) -> float:
    """快速计算NDCG@K"""
    return RankingEvaluator.calculate_ndcg(predicted_ranking, relevance_scores, k)


def evaluate_regression(y_true: List[float], y_pred: List[float]) -> RegressionMetrics:
    """快速评估回归模型"""
    return RegressionEvaluator.evaluate(y_true, y_pred)


def evaluate_quadrant(y_true: List[str], y_pred: List[str]) -> QuadrantMetrics:
    """快速评估四象限分类"""
    return QuadrantEvaluator.evaluate(y_true, y_pred)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 70)
    print("模型评估模块测试")
    print("=" * 70)
    
    # 1. 测试情感分析评估
    print("\n1. 情感分析评估测试")
    print("-" * 50)
    
    y_true_sentiment = ['positive', 'negative', 'neutral', 'positive', 'negative',
                        'positive', 'neutral', 'negative', 'positive', 'neutral']
    y_pred_sentiment = ['positive', 'negative', 'positive', 'positive', 'neutral',
                        'positive', 'neutral', 'negative', 'negative', 'neutral']
    
    sentiment_metrics = evaluate_sentiment(y_true_sentiment, y_pred_sentiment)
    print(sentiment_metrics.classification_report)
    
    # 2. 测试排序评估
    print("\n2. 排序模型评估测试")
    print("-" * 50)
    
    predicted_ranking = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    relevance_scores = {
        'a': 3, 'b': 2, 'c': 3, 'd': 0, 'e': 1,
        'f': 2, 'g': 3, 'h': 0, 'i': 1, 'j': 2
    }
    
    ndcg_5 = evaluate_ranking(predicted_ranking, relevance_scores, k=5)
    ndcg_10 = evaluate_ranking(predicted_ranking, relevance_scores, k=10)
    print(f"NDCG@5: {ndcg_5:.4f}")
    print(f"NDCG@10: {ndcg_10:.4f}")
    
    # 3. 测试热度预测评估
    print("\n3. 热度预测评估测试")
    print("-" * 50)
    
    y_true_heat = [100, 200, 150, 300, 250, 180, 220, 280, 190, 240]
    y_pred_heat = [110, 190, 160, 280, 260, 170, 230, 290, 180, 250]
    
    heat_metrics = evaluate_regression(y_true_heat, y_pred_heat)
    print(f"MAE: {heat_metrics.mae:.4f}")
    print(f"RMSE: {heat_metrics.rmse:.4f}")
    print(f"R²: {heat_metrics.r2_score:.4f}")
    print(f"Pearson相关系数: {heat_metrics.pearson_correlation:.4f}")
    
    # 4. 测试四象限分类评估
    print("\n4. 四象限分类评估测试")
    print("-" * 50)
    
    y_true_quadrant = [
        'high_sentiment_high_heat', 'low_sentiment_low_heat',
        'high_sentiment_low_heat', 'low_sentiment_high_heat',
        'high_sentiment_high_heat', 'low_sentiment_low_heat',
        'high_sentiment_low_heat', 'low_sentiment_high_heat',
        'high_sentiment_high_heat', 'low_sentiment_low_heat',
    ]
    y_pred_quadrant = [
        'high_sentiment_high_heat', 'low_sentiment_low_heat',
        'high_sentiment_high_heat', 'low_sentiment_high_heat',
        'high_sentiment_high_heat', 'high_sentiment_low_heat',
        'high_sentiment_low_heat', 'low_sentiment_high_heat',
        'low_sentiment_high_heat', 'low_sentiment_low_heat',
    ]
    
    quadrant_metrics = evaluate_quadrant(y_true_quadrant, y_pred_quadrant)
    print(f"准确率: {quadrant_metrics.accuracy:.4f}")
    print(f"Cohen's Kappa: {quadrant_metrics.cohen_kappa:.4f}")
    print("各象限F1:")
    for q, f1 in quadrant_metrics.per_quadrant_f1.items():
        print(f"  {QuadrantEvaluator.QUADRANT_NAMES[q]}: {f1:.4f}")
    
    # 5. 综合评估测试
    print("\n5. 综合评估测试")
    print("-" * 50)
    
    evaluator = ModelEvaluation()
    
    # 模拟预测和真实数据
    predictions = [
        {'id': i, 'sentiment': y_pred_sentiment[i], 'heat_score': y_pred_heat[i],
         'dual_score': 0.5 + i * 0.05, 'quadrant': y_pred_quadrant[i]}
        for i in range(10)
    ]
    ground_truth = [
        {'id': i, 'sentiment': y_true_sentiment[i], 'heat_score': y_true_heat[i],
         'dual_score': 0.5 + i * 0.05, 'quadrant': y_true_quadrant[i]}
        for i in range(10)
    ]
    
    report = evaluator.evaluate_dual_dimension_model(predictions, ground_truth)
    
    print(f"综合评分: {report.summary['overall_score']}")
    print(f"情感分析准确率: {report.summary['sentiment_accuracy']:.4f}")
    print(f"热度预测R²: {report.summary['heat_r2']:.4f}")
    print(f"排序NDCG@10: {report.summary['ranking_ndcg_10']:.4f}")
    print(f"四象限准确率: {report.summary['quadrant_accuracy']:.4f}")
    print("\n优化建议:")
    for rec in report.summary['recommendations']:
        print(f"  - {rec}")
    
    print("\n" + "=" * 70)
    print("测试完成！")
