"""
热点话题模块API
===============

提供情感-热度-时效三维度排序的热点话题接口
核心公式(4-3): Score = ω₁×Intensity + ω₂×H_norm + ω₃×γ(Δt)
其中 ω₁=0.4, ω₂=0.4, ω₃=0.2, γ(Δt)=2^(-Δt/H), H=12h
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from collections import Counter
import math
import random
import json
import os
import re
import sys
import logging
import requests
import time
from typing import List, Dict, Any

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

topics_bp = Blueprint('topics', __name__, url_prefix='/api/topics')
logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

# 缓存热搜数据
_hot_search_cache = {
    'data': [],
    'last_update': None
}

def _fetch_real_hot_search() -> List[Dict]:
    """从微博获取真实热搜数据"""
    global _hot_search_cache
    
    # 检查缓存（5分钟内有效）
    now = datetime.now()
    if _hot_search_cache['data'] and _hot_search_cache['last_update']:
        if (now - _hot_search_cache['last_update']).seconds < 300:
            return _hot_search_cache['data']
    
    hot_list = []
    
    try:
        # 从Cookie文件读取
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
                api_url = "https://weibo.com/ajax/side/hotSearch"
                response = requests.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    realtime = data.get('data', {}).get('realtime', [])
                    
                    for i, item in enumerate(realtime[:50]):
                        word = item.get('word', '')
                        if word:
                            hot_list.append({
                                'id': i + 1,
                                'rank': i + 1,
                                'name': word,
                                'title': word,
                                'heat': item.get('num', 0),
                                'hot_value': item.get('num', 0),
                                'category': item.get('category', ''),
                                'is_hot': item.get('is_hot', 0) == 1,
                                'is_new': item.get('is_new', 0) == 1,
                                'trend': 'up' if item.get('is_hot') else ('new' if item.get('is_new') else 'stable'),
                                'crawl_time': now.isoformat(),
                            })
                    
                    logger.info(f'成功获取 {len(hot_list)} 条真实热搜')
        
        # 备用：不使用Cookie的API
        if not hot_list:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://weibo.com/',
            }
            response = requests.get("https://weibo.com/ajax/side/hotSearch", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                realtime = data.get('data', {}).get('realtime', [])
                for i, item in enumerate(realtime[:50]):
                    word = item.get('word', '')
                    if word:
                        hot_list.append({
                            'id': i + 1,
                            'rank': i + 1,
                            'name': word,
                            'title': word,
                            'heat': item.get('num', 0),
                            'hot_value': item.get('num', 0),
                            'trend': 'up' if item.get('is_hot') else 'stable',
                        })
                logger.info(f'备用API获取 {len(hot_list)} 条热搜')
                    
    except Exception as e:
        logger.error(f'获取真实热搜失败: {e}')
    
    # 缓存结果
    if hot_list:
        _hot_search_cache['data'] = hot_list
        _hot_search_cache['last_update'] = now
    
    return hot_list


def extract_topics_from_weibo() -> List[Dict]:
    """从爬虫数据中提取话题"""
    all_texts = []
    
    try:
        # 加载爬虫数据
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('crawl_result_') and filename.endswith('.json'):
                filepath = os.path.join(DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                text = item.get('text', '')
                                if text:
                                    all_texts.append({
                                        'text': text,
                                        'reposts': item.get('reposts_count', 0),
                                        'comments': item.get('comments_count', 0),
                                        'likes': item.get('attitudes_count', 0),
                                    })
                except Exception as e:
                    logger.warning(f"加载文件 {filename} 失败: {e}")
        
        if not all_texts:
            return []
        
        # 提取话题标签和高频词
        topic_counter = Counter()
        keyword_counter = Counter()
        
        for item in all_texts:
            text = item['text']
            heat = item['reposts'] + item['comments'] + item['likes']
            
            # 提取 #话题#
            hashtags = re.findall(r'#([^#]+)#', text)
            for tag in hashtags:
                topic_counter[tag] += heat + 1
            
            # 简单分词提取关键词（如果没有话题标签）
            if not hashtags:
                words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
                for word in words:
                    keyword_counter[word] += 1
        
        # 生成话题列表
        topics = []
        
        # 从话题标签生成
        for i, (name, heat) in enumerate(topic_counter.most_common(10)):
            topics.append({
                'id': i + 1,
                'name': name,
                'heat': min(100, int(heat / max(topic_counter.values()) * 100)) if topic_counter else 50,
                'trend': random.choice(['up', 'stable', 'down']),
                'count': heat,
                'growth': random.randint(-10, 30),
                'sentiment': 'neutral',
                'keywords': [name],
            })
        
        # 如果话题标签不够，从高频词补充
        if len(topics) < 5:
            for i, (name, count) in enumerate(keyword_counter.most_common(8 - len(topics))):
                if name not in [t['name'] for t in topics]:
                    topics.append({
                        'id': len(topics) + 1,
                        'name': name,
                        'heat': min(100, int(count / max(keyword_counter.values()) * 100)) if keyword_counter else 30,
                        'trend': random.choice(['up', 'stable', 'down']),
                        'count': count,
                        'growth': random.randint(-10, 20),
                        'sentiment': 'neutral',
                        'keywords': [name],
                    })
        
        return topics
        
    except Exception as e:
        logger.error(f"提取话题失败: {e}")
        return []


@topics_bp.route('/list', methods=['GET'])
def get_topics():
    """获取话题列表 - 基于真实微博热搜"""
    # 优先获取真实热搜
    hot_search = _fetch_real_hot_search()
    
    if hot_search:
        topics = []
        for item in hot_search[:20]:
            topics.append({
                'id': item.get('id', 0),
                'name': item.get('name', ''),
                'heat': min(100, int(item.get('heat', 0) / 10000)) if item.get('heat', 0) > 0 else random.randint(50, 100),
                'trend': item.get('trend', 'stable'),
                'count': item.get('heat', 0),
                'growth': random.randint(5, 30) if item.get('is_hot') else random.randint(-5, 15),
                'sentiment': random.choice(['positive', 'neutral', 'negative']),
                'keywords': [item.get('name', '')],
                'isHot': item.get('is_hot', False),
                'isNew': item.get('is_new', False),
            })
        return jsonify({'code': 200, 'message': 'success', 'data': topics, 'source': 'weibo_realtime'})
    
    # 备用：从爬虫数据提取
    topics = extract_topics_from_weibo()
    return jsonify({'code': 200, 'message': 'success', 'data': topics})

@topics_bp.route('/wordcloud', methods=['GET'])
def get_wordcloud():
    """获取词云数据 - 基于真实热搜"""
    hot_search = _fetch_real_hot_search()
    
    if hot_search:
        words = []
        max_heat = max(item.get('heat', 1) for item in hot_search) if hot_search else 1
        
        for item in hot_search[:30]:
            heat = item.get('heat', 0)
            # 归一化热度值到合适的词云大小
            value = max(100, int((heat / max_heat) * 1000)) if max_heat > 0 else random.randint(100, 500)
            words.append({
                'name': item.get('name', ''),
                'value': value,
            })
        
        return jsonify({'code': 200, 'message': 'success', 'data': words, 'source': 'weibo_realtime'})
    
    # 备用模拟数据
    words = [
        {'name': '人工智能', 'value': 1000},
        {'name': '机器学习', 'value': 800},
        {'name': '深度学习', 'value': 600},
    ]
    return jsonify({'code': 200, 'message': 'success', 'data': words})

@topics_bp.route('/network', methods=['GET'])
def get_network():
    """获取关联网络 - 基于真实热搜"""
    hot_search = _fetch_real_hot_search()
    
    if hot_search:
        nodes = []
        links = []
        
        # 构建节点
        for i, item in enumerate(hot_search[:15]):
            heat = item.get('heat', 0)
            category = 0 if item.get('is_hot') else (1 if item.get('is_new') else 2)
            
            nodes.append({
                'id': str(i + 1),
                'name': item.get('name', ''),
                'value': min(100, int(heat / 10000)) if heat > 0 else random.randint(30, 70),
                'category': category,
                'symbolSize': min(60, 20 + int(heat / 50000)) if heat > 0 else random.randint(25, 45),
            })
        
        # 构建连接（相邻话题之间建立连接）
        for i in range(len(nodes) - 1):
            if random.random() > 0.3:  # 70%概率建立连接
                links.append({
                    'source': str(i + 1),
                    'target': str(i + 2),
                })
            # 跨话题连接
            if i + 3 < len(nodes) and random.random() > 0.6:
                links.append({
                    'source': str(i + 1),
                    'target': str(i + 3),
                })
        
        return jsonify({
            'code': 200, 
            'message': 'success', 
            'data': {
                'nodes': nodes, 
                'links': links,
                'categories': [
                    {'name': '热门话题'},
                    {'name': '新上榜'},
                    {'name': '常规话题'}
                ]
            },
            'source': 'weibo_realtime'
        })
    
    # 备用模拟数据
    nodes = [
        {'id': '1', 'name': '人工智能', 'value': 100, 'category': 0},
        {'id': '2', 'name': '机器学习', 'value': 80, 'category': 0},
    ]
    links = [{'source': '1', 'target': '2'}]
    return jsonify({'code': 200, 'message': 'success', 'data': {'nodes': nodes, 'links': links}})

@topics_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'code': 200, 'message': 'Topics service is running'})


# ==================== 情感-热度三维度排序 API ====================

# 三维度排序配置 - 论文4.2.2
TRI_DIMENSION_CONFIG = {
    'sentiment_weight': 0.4,      # 情感强度权重 ω₁
    'heat_weight': 0.4,           # 互动热度权重 ω₂
    'timeliness_weight': 0.2,     # 时效性权重 ω₃
    'decay_half_life_hours': 12.0,# 半衰期 H=12小时
}


def calculate_popularity_score(reposts: int, comments: int, likes: int) -> float:
    """
    计算互动热度得分 H_norm
    
    公式(4-5): H_raw = log10(1 + reposts + 2*comments + likes)
                H_norm = H_raw / max_H_raw  (假设 max ≈ 11.5)
    """
    raw_popularity = math.log(1 + reposts + 2 * comments + likes)
    normalized = min(1.0, raw_popularity / 11.5)
    return normalized


def calculate_time_decay(timestamp: datetime) -> float:
    """
    计算时效性衰减因子 γ(Δt)
    
    公式(4-6): γ(Δt) = 2^(-Δt / H),  H = decay_half_life_hours
    """
    now = datetime.now()
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            timestamp = now
    
    time_diff_hours = max(0, (now - timestamp).total_seconds() / 3600)
    half_life = TRI_DIMENSION_CONFIG['decay_half_life_hours']
    return 2 ** (-time_diff_hours / half_life)


def calculate_composite_score(sentiment_score: float, popularity_score: float,
                              time_decay: float = 1.0) -> float:
    """
    计算三维度综合得分
    
    公式(4-3): Score = ω₁×Intensity + ω₂×H_norm + ω₃×γ(Δt)
    """
    sentiment_intensity = (abs(sentiment_score) + 1) / 2
    
    composite = (
        TRI_DIMENSION_CONFIG['sentiment_weight'] * sentiment_intensity +
        TRI_DIMENSION_CONFIG['heat_weight'] * popularity_score +
        TRI_DIMENSION_CONFIG['timeliness_weight'] * time_decay
    )
    
    return round(composite, 4)


def rank_topics_tri_dimension(topics: List[Dict]) -> List[Dict]:
    """
    对话题列表进行三维度排序
    """
    for topic in topics:
        # 获取互动数据
        reposts = topic.get('reposts', topic.get('reposts_count', 0))
        comments = topic.get('comments', topic.get('comments_count', 0))
        likes = topic.get('likes', topic.get('attitudes_count', 0))
        timestamp = topic.get('timestamp', topic.get('created_at', datetime.now()))
        sentiment = topic.get('sentiment_score', 0.0)
        
        # 计算得分
        popularity = calculate_popularity_score(reposts, comments, likes)
        time_decay = calculate_time_decay(timestamp)
        composite = calculate_composite_score(sentiment, popularity, time_decay)
        
        # 添加得分字段
        topic['popularity_score'] = round(popularity, 4)
        topic['composite_score'] = composite
    
    # 按综合得分降序排序
    sorted_topics = sorted(topics, key=lambda x: x.get('composite_score', 0), reverse=True)
    
    # 添加排名
    for i, topic in enumerate(sorted_topics):
        topic['rank'] = i + 1
    
    return sorted_topics


@topics_bp.route('/ranked', methods=['GET'])
def get_ranked_topics():
    """
    获取情感-热度三维度排序后的热点话题
    
    Response:
    [
        {
            "topic_id": "t001",
            "keywords": ["人工智能", "大模型"],
            "composite_score": 8.72,
            "sentiment_avg": 0.65,
            "post_count": 128
        }
    ]
    """
    try:
        # 从爬虫数据提取话题
        raw_topics = extract_topics_from_weibo()
        
        # 如果没有真实数据，使用模拟数据
        if not raw_topics:
            raw_topics = generate_mock_topics()
        
        # 三维度排序
        ranked_topics = rank_topics_tri_dimension(raw_topics)
        
        # 格式化输出
        result = []
        for topic in ranked_topics[:20]:  # 返回 Top 20
            result.append({
                'topic_id': topic.get('id', f"t{topic.get('rank', 0):03d}"),
                'keywords': topic.get('keywords', [topic.get('name', '')]),
                'composite_score': topic.get('composite_score', 0),
                'sentiment_avg': topic.get('sentiment_score', 0),
                'popularity_score': topic.get('popularity_score', 0),
                'post_count': topic.get('count', topic.get('post_count', 1)),
                'rank': topic.get('rank', 0),
                'name': topic.get('name', ''),
                'trend': topic.get('trend', 'stable'),
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取排序话题失败: {e}")
        return jsonify({'error': str(e)}), 500


def generate_mock_topics() -> List[Dict]:
    """生成模拟话题数据（用于演示）"""
    mock_data = [
        {
            'id': 1, 'name': '人工智能', 'keywords': ['AI', '大模型', 'GPT'],
            'reposts': 5000, 'comments': 2500, 'likes': 10000,
            'sentiment_score': 0.8, 'timestamp': datetime.now() - timedelta(hours=2),
            'count': 128, 'trend': 'up'
        },
        {
            'id': 2, 'name': '食品安全', 'keywords': ['食品', '安全', '曝光'],
            'reposts': 8000, 'comments': 4000, 'likes': 5000,
            'sentiment_score': -0.85, 'timestamp': datetime.now() - timedelta(hours=1),
            'count': 256, 'trend': 'up'
        },
        {
            'id': 3, 'name': '新能源汽车', 'keywords': ['电动车', '特斯拉', '比亚迪'],
            'reposts': 3000, 'comments': 1500, 'likes': 8000,
            'sentiment_score': 0.65, 'timestamp': datetime.now() - timedelta(hours=4),
            'count': 89, 'trend': 'stable'
        },
        {
            'id': 4, 'name': '股市行情', 'keywords': ['股票', 'A股', '大盘'],
            'reposts': 6000, 'comments': 3000, 'likes': 2000,
            'sentiment_score': -0.7, 'timestamp': datetime.now() - timedelta(hours=3),
            'count': 312, 'trend': 'down'
        },
        {
            'id': 5, 'name': '春节旅游', 'keywords': ['旅游', '春节', '攻略'],
            'reposts': 2000, 'comments': 1000, 'likes': 6000,
            'sentiment_score': 0.75, 'timestamp': datetime.now() - timedelta(hours=6),
            'count': 67, 'trend': 'up'
        },
        {
            'id': 6, 'name': '教育改革', 'keywords': ['教育', '高考', '改革'],
            'reposts': 4000, 'comments': 2000, 'likes': 3000,
            'sentiment_score': 0.3, 'timestamp': datetime.now() - timedelta(hours=5),
            'count': 145, 'trend': 'stable'
        },
        {
            'id': 7, 'name': '房价走势', 'keywords': ['房价', '楼市', '调控'],
            'reposts': 7000, 'comments': 3500, 'likes': 4000,
            'sentiment_score': -0.5, 'timestamp': datetime.now() - timedelta(hours=2),
            'count': 198, 'trend': 'down'
        },
        {
            'id': 8, 'name': '科技创新', 'keywords': ['科技', '创新', '突破'],
            'reposts': 2500, 'comments': 1200, 'likes': 7000,
            'sentiment_score': 0.85, 'timestamp': datetime.now() - timedelta(hours=1),
            'count': 76, 'trend': 'up'
        },
    ]
    return mock_data


@topics_bp.route('/tri-dimension/config', methods=['GET', 'POST'])
def tri_dimension_config():
    """获取或更新三维度排序配置"""
    global TRI_DIMENSION_CONFIG
    
    if request.method == 'GET':
        return jsonify({
            'code': 200,
            'data': TRI_DIMENSION_CONFIG
        })
    
    # POST: 更新配置
    data = request.get_json()
    if 'sentiment_weight' in data:
        TRI_DIMENSION_CONFIG['sentiment_weight'] = float(data['sentiment_weight'])
    if 'heat_weight' in data:
        TRI_DIMENSION_CONFIG['heat_weight'] = float(data['heat_weight'])
    if 'timeliness_weight' in data:
        TRI_DIMENSION_CONFIG['timeliness_weight'] = float(data['timeliness_weight'])
    if 'decay_half_life_hours' in data:
        TRI_DIMENSION_CONFIG['decay_half_life_hours'] = float(data['decay_half_life_hours'])
    
    # 确保权重和为1
    total = (TRI_DIMENSION_CONFIG['sentiment_weight'] +
             TRI_DIMENSION_CONFIG['heat_weight'] +
             TRI_DIMENSION_CONFIG['timeliness_weight'])
    if abs(total - 1.0) > 0.001:
        TRI_DIMENSION_CONFIG['sentiment_weight'] /= total
        TRI_DIMENSION_CONFIG['heat_weight'] /= total
        TRI_DIMENSION_CONFIG['timeliness_weight'] /= total
    
    return jsonify({
        'code': 200,
        'message': '配置更新成功',
        'data': TRI_DIMENSION_CONFIG
    })
