#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库服务 - 统一数据存储接口
微博情感分析系统 - 毕业设计

作者: 罗森
学号: 2022407443
学校: 四川民族学院 智能科学与技术学院 2248班
指导教师: 罗丹

功能:
1. 连接池管理（支持高并发）
2. 自动重试机制（网络异常时）
3. 批量插入优化（提高性能）
4. 数据验证和清洗（入库前）
5. 事务管理（保证数据一致性）
"""

import os
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
import json
import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Generator
from functools import wraps
import threading

# 尝试导入连接池库
try:
    from dbutils.pooled_db import PooledDB
    POOL_AVAILABLE = True
except ImportError:
    POOL_AVAILABLE = False
    logging.warning("DBUtils未安装，将使用简单连接管理")

# 配置日志
logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (pymysql.Error, ConnectionError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"操作失败，{delay}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(delay * (attempt + 1))  # 指数退避
                    else:
                        logger.error(f"操作失败，已达最大重试次数: {e}")
            raise last_error
        return wrapper
    return decorator


class DatabaseService:
    """数据库服务 - 统一数据存储接口"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', os.getenv('DB_USERNAME', 'root')),
        'password': os.getenv('DB_PASSWORD', '123456'),
        'database': os.getenv('DB_NAME', 'weibo_sentiment'),
        'charset': 'utf8mb4',
        'max_connections': 20,
        'min_cached': 5,
        'max_cached': 10,
        'blocking': True,
        'max_usage': None,
        'set_session': ['SET NAMES utf8mb4', "SET time_zone = '+08:00'"]
    }
    
    def __init__(self, config: Dict = None):
        """
        初始化数据库服务
        
        Args:
            config: 数据库配置字典
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.pool = None
        self._local = threading.local()
        
        # 毕业设计统计
        self.graduation_stats = {
            'total_inserts': 0,
            'total_updates': 0,
            'total_queries': 0,
            'total_errors': 0,
            'start_time': datetime.now(),
            'student_id': '2022407443',
            'student_name': '罗森'
        }
        
        # 必需的表列表
        self.required_tables = [
            'weibo_core_data',
            'sentiment_analysis_results', 
            'tri_dimension_ranking',
            'crawl_batch_log',
            'crawl_request_log',
            'data_quality_log',
            'system_configs',
            'crawl_tasks'
        ]
        
        # 初始化数据库和表
        self._ensure_database_exists()
        
        # 初始化连接池
        self._init_pool()
        
        # 检测并创建缺失的表
        self._ensure_tables_exist()
    
    def _ensure_database_exists(self):
        """确保数据库存在，不存在则创建"""
        database_name = self.config['database']
        
        try:
            # 连接MySQL（不指定数据库）
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                charset=self.config['charset']
            )
            
            with conn.cursor() as cursor:
                # 检查数据库是否存在
                cursor.execute(f"SHOW DATABASES LIKE '{database_name}'")
                exists = cursor.fetchone() is not None
                
                if not exists:
                    logger.info(f"数据库 {database_name} 不存在，正在创建...")
                    cursor.execute(f"""
                        CREATE DATABASE `{database_name}` 
                        CHARACTER SET utf8mb4 
                        COLLATE utf8mb4_unicode_ci
                    """)
                    conn.commit()
                    logger.info(f"数据库 {database_name} 创建成功")
                else:
                    logger.debug(f"数据库 {database_name} 已存在")
            
            conn.close()
            
        except pymysql.Error as e:
            logger.error(f"检查/创建数据库失败: {e}")
            raise
    
    def _ensure_tables_exist(self):
        """确保所有必需的表存在，不存在则创建"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取现有表列表
                    cursor.execute("SHOW TABLES")
                    existing_tables = {list(row.values())[0] for row in cursor.fetchall()}
                    
                    # 检查缺失的表
                    missing_tables = [t for t in self.required_tables if t not in existing_tables]
                    
                    if not missing_tables:
                        logger.debug("所有必需的表已存在")
                        return
                    
                    logger.info(f"检测到缺失的表: {missing_tables}，正在创建...")
                    
                    # 创建缺失的表
                    for table_name in missing_tables:
                        self._create_table(cursor, table_name)
                    
                    conn.commit()
                    logger.info(f"成功创建 {len(missing_tables)} 个表")
                    
        except pymysql.Error as e:
            logger.error(f"检查/创建表失败: {e}")
            # 不抛出异常，允许服务继续运行
    
    def _create_table(self, cursor, table_name: str):
        """创建单个表"""
        table_definitions = {
            'weibo_core_data': """
                CREATE TABLE IF NOT EXISTS `weibo_core_data` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `weibo_id` BIGINT NOT NULL COMMENT '微博ID',
                    `content` TEXT NOT NULL COMMENT '微博内容',
                    `created_at` DATETIME COMMENT '发布时间',
                    `crawled_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
                    `user_id` BIGINT DEFAULT 0 COMMENT '用户ID',
                    `user_name` VARCHAR(128) DEFAULT '未知用户' COMMENT '用户昵称',
                    `verified` TINYINT DEFAULT 0 COMMENT '是否认证',
                    `followers_count` INT DEFAULT 0 COMMENT '粉丝数',
                    `reposts_count` INT DEFAULT 0 COMMENT '转发数',
                    `comments_count` INT DEFAULT 0 COMMENT '评论数',
                    `attitudes_count` INT DEFAULT 0 COMMENT '点赞数',
                    `has_image` TINYINT DEFAULT 0 COMMENT '是否有图片',
                    `has_video` TINYINT DEFAULT 0 COMMENT '是否有视频',
                    `image_urls` JSON COMMENT '图片URL列表',
                    `location` VARCHAR(128) COMMENT '发布位置',
                    `topics` JSON COMMENT '话题标签',
                    `source` VARCHAR(128) COMMENT '来源',
                    `keyword` VARCHAR(128) COMMENT '采集关键词',
                    `batch_id` VARCHAR(64) COMMENT '采集批次ID',
                    `is_processed` TINYINT DEFAULT 0 COMMENT '是否已情感分析',
                    `is_ranked` TINYINT DEFAULT 0 COMMENT '是否已三维度排序',
                    `graduation_batch` TINYINT DEFAULT 1 COMMENT '毕业设计批次标记',
                    `student_id` VARCHAR(20) DEFAULT '2022407443' COMMENT '学号',
                    `update_count` INT DEFAULT 0 COMMENT '更新次数',
                    `last_updated` DATETIME ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
                    UNIQUE KEY `uk_weibo_id` (`weibo_id`),
                    INDEX `idx_created_at` (`created_at`),
                    INDEX `idx_user_id` (`user_id`),
                    INDEX `idx_keyword` (`keyword`),
                    INDEX `idx_batch_id` (`batch_id`),
                    INDEX `idx_graduation` (`graduation_batch`, `student_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='微博核心数据表 - 毕业设计'
            """,
            
            'sentiment_analysis_results': """
                CREATE TABLE IF NOT EXISTS `sentiment_analysis_results` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `weibo_id` BIGINT NOT NULL COMMENT '微博ID',
                    `dict_score` DECIMAL(5,4) DEFAULT 0 COMMENT '词典得分',
                    `bert_score` DECIMAL(5,4) DEFAULT 0 COMMENT 'BERT得分',
                    `hybrid_score` DECIMAL(5,4) DEFAULT 0 COMMENT '混合得分(级联策略)',
                    `sentiment_class` ENUM('positive','neutral','negative') DEFAULT 'neutral' COMMENT '情感分类',
                    `intensity` DECIMAL(3,2) DEFAULT 0 COMMENT '情感强度',
                    `confidence` DECIMAL(3,2) DEFAULT 0 COMMENT '置信度',
                    `dict_positive_count` INT DEFAULT 0 COMMENT '词典正面词数',
                    `dict_negative_count` INT DEFAULT 0 COMMENT '词典负面词数',
                    `bert_positive_prob` DECIMAL(5,4) DEFAULT NULL COMMENT 'BERT正面概率',
                    `bert_neutral_prob` DECIMAL(5,4) DEFAULT NULL COMMENT 'BERT中性概率',
                    `bert_negative_prob` DECIMAL(5,4) DEFAULT NULL COMMENT 'BERT负面概率',
                    `analysis_method` VARCHAR(32) DEFAULT 'cascade' COMMENT '分析方法(cascade-lexicon/cascade-bert)',
                    `model_version` VARCHAR(32) DEFAULT 'v2.0.0' COMMENT '模型版本',
                    `analysis_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
                    `processing_time_ms` INT DEFAULT NULL COMMENT '处理耗时(毫秒)',
                    `graduation_flag` TINYINT DEFAULT 1 COMMENT '毕业设计标记',
                    `student_id` VARCHAR(20) DEFAULT '2022407443' COMMENT '学号',
                    UNIQUE KEY `uk_weibo_analysis` (`weibo_id`, `analysis_method`),
                    INDEX `idx_sentiment_class` (`sentiment_class`),
                    INDEX `idx_analysis_time` (`analysis_time`),
                    INDEX `idx_graduation` (`graduation_flag`, `student_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='情感分析结果表 - 毕业设计'
            """,
            
            'tri_dimension_ranking': """
                CREATE TABLE IF NOT EXISTS `tri_dimension_ranking` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `weibo_id` BIGINT NOT NULL COMMENT '微博ID',
                    `sentiment_score` DECIMAL(5,4) DEFAULT 0 COMMENT '情感得分',
                    `sentiment_category` VARCHAR(32) DEFAULT 'neutral' COMMENT '情感分类',
                    `reposts_count` INT DEFAULT 0 COMMENT '转发数',
                    `comments_count` INT DEFAULT 0 COMMENT '评论数',
                    `attitudes_count` INT DEFAULT 0 COMMENT '点赞数',
                    `raw_popularity` DECIMAL(10,4) DEFAULT 0 COMMENT '原始热度(log平滑后)',
                    `popularity_score` DECIMAL(10,4) DEFAULT 0 COMMENT '归一化热度得分',
                    `popularity_class` ENUM('high','medium','low') DEFAULT 'low' COMMENT '热度等级',
                    `time_decay` DECIMAL(5,4) DEFAULT 1 COMMENT '时间衰减因子γ(Δt)',
                    `alpha_weight` DECIMAL(3,2) DEFAULT 0.40 COMMENT '情感权重ω₁',
                    `beta_weight` DECIMAL(3,2) DEFAULT 0.40 COMMENT '热度权重ω₂',
                    `gamma_weight` DECIMAL(3,2) DEFAULT 0.20 COMMENT '时效性权重ω₃',
                    `composite_score` DECIMAL(10,4) DEFAULT 0 COMMENT '综合排序得分',
                    `ranking_position` INT DEFAULT 0 COMMENT '排名位置',
                    `batch_id` VARCHAR(64) COMMENT '计算批次ID',
                    `calculation_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
                    `algorithm_version` VARCHAR(32) DEFAULT 'v2.0.0' COMMENT '算法版本(级联+半衰期)',
                    `graduation_flag` TINYINT DEFAULT 1 COMMENT '毕业设计标记',
                    `student_id` VARCHAR(20) DEFAULT '2022407443' COMMENT '学号',
                    UNIQUE KEY `uk_weibo_batch` (`weibo_id`, `batch_id`),
                    INDEX `idx_composite_score` (`composite_score` DESC),
                    INDEX `idx_ranking` (`ranking_position`),
                    INDEX `idx_calculation_time` (`calculation_time`),
                    INDEX `idx_graduation` (`graduation_flag`, `student_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='三维度排序结果表 - 毕业设计核心创新点'
            """,
            
            'crawl_batch_log': """
                CREATE TABLE IF NOT EXISTS `crawl_batch_log` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `batch_id` VARCHAR(64) NOT NULL COMMENT '批次ID',
                    `task_name` VARCHAR(128) COMMENT '任务名称',
                    `task_type` VARCHAR(64) COMMENT '任务类型',
                    `keywords` JSON COMMENT '采集关键词列表',
                    `status` ENUM('pending','running','completed','failed') DEFAULT 'pending' COMMENT '状态',
                    `total_weibos` INT DEFAULT 0 COMMENT '采集总数',
                    `success_count` INT DEFAULT 0 COMMENT '成功数',
                    `failure_count` INT DEFAULT 0 COMMENT '失败数',
                    `start_time` DATETIME COMMENT '开始时间',
                    `end_time` DATETIME COMMENT '结束时间',
                    `error_message` TEXT COMMENT '错误信息',
                    `graduation_batch` TINYINT DEFAULT 1 COMMENT '毕业设计批次',
                    `student_id` VARCHAR(20) DEFAULT '2022407443' COMMENT '学号',
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    UNIQUE KEY `uk_batch_id` (`batch_id`),
                    INDEX `idx_status` (`status`),
                    INDEX `idx_created_at` (`created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='爬虫批次日志表'
            """,
            
            'crawl_request_log': """
                CREATE TABLE IF NOT EXISTS `crawl_request_log` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `batch_id` VARCHAR(64) COMMENT '批次ID',
                    `request_url` VARCHAR(512) COMMENT '请求URL',
                    `request_type` VARCHAR(32) COMMENT '请求类型',
                    `status_code` INT COMMENT 'HTTP状态码',
                    `response_time_ms` INT COMMENT '响应时间(毫秒)',
                    `success` TINYINT DEFAULT 0 COMMENT '是否成功',
                    `error_message` TEXT COMMENT '错误信息',
                    `request_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '请求时间',
                    INDEX `idx_batch_id` (`batch_id`),
                    INDEX `idx_request_time` (`request_time`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='爬虫请求日志表'
            """,
            
            'data_quality_log': """
                CREATE TABLE IF NOT EXISTS `data_quality_log` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `batch_id` VARCHAR(64) COMMENT '批次ID',
                    `check_type` VARCHAR(32) COMMENT '检查类型',
                    `total_records` INT DEFAULT 0 COMMENT '总记录数',
                    `valid_records` INT DEFAULT 0 COMMENT '有效记录数',
                    `invalid_records` INT DEFAULT 0 COMMENT '无效记录数',
                    `quality_score` DECIMAL(5,2) DEFAULT 0 COMMENT '质量得分',
                    `issues` JSON COMMENT '问题详情',
                    `graduation_check` TINYINT DEFAULT 1 COMMENT '毕业设计检查',
                    `check_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
                    INDEX `idx_batch_id` (`batch_id`),
                    INDEX `idx_check_time` (`check_time`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='数据质量日志表'
            """,
            
            'crawl_tasks': """
                CREATE TABLE IF NOT EXISTS `crawl_tasks` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `task_id` VARCHAR(64) NOT NULL COMMENT '任务ID',
                    `sys_user_id` VARCHAR(64) DEFAULT '' COMMENT '系统用户标识',
                    `keywords` JSON COMMENT '采集关键词列表',
                    `pages` INT DEFAULT 3 COMMENT '采集页数',
                    `crawl_hot` TINYINT DEFAULT 0 COMMENT '是否爬取热搜',
                    `status` VARCHAR(20) DEFAULT 'pending' COMMENT '任务状态',
                    `progress` INT DEFAULT 0 COMMENT '进度百分比',
                    `collected` INT DEFAULT 0 COMMENT '已采集条数',
                    `start_time` DATETIME COMMENT '开始时间',
                    `end_time` DATETIME COMMENT '结束时间',
                    `error` TEXT COMMENT '错误信息',
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    `updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                    UNIQUE KEY `uk_task_id` (`task_id`),
                    INDEX `idx_sys_user_id` (`sys_user_id`),
                    INDEX `idx_status` (`status`),
                    INDEX `idx_created_at` (`created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='采集任务持久化表（按用户隔离）'
            """,
            
            'system_configs': """
                CREATE TABLE IF NOT EXISTS `system_configs` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                    `config_key` VARCHAR(64) NOT NULL COMMENT '配置键',
                    `config_value` TEXT COMMENT '配置值',
                    `config_type` VARCHAR(32) DEFAULT 'string' COMMENT '配置类型',
                    `description` VARCHAR(256) COMMENT '描述',
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    `updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                    UNIQUE KEY `uk_config_key` (`config_key`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='系统配置表'
            """
        }
        
        if table_name in table_definitions:
            try:
                cursor.execute(table_definitions[table_name])
                logger.info(f"表 {table_name} 创建成功")
            except pymysql.Error as e:
                logger.error(f"创建表 {table_name} 失败: {e}")
        else:
            logger.warning(f"未找到表 {table_name} 的定义")
    
    def check_tables_status(self) -> Dict:
        """
        检查所有表的状态
        
        Returns:
            表状态信息
        """
        status = {
            'database': self.config['database'],
            'tables': {},
            'all_ready': True
        }
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    existing_tables = {list(row.values())[0] for row in cursor.fetchall()}
                    
                    for table in self.required_tables:
                        exists = table in existing_tables
                        row_count = 0
                        
                        if exists:
                            cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                            row_count = cursor.fetchone()['cnt']
                        else:
                            status['all_ready'] = False
                        
                        status['tables'][table] = {
                            'exists': exists,
                            'row_count': row_count
                        }
        except pymysql.Error as e:
            status['error'] = str(e)
            status['all_ready'] = False
        
        return status
    
    def _init_pool(self):
        """初始化数据库连接池"""
        if POOL_AVAILABLE:
            try:
                self.pool = PooledDB(
                    creator=pymysql,
                    maxconnections=self.config['max_connections'],
                    mincached=self.config['min_cached'],
                    maxcached=self.config['max_cached'],
                    blocking=self.config['blocking'],
                    maxusage=self.config['max_usage'],
                    setsession=self.config['set_session'],
                    host=self.config['host'],
                    port=self.config['port'],
                    user=self.config['user'],
                    password=self.config['password'],
                    database=self.config['database'],
                    charset=self.config['charset'],
                    cursorclass=DictCursor
                )
                logger.info(f"数据库连接池初始化成功: {self.config['host']}:{self.config['port']}")
            except Exception as e:
                logger.error(f"连接池初始化失败: {e}")
                self.pool = None
        else:
            logger.info("使用简单连接管理模式")
    
    def _get_simple_connection(self):
        """获取简单连接（无连接池时使用）"""
        return pymysql.connect(
            host=self.config['host'],
            port=self.config['port'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            charset=self.config['charset'],
            cursorclass=DictCursor
        )
    
    @contextmanager
    def get_connection(self) -> Generator:
        """
        获取数据库连接（上下文管理器）
        
        Yields:
            数据库连接对象
        """
        conn = None
        try:
            if self.pool:
                conn = self.pool.connection()
            else:
                conn = self._get_simple_connection()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            self.graduation_stats['total_errors'] += 1
            raise e
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self) -> Generator:
        """
        获取数据库游标（上下文管理器）
        
        Yields:
            数据库游标对象
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
    
    # ==================== 数据验证和清洗 ====================
    
    @staticmethod
    def clean_text(text: str, max_length: int = 5000) -> str:
        """
        清洗文本内容
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ''
        
        # 移除空字符
        text = text.replace('\x00', '')
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 截断长度
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @staticmethod
    def validate_weibo(weibo: Dict) -> Tuple[bool, str]:
        """
        验证微博数据
        
        Args:
            weibo: 微博数据字典
            
        Returns:
            (是否有效, 错误信息)
        """
        required_fields = ['id', 'text']
        
        for field in required_fields:
            if field not in weibo or not weibo[field]:
                return False, f"缺少必要字段: {field}"
        
        # 验证ID（允许数字ID或字符串ID如gen_xxx）
        weibo_id = weibo.get('id')
        if weibo_id is None:
            return False, "缺少微博ID"
        
        # 验证内容长度
        if len(str(weibo.get('text', ''))) < 2:
            return False, "内容过短"
        
        return True, ""
    
    # ==================== 微博数据操作 ====================
    
    @retry_on_error(max_retries=3, delay=1.0)
    def bulk_insert_weibos(self, weibos: List[Dict], batch_id: str = None) -> Dict:
        """
        批量插入微博数据
        
        Args:
            weibos: 微博数据列表
            batch_id: 批次ID
            
        Returns:
            插入结果统计
        """
        if not weibos:
            return {'inserted': 0, 'skipped': 0, 'errors': 0}
        
        sql = """
        INSERT INTO weibo_core_data 
        (weibo_id, content, created_at, crawled_at, user_id, user_name, 
         verified, followers_count, reposts_count, comments_count, attitudes_count,
         has_image, has_video, image_urls, location, topics, source,
         keyword, batch_id, graduation_batch, student_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        reposts_count = VALUES(reposts_count),
        comments_count = VALUES(comments_count),
        attitudes_count = VALUES(attitudes_count),
        update_count = update_count + 1,
        last_updated = NOW()
        """
        
        result = {'inserted': 0, 'skipped': 0, 'errors': 0, 'error_details': []}
        values = []
        
        for weibo in weibos:
            # 验证数据
            is_valid, error_msg = self.validate_weibo(weibo)
            if not is_valid:
                result['skipped'] += 1
                result['error_details'].append({'id': weibo.get('id'), 'error': error_msg})
                continue
            
            try:
                # 提取用户信息
                user = weibo.get('user', {}) or {}
                
                # 处理图片
                pics = weibo.get('pics', []) or []
                image_urls = json.dumps([p.get('url', '') for p in pics if p], ensure_ascii=False) if pics else None
                
                # 处理话题
                topics = weibo.get('topics', [])
                if not topics:
                    # 从内容中提取话题
                    topics = re.findall(r'#([^#]+)#', weibo.get('text', ''))
                topics_json = json.dumps(topics, ensure_ascii=False) if topics else None
                
                # 处理时间
                created_at = weibo.get('created_at')
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
                    except:
                        created_at = datetime.now()
                elif not created_at:
                    created_at = datetime.now()
                
                # 处理ID：纯数字直接用，否则哈希为整数
                raw_id = weibo['id']
                try:
                    weibo_id = int(raw_id)
                except (ValueError, TypeError):
                    weibo_id = abs(hash(str(raw_id))) % (10**18)
                
                raw_user_id = user.get('id', 0)
                try:
                    user_id = int(raw_user_id)
                except (ValueError, TypeError):
                    user_id = abs(hash(str(raw_user_id))) % (10**18)
                
                values.append((
                    weibo_id,
                    self.clean_text(weibo.get('text', ''), 5000),
                    created_at,
                    datetime.now(),
                    user_id,
                    self.clean_text(user.get('screen_name', '未知用户'), 128),
                    1 if user.get('verified') else 0,
                    int(user.get('followers_count', 0)),
                    int(weibo.get('reposts_count', 0)),
                    int(weibo.get('comments_count', 0)),
                    int(weibo.get('attitudes_count', 0)),
                    1 if pics else 0,
                    1 if weibo.get('page_info', {}).get('type') == 'video' else 0,
                    image_urls,
                    self.clean_text(weibo.get('region_name', ''), 128),
                    topics_json,
                    self.clean_text(weibo.get('source', ''), 128),
                    weibo.get('keyword', ''),
                    batch_id or f"batch_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    1,  # graduation_batch
                    '2022407443'  # student_id
                ))
            except Exception as e:
                result['errors'] += 1
                result['error_details'].append({'id': weibo.get('id'), 'error': str(e)})
        
        if not values:
            return result
        
        # 分批插入
        batch_size = 500
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for i in range(0, len(values), batch_size):
                    batch = values[i:i + batch_size]
                    try:
                        cursor.executemany(sql, batch)
                        result['inserted'] += len(batch)
                    except pymysql.Error as e:
                        logger.error(f"批量插入失败: {e}")
                        result['errors'] += len(batch)
                
                conn.commit()
        
        # 更新统计
        self.graduation_stats['total_inserts'] += result['inserted']
        logger.info(f"批量插入完成: 成功 {result['inserted']}, 跳过 {result['skipped']}, 错误 {result['errors']}")
        
        return result
    
    @retry_on_error(max_retries=3, delay=1.0)
    def save_sentiment_results(self, results: List[Dict]) -> Dict:
        """
        保存情感分析结果
        
        Args:
            results: 情感分析结果列表
            
        Returns:
            保存结果统计
        """
        if not results:
            return {'saved': 0, 'errors': 0}
        
        sql = """
        INSERT INTO sentiment_analysis_results 
        (weibo_id, dict_score, bert_score, hybrid_score, 
         sentiment_class, intensity, confidence,
         dict_positive_count, dict_negative_count,
         bert_positive_prob, bert_neutral_prob, bert_negative_prob,
         analysis_method, model_version, analysis_time, processing_time_ms,
         graduation_flag, student_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        dict_score = VALUES(dict_score),
        bert_score = VALUES(bert_score),
        hybrid_score = VALUES(hybrid_score),
        sentiment_class = VALUES(sentiment_class),
        intensity = VALUES(intensity),
        confidence = VALUES(confidence),
        analysis_time = VALUES(analysis_time)
        """
        
        result = {'saved': 0, 'errors': 0}
        values = []
        
        for r in results:
            try:
                # 确定情感分类
                hybrid_score = float(r.get('hybrid_score', r.get('score', 0)))
                if hybrid_score > 0.2:
                    sentiment_class = 'positive'
                elif hybrid_score < -0.2:
                    sentiment_class = 'negative'
                else:
                    sentiment_class = 'neutral'
                
                raw_wid = r['weibo_id']
                try:
                    wid = int(raw_wid)
                except (ValueError, TypeError):
                    wid = abs(hash(str(raw_wid))) % (10**18)
                
                values.append((
                    wid,
                    r.get('dict_score'),
                    r.get('bert_score'),
                    hybrid_score,
                    r.get('sentiment_class', sentiment_class),
                    abs(hybrid_score),  # intensity
                    r.get('confidence', 0.8),
                    r.get('dict_positive_count', 0),
                    r.get('dict_negative_count', 0),
                    r.get('bert_positive_prob'),
                    r.get('bert_neutral_prob'),
                    r.get('bert_negative_prob'),
                    r.get('analysis_method', 'hybrid'),
                    r.get('model_version', 'v1.0.0'),
                    datetime.now(),
                    r.get('processing_time_ms'),
                    1,  # graduation_flag
                    '2022407443'  # student_id
                ))
            except Exception as e:
                logger.error(f"处理情感结果失败: {e}")
                result['errors'] += 1
        
        if values:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(sql, values)
                    result['saved'] = len(values)
                    conn.commit()
            
            # 更新微博处理状态
            weibo_ids = [v[0] for v in values]
            self._update_weibo_processed_status(weibo_ids)
        
        self.graduation_stats['total_inserts'] += result['saved']
        logger.info(f"保存情感分析结果: {result['saved']} 条")
        
        return result
    
    @retry_on_error(max_retries=3, delay=1.0)
    def save_tri_dimension_results(self, results: List[Dict], batch_id: str = None) -> Dict:
        """
        保存三维度排序结果
        
        Args:
            results: 三维度排序结果列表
            batch_id: 批次ID
            
        Returns:
            保存结果统计
        """
        if not results:
            return {'saved': 0, 'errors': 0}
        
        batch_id = batch_id or f"ranking_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        sql = """
        INSERT INTO tri_dimension_ranking 
        (weibo_id, sentiment_score, sentiment_category,
         reposts_count, comments_count, attitudes_count,
         raw_popularity, popularity_score, popularity_class,
         time_decay, alpha_weight, beta_weight, gamma_weight, composite_score,
         ranking_position, batch_id, calculation_time, algorithm_version,
         graduation_flag, student_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        sentiment_score = VALUES(sentiment_score),
        popularity_score = VALUES(popularity_score),
        composite_score = VALUES(composite_score),
        ranking_position = VALUES(ranking_position),
        calculation_time = VALUES(calculation_time)
        """
        
        result = {'saved': 0, 'errors': 0}
        values = []
        
        for idx, r in enumerate(results):
            try:
                sentiment_score = float(r.get('sentiment_score', 0))
                popularity_score = float(r.get('popularity_score', r.get('heat_score', 0)))
                
                # 情感分类
                if sentiment_score >= 0.6:
                    sentiment_category = 'strong_positive'
                elif sentiment_score >= 0.2:
                    sentiment_category = 'positive'
                elif sentiment_score > -0.2:
                    sentiment_category = 'neutral'
                elif sentiment_score > -0.6:
                    sentiment_category = 'negative'
                else:
                    sentiment_category = 'strong_negative'
                
                # 热度分类
                if popularity_score >= 0.7:
                    popularity_class = 'high'
                elif popularity_score >= 0.3:
                    popularity_class = 'medium'
                else:
                    popularity_class = 'low'
                
                # 兼容 id / weibo_id 两种字段名
                raw_wid = r.get('weibo_id', r.get('id'))
                try:
                    wid = int(raw_wid)
                except (ValueError, TypeError):
                    wid = abs(hash(str(raw_wid))) % (10**18)
                
                values.append((
                    wid,
                    sentiment_score,
                    r.get('sentiment_category', sentiment_category),
                    r.get('reposts_count', 0),
                    r.get('comments_count', 0),
                    r.get('attitudes_count', 0),
                    r.get('raw_popularity'),
                    popularity_score,
                    r.get('popularity_class', popularity_class),
                    r.get('time_decay', 1.0),
                    r.get('alpha_weight', 0.4),
                    r.get('beta_weight', 0.4),
                    r.get('gamma_weight', 0.2),
                    float(r.get('composite_score', r.get('tri_score', 0))),
                    r.get('ranking_position', r.get('rank', idx + 1)),
                    batch_id,
                    datetime.now(),
                    r.get('algorithm_version', 'v1.0.0'),
                    1,  # graduation_flag
                    '2022407443'  # student_id
                ))
            except Exception as e:
                logger.error(f"处理排序结果失败: {e}")
                result['errors'] += 1
        
        if values:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(sql, values)
                    result['saved'] = len(values)
                    conn.commit()
            
            # 更新微博排序状态
            weibo_ids = [v[0] for v in values]
            self._update_weibo_ranked_status(weibo_ids)
        
        self.graduation_stats['total_inserts'] += result['saved']
        logger.info(f"保存三维度排序结果: {result['saved']} 条")
        
        return result
    
    def _update_weibo_processed_status(self, weibo_ids: List[int]):
        """更新微博处理状态"""
        if not weibo_ids:
            return
        
        placeholders = ','.join(['%s'] * len(weibo_ids))
        sql = f"UPDATE weibo_core_data SET is_processed = 1 WHERE weibo_id IN ({placeholders})"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, weibo_ids)
                conn.commit()
    
    def _update_weibo_ranked_status(self, weibo_ids: List[int]):
        """更新微博排序状态"""
        if not weibo_ids:
            return
        
        placeholders = ','.join(['%s'] * len(weibo_ids))
        sql = f"UPDATE weibo_core_data SET is_ranked = 1 WHERE weibo_id IN ({placeholders})"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, weibo_ids)
                conn.commit()
    
    # ==================== 爬虫日志操作 ====================
    
    def create_crawl_batch(self, task_name: str, task_type: str, keywords: List[str]) -> str:
        """
        创建爬虫批次
        
        Args:
            task_name: 任务名称
            task_type: 任务类型
            keywords: 关键词列表
            
        Returns:
            批次ID
        """
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(str(keywords).encode()).hexdigest()[:8]}"
        
        sql = """
        INSERT INTO crawl_batch_log 
        (batch_id, task_name, task_type, keywords, start_time, status, graduation_batch, student_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (
                    batch_id,
                    task_name,
                    task_type,
                    json.dumps(keywords, ensure_ascii=False),
                    datetime.now(),
                    'running',
                    1,
                    '2022407443'
                ))
                conn.commit()
        
        logger.info(f"创建爬虫批次: {batch_id}")
        return batch_id
    
    def update_crawl_batch(self, batch_id: str, **kwargs):
        """
        更新爬虫批次
        
        Args:
            batch_id: 批次ID
            **kwargs: 要更新的字段
        """
        if not kwargs:
            return
        
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)
        
        values.append(batch_id)
        
        sql = f"UPDATE crawl_batch_log SET {', '.join(set_clauses)} WHERE batch_id = %s"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                conn.commit()
    
    def complete_crawl_batch(self, batch_id: str, total_weibos: int, 
                            success_count: int, failure_count: int):
        """
        完成爬虫批次
        
        Args:
            batch_id: 批次ID
            total_weibos: 总微博数
            success_count: 成功数
            failure_count: 失败数
        """
        self.update_crawl_batch(
            batch_id,
            status='completed',
            end_time=datetime.now(),
            total_weibos=total_weibos,
            success_count=success_count,
            failure_count=failure_count
        )
        logger.info(f"完成爬虫批次: {batch_id}, 总数: {total_weibos}, 成功: {success_count}")
    
    # ==================== 统计查询 ====================
    
    def get_graduation_statistics(self) -> Dict:
        """
        获取毕业设计统计
        
        Returns:
            统计数据字典
        """
        self.graduation_stats['total_queries'] += 1
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                stats = {}
                
                # 各表数据量
                tables = [
                    'weibo_core_data', 
                    'sentiment_analysis_results', 
                    'tri_dimension_ranking', 
                    'crawl_batch_log'
                ]
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    stats[table] = cursor.fetchone()['count']
                
                # 情感分布
                cursor.execute("""
                    SELECT sentiment_class, COUNT(*) as count
                    FROM sentiment_analysis_results
                    WHERE graduation_flag = 1
                    GROUP BY sentiment_class
                """)
                stats['sentiment_distribution'] = cursor.fetchall()
                
                # 合并运行统计
                stats.update(self.graduation_stats)
                stats['run_time'] = str(datetime.now() - self.graduation_stats['start_time'])
                stats['generated_at'] = datetime.now().isoformat()
                
                return stats
    
    def get_weibo_count(self, graduation_only: bool = True) -> int:
        """获取微博数量"""
        sql = "SELECT COUNT(*) as count FROM weibo_core_data"
        if graduation_only:
            sql += " WHERE graduation_batch = 1"
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchone()['count']
    
    def get_unprocessed_weibos(self, limit: int = 1000, batch_id: str = None) -> List[Dict]:
        """获取未处理的微博"""
        params = []
        sql = """
        SELECT weibo_id, content, user_id, user_name, 
               reposts_count, comments_count, attitudes_count, created_at
        FROM weibo_core_data
        WHERE is_processed = 0 AND graduation_batch = 1
        """
        if batch_id:
            sql += " AND batch_id = %s"
            params.append(batch_id)
        sql += " ORDER BY crawled_at DESC LIMIT %s"
        params.append(limit)
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                return cursor.fetchall()
    
    def get_weibos_by_batch(self, batch_id: str, page: int = 1, page_size: int = 20) -> Dict:
        """按采集批次分页获取微博"""
        page = max(int(page or 1), 1)
        page_size = max(min(int(page_size or 20), 200), 1)
        offset = (page - 1) * page_size
        
        count_sql = """
        SELECT COUNT(*) as count
        FROM weibo_core_data
        WHERE batch_id = %s AND graduation_batch = 1
        """
        data_sql = """
        SELECT weibo_id, content, source, keyword, user_name, user_id,
               reposts_count, comments_count, attitudes_count, created_at, crawled_at
        FROM weibo_core_data
        WHERE batch_id = %s AND graduation_batch = 1
        ORDER BY crawled_at DESC, id DESC
        LIMIT %s OFFSET %s
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(count_sql, (batch_id,))
                total = cursor.fetchone()['count']
                cursor.execute(data_sql, (batch_id, page_size, offset))
                rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append({
                'id': str(row.get('weibo_id')),
                'content': row.get('content', ''),
                'source': row.get('source') or 'weibo',
                'keyword': row.get('keyword') or '',
                'author': row.get('user_name') or '',
                'author_id': str(row.get('user_id') or ''),
                'likes': row.get('attitudes_count') or 0,
                'comments': row.get('comments_count') or 0,
                'shares': row.get('reposts_count') or 0,
                'timestamp': row.get('created_at').isoformat() if row.get('created_at') else None,
                'crawl_time': row.get('crawled_at').isoformat() if row.get('crawled_at') else None,
            })
        
        return {
            'list': items,
            'total': total,
            'page': page,
            'pageSize': page_size,
        }
    
    def get_unranked_weibos(self, limit: int = 1000) -> List[Dict]:
        """获取未排序的微博（已完成情感分析）"""
        sql = """
        SELECT w.weibo_id, w.content, w.reposts_count, w.comments_count, 
               w.attitudes_count, w.created_at, s.hybrid_score, s.sentiment_class
        FROM weibo_core_data w
        JOIN sentiment_analysis_results s ON w.weibo_id = s.weibo_id
        WHERE w.is_ranked = 0 AND w.graduation_batch = 1
        ORDER BY w.crawled_at DESC
        LIMIT %s
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (limit,))
                return cursor.fetchall()
    
    def close(self):
        """关闭数据库服务"""
        if self.pool:
            self.pool.close()
            logger.info("数据库连接池已关闭")


# 单例模式
_db_service_instance = None


def get_db_service(config: Dict = None) -> DatabaseService:
    """
    获取数据库服务单例
    
    Args:
        config: 数据库配置
        
    Returns:
        DatabaseService实例
    """
    global _db_service_instance
    if _db_service_instance is None:
        _db_service_instance = DatabaseService(config)
    return _db_service_instance


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据库服务
    db = DatabaseService()
    
    # 测试连接
    try:
        count = db.get_weibo_count()
        print(f"微博数量: {count}")
        
        stats = db.get_graduation_statistics()
        print(f"统计信息: {json.dumps(stats, ensure_ascii=False, indent=2, default=str)}")
    except Exception as e:
        print(f"测试失败: {e}")
    finally:
        db.close()
