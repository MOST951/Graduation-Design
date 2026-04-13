"""
认证模块API
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)

# 用户数据
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

@auth_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'code': 200, 'message': 'Auth service is running'})
