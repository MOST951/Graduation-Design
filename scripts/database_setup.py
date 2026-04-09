#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
微博情感分析系统 - 毕业设计

作者: 罗森
学号: 2022407443
学校: 四川民族学院 智能科学与技术学院 2248班
指导教师: 罗丹

功能:
1. 检查MySQL连接和权限
2. 创建毕业设计专用数据库
3. 创建所有核心表
4. 创建索引和分区
5. 创建视图和存储过程
6. 初始化系统配置数据
7. 创建毕业设计演示数据
"""

import pymysql
import logging
import os
import sys
from datetime import datetime, timedelta
import json
import hashlib
import random
from typing import Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_setup.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self, host: str = 'localhost', port: int = 3306,
                 user: str = 'root', password: str = '123456'):
        """
        初始化数据库连接
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 用户名
            password: 密码
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database_name = 'weibo_sentiment_graduation'
        self.connection = None
        
        # 毕业设计信息
        self.graduation_info = {
            'student_name': '罗森',
            'student_id': '2022407443',
            'advisor': '罗丹',
            'school': '四川民族学院',
            'college': '智能科学与技术学院',
            'class': '2248班',
            'project_title': '基于Spark的分布式微博情感分析系统',
            'year': 2026
        }
        
        # 初始化统计
        self.stats = {
            'tables_created': 0,
            'indexes_created': 0,
            'views_created': 0,
            'procedures_created': 0,
            'demo_data_inserted': 0,
            'errors': []
        }
        
    def connect(self, database: str = None) -> bool:
        """
        连接数据库
        
        Args:
            database: 数据库名称（可选）
            
        Returns:
            是否连接成功
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            logger.info(f"成功连接到MySQL服务器: {self.host}:{self.port}")
            return True
        except pymysql.Error as e:
            logger.error(f"连接数据库失败: {e}")
            self.stats['errors'].append(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("已断开数据库连接")
    
    def check_connection_and_privileges(self) -> Dict:
        """
        检查MySQL连接和权限
        
        Returns:
            检查结果字典
        """
        logger.info("=" * 50)
        logger.info("检查MySQL连接和权限...")
        
        result = {
            'connection': False,
            'version': None,
            'privileges': [],
            'can_create_db': False,
            'can_create_table': False,
            'can_create_procedure': False
        }
        
        if not self.connect():
            return result
        
        result['connection'] = True
        
        try:
            with self.connection.cursor() as cursor:
                # 检查MySQL版本
                cursor.execute("SELECT VERSION() as version")
                result['version'] = cursor.fetchone()['version']
                logger.info(f"MySQL版本: {result['version']}")
                
                # 检查用户权限
                cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
                grants = cursor.fetchall()
                for grant in grants:
                    grant_str = list(grant.values())[0]
                    result['privileges'].append(grant_str)
                    if 'ALL PRIVILEGES' in grant_str or 'CREATE' in grant_str:
                        result['can_create_db'] = True
                        result['can_create_table'] = True
                    if 'ALL PRIVILEGES' in grant_str or 'CREATE ROUTINE' in grant_str:
                        result['can_create_procedure'] = True
                
                logger.info(f"创建数据库权限: {'✓' if result['can_create_db'] else '✗'}")
                logger.info(f"创建表权限: {'✓' if result['can_create_table'] else '✗'}")
                logger.info(f"创建存储过程权限: {'✓' if result['can_create_procedure'] else '✗'}")
                
        except pymysql.Error as e:
            logger.error(f"检查权限失败: {e}")
            self.stats['errors'].append(f"权限检查失败: {e}")
        
        return result
    
    def create_database(self) -> bool:
        """
        创建毕业设计专用数据库
        
        Returns:
            是否创建成功
        """
        logger.info("=" * 50)
        logger.info(f"创建数据库: {self.database_name}")
        
        try:
            with self.connection.cursor() as cursor:
                # 创建数据库
                cursor.execute(f"""
                    CREATE DATABASE IF NOT EXISTS {self.database_name}
                    DEFAULT CHARACTER SET utf8mb4
                    DEFAULT COLLATE utf8mb4_unicode_ci
                """)
                
                # 切换到新数据库
                cursor.execute(f"USE {self.database_name}")
                
                # 设置时区
                cursor.execute("SET time_zone = '+08:00'")
                
                self.connection.commit()
                logger.info(f"数据库 {self.database_name} 创建成功")
                return True
                
        except pymysql.Error as e:
            logger.error(f"创建数据库失败: {e}")
            self.stats['errors'].append(f"创建数据库失败: {e}")
            self.connection.rollback()
            return False
    
    def create_tables(self) -> bool:
        """
        创建所有核心表
        
        Returns:
            是否创建成功
        """
        logger.info("=" * 50)
        logger.info("创建核心数据表...")
        
        tables = self._get_table_definitions()
        
        try:
            with self.connection.cursor() as cursor:
                for table_name, table_sql in tables.items():
                    logger.info(f"创建表: {table_name}")
                    cursor.execute(table_sql)
                    self.stats['tables_created'] += 1
                
                self.connection.commit()
                logger.info(f"成功创建 {self.stats['tables_created']} 个表")
                return True
                
        except pymysql.Error as e:
            logger.error(f"创建表失败: {e}")
            self.stats['errors'].append(f"创建表失败: {e}")
            self.connection.rollback()
            return False
    
    def _get_table_definitions(self) -> Dict[str, str]:
        """获取表定义SQL"""
        
        tables = {}
        
        # 表1: weibo_core_data - 微博核心数据表
        tables['weibo_core_data'] = """
        CREATE TABLE IF NOT EXISTS weibo_core_data (
            weibo_id BIGINT UNSIGNED NOT NULL COMMENT '微博唯一ID',
            mid VARCHAR(32) COMMENT '微博MID',
            bid VARCHAR(32) COMMENT '微博BID',
            content TEXT NOT NULL COMMENT '微博内容',
            content_clean TEXT COMMENT '清洗后内容',
            content_length INT UNSIGNED DEFAULT 0 COMMENT '内容长度',
            created_at DATETIME NOT NULL COMMENT '发布时间',
            crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
            
            user_id BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
            user_name VARCHAR(128) NOT NULL COMMENT '用户昵称',
            user_avatar VARCHAR(512) COMMENT '用户头像',
            verified TINYINT(1) DEFAULT 0 COMMENT '是否认证',
            verified_type INT DEFAULT -1 COMMENT '认证类型',
            verified_reason VARCHAR(256) COMMENT '认证原因',
            followers_count INT UNSIGNED DEFAULT 0 COMMENT '粉丝数',
            friends_count INT UNSIGNED DEFAULT 0 COMMENT '关注数',
            statuses_count INT UNSIGNED DEFAULT 0 COMMENT '微博数',
            influence_score DECIMAL(8,4) DEFAULT 0 COMMENT '影响力分数',
            
            reposts_count INT UNSIGNED DEFAULT 0 COMMENT '转发数',
            comments_count INT UNSIGNED DEFAULT 0 COMMENT '评论数',
            attitudes_count INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
            
            has_image TINYINT(1) DEFAULT 0 COMMENT '是否有图片',
            has_video TINYINT(1) DEFAULT 0 COMMENT '是否有视频',
            image_urls JSON COMMENT '图片URL列表',
            video_url VARCHAR(512) COMMENT '视频URL',
            image_count INT UNSIGNED DEFAULT 0 COMMENT '图片数量',
            
            location VARCHAR(128) COMMENT '地理位置',
            province VARCHAR(32) COMMENT '省份',
            city VARCHAR(32) COMMENT '城市',
            latitude DECIMAL(10,7) COMMENT '纬度',
            longitude DECIMAL(10,7) COMMENT '经度',
            
            topics JSON COMMENT '话题标签列表',
            topic_count INT UNSIGNED DEFAULT 0 COMMENT '话题数量',
            mentions JSON COMMENT '@用户列表',
            mention_count INT UNSIGNED DEFAULT 0 COMMENT '@数量',
            
            source VARCHAR(128) COMMENT '发布来源',
            source_url VARCHAR(256) COMMENT '来源链接',
            is_long_text TINYINT(1) DEFAULT 0 COMMENT '是否长文本',
            is_repost TINYINT(1) DEFAULT 0 COMMENT '是否转发',
            original_weibo_id BIGINT UNSIGNED COMMENT '原微博ID',
            
            crawl_method VARCHAR(32) DEFAULT 'keyword_search' COMMENT '采集方式',
            keyword VARCHAR(128) COMMENT '搜索关键词',
            hot_search_rank INT COMMENT '热搜排名',
            batch_id VARCHAR(64) COMMENT '批次ID',
            crawl_source VARCHAR(64) DEFAULT 'weibo_spider' COMMENT '爬虫来源',
            
            raw_json JSON COMMENT '原始JSON',
            extra_data JSON COMMENT '扩展数据',
            
            student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
            graduation_batch TINYINT(1) DEFAULT 1 COMMENT '毕业设计批次',
            graduation_note VARCHAR(256) COMMENT '毕业设计备注',
            
            is_processed TINYINT(1) DEFAULT 0 COMMENT '是否已处理',
            is_ranked TINYINT(1) DEFAULT 0 COMMENT '是否已排序',
            is_deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
            update_count INT UNSIGNED DEFAULT 0 COMMENT '更新次数',
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新',
            
            PRIMARY KEY (weibo_id),
            KEY idx_created_at (created_at),
            KEY idx_crawled_at (crawled_at),
            KEY idx_user_id (user_id),
            KEY idx_keyword (keyword),
            KEY idx_batch_id (batch_id),
            KEY idx_is_processed (is_processed),
            KEY idx_graduation_batch (graduation_batch),
            KEY idx_keyword_time (keyword, created_at),
            FULLTEXT KEY ft_content (content) WITH PARSER ngram
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='微博核心数据表（毕业设计：罗森 2022407443）'
        """
        
        # 表2: sentiment_analysis_results - 情感分析结果表
        tables['sentiment_analysis_results'] = """
        CREATE TABLE IF NOT EXISTS sentiment_analysis_results (
            id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
            weibo_id BIGINT UNSIGNED NOT NULL COMMENT '微博ID',
            
            dict_score DECIMAL(5,4) COMMENT '词典得分',
            dict_positive_words JSON COMMENT '正面词列表',
            dict_negative_words JSON COMMENT '负面词列表',
            dict_positive_count INT UNSIGNED DEFAULT 0 COMMENT '正面词数',
            dict_negative_count INT UNSIGNED DEFAULT 0 COMMENT '负面词数',
            
            bert_score DECIMAL(5,4) COMMENT 'BERT得分',
            bert_positive_prob DECIMAL(5,4) COMMENT 'BERT正面概率',
            bert_neutral_prob DECIMAL(5,4) COMMENT 'BERT中性概率',
            bert_negative_prob DECIMAL(5,4) COMMENT 'BERT负面概率',
            
            hybrid_score DECIMAL(5,4) NOT NULL COMMENT '混合得分',
            dict_weight DECIMAL(3,2) DEFAULT 0.40 COMMENT '词典权重',
            bert_weight DECIMAL(3,2) DEFAULT 0.60 COMMENT 'BERT权重',
            
            sentiment_class ENUM('positive', 'negative', 'neutral') NOT NULL COMMENT '情感分类',
            intensity DECIMAL(3,2) NOT NULL COMMENT '情感强度',
            confidence DECIMAL(3,2) NOT NULL COMMENT '置信度',
            
            fine_grained_emotion JSON COMMENT '细粒度情感',
            aspect_sentiment JSON COMMENT '方面级情感',
            
            analysis_method VARCHAR(32) DEFAULT 'hybrid' COMMENT '分析方法',
            model_version VARCHAR(50) DEFAULT 'v1.0.0' COMMENT '模型版本',
            dict_version VARCHAR(50) DEFAULT 'hownet_v1' COMMENT '词典版本',
            bert_model_name VARCHAR(100) DEFAULT 'chinese-bert-wwm' COMMENT 'BERT模型',
            
            analysis_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
            processing_time_ms INT UNSIGNED COMMENT '处理耗时',
            
            accuracy_verified TINYINT(1) DEFAULT 0 COMMENT '是否验证',
            verified_label ENUM('positive', 'negative', 'neutral') COMMENT '验证标签',
            verified_by VARCHAR(64) COMMENT '验证人',
            verified_time DATETIME COMMENT '验证时间',
            
            graduation_flag TINYINT(1) DEFAULT 1 COMMENT '毕业设计标记',
            student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
            
            PRIMARY KEY (id),
            UNIQUE KEY uk_weibo_id (weibo_id),
            KEY idx_sentiment_class (sentiment_class),
            KEY idx_hybrid_score (hybrid_score),
            KEY idx_confidence (confidence),
            KEY idx_analysis_time (analysis_time),
            KEY idx_accuracy_verified (accuracy_verified),
            KEY idx_graduation_flag (graduation_flag)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='情感分析结果表（毕业设计：罗森 2022407443）'
        """
        
        # 表3: dual_dimension_ranking - 双维度排序结果表
        tables['dual_dimension_ranking'] = """
        CREATE TABLE IF NOT EXISTS dual_dimension_ranking (
            id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
            weibo_id BIGINT UNSIGNED NOT NULL COMMENT '微博ID',
            
            sentiment_score DECIMAL(5,4) NOT NULL COMMENT '情感得分',
            sentiment_category ENUM('strong_positive', 'positive', 'neutral', 'negative', 'strong_negative') NOT NULL COMMENT '情感分类',
            
            reposts_count INT UNSIGNED DEFAULT 0 COMMENT '转发数',
            comments_count INT UNSIGNED DEFAULT 0 COMMENT '评论数',
            attitudes_count INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
            raw_popularity DECIMAL(12,4) COMMENT '原始热度',
            popularity_score DECIMAL(8,4) NOT NULL COMMENT '热度得分',
            popularity_class ENUM('high', 'medium', 'low') NOT NULL COMMENT '热度分类',
            
            weibo_created_at DATETIME COMMENT '微博发布时间',
            hours_since_post INT UNSIGNED COMMENT '发布后小时数',
            time_decay DECIMAL(3,2) NOT NULL DEFAULT 1.00 COMMENT '时间衰减',
            decay_half_life INT UNSIGNED DEFAULT 24 COMMENT '衰减半衰期',
            
            alpha_weight DECIMAL(3,2) DEFAULT 0.60 COMMENT 'α权重',
            beta_weight DECIMAL(3,2) DEFAULT 0.40 COMMENT 'β权重',
            composite_score DECIMAL(8,4) NOT NULL COMMENT '综合评分',
            
            ranking_position INT UNSIGNED COMMENT '排名位次',
            ranking_percentile DECIMAL(5,2) COMMENT '排名百分位',
            previous_ranking INT UNSIGNED COMMENT '上次排名',
            ranking_change INT COMMENT '排名变化',
            
            weight_params JSON COMMENT '权重参数',
            
            batch_id VARCHAR(64) COMMENT '批次ID',
            calculation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
            algorithm_version VARCHAR(50) DEFAULT 'v1.0.0' COMMENT '算法版本',
            calculation_note TEXT COMMENT '计算备注',
            
            graduation_flag TINYINT(1) DEFAULT 1 COMMENT '毕业设计标记',
            student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
            
            PRIMARY KEY (id),
            UNIQUE KEY uk_weibo_batch (weibo_id, batch_id),
            KEY idx_composite_score (composite_score DESC),
            KEY idx_ranking_position (ranking_position),
            KEY idx_sentiment_score (sentiment_score),
            KEY idx_popularity_score (popularity_score DESC),
            KEY idx_sentiment_category (sentiment_category),
            KEY idx_popularity_class (popularity_class),
            KEY idx_calculation_time (calculation_time),
            KEY idx_batch_id (batch_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='双维度排序结果表（毕业设计核心创新点：罗森 2022407443）'
        """
        
        # 表4: crawl_batch_log - 爬虫批次日志表
        tables['crawl_batch_log'] = """
        CREATE TABLE IF NOT EXISTS crawl_batch_log (
            batch_id VARCHAR(64) NOT NULL COMMENT '批次ID',
            task_name VARCHAR(128) COMMENT '任务名称',
            task_type VARCHAR(32) DEFAULT 'keyword_search' COMMENT '任务类型',
            keywords JSON COMMENT '关键词列表',
            target_count INT UNSIGNED DEFAULT 0 COMMENT '目标数量',
            
            start_time DATETIME NOT NULL COMMENT '开始时间',
            end_time DATETIME COMMENT '结束时间',
            
            total_weibos INT UNSIGNED DEFAULT 0 COMMENT '总微博数',
            success_count INT UNSIGNED DEFAULT 0 COMMENT '成功数',
            failure_count INT UNSIGNED DEFAULT 0 COMMENT '失败数',
            duplicate_count INT UNSIGNED DEFAULT 0 COMMENT '重复数',
            
            total_requests INT UNSIGNED DEFAULT 0 COMMENT '总请求数',
            avg_response_time DECIMAL(8,2) COMMENT '平均响应时间',
            max_response_time INT UNSIGNED COMMENT '最大响应时间',
            min_response_time INT UNSIGNED COMMENT '最小响应时间',
            
            status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') DEFAULT 'pending' COMMENT '状态',
            error_message TEXT COMMENT '错误信息',
            retry_count INT UNSIGNED DEFAULT 0 COMMENT '重试次数',
            
            config JSON COMMENT '任务配置',
            cookies_used INT UNSIGNED DEFAULT 0 COMMENT 'Cookie数量',
            proxies_used INT UNSIGNED DEFAULT 0 COMMENT '代理数量',
            
            graduation_batch TINYINT(1) DEFAULT 1 COMMENT '毕业设计批次',
            student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
            
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            PRIMARY KEY (batch_id),
            KEY idx_status (status),
            KEY idx_task_type (task_type),
            KEY idx_start_time (start_time),
            KEY idx_graduation_batch (graduation_batch)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='爬虫批次日志表（毕业设计：罗森 2022407443）'
        """
        
        # 表5: crawl_request_log - 爬虫请求日志表
        tables['crawl_request_log'] = """
        CREATE TABLE IF NOT EXISTS crawl_request_log (
            request_id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '请求ID',
            batch_id VARCHAR(64) NOT NULL COMMENT '批次ID',
            
            url VARCHAR(1024) NOT NULL COMMENT '请求URL',
            method VARCHAR(10) DEFAULT 'GET' COMMENT '请求方法',
            params JSON COMMENT '请求参数',
            headers JSON COMMENT '请求头',
            
            status_code INT COMMENT 'HTTP状态码',
            response_size INT UNSIGNED COMMENT '响应大小',
            content_type VARCHAR(128) COMMENT '内容类型',
            
            request_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '请求时间',
            response_time INT UNSIGNED COMMENT '响应时间(ms)',
            
            success TINYINT(1) DEFAULT 0 COMMENT '是否成功',
            error_type VARCHAR(64) COMMENT '错误类型',
            error_message TEXT COMMENT '错误信息',
            retry_count INT UNSIGNED DEFAULT 0 COMMENT '重试次数',
            
            cookie_hash VARCHAR(64) COMMENT 'Cookie哈希',
            proxy VARCHAR(128) COMMENT '代理地址',
            user_agent VARCHAR(512) COMMENT 'User-Agent',
            
            weibos_extracted INT UNSIGNED DEFAULT 0 COMMENT '提取微博数',
            
            PRIMARY KEY (request_id),
            KEY idx_batch_id (batch_id),
            KEY idx_request_time (request_time),
            KEY idx_status_code (status_code),
            KEY idx_success (success)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='爬虫请求日志表（毕业设计：罗森 2022407443）'
        """
        
        # 表6: data_quality_log - 数据质量日志表
        tables['data_quality_log'] = """
        CREATE TABLE IF NOT EXISTS data_quality_log (
            check_id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '检查ID',
            batch_id VARCHAR(64) COMMENT '批次ID',
            
            check_type VARCHAR(32) DEFAULT 'batch' COMMENT '检查类型',
            check_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
            data_count INT UNSIGNED DEFAULT 0 COMMENT '检查数据量',
            
            completeness_score DECIMAL(3,2) COMMENT '完整性得分',
            accuracy_score DECIMAL(3,2) COMMENT '准确性得分',
            consistency_score DECIMAL(3,2) COMMENT '一致性得分',
            timeliness_score DECIMAL(3,2) COMMENT '及时性得分',
            uniqueness_score DECIMAL(3,2) COMMENT '唯一性得分',
            validity_score DECIMAL(3,2) COMMENT '有效性得分',
            overall_score DECIMAL(3,2) COMMENT '综合得分',
            
            issues JSON COMMENT '问题详情',
            issue_count INT UNSIGNED DEFAULT 0 COMMENT '问题数量',
            critical_issues INT UNSIGNED DEFAULT 0 COMMENT '严重问题数',
            
            recommendations JSON COMMENT '改进建议',
            note TEXT COMMENT '备注',
            
            graduation_check TINYINT(1) DEFAULT 1 COMMENT '毕业设计检查',
            student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
            
            PRIMARY KEY (check_id),
            KEY idx_batch_id (batch_id),
            KEY idx_check_time (check_time),
            KEY idx_overall_score (overall_score)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='数据质量日志表（毕业设计：罗森 2022407443）'
        """
        
        # 表7: system_configs - 系统配置表
        tables['system_configs'] = """
        CREATE TABLE IF NOT EXISTS system_configs (
            id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
            config_key VARCHAR(128) NOT NULL COMMENT '配置键',
            config_value TEXT NOT NULL COMMENT '配置值',
            config_type VARCHAR(32) DEFAULT 'string' COMMENT '值类型',
            category VARCHAR(64) DEFAULT 'general' COMMENT '配置分类',
            description VARCHAR(512) COMMENT '配置描述',
            is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
            is_system TINYINT(1) DEFAULT 0 COMMENT '是否系统配置',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            updated_by VARCHAR(64) COMMENT '更新人',
            UNIQUE KEY uk_config_key (config_key),
            KEY idx_category (category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='系统配置表（毕业设计：罗森 2022407443）'
        """
        
        # 表8: graduation_statistics - 毕业设计统计表
        tables['graduation_statistics'] = """
        CREATE TABLE IF NOT EXISTS graduation_statistics (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
            stat_id VARCHAR(64) NOT NULL COMMENT '统计ID',
            stat_type VARCHAR(64) NOT NULL COMMENT '统计类型',
            dimension VARCHAR(64) COMMENT '统计维度',
            dimension_value VARCHAR(256) COMMENT '维度值',
            stat_data JSON NOT NULL COMMENT '统计数据',
            total_count BIGINT UNSIGNED DEFAULT 0 COMMENT '总数',
            positive_count BIGINT UNSIGNED DEFAULT 0 COMMENT '正面数',
            negative_count BIGINT UNSIGNED DEFAULT 0 COMMENT '负面数',
            neutral_count BIGINT UNSIGNED DEFAULT 0 COMMENT '中性数',
            avg_score DECIMAL(8,4) COMMENT '平均分数',
            stat_date DATE COMMENT '统计日期',
            start_time DATETIME COMMENT '开始时间',
            end_time DATETIME COMMENT '结束时间',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            note TEXT COMMENT '备注',
            UNIQUE KEY uk_stat_id (stat_id),
            KEY idx_stat_type (stat_type),
            KEY idx_stat_date (stat_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='毕业设计统计表（毕业设计：罗森 2022407443）'
        """
        
        return tables
    
    def create_indexes(self) -> bool:
        """
        创建额外索引
        
        Returns:
            是否创建成功
        """
        logger.info("=" * 50)
        logger.info("创建额外索引...")
        
        indexes = [
            # 复合索引优化
            ("weibo_core_data", "idx_user_time", "(user_id, created_at)"),
            ("weibo_core_data", "idx_batch_status", "(batch_id, is_processed)"),
            ("sentiment_analysis_results", "idx_class_confidence", "(sentiment_class, confidence DESC)"),
            ("dual_dimension_ranking", "idx_batch_ranking", "(batch_id, ranking_position)"),
            ("dual_dimension_ranking", "idx_class_score", "(sentiment_category, composite_score DESC)"),
        ]
        
        try:
            with self.connection.cursor() as cursor:
                for table, index_name, columns in indexes:
                    try:
                        cursor.execute(f"CREATE INDEX {index_name} ON {table} {columns}")
                        self.stats['indexes_created'] += 1
                        logger.info(f"创建索引: {table}.{index_name}")
                    except pymysql.Error as e:
                        if 'Duplicate key name' in str(e):
                            logger.info(f"索引已存在: {table}.{index_name}")
                        else:
                            raise
                
                self.connection.commit()
                logger.info(f"成功创建 {self.stats['indexes_created']} 个索引")
                return True
                
        except pymysql.Error as e:
            logger.error(f"创建索引失败: {e}")
            self.stats['errors'].append(f"创建索引失败: {e}")
            self.connection.rollback()
            return False
    
    def create_views(self) -> bool:
        """
        创建视图
        
        Returns:
            是否创建成功
        """
        logger.info("=" * 50)
        logger.info("创建视图...")
        
        views = {
            'v_sentiment_distribution': """
                CREATE OR REPLACE VIEW v_sentiment_distribution AS
                SELECT 
                    sentiment_class,
                    COUNT(*) AS count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM sentiment_analysis_results), 2) AS percentage,
                    ROUND(AVG(hybrid_score), 4) AS avg_score,
                    ROUND(AVG(confidence), 4) AS avg_confidence
                FROM sentiment_analysis_results
                WHERE graduation_flag = 1
                GROUP BY sentiment_class
            """,
            
            'v_top100_weibos': """
                CREATE OR REPLACE VIEW v_top100_weibos AS
                SELECT 
                    d.ranking_position,
                    d.weibo_id,
                    w.content,
                    w.user_name,
                    d.sentiment_score,
                    d.sentiment_category,
                    d.popularity_score,
                    d.popularity_class,
                    d.composite_score,
                    w.reposts_count,
                    w.comments_count,
                    w.attitudes_count,
                    w.created_at
                FROM dual_dimension_ranking d
                JOIN weibo_core_data w ON d.weibo_id = w.weibo_id
                WHERE d.graduation_flag = 1
                ORDER BY d.composite_score DESC
                LIMIT 100
            """,
            
            'v_crawl_performance': """
                CREATE OR REPLACE VIEW v_crawl_performance AS
                SELECT 
                    batch_id,
                    task_name,
                    task_type,
                    status,
                    total_weibos,
                    success_count,
                    failure_count,
                    ROUND(success_count * 100.0 / NULLIF(total_weibos, 0), 2) AS success_rate,
                    avg_response_time,
                    TIMESTAMPDIFF(SECOND, start_time, COALESCE(end_time, NOW())) AS duration_seconds,
                    start_time,
                    end_time
                FROM crawl_batch_log
                WHERE graduation_batch = 1
                ORDER BY start_time DESC
            """,
            
            'v_graduation_summary': """
                CREATE OR REPLACE VIEW v_graduation_summary AS
                SELECT 
                    '罗森' AS student_name,
                    '2022407443' AS student_id,
                    '四川民族学院' AS school,
                    '智能科学与技术学院' AS college,
                    '2248班' AS class_name,
                    '罗丹' AS advisor,
                    (SELECT COUNT(*) FROM weibo_core_data WHERE graduation_batch = 1) AS total_weibos,
                    (SELECT COUNT(DISTINCT user_id) FROM weibo_core_data WHERE graduation_batch = 1) AS total_users,
                    (SELECT COUNT(*) FROM sentiment_analysis_results WHERE graduation_flag = 1) AS analyzed_count,
                    (SELECT COUNT(*) FROM dual_dimension_ranking WHERE graduation_flag = 1) AS ranked_count,
                    (SELECT COUNT(*) FROM crawl_batch_log WHERE graduation_batch = 1) AS total_batches,
                    NOW() AS generated_at
            """
        }
        
        try:
            with self.connection.cursor() as cursor:
                for view_name, view_sql in views.items():
                    logger.info(f"创建视图: {view_name}")
                    cursor.execute(view_sql)
                    self.stats['views_created'] += 1
                
                self.connection.commit()
                logger.info(f"成功创建 {self.stats['views_created']} 个视图")
                return True
                
        except pymysql.Error as e:
            logger.error(f"创建视图失败: {e}")
            self.stats['errors'].append(f"创建视图失败: {e}")
            self.connection.rollback()
            return False
    
    def create_stored_procedures(self) -> bool:
        """
        创建存储过程
        
        Returns:
            是否创建成功
        """
        logger.info("=" * 50)
        logger.info("创建存储过程...")
        
        procedures = {
            'sp_calculate_rankings': """
                CREATE PROCEDURE sp_calculate_rankings(IN p_batch_id VARCHAR(64))
                BEGIN
                    SET @rank := 0;
                    UPDATE dual_dimension_ranking 
                    SET ranking_position = (@rank := @rank + 1)
                    WHERE (p_batch_id IS NULL OR batch_id = p_batch_id)
                    ORDER BY composite_score DESC;
                    SELECT CONCAT('排名计算完成，批次: ', COALESCE(p_batch_id, '全部')) AS result;
                END
            """,
            
            'sp_graduation_statistics': """
                CREATE PROCEDURE sp_graduation_statistics()
                BEGIN
                    SELECT * FROM v_graduation_summary;
                    SELECT * FROM v_sentiment_distribution;
                    SELECT * FROM v_crawl_performance LIMIT 10;
                END
            """
        }
        
        try:
            with self.connection.cursor() as cursor:
                for proc_name, proc_sql in procedures.items():
                    try:
                        cursor.execute(f"DROP PROCEDURE IF EXISTS {proc_name}")
                        cursor.execute(proc_sql)
                        self.stats['procedures_created'] += 1
                        logger.info(f"创建存储过程: {proc_name}")
                    except pymysql.Error as e:
                        logger.warning(f"创建存储过程 {proc_name} 失败: {e}")
                
                self.connection.commit()
                logger.info(f"成功创建 {self.stats['procedures_created']} 个存储过程")
                return True
                
        except pymysql.Error as e:
            logger.error(f"创建存储过程失败: {e}")
            self.stats['errors'].append(f"创建存储过程失败: {e}")
            self.connection.rollback()
            return False
    
    def initialize_system_configs(self) -> bool:
        """
        初始化系统配置数据
        
        Returns:
            是否初始化成功
        """
        logger.info("=" * 50)
        logger.info("初始化系统配置...")
        
        configs = [
            ('sentiment.lexicon_weight', '0.40', 'number', 'sentiment', '词典分析权重'),
            ('sentiment.bert_weight', '0.60', 'number', 'sentiment', 'BERT分析权重'),
            ('dual_dimension.sentiment_weight', '0.60', 'number', 'ranking', '双维度排序-情感权重'),
            ('dual_dimension.popularity_weight', '0.40', 'number', 'ranking', '双维度排序-热度权重'),
            ('crawler.request_interval', '2', 'number', 'crawler', '爬虫请求间隔（秒）'),
            ('crawler.max_retry', '3', 'number', 'crawler', '爬虫最大重试次数'),
            ('system.timezone', 'Asia/Shanghai', 'string', 'system', '系统时区'),
            ('graduation.student_name', '罗森', 'string', 'graduation', '学生姓名'),
            ('graduation.student_id', '2022407443', 'string', 'graduation', '学生学号'),
            ('graduation.advisor', '罗丹', 'string', 'graduation', '指导教师'),
            ('graduation.school', '四川民族学院', 'string', 'graduation', '学校'),
            ('graduation.college', '智能科学与技术学院', 'string', 'graduation', '学院'),
            ('graduation.class', '2248班', 'string', 'graduation', '班级'),
            ('graduation.project_title', '基于Spark的分布式微博情感分析系统', 'string', 'graduation', '项目名称'),
        ]
        
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    INSERT INTO system_configs 
                    (config_key, config_value, config_type, category, description, is_system)
                    VALUES (%s, %s, %s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE 
                    config_value = VALUES(config_value),
                    updated_at = NOW()
                """
                
                for config in configs:
                    cursor.execute(sql, config)
                
                self.connection.commit()
                logger.info(f"初始化 {len(configs)} 条系统配置")
                return True
                
        except pymysql.Error as e:
            logger.error(f"初始化系统配置失败: {e}")
            self.stats['errors'].append(f"初始化配置失败: {e}")
            self.connection.rollback()
            return False
    
    def initialize_graduation_data(self) -> bool:
        """
        初始化毕业设计演示数据
        
        Returns:
            是否初始化成功
        """
        logger.info("=" * 50)
        logger.info("初始化毕业设计演示数据...")
        
        try:
            with self.connection.cursor() as cursor:
                # 创建演示批次
                batch_id = f"graduation_demo_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                cursor.execute("""
                    INSERT INTO crawl_batch_log 
                    (batch_id, task_name, task_type, keywords, start_time, status, graduation_batch)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    batch_id,
                    '毕业设计演示数据采集',
                    'keyword_search',
                    json.dumps(['微博', '情感分析', '毕业设计'], ensure_ascii=False),
                    datetime.now(),
                    'completed',
                    1
                ))
                
                # 生成演示微博数据
                demo_weibos = self._generate_demo_weibos(batch_id, count=100)
                
                weibo_sql = """
                    INSERT INTO weibo_core_data 
                    (weibo_id, content, created_at, user_id, user_name, 
                     reposts_count, comments_count, attitudes_count,
                     keyword, batch_id, graduation_batch, student_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.executemany(weibo_sql, demo_weibos)
                self.stats['demo_data_inserted'] += len(demo_weibos)
                
                # 更新批次统计
                cursor.execute("""
                    UPDATE crawl_batch_log 
                    SET total_weibos = %s, success_count = %s, end_time = NOW()
                    WHERE batch_id = %s
                """, (len(demo_weibos), len(demo_weibos), batch_id))
                
                self.connection.commit()
                logger.info(f"初始化 {len(demo_weibos)} 条演示微博数据")
                return True
                
        except pymysql.Error as e:
            logger.error(f"初始化演示数据失败: {e}")
            self.stats['errors'].append(f"初始化演示数据失败: {e}")
            self.connection.rollback()
            return False
    
    def _generate_demo_weibos(self, batch_id: str, count: int = 100) -> List[Tuple]:
        """
        生成演示微博数据
        
        Args:
            batch_id: 批次ID
            count: 生成数量
            
        Returns:
            微博数据列表
        """
        demo_contents = [
            "今天天气真好，心情也很愉快！#美好生活#",
            "这个产品质量太差了，非常失望",
            "刚看完这部电影，剧情一般般吧",
            "恭喜中国队获得冠军！太棒了！",
            "又堵车了，每天上班都这样，烦死了",
            "新买的手机很好用，推荐大家购买",
            "今天的会议内容很重要，需要认真学习",
            "这家餐厅的菜太难吃了，再也不来了",
            "周末去爬山，风景很美，空气清新",
            "股市又跌了，心情很郁闷",
            "孩子考试得了第一名，太开心了！",
            "这个政策对我们老百姓很有帮助",
            "快递又延迟了，物流真是太慢了",
            "今天学到了很多新知识，收获满满",
            "这个游戏太好玩了，根本停不下来",
        ]
        
        demo_users = [
            (1001, "阳光小明"),
            (1002, "快乐小红"),
            (1003, "淡定小刚"),
            (1004, "热情小丽"),
            (1005, "理性小华"),
        ]
        
        keywords = ['微博', '情感分析', '毕业设计', '大数据', 'Spark']
        
        weibos = []
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(count):
            weibo_id = 5000000000000000 + i
            content = random.choice(demo_contents)
            created_at = base_time + timedelta(hours=random.randint(0, 168))
            user_id, user_name = random.choice(demo_users)
            reposts = random.randint(0, 1000)
            comments = random.randint(0, 500)
            attitudes = random.randint(0, 2000)
            keyword = random.choice(keywords)
            
            weibos.append((
                weibo_id, content, created_at, user_id, user_name,
                reposts, comments, attitudes, keyword, batch_id, 1, '2022407443'
            ))
        
        return weibos
    
    def run_full_setup(self) -> Dict:
        """
        运行完整初始化
        
        Returns:
            初始化结果
        """
        logger.info("=" * 60)
        logger.info("开始数据库完整初始化")
        logger.info(f"学生: {self.graduation_info['student_name']}")
        logger.info(f"学号: {self.graduation_info['student_id']}")
        logger.info(f"学校: {self.graduation_info['school']}")
        logger.info(f"指导教师: {self.graduation_info['advisor']}")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. 检查连接和权限
        check_result = self.check_connection_and_privileges()
        if not check_result['connection']:
            return {'success': False, 'error': '无法连接数据库', 'stats': self.stats}
        
        # 2. 创建数据库
        if not self.create_database():
            return {'success': False, 'error': '创建数据库失败', 'stats': self.stats}
        
        # 重新连接到新数据库
        self.disconnect()
        if not self.connect(self.database_name):
            return {'success': False, 'error': '连接新数据库失败', 'stats': self.stats}
        
        # 3. 创建表
        if not self.create_tables():
            return {'success': False, 'error': '创建表失败', 'stats': self.stats}
        
        # 4. 创建索引
        self.create_indexes()
        
        # 5. 创建视图
        self.create_views()
        
        # 6. 创建存储过程
        self.create_stored_procedures()
        
        # 7. 初始化系统配置
        self.initialize_system_configs()
        
        # 8. 初始化演示数据
        self.initialize_graduation_data()
        
        # 断开连接
        self.disconnect()
        
        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()
        
        # 生成报告
        result = {
            'success': len(self.stats['errors']) == 0,
            'database': self.database_name,
            'duration_seconds': duration,
            'stats': self.stats,
            'graduation_info': self.graduation_info,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("=" * 60)
        logger.info("数据库初始化完成")
        logger.info(f"创建表: {self.stats['tables_created']} 个")
        logger.info(f"创建索引: {self.stats['indexes_created']} 个")
        logger.info(f"创建视图: {self.stats['views_created']} 个")
        logger.info(f"创建存储过程: {self.stats['procedures_created']} 个")
        logger.info(f"演示数据: {self.stats['demo_data_inserted']} 条")
        logger.info(f"耗时: {duration:.2f} 秒")
        if self.stats['errors']:
            logger.warning(f"错误: {len(self.stats['errors'])} 个")
            for err in self.stats['errors']:
                logger.warning(f"  - {err}")
        logger.info("=" * 60)
        
        return result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='微博情感分析系统数据库初始化')
    parser.add_argument('--host', default='localhost', help='数据库主机')
    parser.add_argument('--port', type=int, default=3306, help='数据库端口')
    parser.add_argument('--user', default='root', help='数据库用户')
    parser.add_argument('--password', default='123456', help='数据库密码')
    
    args = parser.parse_args()
    
    initializer = DatabaseInitializer(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password
    )
    
    result = initializer.run_full_setup()
    
    if result['success']:
        print("\n✓ 数据库初始化成功！")
        print(f"  数据库: {result['database']}")
        print(f"  耗时: {result['duration_seconds']:.2f} 秒")
    else:
        print("\n✗ 数据库初始化失败！")
        print(f"  错误: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
