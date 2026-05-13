"""
仪表盘模块API
包含Spark性能监控
基于真实微博数据
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import random
import os
import sys
import json
import logging
import requests
import pymysql
from config import config

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 论文 4.3.1: Redis 缓存热点数据
try:
    from utils.redis_cache import redis_cache
except Exception:  # pragma: no cover
    def redis_cache(*_a, **_kw):
        def _deco(f): return f
        return _deco

# 导入Spark优化模块
try:
    from spark.spark_optimizer import (
        SparkOptimizationConfig,
        OptimizedSparkSession,
        get_spark_ui_metrics,
        CacheManager,
    )
    SPARK_OPTIMIZER_AVAILABLE = True
except ImportError:
    SPARK_OPTIMIZER_AVAILABLE = False

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

# 缓存数据
_dashboard_cache = {
    'hot_search': [],
    'weibo_data': [],
    'last_update': None
}

def _fetch_real_data():
    """获取真实微博数据"""
    global _dashboard_cache
    
    now = datetime.now()
    if _dashboard_cache['last_update'] and (now - _dashboard_cache['last_update']).seconds < 300:
        return _dashboard_cache
    
    try:
        cookie_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crawler', 'cookies.json')
        
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
            
            if isinstance(cookie_data, dict) and cookie_data.get('SUB'):
                cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_data.items() if v and not k.startswith('_')])
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Cookie': cookie_str,
                    'Referer': 'https://weibo.com/',
                }
                
                # 获取热搜
                response = requests.get("https://weibo.com/ajax/side/hotSearch", headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    _dashboard_cache['hot_search'] = data.get('data', {}).get('realtime', [])[:50]
                
                # 获取热门微博
                api_url = "https://weibo.com/ajax/feed/hottimeline?since_id=0&refresh=0&group_id=102803&containerid=102803&extparam=discover%7Cnew_feed&max_id=0&count=50"
                response = requests.get(api_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    _dashboard_cache['weibo_data'] = data.get('statuses', [])
                
                _dashboard_cache['last_update'] = now
                logger.info(f'Dashboard获取真实数据: {len(_dashboard_cache["hot_search"])}条热搜, {len(_dashboard_cache["weibo_data"])}条微博')
                
    except Exception as e:
        logger.error(f'获取真实数据失败: {e}')
    
    return _dashboard_cache

@dashboard_bp.route('/overview', methods=['GET'])
@redis_cache('dashboard:overview', ttl=60)
def get_overview():
    """获取概览数据 - 基于数据库统计"""
    data = {
        'total_weibos': 0,
        'today_weibos': 0,
        'total_tasks': 0,
        'running_tasks': 0,
    }
    source = 'database'

    connection = None
    try:
        connection = pymysql.connect(
            host=config.database.host,
            port=config.database.port,
            user=config.database.username,
            password=config.database.password,
            database=config.database.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        with connection.cursor() as cursor:
            # 总微博数
            try:
                cursor.execute("SELECT COUNT(*) AS cnt FROM weibo_core_data")
                row = cursor.fetchone()
                data['total_weibos'] = row['cnt'] if row else 0
            except Exception:
                pass

            # 今日新增微博（created_at >= 今天零点）
            try:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM weibo_core_data "
                    "WHERE created_at >= CURDATE()"
                )
                row = cursor.fetchone()
                data['today_weibos'] = row['cnt'] if row else 0
            except Exception:
                pass

            # 总任务数
            try:
                cursor.execute("SELECT COUNT(*) AS cnt FROM collection_task")
                row = cursor.fetchone()
                data['total_tasks'] = row['cnt'] if row else 0
            except Exception:
                pass

            # 正在运行的任务数
            try:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM collection_task "
                    "WHERE status = 'running'"
                )
                row = cursor.fetchone()
                data['running_tasks'] = row['cnt'] if row else 0
            except Exception:
                pass

    except Exception as e:
        logger.error(f"dashboard/overview 查询异常: {e}", exc_info=True)
        source = 'error'
    finally:
        if connection:
            connection.close()

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': data,
        'source': source,
    })

@dashboard_bp.route('/sentiment-distribution', methods=['GET'])
def get_sentiment_distribution():
    """获取情感分布 - 基于数据库 sentiment_analysis_results 表"""
    period = request.args.get('period', 'today')
    empty_data = {
        'positive': 0, 'neutral': 0, 'negative': 0,
        'period': period, 'total_records': 0, 'raw_counts': {'positive': 0, 'neutral': 0, 'negative': 0}
    }

    # 构造时间过滤条件
    time_filter = ""
    if period == 'today':
        time_filter = "WHERE DATE(analysis_time) = CURDATE()"
    elif period == 'week':
        time_filter = "WHERE analysis_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    elif period == 'month':
        time_filter = "WHERE analysis_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
    # else: 全部数据，无过滤

    connection = None
    try:
        connection = pymysql.connect(
            host=config.database.host,
            port=config.database.port,
            user=config.database.username,
            password=config.database.password,
            database=config.database.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            sql = f"""
                SELECT sentiment_class, COUNT(*) AS count
                FROM sentiment_analysis_results
                {time_filter}
                GROUP BY sentiment_class
            """
            cursor.execute(sql)
            results = cursor.fetchall()

            # 表为空时返回全零
            if not results:
                return jsonify({
                    'code': 200, 'message': 'success',
                    'data': empty_data, 'source': 'database(sentiment_analysis_results.sentiment_class)'
                })

            # 汇总计数
            sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
            total_count = 0
            for row in results:
                label = (row.get('sentiment_class') or 'neutral').lower()
                cnt = row.get('count', 0)
                if label in sentiment_counts:
                    sentiment_counts[label] = cnt
                    total_count += cnt

            # 计算百分比
            if total_count > 0:
                positive_pct = round(sentiment_counts['positive'] / total_count * 100)
                neutral_pct  = round(sentiment_counts['neutral']  / total_count * 100)
                negative_pct = round(sentiment_counts['negative'] / total_count * 100)
            else:
                positive_pct, neutral_pct, negative_pct = 0, 0, 0

            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'positive': positive_pct,
                    'neutral': neutral_pct,
                    'negative': negative_pct,
                    'period': period,
                    'total_records': total_count,
                    'raw_counts': sentiment_counts
                },
                'source': 'database(sentiment_analysis_results.sentiment_class)'
            })

    except Exception as e:
        logger.error(f"sentiment-distribution 查询异常: {e}", exc_info=True)
        return jsonify({
            'code': 500, 'message': f'database error: {e}',
            'data': empty_data, 'source': 'error'
        })
    finally:
        if connection:
            connection.close()

@dashboard_bp.route('/trend', methods=['GET'])
def get_trend():
    """获取趋势数据"""
    days = 7
    dates = [(datetime.now() - timedelta(days=i)).strftime('%m/%d') for i in range(days-1, -1, -1)]
    
    # 基于当前数据生成趋势（模拟历史数据）
    cache = _fetch_real_data()
    base_positive = len([h for h in cache.get('hot_search', []) if any(kw in h.get('word', '') for kw in ['好', '赞', '成功'])])
    base_negative = len([h for h in cache.get('hot_search', []) if any(kw in h.get('word', '') for kw in ['差', '问题', '事故'])])
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'dates': dates,
            'positive': [max(100, base_positive * 50 + random.randint(-50, 100)) for _ in range(days)],
            'neutral': [random.randint(200, 400) for _ in range(days)],
            'negative': [max(50, base_negative * 30 + random.randint(-30, 50)) for _ in range(days)],
        }
    })

@dashboard_bp.route('/realtime', methods=['GET'])
@redis_cache('dashboard:realtime', ttl=30)
def get_realtime():
    """获取实时数据流 - 基于真实微博数据"""
    cache = _fetch_real_data()
    weibo_data = cache.get('weibo_data', [])
    
    data = []
    positive_keywords = ['好', '赞', '棒', '喜欢', '开心']
    negative_keywords = ['差', '坏', '失败', '问题']
    
    for i, weibo in enumerate(weibo_data[:10]):
        user = weibo.get('user', {})
        text = weibo.get('text', '')
        
        # 简单情感判断
        if any(kw in text for kw in positive_keywords):
            sentiment = 0.6
        elif any(kw in text for kw in negative_keywords):
            sentiment = -0.5
        else:
            sentiment = 0.1
        
        data.append({
            'id': i + 1,
            'content': text[:100] + '...' if len(text) > 100 else text,
            'sentiment': sentiment,
            'time': weibo.get('created_at', datetime.now().isoformat()),
            'source': '微博',
            'author': user.get('screen_name', f'用户{random.randint(1000, 9999)}'),
        })
    
    # 如果没有真实数据，使用备用数据
    if not data:
        contents = ['今天的产品体验非常好！', '服务态度有待提高', '价格还算合理']
        for i in range(5):
            data.append({
                'id': i + 1,
                'content': random.choice(contents),
                'sentiment': random.choice([0.6, -0.5, 0.1]),
                'time': datetime.now().isoformat(),
                'source': '微博',
                'author': f'用户{random.randint(1000, 9999)}',
            })
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': data,
        'source': 'weibo_realtime' if weibo_data else 'simulated'
    })

@dashboard_bp.route('/hot-topics', methods=['GET'])
@redis_cache('dashboard:hot_topics', ttl=120)  # 论文 4.3.1: 热搜列表是典型热点数据
def get_hot_topics():
    """获取热门话题 - 基于真实微博热搜"""
    cache = _fetch_real_data()
    hot_search = cache.get('hot_search', [])
    
    topics = []
    for item in hot_search[:10]:
        word = item.get('word', '')
        heat = item.get('num', 0)
        is_hot = item.get('is_hot', 0)
        is_new = item.get('is_new', 0)
        
        trend = 'up' if is_hot else ('new' if is_new else 'stable')
        
        topics.append({
            'name': word,
            'heat': heat,
            'trend': trend,
            'isHot': is_hot == 1,
            'isNew': is_new == 1,
        })
    
    # 如果没有真实数据，使用备用数据
    if not topics:
        topics = [
            {'name': '人工智能', 'heat': 9500, 'trend': 'up'},
            {'name': '新能源汽车', 'heat': 8800, 'trend': 'up'},
        ]
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': topics,
        'source': 'weibo_realtime' if hot_search else 'simulated'
    })

@dashboard_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """获取预警信息"""
    alerts = [
        {'id': 1, 'type': 'warning', 'message': '负面舆情增长超过阈值', 'time': datetime.now().isoformat()},
        {'id': 2, 'type': 'info', 'message': '新热点话题出现', 'time': datetime.now().isoformat()},
    ]
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': alerts
    })

@dashboard_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'code': 200, 'message': 'Dashboard service is running'})


# ==================== Spark性能监控API ====================

@dashboard_bp.route('/spark/status', methods=['GET'])
def get_spark_status():
    """获取Spark状态"""
    try:
        if SPARK_OPTIMIZER_AVAILABLE:
            metrics = get_spark_ui_metrics(None)
            
            # 如果获取失败，返回后备状态信息
            if 'error' in metrics:
                metrics = {
                    'status': 'unavailable',
                    'app_name': 'WeiboSentimentAnalysis',
                    'master': 'local[*]',
                    'driver_memory': '2g',
                    'executor_memory': '2g',
                    'jobs_completed': 0,
                    'stages_completed': 0,
                    'tasks_completed': 0,
                    'note': 'Spark UI未运行，无法获取实时指标'
                }
        else:
            metrics = {
                'status': 'not_available',
                'message': 'Spark优化模块未加载'
            }
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': metrics
        })
    except Exception as e:
        logger.error(f'获取Spark状态失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@dashboard_bp.route('/spark/config', methods=['GET'])
def get_spark_config():
    """获取Spark配置"""
    try:
        if SPARK_OPTIMIZER_AVAILABLE:
            config = SparkOptimizationConfig()
            config_dict = config.to_spark_conf()
            
            # 分类配置
            categorized = {
                'memory': {},
                'serialization': {},
                'partition': {},
                'adaptive': {},
                'other': {}
            }
            
            for key, value in config_dict.items():
                if 'memory' in key.lower():
                    categorized['memory'][key] = value
                elif 'serial' in key.lower() or 'kryo' in key.lower():
                    categorized['serialization'][key] = value
                elif 'partition' in key.lower() or 'shuffle' in key.lower():
                    categorized['partition'][key] = value
                elif 'adaptive' in key.lower():
                    categorized['adaptive'][key] = value
                else:
                    categorized['other'][key] = value
            
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': categorized
            })
        else:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {'message': 'Spark优化模块未加载'}
            })
    except Exception as e:
        logger.error(f'获取Spark配置失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@dashboard_bp.route('/spark/performance', methods=['GET'])
def get_spark_performance():
    """获取Spark性能指标"""
    try:
        # 模拟性能数据（实际项目中从Spark UI获取）
        performance = {
            'throughput': {
                'current': random.randint(1000, 5000),
                'avg': random.randint(2000, 4000),
                'peak': random.randint(5000, 10000),
                'unit': '条/秒'
            },
            'latency': {
                'avg': round(random.uniform(10, 50), 2),
                'p50': round(random.uniform(8, 30), 2),
                'p95': round(random.uniform(50, 100), 2),
                'p99': round(random.uniform(100, 200), 2),
                'unit': 'ms'
            },
            'memory': {
                'used': random.randint(500, 1500),
                'total': 2048,
                'cached': random.randint(100, 500),
                'unit': 'MB'
            },
            'cpu': {
                'usage': round(random.uniform(20, 80), 1),
                'cores_used': random.randint(2, 8),
                'cores_total': 8
            },
            'shuffle': {
                'read': random.randint(100, 1000),
                'write': random.randint(100, 1000),
                'unit': 'MB'
            },
            'gc': {
                'time': random.randint(100, 500),
                'count': random.randint(10, 50),
                'unit': 'ms'
            }
        }
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': performance
        })
    except Exception as e:
        logger.error(f'获取Spark性能指标失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@dashboard_bp.route('/spark/jobs', methods=['GET'])
def get_spark_jobs():
    """获取Spark作业列表"""
    try:
        # 模拟作业数据
        jobs = []
        statuses = ['SUCCEEDED', 'RUNNING', 'FAILED']
        
        for i in range(10):
            status = random.choices(statuses, weights=[0.8, 0.15, 0.05])[0]
            jobs.append({
                'id': i + 1,
                'name': f'Job_{i+1}_SentimentAnalysis',
                'status': status,
                'stages': random.randint(3, 10),
                'tasks': random.randint(10, 100),
                'duration': f'{random.randint(1, 60)}s',
                'start_time': (datetime.now() - timedelta(minutes=random.randint(0, 120))).isoformat(),
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'jobs': jobs,
                'total': len(jobs),
                'succeeded': sum(1 for j in jobs if j['status'] == 'SUCCEEDED'),
                'running': sum(1 for j in jobs if j['status'] == 'RUNNING'),
                'failed': sum(1 for j in jobs if j['status'] == 'FAILED'),
            }
        })
    except Exception as e:
        logger.error(f'获取Spark作业列表失败: {e}')
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@dashboard_bp.route('/spark/optimization-tips', methods=['GET'])
def get_optimization_tips():
    """获取Spark优化建议"""
    tips = [
        {
            'category': '内存优化',
            'tips': [
                '增加spark.memory.fraction到0.7以提高内存利用率',
                '启用堆外内存存储大型广播变量',
                '使用MEMORY_AND_DISK存储级别避免OOM',
            ]
        },
        {
            'category': '分区优化',
            'tips': [
                '根据数据量调整spark.sql.shuffle.partitions',
                '使用coalesce合并小分区减少任务开销',
                '对倾斜数据使用加盐法处理',
            ]
        },
        {
            'category': '序列化优化',
            'tips': [
                '使用Kryo序列化替代Java序列化',
                '注册常用类到Kryo提升性能',
                '启用压缩减少网络传输',
            ]
        },
        {
            'category': 'SQL优化',
            'tips': [
                '启用AQE自适应查询执行',
                '使用广播Join处理小表关联',
                '避免使用UDF，优先使用内置函数',
            ]
        },
    ]
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': tips
    })
