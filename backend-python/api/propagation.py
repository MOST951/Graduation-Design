"""
传播路径分析API
================
提供微博传播路径网络图数据

核心功能：
1. 提取转发关系构建传播网络
2. 计算用户影响力分数
3. 生成ECharts关系图数据
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import random
import os
import json
import math
import logging
from typing import Dict, List, Any
from collections import defaultdict

propagation_bp = Blueprint('propagation', __name__, url_prefix='/api/propagation')
logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def load_weibo_data() -> List[Dict]:
    """加载微博数据"""
    all_data = []
    try:
        for filename in os.listdir(DATA_DIR):
            if (filename.startswith('crawl_result_') or filename.startswith('demo_')) and filename.endswith('.json'):
                filepath = os.path.join(DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            all_data.extend(data)
                except Exception as e:
                    logger.warning(f"加载文件 {filename} 失败: {e}")
    except Exception as e:
        logger.error(f"读取数据目录失败: {e}")
    return all_data


def generate_propagation_network(weibo_data: List[Dict], max_nodes: int = 50) -> Dict:
    """
    生成传播网络数据
    
    由于真实转发关系需要额外API调用，这里基于现有数据模拟传播网络：
    - 高转发量的微博作为传播源头
    - 根据用户粉丝数模拟传播层级
    """
    if not weibo_data:
        return {"nodes": [], "links": [], "categories": []}
    
    # 按转发量排序，取前N条作为传播源
    sorted_data = sorted(weibo_data, key=lambda x: x.get('reposts_count', 0), reverse=True)
    top_weibos = sorted_data[:min(5, len(sorted_data))]
    
    nodes = []
    links = []
    node_ids = set()
    
    # 定义节点类别
    categories = [
        {"name": "原创博主", "itemStyle": {"color": "#e74c3c"}},
        {"name": "一级传播", "itemStyle": {"color": "#3498db"}},
        {"name": "二级传播", "itemStyle": {"color": "#2ecc71"}},
        {"name": "三级传播", "itemStyle": {"color": "#9b59b6"}},
    ]
    
    for weibo in top_weibos:
        user = weibo.get('user', {})
        user_id = user.get('id', f"user_{random.randint(1000, 9999)}")
        user_name = user.get('screen_name', '匿名用户')
        followers = user.get('followers_count', 1000)
        reposts = weibo.get('reposts_count', 0)
        
        if user_id in node_ids:
            continue
        
        # 添加原创博主节点
        nodes.append({
            "id": user_id,
            "name": user_name,
            "symbolSize": min(60, 20 + math.log(followers + 1) * 5),
            "category": 0,
            "value": followers,
            "label": {"show": True},
            "itemStyle": {"color": "#e74c3c"},
            "tooltip": f"粉丝: {followers}, 转发: {reposts}"
        })
        node_ids.add(user_id)
        
        # 模拟一级传播者（转发用户）
        level1_count = min(8, max(2, reposts // 50))
        for i in range(level1_count):
            l1_id = f"{user_id}_l1_{i}"
            l1_name = f"用户{random.randint(100, 999)}"
            l1_followers = random.randint(100, 5000)
            
            nodes.append({
                "id": l1_id,
                "name": l1_name,
                "symbolSize": min(40, 15 + math.log(l1_followers + 1) * 3),
                "category": 1,
                "value": l1_followers,
                "itemStyle": {"color": "#3498db"},
            })
            node_ids.add(l1_id)
            
            links.append({
                "source": user_id,
                "target": l1_id,
                "value": random.randint(1, 5),
                "lineStyle": {"width": 2, "curveness": 0.2}
            })
            
            # 模拟二级传播者
            level2_count = min(4, random.randint(1, 3))
            for j in range(level2_count):
                l2_id = f"{l1_id}_l2_{j}"
                l2_name = f"用户{random.randint(100, 999)}"
                l2_followers = random.randint(50, 2000)
                
                nodes.append({
                    "id": l2_id,
                    "name": l2_name,
                    "symbolSize": min(30, 10 + math.log(l2_followers + 1) * 2),
                    "category": 2,
                    "value": l2_followers,
                    "itemStyle": {"color": "#2ecc71"},
                })
                node_ids.add(l2_id)
                
                links.append({
                    "source": l1_id,
                    "target": l2_id,
                    "value": random.randint(1, 3),
                    "lineStyle": {"width": 1.5, "curveness": 0.2}
                })
                
                # 模拟三级传播者（少量）
                if random.random() > 0.6:
                    l3_id = f"{l2_id}_l3_0"
                    l3_name = f"用户{random.randint(100, 999)}"
                    l3_followers = random.randint(20, 500)
                    
                    nodes.append({
                        "id": l3_id,
                        "name": l3_name,
                        "symbolSize": 15,
                        "category": 3,
                        "value": l3_followers,
                        "itemStyle": {"color": "#9b59b6"},
                    })
                    node_ids.add(l3_id)
                    
                    links.append({
                        "source": l2_id,
                        "target": l3_id,
                        "value": 1,
                        "lineStyle": {"width": 1, "curveness": 0.2}
                    })
        
        # 限制节点数量
        if len(nodes) >= max_nodes:
            break
    
    return {
        "nodes": nodes[:max_nodes],
        "links": links,
        "categories": categories
    }


def calculate_influence_score(user_data: Dict) -> float:
    """
    计算用户影响力分数
    
    公式: influence = 0.4 * log(followers+1) + 0.3 * log(reposts+1) + 0.2 * log(comments+1) + 0.1 * verified_bonus
    """
    followers = user_data.get('followers_count', 0)
    reposts = user_data.get('total_reposts', 0)
    comments = user_data.get('total_comments', 0)
    verified = user_data.get('verified', False)
    
    score = (
        0.4 * math.log(followers + 1) +
        0.3 * math.log(reposts + 1) +
        0.2 * math.log(comments + 1) +
        (0.1 * 10 if verified else 0)
    )
    
    # 归一化到0-100
    return min(100, round(score * 10, 2))


@propagation_bp.route('/network', methods=['GET'])
def get_propagation_network():
    """获取传播路径网络图数据"""
    try:
        max_nodes = request.args.get('max_nodes', 50, type=int)
        
        weibo_data = load_weibo_data()
        network = generate_propagation_network(weibo_data, max_nodes)
        
        return jsonify({
            'code': 200,
            'success': True,
            'message': '获取传播网络成功',
            'data': {
                'network': network,
                'stats': {
                    'total_nodes': len(network['nodes']),
                    'total_links': len(network['links']),
                    'source_count': len([n for n in network['nodes'] if n.get('category') == 0]),
                }
            }
        })
    except Exception as e:
        logger.error(f"获取传播网络失败: {e}")
        return jsonify({
            'code': 500,
            'success': False,
            'message': f'获取传播网络失败: {str(e)}'
        }), 500


@propagation_bp.route('/influence-ranking', methods=['GET'])
def get_influence_ranking():
    """获取用户影响力排行榜"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        weibo_data = load_weibo_data()
        
        # 聚合用户数据
        user_stats = defaultdict(lambda: {
            'user_id': '',
            'screen_name': '',
            'followers_count': 0,
            'verified': False,
            'total_reposts': 0,
            'total_comments': 0,
            'total_likes': 0,
            'weibo_count': 0,
            'location': ''
        })
        
        for weibo in weibo_data:
            user = weibo.get('user', {})
            user_id = user.get('id', '')
            if not user_id:
                continue
            
            stats = user_stats[user_id]
            stats['user_id'] = user_id
            stats['screen_name'] = user.get('screen_name', '匿名用户')
            stats['followers_count'] = max(stats['followers_count'], user.get('followers_count', 0))
            stats['verified'] = user.get('verified', False)
            stats['total_reposts'] += weibo.get('reposts_count', 0)
            stats['total_comments'] += weibo.get('comments_count', 0)
            stats['total_likes'] += weibo.get('attitudes_count', 0)
            stats['weibo_count'] += 1
            stats['location'] = user.get('location', '')
        
        # 计算影响力分数并排序
        ranking = []
        for user_id, stats in user_stats.items():
            influence_score = calculate_influence_score(stats)
            ranking.append({
                **stats,
                'influence_score': influence_score
            })
        
        ranking.sort(key=lambda x: x['influence_score'], reverse=True)
        
        return jsonify({
            'code': 200,
            'success': True,
            'message': '获取影响力排行成功',
            'data': {
                'ranking': ranking[:limit],
                'total_users': len(ranking)
            }
        })
    except Exception as e:
        logger.error(f"获取影响力排行失败: {e}")
        return jsonify({
            'code': 500,
            'success': False,
            'message': f'获取影响力排行失败: {str(e)}'
        }), 500


