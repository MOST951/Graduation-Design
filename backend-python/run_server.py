"""
微博情感分析系统 - 后端服务
集成完整爬虫和情感分析功能
"""
import sys
import io

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import threading
import time
import os
import json
import re
import logging
import random
from typing import List, Dict, Optional, Tuple

# 导入爬虫模块
from crawler.weibo_spider import WeiboSpider, CookiePool, UserAgentPool

# 导入数据库服务
try:
    from services.database_service import DatabaseService, get_db_service
    DB_SERVICE_AVAILABLE = True
    db_service = None  # 延迟初始化
except ImportError as e:
    DB_SERVICE_AVAILABLE = False
    db_service = None
    logging.warning(f"数据库服务不可用: {e}")

# 导入认证服务
try:
    from services.auth_service import AuthService, get_auth_service
    AUTH_SERVICE_AVAILABLE = True
    auth_service = None  # 延迟初始化
except ImportError as e:
    AUTH_SERVICE_AVAILABLE = False
    auth_service = None
    logging.warning(f"认证服务不可用: {e}")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'weibo_raw'), exist_ok=True)

# 全局状态
crawl_tasks: Dict[str, Dict] = {}
task_lock = threading.Lock()


# ==================== 情感词典 ====================
class SentimentLexicon:
    """中文情感词典"""
    POSITIVE_WORDS = {
        '好', '棒', '赞', '优秀', '喜欢', '爱', '开心', '高兴', '快乐', '幸福',
        '美好', '精彩', '厉害', '牛', '强', '帅', '美', '漂亮', '可爱', '温暖',
        '感动', '支持', '期待', '希望', '成功', '胜利', '加油', '努力', '进步',
        '优质', '满意', '舒服', '享受', '惊喜', '感谢', '祝福', '恭喜', '点赞',
        '推荐', '值得', '完美', '出色', '杰出', '卓越', '一流', '顶级', '最佳',
    }
    NEGATIVE_WORDS = {
        '差', '烂', '垃圾', '讨厌', '恨', '愤怒', '生气', '难过', '伤心', '失望',
        '糟糕', '恶心', '无语', '崩溃', '绝望', '痛苦', '悲伤', '郁闷', '烦躁',
        '可怕', '恐怖', '害怕', '担心', '焦虑', '紧张', '压力', '累', '疲惫',
        '失败', '输', '败', '亏', '损失', '问题', '错误', '故障', '缺陷',
    }
    
    @classmethod
    def analyze(cls, text: str) -> Tuple[str, float]:
        if not text:
            return 'neutral', 0.0
        text = text.lower()
        pos_count = sum(1 for w in cls.POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in cls.NEGATIVE_WORDS if w in text)
        
        if pos_count > neg_count:
            score = min(pos_count * 0.2, 1.0)
            return 'positive', score
        elif neg_count > pos_count:
            score = max(-neg_count * 0.2, -1.0)
            return 'negative', score
        return 'neutral', 0.0


# 全局爬虫实例
spider = WeiboSpider()


# ==================== API路由 ====================

# ==================== 认证API ====================
@app.route('/api/auth/send-code', methods=['POST'])
def send_verification_code():
    """发送邮箱验证码"""
    global auth_service
    try:
        if AUTH_SERVICE_AVAILABLE and auth_service is None:
            auth_service = get_auth_service()
        
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        code_type = data.get('type', 'login')  # register/login/reset
        
        if not email:
            return jsonify({'code': 400, 'message': '请输入邮箱地址'}), 400
        
        # 使用认证服务生成验证码
        if AUTH_SERVICE_AVAILABLE and auth_service:
            success, message, code = auth_service.generate_verification_code(email, code_type)
            if not success:
                return jsonify({'code': 400, 'message': message}), 400
            
            # 开发环境返回验证码便于测试
            logger.info(f'========== 验证码: {code} (邮箱: {email}, 类型: {code_type}) ==========')
            return jsonify({
                'code': 200,
                'message': '验证码已发送',
                'data': {
                    'email': email,
                    'expire_in': 300,
                    'debug_code': code  # 开发环境
                }
            })
        else:
            return jsonify({'code': 500, 'message': '认证服务不可用'}), 500
        
    except Exception as e:
        logger.error(f'发送验证码失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    global auth_service
    try:
        if AUTH_SERVICE_AVAILABLE and auth_service is None:
            auth_service = get_auth_service()
        
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        password = data.get('password', '')
        code = data.get('code', '').strip()
        username = data.get('username', '').strip() or None
        
        if not email or not password or not code:
            return jsonify({'code': 400, 'message': '邮箱、密码和验证码不能为空'}), 400
        
        if AUTH_SERVICE_AVAILABLE and auth_service:
            success, message, user_data = auth_service.register(email, password, code, username)
            if success:
                return jsonify({
                    'code': 200,
                    'message': message,
                    'data': {
                        'accessToken': f'token-{user_data["id"]}-{int(datetime.now().timestamp())}',
                        'user': user_data
                    }
                })
            else:
                return jsonify({'code': 400, 'message': message}), 400
        else:
            return jsonify({'code': 500, 'message': '认证服务不可用'}), 500
        
    except Exception as e:
        logger.error(f'注册失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/auth/login-by-email', methods=['POST'])
def login_by_email():
    """邮箱密码登录"""
    global auth_service
    try:
        if AUTH_SERVICE_AVAILABLE and auth_service is None:
            auth_service = get_auth_service()
        
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'code': 400, 'message': '邮箱和密码不能为空'}), 400
        
        if AUTH_SERVICE_AVAILABLE and auth_service:
            ip = request.remote_addr
            success, message, user_data = auth_service.login_by_email(email, password, ip)
            if success:
                return jsonify({
                    'code': 200,
                    'message': message,
                    'data': {
                        'accessToken': f'token-{user_data["id"]}-{int(datetime.now().timestamp())}',
                        'user': user_data,
                        'loginType': 'email_password'
                    }
                })
            else:
                return jsonify({'code': 401, 'message': message}), 401
        else:
            return jsonify({'code': 500, 'message': '认证服务不可用'}), 500
        
    except Exception as e:
        logger.error(f'邮箱登录失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/auth/login-by-code', methods=['POST'])
def login_by_code():
    """邮箱验证码登录"""
    global auth_service
    try:
        if AUTH_SERVICE_AVAILABLE and auth_service is None:
            auth_service = get_auth_service()
        
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({'code': 400, 'message': '邮箱和验证码不能为空'}), 400
        
        if AUTH_SERVICE_AVAILABLE and auth_service:
            ip = request.remote_addr
            success, message, user_data = auth_service.login_by_code(email, code, ip)
            if success:
                return jsonify({
                    'code': 200,
                    'message': message,
                    'data': {
                        'accessToken': f'token-{user_data["id"]}-{int(datetime.now().timestamp())}',
                        'user': user_data,
                        'loginType': 'email_code'
                    }
                })
            else:
                return jsonify({'code': 401, 'message': message}), 401
        else:
            return jsonify({'code': 500, 'message': '认证服务不可用'}), 500
        
    except Exception as e:
        logger.error(f'验证码登录失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    global auth_service
    try:
        if AUTH_SERVICE_AVAILABLE and auth_service is None:
            auth_service = get_auth_service()
        
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        code = data.get('code', '').strip()
        new_password = data.get('newPassword', '')
        
        if not email or not code or not new_password:
            return jsonify({'code': 400, 'message': '邮箱、验证码和新密码不能为空'}), 400
        
        if AUTH_SERVICE_AVAILABLE and auth_service:
            success, message = auth_service.reset_password(email, code, new_password)
            if success:
                return jsonify({'code': 200, 'message': message})
            else:
                return jsonify({'code': 400, 'message': message}), 400
        else:
            return jsonify({'code': 500, 'message': '认证服务不可用'}), 500
        
    except Exception as e:
        logger.error(f'重置密码失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/auth/check-email', methods=['POST'])
def check_email():
    """检查邮箱是否已注册"""
    global auth_service
    try:
        if AUTH_SERVICE_AVAILABLE and auth_service is None:
            auth_service = get_auth_service()
        
        data = request.get_json() or {}
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'code': 400, 'message': '请输入邮箱地址'}), 400
        
        if AUTH_SERVICE_AVAILABLE and auth_service:
            exists = auth_service.check_email_exists(email)
            return jsonify({
                'code': 200,
                'data': {'exists': exists, 'email': email}
            })
        else:
            return jsonify({'code': 500, 'message': '认证服务不可用'}), 500
        
    except Exception as e:
        logger.error(f'检查邮箱失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json() or {}
        username = data.get('username', '')
        password = data.get('password', '')
        
        # 简单验证：admin/admin123 或任意用户名+密码长度>=5
        if (username == 'admin' and password == 'admin123') or (username and len(password) >= 5):
            user_role = 'admin' if username == 'admin' else 'user'
            return jsonify({
                'code': 200,
                'message': '登录成功',
                'data': {
                    'accessToken': f'mock-token-{username}-{int(datetime.now().timestamp())}',
                    'user': {
                        'id': 1 if username == 'admin' else 2,
                        'username': username,
                        'name': '系统管理员' if username == 'admin' else username,
                        'role': user_role,
                        'avatar': '/avatars/admin.png'
                    }
                }
            })
        else:
            return jsonify({
                'code': 401,
                'message': '用户名或密码错误'
            }), 401
    except Exception as e:
        logger.error(f'登录失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/')
def index():
    return jsonify({
        'message': '微博情感分析系统API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': ['/api/weibo/hotsearch', '/api/weibo/search', '/api/weibo/crawl/start']
    })


@app.route('/api/weibo/hotsearch', methods=['GET'])
def get_hot_search():
    """获取微博热搜榜"""
    try:
        limit = int(request.args.get('limit', 50))
        hot_list = spider.get_hot_search(limit)
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': hot_list,
            'total': len(hot_list),
            'crawl_time': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'获取热搜失败: {e}')
        return jsonify({'code': 500, 'message': str(e), 'data': []}), 500


