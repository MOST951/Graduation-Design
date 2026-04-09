"""
分析流水线API
==============

整合数据采集、清洗、情感分析和双维度排序的完整API

功能：
1. 一站式微博数据分析
2. 支持批量和实时分析
3. 完整的分析报告生成
4. WebSocket实时推送

作者：毕业设计
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

from flask import Blueprint, request, jsonify, Response
from functools import wraps

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AnalysisPipelineAPI')

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入服务
try:
    from services.enhanced_crawler import EnhancedCrawlerService, CrawlConfig, CrawlResult
    CRAWLER_AVAILABLE = True
except ImportError:
    CRAWLER_AVAILABLE = False
    logger.warning("增强型爬虫服务不可用")

try:
    from services.hybrid_analyzer import HybridSentimentAnalyzer, analyze_sentiment
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False
    logger.warning("混合情感分析器不可用")

try:
    from spark.enhanced_dual_dimension import (
        EnhancedDualDimensionModel, 
        EnhancedDualDimensionConfig,
        rank_weibo_enhanced
    )
    RANKING_AVAILABLE = True
except ImportError:
    RANKING_AVAILABLE = False
    logger.warning("增强型双维度排序模型不可用")


# 创建蓝图（使用唯一名称避免冲突）
analysis_bp = Blueprint('analysis_pipeline', __name__, url_prefix='/api/pipeline')


# ==================== 数据模型 ====================

@dataclass
class AnalysisTask:
    """分析任务"""
    task_id: str
    status: str  # pending, crawling, analyzing, ranking, completed, failed
    progress: int  # 0-100
    message: str
    created_at: datetime
    updated_at: datetime
    config: Dict
    result: Optional[Dict] = None
    errors: List[str] = None


@dataclass
class AnalysisResult:
    """分析结果"""
    task_id: str
    total_weibos: int
    analysis_time: float  # 秒
    
    # 情感分析结果
    sentiment_distribution: Dict[str, int]
    sentiment_stats: Dict[str, float]
    
    # 双维度排序结果
    top_weibos: List[Dict]
    quadrant_distribution: Dict[str, int]
    
    # 热门话题
    hot_topics: List[Dict]
    hot_keywords: List[Dict]
    
    # 时间趋势
    time_trend: List[Dict]


# ==================== 任务管理 ====================

class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, AnalysisTask] = {}
        self._lock = threading.Lock()
    
    def create_task(self, config: Dict) -> AnalysisTask:
        """创建新任务"""
        task_id = f"analysis_{int(time.time() * 1000)}"
        task = AnalysisTask(
            task_id=task_id,
            status='pending',
            progress=0,
            message='任务已创建',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            config=config,
            errors=[]
        )
        
        with self._lock:
            self.tasks[task_id] = task
        
        return task
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                task.updated_at = datetime.now()
    
    def get_task(self, task_id: str) -> Optional[AnalysisTask]:
        """获取任务"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[AnalysisTask]:
        """获取所有任务"""
        with self._lock:
            return list(self.tasks.values())


# 全局任务管理器
task_manager = TaskManager()


# ==================== API装饰器 ====================

