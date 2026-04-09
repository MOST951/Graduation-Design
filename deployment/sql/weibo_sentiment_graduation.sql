-- ============================================================================
-- 微博情感分析系统 - 毕业设计数据库架构
-- 数据库名称: weibo_sentiment_graduation
-- 创建日期: 2026-01-28
-- 作者: 毕业设计项目
-- 描述: 基于Spark的分布式微博情感分析系统完整数据库架构
-- ============================================================================

-- ============================================================================
-- 第一部分：数据库创建
-- ============================================================================

-- 删除已存在的数据库（谨慎使用）
-- DROP DATABASE IF EXISTS weibo_sentiment_graduation;

-- 创建数据库
CREATE DATABASE IF NOT EXISTS weibo_sentiment_graduation
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE weibo_sentiment_graduation;

-- 设置时区
SET time_zone = '+08:00';

-- ============================================================================
-- 第二部分：原始数据层 (raw_data) - 存储爬虫采集的原始数据
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 表1: weibo_raw - 原始微博数据表
-- 描述: 存储从微博平台爬取的原始微博内容
-- 分区策略: 按月分区，便于历史数据管理
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weibo_raw (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博唯一ID（来自微博平台）',
    mid VARCHAR(64) COMMENT '微博MID',
    bid VARCHAR(64) COMMENT '微博BID（短链接ID）',
    
    -- 内容相关
    content TEXT NOT NULL COMMENT '微博原始内容（含HTML标签）',
    content_length INT UNSIGNED DEFAULT 0 COMMENT '内容长度',
    pics JSON COMMENT '图片URL列表',
    video_url VARCHAR(512) COMMENT '视频URL',
    has_video TINYINT(1) DEFAULT 0 COMMENT '是否包含视频',
    is_long_text TINYINT(1) DEFAULT 0 COMMENT '是否为长文本',
    
    -- 用户相关
    user_id VARCHAR(64) NOT NULL COMMENT '发布用户ID',
    screen_name VARCHAR(128) COMMENT '用户昵称',
    
    -- 互动数据
    reposts_count INT UNSIGNED DEFAULT 0 COMMENT '转发数',
    comments_count INT UNSIGNED DEFAULT 0 COMMENT '评论数',
    attitudes_count INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
    
    -- 来源信息
    source VARCHAR(256) COMMENT '发布来源（如：iPhone客户端）',
    region_name VARCHAR(128) COMMENT '发布地区',
    
    -- 时间信息
    created_at DATETIME NOT NULL COMMENT '微博发布时间',
    crawl_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬取时间',
    
    -- 关联信息
    topic VARCHAR(256) COMMENT '关联话题（#话题#）',
    keyword VARCHAR(128) COMMENT '搜索关键词',
    hot_search_rank INT COMMENT '热搜排名（如果来自热搜）',
    
    -- 元数据
    raw_json JSON COMMENT '原始JSON数据（完整保留）',
    data_source ENUM('search', 'hot_search', 'topic', 'user', 'realtime') DEFAULT 'search' COMMENT '数据来源类型',
    
    -- 状态标记
    is_processed TINYINT(1) DEFAULT 0 COMMENT '是否已处理',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）',
    
    -- 索引和约束
    PRIMARY KEY (id, crawl_time),
    UNIQUE KEY uk_weibo_id (weibo_id),
    KEY idx_user_id (user_id),
    KEY idx_created_at (created_at),
    KEY idx_crawl_time (crawl_time),
    KEY idx_keyword (keyword),
    KEY idx_topic (topic(64)),
    KEY idx_is_processed (is_processed),
    KEY idx_data_source (data_source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='原始微博数据表'
PARTITION BY RANGE (TO_DAYS(crawl_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- -----------------------------------------------------------------------------
-- 表2: user_raw - 原始用户数据表
-- 描述: 存储微博用户的基本信息
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_raw (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    
    -- 基本信息
    screen_name VARCHAR(128) NOT NULL COMMENT '用户昵称',
    profile_url VARCHAR(512) COMMENT '用户主页URL',
    avatar_hd VARCHAR(512) COMMENT '高清头像URL',
    description TEXT COMMENT '用户简介',
    
    -- 认证信息
    verified TINYINT(1) DEFAULT 0 COMMENT '是否认证',
    verified_type INT DEFAULT -1 COMMENT '认证类型（-1:未认证, 0:个人, 1:企业, 2:媒体, 3:政府）',
    verified_reason VARCHAR(512) COMMENT '认证原因',
    
    -- 统计数据
    followers_count INT UNSIGNED DEFAULT 0 COMMENT '粉丝数',
    friends_count INT UNSIGNED DEFAULT 0 COMMENT '关注数',
    statuses_count INT UNSIGNED DEFAULT 0 COMMENT '微博数',
    
    -- 地理信息
    location VARCHAR(128) COMMENT '所在地',
    province_code INT COMMENT '省份代码',
    city_code INT COMMENT '城市代码',
    
    -- 其他信息
    gender ENUM('m', 'f', 'n') DEFAULT 'n' COMMENT '性别（m:男, f:女, n:未知）',
    mbrank INT DEFAULT 0 COMMENT '会员等级',
    urank INT DEFAULT 0 COMMENT '用户等级',
    
    -- 时间信息
    created_at DATETIME COMMENT '用户注册时间',
    first_crawl_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次爬取时间',
    last_crawl_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后爬取时间',
    
    -- 元数据
    raw_json JSON COMMENT '原始JSON数据',
    
    -- 索引和约束
    UNIQUE KEY uk_user_id (user_id),
    KEY idx_screen_name (screen_name),
    KEY idx_verified (verified),
    KEY idx_followers_count (followers_count),
    KEY idx_location (location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='原始用户数据表';

-- -----------------------------------------------------------------------------
-- 表3: interaction_raw - 原始互动数据表
-- 描述: 存储微博的评论、转发等互动数据
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interaction_raw (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    interaction_id VARCHAR(64) NOT NULL COMMENT '互动ID',
    weibo_id VARCHAR(64) NOT NULL COMMENT '关联微博ID',
    
    -- 互动类型
    interaction_type ENUM('comment', 'repost', 'like') NOT NULL COMMENT '互动类型',
    
    -- 内容
    content TEXT COMMENT '互动内容（评论/转发文本）',
    
    -- 用户信息
    user_id VARCHAR(64) NOT NULL COMMENT '互动用户ID',
    screen_name VARCHAR(128) COMMENT '用户昵称',
    
    -- 统计数据
    like_count INT UNSIGNED DEFAULT 0 COMMENT '点赞数（评论的点赞）',
    reply_count INT UNSIGNED DEFAULT 0 COMMENT '回复数',
    
    -- 时间信息
    created_at DATETIME NOT NULL COMMENT '互动时间',
    crawl_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬取时间',
    
    -- 元数据
    raw_json JSON COMMENT '原始JSON数据',
    
    -- 索引和约束
    PRIMARY KEY (id, crawl_time),
    UNIQUE KEY uk_interaction_id (interaction_id),
    KEY idx_weibo_id (weibo_id),
    KEY idx_user_id (user_id),
    KEY idx_interaction_type (interaction_type),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='原始互动数据表'
PARTITION BY RANGE (TO_DAYS(crawl_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- 第三部分：处理数据层 (processed_data) - 存储清洗和分析后的数据
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 表4: weibo_processed - 清洗后微博数据表
-- 描述: 存储经过Spark清洗处理后的微博数据
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weibo_processed (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博ID（关联weibo_raw）',
    
    -- 清洗后内容
    clean_content TEXT NOT NULL COMMENT '清洗后的纯文本内容',
    content_length INT UNSIGNED DEFAULT 0 COMMENT '清洗后内容长度',
    
    -- 分词结果
    word_segments JSON COMMENT '分词结果列表',
    word_count INT UNSIGNED DEFAULT 0 COMMENT '词数量',
    
    -- 关键词提取
    keywords JSON COMMENT '提取的关键词（TF-IDF）',
    entities JSON COMMENT '命名实体识别结果',
    
    -- 文本特征
    has_url TINYINT(1) DEFAULT 0 COMMENT '是否包含URL',
    has_mention TINYINT(1) DEFAULT 0 COMMENT '是否包含@用户',
    has_hashtag TINYINT(1) DEFAULT 0 COMMENT '是否包含话题标签',
    has_emoji TINYINT(1) DEFAULT 0 COMMENT '是否包含表情',
    url_count INT UNSIGNED DEFAULT 0 COMMENT 'URL数量',
    mention_count INT UNSIGNED DEFAULT 0 COMMENT '@用户数量',
    hashtag_count INT UNSIGNED DEFAULT 0 COMMENT '话题标签数量',
    
    -- 语言特征
    language VARCHAR(16) DEFAULT 'zh' COMMENT '语言类型',
    encoding_quality DECIMAL(5,4) DEFAULT 1.0000 COMMENT '编码质量分数',
    
    -- 处理信息
    process_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '处理时间',
    process_version VARCHAR(32) DEFAULT '1.0.0' COMMENT '处理程序版本',
    spark_job_id VARCHAR(64) COMMENT 'Spark作业ID',
    
    -- 质量标记
    quality_score DECIMAL(5,4) DEFAULT 0.0000 COMMENT '数据质量分数（0-1）',
    is_valid TINYINT(1) DEFAULT 1 COMMENT '是否有效数据',
    invalid_reason VARCHAR(256) COMMENT '无效原因',
    
    -- 索引和约束
    PRIMARY KEY (id, process_time),
    UNIQUE KEY uk_weibo_id (weibo_id),
    KEY idx_process_time (process_time),
    KEY idx_quality_score (quality_score),
    KEY idx_is_valid (is_valid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='清洗后微博数据表'
PARTITION BY RANGE (TO_DAYS(process_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- -----------------------------------------------------------------------------
-- 表5: sentiment_results - 情感分析结果表
-- 描述: 存储情感分析的详细结果（词典+BERT混合分析）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sentiment_results (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博ID',
    
    -- 情感分类结果
    sentiment_label ENUM('positive', 'neutral', 'negative') NOT NULL COMMENT '情感标签',
    sentiment_score DECIMAL(6,4) NOT NULL COMMENT '情感得分（-1到1）',
    confidence DECIMAL(5,4) NOT NULL COMMENT '置信度（0-1）',
    
    -- 词典分析结果
    lexicon_score DECIMAL(6,4) COMMENT '词典分析得分',
    lexicon_positive_count INT UNSIGNED DEFAULT 0 COMMENT '正面词数量',
    lexicon_negative_count INT UNSIGNED DEFAULT 0 COMMENT '负面词数量',
    lexicon_words JSON COMMENT '匹配的情感词列表',
    
    -- BERT分析结果
    bert_score DECIMAL(6,4) COMMENT 'BERT模型得分',
    bert_probabilities JSON COMMENT 'BERT三分类概率',
    
    -- 混合分析权重
    lexicon_weight DECIMAL(3,2) DEFAULT 0.40 COMMENT '词典权重',
    bert_weight DECIMAL(3,2) DEFAULT 0.60 COMMENT 'BERT权重',
    
    -- 细粒度情感（可选）
    emotion_labels JSON COMMENT '细粒度情感标签（如：愤怒、喜悦、悲伤等）',
    aspect_sentiments JSON COMMENT '方面级情感分析结果',
    
    -- 分析元信息
    analysis_method ENUM('lexicon', 'bert', 'hybrid') DEFAULT 'hybrid' COMMENT '分析方法',
    model_version VARCHAR(32) DEFAULT '1.0.0' COMMENT '模型版本',
    analysis_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
    processing_time_ms INT UNSIGNED COMMENT '处理耗时（毫秒）',
    
    -- 索引和约束
    PRIMARY KEY (id, analysis_time),
    UNIQUE KEY uk_weibo_id (weibo_id),
    KEY idx_sentiment_label (sentiment_label),
    KEY idx_sentiment_score (sentiment_score),
    KEY idx_confidence (confidence),
    KEY idx_analysis_time (analysis_time),
    KEY idx_analysis_method (analysis_method)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='情感分析结果表'
PARTITION BY RANGE (TO_DAYS(analysis_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- -----------------------------------------------------------------------------
-- 表6: dual_dimension_scores - 双维度排序结果表
-- 描述: 存储情感-热度双维度排序模型的计算结果
-- 核心创新点：composite_score = 0.6 * sentiment_score + 0.4 * popularity_score
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dual_dimension_scores (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博ID',
    
    -- 情感维度
    sentiment_score DECIMAL(6,4) NOT NULL COMMENT '归一化情感得分（0-1）',
    sentiment_label ENUM('positive', 'neutral', 'negative') NOT NULL COMMENT '情感标签',
    sentiment_weight DECIMAL(3,2) DEFAULT 0.60 COMMENT '情感权重（默认0.6）',
    
    -- 热度维度
    popularity_score DECIMAL(6,4) NOT NULL COMMENT '归一化热度得分（0-1）',
    popularity_weight DECIMAL(3,2) DEFAULT 0.40 COMMENT '热度权重（默认0.4）',
    
    -- 热度计算明细
    reposts_count INT UNSIGNED DEFAULT 0 COMMENT '转发数',
    comments_count INT UNSIGNED DEFAULT 0 COMMENT '评论数',
    attitudes_count INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
    raw_popularity DECIMAL(12,4) COMMENT '原始热度值（log计算前）',
    
    -- 时间衰减
    time_decay_factor DECIMAL(6,4) DEFAULT 1.0000 COMMENT '时间衰减因子',
    hours_since_post INT UNSIGNED COMMENT '发布后小时数',
    
    -- 综合得分
    composite_score DECIMAL(6,4) NOT NULL COMMENT '综合得分（0-1）',
    ranking INT UNSIGNED COMMENT '排名（在当前批次中）',
    
    -- 计算信息
    batch_id VARCHAR(64) COMMENT '计算批次ID',
    calculate_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
    algorithm_version VARCHAR(32) DEFAULT '1.0.0' COMMENT '算法版本',
    
    -- 索引和约束
    PRIMARY KEY (id, calculate_time),
    UNIQUE KEY uk_weibo_batch (weibo_id, batch_id),
    KEY idx_composite_score (composite_score DESC),
    KEY idx_sentiment_score (sentiment_score),
    KEY idx_popularity_score (popularity_score),
    KEY idx_ranking (ranking),
    KEY idx_batch_id (batch_id),
    KEY idx_calculate_time (calculate_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='双维度排序结果表（核心创新点）'
PARTITION BY RANGE (TO_DAYS(calculate_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- ============================================================================
-- 第四部分：业务数据层 (business_data) - 存储业务分析结果
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 表7: hot_topics - 热点话题表
-- 描述: 存储热搜话题及其情感分析汇总
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hot_topics (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    topic_id VARCHAR(64) NOT NULL COMMENT '话题ID',
    
    -- 话题基本信息
    title VARCHAR(256) NOT NULL COMMENT '话题标题',
    category VARCHAR(64) COMMENT '话题分类（娱乐、社会、科技等）',
    hot_value BIGINT UNSIGNED DEFAULT 0 COMMENT '热度值',
    hot_rank INT UNSIGNED COMMENT '热搜排名',
    
    -- 情感汇总
    weibo_count INT UNSIGNED DEFAULT 0 COMMENT '相关微博数',
    positive_count INT UNSIGNED DEFAULT 0 COMMENT '正面微博数',
    neutral_count INT UNSIGNED DEFAULT 0 COMMENT '中性微博数',
    negative_count INT UNSIGNED DEFAULT 0 COMMENT '负面微博数',
    positive_ratio DECIMAL(5,4) DEFAULT 0.0000 COMMENT '正面比例',
    negative_ratio DECIMAL(5,4) DEFAULT 0.0000 COMMENT '负面比例',
    avg_sentiment_score DECIMAL(6,4) COMMENT '平均情感得分',
    
    -- 热度趋势
    trend ENUM('rising', 'stable', 'falling', 'new', 'hot', 'explosive') DEFAULT 'stable' COMMENT '趋势',
    trend_change DECIMAL(8,4) COMMENT '趋势变化值',
    
    -- 时间信息
    first_appear_time DATETIME COMMENT '首次出现时间',
    peak_time DATETIME COMMENT '热度峰值时间',
    last_update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    crawl_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬取时间',
    
    -- 关键词和标签
    keywords JSON COMMENT '关联关键词',
    tags JSON COMMENT '话题标签',
    
    -- 索引和约束
    UNIQUE KEY uk_topic_id (topic_id),
    KEY idx_title (title(64)),
    KEY idx_hot_rank (hot_rank),
    KEY idx_hot_value (hot_value DESC),
    KEY idx_category (category),
    KEY idx_trend (trend),
    KEY idx_crawl_time (crawl_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='热点话题表';

-- -----------------------------------------------------------------------------
-- 表8: propagation_paths - 传播路径表
-- 描述: 存储微博传播路径分析结果
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS propagation_paths (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    path_id VARCHAR(64) NOT NULL COMMENT '传播路径ID',
    
    -- 源微博信息
    source_weibo_id VARCHAR(64) NOT NULL COMMENT '源微博ID',
    source_user_id VARCHAR(64) NOT NULL COMMENT '源用户ID',
    
    -- 传播信息
    target_weibo_id VARCHAR(64) COMMENT '目标微博ID（转发）',
    target_user_id VARCHAR(64) COMMENT '目标用户ID',
    propagation_type ENUM('repost', 'comment', 'mention') NOT NULL COMMENT '传播类型',
    
    -- 传播层级
    depth INT UNSIGNED DEFAULT 1 COMMENT '传播深度',
    path_sequence JSON COMMENT '传播路径序列',
    
    -- 传播时间
    propagation_time DATETIME NOT NULL COMMENT '传播时间',
    time_lag_seconds INT UNSIGNED COMMENT '传播时间差（秒）',
    
    -- 影响力指标
    influence_score DECIMAL(8,4) COMMENT '影响力得分',
    reach_count INT UNSIGNED DEFAULT 0 COMMENT '触达人数',
    
    -- 分析时间
    analysis_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
    
    -- 索引和约束
    UNIQUE KEY uk_path_id (path_id),
    KEY idx_source_weibo_id (source_weibo_id),
    KEY idx_source_user_id (source_user_id),
    KEY idx_propagation_type (propagation_type),
    KEY idx_depth (depth),
    KEY idx_propagation_time (propagation_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='传播路径表';

-- -----------------------------------------------------------------------------
-- 表9: alert_events - 预警事件表
-- 描述: 存储舆情预警事件
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    alert_id VARCHAR(64) NOT NULL COMMENT '预警ID',
    
    -- 预警基本信息
    alert_type ENUM('negative_surge', 'hot_topic', 'sensitive_word', 'abnormal_spread', 'custom') NOT NULL COMMENT '预警类型',
    alert_level ENUM('low', 'medium', 'high', 'critical') NOT NULL COMMENT '预警级别',
    title VARCHAR(256) NOT NULL COMMENT '预警标题',
    description TEXT COMMENT '预警描述',
    
    -- 触发条件
    trigger_condition JSON COMMENT '触发条件详情',
    trigger_value DECIMAL(12,4) COMMENT '触发值',
    threshold_value DECIMAL(12,4) COMMENT '阈值',
    
    -- 关联信息
    related_topic VARCHAR(256) COMMENT '关联话题',
    related_weibo_ids JSON COMMENT '关联微博ID列表',
    related_keywords JSON COMMENT '关联关键词',
    
    -- 情感数据
    negative_ratio DECIMAL(5,4) COMMENT '负面比例',
    sentiment_change DECIMAL(6,4) COMMENT '情感变化值',
    
    -- 状态信息
    status ENUM('pending', 'processing', 'resolved', 'ignored') DEFAULT 'pending' COMMENT '处理状态',
    handler VARCHAR(64) COMMENT '处理人',
    handle_time DATETIME COMMENT '处理时间',
    handle_note TEXT COMMENT '处理备注',
    
    -- 时间信息
    trigger_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '触发时间',
    expire_time DATETIME COMMENT '过期时间',
    
    -- 索引和约束
    UNIQUE KEY uk_alert_id (alert_id),
    KEY idx_alert_type (alert_type),
    KEY idx_alert_level (alert_level),
    KEY idx_status (status),
    KEY idx_trigger_time (trigger_time),
    KEY idx_related_topic (related_topic(64))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='预警事件表';

-- ============================================================================
-- 第五部分：系统管理层 (system_data) - 存储系统运行数据
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 表10: crawl_logs - 爬虫日志表
-- 描述: 记录爬虫任务执行日志
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crawl_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    
    -- 任务信息
    task_type ENUM('hot_search', 'keyword_search', 'topic', 'user', 'realtime') NOT NULL COMMENT '任务类型',
    keywords JSON COMMENT '搜索关键词列表',
    
    -- 执行状态
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    progress DECIMAL(5,2) DEFAULT 0.00 COMMENT '进度百分比',
    
    -- 统计数据
    total_count INT UNSIGNED DEFAULT 0 COMMENT '预期采集数',
    collected_count INT UNSIGNED DEFAULT 0 COMMENT '已采集数',
    failed_count INT UNSIGNED DEFAULT 0 COMMENT '失败数',
    duplicate_count INT UNSIGNED DEFAULT 0 COMMENT '重复数',
    
    -- 性能数据
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_seconds INT UNSIGNED COMMENT '耗时（秒）',
    avg_speed DECIMAL(8,2) COMMENT '平均速度（条/分钟）',
    
    -- 错误信息
    error_message TEXT COMMENT '错误信息',
    error_count INT UNSIGNED DEFAULT 0 COMMENT '错误次数',
    last_error_time DATETIME COMMENT '最后错误时间',
    
    -- 配置信息
    config JSON COMMENT '任务配置',
    
    -- 时间信息
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引和约束
    PRIMARY KEY (id, created_at),
    UNIQUE KEY uk_task_id (task_id),
    KEY idx_task_type (task_type),
    KEY idx_status (status),
    KEY idx_start_time (start_time),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='爬虫日志表'
PARTITION BY RANGE (TO_DAYS(created_at)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- -----------------------------------------------------------------------------
-- 表11: system_configs - 系统配置表
-- 描述: 存储系统配置参数
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_configs (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    config_key VARCHAR(128) NOT NULL COMMENT '配置键',
    config_value TEXT NOT NULL COMMENT '配置值',
    config_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string' COMMENT '值类型',
    
    -- 分类信息
    category VARCHAR(64) DEFAULT 'general' COMMENT '配置分类',
    description VARCHAR(512) COMMENT '配置描述',
    
    -- 状态信息
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    is_system TINYINT(1) DEFAULT 0 COMMENT '是否系统配置（不可删除）',
    
    -- 时间信息
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by VARCHAR(64) COMMENT '更新人',
    
    -- 索引和约束
    UNIQUE KEY uk_config_key (config_key),
    KEY idx_category (category),
    KEY idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='系统配置表';

-- -----------------------------------------------------------------------------
-- 表12: user_management - 用户管理表
-- 描述: 系统用户管理（非微博用户）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_management (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    username VARCHAR(64) NOT NULL COMMENT '用户名',
    password_hash VARCHAR(256) NOT NULL COMMENT '密码哈希',
    
    -- 用户信息
    display_name VARCHAR(128) COMMENT '显示名称',
    email VARCHAR(256) COMMENT '邮箱',
    phone VARCHAR(32) COMMENT '手机号',
    avatar_url VARCHAR(512) COMMENT '头像URL',
    
    -- 权限信息
    role ENUM('admin', 'analyst', 'viewer', 'guest') DEFAULT 'viewer' COMMENT '角色',
    permissions JSON COMMENT '权限列表',
    
    -- 状态信息
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    is_locked TINYINT(1) DEFAULT 0 COMMENT '是否锁定',
    lock_reason VARCHAR(256) COMMENT '锁定原因',
    
    -- 登录信息
    last_login_time DATETIME COMMENT '最后登录时间',
    last_login_ip VARCHAR(64) COMMENT '最后登录IP',
    login_count INT UNSIGNED DEFAULT 0 COMMENT '登录次数',
    failed_login_count INT UNSIGNED DEFAULT 0 COMMENT '失败登录次数',
    
    -- 时间信息
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引和约束
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    KEY idx_role (role),
    KEY idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用户管理表';

-- ============================================================================
-- 第六部分：毕业设计层 (graduation_data) - 毕业设计专用统计表
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 表13: graduation_statistics - 毕业设计统计表
-- 描述: 存储毕业设计所需的各类统计数据
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS graduation_statistics (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    stat_id VARCHAR(64) NOT NULL COMMENT '统计ID',
    
    -- 统计类型
    stat_type ENUM(
        'daily_summary',           -- 每日汇总
        'sentiment_distribution',  -- 情感分布
        'topic_analysis',          -- 话题分析
        'user_behavior',           -- 用户行为
        'system_performance',      -- 系统性能
        'model_accuracy',          -- 模型准确率
        'data_quality',            -- 数据质量
        'custom'                   -- 自定义
    ) NOT NULL COMMENT '统计类型',
    
    -- 统计维度
    dimension VARCHAR(64) COMMENT '统计维度（如：日期、话题、用户等）',
    dimension_value VARCHAR(256) COMMENT '维度值',
    
    -- 统计数据
    stat_data JSON NOT NULL COMMENT '统计数据（JSON格式）',
    
    -- 数值汇总（便于查询）
    total_count BIGINT UNSIGNED DEFAULT 0 COMMENT '总数',
    positive_count BIGINT UNSIGNED DEFAULT 0 COMMENT '正面数',
    negative_count BIGINT UNSIGNED DEFAULT 0 COMMENT '负面数',
    neutral_count BIGINT UNSIGNED DEFAULT 0 COMMENT '中性数',
    avg_score DECIMAL(8,4) COMMENT '平均分数',
    
    -- 时间范围
    stat_date DATE COMMENT '统计日期',
    start_time DATETIME COMMENT '统计开始时间',
    end_time DATETIME COMMENT '统计结束时间',
    
    -- 元信息
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    note TEXT COMMENT '备注',
    
    -- 索引和约束
    UNIQUE KEY uk_stat_id (stat_id),
    KEY idx_stat_type (stat_type),
    KEY idx_stat_date (stat_date),
    KEY idx_dimension (dimension),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='毕业设计统计表';

-- -----------------------------------------------------------------------------
-- 表14: performance_metrics - 性能指标表
-- 描述: 存储系统性能指标数据
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS performance_metrics (
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    metric_id VARCHAR(64) NOT NULL COMMENT '指标ID',
    
    -- 指标类型
    metric_type ENUM(
        'crawl_speed',             -- 爬取速度
        'process_throughput',      -- 处理吞吐量
        'analysis_latency',        -- 分析延迟
        'api_response_time',       -- API响应时间
        'spark_job_duration',      -- Spark作业耗时
        'memory_usage',            -- 内存使用
        'cpu_usage',               -- CPU使用
        'disk_io',                 -- 磁盘IO
        'network_io',              -- 网络IO
        'custom'                   -- 自定义
    ) NOT NULL COMMENT '指标类型',
    
    -- 指标数据
    metric_name VARCHAR(128) NOT NULL COMMENT '指标名称',
    metric_value DECIMAL(16,4) NOT NULL COMMENT '指标值',
    metric_unit VARCHAR(32) COMMENT '单位（如：ms, MB, req/s）',
    
    -- 上下文信息
    component VARCHAR(64) COMMENT '组件名称（如：crawler, spark, api）',
    operation VARCHAR(128) COMMENT '操作名称',
    
    -- 统计信息
    sample_count INT UNSIGNED DEFAULT 1 COMMENT '采样数',
    min_value DECIMAL(16,4) COMMENT '最小值',
    max_value DECIMAL(16,4) COMMENT '最大值',
    avg_value DECIMAL(16,4) COMMENT '平均值',
    p50_value DECIMAL(16,4) COMMENT 'P50值',
    p95_value DECIMAL(16,4) COMMENT 'P95值',
    p99_value DECIMAL(16,4) COMMENT 'P99值',
    
    -- 时间信息
    record_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    
    -- 索引和约束
    PRIMARY KEY (id, record_time),
    UNIQUE KEY uk_metric_id (metric_id),
    KEY idx_metric_type (metric_type),
    KEY idx_component (component),
    KEY idx_record_time (record_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='性能指标表'
PARTITION BY RANGE (TO_DAYS(record_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- -----------------------------------------------------------------------------
-- 表15: validation_results - 验证结果表
-- 描述: 存储模型验证和测试结果
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    validation_id VARCHAR(64) NOT NULL COMMENT '验证ID',
    
    -- 验证类型
    validation_type ENUM(
        'sentiment_accuracy',      -- 情感分析准确率
        'dual_dimension_eval',     -- 双维度模型评估
        'data_quality_check',      -- 数据质量检查
        'system_integration',      -- 系统集成测试
        'performance_benchmark',   -- 性能基准测试
        'regression_test',         -- 回归测试
        'custom'                   -- 自定义
    ) NOT NULL COMMENT '验证类型',
    
    -- 验证配置
    test_name VARCHAR(256) NOT NULL COMMENT '测试名称',
    test_description TEXT COMMENT '测试描述',
    test_config JSON COMMENT '测试配置',
    
    -- 数据集信息
    dataset_name VARCHAR(128) COMMENT '数据集名称',
    dataset_size INT UNSIGNED COMMENT '数据集大小',
    train_size INT UNSIGNED COMMENT '训练集大小',
    test_size INT UNSIGNED COMMENT '测试集大小',
    
    -- 评估指标
    accuracy DECIMAL(6,4) COMMENT '准确率',
    precision_score DECIMAL(6,4) COMMENT '精确率',
    recall DECIMAL(6,4) COMMENT '召回率',
    f1_score DECIMAL(6,4) COMMENT 'F1分数',
    auc DECIMAL(6,4) COMMENT 'AUC值',
    
    -- 混淆矩阵
    confusion_matrix JSON COMMENT '混淆矩阵',
    
    -- 详细结果
    detailed_results JSON COMMENT '详细结果',
    error_analysis JSON COMMENT '错误分析',
    
    -- 状态信息
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '状态',
    error_message TEXT COMMENT '错误信息',
    
    -- 时间信息
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_seconds INT UNSIGNED COMMENT '耗时（秒）',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 备注
    note TEXT COMMENT '备注',
    created_by VARCHAR(64) COMMENT '创建人',
    
    -- 索引和约束
    UNIQUE KEY uk_validation_id (validation_id),
    KEY idx_validation_type (validation_type),
    KEY idx_status (status),
    KEY idx_accuracy (accuracy),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='验证结果表';

-- ============================================================================
-- 第七部分：视图定义 - 便于数据查询和分析
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 视图1: v_weibo_full_analysis - 微博完整分析视图
-- 描述: 关联原始数据、处理数据和情感分析结果
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_weibo_full_analysis AS
SELECT 
    wr.weibo_id,
    wr.content AS raw_content,
    wp.clean_content,
    wr.user_id,
    wr.screen_name,
    wr.reposts_count,
    wr.comments_count,
    wr.attitudes_count,
    wr.created_at AS weibo_created_at,
    wr.topic,
    wr.keyword,
    sr.sentiment_label,
    sr.sentiment_score,
    sr.confidence,
    sr.analysis_method,
    dds.popularity_score,
    dds.composite_score,
    dds.ranking
FROM weibo_raw wr
LEFT JOIN weibo_processed wp ON wr.weibo_id = wp.weibo_id
LEFT JOIN sentiment_results sr ON wr.weibo_id = sr.weibo_id
LEFT JOIN dual_dimension_scores dds ON wr.weibo_id = dds.weibo_id;

-- -----------------------------------------------------------------------------
-- 视图2: v_daily_sentiment_summary - 每日情感汇总视图
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_daily_sentiment_summary AS
SELECT 
    DATE(sr.analysis_time) AS stat_date,
    COUNT(*) AS total_count,
    SUM(CASE WHEN sr.sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_count,
    SUM(CASE WHEN sr.sentiment_label = 'neutral' THEN 1 ELSE 0 END) AS neutral_count,
    SUM(CASE WHEN sr.sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_count,
    AVG(sr.sentiment_score) AS avg_sentiment_score,
    AVG(sr.confidence) AS avg_confidence
FROM sentiment_results sr
GROUP BY DATE(sr.analysis_time);

-- -----------------------------------------------------------------------------
-- 视图3: v_hot_topic_sentiment - 热点话题情感视图
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_hot_topic_sentiment AS
SELECT 
    ht.topic_id,
    ht.title,
    ht.category,
    ht.hot_value,
    ht.hot_rank,
    ht.weibo_count,
    ht.positive_ratio,
    ht.negative_ratio,
    ht.avg_sentiment_score,
    ht.trend,
    ht.crawl_time
FROM hot_topics ht
ORDER BY ht.hot_rank ASC, ht.hot_value DESC;

-- ============================================================================
-- 第八部分：触发器定义 - 数据一致性保障
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 触发器1: 更新微博处理状态
-- -----------------------------------------------------------------------------
DELIMITER //

CREATE TRIGGER tr_update_weibo_processed_status
AFTER INSERT ON weibo_processed
FOR EACH ROW
BEGIN
    UPDATE weibo_raw 
    SET is_processed = 1 
    WHERE weibo_id = NEW.weibo_id;
END//

-- -----------------------------------------------------------------------------
-- 触发器2: 更新热点话题统计
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_update_hot_topic_stats
AFTER INSERT ON sentiment_results
FOR EACH ROW
BEGIN
    DECLARE v_topic VARCHAR(256);
    
    -- 获取微博关联的话题
    SELECT topic INTO v_topic 
    FROM weibo_raw 
    WHERE weibo_id = NEW.weibo_id 
    LIMIT 1;
    
    -- 如果有关联话题，更新统计
    IF v_topic IS NOT NULL AND v_topic != '' THEN
        UPDATE hot_topics 
        SET 
            weibo_count = weibo_count + 1,
            positive_count = positive_count + IF(NEW.sentiment_label = 'positive', 1, 0),
            neutral_count = neutral_count + IF(NEW.sentiment_label = 'neutral', 1, 0),
            negative_count = negative_count + IF(NEW.sentiment_label = 'negative', 1, 0),
            last_update_time = NOW()
        WHERE title = v_topic;
    END IF;
END//

-- -----------------------------------------------------------------------------
-- 触发器3: 自动计算热点话题比例
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_calculate_topic_ratios
BEFORE UPDATE ON hot_topics
FOR EACH ROW
BEGIN
    IF NEW.weibo_count > 0 THEN
        SET NEW.positive_ratio = NEW.positive_count / NEW.weibo_count;
        SET NEW.negative_ratio = NEW.negative_count / NEW.weibo_count;
    END IF;
END//

-- -----------------------------------------------------------------------------
-- 触发器4: 爬虫任务完成时更新统计
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_crawl_task_completed
AFTER UPDATE ON crawl_logs
FOR EACH ROW
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        -- 计算耗时
        UPDATE crawl_logs 
        SET duration_seconds = TIMESTAMPDIFF(SECOND, start_time, end_time)
        WHERE task_id = NEW.task_id;
    END IF;
END//

DELIMITER ;

-- ============================================================================
-- 第九部分：存储过程 - 常用数据操作
-- ============================================================================

DELIMITER //

-- -----------------------------------------------------------------------------
-- 存储过程1: 生成每日统计报告
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_generate_daily_stats(IN p_date DATE)
BEGIN
    DECLARE v_stat_id VARCHAR(64);
    SET v_stat_id = CONCAT('daily_', DATE_FORMAT(p_date, '%Y%m%d'), '_', UNIX_TIMESTAMP());
    
    INSERT INTO graduation_statistics (
        stat_id, stat_type, dimension, dimension_value, stat_data,
        total_count, positive_count, negative_count, neutral_count, avg_score,
        stat_date, start_time, end_time
    )
    SELECT 
        v_stat_id,
        'daily_summary',
        'date',
        DATE_FORMAT(p_date, '%Y-%m-%d'),
        JSON_OBJECT(
            'total_weibo', COUNT(*),
            'positive_count', SUM(CASE WHEN sr.sentiment_label = 'positive' THEN 1 ELSE 0 END),
            'neutral_count', SUM(CASE WHEN sr.sentiment_label = 'neutral' THEN 1 ELSE 0 END),
            'negative_count', SUM(CASE WHEN sr.sentiment_label = 'negative' THEN 1 ELSE 0 END),
            'avg_sentiment_score', AVG(sr.sentiment_score),
            'avg_confidence', AVG(sr.confidence)
        ),
        COUNT(*),
        SUM(CASE WHEN sr.sentiment_label = 'positive' THEN 1 ELSE 0 END),
        SUM(CASE WHEN sr.sentiment_label = 'negative' THEN 1 ELSE 0 END),
        SUM(CASE WHEN sr.sentiment_label = 'neutral' THEN 1 ELSE 0 END),
        AVG(sr.sentiment_score),
        p_date,
        CONCAT(p_date, ' 00:00:00'),
        CONCAT(p_date, ' 23:59:59')
    FROM sentiment_results sr
    WHERE DATE(sr.analysis_time) = p_date;
END//

-- -----------------------------------------------------------------------------
-- 存储过程2: 清理过期数据
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_cleanup_expired_data(IN p_days_to_keep INT)
BEGIN
    DECLARE v_cutoff_date DATETIME;
    SET v_cutoff_date = DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY);
    
    -- 删除过期的原始数据（软删除）
    UPDATE weibo_raw 
    SET is_deleted = 1 
    WHERE crawl_time < v_cutoff_date AND is_deleted = 0;
    
    -- 删除过期的性能指标
    DELETE FROM performance_metrics 
    WHERE record_time < v_cutoff_date;
    
    -- 记录清理操作
    INSERT INTO graduation_statistics (
        stat_id, stat_type, dimension, dimension_value, stat_data, stat_date
    ) VALUES (
        CONCAT('cleanup_', UNIX_TIMESTAMP()),
        'custom',
        'cleanup',
        'expired_data',
        JSON_OBJECT('cutoff_date', v_cutoff_date, 'days_kept', p_days_to_keep),
        CURDATE()
    );
END//

-- -----------------------------------------------------------------------------
-- 存储过程3: 计算模型准确率
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_calculate_model_accuracy(
    IN p_start_date DATE,
    IN p_end_date DATE,
    OUT p_accuracy DECIMAL(6,4)
)
BEGIN
    -- 这里假设有人工标注的数据用于验证
    -- 实际使用时需要根据具体的验证数据集进行计算
    SELECT 
        AVG(sr.confidence) INTO p_accuracy
    FROM sentiment_results sr
    WHERE DATE(sr.analysis_time) BETWEEN p_start_date AND p_end_date;
    
    -- 记录验证结果
    INSERT INTO validation_results (
        validation_id, validation_type, test_name, accuracy, status, created_at
    ) VALUES (
        CONCAT('accuracy_', UNIX_TIMESTAMP()),
        'sentiment_accuracy',
        CONCAT('Accuracy check from ', p_start_date, ' to ', p_end_date),
        p_accuracy,
        'completed',
        NOW()
    );
END//

DELIMITER ;

-- ============================================================================
-- 第十部分：初始数据插入
-- ============================================================================

-- 插入默认系统配置
INSERT INTO system_configs (config_key, config_value, config_type, category, description, is_system) VALUES
('sentiment.lexicon_weight', '0.40', 'number', 'sentiment', '词典分析权重', 1),
('sentiment.bert_weight', '0.60', 'number', 'sentiment', 'BERT分析权重', 1),
('dual_dimension.sentiment_weight', '0.60', 'number', 'ranking', '双维度排序-情感权重', 1),
('dual_dimension.popularity_weight', '0.40', 'number', 'ranking', '双维度排序-热度权重', 1),
('crawler.request_interval', '2', 'number', 'crawler', '爬虫请求间隔（秒）', 1),
('crawler.max_retry', '3', 'number', 'crawler', '爬虫最大重试次数', 1),
('alert.negative_threshold', '0.30', 'number', 'alert', '负面情感预警阈值', 1),
('system.data_retention_days', '180', 'number', 'system', '数据保留天数', 1),
('system.timezone', 'Asia/Shanghai', 'string', 'system', '系统时区', 1),
('graduation.project_name', '基于Spark的分布式微博情感分析系统', 'string', 'graduation', '毕业设计项目名称', 1);

-- 插入默认管理员用户
INSERT INTO user_management (username, password_hash, display_name, role, is_active) VALUES
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMy.MqrqBuBjZWpBNvH8TZGy6fLdGIr9FdC', '系统管理员', 'admin', 1);

-- ============================================================================
-- 第十一部分：索引优化建议
-- ============================================================================

-- 复合索引优化（根据常用查询模式）
-- 1. 按时间和情感标签查询
CREATE INDEX idx_sentiment_time_label ON sentiment_results(analysis_time, sentiment_label);

-- 2. 按话题和时间查询
CREATE INDEX idx_weibo_topic_time ON weibo_raw(topic(64), crawl_time);

-- 3. 按用户和时间查询
CREATE INDEX idx_weibo_user_time ON weibo_raw(user_id, created_at);

-- 4. 双维度排序查询优化
CREATE INDEX idx_dual_composite_batch ON dual_dimension_scores(batch_id, composite_score DESC);

-- 5. 热点话题查询优化
CREATE INDEX idx_hot_topic_rank_time ON hot_topics(hot_rank, crawl_time);

-- ============================================================================
-- 第十二部分：数据备份和恢复机制
-- ============================================================================

-- 备份表：存储备份记录
CREATE TABLE IF NOT EXISTS backup_logs (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    backup_id VARCHAR(64) NOT NULL COMMENT '备份ID',
    backup_type ENUM('full', 'incremental', 'table') NOT NULL COMMENT '备份类型',
    backup_path VARCHAR(512) NOT NULL COMMENT '备份文件路径',
    tables_included JSON COMMENT '包含的表',
    file_size_mb DECIMAL(12,2) COMMENT '文件大小（MB）',
    row_count BIGINT UNSIGNED COMMENT '记录数',
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '状态',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by VARCHAR(64) COMMENT '创建人',
    
    UNIQUE KEY uk_backup_id (backup_id),
    KEY idx_backup_type (backup_type),
    KEY idx_status (status),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='备份日志表';

-- ============================================================================
-- 完成提示
-- ============================================================================

SELECT '数据库 weibo_sentiment_graduation 创建完成！' AS message;
SELECT CONCAT('共创建 ', COUNT(*), ' 个表') AS table_count 
FROM information_schema.tables 
WHERE table_schema = 'weibo_sentiment_graduation';