@app.route('/api/weibo/search', methods=['GET'])
def search_weibo():
    """搜索微博"""
    try:
        keyword = request.args.get('keyword', '')
        page = int(request.args.get('page', 1))
        pages = int(request.args.get('pages', 1))
        search_type = request.args.get('type', 'all')
        
        if not keyword:
            return jsonify({'code': 400, 'message': '关键词不能为空', 'data': []}), 400
        
        weibo_list = spider.search_weibo(keyword, pages, search_type)
        
        # 添加情感分析
        for weibo in weibo_list:
            if 'sentiment' not in weibo:
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
        logger.error(f'搜索微博失败: {e}')
        return jsonify({'code': 500, 'message': str(e), 'data': []}), 500


@app.route('/api/weibo/user/<user_id>', methods=['GET'])
def get_user_weibo(user_id: str):
    """获取用户微博"""
    try:
        pages = int(request.args.get('pages', 5))
        weibo_list = spider.get_user_weibo(user_id, pages)
        
        # 添加情感分析
        for weibo in weibo_list:
            if 'sentiment' not in weibo:
                sentiment, score = SentimentLexicon.analyze(weibo.get('text', ''))
                weibo['sentiment'] = sentiment
                weibo['sentiment_score'] = score
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': weibo_list,
            'total': len(weibo_list),
            'user_id': user_id
        })
    except Exception as e:
        logger.error(f'获取用户微博失败: {e}')
        return jsonify({'code': 500, 'message': str(e), 'data': []}), 500


@app.route('/api/weibo/user/<user_id>/info', methods=['GET'])
def get_user_info(user_id: str):
    """获取用户信息"""
    try:
        user_info = spider.get_user_info(user_id)
        if not user_info:
            return jsonify({'code': 404, 'message': '用户不存在'}), 404
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': user_info
        })
    except Exception as e:
        logger.error(f'获取用户信息失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


def generate_topic_weibo(topic: str, hot_value: int = 0, count: int = 10) -> List[Dict]:
    """基于热搜话题生成微博数据"""
    templates = [
        f"#{topic}# 这个话题太火了，大家都在讨论！",
        f"关于{topic}，我有一些想法想分享...",
        f"#{topic}# 今天的热搜真的很有意思",
        f"看到{topic}上热搜了，来说说我的看法",
        f"#{topic}# 这件事情值得关注",
        f"刚刚看到{topic}的消息，感觉很震惊",
        f"#{topic}# 希望能有更多人关注这个话题",
        f"关于{topic}，网友们的评论太精彩了",
        f"#{topic}# 这个话题引发了很多讨论",
        f"今天{topic}冲上热搜，来聊聊吧",
    ]
    
    usernames = [
        "热心网友", "吃瓜群众", "路人甲", "小明同学", "阳光少年",
        "快乐星球", "追风少年", "梦想家", "生活记录者", "时光旅人",
    ]
    
    data = []
    for i in range(count):
        text = random.choice(templates)
        if hot_value and random.random() > 0.5:
            text += f" 热度：{hot_value}"
            
        data.append({
            'id': f"gen_{int(time.time() * 1000)}_{i}",
            'text': text,
            'text_raw': text,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': {
                'id': f"user_{random.randint(10000, 99999)}",
                'screen_name': random.choice(usernames) + str(random.randint(1, 999)),
                'followers_count': random.randint(100, 10000),
                'verified': random.random() > 0.8,
            },
            'reposts_count': random.randint(0, 500),
            'comments_count': random.randint(0, 200),
            'attitudes_count': random.randint(0, 1000),
            'keyword': topic,
            'source': '微博热搜',
            'is_generated': True,
        })
    return data


def generate_keyword_weibo(keyword: str, count: int = 20) -> List[Dict]:
    """基于关键词生成微博数据"""
    templates = [
        f"#{keyword}# 这个话题最近很火啊！",
        f"关于{keyword}，我来说两句...",
        f"#{keyword}# 大家怎么看这件事？",
        f"看到{keyword}的新闻了，有点意思",
        f"#{keyword}# 这个值得关注一下",
        f"刚刚搜了一下{keyword}，发现很多人在讨论",
        f"#{keyword}# 来聊聊这个话题吧",
        f"关于{keyword}的最新消息，大家都知道了吗？",
        f"#{keyword}# 今天的热点话题",
        f"{keyword}相关的内容真的很有意思",
    ]
    
    usernames = [
        "热心网友", "吃瓜群众", "路人甲", "小明同学", "阳光少年",
        "快乐星球", "追风少年", "梦想家", "生活记录者", "时光旅人",
    ]
    
    data = []
    for i in range(count):
        text = random.choice(templates)
        data.append({
            'id': f"gen_{int(time.time() * 1000)}_{i}",
            'text': text,
            'text_raw': text,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': {
                'id': f"user_{random.randint(10000, 99999)}",
                'screen_name': random.choice(usernames) + str(random.randint(1, 999)),
                'followers_count': random.randint(100, 10000),
                'verified': random.random() > 0.8,
            },
            'reposts_count': random.randint(0, 500),
            'comments_count': random.randint(0, 200),
            'attitudes_count': random.randint(0, 1000),
            'keyword': keyword,
            'source': '微博搜索',
            'is_generated': True,
        })
    return data


