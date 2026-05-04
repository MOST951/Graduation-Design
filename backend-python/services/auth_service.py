#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户认证服务 - 用户名密码登录
微博情感分析系统 - 毕业设计

作者: 罗森
学号: 2022407443
"""

import pymysql
from pymysql.cursors import DictCursor
import hashlib
import secrets
import os
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class AuthService:
    """用户认证服务"""
    
    # 数据库配置
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', '123456'),
        'database': os.getenv('DB_NAME', 'weibo_sentiment_graduation'),
        'charset': 'utf8mb4'
    }
    
    # 默认用户（系统启动时自动创建）
    DEFAULT_USERS = [
        {'username': 'admin', 'password': 'admin123', 'nickname': '系统管理员',
         'email': 'admin@example.com', 'role': 'admin'},
        {'username': 'user01', 'password': 'user123', 'nickname': '普通用户',
         'email': 'user01@example.com', 'role': 'user'},
    ]
    
    def __init__(self, config: Dict = None):
        """初始化认证服务"""
        if config:
            self.DB_CONFIG.update(config)
        self._ensure_user_table()
        self._seed_default_users()
    
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
            `username` VARCHAR(64) NOT NULL COMMENT '用户名',
            `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
            `salt` VARCHAR(64) NOT NULL COMMENT '密码盐值',
            `nickname` VARCHAR(64) COMMENT '昵称',
            `email` VARCHAR(255) DEFAULT '' COMMENT '邮箱地址',
            `avatar` VARCHAR(512) DEFAULT '/avatars/default.png' COMMENT '头像URL',
            `role` ENUM('admin', 'user') DEFAULT 'user' COMMENT '角色',
            `status` ENUM('active', 'inactive', 'banned') DEFAULT 'active' COMMENT '状态',
            `last_login_at` DATETIME COMMENT '最后登录时间',
            `last_login_ip` VARCHAR(64) COMMENT '最后登录IP',
            `login_count` INT DEFAULT 0 COMMENT '登录次数',
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            `updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
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
    
    def _seed_default_users(self):
        """自动创建默认用户（幂等）"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                for u in self.DEFAULT_USERS:
                    cursor.execute("SELECT id FROM users WHERE username = %s", (u['username'],))
                    if cursor.fetchone():
                        continue
                    password_hash, salt = self._hash_password(u['password'])
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, salt, nickname, email, role)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (u['username'], password_hash, salt, u['nickname'], u['email'], u['role']))
                    logger.info(f"默认用户已创建: {u['username']} ({u['role']})")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"创建默认用户失败: {e}")
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """密码哈希"""
        if salt is None:
            salt = secrets.token_hex(32)
        hash_input = f"{password}{salt}"
        for _ in range(10000):
            hash_input = hashlib.sha256(hash_input.encode()).hexdigest()
        return hash_input, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self._hash_password(password, salt)
        return computed_hash == password_hash
    
    def login(self, username: str, password: str, ip: str = None) -> Tuple[bool, str, Dict]:
        """用户名密码登录"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                
                if not user:
                    conn.close()
                    return False, "用户不存在", {}
                
                if user['status'] == 'banned':
                    conn.close()
                    return False, "账号已被禁用", {}
                
                if not self._verify_password(password, user['password_hash'], user['salt']):
                    conn.close()
                    return False, "密码错误", {}
                
                cursor.execute("""
                    UPDATE users SET 
                        last_login_at = NOW(),
                        last_login_ip = %s,
                        login_count = login_count + 1
                    WHERE id = %s
                """, (ip, user['id']))
                conn.commit()
                conn.close()
                
                logger.info(f"用户登录成功: {username}")
                return True, "登录成功", {
                    'id': user['id'],
                    'username': user['username'],
                    'nickname': user['nickname'],
                    'email': user['email'],
                    'avatar': user['avatar'],
                    'role': user['role']
                }
                
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False, f"登录失败: {str(e)}", {}

    def register(self, username: str, password: str, email: str, nickname: str = None, role: str = 'user') -> Tuple[bool, str, Dict]:
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
                if cursor.fetchone():
                    conn.close()
                    return False, "用户名或邮箱已存在", {}

                password_hash, salt = self._hash_password(password)
                cursor.execute("""
                    INSERT INTO users (username, password_hash, salt, nickname, email, role, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (username, password_hash, salt, nickname or username, email, role, 'active'))
                user_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return True, "注册成功", {
                'id': user_id,
                'username': username,
                'nickname': nickname or username,
                'email': email,
                'avatar': '/avatars/default.png',
                'role': role
            }
        except Exception as e:
            logger.error(f"注册失败: {e}")
            return False, f"注册失败: {str(e)}", {}

    def email_exists(self, email: str) -> bool:
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
                    'username': user['username'],
                    'nickname': user['nickname'],
                    'email': user['email'],
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
