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
        'database': os.getenv('DB_NAME', 'weibo_sentiment'),
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

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SHOW COLUMNS FROM users")
                columns = {row['Field'] for row in cursor.fetchall()}
                alter_sql = []
                if 'password_hash' not in columns:
                    alter_sql.append("ADD COLUMN `password_hash` VARCHAR(255) DEFAULT '' COMMENT '密码哈希'")
                if 'salt' not in columns:
                    alter_sql.append("ADD COLUMN `salt` VARCHAR(64) DEFAULT '' COMMENT '密码盐值'")
                if 'nickname' not in columns:
                    alter_sql.append("ADD COLUMN `nickname` VARCHAR(64) DEFAULT '' COMMENT '昵称'")
                if 'avatar' not in columns:
                    alter_sql.append("ADD COLUMN `avatar` VARCHAR(512) DEFAULT '/avatars/default.png' COMMENT '头像URL'")
                if 'role' not in columns:
                    alter_sql.append("ADD COLUMN `role` VARCHAR(32) DEFAULT 'user' COMMENT '角色'")
                if 'last_login_at' not in columns:
                    alter_sql.append("ADD COLUMN `last_login_at` DATETIME NULL COMMENT '最后登录时间'")
                if 'last_login_ip' not in columns:
                    alter_sql.append("ADD COLUMN `last_login_ip` VARCHAR(64) DEFAULT '' COMMENT '最后登录IP'")
                if 'login_count' not in columns:
                    alter_sql.append("ADD COLUMN `login_count` INT DEFAULT 0 COMMENT '登录次数'")
                if alter_sql:
                    cursor.execute(f"ALTER TABLE users {', '.join(alter_sql)}")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"修复用户表结构失败: {e}")
    
    def _bcrypt_hash(self, plain: str) -> str:
        """生成 Java Spring Security 兼容的 BCrypt 哈希.

        论文 6.2.3 双后端协同: DB 中 `password` 列必须是 BCrypt (Spring
        BCryptPasswordEncoder 能识别的 `$2a$/$2b$` 格式), 否则 Java 登录失败.
        Python 自身仍使用 `password_hash` + `salt` 两列做 SHA256+salt 校验,
        `password` 列作为双后端共用字段另存一份 BCrypt.
        """
        try:
            import bcrypt
            return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt(rounds=10)).decode()
        except ImportError:
            logger.warning("bcrypt 库缺失, password 列将存明文 (Java 后端无法登录). pip install bcrypt")
            return plain

    def _seed_default_users(self):
        """自动创建默认用户（幂等）.

        - `password_hash` + `salt`: Python 自己的 SHA256 + salt (旧兼容).
        - `password`: BCrypt 哈希 (论文 6.2.3 供 Java Spring Security 认证).
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SHOW COLUMNS FROM users")
                columns = {row['Field'] for row in cursor.fetchall()}
                for u in self.DEFAULT_USERS:
                    cursor.execute("SELECT * FROM users WHERE username = %s", (u['username'],))
                    existing = cursor.fetchone()
                    password_hash, salt = self._hash_password(u['password'])
                    bcrypt_pwd = self._bcrypt_hash(u['password'])
                    if existing:
                        # 触发重置的两种情形:
                        # 1) Python 侧的 password_hash/salt 缺失或不匹配
                        # 2) password 列不是 BCrypt (可能是明文遗留) —— 否则 Java 登录会失败
                        existing_pwd = str(existing.get('password') or '')
                        pwd_is_bcrypt = existing_pwd.startswith(('$2a$', '$2b$', '$2y$'))
                        needs_reset = (
                            not existing.get('password_hash')
                            or not existing.get('salt')
                            or not self._verify_password(u['password'], existing.get('password_hash', ''), existing.get('salt', ''))
                            or not pwd_is_bcrypt
                        )
                        if needs_reset:
                            fields = ['password_hash', 'salt']
                            values = [password_hash, salt]
                            for field, value in [
                                ('password', bcrypt_pwd),      # 论文 6.2.3: Java BCrypt
                                ('nickname', u['nickname']),
                                ('email', u['email']),
                                ('role', u['role']),
                                ('status', 'active'),
                            ]:
                                if field in columns:
                                    fields.append(field)
                                    values.append(value)
                            set_clause = ', '.join(f'{field} = %s' for field in fields)
                            cursor.execute(
                                f"UPDATE users SET {set_clause} WHERE username = %s",
                                (*values, u['username'])
                            )
                            logger.info(f"默认用户密码已重置 (BCrypt+SHA256): {u['username']} ({u['role']})")
                        continue
                    fields = ['username', 'password_hash', 'salt']
                    values = [u['username'], password_hash, salt]
                    for field, value in [
                        ('password', bcrypt_pwd),      # 论文 6.2.3: Java BCrypt
                        ('nickname', u['nickname']),
                        ('email', u['email']),
                        ('role', u['role']),
                        ('roles', 'ROLE_ADMIN,ROLE_USER' if u['role'] == 'admin' else 'ROLE_USER'),
                        ('status', 'active'),
                    ]:
                        if field in columns:
                            fields.append(field)
                            values.append(value)
                    placeholders = ', '.join(['%s'] * len(fields))
                    cursor.execute(
                        f"INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders})",
                        values
                    )
                    logger.info(f"默认用户已创建 (BCrypt+SHA256): {u['username']} ({u['role']})")
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
                
                status = str(user.get('status') or 'active').lower()
                if status == 'banned':
                    conn.close()
                    return False, "账号已被禁用", {}
                
                if not user.get('password_hash') or not user.get('salt'):
                    conn.close()
                    return False, "密码未初始化，请重启后端服务后重试", {}

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
                    'nickname': user.get('nickname') or user['username'],
                    'email': user.get('email', ''),
                    'avatar': user.get('avatar') or '/avatars/default.png',
                    'role': user.get('role') or 'user'
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
    
    def get_all_users(self) -> list:
        """获取所有用户列表（管理员用）"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, nickname, email, avatar, role, status, "
                    "created_at, last_login_at FROM users ORDER BY id"
                )
                rows = cursor.fetchall()
            conn.close()
            users = []
            for u in rows:
                users.append({
                    'id': u['id'],
                    'username': u['username'],
                    'name': u.get('nickname') or u['username'],
                    'email': u.get('email', ''),
                    'avatar': u.get('avatar') or '/avatars/default.png',
                    'role': u.get('role', 'user'),
                    'status': u.get('status', 'active'),
                    'lastLoginAt': u['last_login_at'].isoformat() if u.get('last_login_at') else None,
                    'createdAt': u['created_at'].isoformat() if u.get('created_at') else None,
                })
            return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []

    def update_user_role(self, user_id: int, role: str) -> bool:
        """更新用户角色"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET role = %s WHERE id = %s", (role, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新用户角色失败: {e}")
            return False

    def update_user_status(self, user_id: int, status: str) -> bool:
        """更新用户状态"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新用户状态失败: {e}")
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