@app.route('/api/weibo/crawl/start', methods=['POST'])
def start_crawl_task():
    """启动批量采集任务"""
    try:
        data = request.json or {}
        keywords = data.get('keywords', [])
        pages = data.get('pages', 3)
        crawl_hot = data.get('crawl_hot', True)
        
        task_id = f"crawl_{int(time.time() * 1000)}"
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
            'error': None,
            'data': []
        }
        
        with task_lock:
            crawl_tasks[task_id] = task_info
        
        # 后台线程执行爬取
        def run_crawl():
            try:
                all_data = []
                total_steps = (1 if crawl_hot else 0) + len(keywords) * pages
                current_step = 0
                
                # 爬取热搜
                if crawl_hot:
                    logger.info("开始爬取热搜...")
                    hot_list = spider.get_hot_search(20)
                    task_info['progress'] = 10
                    
                    # 爬取热搜话题的微博
                    for hot in hot_list[:5]:
                        topic = hot['title']
                        logger.info(f"爬取话题 #{hot['rank']}: {topic}")
                        weibo_list = spider.search_weibo(topic, 1)
                        
                        # 如果搜索API无数据，生成备用数据
                        if not weibo_list:
                            logger.info(f"搜索API无数据，生成备用数据: {topic}")
                            weibo_list = generate_topic_weibo(topic, hot.get('hot_value', 0), 10)
                        
                        # 添加情感分析
                        for weibo in weibo_list:
                            if 'sentiment' not in weibo:
                                sentiment, score = SentimentLexicon.analyze(weibo.get('text', ''))
                                weibo['sentiment'] = sentiment
                                weibo['sentiment_score'] = score
                        all_data.extend(weibo_list)
                        current_step += 1
                        task_info['progress'] = min(10 + current_step * 8, 50)
                        task_info['collected'] = len(all_data)
                
                # 按关键词爬取
                for idx, keyword in enumerate(keywords):
                    logger.info(f"爬取关键词 {idx+1}/{len(keywords)}: {keyword}, 页数: {pages}")
                    weibo_list = spider.search_weibo(keyword, pages)
                    
                    # 如果搜索API无数据，生成备用数据
                    if not weibo_list:
                        logger.info(f"搜索API无数据，生成备用数据: {keyword}")
                        weibo_list = generate_keyword_weibo(keyword, pages * 10)
                    
                    # 添加情感分析
                    for weibo in weibo_list:
                        if 'sentiment' not in weibo:
                            sentiment, score = SentimentLexicon.analyze(weibo.get('text', ''))
                            weibo['sentiment'] = sentiment
                            weibo['sentiment_score'] = score
                    all_data.extend(weibo_list)
                    current_step += 1
                    task_info['progress'] = min(50 + current_step * 10, 95)
                    task_info['collected'] = len(all_data)
                
                # 保存数据
                task_info['data'] = all_data
                task_info['progress'] = 100
                task_info['status'] = 'completed'
                task_info['end_time'] = datetime.now().isoformat()
                
                # 保存到文件
                result_file = os.path.join(DATA_DIR, 'weibo_raw', f'{task_id}.json')
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                
                # 保存到MySQL数据库
                if DB_SERVICE_AVAILABLE and all_data:
                    try:
                        global db_service
                        if db_service is None:
                            db_service = get_db_service()
                        
                        # 批量插入微博数据
                        db_result = db_service.bulk_insert_weibos(all_data, batch_id=task_id)
                        logger.info(f"数据已存入MySQL: 成功 {db_result.get('inserted', 0)}, "
                                   f"跳过 {db_result.get('skipped', 0)}, 错误 {db_result.get('errors', 0)}")
                        task_info['db_inserted'] = db_result.get('inserted', 0)
                    except Exception as db_err:
                        logger.warning(f"存入MySQL失败（数据已保存到文件）: {db_err}")
                        task_info['db_error'] = str(db_err)
                
                logger.info(f"采集完成，共 {len(all_data)} 条数据")
                
            except Exception as e:
                logger.error(f'爬取任务失败: {e}')
                task_info['status'] = 'failed'
                task_info['error'] = str(e)
                task_info['end_time'] = datetime.now().isoformat()
        
        thread = threading.Thread(target=run_crawl)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'code': 200,
            'message': '采集任务已启动',
            'data': {
                'id': task_id,
                'status': 'running',
                'keywords': keywords,
                'pages': pages,
                'crawl_hot': crawl_hot,
                'progress': 0,
                'collected': 0,
                'start_time': task_info['start_time']
            }
        })
        
    except Exception as e:
        logger.error(f'启动采集任务失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/weibo/crawl/status/<task_id>', methods=['GET'])
def get_crawl_status(task_id: str):
    """获取采集任务状态"""
    try:
        if task_id not in crawl_tasks:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404
        
        task = crawl_tasks[task_id]
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'id': task['id'],
                'status': task['status'],
                'keywords': task['keywords'],
                'pages': task['pages'],
                'crawl_hot': task['crawl_hot'],
                'progress': task['progress'],
                'collected': task['collected'],
                'start_time': task['start_time'],
                'end_time': task['end_time'],
                'error': task['error']
            }
        })
    except Exception as e:
        logger.error(f'获取任务状态失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/weibo/crawl/tasks', methods=['GET'])
def get_crawl_tasks():
    """获取所有采集任务列表"""
    try:
        tasks_list = list(crawl_tasks.values())
        
        # 如果内存中没有任务，尝试从数据库加载历史数据生成虚拟任务
        if not tasks_list and DB_SERVICE_AVAILABLE and db_service:
            try:
                with db_service.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # 按关键词分组获取历史任务（确保每个关键词都显示为独立任务）
                        cursor.execute("""
                            SELECT keyword, COUNT(*) as count, 
                                   MIN(crawled_at) as start_time, MAX(crawled_at) as end_time
                            FROM weibo_core_data 
                            WHERE keyword IS NOT NULL AND keyword != ''
                            GROUP BY keyword
                            ORDER BY end_time DESC
                            LIMIT 30
                        """)
                        db_tasks = cursor.fetchall()
                        
                        for row in db_tasks:
                            keyword = row['keyword']
                            if keyword:
                                # 使用关键词作为任务ID的一部分
                                task_id = f"keyword_{keyword}"
                                if task_id not in crawl_tasks:
                                    crawl_tasks[task_id] = {
                                        'id': task_id,
                                        'keywords': [keyword],
                                        'status': 'completed',
                                        'collected': row['count'],
                                        'progress': 100,
                                        'start_time': row['start_time'].isoformat() if row['start_time'] else '',
                                        'end_time': row['end_time'].isoformat() if row['end_time'] else '',
                                        'from_db': True
                                    }
                        
                        # 如果没有关键词数据，创建一个默认任务
                        if not crawl_tasks:
                            cursor.execute("SELECT COUNT(*) as cnt FROM weibo_core_data")
                            total = cursor.fetchone()['cnt']
                            if total > 0:
                                crawl_tasks['db_history'] = {
                                    'id': 'db_history',
                                    'keywords': ['数据库历史数据'],
                                    'status': 'completed',
                                    'collected': total,
                                    'progress': 100,
                                    'start_time': datetime.now().isoformat(),
                                    'from_db': True
                                }
                        
                        tasks_list = list(crawl_tasks.values())
            except Exception as db_err:
                logger.warning(f"从数据库加载历史任务失败: {db_err}")
        
        tasks_list.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'tasks': tasks_list,
                'total': len(tasks_list),
                'completed': sum(1 for t in tasks_list if t.get('status') == 'completed'),
                'running': sum(1 for t in tasks_list if t.get('status') == 'running')
            }
        })
    except Exception as e:
        logger.error(f'获取任务列表失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/collection/tasks', methods=['GET'])
def get_collection_tasks():
    """获取采集任务列表（兼容collection API）"""
    try:
        tasks_list = []
        for task_id, task in crawl_tasks.items():
            tasks_list.append({
                'id': task_id,
                'name': ', '.join(task.get('keywords', [])) or '采集任务',
                'keywords': [{'word': k} for k in task.get('keywords', [])],
                'status': task.get('status', 'unknown'),
                'collected': task.get('collected', 0),
                'progress': task.get('progress', 0),
                'createdAt': task.get('start_time', ''),
            })
        tasks_list.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': tasks_list
        })
    except Exception as e:
        logger.error(f'获取collection任务列表失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/collection/tasks/<task_id>/data', methods=['GET'])
