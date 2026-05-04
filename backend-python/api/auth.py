"""
认证模块API
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging
import random
import string
import hashlib
import re
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)

# ==================== 用户数据存储 ====================
_next_user_id = 3

users = {
    'admin': {
        'id': 1,
        'username': 'admin',
        'password': 'admin123',
        'name': '系统管理员',
        'email': 'admin@example.com',
        'role': 'admin',
        'avatar': 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    },
    'user01': {
        'id': 2,
        'username': 'user01',
        'password': 'user123',
        'name': '普通用户',
        'email': 'user01@example.com',
        'role': 'user',
        'avatar': 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    }
}

# 邮箱 → 用户名 快速索引
_email_to_username = {u['email']: u['username'] for u in users.values()}

# ==================== 验证码缓存 ====================
# { email: { code: '123456', expires: datetime, type: 'register' } }
_verification_codes = {}

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        username = data.get('username', '')
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({
                'code': 400,
                'message': '用户名和密码不能为空',
            }), 400
        
        user = users.get(username)
        if not user or user['password'] != password:
            return jsonify({
                'code': 401,
                'message': '用户名或密码错误',
            }), 401
        
        # 生成模拟token
        token = f"token_{username}_{datetime.now().timestamp()}"
        
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'accessToken': token,
                'tokenType': 'Bearer',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'email': user['email'],
                    'role': user['role'],
                    'avatar': user['avatar'],
                }
            }
        })
    except Exception as e:
        logger.error(f'Login failed: {e}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': str(e),
        }), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    return jsonify({
        'code': 200,
        'message': '登出成功',
    })

@auth_bp.route('/info', methods=['GET'])
def get_user_info():
    """获取用户信息"""
    # 简化处理，返回admin用户信息
    user = users['admin']
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': user['id'],
            'username': user['username'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'avatar': user['avatar'],
        }
    })

@auth_bp.route('/send-code', methods=['POST'])
def send_verification_code():
    """发送邮箱验证码"""
    try:
        data = request.json or {}
        email = data.get('email', '').strip()
        code_type = data.get('type', 'register')  # register / reset

        if not email:
            return jsonify({'code': 400, 'message': '邮箱不能为空'}), 400

        if not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', email):
            return jsonify({'code': 400, 'message': '邮箱格式不正确'}), 400

        # 注册场景：检查邮箱是否已被注册
        if code_type == 'register' and email in _email_to_username:
            return jsonify({'code': 409, 'message': '该邮箱已被注册'}), 409

        # 防刷：同一邮箱 60 秒内不能重复发送
        cached = _verification_codes.get(email)
        if cached and (datetime.now() - cached.get('created_at', datetime.min)).total_seconds() < 60:
            return jsonify({'code': 429, 'message': '发送过于频繁，请60秒后重试'}), 429

        # 生成 6 位数字验证码
        code = ''.join(random.choices(string.digits, k=6))

        # 存入缓存（5 分钟有效）
        _verification_codes[email] = {
            'code': code,
            'expires': datetime.now() + timedelta(minutes=5),
            'type': code_type,
            'created_at': datetime.now(),
        }

        logger.info(f'验证码已生成: {email} -> {code} (type={code_type})')

        # ---- 发送邮件 ----
        from services.email_service import send_verification_email
        email_sent = send_verification_email(email, code, expire_minutes=5)

        # 开发环境始终返回 debug_code 方便调试
        is_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

        return jsonify({
            'code': 200,
            'message': '验证码已发送到您的邮箱' if email_sent else '验证码已生成（邮件服务未配置，请查看控制台日志）',
            'data': {
                'debug_code': code if is_debug else None,
                'email_sent': email_sent,
            }
        })

    except Exception as e:
        logger.error(f'Send code failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    global _next_user_id

    try:
        data = request.json or {}
        email = data.get('email', '').strip()
        code = data.get('code', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        # ---- 参数校验 ----
        if not email or not password:
            return jsonify({'code': 400, 'message': '邮箱和密码不能为空'}), 400

        if not code:
            return jsonify({'code': 400, 'message': '验证码不能为空'}), 400

        if len(password) < 6 or len(password) > 32:
            return jsonify({'code': 400, 'message': '密码长度需为6-32位'}), 400

        if not re.search(r'[a-zA-Z]', password) or not re.search(r'\d', password):
            return jsonify({'code': 400, 'message': '密码必须包含字母和数字'}), 400

        # ---- 验证码校验 ----
        cached = _verification_codes.get(email)
        if not cached:
            return jsonify({'code': 400, 'message': '请先获取验证码'}), 400

        if datetime.now() > cached['expires']:
            _verification_codes.pop(email, None)
            return jsonify({'code': 400, 'message': '验证码已过期，请重新获取'}), 400

        if cached['code'] != code:
            return jsonify({'code': 400, 'message': '验证码错误'}), 400

        # 验证通过，移除已使用的验证码
        _verification_codes.pop(email, None)

        # ---- 重复检查 ----
        if email in _email_to_username:
            return jsonify({'code': 409, 'message': '该邮箱已被注册'}), 409

        # 用户名默认取邮箱前缀
        if not username:
            username = email.split('@')[0]

        # 用户名去重
        base_username = username
        suffix = 1
        while username in users:
            username = f'{base_username}{suffix}'
            suffix += 1

        if username in users:
            return jsonify({'code': 409, 'message': '用户名已存在'}), 409

        # ---- 创建用户 ----
        new_user = {
            'id': _next_user_id,
            'username': username,
            'password': password,
            'name': username,
            'email': email,
            'role': 'user',
            'avatar': 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
            'created_at': datetime.now().isoformat(),
        }

        users[username] = new_user
        _email_to_username[email] = username
        _next_user_id += 1

        logger.info(f'用户注册成功: {username} ({email}), id={new_user["id"]}')

        # 同时写入数据库（如果可用）
        _save_user_to_db(new_user)

        # 自动登录：生成 token
        token = f"token_{username}_{datetime.now().timestamp()}"

        return jsonify({
            'code': 200,
            'message': '注册成功',
            'data': {
                'accessToken': token,
                'tokenType': 'Bearer',
                'user': {
                    'id': new_user['id'],
                    'username': new_user['username'],
                    'name': new_user['name'],
                    'email': new_user['email'],
                    'role': new_user['role'],
                    'avatar': new_user['avatar'],
                }
            }
        })

    except Exception as e:
        logger.error(f'Register failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500


def _save_user_to_db(user: dict):
    """尝试将用户持久化到 MySQL（非必须，失败静默）"""
    try:
        from services.database_service import get_db_service
        db = get_db_service()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT IGNORE INTO users (username, password, email, roles, status, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, NOW(), NOW())""",
                    (user['username'], user['password'], user['email'], user['role'], 'active')
                )
            conn.commit()
        logger.info(f'用户已持久化到数据库: {user["username"]}')
    except Exception as e:
        logger.warning(f'用户持久化失败（不影响注册）: {e}')


@auth_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'code': 200, 'message': 'Auth service is running'})
