"""
模型模块

包含模型评估、训练、管理等功能
"""

from .model_evaluation import (
    ModelEvaluation,
    SentimentEvaluator,
    RankingEvaluator,
    RegressionEvaluator,
    QuadrantEvaluator,
    SentimentMetrics,
    RankingMetrics,
    RegressionMetrics,
    QuadrantMetrics,
    EvaluationReport,
    evaluate_sentiment,
    evaluate_ranking,
    evaluate_regression,
    evaluate_quadrant,
)

from .model_manager import (
    ModelManager,
    ModelStatus,
    ModelInfo,
    preload_models_on_startup,
    preload_models_sync,
    get_model_manager,
    get_sentiment_lexicon,
    get_bert_analyzer,
    get_hybrid_analyzer,
    get_dual_dimension_model,
    with_model,
    ensure_model_loaded,
)

# BERT情感分析模块（可选，需要torch和transformers）
try:
    from .chinese_bert_sentiment import (
        ChineseBertSentimentModel,
        WeiboSentimentDataset,
        ModelConfig as BertModelConfig,
        TrainingConfig,
        DataAugmentConfig,
        MetricsCalculator,
        create_model as create_bert_model,
        quick_predict as bert_quick_predict,
    )
    BERT_AVAILABLE = True
except ImportError:
    BERT_AVAILABLE = False
    ChineseBertSentimentModel = None
    WeiboSentimentDataset = None
    BertModelConfig = None
    TrainingConfig = None
    DataAugmentConfig = None
    MetricsCalculator = None
    create_bert_model = None
    bert_quick_predict = None

__all__ = [
    # 评估模块
    'ModelEvaluation',
    'SentimentEvaluator',
    'RankingEvaluator',
    'RegressionEvaluator',
    'QuadrantEvaluator',
    'SentimentMetrics',
    'RankingMetrics',
    'RegressionMetrics',
    'QuadrantMetrics',
    'EvaluationReport',
    'evaluate_sentiment',
    'evaluate_ranking',
    'evaluate_regression',
    'evaluate_quadrant',
    # 管理模块
    'ModelManager',
    'ModelStatus',
    'ModelInfo',
    'preload_models_on_startup',
    'preload_models_sync',
    'get_model_manager',
    'get_sentiment_lexicon',
    'get_bert_analyzer',
    'get_hybrid_analyzer',
    'get_dual_dimension_model',
    'with_model',
    'ensure_model_loaded',
    # BERT模块
    'BERT_AVAILABLE',
    'ChineseBertSentimentModel',
    'WeiboSentimentDataset',
    'BertModelConfig',
    'TrainingConfig',
    'DataAugmentConfig',
    'MetricsCalculator',
    'create_bert_model',
    'bert_quick_predict',
]