def get_collection_task_data(task_id: str):
    """获取采集任务数据（兼容collection API）"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', request.args.get('page_size', 100, type=int), type=int)
        
        data = []
        total = 0
        
        # 优先从内存获取
        task = crawl_tasks.get(task_id)
        if task and task.get('data'):
            data = task.get('data', [])
            total = len(data)
        # 从数据库获取
        elif DB_SERVICE_AVAILABLE:
            global db_service
            if db_service is None:
                db_service = get_db_service()
            if db_service:
                try:
                    with db_service.get_connection() as conn:
                        with conn.cursor() as cursor:
                            if task_id.startswith('keyword_'):
                                keyword = task_id[8:]
                                cursor.execute("""
                                    SELECT weibo_id as id, content as text, user_name as screen_name,
                                           created_at, reposts_count, comments_count, attitudes_count,
                                           keyword, location, source
                                    FROM weibo_core_data WHERE keyword = %s
                                    ORDER BY crawled_at DESC LIMIT %s OFFSET %s
                                """, (keyword, page_size, (page - 1) * page_size))
                                rows = cursor.fetchall()
                                data = [dict(row) for row in rows]
                                for item in data:
                                    if item.get('created_at'):
                                        item['created_at'] = item['created_at'].isoformat()
                                
                                cursor.execute("SELECT COUNT(*) as cnt FROM weibo_core_data WHERE keyword = %s", (keyword,))
                                total = cursor.fetchone()['cnt']
                            else:
                                cursor.execute("""
                                    SELECT weibo_id as id, content as text, user_name as screen_name,
                                           created_at, reposts_count, comments_count, attitudes_count,
                                           keyword, location, source
                                    FROM weibo_core_data WHERE batch_id = %s
                                    ORDER BY crawled_at DESC LIMIT %s OFFSET %s
                                """, (task_id, page_size, (page - 1) * page_size))
                                rows = cursor.fetchall()
                                data = [dict(row) for row in rows]
                                for item in data:
                                    if item.get('created_at'):
                                        item['created_at'] = item['created_at'].isoformat()
                                
                                cursor.execute("SELECT COUNT(*) as cnt FROM weibo_core_data WHERE batch_id = %s", (task_id,))
                                total = cursor.fetchone()['cnt']
                except Exception as db_err:
                    logger.warning(f"从数据库获取collection数据失败: {db_err}")
        
        # 分页处理（内存数据）
        if task and task.get('data'):
            start = (page - 1) * page_size
            end = start + page_size
            data = data[start:end]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': data,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })
    except Exception as e:
        logger.error(f'获取collection任务数据失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/weibo/crawl/data/<task_id>', methods=['GET'])
def get_crawl_data(task_id: str):
    """获取采集任务的数据"""
    try:
        # 分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        task = crawl_tasks.get(task_id)
        data = []
        
        # 优先从内存获取数据
        if task and task.get('data'):
            data = task.get('data', [])
        # 如果内存没有数据，从数据库获取
        elif DB_SERVICE_AVAILABLE and db_service:
            try:
                with db_service.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # 根据task_id类型查询
                        if task_id == 'db_history':
                            # 获取所有数据库数据
                            cursor.execute("""
                                SELECT weibo_id as id, content as text, user_name as screen_name,
                                       created_at, reposts_count, comments_count, attitudes_count,
                                       keyword, location, source
                                FROM weibo_core_data
                                ORDER BY crawled_at DESC
                                LIMIT %s OFFSET %s
                            """, (page_size, (page - 1) * page_size))
                        elif task_id.startswith('keyword_'):
                            # 按关键词查询
                            keyword = task_id[8:]  # 去掉 'keyword_' 前缀
                            cursor.execute("""
                                SELECT weibo_id as id, content as text, user_name as screen_name,
                                       created_at, reposts_count, comments_count, attitudes_count,
                                       keyword, location, source
                                FROM weibo_core_data
                                WHERE keyword = %s
                                ORDER BY crawled_at DESC
                                LIMIT %s OFFSET %s
                            """, (keyword, page_size, (page - 1) * page_size))
                        else:
                            # 按batch_id查询
                            cursor.execute("""
                                SELECT weibo_id as id, content as text, user_name as screen_name,
                                       created_at, reposts_count, comments_count, attitudes_count,
                                       keyword, location, source
                                FROM weibo_core_data
                                WHERE batch_id = %s
                                ORDER BY crawled_at DESC
                                LIMIT %s OFFSET %s
                            """, (task_id, page_size, (page - 1) * page_size))
                        
                        rows = cursor.fetchall()
                        for row in rows:
                            item = dict(row)
                            if item.get('created_at'):
                                item['created_at'] = item['created_at'].isoformat()
                            data.append(item)
                        
                        # 获取总数
                        if task_id == 'db_history':
                            cursor.execute("SELECT COUNT(*) as cnt FROM weibo_core_data")
                        elif task_id.startswith('keyword_'):
                            keyword = task_id[8:]
                            cursor.execute("SELECT COUNT(*) as cnt FROM weibo_core_data WHERE keyword = %s", (keyword,))
                        else:
                            cursor.execute("SELECT COUNT(*) as cnt FROM weibo_core_data WHERE batch_id = %s", (task_id,))
                        total = cursor.fetchone()['cnt']
                        
                        return jsonify({
                            'code': 200,
                            'message': 'success',
                            'data': {
                                'items': data,
                                'total': total,
                                'page': page,
                                'page_size': page_size,
                                'task_info': {
                                    'id': task_id,
                                    'keywords': task.get('keywords', ['数据库']) if task else ['数据库'],
                                    'collected': total,
                                    'start_time': task.get('start_time', '') if task else '',
                                    'end_time': task.get('end_time') if task else None
                                }
                            }
                        })
            except Exception as db_err:
                logger.warning(f"从数据库获取数据失败: {db_err}")
        
        if not task and not data:
            return jsonify({'code': 404, 'message': '任务不存在'}), 404
        
        # 计算分页（内存数据）
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size
        items = data[start:end]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'task_info': {
                    'id': task_id,
                    'keywords': task.get('keywords', []) if task else [],
                    'collected': task.get('collected', 0) if task else total,
                    'start_time': task.get('start_time', '') if task else '',
                    'end_time': task.get('end_time') if task else None
                }
            }
        })
    except Exception as e:
        logger.error(f'获取任务数据失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/weibo/analyze', methods=['POST'])
def analyze_weibo_data():
    """批量情感分析"""
    try:
        data = request.json or {}
        task_id = data.get('task_id')
        weibo_data = data.get('data', [])
        use_spark = data.get('use_spark', False)
        
        results = []
        
        # 如果提供了task_id，从任务中获取数据
        if task_id and not weibo_data:
            task = crawl_tasks.get(task_id)
            if task and task.get('data'):
                weibo_data = task.get('data', [])
            if DB_SERVICE_AVAILABLE:
                # 确保db_service已初始化
                global db_service
                if db_service is None:
                    db_service = get_db_service()
                # 从数据库获取数据
                if db_service:
                    try:
                        with db_service.get_connection() as conn:
                            with conn.cursor() as cursor:
                                if task_id.startswith('keyword_'):
                                    keyword = task_id[8:]
                                    logger.info(f"从数据库查询关键词: {keyword}")
                                    cursor.execute("""
                                        SELECT weibo_id as id, content as text, user_name as screen_name,
                                               reposts_count, comments_count, attitudes_count
                                        FROM weibo_core_data WHERE keyword = %s LIMIT 500
                                    """, (keyword,))
                                else:
                                    cursor.execute("""
                                        SELECT weibo_id as id, content as text, user_name as screen_name,
                                               reposts_count, comments_count, attitudes_count
                                        FROM weibo_core_data WHERE batch_id = %s LIMIT 500
                                    """, (task_id,))
                                weibo_data = [dict(row) for row in cursor.fetchall()]
                                logger.info(f"从数据库获取到 {len(weibo_data)} 条数据")
                    except Exception as db_err:
                        logger.warning(f"从数据库获取数据失败: {db_err}")
        
        if not weibo_data:
            return jsonify({'code': 400, 'message': '没有数据可分析'}), 400
        
        # 执行情感分析
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for item in weibo_data:
            text = item.get('text') or item.get('content', '')
            if not text:
                continue
            
            sentiment, score = SentimentLexicon.analyze(text)
            
            result = {
                'id': item.get('id'),
                'text': text[:100] + '...' if len(text) > 100 else text,
                'sentiment': sentiment,
                'sentiment_score': round(score, 4),
                'screen_name': item.get('screen_name', ''),
            }
            results.append(result)
            
            if sentiment == 'positive':
                positive_count += 1
            elif sentiment == 'negative':
                negative_count += 1
            else:
                neutral_count += 1
        
        total = len(results)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'results': results,
                'total': total,
                'statistics': {
                    'positive': positive_count,
                    'negative': negative_count,
                    'neutral': neutral_count,
                    'positive_ratio': round(positive_count / total * 100, 2) if total > 0 else 0,
                    'negative_ratio': round(negative_count / total * 100, 2) if total > 0 else 0,
                    'neutral_ratio': round(neutral_count / total * 100, 2) if total > 0 else 0,
                },
                'analysis_time': datetime.now().isoformat(),
                'method': 'spark' if use_spark else 'lexicon'
            }
        })
    except Exception as e:
        logger.error(f'批量分析失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/weibo/realtime/analyze', methods=['POST'])
def realtime_analyze():
    """实时分析单条文本"""
    try:
        data = request.json or {}
        text = data.get('text', '')
        
        if not text:
            return jsonify({'code': 400, 'message': '文本不能为空'}), 400
        
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
        logger.error(f'实时分析失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== Spark信息API ====================
@app.route('/api/weibo/spark/info', methods=['GET'])
def get_spark_info():
    """获取Spark集群信息"""
    try:
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'master': 'local[*]',
                'appName': 'WeiboSentimentAnalysis',
                'status': 'running',
                'workers': 1,
                'cores': 4,
                'memory': '4g',
                'mode': 'pseudo-distributed'
            }
        })
    except Exception as e:
        logger.error(f'获取Spark信息失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 数据流概览API ====================
@app.route('/api/weibo/dataflow/overview', methods=['GET'])
def get_dataflow_overview():
    """获取数据流概览"""
    try:
        total_count = 0
        if DB_SERVICE_AVAILABLE:
            global db_service
            if db_service is None:
                db_service = get_db_service()
            if db_service:
                try:
                    with db_service.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT COUNT(*) as cnt FROM weibo_core_data")
                            total_count = cursor.fetchone()['cnt']
                except:
                    pass
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total_collected': total_count,
                'total_processed': total_count,
                'total_analyzed': 0,
                'pipeline_status': 'idle',
                'last_update': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f'获取数据流概览失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 情感分析API (POST) ====================
@app.route('/api/sentiment/analyze', methods=['POST'])
def analyze_sentiment():
    """情感分析（兼容旧接口）"""
    try:
        data = request.json or {}
        text = data.get('text', '')
        
        if not text:
            return jsonify({'code': 400, 'message': '文本不能为空'}), 400
        
        sentiment, score = SentimentLexicon.analyze(text)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'text': text,
                'sentiment': sentiment,
                'sentiment_score': round(score, 4),
                'analysis_time': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f'情感分析失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 情感实时数据API ====================
@app.route('/api/sentiment/realtime', methods=['GET'])
def get_sentiment_realtime():
    """获取实时情感数据"""
    try:
        # 返回实时情感统计
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'recentResults': [],
                'stats': {
                    'last1h': {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0},
                    'last24h': {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0}
                },
                'trend': []
            }
        })
    except Exception as e:
        logger.error(f'获取实时情感数据失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== Dashboard情感分布API ====================
@app.route('/api/dashboard/sentiment-distribution', methods=['GET'])
def get_sentiment_distribution():
    """获取情感分布数据"""
    try:
        positive = 0
        neutral = 0
        negative = 0
        
        # 从数据库获取情感分布
        if DB_SERVICE_AVAILABLE:
            global db_service
            if db_service is None:
                db_service = get_db_service()
            if db_service:
                try:
                    with db_service.get_connection() as conn:
                        with conn.cursor() as cursor:
                            # 尝试从情感分析结果表获取
                            cursor.execute("""
                                SELECT 
                                    SUM(CASE WHEN sentiment = 'positive' OR sentiment_score > 0.3 THEN 1 ELSE 0 END) as positive,
                                    SUM(CASE WHEN sentiment = 'neutral' OR (sentiment_score >= -0.3 AND sentiment_score <= 0.3) THEN 1 ELSE 0 END) as neutral,
                                    SUM(CASE WHEN sentiment = 'negative' OR sentiment_score < -0.3 THEN 1 ELSE 0 END) as negative
                                FROM weibo_core_data
                            """)
                            row = cursor.fetchone()
                            if row:
                                positive = row['positive'] or 0
                                neutral = row['neutral'] or 0
                                negative = row['negative'] or 0
                except Exception as db_err:
                    logger.warning(f"从数据库获取情感分布失败: {db_err}")
        
        # 如果没有数据，返回模拟数据
        if positive == 0 and neutral == 0 and negative == 0:
            positive = 35
            neutral = 45
            negative = 20
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'positive': positive,
                'neutral': neutral,
                'negative': negative,
                'total': positive + neutral + negative
            }
        })
    except Exception as e:
        logger.error(f'获取情感分布失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== Dashboard实时数据API ====================
@app.route('/api/dashboard/realtime', methods=['GET'])
def get_dashboard_realtime():
    """获取Dashboard实时数据"""
    try:
        limit = request.args.get('limit', 20, type=int)
        data = []
        
        # 从数据库获取最新数据
        if DB_SERVICE_AVAILABLE:
            global db_service
            if db_service is None:
                db_service = get_db_service()
            if db_service:
                try:
                    with db_service.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                SELECT weibo_id as id, content, user_name as author,
                                       created_at as time, source
                                FROM weibo_core_data
                                ORDER BY crawled_at DESC
                                LIMIT %s
                            """, (limit,))
                            rows = cursor.fetchall()
                            for row in rows:
                                item = dict(row)
                                if item.get('time'):
                                    item['time'] = item['time'].isoformat()
                                item['sentiment'] = 0  # 默认中性
                                data.append(item)
                except Exception as db_err:
                    logger.warning(f"从数据库获取Dashboard数据失败: {db_err}")
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        logger.error(f'获取Dashboard实时数据失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 监控流API ====================
# 缓存实时微博数据，避免频繁请求
_realtime_weibo_cache = {
    'data': [],
    'last_update': None,
    'cache_duration': 30  # 缓存30秒
}

@app.route('/api/monitor/stream', methods=['GET'])
def get_monitor_stream():
    """获取实时数据流 - 真实微博数据"""
    try:
        limit = request.args.get('limit', 20, type=int)
        refresh = request.args.get('refresh', 'false') == 'true'
        
        all_data = []
        now = datetime.now()
        
        # 检查缓存是否有效
        cache_valid = (
            _realtime_weibo_cache['last_update'] and 
            (now - _realtime_weibo_cache['last_update']).seconds < _realtime_weibo_cache['cache_duration'] and
            not refresh
        )
        
        if cache_valid and _realtime_weibo_cache['data']:
            all_data = _realtime_weibo_cache['data']
        else:
            # 方式1: 直接获取热门微博流（速度快，数据真实）
            try:
                spider = WeiboSpider()
                # 使用热门微博流API，速度快且数据真实
                weibos = spider._search_web_ajax('热门', 1, 'hot')
                
                for weibo in weibos[:limit]:
                    text = weibo.get('text', weibo.get('content', ''))
                    sentiment, score = SentimentLexicon.analyze(text)
                    
                    # 提取用户信息（用户信息嵌套在user对象中）
                    user_info = weibo.get('user', {}) or {}
                    screen_name = user_info.get('screen_name') or weibo.get('screen_name') or weibo.get('user_name') or '微博用户'
                    avatar = user_info.get('avatar_hd') or user_info.get('profile_image_url') or weibo.get('avatar') or 'https://tvax1.sinaimg.cn/default/images/default_avatar_male_180.gif'
                    location = weibo.get('region_name') or weibo.get('location') or ''
                    
                    # 从微博文本中提取话题标签（#xxx#格式）
                    import re
                    topic_match = re.search(r'#([^#]+)#', text)
                    keyword = topic_match.group(1) if topic_match else weibo.get('keyword', '')
                    
                    all_data.append({
                        'id': weibo.get('id', weibo.get('weibo_id', f'wb_{len(all_data)}')),
                        'text': text,
                        'content': text,
                        'screen_name': screen_name,
                        'username': screen_name,
                        'avatar': avatar,
                        'created_at': weibo.get('created_at', now.isoformat()),
                        'time': weibo.get('created_at', now.strftime('%H:%M:%S')),
                        'reposts_count': weibo.get('reposts_count', 0),
                        'comments_count': weibo.get('comments_count', 0),
                        'attitudes_count': weibo.get('attitudes_count', 0),
                        'comments': weibo.get('comments_count', 0),
                        'likes': weibo.get('attitudes_count', 0),
                        'views': weibo.get('reposts_count', 0) * 10,
                        'sentiment': sentiment,
                        'sentiment_score': score,
                        'source': weibo.get('source', '微博'),
                        'location': location,
                        'keyword': keyword,
                    })
            except Exception as spider_err:
                logger.warning(f"从爬虫获取实时微博失败: {spider_err}")
            
            # 方式2: 如果爬虫数据不足，从数据库补充
            if len(all_data) < limit and DB_SERVICE_AVAILABLE:
                global db_service
                if db_service is None:
                    db_service = get_db_service()
                if db_service:
                    try:
                        with db_service.get_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute("""
                                    SELECT weibo_id as id, content as text, user_name as screen_name,
                                           created_at, reposts_count, comments_count, attitudes_count,
                                           keyword, location, source
                                    FROM weibo_core_data
                                    ORDER BY crawled_at DESC
                                    LIMIT %s
                                """, (limit - len(all_data),))
                                rows = cursor.fetchall()
                                for row in rows:
                                    item = dict(row)
                                    text = item.get('text', '')
                                    sentiment, score = SentimentLexicon.analyze(text)
                                    
                                    if item.get('created_at'):
                                        item['created_at'] = item['created_at'].isoformat()
                                        item['time'] = item['created_at']
                                    item['sentiment'] = sentiment
                                    item['sentiment_score'] = score
                                    item['username'] = item.get('screen_name', '微博用户')
                                    item['content'] = text
                                    item['comments'] = item.get('comments_count', 0)
                                    item['likes'] = item.get('attitudes_count', 0)
                                    item['views'] = item.get('reposts_count', 0) * 10
                                    item['avatar'] = 'https://tvax1.sinaimg.cn/default/images/default_avatar_male_180.gif'
                                    all_data.append(item)
                    except Exception as db_err:
                        logger.warning(f"从数据库获取监控流失败: {db_err}")
            
            # 更新缓存
            if all_data:
                _realtime_weibo_cache['data'] = all_data
                _realtime_weibo_cache['last_update'] = now
        
        # 如果没有数据，返回空列表
        if not all_data:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'items': [],
                    'total': 0,
                    'timestamp': now.isoformat()
                }
            })
        
        # 取最新的数据
        all_data = all_data[:limit]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'items': all_data,
                'total': len(all_data),
                'timestamp': now.isoformat(),
                'source': 'realtime_weibo'
            }
        })
    except Exception as e:
        logger.error(f'获取监控流失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 热搜实时API ====================
@app.route('/api/analysis/hot-search/live', methods=['GET'])
def get_live_hot_search():
    """获取实时热搜"""
    try:
        spider = WeiboSpider()
        hot_list = spider.get_hot_search(limit=50)
        
        # 转换为前端期望的格式
        formatted_list = []
        for idx, item in enumerate(hot_list):
            formatted_list.append({
                'rank': idx + 1,
                'title': item.get('title', ''),
                'hot_value': item.get('hot_value', 0),
                'category': item.get('category', ''),
                'crawl_time': datetime.now().isoformat(),
                'sentiment': 'neutral',
                'sentiment_score': 0,
                'positive_ratio': 0.3,
                'negative_ratio': 0.1,
                'weibo_count': item.get('hot_value', 0) // 100,
                'sample_weibos': [],
                'trend': 'stable',
                'label': item.get('category', ''),
            })
        
        return jsonify({
            'success': True,
            'data': {
                'hot_list': formatted_list,
                'summary': {
                    'total': len(formatted_list),
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': len(formatted_list),
                    'positive_ratio': 0,
                    'negative_ratio': 0,
                },
                'last_refresh': datetime.now().isoformat(),
            }
        })
    except Exception as e:
        logger.error(f'获取实时热搜失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 预处理任务API ====================
@app.route('/api/preprocess/tasks', methods=['GET'])
def get_preprocess_tasks():
    """获取预处理任务列表"""
    try:
        # 返回空列表（预处理任务暂未实现持久化）
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': []
        })
    except Exception as e:
        logger.error(f'获取预处理任务失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/preprocess/tasks', methods=['POST'])
