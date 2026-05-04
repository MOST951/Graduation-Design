"""
统一API接口
==========

整合所有核心功能的统一API

提供功能：
1. 数据采集接口
2. 情感分析接口
3. 三维度排序接口
4. 统计分析接口
5. 系统监控接口

作者：毕业设计
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
import sys
import logging
from typing import Dict, List, Any

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('UnifiedAPI')

# 创建蓝图
unified_bp = Blueprint('unified', __name__, url_prefix='/api/v2')

# 导入核心模块
try:
    from core.data_pipeline import DataPipeline, PipelineConfig
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_AVAILABLE = False
    logger.warning(f"数据流水线不可用: {e}")

try:
    from core.spark_engine import SparkEngine, SparkConfig, TriDimensionSparkConfig
    SPARK_AVAILABLE = True
except ImportError as e:
    SPARK_AVAILABLE = False
    logger.warning(f"Spark引擎不可用: {e}")

# 导入情感分析模块
try:
    from services.hybrid_analyzer import HybridSentimentAnalyzer, analyze_sentiment
    HYBRID_ANALYZER_AVAILABLE = True
except ImportError:
    HYBRID_ANALYZER_AVAILABLE = False

try:
    from spark.tri_dimension_model import rank_weibo_data, TriDimensionConfig
    TRI_DIMENSION_AVAILABLE = True
except ImportError:
    TRI_DIMENSION_AVAILABLE = False

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

# 全局实例
_pipeline = None
_spark_engine = None
_hybrid_analyzer = None


def get_pipeline() -> DataPipeline:
    """获取数据流水线实例"""
    global _pipeline
    if _pipeline is None and PIPELINE_AVAILABLE:
        _pipeline = DataPipeline()
    return _pipeline


def get_hybrid_analyzer() -> HybridSentimentAnalyzer:
    """获取混合分析器实例"""
    global _hybrid_analyzer
    if _hybrid_analyzer is None and HYBRID_ANALYZER_AVAILABLE:
        _hybrid_analyzer = HybridSentimentAnalyzer()
    return _hybrid_analyzer


# ==================== 系统状态API ====================

@unified_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    获取系统状态
    
    返回所有模块的可用性和健康状态
    """
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'modules': {
                'pipeline': PIPELINE_AVAILABLE,
                'spark': SPARK_AVAILABLE,
                'hybrid_analyzer': HYBRID_ANALYZER_AVAILABLE,
                'tri_dimension': TRI_DIMENSION_AVAILABLE,
            },
            'data_dir': DATA_DIR,
            'data_files': _count_data_files(),
            'timestamp': datetime.now().isoformat(),
        }
    })


def _count_data_files() -> Dict[str, int]:
    """统计数据文件"""
    counts = {
        'crawl_results': 0,
        'processed': 0,
        'analysis': 0,
    }
    
    try:
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('crawl_result_'):
                counts['crawl_results'] += 1
            elif filename.startswith('processed_'):
                counts['processed'] += 1
            elif filename.startswith('analysis_'):
                counts['analysis'] += 1
    except:
        pass
    
    return counts


# ==================== 数据采集API ====================

