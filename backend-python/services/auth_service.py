#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户认证服务 - 邮箱注册登录、密码找回
微博情感分析系统 - 毕业设计

作者: 罗森
学号: 2022407443
"""

import pymysql
from pymysql.cursors import DictCursor
import hashlib
import secrets
import time
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class AuthService:
    """用户认证服务"""
    
    # 数据库配置
    DB_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'weibo_sentiment_graduation',
        'charset': 'utf8mb4'
    }
    
    # 验证码存储 {email: {code, expire_time, type, attempts}}
    verification_codes: Dict[str, Dict] = {}
    
    def __init__(self, config: Dict = None):
        """初始化认证服务"""
        if config:
            self.DB_CONFIG.update(config)
        self._ensure_user_table()
    
    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            **self.DB_CONFIG,
            cursorclass=DictCursor
        )
    
    def _ensure_user_table(self):
        """确保用户表存在"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS `users` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
            `email` VARCHAR(255) NOT NULL COMMENT '邮箱地址',
            `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
            `salt` VARCHAR(64) NOT NULL COMMENT '密码盐值',
            `username` VARCHAR(64) COMMENT '用户名',
            `nickname` VARCHAR(64) COMMENT '昵称',
            `avatar` VARCHAR(512) DEFAULT '/avatars/default.png' COMMENT '头像URL',
            `role` ENUM('admin', 'user') DEFAULT 'user' COMMENT '角色',
            `status` ENUM('active', 'inactive', 'banned') DEFAULT 'active' COMMENT '状态',
            `email_verified` TINYINT DEFAULT 0 COMMENT '邮箱是否验证',
            `last_login_at` DATETIME COMMENT '最后登录时间',
            `last_login_ip` VARCHAR(64) COMMENT '最后登录IP',
            `login_count` INT DEFAULT 0 COMMENT '登录次数',
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            `updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            UNIQUE KEY `uk_email` (`email`),
            UNIQUE KEY `uk_username` (`username`),
            INDEX `idx_status` (`status`),
            INDEX `idx_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='用户表 - 毕业设计'
        """
        
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(create_table_sql)
            conn.commit()
            conn.close()
            logger.info("用户表已就绪")
        except Exception as e:
            logger.error(f"创建用户表失败: {e}")
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """
        密码哈希
        
        Args:
            password: 明文密码
            salt: 盐值（可选，不提供则生成新的）
            
        Returns:
            (password_hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # 使用 PBKDF2-like 方式：多次哈希
        hash_input = f"{password}{salt}"
        for _ in range(10000):
            hash_input = hashlib.sha256(hash_input.encode()).hexdigest()
        
        return hash_input, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == password_hash
    
    def _validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))
    
    def _validate_password(self, password: str) -> Tuple[bool, str]:
        """
        验证密码强度
        
        Returns:
            (is_valid, error_message)
        """
        if len(password) < 6:
            return False, "密码长度不能少于6位"
        if len(password) > 32:
            return False, "密码长度不能超过32位"
        if not re.search(r'[a-zA-Z]', password):
            return False, "密码必须包含字母"
        if not re.search(r'\d', password):
            return False, "密码必须包含数字"
        return True, ""
    
    def generate_verification_code(self, email: str, code_type: str = 'register') -> Tuple[bool, str, str]:
        """
        生成验证码
        
        Args:
            email: 邮箱地址
            code_type: 验证码类型 (register/login/reset)
            
        Returns:
            (success, message, code)
        """
        if not self._validate_email(email):
            return False, "邮箱格式不正确", ""
        
        # 检查发送频率（60秒内只能发送一次）
        key = f"{email}:{code_type}"
        if key in self.verification_codes:
            last_send = self.verification_codes[key].get('send_time', 0)
            if time.time() - last_send < 60:
                remaining = int(60 - (time.time() - last_send))
                return False, f"请{remaining}秒后再试", ""
        
        # 生成6位数字验证码
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # 存储验证码（5分钟有效）
        self.verification_codes[key] = {
            'code': code,
            'expire_time': time.time() + 300,
            'send_time': time.time(),
            'type': code_type,
            'attempts': 0
        }
        
        logger.info(f"验证码已生成: {email} ({code_type}) -> {code}")
        return True, "验证码已发送", code
    
    def verify_code(self, email: str, code: str, code_type: str = 'register') -> Tuple[bool, str]:
        """
        验证验证码
        
        Returns:
            (success, message)
        """
        key = f"{email}:{code_type}"
        
        if key not in self.verification_codes:
            return False, "请先获取验证码"
        
        stored = self.verification_codes[key]
        
        # 检查尝试次数
        if stored['attempts'] >= 5:
            del self.verification_codes[key]
            return False, "验证码错误次数过多，请重新获取"
        
        # 检查是否过期
        if time.time() > stored['expire_time']:
            del self.verification_codes[key]
            return False, "验证码已过期，请重新获取"
        
        # 验证码校验
        if code != stored['code']:
            stored['attempts'] += 1
            remaining = 5 - stored['attempts']
            return False, f"验证码错误，还剩{remaining}次机会"
        
        # 验证成功，删除验证码
        del self.verification_codes[key]
        return True, "验证成功"
    
    def register(self, email: str, password: str, code: str, username: str = None) -> Tuple[bool, str, Dict]:
        """
        用户注册
        
        Args:
            email: 邮箱
            password: 密码
            code: 验证码
            username: 用户名（可选）
            
        Returns:
            (success, message, user_data)
        """
        # 验证邮箱格式
        if not self._validate_email(email):
            return False, "邮箱格式不正确", {}
        
        # 验证密码强度
        valid, msg = self._validate_password(password)
        if not valid:
            return False, msg, {}
        
        # 验证验证码
        valid, msg = self.verify_code(email, code, 'register')
        if not valid:
            return False, msg, {}
        
        # 检查邮箱是否已注册
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    conn.close()
                    return False, "该邮箱已注册", {}
                
                # 如果提供了用户名，检查是否已存在
                if username:
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    if cursor.fetchone():
                        conn.close()
                        return False, "该用户名已被使用", {}
                
                # 生成密码哈希
                password_hash, salt = self._hash_password(password)
                
                # 生成默认用户名
                if not username:
                    username = email.split('@')[0]
                    # 确保用户名唯一
                    base_username = username
                    counter = 1
                    while True:
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        if not cursor.fetchone():
                            break
                        username = f"{base_username}{counter}"
                        counter += 1
                
                # 插入用户
                cursor.execute("""
                    INSERT INTO users (email, password_hash, salt, username, nickname, email_verified)
                    VALUES (%s, %s, %s, %s, %s, 1)
                """, (email, password_hash, salt, username, username))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                # 获取用户信息
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                conn.close()
                
                logger.info(f"用户注册成功: {email}")
                return True, "注册成功", {
                    'id': user['id'],
                    'email': user['email'],
                    'username': user['username'],
                    'nickname': user['nickname'],
                    'avatar': user['avatar'],
                    'role': user['role']
                }
                
        except Exception as e:
            logger.error(f"注册失败: {e}")
            return False, f"注册失败: {str(e)}", {}
    
    def login_by_email(self, email: str, password: str, ip: str = None) -> Tuple[bool, str, Dict]:
        """
        邮箱密码登录
        
        Returns:
            (success, message, user_data)
        """
        if not self._validate_email(email):
            return False, "邮箱格式不正确", {}
        
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if not user:
                    conn.close()
                    return False, "该邮箱未注册", {}
                
                if user['status'] == 'banned':
                    conn.close()
                    return False, "账号已被禁用", {}
                
                # 验证密码
                if not self._verify_password(password, user['password_hash'], user['salt']):
                    conn.close()
                    return False, "密码错误", {}
                
                # 更新登录信息
                cursor.execute("""
                    UPDATE users SET 
                        last_login_at = NOW(),
                        last_login_ip = %s,
                        login_count = login_count + 1
                    WHERE id = %s
                """, (ip, user['id']))
                conn.commit()
                conn.close()
                
                logger.info(f"用户登录成功: {email}")
                return True, "登录成功", {
                    'id': user['id'],
                    'email': user['email'],
                    'username': user['username'],
                    'nickname': user['nickname'],
                    'avatar': user['avatar'],
                    'role': user['role']
                }
                
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False, f"登录失败: {str(e)}", {}
    
    def login_by_code(self, email: str, code: str, ip: str = None) -> Tuple[bool, str, Dict]:
        """
        邮箱验证码登录
        
        Returns:
            (success, message, user_data)
        """
        # 验证验证码
        valid, msg = self.verify_code(email, code, 'login')
        if not valid:
            return False, msg, {}
        
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if not user:
                    # 验证码登录时，如果用户不存在，自动创建账号
                    # 生成随机密码
                    random_password = secrets.token_urlsafe(12)
                    password_hash, salt = self._hash_password(random_password)
                    username = email.split('@')[0]
                    
                    # 确保用户名唯一
                    base_username = username
                    counter = 1
                    while True:
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        if not cursor.fetchone():
                            break
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    cursor.execute("""
                        INSERT INTO users (email, password_hash, salt, username, nickname, email_verified)
                        VALUES (%s, %s, %s, %s, %s, 1)
                    """, (email, password_hash, salt, username, username))
                    
                    user_id = cursor.lastrowid
                    conn.commit()
                    
                    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    user = cursor.fetchone()
                    
                    logger.info(f"验证码登录自动注册: {email}")
                
                if user['status'] == 'banned':
                    conn.close()
                    return False, "账号已被禁用", {}
                
                # 更新登录信息
                cursor.execute("""
                    UPDATE users SET 
                        last_login_at = NOW(),
                        last_login_ip = %s,
                        login_count = login_count + 1
                    WHERE id = %s
                """, (ip, user['id']))
                conn.commit()
                conn.close()
                
                logger.info(f"验证码登录成功: {email}")
                return True, "登录成功", {
                    'id': user['id'],
                    'email': user['email'],
                    'username': user['username'],
                    'nickname': user['nickname'],
                    'avatar': user['avatar'],
                    'role': user['role']
                }
                
        except Exception as e:
            logger.error(f"验证码登录失败: {e}")
            return False, f"登录失败: {str(e)}", {}
    
    def reset_password(self, email: str, code: str, new_password: str) -> Tuple[bool, str]:
        """
        重置密码
        
        Returns:
            (success, message)
        """
        # 验证密码强度
        valid, msg = self._validate_password(new_password)
        if not valid:
            return False, msg
        
        # 验证验证码
        valid, msg = self.verify_code(email, code, 'reset')
        if not valid:
            return False, msg
        
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if not user:
                    conn.close()
                    return False, "该邮箱未注册"
                
                # 生成新密码哈希
                password_hash, salt = self._hash_password(new_password)
                
                # 更新密码
                cursor.execute("""
                    UPDATE users SET password_hash = %s, salt = %s WHERE id = %s
                """, (password_hash, salt, user['id']))
                conn.commit()
                conn.close()
                
                logger.info(f"密码重置成功: {email}")
                return True, "密码重置成功"
                
        except Exception as e:
            logger.error(f"密码重置失败: {e}")
            return False, f"密码重置失败: {str(e)}"
    
    def check_email_exists(self, email: str) -> bool:
        """检查邮箱是否已注册"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception as e:
            logger.error(f"检查邮箱失败: {e}")
            return False
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据ID获取用户信息"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
            conn.close()
            
            if user:
                return {
                    'id': user['id'],
                    'email': user['email'],
                    'username': user['username'],
                    'nickname': user['nickname'],
                    'avatar': user['avatar'],
                    'role': user['role'],
                    'status': user['status'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None
                }
            return None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None


# 全局认证服务实例
_auth_service = None

def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