@propagation_bp.route('/user-profile/<user_id>', methods=['GET'])
def get_user_profile(user_id: str):
    """获取用户画像详情"""
    try:
        weibo_data = load_weibo_data()
        
        # 查找用户数据
        user_weibos = [w for w in weibo_data if w.get('user', {}).get('id') == user_id]
        
        if not user_weibos:
            return jsonify({
                'code': 404,
                'success': False,
                'message': '用户不存在'
            }), 404
        
        user = user_weibos[0].get('user', {})
        
        # 统计用户数据
        total_reposts = sum(w.get('reposts_count', 0) for w in user_weibos)
        total_comments = sum(w.get('comments_count', 0) for w in user_weibos)
        total_likes = sum(w.get('attitudes_count', 0) for w in user_weibos)
        
        # 情感分布
        sentiment_dist = {'positive': 0, 'negative': 0, 'neutral': 0}
        for w in user_weibos:
            sentiment = w.get('expected_sentiment', 'neutral')
            sentiment_dist[sentiment] = sentiment_dist.get(sentiment, 0) + 1
        
        profile = {
            'user_id': user_id,
            'screen_name': user.get('screen_name', '匿名用户'),
            'followers_count': user.get('followers_count', 0),
            'friends_count': user.get('friends_count', 0),
            'verified': user.get('verified', False),
            'location': user.get('location', '未知'),
            'weibo_count': len(user_weibos),
            'total_reposts': total_reposts,
            'total_comments': total_comments,
            'total_likes': total_likes,
            'avg_engagement': round((total_reposts + total_comments + total_likes) / max(1, len(user_weibos)), 2),
            'sentiment_distribution': sentiment_dist,
            'influence_score': calculate_influence_score({
                'followers_count': user.get('followers_count', 0),
                'total_reposts': total_reposts,
                'total_comments': total_comments,
                'verified': user.get('verified', False)
            })
        }
        
        return jsonify({
            'code': 200,
            'success': True,
            'message': '获取用户画像成功',
            'data': profile
        })
    except Exception as e:
        logger.error(f"获取用户画像失败: {e}")
        return jsonify({
            'code': 500,
            'success': False,
            'message': f'获取用户画像失败: {str(e)}'
        }), 500
