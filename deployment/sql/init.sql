-- ===================================================================
-- Weibo Sentiment Analysis Platform - Database Initialization Script
-- ===================================================================

-- ---------------------------------
-- 1. Database and User Creation
-- ---------------------------------
CREATE DATABASE IF NOT EXISTS weibo_prod
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER 'prod_user'@'localhost' IDENTIFIED BY 'your_secure_password';

GRANT ALL PRIVILEGES ON weibo_prod.* TO 'prod_user'@'localhost';

FLUSH PRIVILEGES;

USE weibo_prod;

-- ---------------------------------
-- 2. Table Creation
-- ---------------------------------

-- Users Table
CREATE TABLE IF NOT EXISTS users (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  email VARCHAR(100) UNIQUE,
  roles VARCHAR(255) NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Collection Task Table
CREATE TABLE IF NOT EXISTS collection_task (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  task_name VARCHAR(255) NOT NULL,
  keywords TEXT NOT NULL,
  status VARCHAR(20) NOT NULL,
  start_time DATETIME,
  end_time DATETIME,
  user_id BIGINT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sentiment Result Table
CREATE TABLE IF NOT EXISTS sentiment_result (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  task_id BIGINT,
  weibo_id VARCHAR(50) NOT NULL UNIQUE,
  content TEXT,
  sentiment VARCHAR(20),
  confidence DOUBLE,
  publish_time DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (task_id) REFERENCES collection_task(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Spark Jobs Table
CREATE TABLE IF NOT EXISTS spark_jobs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_id VARCHAR(255) NOT NULL UNIQUE,
  job_name VARCHAR(255) NOT NULL,
  status VARCHAR(255) NOT NULL,
  submit_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finish_time DATETIME,
  arguments TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- System Log Table
CREATE TABLE IF NOT EXISTS system_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50),
  operation VARCHAR(255),
  method VARCHAR(255),
  params TEXT,
  execution_time BIGINT,
  ip_address VARCHAR(50),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------
-- 3. Core Data Tables (Python Backend)
-- ---------------------------------

-- 微博核心数据表
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
    `is_ranked` TINYINT DEFAULT 0 COMMENT '是否已双维度排序',
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
COMMENT='微博核心数据表 - 毕业设计';

-- 情感分析结果表
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
COMMENT='情感分析结果表 - 毕业设计';

-- 双维度排序结果表
CREATE TABLE IF NOT EXISTS `dual_dimension_ranking` (
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
    `time_decay` DECIMAL(5,4) DEFAULT 1 COMMENT '时间衰减因子γ(t)',
    `alpha_weight` DECIMAL(3,2) DEFAULT 0.40 COMMENT '情感权重ω₁',
    `beta_weight` DECIMAL(3,2) DEFAULT 0.40 COMMENT '热度权重ω₂',
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
COMMENT='双维度排序结果表 - 毕业设计核心创新点';

-- 爬虫批次日志表
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
COMMENT='爬虫批次日志表';

-- 爬虫请求日志表
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
COMMENT='爬虫请求日志表';

-- 数据质量日志表
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
COMMENT='数据质量日志表';

-- 系统配置表
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
COMMENT='系统配置表';

-- ---------------------------------
-- 4. Initial Data Insertion
-- ---------------------------------

-- Insert a default admin user
-- IMPORTANT: The password 'admin' is insecure. Change it immediately after first login.
-- The password here is hashed using BCrypt. You should generate a new hash for your password.
INSERT INTO users (username, password, email, roles, status) 
VALUES ('admin', '$2a$10$G.A.sV4.gY3.x2.jK8l/..sY.Z.f8.j/2.G/g.Z/g.G/g.Z/g.G', 'admin@example.com', 'ROLE_ADMIN,ROLE_USER', 'ACTIVE');