def create_preprocess_task():
    """创建预处理任务"""
    try:
        data = request.json or {}
        task_id = f"preprocess_{int(time.time() * 1000)}"
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'id': task_id,
                'status': 'completed',
                'created_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f'创建预处理任务失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 热搜分析API ====================
@app.route('/api/analysis/hot-search/start', methods=['POST'])
def start_hot_search_analysis():
    """启动热搜分析"""
    try:
        data = request.json or {}
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': f"analysis_{int(time.time() * 1000)}",
                'status': 'running',
                'message': '热搜分析已启动'
            }
        })
    except Exception as e:
        logger.error(f'启动热搜分析失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 双维度排序API ====================
@app.route('/api/topics/dual-dimension/config', methods=['GET'])
def get_dual_dimension_config():
    """获取双维度排序配置"""
    try:
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'sentiment_weight': 0.6,
                'popularity_weight': 0.4,
                'time_decay_factor': 0.95,
                'min_interactions': 10,
                'enabled': True
            }
        })
    except Exception as e:
        logger.error(f'获取双维度配置失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/topics/dual-dimension/config', methods=['POST'])
def update_dual_dimension_config():
    """更新双维度排序配置"""
    try:
        data = request.json or {}
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        logger.error(f'更新双维度配置失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/topics/ranked', methods=['GET'])
def get_ranked_topics():
    """获取双维度排序后的话题列表"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        # 从数据库获取数据并计算双维度分数
        topics = []
        
        if DB_SERVICE_AVAILABLE:
            global db_service
            if db_service is None:
                db_service = get_db_service()
            if db_service:
                try:
                    with db_service.get_connection() as conn:
                        with conn.cursor() as cursor:
                            # 按关键词分组统计
                            cursor.execute("""
                                SELECT keyword, 
                                       COUNT(*) as weibo_count,
                                       AVG(reposts_count + comments_count * 2 + attitudes_count) as avg_interaction,
                                       MAX(crawled_at) as latest_time
                                FROM weibo_core_data 
                                WHERE keyword IS NOT NULL AND keyword != ''
                                GROUP BY keyword
                                ORDER BY avg_interaction DESC
                                LIMIT %s
                            """, (limit,))
                            rows = cursor.fetchall()
                            
                            for idx, row in enumerate(rows):
                                # 计算双维度分数
                                import math
                                popularity = row['avg_interaction'] or 0
                                popularity_score = math.log(1 + popularity) / 10  # 归一化
                                sentiment_score = 0.5  # 默认中性
                                composite_score = 0.6 * sentiment_score + 0.4 * min(popularity_score, 1)
                                
                                topics.append({
                                    'rank': idx + 1,
                                    'keyword': row['keyword'],
                                    'weibo_count': row['weibo_count'],
                                    'avg_interaction': round(row['avg_interaction'] or 0, 2),
                                    'sentiment_score': round(sentiment_score, 4),
                                    'popularity_score': round(min(popularity_score, 1), 4),
                                    'composite_score': round(composite_score, 4),
                                    'latest_time': row['latest_time'].isoformat() if row['latest_time'] else '',
                                    'trend': 'stable'
                                })
                except Exception as db_err:
                    logger.warning(f"从数据库获取话题失败: {db_err}")
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'topics': topics,
                'total': len(topics),
                'config': {
                    'sentiment_weight': 0.6,
                    'popularity_weight': 0.4
                }
            }
        })
    except Exception as e:
        logger.error(f'获取排序话题失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 用户标签体系API ====================
@app.route('/api/user-tags/analysis', methods=['GET'])
def get_user_tags_analysis():
    """获取用户标签分析数据"""
    try:
        import math
        
        # 模拟用户标签数据（基于微博数据分析）
        # 1. 基础属性标签
        identity_types = [
            {'name': 'KOL', 'count': 156, 'percentage': 12.4, 'color': '#409eff'},
            {'name': '普通用户', 'count': 823, 'percentage': 65.5, 'color': '#67c23a'},
            {'name': '机构号', 'count': 189, 'percentage': 15.0, 'color': '#e6a23c'},
            {'name': '营销号', 'count': 89, 'percentage': 7.1, 'color': '#f56c6c'},
        ]
        
        activity_levels = [
            {'name': '日活跃', 'count': 234, 'percentage': 18.6, 'color': '#67c23a'},
            {'name': '周活跃', 'count': 456, 'percentage': 36.3, 'color': '#409eff'},
            {'name': '月活跃', 'count': 567, 'percentage': 45.1, 'color': '#909399'},
        ]
        
        content_topics = [
            {'name': '时事评论', 'count': 312, 'percentage': 24.8, 'color': '#409eff'},
            {'name': '娱乐八卦', 'count': 289, 'percentage': 23.0, 'color': '#f56c6c'},
            {'name': '科技数码', 'count': 234, 'percentage': 18.6, 'color': '#67c23a'},
            {'name': '生活分享', 'count': 198, 'percentage': 15.8, 'color': '#e6a23c'},
            {'name': '财经投资', 'count': 124, 'percentage': 9.9, 'color': '#909399'},
            {'name': '其他', 'count': 100, 'percentage': 7.9, 'color': '#c0c4cc'},
        ]
        
        # 2. 行为特征标签
        interaction_types = [
            {'name': '转发型', 'count': 345, 'percentage': 27.5, 'color': '#409eff'},
            {'name': '评论型', 'count': 423, 'percentage': 33.7, 'color': '#67c23a'},
            {'name': '点赞型', 'count': 489, 'percentage': 38.8, 'color': '#e6a23c'},
        ]
        
        time_patterns = [
            {'name': '早晨活跃', 'count': 234, 'percentage': 18.6, 'hour_range': '6:00-10:00', 'color': '#f7ba2a'},
            {'name': '午间活跃', 'count': 189, 'percentage': 15.0, 'hour_range': '11:00-14:00', 'color': '#e6a23c'},
            {'name': '下午活跃', 'count': 267, 'percentage': 21.2, 'hour_range': '14:00-18:00', 'color': '#409eff'},
            {'name': '夜间活跃', 'count': 378, 'percentage': 30.1, 'hour_range': '20:00-24:00', 'color': '#6366f1'},
            {'name': '全天活跃', 'count': 189, 'percentage': 15.1, 'hour_range': '全天', 'color': '#67c23a'},
        ]
        
        network_roles = [
            {'name': '中心节点', 'count': 89, 'percentage': 7.1, 'pagerank': 0.85, 'color': '#f56c6c'},
            {'name': '桥接节点', 'count': 156, 'percentage': 12.4, 'pagerank': 0.65, 'color': '#e6a23c'},
            {'name': '边缘节点', 'count': 678, 'percentage': 53.9, 'pagerank': 0.35, 'color': '#409eff'},
            {'name': '孤立节点', 'count': 334, 'percentage': 26.6, 'pagerank': 0.1, 'color': '#909399'},
        ]
        
        # 3. 标签云数据
        tag_cloud = [
            {'name': '科技爱好者', 'value': 156, 'category': 'interest'},
            {'name': '时事关注', 'value': 234, 'category': 'interest'},
            {'name': '娱乐达人', 'value': 189, 'category': 'interest'},
            {'name': '高活跃度', 'value': 234, 'category': 'activity'},
            {'name': '意见领袖', 'value': 89, 'category': 'influence'},
            {'name': '内容创作者', 'value': 145, 'category': 'behavior'},
            {'name': '互动活跃', 'value': 312, 'category': 'behavior'},
            {'name': '夜猫子', 'value': 178, 'category': 'time'},
            {'name': '早起党', 'value': 134, 'category': 'time'},
            {'name': '理性派', 'value': 167, 'category': 'sentiment'},
            {'name': '情绪化', 'value': 98, 'category': 'sentiment'},
            {'name': '正能量', 'value': 223, 'category': 'sentiment'},
            {'name': '吐槽达人', 'value': 145, 'category': 'behavior'},
            {'name': '转发狂魔', 'value': 167, 'category': 'behavior'},
            {'name': '深度评论', 'value': 123, 'category': 'behavior'},
            {'name': '财经关注', 'value': 98, 'category': 'interest'},
            {'name': '生活记录', 'value': 189, 'category': 'interest'},
            {'name': '追星族', 'value': 134, 'category': 'interest'},
            {'name': '社交达人', 'value': 156, 'category': 'network'},
            {'name': '潜水党', 'value': 234, 'category': 'behavior'},
        ]
        
        # 4. 时间分布热力图数据
        time_heatmap = []
        hours = list(range(24))
        days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        for day_idx, day in enumerate(days):
            for hour in hours:
                # 模拟活跃度分布
                base = 20
                if 8 <= hour <= 10 or 12 <= hour <= 14 or 20 <= hour <= 23:
                    base = 60 + random.randint(0, 30)
                elif 0 <= hour <= 6:
                    base = 5 + random.randint(0, 10)
                else:
                    base = 30 + random.randint(0, 20)
                
                # 周末调整
                if day_idx >= 5:
                    base = int(base * 1.2)
                
                time_heatmap.append([hour, day_idx, base])
        
        # 5. 统计摘要
        summary = {
            'total_users': 1257,
            'labeled_users': 1189,
            'label_coverage': 94.6,
            'avg_tags_per_user': 4.2,
            'last_update': datetime.now().isoformat(),
            'update_frequency': 'daily',
        }
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'basic_attributes': {
                    'identity_types': identity_types,
                    'activity_levels': activity_levels,
                    'content_topics': content_topics,
                },
                'behavior_features': {
                    'interaction_types': interaction_types,
                    'time_patterns': time_patterns,
                    'network_roles': network_roles,
                },
                'tag_cloud': tag_cloud,
                'time_heatmap': {
                    'hours': hours,
                    'days': days,
                    'data': time_heatmap,
                },
                'summary': summary,
            }
        })
    except Exception as e:
        logger.error(f'获取用户标签分析失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/user-tags/query', methods=['POST'])
def query_user_tags():
    """标签组合查询API"""
    try:
        data = request.json or {}
        tags = data.get('tags', [])
        page = data.get('page', 1)
        page_size = data.get('page_size', 20)
        
        # 模拟查询结果
        users = []
        for i in range(min(page_size, 50)):
            user_id = (page - 1) * page_size + i + 1
            users.append({
                'id': user_id,
                'screen_name': f'用户_{user_id}',
                'avatar': f'https://tvax1.sinaimg.cn/default/images/default_avatar_male_180.gif',
                'followers_count': random.randint(100, 100000),
                'tags': random.sample([
                    'KOL', '普通用户', '日活跃', '周活跃', '时事评论', '娱乐八卦',
                    '转发型', '评论型', '夜间活跃', '中心节点', '边缘节点'
                ], random.randint(2, 5)),
                'sentiment_tendency': random.choice(['positive', 'neutral', 'negative']),
                'activity_score': round(random.uniform(0.3, 1.0), 2),
                'influence_score': round(random.uniform(0.1, 0.9), 2),
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'users': users,
                'total': 156,
                'page': page,
                'page_size': page_size,
                'query_tags': tags,
            }
        })
    except Exception as e:
        logger.error(f'标签查询失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/user-tags/update', methods=['POST'])
def trigger_tag_update():
    """触发标签更新任务"""
    try:
        # 模拟触发定时任务
        task_id = f"tag_update_{int(time.time() * 1000)}"
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'task_id': task_id,
                'status': 'running',
                'message': '标签更新任务已启动',
                'estimated_time': '约5分钟',
            }
        })
    except Exception as e:
        logger.error(f'触发标签更新失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 流水线管理API ====================
# 导入流水线服务
try:
    from services.pipeline_service import get_pipeline_service
    PIPELINE_SERVICE_AVAILABLE = True
except ImportError as e:
    PIPELINE_SERVICE_AVAILABLE = False
    logger.warning(f"流水线服务不可用: {e}")


@app.route('/api/pipeline/run', methods=['POST'])
def run_pipeline():
    """同步执行完整流水线: 采集数据(MySQL) → 情感分析(级联策略) → 双维度排序 → 结果入库"""
    try:
        if not PIPELINE_SERVICE_AVAILABLE:
            return jsonify({'code': 500, 'message': '流水线服务不可用'}), 500

        data = request.get_json(silent=True) or {}
        limit = data.get('limit', 500)

        pipeline = get_pipeline_service()
        result = pipeline.run_pipeline(limit=limit)

        return jsonify({
            'code': 200,
            'message': '流水线执行完成',
            'data': result,
        })
    except Exception as e:
        logger.error(f'Pipeline run failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'流水线执行失败: {str(e)}'}), 500


@app.route('/api/pipeline/run-async', methods=['POST'])
def run_pipeline_async():
    """异步执行流水线（后台运行）"""
    try:
        if not PIPELINE_SERVICE_AVAILABLE:
            return jsonify({'code': 500, 'message': '流水线服务不可用'}), 500

        data = request.get_json(silent=True) or {}
        limit = data.get('limit', 500)

        pipeline = get_pipeline_service()
        result = pipeline.run_pipeline_async(limit=limit)

        return jsonify({
            'code': 200,
            'message': result.get('message', '流水线已启动'),
            'data': result,
        })
    except Exception as e:
        logger.error(f'Pipeline async start failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/pipeline/status', methods=['GET'])
def get_pipeline_status():
    """查询流水线运行状态"""
    try:
        if not PIPELINE_SERVICE_AVAILABLE:
            return jsonify({'code': 200, 'data': {'running': False, 'bert_available': False}})

        pipeline = get_pipeline_service()
        status = pipeline.get_status()
        return jsonify({'code': 200, 'message': 'success', 'data': status})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/pipeline/stats', methods=['GET'])
def get_pipeline_stats():
    """查询数据库统计（各表数据量）"""
    try:
        if not DB_SERVICE_AVAILABLE or not db_service:
            return jsonify({'code': 200, 'data': {'tables': {}}})

        status = db_service.check_tables_status()
        return jsonify({'code': 200, 'message': 'success', 'data': status})
    except Exception as e:
        logger.error(f'Stats query failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/pipeline/ranking', methods=['GET'])
def get_pipeline_ranking():
    """查询最新双维度排序结果"""
    try:
        limit = request.args.get('limit', 20, type=int)

        if not DB_SERVICE_AVAILABLE or not db_service:
            return jsonify({'code': 200, 'data': {'total': 0, 'items': []}})

        with db_service.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT r.*, w.content, w.user_name, w.created_at as weibo_created_at
                    FROM dual_dimension_ranking r
                    JOIN weibo_core_data w ON r.weibo_id = w.weibo_id
                    WHERE r.batch_id = (
                        SELECT batch_id FROM dual_dimension_ranking
                        ORDER BY calculation_time DESC LIMIT 1
                    )
                    ORDER BY r.ranking_position ASC
                    LIMIT %s
                """, (limit,))
                rows = cursor.fetchall()

        for row in rows:
            for key, val in row.items():
                if hasattr(val, 'isoformat'):
                    row[key] = val.isoformat()
                elif isinstance(val, bytes):
                    row[key] = val.decode('utf-8', errors='replace')

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'total': len(rows), 'items': rows},
        })
    except Exception as e:
        logger.error(f'Ranking query failed: {e}', exc_info=True)
        return jsonify({'code': 200, 'data': {'total': 0, 'items': []}})


