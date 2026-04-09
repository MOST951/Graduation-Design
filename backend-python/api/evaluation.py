"""
模型评估API

提供模型效果验证的接口
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import sys
import os
import logging

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.model_evaluation import (
    ModelEvaluation,
    SentimentEvaluator,
    RankingEvaluator,
    RegressionEvaluator,
    QuadrantEvaluator,
)

logger = logging.getLogger(__name__)

evaluation_bp = Blueprint('evaluation', __name__, url_prefix='/api/evaluation')

# 全局评估器实例
_evaluator = ModelEvaluation()


@evaluation_bp.route('/sentiment', methods=['POST'])
def evaluate_sentiment():
    """
    评估情感分析模型
    
    Body:
        y_true: 真实标签列表
        y_pred: 预测标签列表
    """
    try:
        data = request.json
        y_true = data.get('y_true', [])
        y_pred = data.get('y_pred', [])
        
        if not y_true or not y_pred:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        if len(y_true) != len(y_pred):
            return jsonify({'code': 400, 'message': '标签长度不一致'}), 400
        
        metrics = SentimentEvaluator.evaluate(y_true, y_pred)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'accuracy': round(metrics.accuracy, 4),
                'precision': {k: round(v, 4) for k, v in metrics.precision.items()},
                'recall': {k: round(v, 4) for k, v in metrics.recall.items()},
                'f1_score': {k: round(v, 4) for k, v in metrics.f1_score.items()},
                'macro_f1': round(metrics.macro_f1, 4),
                'weighted_f1': round(metrics.weighted_f1, 4),
                'confusion_matrix': metrics.confusion_matrix,
                'report': metrics.classification_report,
            }
        })
    except Exception as e:
        logger.error(f'情感评估失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@evaluation_bp.route('/ranking', methods=['POST'])
def evaluate_ranking():
    """
    评估排序模型（NDCG）
    
    Body:
        predicted_ranking: 预测排序列表
        relevance_scores: 相关性得分字典
        k_values: K值列表（可选，默认[5,10,20]）
    """
    try:
        data = request.json
        predicted_ranking = data.get('predicted_ranking', [])
        relevance_scores = data.get('relevance_scores', {})
        k_values = data.get('k_values', [5, 10, 20])
        
        if not predicted_ranking or not relevance_scores:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        # 计算各K值的NDCG
        ndcg_results = {}
        for k in k_values:
            ndcg = RankingEvaluator.calculate_ndcg(
                predicted_ranking, relevance_scores, k
            )
            ndcg_results[f'ndcg@{k}'] = round(ndcg, 4)
        
        # 计算Spearman相关系数
        ideal_ranking = sorted(
            relevance_scores.keys(),
            key=lambda x: relevance_scores[x],
            reverse=True
        )
        spearman = RankingEvaluator.calculate_spearman_correlation(
            predicted_ranking, ideal_ranking
        )
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                **ndcg_results,
                'spearman_correlation': round(spearman, 4),
                'sample_size': len(predicted_ranking),
            }
        })
    except Exception as e:
        logger.error(f'排序评估失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@evaluation_bp.route('/regression', methods=['POST'])
def evaluate_regression():
    """
    评估回归模型（热度预测）
    
    Body:
        y_true: 真实值列表
        y_pred: 预测值列表
    """
    try:
        data = request.json
        y_true = data.get('y_true', [])
        y_pred = data.get('y_pred', [])
        
        if not y_true or not y_pred:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        metrics = RegressionEvaluator.evaluate(y_true, y_pred)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'mae': round(metrics.mae, 4),
                'mse': round(metrics.mse, 4),
                'rmse': round(metrics.rmse, 4),
                'mape': round(metrics.mape, 4),
                'r2_score': round(metrics.r2_score, 4),
                'pearson_correlation': round(metrics.pearson_correlation, 4),
                'sample_size': len(y_true),
            }
        })
    except Exception as e:
        logger.error(f'回归评估失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@evaluation_bp.route('/quadrant', methods=['POST'])
def evaluate_quadrant():
    """
    评估四象限分类
    
    Body:
        y_true: 真实象限列表
        y_pred: 预测象限列表
    """
    try:
        data = request.json
        y_true = data.get('y_true', [])
        y_pred = data.get('y_pred', [])
        
        if not y_true or not y_pred:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        metrics = QuadrantEvaluator.evaluate(y_true, y_pred)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'accuracy': round(metrics.accuracy, 4),
                'cohen_kappa': round(metrics.cohen_kappa, 4),
                'per_quadrant_precision': {k: round(v, 4) for k, v in metrics.per_quadrant_precision.items()},
                'per_quadrant_recall': {k: round(v, 4) for k, v in metrics.per_quadrant_recall.items()},
                'per_quadrant_f1': {k: round(v, 4) for k, v in metrics.per_quadrant_f1.items()},
                'confusion_matrix': metrics.confusion_matrix,
                'sample_size': len(y_true),
            }
        })
    except Exception as e:
        logger.error(f'四象限评估失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@evaluation_bp.route('/dual-dimension', methods=['POST'])
def evaluate_dual_dimension():
    """
    综合评估双维度模型
    
    Body:
        predictions: 预测结果列表
        ground_truth: 真实标签列表
    """
    try:
        data = request.json
        predictions = data.get('predictions', [])
        ground_truth = data.get('ground_truth', [])
        
        if not predictions or not ground_truth:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        
        report = _evaluator.evaluate_dual_dimension_model(predictions, ground_truth)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'timestamp': report.timestamp,
                'summary': report.summary,
                'sentiment': {
                    'accuracy': round(report.sentiment_metrics.accuracy, 4),
                    'macro_f1': round(report.sentiment_metrics.macro_f1, 4),
                },
                'heat': {
                    'rmse': round(report.heat_metrics.rmse, 4),
                    'r2': round(report.heat_metrics.r2_score, 4),
                },
                'ranking': {
                    'ndcg_10': round(report.ranking_metrics.ndcg_at_k.get(10, 0), 4),
                    'spearman': round(report.ranking_metrics.spearman_correlation, 4),
                },
                'quadrant': {
                    'accuracy': round(report.quadrant_metrics.accuracy, 4),
                    'kappa': round(report.quadrant_metrics.cohen_kappa, 4),
                },
            }
        })
    except Exception as e:
        logger.error(f'双维度评估失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@evaluation_bp.route('/metrics-explanation', methods=['GET'])
def get_metrics_explanation():
    """获取评估指标说明"""
    explanations = {
        'sentiment_metrics': {
            'accuracy': '准确率：预测正确的样本占总样本的比例',
            'precision': '精确率：预测为某类的样本中实际为该类的比例',
            'recall': '召回率：实际为某类的样本中被正确预测的比例',
            'f1_score': 'F1分数：精确率和召回率的调和平均',
            'macro_f1': '宏平均F1：各类别F1的算术平均',
            'weighted_f1': '加权F1：按类别样本数加权的F1',
        },
        'ranking_metrics': {
            'ndcg': 'NDCG (Normalized DCG)：归一化折损累积增益，评估排序质量',
            'map': 'MAP (Mean Average Precision)：平均精度均值',
            'mrr': 'MRR (Mean Reciprocal Rank)：平均倒数排名',
            'spearman': 'Spearman相关系数：评估排序相关性',
        },
        'regression_metrics': {
            'mae': 'MAE (Mean Absolute Error)：平均绝对误差',
            'rmse': 'RMSE (Root Mean Squared Error)：均方根误差',
            'mape': 'MAPE (Mean Absolute Percentage Error)：平均绝对百分比误差',
            'r2': 'R² (决定系数)：模型解释的方差比例',
            'pearson': 'Pearson相关系数：线性相关程度',
        },
        'quadrant_metrics': {
            'accuracy': '准确率：四象限分类的整体准确率',
            'cohen_kappa': "Cohen's Kappa：考虑随机一致性的分类一致性系数",
            'per_quadrant_f1': '各象限F1：每个象限的F1分数',
        },
    }
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': explanations
    })


@evaluation_bp.route('/benchmark', methods=['POST'])
def run_benchmark():
    """
    运行基准测试
    
    Body:
        num_samples: 测试样本数（默认100）
    """
    try:
        import random
        
        data = request.json or {}
        num_samples = data.get('num_samples', 100)
        
        # 生成模拟数据
        sentiments = ['positive', 'neutral', 'negative']
        quadrants = [
            'high_sentiment_high_heat', 'high_sentiment_low_heat',
            'low_sentiment_high_heat', 'low_sentiment_low_heat'
        ]
        
        predictions = []
        ground_truth = []
        
        for i in range(num_samples):
            # 模拟80%准确率
            if random.random() < 0.8:
                sentiment = random.choice(sentiments)
                quadrant = random.choice(quadrants)
                heat = random.uniform(0, 1000)
                dual_score = random.uniform(0, 1)
            else:
                sentiment = random.choice(sentiments)
                quadrant = random.choice(quadrants)
                heat = random.uniform(0, 1000)
                dual_score = random.uniform(0, 1)
            
            true_sentiment = sentiment if random.random() < 0.8 else random.choice(sentiments)
            true_quadrant = quadrant if random.random() < 0.75 else random.choice(quadrants)
            true_heat = heat * (1 + random.uniform(-0.2, 0.2))
            
            predictions.append({
                'id': i,
                'sentiment': sentiment,
                'heat_score': heat,
                'dual_score': dual_score,
                'quadrant': quadrant,
            })
            ground_truth.append({
                'id': i,
                'sentiment': true_sentiment,
                'heat_score': true_heat,
                'dual_score': dual_score * (1 + random.uniform(-0.1, 0.1)),
                'quadrant': true_quadrant,
            })
        
        # 运行评估
        report = _evaluator.evaluate_dual_dimension_model(predictions, ground_truth)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'num_samples': num_samples,
                'overall_score': report.summary['overall_score'],
                'sentiment_accuracy': round(report.sentiment_metrics.accuracy, 4),
                'sentiment_f1': round(report.sentiment_metrics.macro_f1, 4),
                'heat_r2': round(report.heat_metrics.r2_score, 4),
                'ranking_ndcg': round(report.ranking_metrics.ndcg_at_k.get(10, 0), 4),
                'quadrant_accuracy': round(report.quadrant_metrics.accuracy, 4),
                'recommendations': report.summary['recommendations'],
            }
        })
    except Exception as e:
        logger.error(f'基准测试失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@evaluation_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 200,
        'message': 'Evaluation service is running',
        'timestamp': datetime.now().isoformat(),
    })
