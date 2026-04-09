"""
用户行为分析模块API
基于真实微博数据进行用户行为分析
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import random
import os
import sys
import logging

# 添加路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

# 导入爬虫模块
try:
    from crawler.weibo_crawler import WeiboCrawler
    CRAWLER_AVAILABLE = True
except ImportError:
    CRAWLER_AVAILABLE = False

behavior_bp = Blueprint('behavior', __name__, url_prefix='/api/behavior')

# 缓存真实用户数据
_user_cache = {
    'users': [],
    'last_update': None
}

def _fetch_real_users(limit: int = 20) -> list:
    """从微博获取真实用户数据"""
    global _user_cache
    import requests
    import time
    
    # 检查缓存（5分钟内有效）
    now = datetime.now()
    if _user_cache['users'] and _user_cache['last_update']:
        if (now - _user_cache['last_update']).seconds < 300:
            logger.info(f'使用缓存的用户数据: {len(_user_cache["users"])} 个')
            return _user_cache['users'][:limit]
    
    users = []
    
    # 直接从Cookie文件读取
    try:
        import json
        cookie_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crawler', 'cookies.json')
        logger.info(f'读取Cookie文件: {cookie_file}')
        
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
                
            if isinstance(cookie_data, dict) and cookie_data.get('SUB'):
                cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_data.items() if v and not k.startswith('_')])
                logger.info(f'Cookie加载成功')
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Cookie': cookie_str,
                    'Referer': 'https://weibo.com/',
                }
                
                # 获取热门微博用户 - 使用多个API尝试
                apis = [
                    "https://weibo.com/ajax/feed/hottimeline?since_id=0&refresh=0&group_id=102803&containerid=102803&extparam=discover%7Cnew_feed&max_id=0&count=50",
                    "https://weibo.com/ajax/statuses/friends_timeline?since_id=0&count=50",
                ]
                
                response = None
                for api_url in apis:
                    time.sleep(1)
                    try:
                        response = requests.get(api_url, headers=headers, timeout=15)
                        logger.info(f'API响应状态码: {response.status_code} - {api_url[:50]}')
                        if response.status_code == 200:
                            break
                    except Exception as e:
                        logger.warning(f'API请求失败: {e}')
                        continue
                
                if not response or response.status_code != 200:
                    logger.warning('所有API请求失败')
                    return users
                
                if response.status_code == 200:
                    data = response.json()
                    statuses = data.get('statuses', [])
                    logger.info(f'获取到 {len(statuses)} 条微博')
                    
                    seen_users = set()
                    for weibo in statuses:
                        user_info = weibo.get('user', {})
                        screen_name = user_info.get('screen_name', '')
                        user_id = user_info.get('id', 0)
                        
                        if screen_name and user_id not in seen_users:
                            seen_users.add(user_id)
                            followers = user_info.get('followers_count', 0)
                            
                            # 根据粉丝数判断用户类型
                            if followers >= 100000:
                                user_type = 'kol'
                                activity = '高'
                            elif followers >= 10000:
                                user_type = 'active'
                                activity = '高'
                            elif followers >= 1000:
                                user_type = 'active'
                                activity = '中'
                            else:
                                user_type = 'normal'
                                activity = '低'
                            
                            # 计算影响力指数
                            influence = min(100, int(50 + (followers / 10000) * 5))
                            
                            users.append({
                                'id': user_id,
                                'name': screen_name,
                                'avatar': user_info.get('avatar_hd', '') or user_info.get('profile_image_url', '') or 'https://tvax1.sinaimg.cn/default/images/default_avatar_male_180.gif',
                                'followers': followers,
                                'following': user_info.get('friends_count', 0),
                                'influence': influence,
                                'activity': activity,
                                'type': user_type,
                                'verified': user_info.get('verified', False),
                                'description': user_info.get('description', ''),
                                'location': user_info.get('location', ''),
                                'statuses_count': user_info.get('statuses_count', 0),
                            })
                            logger.info(f'真实用户: @{screen_name} (粉丝: {followers})')
                            
                            if len(users) >= limit:
                                break
                    
                    logger.info(f'成功获取 {len(users)} 个真实微博用户')
                    
    except Exception as e:
        logger.error(f'获取真实用户数据失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
    
    # 缓存结果
    if users:
        _user_cache['users'] = users
        _user_cache['last_update'] = now
    
    return users[:limit]

@behavior_bp.route('/users', methods=['GET'])
def get_users():
    """获取用户列表 - 基于真实微博数据"""
    limit = request.args.get('limit', 20, type=int)
    user_type = request.args.get('type', '')  # kol, active, normal
    
    users = _fetch_real_users(50)  # 获取更多用户以便筛选
    
    # 按类型筛选
    if user_type:
        types = user_type.split(',')
        users = [u for u in users if u.get('type') in types]
    
    return jsonify({
        'code': 200, 
        'message': 'success', 
        'data': users[:limit],
        'meta': {
            'total': len(users),
            'source': 'weibo_realtime'
        }
    })

@behavior_bp.route('/network', methods=['GET'])
def get_network():
    """获取影响力网络 - 基于真实用户数据"""
    users = _fetch_real_users(20)
    
    if not users:
        # 返回空网络
        return jsonify({'code': 200, 'message': 'success', 'data': {'nodes': [], 'links': []}})
    
    # 按粉丝数排序
    users_sorted = sorted(users, key=lambda x: x.get('followers', 0), reverse=True)
    
    nodes = []
    links = []
    
    # 构建节点
    for i, user in enumerate(users_sorted[:15]):
        followers = user.get('followers', 0)
        
        # 根据粉丝数确定节点大小和类别
        if followers >= 100000:
            category = 0  # KOL
            symbol_size = min(80, 40 + followers // 50000)
        elif followers >= 10000:
            category = 1  # 活跃用户
            symbol_size = min(50, 30 + followers // 10000)
        else:
            category = 2  # 普通用户
            symbol_size = max(20, 15 + followers // 5000)
        
        nodes.append({
            'name': user.get('name', ''),
            'value': followers,
            'category': category,
            'symbolSize': symbol_size,
            'id': str(user.get('id', i)),
            'verified': user.get('verified', False),
        })
    
    # 构建连接关系（基于影响力层级）
    kol_nodes = [n for n in nodes if n['category'] == 0]
    active_nodes = [n for n in nodes if n['category'] == 1]
    normal_nodes = [n for n in nodes if n['category'] == 2]
    
    # KOL之间的连接
    for i, kol in enumerate(kol_nodes):
        for other_kol in kol_nodes[i+1:i+3]:
            links.append({'source': kol['name'], 'target': other_kol['name']})
    
    # KOL连接活跃用户
    for kol in kol_nodes[:3]:
        for active in active_nodes[:4]:
            links.append({'source': kol['name'], 'target': active['name']})
    
    # 活跃用户连接普通用户
    for active in active_nodes[:3]:
        for normal in normal_nodes[:3]:
            links.append({'source': active['name'], 'target': normal['name']})
    
    return jsonify({
        'code': 200, 
        'message': 'success', 
        'data': {
            'nodes': nodes, 
            'links': links,
            'categories': [
                {'name': 'KOL'},
                {'name': '活跃用户'},
                {'name': '普通用户'}
            ]
        }
    })

@behavior_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取用户统计数据"""
    users = _fetch_real_users(50)
    
    kol_count = len([u for u in users if u.get('type') == 'kol'])
    active_count = len([u for u in users if u.get('type') == 'active'])
    normal_count = len([u for u in users if u.get('type') == 'normal'])
    
    total_followers = sum(u.get('followers', 0) for u in users)
    avg_followers = total_followers // len(users) if users else 0
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'totalUsers': len(users),
            'kolCount': kol_count,
            'activeCount': active_count,
            'normalCount': normal_count,
            'totalFollowers': total_followers,
            'avgFollowers': avg_followers,
            'verifiedCount': len([u for u in users if u.get('verified')]),
        }
    })

@behavior_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'code': 200, 'message': 'Behavior service is running'})
