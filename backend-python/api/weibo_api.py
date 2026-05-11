"""
微博数据采集与分析API
整合真实爬虫和Spark情感分析
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import threading
import time
import os
import json
from typing import Dict, List
import logging

# 导入爬虫和分析模块
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from crawler.weibo_crawler import WeiboCrawler, WeiboCrawlerTask
from spark.sentiment_analyzer import (
    SparkSentimentAnalyzer, 
    SentimentLexicon,
    SparkClusterManager,
    analyze_weibo_sentiment
)
from spark.tri_dimension_model import (
    TriDimensionRankingModel,
    TriDimensionConfig,
    rank_weibo_data,
    WeiboItem
)
from spark.bert_sentiment import (
    ChineseBERTSentimentAnalyzer,
    HybridSentimentAnalyzer,
    analyze_sentiment_bert,
    analyze_sentiment_hybrid
)

# 创建蓝图
weibo_bp = Blueprint('weibo', __name__, url_prefix='/api/weibo')

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 元数据文件路径 (模拟MySQL元数据表)
METADATA_FILE = os.path.join(DATA_DIR, 'metadata_tasks.json')
ANALYSIS_META_FILE = os.path.join(DATA_DIR, 'metadata_analysis.json')

# 全局状态
crawl_tasks: Dict[str, Dict] = {}
analysis_results: Dict[str, Dict] = {}
task_lock = threading.Lock()

def load_metadata():
    """加载元数据 (系统启动时调用)"""
    global crawl_tasks, analysis_results
    try:
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                crawl_tasks = json.load(f)
            logger.info(f"已加载 {len(crawl_tasks)} 条采集任务记录")
            
            # 将服务重启前未完成的任务标记为失败
            interrupted = 0
            for tid, task in crawl_tasks.items():
                if task.get('status') in ('crawling', 'processing', 'running'):
                    task['status'] = 'failed'
                    task['error'] = '服务重启，任务中断'
                    task['end_time'] = datetime.now().isoformat()
                    # 同步更新 phases 中正在运行的阶段
                    for phase in task.get('phases', {}).values():
                        if phase.get('status') == 'running':
                            phase['status'] = 'failed'
                    interrupted += 1
            if interrupted:
                logger.warning(f"已将 {interrupted} 个中断任务标记为失败")
                save_metadata()
            
        if os.path.exists(ANALYSIS_META_FILE):
            with open(ANALYSIS_META_FILE, 'r', encoding='utf-8') as f:
                analysis_results = json.load(f)
            logger.info(f"已加载 {len(analysis_results)} 条分析结果记录")
    except Exception as e:
        logger.error(f"加载元数据失败: {e}")

def save_metadata():
    """保存元数据 (数据变更时调用)"""
    try:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(crawl_tasks, f, ensure_ascii=False, indent=2)
            
        with open(ANALYSIS_META_FILE, 'w', encoding='utf-8') as f:
            # 分析结果可能很大，元数据只存摘要信息，这里简化处理直接存
            # 实际生产环境应存数据库
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存元数据失败: {e}")

# 初始化时加载元数据
load_metadata()


# ==================== 热搜相关API ====================

@weibo_bp.route('/hotsearch', methods=['GET'])
def get_hot_search():
    """
    获取微博热搜榜
    真实从微博爬取数据
    """
    try:
        crawler = WeiboCrawler()
        hot_list = crawler.get_hot_search()
        
        if not hot_list:
            # 如果爬取失败，返回缓存数据
            cache_file = os.path.join(DATA_DIR, 'hotsearch_cache.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    hot_list = json.load(f)
            else:
                return jsonify({
                    'code': 500,
                    'message': '获取热搜失败，请稍后重试',
                    'data': []
                }), 500
        else:
            # 缓存数据
            cache_file = os.path.join(DATA_DIR, 'hotsearch_cache.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(hot_list, f, ensure_ascii=False)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': hot_list,
            'crawl_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f'获取热搜失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
            'data': []
        }), 500


# ==================== 微博搜索API ====================

@weibo_bp.route('/search', methods=['GET'])
def search_weibo():
    """
    搜索微博
    
    Query参数:
        keyword: 搜索关键词
        page: 页码 (默认1)
        type: 搜索类型 (all/hot/ori)
        analyze: 是否进行情感分析 (true/false)
    """
    try:
        keyword = request.args.get('keyword', '')
        page = int(request.args.get('page', 1))
        search_type = request.args.get('type', 'all')
        do_analyze = request.args.get('analyze', 'true').lower() == 'true'
        
        if not keyword:
            return jsonify({
                'code': 400,
                'message': '关键词不能为空',
                'data': []
            }), 400
        
        crawler = WeiboCrawler()
        weibo_list = list(crawler.search_weibo(keyword, page, search_type))
        
        # 情感分析
        if do_analyze and weibo_list:
            for weibo in weibo_list:
                sentiment, score = SentimentLexicon.analyze(weibo.get('text', ''))
                weibo['sentiment'] = sentiment
                weibo['sentiment_score'] = score
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': weibo_list,
            'total': len(weibo_list),
            'keyword': keyword,
            'page': page
        })
        
    except Exception as e:
        logger.error(f'搜索微博失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
            'data': []
        }), 500


# ==================== 话题微博API ====================

@weibo_bp.route('/topic', methods=['GET'])
def get_topic_weibo():
    """
    获取话题微博
    
    Query参数:
        topic: 话题名称
        page: 页码 (默认1)
        analyze: 是否进行情感分析
    """
    try:
        topic = request.args.get('topic', '')
        page = int(request.args.get('page', 1))
        do_analyze = request.args.get('analyze', 'true').lower() == 'true'
        
        if not topic:
            return jsonify({
                'code': 400,
                'message': '话题不能为空',
                'data': []
            }), 400
        
        crawler = WeiboCrawler()
        weibo_list = list(crawler.get_topic_weibo(topic, page))
        
        # 情感分析
        if do_analyze and weibo_list:
            for weibo in weibo_list:
                sentiment, score = SentimentLexicon.analyze(weibo.get('text', ''))
                weibo['sentiment'] = sentiment
                weibo['sentiment_score'] = score
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': weibo_list,
            'total': len(weibo_list),
            'topic': topic,
            'page': page
        })
        
    except Exception as e:
        logger.error(f'获取话题微博失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
            'data': []
        }), 500


# ==================== 批量采集任务API ====================

@weibo_bp.route('/crawl/start', methods=['POST'])
def start_crawl_task():
    """
    启动批量采集任务
    
    Body参数:
        keywords: 关键词列表
        pages: 每个关键词爬取页数
        crawl_hot: 是否爬取热搜话题
    """
    try:
        data = request.json or {}
        keywords = data.get('keywords', [])
        pages = data.get('pages', 3)
        crawl_hot = data.get('crawl_hot', True)
        
        # 创建任务ID
        task_id = f"crawl_{int(time.time() * 1000)}"
        
        # 创建任务记录
        task_info = {
            'id': task_id,
            'status': 'running',
            'keywords': keywords,
            'pages': pages,
            'crawl_hot': crawl_hot,
            'progress': 0,
            'collected': 0,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'result_file': None,
            'error': None
        }
        
        with task_lock:
            crawl_tasks[task_id] = task_info
            save_metadata()  # 保存任务记录
        
        # 在后台线程执行爬取
        def run_crawl():
            try:
                crawler_task = WeiboCrawlerTask(os.path.join(DATA_DIR, 'weibo_raw'))
                all_data = []
                
                # 爬取热搜
                if crawl_hot:
                    task_info['progress'] = 10
                    try:
                        hot_list = crawler_task.crawl_hot_search(save=True)
                        task_info['progress'] = 20
                        
                        # 爬取热搜话题的微博
                        hot_weibo = crawler_task.crawl_hot_topics(
                            top_n=5, 
                            pages_per_topic=pages, 
                            save=True
                        )
                        all_data.extend(hot_weibo)
                        task_info['progress'] = 50
                    except Exception as e:
                        logger.warning(f"热搜爬取部分失败: {e}")
                
                # 按关键词爬取
                if keywords:
                    try:
                        keyword_weibo = crawler_task.crawl_by_keywords(
                            keywords, 
                            pages=pages, 
                            save=True
                        )
                        all_data.extend(keyword_weibo)
                    except Exception as e:
                        logger.warning(f"关键词爬取部分失败: {e}")
                
                task_info['progress'] = 80
                
                # 如果数据为空，记录警告但不再生成模拟数据
                if not all_data:
                    logger.warning("爬取数据为空，请检查网络连接或Cookie配置")
                    task_info['note'] = '未获取到数据，请检查爬虫配置'
                
                task_info['collected'] = len(all_data)
                
                # 保存汇总数据
                result_file = os.path.join(
                    DATA_DIR, 
                    f'crawl_result_{task_id}.json'
                )
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                
                task_info['result_file'] = result_file
                task_info['status'] = 'completed'
                task_info['progress'] = 100
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()  # 任务完成后保存状态
                
            except Exception as e:
                logger.error(f'爬取任务失败: {e}', exc_info=True)
                task_info['status'] = 'failed'
                task_info['error'] = str(e)
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()  # 任务失败保存状态
        
        thread = threading.Thread(target=run_crawl)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'code': 200,
            'message': '采集任务已启动',
            'data': task_info
        })
        
    except Exception as e:
        logger.error(f'启动采集任务失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/crawl/status/<task_id>', methods=['GET'])
def get_crawl_status(task_id: str):
    """获取采集任务状态"""
    try:
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': crawl_tasks[task_id]
        })
        
    except Exception as e:
        logger.error(f'获取任务状态失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/crawl/tasks', methods=['GET'])
def get_crawl_tasks():
    """获取所有采集任务列表"""
    try:
        # 获取任务列表，按时间倒序
        tasks_list = list(crawl_tasks.values())
        tasks_list.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'tasks': tasks_list,
                'total': len(tasks_list),
                'completed': sum(1 for t in tasks_list if t['status'] == 'completed'),
                'running': sum(1 for t in tasks_list if t['status'] == 'running')
            }
        })
        
    except Exception as e:
        logger.error(f'获取任务列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/crawl/data/<task_id>', methods=['GET'])
def get_crawl_data(task_id: str):
    """获取采集任务的数据"""
    try:
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        task_info = crawl_tasks[task_id]
        
        if task_info['status'] != 'completed':
            return jsonify({
                'code': 400,
                'message': '任务尚未完成'
            }), 400
        
        result_file = task_info.get('result_file')
        if not result_file or not os.path.exists(result_file):
            return jsonify({
                'code': 404,
                'message': '数据文件不存在'
            }), 404
        
        # 读取数据
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 支持分页
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = data[start:end]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': paginated_data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'task_info': {
                    'id': task_info['id'],
                    'keywords': task_info['keywords'],
                    'collected': task_info['collected'],
                    'start_time': task_info['start_time'],
                    'end_time': task_info.get('end_time')
                }
            }
        })
        
    except Exception as e:
        logger.error(f'获取任务数据失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== Spark分析API ====================

@weibo_bp.route('/analyze', methods=['POST'])
def analyze_data():
    """
    使用Spark进行情感分析
    
    Body参数:
        task_id: 采集任务ID (可选，使用已采集的数据)
        data: 微博数据列表 (可选，直接分析)
        use_spark: 是否使用Spark (默认true)
    """
    try:
        data = request.json or {}
        task_id = data.get('task_id')
        weibo_data = data.get('data', [])
        use_spark = data.get('use_spark', True)
        
        # 如果指定了任务ID，从文件加载数据
        if task_id and task_id in crawl_tasks:
            result_file = crawl_tasks[task_id].get('result_file')
            if result_file and os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    weibo_data = json.load(f)
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '没有可分析的数据'
            }), 400
        
        # 创建分析任务ID
        analysis_id = f"analysis_{int(time.time() * 1000)}"
        
        # 执行分析
        analyzer = SparkSentimentAnalyzer()
        analyzed_data = analyzer.analyze_batch(weibo_data)
        stats = analyzer.get_statistics(analyzed_data)
        keyword_stats = analyzer.get_keyword_sentiment(analyzed_data)
        time_series = analyzer.get_time_series(analyzed_data)
        
        # 保存分析结果
        result = {
            'id': analysis_id,
            'data': analyzed_data,
            'statistics': stats,
            'keyword_stats': keyword_stats,
            'time_series': time_series,
            'analysis_time': datetime.now().isoformat()
        }
        
        analysis_results[analysis_id] = result
        save_metadata()  # 保存分析结果记录
        
        # 保存到文件
        result_file = os.path.join(DATA_DIR, f'analysis_{analysis_id}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'code': 200,
            'message': '分析完成',
            'data': {
                'id': analysis_id,
                'results': analyzed_data,  # 返回分析后的数据列表
                'statistics': stats,
                'keyword_stats': keyword_stats,
                'time_series': time_series,
                'total_analyzed': len(analyzed_data)
            }
        })
        
    except Exception as e:
        logger.error(f'分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/analyze/<analysis_id>', methods=['GET'])
def get_analysis_result(analysis_id: str):
    """获取分析结果"""
    try:
        if analysis_id in analysis_results:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': analysis_results[analysis_id]
            })
        
        # 尝试从文件加载
        result_file = os.path.join(DATA_DIR, f'analysis_{analysis_id}.json')
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result
            })
        
        return jsonify({
            'code': 404,
            'message': '分析结果不存在'
        }), 404
        
    except Exception as e:
        logger.error(f'获取分析结果失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== Spark集群信息API ====================

@weibo_bp.route('/spark/info', methods=['GET'])
def get_spark_info():
    """获取Spark集群信息"""
    try:
        manager = SparkClusterManager()
        info = manager.get_cluster_info()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': info
        })
        
    except Exception as e:
        logger.error(f'获取Spark信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 数据统计API ====================

@weibo_bp.route('/stats/overview', methods=['GET'])
def get_overview_stats():
    """获取数据概览统计"""
    try:
        # 统计已采集的数据
        raw_dir = os.path.join(DATA_DIR, 'weibo_raw')
        total_files = 0
        total_records = 0
        
        if os.path.exists(raw_dir):
            for filename in os.listdir(raw_dir):
                if filename.endswith('.json'):
                    total_files += 1
                    filepath = os.path.join(raw_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            total_records += len(data) if isinstance(data, list) else 1
                    except:
                        pass
        
        # 统计分析结果
        total_analyses = len(analysis_results)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total_crawl_tasks': len(crawl_tasks),
                'total_data_files': total_files,
                'total_records': total_records,
                'total_analyses': total_analyses,
                'active_tasks': sum(1 for t in crawl_tasks.values() if t['status'] == 'running'),
                'update_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'获取统计信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 实时分析API ====================

@weibo_bp.route('/realtime/analyze', methods=['POST'])
def realtime_analyze():
    """
    实时分析单条文本
    
    Body参数:
        text: 要分析的文本
    """
    try:
        data = request.json or {}
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'code': 400,
                'message': '文本不能为空'
            }), 400
        
        sentiment, score = SentimentLexicon.analyze(text)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'text': text,
                'sentiment': sentiment,
                'sentiment_score': score,
                'analysis_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'实时分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 三维度排序API ====================

@weibo_bp.route('/rank/tri-dimension', methods=['POST'])
def tri_dimension_rank():
    """
    情感-热度三维度排序
    
    创新点：融合情感强度和传播热度两个维度进行综合排序
    
    Body参数:
        data: 微博数据列表
        sentiment_weight: 情感权重 (默认0.4)
        heat_weight: 热度权重 (默认0.4)
        timeliness_weight: 时效性权重 (默认0.2)
        top_k: 返回前k条 (可选)
    """
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        sentiment_weight = req_data.get('sentiment_weight', 0.4)
        heat_weight = req_data.get('heat_weight', 0.4)
        timeliness_weight = req_data.get('timeliness_weight', 0.2)
        top_k = req_data.get('top_k')
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '数据不能为空'
            }), 400
        
        # 预处理：如果数据缺少情感得分，先进行情感分析
        for item in weibo_data:
            if 'sentiment_score' not in item:
                text = item.get('text', '')
                sentiment, score = SentimentLexicon.analyze(text)
                item['sentiment_score'] = score
                item['sentiment_label'] = sentiment
        
        # 执行三维度排序
        ranked_data = rank_weibo_data(
            weibo_data, 
            sentiment_weight=sentiment_weight,
            heat_weight=heat_weight
        )
        
        if top_k:
            ranked_data = ranked_data[:top_k]
        
        # 转换为前端期望的数据格式
        formatted_items = []
        for item in ranked_data:
            sentiment_score = item.get('sentiment_score', 0)
            heat_score = item.get('heat_score', 0)
            
            # 确定情感极性
            if sentiment_score > 0.2:
                polarity = 'positive'
            elif sentiment_score < -0.2:
                polarity = 'negative'
            else:
                polarity = 'neutral'
            
            # 确定四象限 (基于归一化后的值)
            # 情感强度归一化到 0-1
            sentiment_intensity = min(1.0, abs(sentiment_score) * 1.5)
            # 热度归一化到 0-1 (假设最大热度对应 log(1+100000) ≈ 11.5)
            heat_normalized = min(1.0, heat_score / 11.5)
            
            high_sentiment = sentiment_intensity >= 0.5
            high_heat = heat_normalized >= 0.5
            
            if high_sentiment and high_heat:
                quadrant = 'high_sentiment_high_heat'
            elif high_sentiment and not high_heat:
                quadrant = 'high_sentiment_low_heat'
            elif not high_sentiment and high_heat:
                quadrant = 'low_sentiment_high_heat'
            else:
                quadrant = 'low_sentiment_low_heat'
            
            # 获取互动数据
            interactions = item.get('interactions', {})
            if not interactions:
                interactions = {
                    'reposts': item.get('reposts_count', 0),
                    'comments': item.get('comments_count', 0),
                    'likes': item.get('attitudes_count', 0)
                }
            
            formatted_item = {
                'id': item.get('id', ''),
                'text': item.get('text', ''),
                'rank': item.get('rank', 0),
                'tri_score': round(item.get('tri_score', 0), 4),
                'quadrant': quadrant,
                'sentiment': {
                    'polarity': polarity,
                    'score': round(sentiment_score, 4),
                    'intensity': round(sentiment_intensity * 100, 2)
                },
                'heat': {
                    'score': round(heat_normalized, 4),
                    'time_decay': round(item.get('score_breakdown', {}).get('timeliness_score', 0.5), 4),
                    'influence': round(1.0, 4)  # 简化处理
                },
                'interactions': interactions,
                'created_at': item.get('created_at', ''),
                'user': item.get('user', {})
            }
            formatted_items.append(formatted_item)
        
        # 保存分析结果
        analysis_id = f"tri_analysis_{int(time.time() * 1000)}"
        result = {
            'id': analysis_id,
            'type': 'tri_dimension',
            'data': formatted_items,
            'config': {
                'sentiment_weight': sentiment_weight,
                'heat_weight': heat_weight,
                'timeliness_weight': timeliness_weight
            },
            'analysis_time': datetime.now().isoformat()
        }
        
        analysis_results[analysis_id] = result
        save_metadata()
        
        # 保存到文件
        result_file = os.path.join(DATA_DIR, f'analysis_{analysis_id}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'id': analysis_id,
                'ranked_items': formatted_items,
                'total': len(formatted_items),
                'config': result['config'],
                'analysis_time': result['analysis_time']
            }
        })
        
    except Exception as e:
        logger.error(f'三维度排序失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/rank/config', methods=['GET', 'POST'])
def rank_config():
    """
    获取或设置三维度排序配置
    """
    if request.method == 'GET':
        config = TriDimensionConfig()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'sentiment_weight': config.sentiment_weight,
                'heat_weight': config.heat_weight,
                'timeliness_weight': config.timeliness_weight,
                'repost_factor': config.repost_factor,
                'comment_factor': config.comment_factor,
                'like_factor': config.like_factor,
                'decay_half_life_hours': config.decay_half_life_hours,
                'negative_boost': config.negative_boost,
                'negative_boost_factor': config.negative_boost_factor
            }
        })
    else:
        # POST: 更新配置（这里只返回示例，实际可以持久化）
        return jsonify({
            'code': 200,
            'message': '配置更新成功（演示模式）'
        })


# ==================== BERT情感分析API ====================

@weibo_bp.route('/analyze/bert', methods=['POST'])
def bert_analyze():
    """
    使用BERT模型进行情感分析
    
    Body参数:
        text: 单条文本
        texts: 文本列表（批量分析）
    """
    try:
        req_data = request.json or {}
        text = req_data.get('text')
        texts = req_data.get('texts', [])
        
        if text:
            # 单条分析
            result = analyze_sentiment_bert(text)
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result
            })
        elif texts:
            # 批量分析
            analyzer = ChineseBERTSentimentAnalyzer()
            analyzer.initialize()
            results = analyzer.analyze_batch(texts)
            
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'results': [
                        {
                            'text': r.text,
                            'sentiment': r.sentiment,
                            'confidence': round(r.confidence, 4)
                        } for r in results
                    ],
                    'total': len(results)
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': '请提供text或texts参数'
            }), 400
            
    except Exception as e:
        logger.error(f'BERT分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/analyze/hybrid', methods=['POST'])
def hybrid_analyze():
    """
    混合情感分析（词典+BERT）
    
    Body参数:
        text: 要分析的文本
        strategy: 融合策略 (weighted/confidence/cascade)
    """
    try:
        req_data = request.json or {}
        text = req_data.get('text', '')
        strategy = req_data.get('strategy', 'weighted')
        
        if not text:
            return jsonify({
                'code': 400,
                'message': '文本不能为空'
            }), 400
        
        result = analyze_sentiment_hybrid(text, strategy)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f'混合分析失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== Spark流水线API ====================

@weibo_bp.route('/pipeline/run', methods=['POST'])
def run_pipeline():
    """
    运行Spark分析流水线
    
    Body参数:
        data: 微博数据列表
        stages: 要执行的阶段列表 (可选)
    """
    try:
        req_data = request.json or {}
        weibo_data = req_data.get('data', [])
        
        if not weibo_data:
            return jsonify({
                'code': 400,
                'message': '数据不能为空'
            }), 400
        
        # 导入流水线
        from spark.spark_pipeline import SentimentPipeline, PipelineConfig
        
        config = PipelineConfig()
        pipeline = SentimentPipeline(config)
        
        # 运行流水线
        df = pipeline.run(weibo_data)
        
        # 获取统计信息
        stats = pipeline.get_statistics(df)
        metrics = pipeline.get_metrics()
        
        # 获取结果数据
        result_data = df.limit(100).toPandas().to_dict('records')
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'results': result_data,
                'statistics': stats,
                'metrics': metrics
            }
        })
        
    except Exception as e:
        logger.error(f'流水线执行失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 模型信息API ====================

@weibo_bp.route('/models/info', methods=['GET'])
def get_models_info():
    """获取可用模型信息"""
    try:
        # BERT模型信息
        bert_analyzer = ChineseBERTSentimentAnalyzer()
        bert_info = bert_analyzer.get_model_info()
        
        # 三维度模型信息
        tri_config = TriDimensionConfig()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'bert_model': bert_info,
                'tri_dimension_model': {
                    'name': '情感-热度三维度排序模型',
                    'description': '融合情感强度和传播热度的综合排序算法',
                    'parameters': {
                        'sentiment_weight': tri_config.sentiment_weight,
                        'heat_weight': tri_config.heat_weight,
                        'timeliness_weight': tri_config.timeliness_weight
                    }
                },
                'lexicon_model': {
                    'name': '中文情感词典',
                    'positive_words_count': len(SentimentLexicon.POSITIVE_WORDS),
                    'negative_words_count': len(SentimentLexicon.NEGATIVE_WORDS),
                    'negation_words_count': len(SentimentLexicon.NEGATION_WORDS),
                    'degree_words_count': len(SentimentLexicon.DEGREE_WORDS)
                },
                'available_strategies': ['lexicon', 'bert', 'hybrid', 'tri_dimension']
            }
        })
        
    except Exception as e:
        logger.error(f'获取模型信息失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 完整数据流连通API ====================
# 解决中期检查表中"爬虫数据未与各个模块连通"问题
# 数据流：微博爬虫 → HDFS原始存储 → Spark清洗 → HBase结构化 → 三维度排序 → 前端展示

@weibo_bp.route('/collect', methods=['POST'])
def collect_and_process():
    """
    启动完整数据采集与处理流程
    
    数据流：
    1. 启动爬虫任务，采集微博数据
    2. 采集完成后自动触发Spark清洗作业
    3. 清洗完成后写入HBase
    4. 最后执行三维度排序
    
    Body参数:
        keywords: 关键词列表
        pages: 每个关键词爬取页数 (默认3)
        crawl_hot: 是否爬取热搜话题 (默认true)
        auto_process: 是否自动触发后续处理 (默认true)
    
    Returns:
        task_id: 任务ID，用于查询状态
    """
    try:
        data = request.json or {}
        keywords = data.get('keywords', [])
        pages = data.get('pages', 3)
        crawl_hot = data.get('crawl_hot', True)
        auto_process = data.get('auto_process', True)
        
        # 参数校验
        if not isinstance(keywords, list):
            return jsonify({'code': 400, 'message': '关键词必须为数组格式'}), 400
        # 过滤空字符串和超长关键词
        cleaned_keywords = []
        for kw in keywords:
            kw = str(kw).strip()
            if not kw:
                continue
            if len(kw) > 100:
                return jsonify({'code': 400, 'message': f'关键词长度不能超过100字符: {kw[:20]}...'}), 400
            cleaned_keywords.append(kw)
        keywords = cleaned_keywords
        
        if not keywords and not crawl_hot:
            return jsonify({'code': 400, 'message': '关键词列表不能为空（或开启热搜爬取）'}), 400
        
        # 创建任务ID
        task_id = f"collect_{int(time.time() * 1000)}"
        
        # 创建任务记录
        task_info = {
            'id': task_id,
            'status': 'crawling',
            'phase': 'crawl',  # crawl -> clean -> analyze -> rank -> done
            'keywords': keywords,
            'pages': pages,
            'crawl_hot': crawl_hot,
            'auto_process': auto_process,
            'progress': 0,
            'collected': 0,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'result_file': None,
            'spark_job_id': None,
            'error': None,
            'phases': {
                'crawl': {'status': 'running', 'progress': 0},
                'clean': {'status': 'pending', 'progress': 0},
                'analyze': {'status': 'pending', 'progress': 0},
                'rank': {'status': 'pending', 'progress': 0},
            }
        }
        
        with task_lock:
            crawl_tasks[task_id] = task_info
            save_metadata()
        
        # 在后台线程执行完整流程
        def run_full_pipeline():
            try:
                # ========== 阶段1: 数据采集 ==========
                logger.info(f"[{task_id}] 阶段1: 开始数据采集...")
                task_info['phases']['crawl']['status'] = 'running'
                task_info['phases']['crawl']['progress'] = 5
                task_info['progress'] = 2
                
                crawler_task = WeiboCrawlerTask(os.path.join(DATA_DIR, 'weibo_raw'))
                all_data = []
                
                # 计算总步骤用于进度
                hot_topic_n = 3  # 减少热搜话题数避免过慢
                total_steps = (1 + hot_topic_n if crawl_hot else 0) + len(keywords)
                finished_steps = 0
                
                def update_crawl_progress():
                    nonlocal finished_steps
                    finished_steps += 1
                    pct = min(int(finished_steps / max(total_steps, 1) * 100), 99)
                    task_info['phases']['crawl']['progress'] = pct
                    task_info['progress'] = int(pct * 0.2)  # 爬虫占总进度20%
                    task_info['collected'] = len(all_data)
                
                # 爬取热搜
                if crawl_hot:
                    try:
                        hot_list = crawler_task.crawl_hot_search(save=True)
                        update_crawl_progress()
                        logger.info(f"[{task_id}] 热搜榜爬取完成，共 {len(hot_list)} 条")
                        
                        # 爬取热搜话题的微博（减少数量加速）
                        hot_weibo = crawler_task.crawl_hot_topics(
                            top_n=hot_topic_n, 
                            pages_per_topic=pages, 
                            save=True
                        )
                        all_data.extend(hot_weibo)
                        update_crawl_progress()
                        logger.info(f"[{task_id}] 热搜话题微博爬取完成，共 {len(hot_weibo)} 条")
                    except Exception as e:
                        logger.warning(f"热搜爬取部分失败: {e}")
                        finished_steps += 2  # 跳过这些步骤
                
                # 按关键词爬取
                if keywords:
                    for kw in keywords:
                        try:
                            kw_data = crawler_task.crawl_by_keywords(
                                [kw], 
                                pages=pages, 
                                save=True
                            )
                            all_data.extend(kw_data)
                            logger.info(f"[{task_id}] 关键词 '{kw}' 爬取完成，共 {len(kw_data)} 条")
                        except Exception as e:
                            logger.warning(f"关键词 '{kw}' 爬取失败: {e}")
                        update_crawl_progress()
                
                task_info['progress'] = 20
                task_info['collected'] = len(all_data)
                task_info['phases']['crawl']['progress'] = 100
                task_info['phases']['crawl']['status'] = 'completed'
                
                # 保存采集数据
                result_file = os.path.join(DATA_DIR, f'crawl_result_{task_id}.json')
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                task_info['result_file'] = result_file
                
                logger.info(f"[{task_id}] 采集完成，共 {len(all_data)} 条数据")
                
                if not auto_process:
                    task_info['status'] = 'crawl_completed'
                    task_info['phase'] = 'crawl_done'
                    save_metadata()
                    return
                
                # ========== 阶段2: 数据清洗 ==========
                logger.info(f"[{task_id}] 阶段2: 开始数据清洗...")
                task_info['phase'] = 'clean'
                task_info['phases']['clean']['status'] = 'running'
                task_info['progress'] = 25
                
                # 导入Spark服务
                from services.spark_service import get_spark_service, JobStatus
                spark_service = get_spark_service()
                
                # 提交清洗作业
                clean_job = spark_service.submit_cleaning_job(
                    input_path=result_file,
                    output_path=f'/weibo/cleaned/{task_id}',
                    crawl_task_id=task_id
                )
                task_info['spark_job_id'] = clean_job.job_id
                
                # 等待清洗完成
                while True:
                    job_status = spark_service.get_job_status(clean_job.job_id)
                    if job_status:
                        task_info['phases']['clean']['progress'] = job_status.get('progress', 0)
                        task_info['progress'] = 25 + int(job_status.get('progress', 0) * 0.2)
                        
                        if job_status['status'] == JobStatus.COMPLETED.value:
                            break
                        elif job_status['status'] == JobStatus.FAILED.value:
                            raise Exception(f"清洗作业失败: {job_status.get('error_message')}")
                    
                    time.sleep(2)
                
                task_info['phases']['clean']['status'] = 'completed'
                task_info['progress'] = 45
                logger.info(f"[{task_id}] 数据清洗完成")
                
                # ========== 阶段3: 情感分析 ==========
                logger.info(f"[{task_id}] 阶段3: 开始情感分析...")
                task_info['phase'] = 'analyze'
                task_info['phases']['analyze']['status'] = 'running'
                
                # 使用本地情感分析器
                analyzer = SparkSentimentAnalyzer()
                analyzed_data = analyzer.analyze_batch(all_data)
                
                task_info['phases']['analyze']['progress'] = 100
                task_info['phases']['analyze']['status'] = 'completed'
                task_info['progress'] = 70
                
                # 保存分析结果
                analysis_file = os.path.join(DATA_DIR, f'analysis_{task_id}.json')
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analyzed_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"[{task_id}] 情感分析完成")
                
                # ========== 阶段4: 三维度排序 ==========
                logger.info(f"[{task_id}] 阶段4: 开始三维度排序...")
                task_info['phase'] = 'rank'
                task_info['phases']['rank']['status'] = 'running'
                task_info['progress'] = 75
                
                # 执行三维度排序
                ranked_data = rank_weibo_data(analyzed_data)
                
                task_info['phases']['rank']['progress'] = 100
                task_info['phases']['rank']['status'] = 'completed'
                task_info['progress'] = 95
                
                # 保存排序结果
                rank_file = os.path.join(DATA_DIR, f'ranked_{task_id}.json')
                with open(rank_file, 'w', encoding='utf-8') as f:
                    json.dump(ranked_data[:100], f, ensure_ascii=False, indent=2)
                
                logger.info(f"[{task_id}] 三维度排序完成")
                
                # ========== 阶段5: 结果入库 ==========
                logger.info(f"[{task_id}] 阶段5: 开始结果入库...")
                task_info['phase'] = 'store'
                task_info['progress'] = 96
                
                try:
                    from services.database_service import get_db_service
                    db = get_db_service()
                    batch_id = task_id
                    
                    # 5a: 写入微博原始数据
                    weibo_insert_result = db.bulk_insert_weibos(all_data, batch_id=batch_id)
                    logger.info(f"[{task_id}] 微博数据入库: inserted={weibo_insert_result.get('inserted', 0)}, skipped={weibo_insert_result.get('skipped', 0)}")
                    
                    # 5b: 写入情感分析结果
                    sentiment_records = []
                    for item in analyzed_data:
                        if item.get('id') or item.get('weibo_id'):
                            sentiment_records.append({
                                'weibo_id': item.get('id') or item.get('weibo_id'),
                                'hybrid_score': item.get('sentiment_score', item.get('score', 0)),
                                'dict_score': item.get('dict_score'),
                                'bert_score': item.get('bert_score'),
                                'sentiment_class': item.get('sentiment', item.get('sentiment_class', 'neutral')),
                                'confidence': item.get('confidence', 0.8),
                                'analysis_method': 'hybrid',
                            })
                    if sentiment_records:
                        sent_result = db.save_sentiment_results(sentiment_records)
                        logger.info(f"[{task_id}] 情感结果入库: saved={sent_result.get('saved', 0)}")
                    
                    # 5c: 写入三维度排序结果
                    if ranked_data:
                        rank_result = db.save_tri_dimension_results(ranked_data, batch_id=batch_id)
                        logger.info(f"[{task_id}] 排序结果入库: saved={rank_result.get('saved', 0)}")
                    
                    # 5d: 写入采集批次日志
                    try:
                        log_sql = """
                        INSERT INTO crawl_batch_log 
                        (batch_id, status, total_weibos, success_count, failure_count,
                         start_time, end_time, student_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE status=VALUES(status), end_time=VALUES(end_time)
                        """
                        with db.get_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute(log_sql, (
                                    batch_id,
                                    'completed',
                                    len(all_data),
                                    len(sentiment_records),
                                    0,
                                    task_info.get('start_time'),
                                    datetime.now().isoformat(),
                                    '2022407443'
                                ))
                            conn.commit()
                    except Exception as db_log_err:
                        logger.warning(f"[{task_id}] 批次日志写入失败（非关键）: {db_log_err}")
                    
                    logger.info(f"[{task_id}] 结果入库完成")
                except Exception as db_err:
                    logger.error(f"[{task_id}] 结果入库失败: {db_err}", exc_info=True)
                
                # ========== 完成 ==========
                task_info['status'] = 'completed'
                task_info['phase'] = 'done'
                task_info['progress'] = 100
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()
                
                logger.info(f"[{task_id}] 完整数据流处理完成!")
                
            except Exception as e:
                logger.error(f'完整流程执行失败: {e}', exc_info=True)
                task_info['status'] = 'failed'
                task_info['error'] = str(e)
                task_info['end_time'] = datetime.now().isoformat()
                save_metadata()
        
        thread = threading.Thread(target=run_full_pipeline)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'code': 200,
            'message': '数据采集与处理任务已启动',
            'data': {
                'task_id': task_id,
                'status': 'crawling',
                'auto_process': auto_process,
                'phases': ['crawl', 'clean', 'analyze', 'rank']
            }
        })
        
    except Exception as e:
        logger.error(f'启动采集任务失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/collect/status/<task_id>', methods=['GET'])
def get_collect_status(task_id: str):
    """
    获取完整数据流任务状态
    
    Returns:
        任务状态，包括各阶段进度
    """
    try:
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        task_info = crawl_tasks[task_id]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'task_id': task_id,
                'status': task_info.get('status'),
                'phase': task_info.get('phase'),
                'progress': task_info.get('progress', 0),
                'collected': task_info.get('collected', 0),
                'phases': task_info.get('phases', {}),
                'start_time': task_info.get('start_time'),
                'end_time': task_info.get('end_time'),
                'error': task_info.get('error'),
                'spark_job_id': task_info.get('spark_job_id')
            }
        })
        
    except Exception as e:
        logger.error(f'获取任务状态失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/collect/result/<task_id>', methods=['GET'])
def get_collect_result(task_id: str):
    """
    获取完整数据流处理结果
    
    Query参数:
        type: 结果类型 (raw/analyzed/ranked)
        page: 页码
        page_size: 每页数量
    """
    try:
        if task_id not in crawl_tasks:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        task_info = crawl_tasks[task_id]
        result_type = request.args.get('type', 'ranked')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        # 根据类型选择文件
        if result_type == 'raw':
            file_path = os.path.join(DATA_DIR, f'crawl_result_{task_id}.json')
        elif result_type == 'analyzed':
            file_path = os.path.join(DATA_DIR, f'analysis_{task_id}.json')
        else:  # ranked
            file_path = os.path.join(DATA_DIR, f'ranked_{task_id}.json')
        
        if not os.path.exists(file_path):
            return jsonify({
                'code': 404,
                'message': f'{result_type}类型的结果文件不存在'
            }), 404
        
        # 读取数据
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 分页
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = data[start:end]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': paginated_data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'type': result_type,
                'task_info': {
                    'id': task_id,
                    'status': task_info.get('status'),
                    'collected': task_info.get('collected', 0)
                }
            }
        })
        
    except Exception as e:
        logger.error(f'获取结果失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/spark/jobs', methods=['GET'])
def get_spark_jobs():
    """获取所有Spark作业列表"""
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        jobs = spark_service.get_all_jobs()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'jobs': jobs,
                'total': len(jobs),
                'running': sum(1 for j in jobs if j['status'] == 'running'),
                'completed': sum(1 for j in jobs if j['status'] == 'completed'),
                'failed': sum(1 for j in jobs if j['status'] == 'failed')
            }
        })
        
    except Exception as e:
        logger.error(f'获取Spark作业列表失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/spark/jobs/<job_id>', methods=['GET'])
def get_spark_job_status(job_id: str):
    """获取单个Spark作业状态"""
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        job = spark_service.get_job_status(job_id)
        
        if not job:
            return jsonify({
                'code': 404,
                'message': '作业不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': job
        })
        
    except Exception as e:
        logger.error(f'获取Spark作业状态失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/spark/jobs/<job_id>/cancel', methods=['POST'])
def cancel_spark_job(job_id: str):
    """取消Spark作业"""
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        success = spark_service.cancel_job(job_id)
        
        if success:
            return jsonify({
                'code': 200,
                'message': '作业已取消'
            })
        else:
            return jsonify({
                'code': 404,
                'message': '作业不存在或无法取消'
            }), 404
        
    except Exception as e:
        logger.error(f'取消Spark作业失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 数据质量监控API ====================

@weibo_bp.route('/data-quality', methods=['GET'])
def get_data_quality():
    """
    获取数据质量概览
    
    返回最新的数据质量指标和报警信息
    """
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        summary = validator.get_latest_quality_summary()
        reports = validator.get_quality_reports(limit=5)
        error_log = validator.get_error_log(limit=20)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'summary': summary,
                'recent_reports': reports,
                'recent_errors': error_log,
                'thresholds': validator.QUALITY_THRESHOLDS
            }
        })
        
    except Exception as e:
        logger.error(f'获取数据质量失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/validate', methods=['POST'])
def validate_data():
    """
    验证数据质量
    
    Body参数:
        data: 要验证的数据列表
        check_duplicates: 是否检查重复 (默认true)
        auto_fix: 是否自动修复 (默认true)
        generate_report: 是否生成报告 (默认true)
        task_id: 关联的任务ID (可选)
    """
    try:
        from utils.data_validator import get_validator, validate_weibo_batch, generate_quality_report
        
        req_data = request.json or {}
        data_list = req_data.get('data', [])
        check_duplicates = req_data.get('check_duplicates', True)
        auto_fix = req_data.get('auto_fix', True)
        gen_report = req_data.get('generate_report', True)
        task_id = req_data.get('task_id')
        
        if not data_list:
            return jsonify({
                'code': 400,
                'message': '数据列表不能为空'
            }), 400
        
        # 验证数据
        valid_data, metrics = validate_weibo_batch(
            data_list, 
            check_duplicates=check_duplicates,
            auto_fix=auto_fix
        )
        
        # 生成报告
        report = None
        if gen_report:
            report = generate_quality_report(metrics, task_id)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'metrics': metrics.to_dict(),
                'valid_count': len(valid_data),
                'report': report,
                'alerts': report.get('alerts', []) if report else []
            }
        })
        
    except Exception as e:
        logger.error(f'数据验证失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/reports', methods=['GET'])
def get_quality_reports():
    """获取数据质量报告列表"""
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        limit = request.args.get('limit', 10, type=int)
        reports = validator.get_quality_reports(limit=limit)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'reports': reports,
                'total': len(reports)
            }
        })
        
    except Exception as e:
        logger.error(f'获取质量报告失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/errors', methods=['GET'])
def get_quality_errors():
    """获取数据质量错误日志"""
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        limit = request.args.get('limit', 100, type=int)
        error_type = request.args.get('error_type')
        
        errors = validator.get_error_log(limit=limit, error_type=error_type)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'errors': errors,
                'total': len(errors)
            }
        })
        
    except Exception as e:
        logger.error(f'获取错误日志失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/data-quality/alerts', methods=['GET'])
def get_quality_alerts():
    """获取当前质量报警"""
    try:
        from utils.data_validator import get_validator
        validator = get_validator()
        
        reports = validator.get_quality_reports(limit=1)
        
        if not reports:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'alerts': [],
                    'status': 'no_data'
                }
            })
        
        latest_report = reports[-1]
        alerts = latest_report.get('alerts', [])
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'alerts': alerts,
                'status': latest_report['summary']['status'],
                'generated_at': latest_report['generated_at']
            }
        })
        
    except Exception as e:
        logger.error(f'获取质量报警失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@weibo_bp.route('/dataflow/overview', methods=['GET'])
def get_dataflow_overview():
    """
    获取数据流概览
    
    展示完整数据流的状态：
    微博爬虫 → HDFS原始存储 → Spark清洗 → HBase结构化 → 三维度排序
    """
    try:
        from services.spark_service import get_spark_service
        spark_service = get_spark_service()
        
        # 统计采集任务
        total_crawl_tasks = len(crawl_tasks)
        completed_crawl = sum(1 for t in crawl_tasks.values() if t.get('status') == 'completed')
        running_crawl = sum(1 for t in crawl_tasks.values() if t.get('status') in ['crawling', 'running'])
        
        # 统计Spark作业
        spark_jobs = spark_service.get_all_jobs()
        
        # 统计数据量
        raw_dir = os.path.join(DATA_DIR, 'weibo_raw')
        total_raw_files = 0
        total_raw_records = 0
        if os.path.exists(raw_dir):
            for f in os.listdir(raw_dir):
                if f.endswith('.json'):
                    total_raw_files += 1
                    try:
                        with open(os.path.join(raw_dir, f), 'r', encoding='utf-8') as file:
                            data = json.load(file)
                            total_raw_records += len(data) if isinstance(data, list) else 1
                    except:
                        pass
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'dataflow': {
                    'stages': [
                        {'name': '微博爬虫', 'status': 'active', 'count': total_crawl_tasks},
                        {'name': 'HDFS存储', 'status': 'active', 'count': total_raw_files},
                        {'name': 'Spark清洗', 'status': 'active', 'count': sum(1 for j in spark_jobs if j['job_type'] == 'data_cleaning')},
                        {'name': 'HBase存储', 'status': 'active', 'count': total_raw_records},
                        {'name': '三维度排序', 'status': 'active', 'count': sum(1 for j in spark_jobs if j['job_type'] == 'topic_ranking')},
                    ]
                },
                'crawl_stats': {
                    'total': total_crawl_tasks,
                    'completed': completed_crawl,
                    'running': running_crawl,
                    'failed': sum(1 for t in crawl_tasks.values() if t.get('status') == 'failed')
                },
                'spark_stats': {
                    'total': len(spark_jobs),
                    'running': sum(1 for j in spark_jobs if j['status'] == 'running'),
                    'completed': sum(1 for j in spark_jobs if j['status'] == 'completed'),
                    'failed': sum(1 for j in spark_jobs if j['status'] == 'failed')
                },
                'data_stats': {
                    'raw_files': total_raw_files,
                    'raw_records': total_raw_records,
                    'analysis_results': len(analysis_results)
                },
                'update_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'获取数据流概览失败: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500
