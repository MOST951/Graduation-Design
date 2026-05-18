"""
认证模块API
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging
import random
import string
import re
import os
import json
import base64
import hmac
import hashlib

from services.auth_service import get_auth_service

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)

# ==================== 验证码缓存（进程内存） ====================
# { "register:email": { code, expires, type, created_at } }
_verification_codes = {}


def _vcode_key(email: str, code_type: str) -> str:
    return f'{code_type}:{email}'


def _store_verification_code(email: str, code_type: str, code: str):
    _verification_codes[_vcode_key(email, code_type)] = {
        'code': code,
        'type': code_type,
        'expires': datetime.now() + timedelta(minutes=5),
        'created_at': datetime.now(),
    }


def _get_verification_code(email: str, code_type: str):
    entry = _verification_codes.get(_vcode_key(email, code_type))
    if entry and datetime.now() > entry.get('expires', datetime.min):
        _verification_codes.pop(_vcode_key(email, code_type), None)
        return None
    return entry


def _delete_verification_code(email: str, code_type: str):
    _verification_codes.pop(_vcode_key(email, code_type), None)


def _generate_token(user: dict) -> str:
    secret = os.getenv('JWT_SECRET_KEY') or os.getenv('JWT_SECRET') or os.getenv('SECRET_KEY') or 'dev-secret'
    payload = {
        'sub': str(user['id']),
        'username': user['username'],
        'role': user['role'],
        'iat': int(datetime.now().timestamp()),
        'exp': int((datetime.now() + timedelta(hours=2)).timestamp()),
    }
    payload_json = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode().rstrip('=')
    signature = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    return f'{payload_b64}.{signature_b64}'


def _format_user(user: dict) -> dict:
    return {
        'id': user['id'],
        'username': user['username'],
        'name': user.get('nickname') or user.get('name') or user['username'],
        'email': user.get('email', ''),
        'role': user.get('role', 'user'),
        'avatar': user.get('avatar') or 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    }

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
        
        success, message, user = get_auth_service().login(username, password, request.remote_addr)
        if not success:
            return jsonify({
                'code': 401,
                'message': message,
            }), 401
        
        token = _generate_token(user)
        formatted_user = _format_user(user)
        
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'accessToken': token,
                'tokenType': 'Bearer',
                'user': formatted_user
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
    user = get_auth_service().get_user_by_id(1)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': _format_user(user)
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
        if code_type == 'register' and get_auth_service().email_exists(email):
            return jsonify({'code': 409, 'message': '该邮箱已被注册'}), 409

        # 防刷：同一邮箱 60 秒内不能重复发送
        cached = _get_verification_code(email, code_type)
        created_at = cached.get('created_at') if cached else None
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if cached and created_at and (datetime.now() - created_at).total_seconds() < 60:
            return jsonify({'code': 429, 'message': '发送过于频繁，请60秒后重试'}), 429

        # 生成 6 位数字验证码
        code = ''.join(random.choices(string.digits, k=6))

        # 存入缓存（5 分钟有效）
        _store_verification_code(email, code_type, code)

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
        cached = _get_verification_code(email, 'register')
        if not cached:
            return jsonify({'code': 400, 'message': '请先获取验证码'}), 400

        expires = cached.get('expires')
        if expires and datetime.now() > expires:
            _delete_verification_code(email, 'register')
            return jsonify({'code': 400, 'message': '验证码已过期，请重新获取'}), 400

        if cached['code'] != code:
            return jsonify({'code': 400, 'message': '验证码错误'}), 400

        # 验证通过，移除已使用的验证码
        _delete_verification_code(email, 'register')

        # 用户名默认取邮箱前缀
        if not username:
            username = email.split('@')[0]

        success, message, user = get_auth_service().register(username, password, email, username)
        if not success:
            return jsonify({'code': 409, 'message': message}), 409

        token = _generate_token(user)
        formatted_user = _format_user(user)
        logger.info(f'用户注册成功: {username} ({email}), id={user["id"]}')

        return jsonify({
            'code': 200,
            'message': '注册成功',
            'data': {
                'accessToken': token,
                'tokenType': 'Bearer',
                'user': formatted_user
            }
        })

    except Exception as e:
        logger.error(f'Register failed: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)}), 500

@auth_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'code': 200, 'message': 'Auth service is running'})