@unified_bp.route('/crawl/start', methods=['POST'])
def start_crawl():
    """
    启动数据采集
    
    Body参数:
        keywords: 关键词列表 (可选)
        crawl_hot: 是否爬取热搜 (默认true)
        pages: 每个关键词页数 (默认5)
    """
    if not PIPELINE_AVAILABLE:
        return jsonify({
            'code': 500,
            'message': '数据流水线模块不可用'
        }), 500
    
    try:
        data = request.json or {}
        keywords = data.get('keywords', [])
        crawl_hot = data.get('crawl_hot', True)
        pages = data.get('pages', 5)
        
        pipeline = get_pipeline()
        
        # 更新配置
        pipeline.config.pages_per_keyword = pages
        
        # 运行流水线
        result = pipeline.run_full_pipeline(
            keywords=keywords if keywords else None,
            crawl_hot=crawl_hot
        )
        
        return jsonify({
            'code': 200,
            'message': '采集完成',
            'data': result
        })
        
    except Exception as e:
        logger.error(f'采集失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@unified_bp.route('/crawl/hot-search', methods=['GET'])
def get_hot_search():
    """获取热搜榜"""
    if not PIPELINE_AVAILABLE:
        return jsonify({
            'code': 500,
            'message': '数据流水线模块不可用'
        }), 500
    
    try:
        pipeline = get_pipeline()
        hot_list = pipeline.crawl_hot_search()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': hot_list
        })
        
    except Exception as e:
        logger.error(f'获取热搜失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 情感分析API ====================

@unified_bp.route('/sentiment/analyze', methods=['POST'])
def analyze_text():
    """
    分析文本情感
    
    Body参数:
        text: 单条文本
        texts: 文本列表（批量分析）
        method: 分析方法 (lexicon/bert/hybrid)
        context: 上下文信息
    """
    try:
        data = request.json or {}
        text = data.get('text')
        texts = data.get('texts', [])
        method = data.get('method', 'hybrid')
        context = data.get('context', {})
        
        if text:
            # 单条分析
            if HYBRID_ANALYZER_AVAILABLE:
                analyzer = get_hybrid_analyzer()
                result = analyzer.analyze(text, context)
                return jsonify({
                    'code': 200,
                    'message': 'success',
                    'data': {
                        'text': text,
                        'sentiment': result.polarity,
                        'score': result.score,
                        'confidence': result.confidence,
                        'label': result.label,
                        'fusion_method': result.fusion_method,
                    }
                })
            else:
                # 使用简单词典方法
                from spark.sentiment_analyzer import SentimentLexicon
                sentiment, score = SentimentLexicon.analyze(text)
                return jsonify({
                    'code': 200,
                    'message': 'success',
                    'data': {
                        'text': text,
                        'sentiment': sentiment,
                        'score': round(score, 4),
                        'confidence': round(min(1.0, abs(score) + 0.3), 4),
                        'method': 'lexicon'
                    }
                })
        
        elif texts:
            # 批量分析
            results = []
            if HYBRID_ANALYZER_AVAILABLE:
                analyzer = get_hybrid_analyzer()
                for t in texts:
                    result = analyzer.analyze(t)
                    results.append({
                        'text': t,
                        'sentiment': result.polarity,
                        'score': result.score,
                        'confidence': result.confidence,
                    })
            else:
                from spark.sentiment_analyzer import SentimentLexicon
                for t in texts:
                    sentiment, score = SentimentLexicon.analyze(t)
                    results.append({
                        'text': t,
                        'sentiment': sentiment,
                        'score': round(score, 4),
                    })
            
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'results': results,
                    'total': len(results)
                }
            })
        
        else:
            return jsonify({
                'code': 400,
                'message': '请提供text或texts参数'
            }), 400
            
    except Exception as e:
        logger.error(f'情感分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@unified_bp.route('/sentiment/distribution', methods=['GET'])
def get_sentiment_distribution():
    """获取情感分布统计"""
    try:
        # 从已处理的数据中统计
        distribution = {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0}
        
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('crawl_result_') and filename.endswith('.json'):
                filepath = os.path.join(DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for item in data:
                            sentiment = item.get('sentiment')
                            if sentiment in distribution:
                                distribution[sentiment] += 1
                            distribution['total'] += 1
                except:
                    pass
        
        # 如果数据没有情感标签，进行实时分析
        if distribution['total'] == 0 or (distribution['positive'] == 0 and 
                                          distribution['negative'] == 0):
            # 重新分析
            if PIPELINE_AVAILABLE:
                pipeline = get_pipeline()
                all_data = []
                
                for filename in os.listdir(DATA_DIR):
                    if filename.startswith('crawl_result_') and filename.endswith('.json'):
                        filepath = os.path.join(DATA_DIR, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                all_data.extend(data)
                        except:
                            pass
                
                if all_data:
                    processed = pipeline.process_data(all_data[:1000])  # 限制数量
                    distribution = {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0}
                    for item in processed:
                        distribution[item.sentiment] += 1
                        distribution['total'] += 1
        
        # 计算百分比
        total = distribution['total'] or 1
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'distribution': distribution,
                'percentage': {
                    'positive': round(distribution['positive'] / total * 100, 2),
                    'neutral': round(distribution['neutral'] / total * 100, 2),
                    'negative': round(distribution['negative'] / total * 100, 2),
                }
            }
        })
        
    except Exception as e:
        logger.error(f'获取情感分布失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 三维度排序API ====================

@unified_bp.route('/ranking/tri-dimension', methods=['POST'])
def tri_dimension_ranking():
    """
    三维度排序
    
    Body参数:
        data: 微博数据列表 (可选，不传则从文件加载)
        sentiment_weight: 情感权重 (默认0.4)
        heat_weight: 热度权重 (默认0.4)
        timeliness_weight: 时效性权重 (默认0.2)
        top_k: 返回Top-K (可选)
    """
    if not TRI_DIMENSION_AVAILABLE:
        return jsonify({
            'code': 500,
            'message': '三维度排序模块不可用'
        }), 500
    
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        sentiment_weight = req_data.get('sentiment_weight', 0.4)
        heat_weight = req_data.get('heat_weight', 0.4)
        top_k = req_data.get('top_k')
        
        # 如果没有传数据，从文件加载
        if not weibo_data:
            weibo_data = _load_weibo_data()
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '没有可用的数据'
            }), 400
        
        # 执行三维度排序
        ranked_data = rank_weibo_data(
            weibo_data,
            sentiment_weight=sentiment_weight,
            heat_weight=heat_weight
        )
        
        if top_k:
            ranked_data = ranked_data[:top_k]
        
        # 统计四象限分布
        quadrant_dist = _calculate_quadrant_distribution(ranked_data)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'ranked_items': ranked_data[:100],  # 限制返回数量
                'total': len(ranked_data),
                'quadrant_distribution': quadrant_dist,
                'config': {
                    'sentiment_weight': sentiment_weight,
                    'heat_weight': heat_weight,
                }
            }
        })
        
    except Exception as e:
        logger.error(f'三维度排序失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


def _load_weibo_data() -> List[Dict]:
    """从文件加载微博数据"""
    all_data = []
    
    for filename in os.listdir(DATA_DIR):
        if filename.startswith('crawl_result_') and filename.endswith('.json'):
            filepath = os.path.join(DATA_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_data.extend(data)
            except Exception as e:
                logger.warning(f"加载文件失败 {filename}: {e}")
    
    return all_data


def _calculate_quadrant_distribution(ranked_data: List[Dict]) -> Dict[str, int]:
    """计算四象限分布"""
    distribution = {
        'high_sentiment_high_heat': 0,
        'high_sentiment_low_heat': 0,
        'low_sentiment_high_heat': 0,
        'low_sentiment_low_heat': 0,
    }
    
    if not ranked_data:
        return distribution
    
    # 计算阈值
    sentiment_scores = [abs(d.get('sentiment_score', 0)) for d in ranked_data]
    heat_scores = [d.get('heat_score', 0) for d in ranked_data]
    
    sentiment_median = sorted(sentiment_scores)[len(sentiment_scores) // 2] if sentiment_scores else 0.5
    heat_median = sorted(heat_scores)[len(heat_scores) // 2] if heat_scores else 5
    
    for item in ranked_data:
        sentiment = abs(item.get('sentiment_score', 0))
        heat = item.get('heat_score', 0)
        
        if sentiment >= sentiment_median and heat >= heat_median:
            distribution['high_sentiment_high_heat'] += 1
        elif sentiment >= sentiment_median and heat < heat_median:
            distribution['high_sentiment_low_heat'] += 1
        elif sentiment < sentiment_median and heat >= heat_median:
            distribution['low_sentiment_high_heat'] += 1
        else:
            distribution['low_sentiment_low_heat'] += 1
    
    return distribution


@unified_bp.route('/ranking/quadrant-analysis', methods=['GET'])
def get_quadrant_analysis():
    """获取四象限分析"""
    try:
        weibo_data = _load_weibo_data()
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '没有可用的数据'
            }), 400
        
        if TRI_DIMENSION_AVAILABLE:
            ranked_data = rank_weibo_data(weibo_data)
        else:
            ranked_data = weibo_data
        
        quadrant_dist = _calculate_quadrant_distribution(ranked_data)
        
        # 获取各象限的代表性数据
        quadrant_samples = {
            'high_sentiment_high_heat': [],
            'high_sentiment_low_heat': [],
            'low_sentiment_high_heat': [],
            'low_sentiment_low_heat': [],
        }
        
        sentiment_median = 0.5
        heat_median = 5
        
        for item in ranked_data[:100]:
            sentiment = abs(item.get('sentiment_score', 0))
            heat = item.get('heat_score', 0)
            
            if sentiment >= sentiment_median and heat >= heat_median:
                if len(quadrant_samples['high_sentiment_high_heat']) < 5:
                    quadrant_samples['high_sentiment_high_heat'].append(item)
            elif sentiment >= sentiment_median and heat < heat_median:
                if len(quadrant_samples['high_sentiment_low_heat']) < 5:
                    quadrant_samples['high_sentiment_low_heat'].append(item)
            elif sentiment < sentiment_median and heat >= heat_median:
                if len(quadrant_samples['low_sentiment_high_heat']) < 5:
                    quadrant_samples['low_sentiment_high_heat'].append(item)
            else:
                if len(quadrant_samples['low_sentiment_low_heat']) < 5:
                    quadrant_samples['low_sentiment_low_heat'].append(item)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'distribution': quadrant_dist,
                'samples': quadrant_samples,
                'total': len(ranked_data),
            }
        })
        
    except Exception as e:
        logger.error(f'四象限分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 数据统计API ====================

@unified_bp.route('/stats/overview', methods=['GET'])
def get_overview_stats():
    """获取数据概览统计"""
    try:
        stats = {
            'total_weibo': 0,
            'total_users': set(),
            'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
            'top_keywords': {},
            'time_range': {'earliest': None, 'latest': None},
        }
        
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('crawl_result_') and filename.endswith('.json'):
                filepath = os.path.join(DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for item in data:
                            stats['total_weibo'] += 1
                            
                            # 用户统计
                            user = item.get('user', {})
                            if user.get('id'):
                                stats['total_users'].add(user['id'])
                            
                            # 情感统计
                            sentiment = item.get('sentiment')
                            if sentiment in stats['sentiment_distribution']:
                                stats['sentiment_distribution'][sentiment] += 1
                            
                            # 关键词统计
                            keyword = item.get('keyword', '')
                            if keyword:
                                stats['top_keywords'][keyword] = stats['top_keywords'].get(keyword, 0) + 1
                            
                            # 时间范围
                            crawl_time = item.get('crawl_time')
                            if crawl_time:
                                if stats['time_range']['earliest'] is None or crawl_time < stats['time_range']['earliest']:
                                    stats['time_range']['earliest'] = crawl_time
                                if stats['time_range']['latest'] is None or crawl_time > stats['time_range']['latest']:
                                    stats['time_range']['latest'] = crawl_time
                                    
                except Exception as e:
                    logger.warning(f"读取文件失败 {filename}: {e}")
        
        # 处理统计结果
        stats['total_users'] = len(stats['total_users'])
        stats['top_keywords'] = sorted(
            stats['top_keywords'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': stats
        })
        
    except Exception as e:
        logger.error(f'获取统计信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@unified_bp.route('/stats/trend', methods=['GET'])
def get_sentiment_trend():
    """获取情感趋势"""
    try:
        days = request.args.get('days', 7, type=int)
        
        # 按日期统计情感分布
        from collections import defaultdict
        daily_stats = defaultdict(lambda: {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0})
        
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('crawl_result_') and filename.endswith('.json'):
                filepath = os.path.join(DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for item in data:
                            crawl_time = item.get('crawl_time', '')[:10]
                            sentiment = item.get('sentiment', 'neutral')
                            
                            if crawl_time:
                                daily_stats[crawl_time][sentiment] += 1
                                daily_stats[crawl_time]['total'] += 1
                                
                except Exception as e:
                    pass
        
        # 生成趋势数据
        from datetime import timedelta
        trend = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).strftime('%Y-%m-%d')
            stats = daily_stats.get(date, {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0})
            total = stats['total'] or 1
            
            trend.append({
                'date': date,
                'positive': round(stats['positive'] / total * 100, 1),
                'neutral': round(stats['neutral'] / total * 100, 1),
                'negative': round(stats['negative'] / total * 100, 1),
                'count': stats['total'],
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': trend
        })
        
    except Exception as e:
        logger.error(f'获取趋势数据失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 健康检查 ====================

@unified_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'code': 200,
        'message': 'Unified API is running',
        'version': '2.0',
        'timestamp': datetime.now().isoformat(),
    })