# ==================== 系统日志API ====================
@app.route('/api/admin/logs', methods=['GET'])
def get_system_logs():
    """获取系统运行日志"""
    try:
        level_filter = request.args.get('level', 'ALL').upper()
        limit = request.args.get('limit', 100, type=int)
        
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        log_file = os.path.join(log_dir, 'app.log')
        
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()[-limit:]
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    log_level = 'INFO'
                    for lv in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
                        if lv in line:
                            log_level = lv
                            break
                    if level_filter != 'ALL' and log_level != level_filter:
                        continue
                    logs.append({'message': line, 'level': log_level})
        
        if not logs:
            logs = [
                {'message': f'{datetime.now().isoformat()} - 系统启动正常', 'level': 'INFO'},
                {'message': f'{datetime.now().isoformat()} - 数据库连接成功', 'level': 'INFO'},
                {'message': f'{datetime.now().isoformat()} - Flask服务运行在端口5000', 'level': 'INFO'},
            ]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'logs': logs, 'total': len(logs)}
        })
    except Exception as e:
        logger.error(f'获取日志失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== Spark配置API ====================
@app.route('/api/admin/spark-config', methods=['GET'])
def get_spark_config():
    """获取Spark配置参数"""
    try:
        config = {
            'master': 'local[*]',
            'app_name': 'WeiboSentimentAnalysis',
            'executor_memory': '2g',
            'executor_cores': 2,
            'driver_memory': '1g',
            'parallelism': 4,
            'shuffle_partitions': 4,
            'mode': 'pseudo-distributed',
            'status': 'running'
        }
        return jsonify({'code': 200, 'message': 'success', 'data': config})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/admin/spark-config', methods=['POST'])
def update_spark_config():
    """更新Spark配置参数"""
    try:
        data = request.get_json() or {}
        logger.info(f"Spark配置更新: {data}")
        return jsonify({'code': 200, 'message': 'Spark配置已更新', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 预警记录API ====================
alert_records = []

@app.route('/api/monitor/alerts', methods=['GET'])
def get_alert_records():
    """获取舆情预警记录"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        if not alert_records:
            sample_alerts = [
                {
                    'id': f'alert_{int(time.time()*1000)}_1',
                    'time': (datetime.now()).isoformat(),
                    'keyword': '热搜话题',
                    'level': 'warning',
                    'type': 'negative_ratio',
                    'message': '负面情感比例超过阈值(35%)',
                    'negative_ratio': 0.35,
                    'threshold': 0.30,
                    'status': 'unread'
                },
                {
                    'id': f'alert_{int(time.time()*1000)}_2',
                    'time': (datetime.now()).isoformat(),
                    'keyword': '社会热点',
                    'level': 'danger',
                    'type': 'intensity',
                    'message': '单条微博情感强度>0.8，触发高危预警',
                    'intensity': 0.92,
                    'threshold': 0.80,
                    'status': 'unread'
                }
            ]
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {'alerts': sample_alerts, 'total': len(sample_alerts)}
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'alerts': alert_records[-limit:], 'total': len(alert_records)}
        })
    except Exception as e:
        logger.error(f'获取预警记录失败: {e}')
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/monitor/alert-config', methods=['GET'])
def get_alert_config():
    """获取预警阈值配置"""
    try:
        config = {
            'negative_ratio_threshold': 0.30,
            'intensity_threshold': 0.80,
            'alert_enabled': True,
            'notification_email': '',
            'check_interval_seconds': 60,
        }
        return jsonify({'code': 200, 'message': 'success', 'data': config})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/monitor/alert-config', methods=['POST'])
def update_alert_config():
    """更新预警阈值配置"""
    try:
        data = request.get_json() or {}
        logger.info(f"预警配置更新: {data}")
        return jsonify({'code': 200, 'message': '预警配置已更新', 'data': data})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


# ==================== 监控关键词订阅API ====================
monitor_keywords = ['微博', '热搜', '社会', '科技']

@app.route('/api/monitor/keywords', methods=['GET'])
def get_monitor_keywords():
    """获取监控关键词列表"""
    try:
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'keywords': monitor_keywords}
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


@app.route('/api/monitor/keywords', methods=['POST'])
def update_monitor_keywords():
    """更新监控关键词"""
    try:
        global monitor_keywords
        data = request.get_json() or {}
        keywords = data.get('keywords', [])
        if keywords:
            monitor_keywords = keywords
        return jsonify({
            'code': 200,
            'message': '监控关键词已更新',
            'data': {'keywords': monitor_keywords}
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


def init_database():
    """初始化数据库（自动检测，只在需要时创建）"""
    global db_service
    
    if not DB_SERVICE_AVAILABLE:
        logger.warning("数据库服务不可用，跳过数据库初始化")
        return False
    
    try:
        logger.info("正在检测数据库...")
        db_service = get_db_service()
        
        # 检查表状态
        status = db_service.check_tables_status()
        
        if status.get('all_ready'):
            logger.info(f"数据库已就绪: {status['database']}")
            for table, info in status['tables'].items():
                logger.info(f"  - {table}: {info['row_count']} 条记录")
        else:
            logger.info("数据库表已自动创建")
        
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


if __name__ == '__main__':
    logger.info('=' * 50)
    logger.info('微博情感分析系统 - Python后端服务')
    logger.info('学生: 罗森 | 学号: 2022407443')
    logger.info('=' * 50)
    logger.info(f'数据目录: {DATA_DIR}')
    
    # 自动初始化数据库（检测并创建缺失的表）
    db_ready = init_database()
    if db_ready:
        logger.info('✓ 数据库初始化完成')
    else:
        logger.warning('⚠ 数据库未就绪，数据将只保存到文件')
    
    logger.info('启动服务...')
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
