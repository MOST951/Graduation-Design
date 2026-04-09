-- ===================================================================
-- 数据存储系统 - 数据库表结构
-- ===================================================================

USE weibo_prod;

-- 1. 采集任务表 (增强版)
CREATE TABLE IF NOT EXISTS collection_tasks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress DECIMAL(5,2) DEFAULT 0.00,
    params JSON,
    result_count BIGINT DEFAULT 0,
    error_message TEXT,
    checkpoint JSON,
    priority INT DEFAULT 5,
    created_by BIGINT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 模型元数据表
CREATE TABLE IF NOT EXISTS model_metadata (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id VARCHAR(64) NOT NULL UNIQUE,
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(50),
    path VARCHAR(500),
    config JSON,
    metrics JSON,
    status VARCHAR(20) DEFAULT 'active',
    is_default BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_model_type (model_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(10) NOT NULL,
    module VARCHAR(100),
    message TEXT NOT NULL,
    details JSON,
    user_id BIGINT,
    ip_address VARCHAR(45),
    execution_time INT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_level (level),
    INDEX idx_module (module),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 用户配置表
CREATE TABLE IF NOT EXISTS user_configs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT,
    config_type VARCHAR(20) DEFAULT 'string',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_config (user_id, config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 数据集元数据表
CREATE TABLE IF NOT EXISTS dataset_metadata (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    storage_type VARCHAR(20) NOT NULL,
    storage_path VARCHAR(500),
    record_count BIGINT,
    file_size BIGINT,
    schema_info JSON,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 热点话题表
CREATE TABLE IF NOT EXISTS hot_topics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    hot_value BIGINT DEFAULT 0,
    rank_position INT,
    weibo_count BIGINT DEFAULT 0,
    positive_ratio DECIMAL(5,4),
    negative_ratio DECIMAL(5,4),
    neutral_ratio DECIMAL(5,4),
    hourly_trend JSON,
    crawl_time DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_topic (topic),
    INDEX idx_crawl_time (crawl_time),
    INDEX idx_hot_value (hot_value DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 用户画像表
CREATE TABLE IF NOT EXISTS user_profiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    weibo_user_id VARCHAR(64) NOT NULL UNIQUE,
    screen_name VARCHAR(100),
    description TEXT,
    location VARCHAR(100),
    verified BOOLEAN DEFAULT FALSE,
    followers_count BIGINT DEFAULT 0,
    friends_count BIGINT DEFAULT 0,
    statuses_count BIGINT DEFAULT 0,
    influence_score DECIMAL(10,4),
    activity_score DECIMAL(10,4),
    sentiment_avg DECIMAL(5,4),
    interest_tags JSON,
    last_crawl_time DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_screen_name (screen_name),
    INDEX idx_influence (influence_score DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 微博数据表 (用于小规模存储)
CREATE TABLE IF NOT EXISTS weibo_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    weibo_id VARCHAR(64) NOT NULL UNIQUE,
    mid VARCHAR(64),
    text TEXT NOT NULL,
    cleaned_text TEXT,
    source VARCHAR(100),
    created_at_weibo DATETIME,
    user_id VARCHAR(64),
    user_name VARCHAR(100),
    reposts_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    attitudes_count INT DEFAULT 0,
    sentiment_label VARCHAR(20),
    sentiment_score DECIMAL(5,4),
    keyword VARCHAR(255),
    topic VARCHAR(255),
    content_hash VARCHAR(64),
    crawl_time DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_weibo_id (weibo_id),
    INDEX idx_user_id (user_id),
    INDEX idx_keyword (keyword),
    INDEX idx_sentiment (sentiment_label),
    INDEX idx_crawl_time (crawl_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