def handle_errors(f):
    """错误处理装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"API错误: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'message': '服务器内部错误'
            }), 500
    return decorated


# ==================== API路由 ====================

@analysis_bp.route('/status', methods=['GET'])
@handle_errors
def get_status():
    """获取服务状态"""
    return jsonify({
        'success': True,
        'data': {
            'crawler_available': CRAWLER_AVAILABLE,
            'analyzer_available': ANALYZER_AVAILABLE,
            'ranking_available': RANKING_AVAILABLE,
            'active_tasks': len([t for t in task_manager.get_all_tasks() 
                               if t.status not in ['completed', 'failed']]),
            'server_time': datetime.now().isoformat(),
        }
    })


@analysis_bp.route('/start', methods=['POST'])
@handle_errors
def start_analysis():
    """
    开始分析任务
    
    请求体:
    {
        "keywords": ["关键词1", "关键词2"],
        "crawl_hot": true,
        "pages": 3,
        "sentiment_weight": 0.35,
        "heat_weight": 0.35,
        "enable_ranking": true
    }
    """
    data = request.get_json() or {}
    
    # 解析配置
    config = {
        'keywords': data.get('keywords', []),
        'crawl_hot': data.get('crawl_hot', True),
        'pages': data.get('pages', 3),
        'sentiment_weight': data.get('sentiment_weight', 0.35),
        'heat_weight': data.get('heat_weight', 0.35),
        'timeliness_weight': data.get('timeliness_weight', 0.15),
        'influence_weight': data.get('influence_weight', 0.15),
        'enable_ranking': data.get('enable_ranking', True),
        'top_k': data.get('top_k', 100),
    }
    
    # 创建任务
    task = task_manager.create_task(config)
    
    # 后台执行分析
    thread = threading.Thread(target=run_analysis, args=(task.task_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'data': {
            'task_id': task.task_id,
            'status': task.status,
            'message': '分析任务已启动'
        }
    })


@analysis_bp.route('/task/<task_id>', methods=['GET'])
@handle_errors
def get_task_status(task_id: str):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    
    if not task:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'task_id': task.task_id,
            'status': task.status,
            'progress': task.progress,
            'message': task.message,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'errors': task.errors,
        }
    })


@analysis_bp.route('/task/<task_id>/result', methods=['GET'])
@handle_errors
def get_task_result(task_id: str):
    """获取任务结果"""
    task = task_manager.get_task(task_id)
    
    if not task:
        return jsonify({
            'success': False,
            'error': '任务不存在'
        }), 404
    
    if task.status != 'completed':
        return jsonify({
            'success': False,
            'error': f'任务未完成，当前状态: {task.status}'
        }), 400
    
    return jsonify({
        'success': True,
        'data': task.result
    })


@analysis_bp.route('/tasks', methods=['GET'])
@handle_errors
def list_tasks():
    """列出所有任务"""
    tasks = task_manager.get_all_tasks()
    
    # 按创建时间倒序
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    
    return jsonify({
        'success': True,
        'data': {
            'total': len(tasks),
            'tasks': [
                {
                    'task_id': t.task_id,
                    'status': t.status,
                    'progress': t.progress,
                    'message': t.message,
                    'created_at': t.created_at.isoformat(),
                }
                for t in tasks[:20]  # 只返回最近20个
            ]
        }
    })


@analysis_bp.route('/quick', methods=['POST'])
@handle_errors
def quick_analysis():
    """
    快速分析（同步接口，适用于少量数据）
    
    请求体:
    {
        "texts": ["文本1", "文本2", ...],
        "enable_ranking": true
    }
    """
    data = request.get_json() or {}
    texts = data.get('texts', [])
    
    if not texts:
        return jsonify({
            'success': False,
            'error': '请提供待分析文本'
        }), 400
    
    if len(texts) > 100:
        return jsonify({
            'success': False,
            'error': '快速分析最多支持100条文本，请使用异步接口'
        }), 400
    
    results = []
    
    # 情感分析
    if ANALYZER_AVAILABLE:
        analyzer = HybridSentimentAnalyzer()
        for text in texts:
            result = analyzer.analyze(text)
            results.append({
                'text': text,
                'sentiment': result.polarity,
                'label': result.label,
                'score': result.score,
                'confidence': result.confidence,
            })
    else:
        # 简化分析
        for text in texts:
            results.append({
                'text': text,
                'sentiment': 'neutral',
                'label': '中性',
                'score': 0.0,
                'confidence': 0.5,
            })
    
    # 双维度排序
    if data.get('enable_ranking', True) and RANKING_AVAILABLE:
        # 构建排序数据
        ranking_data = [
            {
                'id': str(i),
                'text': r['text'],
                'sentiment_score': r['score'],
                'reposts_count': 0,
                'comments_count': 0,
                'attitudes_count': 0,
            }
            for i, r in enumerate(results)
        ]
        ranked = rank_weibo_enhanced(ranking_data)
        
        # 合并排序结果
        for r, ranked_item in zip(results, ranked):
            r['rank'] = ranked_item['rank']
            r['dual_score'] = ranked_item['dual_score']
            r['quadrant'] = ranked_item['quadrant']
    
    # 统计
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    for r in results:
        s = r.get('sentiment', 'neutral')
        if s in sentiment_counts:
            sentiment_counts[s] += 1
    
    return jsonify({
        'success': True,
        'data': {
            'total': len(results),
            'results': results,
            'sentiment_distribution': sentiment_counts,
            'analysis_time': time.time(),
        }
    })


@analysis_bp.route('/sentiment', methods=['POST'])
@handle_errors
def analyze_single_text():
    """
    单文本情感分析
    
    请求体:
    {
        "text": "待分析文本",
        "context": {
            "topic": "话题",
            "user_id": "用户ID"
        }
    }
    """
    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({
            'success': False,
            'error': '请提供待分析文本'
        }), 400
    
    context = data.get('context', {})
    
    if ANALYZER_AVAILABLE:
        analyzer = HybridSentimentAnalyzer()
        result = analyzer.analyze(text, context)
        
        return jsonify({
            'success': True,
            'data': {
                'text': text,
                'polarity': result.polarity,
                'label': result.label,
                'score': result.score,
                'confidence': result.confidence,
                'fusion_method': result.fusion_method,
                'rule_weight': result.rule_weight,
                'bert_weight': result.bert_weight,
                'processing_time_ms': result.processing_time_ms,
            }
        })
    else:
        return jsonify({
            'success': True,
            'data': {
                'text': text,
                'polarity': 'neutral',
                'label': '中性',
                'score': 0.0,
                'confidence': 0.5,
                'fusion_method': 'unavailable',
            }
        })


@analysis_bp.route('/ranking', methods=['POST'])
@handle_errors
def rank_weibos():
    """
    微博双维度排序
    
    请求体:
    {
        "data": [
            {
                "id": "1",
                "text": "微博内容",
                "sentiment_score": 0.8,
                "reposts_count": 100,
                "comments_count": 50,
                "attitudes_count": 200,
                ...
            }
        ],
        "weights": {
            "sentiment": 0.35,
            "heat": 0.35,
            "timeliness": 0.15,
            "influence": 0.15
        },
        "top_k": 50
    }
    """
    data = request.get_json() or {}
    weibo_data = data.get('data', [])
    
    if not weibo_data:
        return jsonify({
            'success': False,
            'error': '请提供微博数据'
        }), 400
    
    weights = data.get('weights', {})
    top_k = data.get('top_k', 100)
    
    if RANKING_AVAILABLE:
        ranked = rank_weibo_enhanced(
            weibo_data,
            sentiment_weight=weights.get('sentiment', 0.35),
            heat_weight=weights.get('heat', 0.35),
            timeliness_weight=weights.get('timeliness', 0.15),
            influence_weight=weights.get('influence', 0.15),
        )
        
        # 四象限统计
        quadrant_counts = {}
        for item in ranked:
            q = item.get('quadrant', 'unknown')
            quadrant_counts[q] = quadrant_counts.get(q, 0) + 1
        
        return jsonify({
            'success': True,
            'data': {
                'total': len(ranked),
                'top_k': ranked[:top_k],
                'quadrant_distribution': quadrant_counts,
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': '排序模型不可用'
        }), 503


# ==================== 后台任务执行 ====================

def run_analysis(task_id: str):
    """执行分析任务"""
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    try:
        config = task.config
        all_data = []
        
        # 阶段1: 数据采集
        task_manager.update_task(task_id, status='crawling', progress=10, 
                                message='正在采集微博数据...')
        
        if CRAWLER_AVAILABLE:
            crawl_config = CrawlConfig(
                keywords=config.get('keywords', []),
                crawl_hot=config.get('crawl_hot', True),
                pages_per_keyword=config.get('pages', 3),
            )
            
            crawler = EnhancedCrawlerService(crawl_config)
            
            def progress_callback(progress, message):
                task_manager.update_task(
                    task_id, 
                    progress=10 + int(progress * 0.4),
                    message=message
                )
            
            crawl_result = crawler.crawl(progress_callback)
            all_data = crawl_result.data
            
            if crawl_result.status == 'failed':
                task_manager.update_task(
                    task_id, 
                    status='failed',
                    errors=crawl_result.errors
                )
                return
        else:
            task_manager.update_task(
                task_id, 
                progress=50,
                message='爬虫不可用，跳过数据采集'
            )
        
        # 阶段2: 情感分析
        task_manager.update_task(task_id, status='analyzing', progress=50,
                                message='正在进行情感分析...')
        
        if ANALYZER_AVAILABLE and all_data:
            analyzer = HybridSentimentAnalyzer()
            
            for i, weibo in enumerate(all_data):
                text = weibo.get('text', '')
                if text:
                    result = analyzer.analyze(text)
                    weibo['sentiment'] = result.polarity
                    weibo['sentiment_score'] = result.score
                    weibo['sentiment_label'] = result.label
                    weibo['sentiment_confidence'] = result.confidence
                
                if i % 10 == 0:
                    progress = 50 + int((i / len(all_data)) * 30)
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        message=f'情感分析中... ({i}/{len(all_data)})'
                    )
        
        # 阶段3: 双维度排序
        task_manager.update_task(task_id, status='ranking', progress=80,
                                message='正在进行双维度排序...')
        
        ranked_data = []
        if config.get('enable_ranking', True) and RANKING_AVAILABLE and all_data:
            ranked_data = rank_weibo_enhanced(
                all_data,
                sentiment_weight=config.get('sentiment_weight', 0.35),
                heat_weight=config.get('heat_weight', 0.35),
                timeliness_weight=config.get('timeliness_weight', 0.15),
                influence_weight=config.get('influence_weight', 0.15),
            )
        else:
            ranked_data = all_data
        
        # 阶段4: 生成报告
        task_manager.update_task(task_id, progress=90, message='正在生成分析报告...')
        
        result = generate_analysis_report(ranked_data, config)
        
        # 完成
        task_manager.update_task(
            task_id,
            status='completed',
            progress=100,
            message='分析完成',
            result=result
        )
        
        logger.info(f"任务 {task_id} 完成，共分析 {len(all_data)} 条数据")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 失败: {e}", exc_info=True)
        task_manager.update_task(
            task_id,
            status='failed',
            message=f'分析失败: {str(e)}',
            errors=[str(e)]
        )


def generate_analysis_report(data: List[Dict], config: Dict) -> Dict:
    """生成分析报告"""
    if not data:
        return {
            'total_weibos': 0,
            'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
            'top_weibos': [],
            'quadrant_distribution': {},
            'hot_keywords': [],
        }
    
    # 情感分布统计
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    sentiment_scores = []
    
    for item in data:
        s = item.get('sentiment', 'neutral')
        if s in sentiment_counts:
            sentiment_counts[s] += 1
        sentiment_scores.append(item.get('sentiment_score', 0))
    
    # 四象限分布
    quadrant_counts = {}
    for item in data:
        q = item.get('quadrant', 'unknown')
        quadrant_counts[q] = quadrant_counts.get(q, 0) + 1
    
    # Top微博
    top_k = config.get('top_k', 50)
    top_weibos = data[:top_k] if len(data) > top_k else data
    
    # 关键词提取（简单词频统计）
    word_counts = {}
    for item in data:
        keywords = item.get('extracted_hashtags', []) or []
        for kw in keywords:
            word_counts[kw] = word_counts.get(kw, 0) + 1
    
    hot_keywords = sorted(
        [{'word': k, 'count': v} for k, v in word_counts.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:20]
    
    # 计算统计值
    avg_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    
    return {
        'total_weibos': len(data),
        'sentiment_distribution': sentiment_counts,
        'sentiment_stats': {
            'avg_score': round(avg_score, 4),
            'positive_rate': round(sentiment_counts['positive'] / len(data) * 100, 2),
            'negative_rate': round(sentiment_counts['negative'] / len(data) * 100, 2),
        },
        'quadrant_distribution': quadrant_counts,
        'top_weibos': [
            {
                'id': w.get('id', ''),
                'text': w.get('text', '')[:200],
                'rank': w.get('rank', 0),
                'dual_score': w.get('dual_score', 0),
                'sentiment': w.get('sentiment', 'neutral'),
                'sentiment_score': w.get('sentiment_score', 0),
                'quadrant': w.get('quadrant', ''),
                'reposts_count': w.get('reposts_count', 0),
                'comments_count': w.get('comments_count', 0),
                'attitudes_count': w.get('attitudes_count', 0),
            }
            for w in top_weibos
        ],
        'hot_keywords': hot_keywords,
        'generated_at': datetime.now().isoformat(),
    }


# ==================== 注册蓝图 ====================

def register_analysis_api(app):
    """注册分析API蓝图"""
    app.register_blueprint(analysis_bp)
    logger.info("分析流水线API已注册")


# ==================== 测试 ====================

if __name__ == '__main__':
    from flask import Flask
    
    app = Flask(__name__)
    register_analysis_api(app)
    
    print("分析流水线API测试服务器启动...")
    print("API端点:")
    print("  GET  /api/analysis/status - 服务状态")
    print("  POST /api/analysis/start - 开始分析")
    print("  GET  /api/analysis/task/<id> - 任务状态")
    print("  GET  /api/analysis/task/<id>/result - 任务结果")
    print("  POST /api/analysis/quick - 快速分析")
    print("  POST /api/analysis/sentiment - 单文本分析")
    print("  POST /api/analysis/ranking - 双维度排序")
    
    app.run(debug=True, port=5001)

