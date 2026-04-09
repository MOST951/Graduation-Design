-- ============================================================================
-- 微博情感分析系统 - 核心数据表
-- 数据库名称: weibo_sentiment_graduation
-- 创建日期: 2026-01-28
-- 作者: 罗森 (学号: 2022407443)
-- 学校: 四川民族学院 智能科学与技术学院 2248班
-- 指导教师: 罗丹
-- ============================================================================

USE weibo_sentiment_graduation;

-- ============================================================================
-- 表1: weibo_core_data - 微博核心数据表
-- 描述: 存储所有爬取的微博数据，是系统的核心数据表
-- ============================================================================

DROP TABLE IF EXISTS weibo_core_data;

CREATE TABLE weibo_core_data (
    -- ==================== 基础信息 ====================
    weibo_id BIGINT UNSIGNED NOT NULL COMMENT '微博唯一ID（主键）',
    mid VARCHAR(32) COMMENT '微博MID',
    bid VARCHAR(32) COMMENT '微博BID（短链接ID）',
    content TEXT NOT NULL COMMENT '微博内容（原始文本）',
    content_clean TEXT COMMENT '清洗后的微博内容',
    content_length INT UNSIGNED DEFAULT 0 COMMENT '内容长度（字符数）',
    created_at DATETIME NOT NULL COMMENT '微博发布时间',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据采集时间',
    
    -- ==================== 用户信息 ====================
    user_id BIGINT UNSIGNED NOT NULL COMMENT '发布用户ID',
    user_name VARCHAR(128) NOT NULL COMMENT '用户昵称',
    user_avatar VARCHAR(512) COMMENT '用户头像URL',
    verified TINYINT(1) DEFAULT 0 COMMENT '是否认证用户（0:否, 1:是）',
    verified_type INT DEFAULT -1 COMMENT '认证类型（-1:未认证, 0:个人, 1:企业, 2:媒体, 3:政府）',
    verified_reason VARCHAR(256) COMMENT '认证原因/说明',
    followers_count INT UNSIGNED DEFAULT 0 COMMENT '粉丝数',
    friends_count INT UNSIGNED DEFAULT 0 COMMENT '关注数',
    statuses_count INT UNSIGNED DEFAULT 0 COMMENT '微博数',
    influence_score DECIMAL(8,4) DEFAULT 0.0000 COMMENT '用户影响力分数（计算得出）',
    
    -- ==================== 互动数据 ====================
    reposts_count INT UNSIGNED DEFAULT 0 COMMENT '转发数',
    comments_count INT UNSIGNED DEFAULT 0 COMMENT '评论数',
    attitudes_count INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
    total_interaction INT UNSIGNED GENERATED ALWAYS AS (reposts_count + comments_count + attitudes_count) STORED COMMENT '总互动数（自动计算）',
    
    -- ==================== 媒体信息 ====================
    has_image TINYINT(1) DEFAULT 0 COMMENT '是否包含图片',
    has_video TINYINT(1) DEFAULT 0 COMMENT '是否包含视频',
    image_urls JSON COMMENT '图片URL列表（JSON数组）',
    video_url VARCHAR(512) COMMENT '视频URL',
    image_count INT UNSIGNED DEFAULT 0 COMMENT '图片数量',
    
    -- ==================== 位置信息 ====================
    location VARCHAR(128) COMMENT '地理位置（原始字符串）',
    province VARCHAR(32) COMMENT '省份',
    city VARCHAR(32) COMMENT '城市',
    latitude DECIMAL(10,7) COMMENT '纬度',
    longitude DECIMAL(10,7) COMMENT '经度',
    
    -- ==================== 话题信息 ====================
    topics JSON COMMENT '话题标签列表（JSON数组，如：["#话题1#", "#话题2#"]）',
    topic_count INT UNSIGNED DEFAULT 0 COMMENT '话题数量',
    mentions JSON COMMENT '@用户列表（JSON数组）',
    mention_count INT UNSIGNED DEFAULT 0 COMMENT '@用户数量',
    
    -- ==================== 来源信息 ====================
    source VARCHAR(128) COMMENT '发布来源（如：iPhone客户端）',
    source_url VARCHAR(256) COMMENT '来源链接',
    is_long_text TINYINT(1) DEFAULT 0 COMMENT '是否为长文本',
    is_repost TINYINT(1) DEFAULT 0 COMMENT '是否为转发微博',
    original_weibo_id BIGINT UNSIGNED COMMENT '原始微博ID（如果是转发）',
    
    -- ==================== 爬虫信息 ====================
    crawl_method ENUM('hot_search', 'keyword_search', 'topic', 'user_timeline', 'realtime', 'api') DEFAULT 'keyword_search' COMMENT '采集方式',
    keyword VARCHAR(128) COMMENT '搜索关键词',
    hot_search_rank INT COMMENT '热搜排名（如果来自热搜）',
    batch_id VARCHAR(64) COMMENT '采集批次ID',
    crawl_source VARCHAR(64) DEFAULT 'weibo_spider' COMMENT '爬虫来源标识',
    
    -- ==================== 扩展信息 ====================
    raw_json JSON COMMENT '原始JSON数据（完整保留）',
    extra_data JSON COMMENT '扩展数据字段',
    
    -- ==================== 毕业设计专用字段 ====================
    student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号（毕业设计标识）',
    graduation_batch TINYINT(1) DEFAULT 1 COMMENT '是否为毕业设计批次数据',
    graduation_note VARCHAR(256) COMMENT '毕业设计备注',
    
    -- ==================== 状态标记 ====================
    is_processed TINYINT(1) DEFAULT 0 COMMENT '是否已处理（情感分析）',
    is_ranked TINYINT(1) DEFAULT 0 COMMENT '是否已排序（双维度）',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '是否已删除（软删除）',
    update_count INT UNSIGNED DEFAULT 0 COMMENT '更新次数',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    
    -- ==================== 主键和索引 ====================
    PRIMARY KEY (weibo_id, crawled_at),
    
    -- 唯一索引
    UNIQUE KEY uk_weibo_id (weibo_id),
    
    -- 时间索引（用于时间范围查询）
    KEY idx_created_at (created_at),
    KEY idx_crawled_at (crawled_at),
    
    -- 用户索引（用于用户分析）
    KEY idx_user_id (user_id),
    KEY idx_user_name (user_name),
    
    -- 关键词索引
    KEY idx_keyword (keyword),
    KEY idx_batch_id (batch_id),
    
    -- 互动数据索引（用于热度排序）
    KEY idx_reposts (reposts_count DESC),
    KEY idx_comments (comments_count DESC),
    KEY idx_attitudes (attitudes_count DESC),
    KEY idx_total_interaction (total_interaction DESC),
    
    -- 状态索引
    KEY idx_is_processed (is_processed),
    KEY idx_is_ranked (is_ranked),
    KEY idx_graduation_batch (graduation_batch),
    
    -- 复合索引（优化常用查询）
    KEY idx_keyword_time (keyword, created_at),
    KEY idx_user_time (user_id, created_at),
    KEY idx_batch_status (batch_id, is_processed),
    KEY idx_graduation_time (graduation_batch, crawled_at),
    
    -- 全文索引（用于内容搜索）
    FULLTEXT KEY ft_content (content) WITH PARSER ngram,
    FULLTEXT KEY ft_keyword (keyword) WITH PARSER ngram
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='微博核心数据表 - 存储所有爬取的微博数据（毕业设计：罗森 2022407443）'
PARTITION BY RANGE (TO_DAYS(crawled_at)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')) COMMENT '2026年1月数据',
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')) COMMENT '2026年2月数据',
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')) COMMENT '2026年3月数据',
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')) COMMENT '2026年4月数据',
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')) COMMENT '2026年5月数据',
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')) COMMENT '2026年6月数据',
    PARTITION p_future VALUES LESS THAN MAXVALUE COMMENT '未来数据'
);


-- ============================================================================
-- 表2: sentiment_analysis_results - 情感分析结果表
-- 描述: 存储混合情感分析的详细结果（词典+BERT+混合）
-- ============================================================================

DROP TABLE IF EXISTS sentiment_analysis_results;

CREATE TABLE sentiment_analysis_results (
    -- ==================== 主键 ====================
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    weibo_id BIGINT UNSIGNED NOT NULL COMMENT '微博ID（关联weibo_core_data）',
    
    -- ==================== 词典分析结果 ====================
    dict_score DECIMAL(5,4) COMMENT '词典方法得分（-1到1）',
    dict_positive_words JSON COMMENT '匹配的正面词列表',
    dict_negative_words JSON COMMENT '匹配的负面词列表',
    dict_positive_count INT UNSIGNED DEFAULT 0 COMMENT '正面词数量',
    dict_negative_count INT UNSIGNED DEFAULT 0 COMMENT '负面词数量',
    dict_degree_words JSON COMMENT '程度副词列表',
    dict_negation_words JSON COMMENT '否定词列表',
    
    -- ==================== BERT分析结果 ====================
    bert_score DECIMAL(5,4) COMMENT 'BERT模型得分（-1到1）',
    bert_positive_prob DECIMAL(5,4) COMMENT 'BERT正面概率',
    bert_neutral_prob DECIMAL(5,4) COMMENT 'BERT中性概率',
    bert_negative_prob DECIMAL(5,4) COMMENT 'BERT负面概率',
    bert_hidden_state JSON COMMENT 'BERT隐藏层特征（可选）',
    
    -- ==================== 混合分析结果 ====================
    hybrid_score DECIMAL(5,4) NOT NULL COMMENT '混合方法得分（-1到1）',
    dict_weight DECIMAL(3,2) DEFAULT 0.40 COMMENT '词典权重（默认0.4）',
    bert_weight DECIMAL(3,2) DEFAULT 0.60 COMMENT 'BERT权重（默认0.6）',
    
    -- ==================== 情感分类 ====================
    sentiment_class ENUM('positive', 'negative', 'neutral') NOT NULL COMMENT '情感分类',
    sentiment_class_cn VARCHAR(16) GENERATED ALWAYS AS (
        CASE sentiment_class 
            WHEN 'positive' THEN '正面'
            WHEN 'negative' THEN '负面'
            WHEN 'neutral' THEN '中性'
        END
    ) STORED COMMENT '情感分类（中文）',
    
    -- ==================== 情感强度和置信度 ====================
    intensity DECIMAL(3,2) NOT NULL COMMENT '情感强度（0-1，绝对值）',
    confidence DECIMAL(3,2) NOT NULL COMMENT '分类置信度（0-1）',
    
    -- ==================== 细粒度情感（可选） ====================
    fine_grained_emotion JSON COMMENT '细粒度情感（如：愤怒、喜悦、悲伤、恐惧、惊讶、厌恶）',
    aspect_sentiment JSON COMMENT '方面级情感分析结果',
    
    -- ==================== 分析元信息 ====================
    analysis_method ENUM('dict_only', 'bert_only', 'hybrid') DEFAULT 'hybrid' COMMENT '分析方法',
    model_version VARCHAR(50) DEFAULT 'v1.0.0' COMMENT '模型版本',
    dict_version VARCHAR(50) DEFAULT 'hownet_v1' COMMENT '词典版本',
    bert_model_name VARCHAR(100) DEFAULT 'chinese-bert-wwm' COMMENT 'BERT模型名称',
    
    -- ==================== 时间信息 ====================
    analysis_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
    processing_time_ms INT UNSIGNED COMMENT '处理耗时（毫秒）',
    
    -- ==================== 准确率验证 ====================
    accuracy_verified TINYINT(1) DEFAULT 0 COMMENT '是否已人工验证',
    verified_label ENUM('positive', 'negative', 'neutral') COMMENT '人工标注的正确标签',
    is_correct TINYINT(1) GENERATED ALWAYS AS (
        CASE WHEN accuracy_verified = 1 AND sentiment_class = verified_label THEN 1 ELSE 0 END
    ) STORED COMMENT '预测是否正确',
    verified_by VARCHAR(64) COMMENT '验证人',
    verified_time DATETIME COMMENT '验证时间',
    
    -- ==================== 毕业设计标记 ====================
    graduation_flag TINYINT(1) DEFAULT 1 COMMENT '毕业设计数据标记',
    student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
    
    -- ==================== 主键和索引 ====================
    PRIMARY KEY (id, analysis_time),
    UNIQUE KEY uk_weibo_id (weibo_id),
    
    -- 情感分类索引
    KEY idx_sentiment_class (sentiment_class),
    KEY idx_hybrid_score (hybrid_score),
    KEY idx_confidence (confidence),
    
    -- 时间索引
    KEY idx_analysis_time (analysis_time),
    
    -- 验证索引
    KEY idx_accuracy_verified (accuracy_verified),
    KEY idx_is_correct (is_correct),
    
    -- 复合索引
    KEY idx_weibo_analysis_time (weibo_id, analysis_time),
    KEY idx_class_confidence (sentiment_class, confidence DESC),
    KEY idx_graduation_class (graduation_flag, sentiment_class),
    
    -- 外键约束
    CONSTRAINT fk_sentiment_weibo FOREIGN KEY (weibo_id) 
        REFERENCES weibo_core_data(weibo_id) ON DELETE CASCADE ON UPDATE CASCADE
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='情感分析结果表 - 存储词典+BERT混合分析结果（毕业设计：罗森 2022407443）'
PARTITION BY RANGE (TO_DAYS(analysis_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);


-- ============================================================================
-- 表3: dual_dimension_ranking - 双维度排序结果表
-- 描述: 存储情感-热度双维度排序结果（毕业设计核心创新点）
-- 核心公式: C_score = 0.6 × |sentiment_score| + 0.4 × popularity_score × time_decay
-- ============================================================================

DROP TABLE IF EXISTS dual_dimension_ranking;

CREATE TABLE dual_dimension_ranking (
    -- ==================== 主键 ====================
    id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '自增主键',
    weibo_id BIGINT UNSIGNED NOT NULL COMMENT '微博ID（关联weibo_core_data）',
    
    -- ==================== 情感维度 ====================
    sentiment_score DECIMAL(5,4) NOT NULL COMMENT '情感得分（-1到1）',
    sentiment_abs DECIMAL(5,4) GENERATED ALWAYS AS (ABS(sentiment_score)) STORED COMMENT '情感得分绝对值',
    sentiment_category ENUM('strong_positive', 'positive', 'neutral', 'negative', 'strong_negative') NOT NULL COMMENT '情感分类',
    sentiment_category_cn VARCHAR(16) GENERATED ALWAYS AS (
        CASE sentiment_category 
            WHEN 'strong_positive' THEN '强正面'
            WHEN 'positive' THEN '正面'
            WHEN 'neutral' THEN '中性'
            WHEN 'negative' THEN '负面'
            WHEN 'strong_negative' THEN '强负面'
        END
    ) STORED COMMENT '情感分类（中文）',
    
    -- ==================== 热度维度 ====================
    reposts_count INT UNSIGNED DEFAULT 0 COMMENT '转发数',
    comments_count INT UNSIGNED DEFAULT 0 COMMENT '评论数',
    attitudes_count INT UNSIGNED DEFAULT 0 COMMENT '点赞数',
    raw_popularity DECIMAL(12,4) COMMENT '原始热度值（未归一化）',
    popularity_score DECIMAL(8,4) NOT NULL COMMENT '归一化热度得分（0-1）',
    popularity_class ENUM('high', 'medium', 'low') NOT NULL COMMENT '热度分类',
    popularity_class_cn VARCHAR(8) GENERATED ALWAYS AS (
        CASE popularity_class 
            WHEN 'high' THEN '高热度'
            WHEN 'medium' THEN '中热度'
            WHEN 'low' THEN '低热度'
        END
    ) STORED COMMENT '热度分类（中文）',
    
    -- ==================== 时间衰减 ====================
    weibo_created_at DATETIME COMMENT '微博发布时间',
    hours_since_post INT UNSIGNED COMMENT '发布后小时数',
    time_decay DECIMAL(3,2) NOT NULL DEFAULT 1.00 COMMENT '时间衰减因子（0-1）',
    decay_half_life INT UNSIGNED DEFAULT 24 COMMENT '衰减半衰期（小时）',
    
    -- ==================== 综合评分（核心公式） ====================
    -- C_score = α × |sentiment_score| + β × popularity_score × time_decay
    alpha_weight DECIMAL(3,2) DEFAULT 0.60 COMMENT 'α权重（情感权重，默认0.6）',
    beta_weight DECIMAL(3,2) DEFAULT 0.40 COMMENT 'β权重（热度权重，默认0.4）',
    composite_score DECIMAL(8,4) NOT NULL COMMENT '综合评分（0-1）',
    
    -- ==================== 排名信息 ====================
    ranking_position INT UNSIGNED COMMENT '排名位次（在当前批次中）',
    ranking_percentile DECIMAL(5,2) COMMENT '排名百分位（0-100）',
    previous_ranking INT UNSIGNED COMMENT '上次排名',
    ranking_change INT COMMENT '排名变化（正数上升，负数下降）',
    
    -- ==================== 权重参数（JSON存储） ====================
    weight_params JSON COMMENT '权重参数详情（存储α,β,γ等参数）',
    
    -- ==================== 计算信息 ====================
    batch_id VARCHAR(64) COMMENT '计算批次ID',
    calculation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
    algorithm_version VARCHAR(50) DEFAULT 'v1.0.0' COMMENT '算法版本',
    calculation_note TEXT COMMENT '计算备注',
    
    -- ==================== 毕业设计标记 ====================
    graduation_flag TINYINT(1) DEFAULT 1 COMMENT '毕业设计数据标记',
    student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
    
    -- ==================== 主键和索引 ====================
    PRIMARY KEY (id, calculation_time),
    UNIQUE KEY uk_weibo_batch (weibo_id, batch_id),
    
    -- 综合评分索引（核心查询）
    KEY idx_composite_score (composite_score DESC),
    KEY idx_ranking_position (ranking_position),
    
    -- 维度索引
    KEY idx_sentiment_score (sentiment_score),
    KEY idx_sentiment_abs (sentiment_abs DESC),
    KEY idx_popularity_score (popularity_score DESC),
    KEY idx_time_decay (time_decay),
    
    -- 分类索引
    KEY idx_sentiment_category (sentiment_category),
    KEY idx_popularity_class (popularity_class),
    
    -- 时间索引
    KEY idx_calculation_time (calculation_time),
    KEY idx_batch_id (batch_id),
    
    -- 复合索引
    KEY idx_batch_ranking (batch_id, ranking_position),
    KEY idx_class_score (sentiment_category, composite_score DESC),
    KEY idx_popularity_sentiment (popularity_class, sentiment_category),
    
    -- 外键约束
    CONSTRAINT fk_ranking_weibo FOREIGN KEY (weibo_id) 
        REFERENCES weibo_core_data(weibo_id) ON DELETE CASCADE ON UPDATE CASCADE
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='双维度排序结果表 - 情感-热度双维度排序（毕业设计核心创新点：罗森 2022407443）'
PARTITION BY RANGE (TO_DAYS(calculation_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);


-- ============================================================================
-- 表4: crawl_batch_log - 爬虫批次日志表
-- 描述: 记录每次爬虫任务的执行情况
-- ============================================================================

DROP TABLE IF EXISTS crawl_batch_log;

CREATE TABLE crawl_batch_log (
    -- ==================== 主键 ====================
    batch_id VARCHAR(64) NOT NULL COMMENT '批次ID（主键）',
    
    -- ==================== 任务信息 ====================
    task_name VARCHAR(128) COMMENT '任务名称',
    task_type ENUM('hot_search', 'keyword_search', 'topic', 'user_timeline', 'realtime') DEFAULT 'keyword_search' COMMENT '任务类型',
    keywords JSON COMMENT '关键词列表（JSON数组）',
    target_count INT UNSIGNED DEFAULT 0 COMMENT '目标采集数量',
    
    -- ==================== 执行时间 ====================
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    duration_seconds INT UNSIGNED GENERATED ALWAYS AS (
        TIMESTAMPDIFF(SECOND, start_time, COALESCE(end_time, NOW()))
    ) STORED COMMENT '执行时长（秒）',
    
    -- ==================== 统计数据 ====================
    total_weibos INT UNSIGNED DEFAULT 0 COMMENT '采集微博总数',
    success_count INT UNSIGNED DEFAULT 0 COMMENT '成功数',
    failure_count INT UNSIGNED DEFAULT 0 COMMENT '失败数',
    duplicate_count INT UNSIGNED DEFAULT 0 COMMENT '重复数',
    success_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE WHEN total_weibos > 0 THEN success_count * 100.0 / total_weibos ELSE 0 END
    ) STORED COMMENT '成功率（%）',
    
    -- ==================== 性能数据 ====================
    total_requests INT UNSIGNED DEFAULT 0 COMMENT '总请求数',
    avg_response_time DECIMAL(8,2) COMMENT '平均响应时间（毫秒）',
    max_response_time INT UNSIGNED COMMENT '最大响应时间（毫秒）',
    min_response_time INT UNSIGNED COMMENT '最小响应时间（毫秒）',
    requests_per_minute DECIMAL(8,2) COMMENT '每分钟请求数',
    
    -- ==================== 状态信息 ====================
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled') DEFAULT 'pending' COMMENT '任务状态',
    error_message TEXT COMMENT '错误信息',
    retry_count INT UNSIGNED DEFAULT 0 COMMENT '重试次数',
    
    -- ==================== 配置信息 ====================
    config JSON COMMENT '任务配置（JSON格式）',
    cookies_used INT UNSIGNED DEFAULT 0 COMMENT '使用的Cookie数量',
    proxies_used INT UNSIGNED DEFAULT 0 COMMENT '使用的代理数量',
    
    -- ==================== 毕业设计标记 ====================
    graduation_batch TINYINT(1) DEFAULT 1 COMMENT '是否为毕业设计批次',
    student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
    
    -- ==================== 时间戳 ====================
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- ==================== 主键和索引 ====================
    PRIMARY KEY (batch_id),
    KEY idx_status (status),
    KEY idx_task_type (task_type),
    KEY idx_start_time (start_time),
    KEY idx_graduation_batch (graduation_batch),
    KEY idx_status_time (status, start_time)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='爬虫批次日志表 - 记录爬虫任务执行情况（毕业设计：罗森 2022407443）';


-- ============================================================================
-- 表5: crawl_request_log - 爬虫请求日志表
-- 描述: 记录每个HTTP请求的详细信息
-- ============================================================================

DROP TABLE IF EXISTS crawl_request_log;

CREATE TABLE crawl_request_log (
    -- ==================== 主键 ====================
    request_id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '请求ID（自增主键）',
    batch_id VARCHAR(64) NOT NULL COMMENT '批次ID（外键）',
    
    -- ==================== 请求信息 ====================
    url VARCHAR(1024) NOT NULL COMMENT '请求URL',
    method ENUM('GET', 'POST') DEFAULT 'GET' COMMENT '请求方法',
    params JSON COMMENT '请求参数',
    headers JSON COMMENT '请求头（脱敏）',
    
    -- ==================== 响应信息 ====================
    status_code INT COMMENT 'HTTP状态码',
    response_size INT UNSIGNED COMMENT '响应大小（字节）',
    content_type VARCHAR(128) COMMENT '响应内容类型',
    
    -- ==================== 时间信息 ====================
    request_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '请求时间',
    response_time INT UNSIGNED COMMENT '响应时间（毫秒）',
    
    -- ==================== 状态信息 ====================
    success TINYINT(1) DEFAULT 0 COMMENT '是否成功',
    error_type VARCHAR(64) COMMENT '错误类型',
    error_message TEXT COMMENT '错误信息',
    retry_count INT UNSIGNED DEFAULT 0 COMMENT '重试次数',
    
    -- ==================== 代理和Cookie ====================
    cookie_hash VARCHAR(64) COMMENT '使用的Cookie哈希值',
    proxy VARCHAR(128) COMMENT '使用的代理地址',
    user_agent VARCHAR(512) COMMENT 'User-Agent',
    
    -- ==================== 结果信息 ====================
    weibos_extracted INT UNSIGNED DEFAULT 0 COMMENT '提取的微博数',
    
    -- ==================== 主键和索引 ====================
    PRIMARY KEY (request_id, request_time),
    KEY idx_batch_id (batch_id),
    KEY idx_request_time (request_time),
    KEY idx_status_code (status_code),
    KEY idx_success (success),
    KEY idx_batch_success (batch_id, success),
    
    -- 外键约束
    CONSTRAINT fk_request_batch FOREIGN KEY (batch_id) 
        REFERENCES crawl_batch_log(batch_id) ON DELETE CASCADE ON UPDATE CASCADE
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='爬虫请求日志表 - 记录HTTP请求详情（毕业设计：罗森 2022407443）'
PARTITION BY RANGE (TO_DAYS(request_time)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01')),
    PARTITION p202606 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);


-- ============================================================================
-- 表6: data_quality_log - 数据质量日志表
-- 描述: 记录数据质量检查结果
-- ============================================================================

DROP TABLE IF EXISTS data_quality_log;

CREATE TABLE data_quality_log (
    -- ==================== 主键 ====================
    check_id BIGINT UNSIGNED AUTO_INCREMENT COMMENT '检查ID（自增主键）',
    batch_id VARCHAR(64) COMMENT '批次ID（外键，可为空表示全局检查）',
    
    -- ==================== 检查信息 ====================
    check_type ENUM('batch', 'daily', 'weekly', 'manual') DEFAULT 'batch' COMMENT '检查类型',
    check_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '检查时间',
    data_count INT UNSIGNED DEFAULT 0 COMMENT '检查数据量',
    
    -- ==================== 质量维度得分（0-1） ====================
    completeness_score DECIMAL(3,2) COMMENT '完整性得分（字段填充率）',
    accuracy_score DECIMAL(3,2) COMMENT '准确性得分（数据正确性）',
    consistency_score DECIMAL(3,2) COMMENT '一致性得分（数据一致性）',
    timeliness_score DECIMAL(3,2) COMMENT '及时性得分（数据新鲜度）',
    uniqueness_score DECIMAL(3,2) COMMENT '唯一性得分（重复率）',
    validity_score DECIMAL(3,2) COMMENT '有效性得分（格式正确性）',
    
    -- ==================== 综合得分 ====================
    overall_score DECIMAL(3,2) GENERATED ALWAYS AS (
        (COALESCE(completeness_score, 0) + COALESCE(accuracy_score, 0) + 
         COALESCE(consistency_score, 0) + COALESCE(timeliness_score, 0) + 
         COALESCE(uniqueness_score, 0) + COALESCE(validity_score, 0)) / 6
    ) STORED COMMENT '综合质量得分',
    quality_level ENUM('excellent', 'good', 'fair', 'poor') GENERATED ALWAYS AS (
        CASE 
            WHEN overall_score >= 0.9 THEN 'excellent'
            WHEN overall_score >= 0.7 THEN 'good'
            WHEN overall_score >= 0.5 THEN 'fair'
            ELSE 'poor'
        END
    ) STORED COMMENT '质量等级',
    
    -- ==================== 问题详情 ====================
    issues JSON COMMENT '发现的问题详情（JSON格式）',
    issue_count INT UNSIGNED DEFAULT 0 COMMENT '问题数量',
    critical_issues INT UNSIGNED DEFAULT 0 COMMENT '严重问题数',
    
    -- ==================== 建议和备注 ====================
    recommendations JSON COMMENT '改进建议',
    note TEXT COMMENT '备注',
    
    -- ==================== 毕业设计标记 ====================
    graduation_check TINYINT(1) DEFAULT 1 COMMENT '毕业设计检查标记',
    student_id VARCHAR(20) DEFAULT '2022407443' COMMENT '学生学号',
    
    -- ==================== 主键和索引 ====================
    PRIMARY KEY (check_id),
    KEY idx_batch_id (batch_id),
    KEY idx_check_time (check_time),
    KEY idx_overall_score (overall_score),
    KEY idx_quality_level (quality_level),
    KEY idx_check_type (check_type),
    
    -- 外键约束（可选，因为batch_id可为空）
    CONSTRAINT fk_quality_batch FOREIGN KEY (batch_id) 
        REFERENCES crawl_batch_log(batch_id) ON DELETE SET NULL ON UPDATE CASCADE
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='数据质量日志表 - 记录数据质量检查结果（毕业设计：罗森 2022407443）';


-- ============================================================================
-- 触发器定义
-- ============================================================================

DELIMITER //

-- -----------------------------------------------------------------------------
-- 触发器1: 情感分析完成后更新微博处理状态
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_sentiment_update_weibo_status
AFTER INSERT ON sentiment_analysis_results
FOR EACH ROW
BEGIN
    UPDATE weibo_core_data 
    SET is_processed = 1,
        last_updated = NOW()
    WHERE weibo_id = NEW.weibo_id;
END//

-- -----------------------------------------------------------------------------
-- 触发器2: 双维度排序完成后更新微博排序状态
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_ranking_update_weibo_status
AFTER INSERT ON dual_dimension_ranking
FOR EACH ROW
BEGIN
    UPDATE weibo_core_data 
    SET is_ranked = 1,
        last_updated = NOW()
    WHERE weibo_id = NEW.weibo_id;
END//

-- -----------------------------------------------------------------------------
-- 触发器3: 自动计算综合评分（插入前）
-- 公式: C_score = α × |sentiment_score| + β × popularity_score × time_decay
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_calculate_composite_score
BEFORE INSERT ON dual_dimension_ranking
FOR EACH ROW
BEGIN
    -- 如果未提供综合评分，自动计算
    IF NEW.composite_score IS NULL OR NEW.composite_score = 0 THEN
        SET NEW.composite_score = 
            NEW.alpha_weight * ABS(NEW.sentiment_score) + 
            NEW.beta_weight * NEW.popularity_score * NEW.time_decay;
    END IF;
    
    -- 自动设置情感分类
    IF NEW.sentiment_category IS NULL THEN
        SET NEW.sentiment_category = CASE
            WHEN NEW.sentiment_score >= 0.6 THEN 'strong_positive'
            WHEN NEW.sentiment_score >= 0.2 THEN 'positive'
            WHEN NEW.sentiment_score > -0.2 THEN 'neutral'
            WHEN NEW.sentiment_score > -0.6 THEN 'negative'
            ELSE 'strong_negative'
        END;
    END IF;
    
    -- 自动设置热度分类
    IF NEW.popularity_class IS NULL THEN
        SET NEW.popularity_class = CASE
            WHEN NEW.popularity_score >= 0.7 THEN 'high'
            WHEN NEW.popularity_score >= 0.3 THEN 'medium'
            ELSE 'low'
        END;
    END IF;
END//

-- -----------------------------------------------------------------------------
-- 触发器4: 爬虫批次完成时更新统计
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_batch_completed_stats
BEFORE UPDATE ON crawl_batch_log
FOR EACH ROW
BEGIN
    -- 当状态变为completed时，计算成功率等
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        SET NEW.end_time = COALESCE(NEW.end_time, NOW());
    END IF;
END//

-- -----------------------------------------------------------------------------
-- 触发器5: 情感分析结果自动设置分析时间
-- -----------------------------------------------------------------------------
CREATE TRIGGER tr_sentiment_auto_time
BEFORE INSERT ON sentiment_analysis_results
FOR EACH ROW
BEGIN
    IF NEW.analysis_time IS NULL THEN
        SET NEW.analysis_time = NOW();
    END IF;
    
    -- 自动计算情感强度
    IF NEW.intensity IS NULL OR NEW.intensity = 0 THEN
        SET NEW.intensity = ABS(NEW.hybrid_score);
    END IF;
END//

DELIMITER ;


-- ============================================================================
-- 视图定义
-- ============================================================================

-- -----------------------------------------------------------------------------
-- 视图1: v_sentiment_distribution - 情感分布统计视图
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_sentiment_distribution AS
SELECT 
    sentiment_class,
    sentiment_class_cn,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM sentiment_analysis_results), 2) AS percentage,
    ROUND(AVG(hybrid_score), 4) AS avg_score,
    ROUND(AVG(confidence), 4) AS avg_confidence,
    ROUND(AVG(intensity), 4) AS avg_intensity,
    MIN(analysis_time) AS first_analysis,
    MAX(analysis_time) AS last_analysis
FROM sentiment_analysis_results
WHERE graduation_flag = 1
GROUP BY sentiment_class, sentiment_class_cn
ORDER BY count DESC;

-- -----------------------------------------------------------------------------
-- 视图2: v_top100_weibos - 热门微博TOP100视图
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_top100_weibos AS
SELECT 
    d.ranking_position,
    d.weibo_id,
    w.content,
    w.user_name,
    w.verified,
    d.sentiment_score,
    d.sentiment_category_cn,
    d.popularity_score,
    d.popularity_class_cn,
    d.time_decay,
    d.composite_score,
    w.reposts_count,
    w.comments_count,
    w.attitudes_count,
    w.created_at AS weibo_time,
    d.calculation_time
FROM dual_dimension_ranking d
JOIN weibo_core_data w ON d.weibo_id = w.weibo_id
WHERE d.graduation_flag = 1
ORDER BY d.composite_score DESC
LIMIT 100;

-- -----------------------------------------------------------------------------
-- 视图3: v_crawl_performance - 爬虫性能监控视图
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_crawl_performance AS
SELECT 
    b.batch_id,
    b.task_name,
    b.task_type,
    b.status,
    b.total_weibos,
    b.success_count,
    b.failure_count,
    b.success_rate,
    b.avg_response_time,
    b.duration_seconds,
    ROUND(b.total_weibos * 60.0 / NULLIF(b.duration_seconds, 0), 2) AS weibos_per_minute,
    b.start_time,
    b.end_time,
    (SELECT COUNT(*) FROM crawl_request_log r WHERE r.batch_id = b.batch_id) AS total_requests,
    (SELECT COUNT(*) FROM crawl_request_log r WHERE r.batch_id = b.batch_id AND r.success = 1) AS successful_requests
FROM crawl_batch_log b
WHERE b.graduation_batch = 1
ORDER BY b.start_time DESC;

-- -----------------------------------------------------------------------------
-- 视图4: v_data_quality_trend - 数据质量趋势视图
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_data_quality_trend AS
SELECT 
    DATE(check_time) AS check_date,
    COUNT(*) AS check_count,
    ROUND(AVG(completeness_score), 4) AS avg_completeness,
    ROUND(AVG(accuracy_score), 4) AS avg_accuracy,
    ROUND(AVG(consistency_score), 4) AS avg_consistency,
    ROUND(AVG(timeliness_score), 4) AS avg_timeliness,
    ROUND(AVG(uniqueness_score), 4) AS avg_uniqueness,
    ROUND(AVG(overall_score), 4) AS avg_overall,
    SUM(issue_count) AS total_issues,
    SUM(critical_issues) AS total_critical
FROM data_quality_log
WHERE graduation_check = 1
GROUP BY DATE(check_time)
ORDER BY check_date DESC;

-- -----------------------------------------------------------------------------
-- 视图5: v_graduation_summary - 毕业设计数据汇总视图
-- -----------------------------------------------------------------------------
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
    (SELECT COUNT(DISTINCT keyword) FROM weibo_core_data WHERE graduation_batch = 1 AND keyword IS NOT NULL) AS total_keywords,
    (SELECT COUNT(*) FROM sentiment_analysis_results WHERE graduation_flag = 1) AS analyzed_count,
    (SELECT COUNT(*) FROM dual_dimension_ranking WHERE graduation_flag = 1) AS ranked_count,
    (SELECT COUNT(*) FROM crawl_batch_log WHERE graduation_batch = 1) AS total_batches,
    (SELECT ROUND(AVG(overall_score), 4) FROM data_quality_log WHERE graduation_check = 1) AS avg_data_quality,
    NOW() AS generated_at;


-- ============================================================================
-- 存储过程定义
-- ============================================================================

DELIMITER //

-- -----------------------------------------------------------------------------
-- 存储过程1: sp_batch_import_sentiment - 批量导入情感分析结果
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_batch_import_sentiment(
    IN p_batch_size INT
)
BEGIN
    DECLARE v_imported INT DEFAULT 0;
    DECLARE v_start_time DATETIME;
    
    SET v_start_time = NOW();
    
    -- 这里是批量导入的逻辑框架
    -- 实际使用时通过应用程序调用
    
    SELECT CONCAT('批量导入完成，共导入 ', v_imported, ' 条记录，耗时 ', 
                  TIMESTAMPDIFF(SECOND, v_start_time, NOW()), ' 秒') AS result;
END//

-- -----------------------------------------------------------------------------
-- 存储过程2: sp_calculate_rankings - 计算双维度排名
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_calculate_rankings(
    IN p_batch_id VARCHAR(64)
)
BEGIN
    DECLARE v_rank INT DEFAULT 0;
    
    -- 更新排名位次
    SET @rank := 0;
    
    UPDATE dual_dimension_ranking d
    SET ranking_position = (@rank := @rank + 1)
    WHERE (p_batch_id IS NULL OR d.batch_id = p_batch_id)
    ORDER BY d.composite_score DESC;
    
    -- 计算排名百分位
    UPDATE dual_dimension_ranking d
    SET ranking_percentile = ROUND(
        (1 - (ranking_position - 1) / 
         (SELECT COUNT(*) FROM dual_dimension_ranking WHERE batch_id = d.batch_id)) * 100, 2
    )
    WHERE p_batch_id IS NULL OR d.batch_id = p_batch_id;
    
    SELECT CONCAT('排名计算完成，批次: ', COALESCE(p_batch_id, '全部')) AS result;
END//

-- -----------------------------------------------------------------------------
-- 存储过程3: sp_crawl_performance_report - 生成爬虫性能报告
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_crawl_performance_report(
    IN p_start_date DATE,
    IN p_end_date DATE
)
BEGIN
    SELECT 
        COUNT(*) AS total_batches,
        SUM(total_weibos) AS total_weibos,
        SUM(success_count) AS total_success,
        SUM(failure_count) AS total_failures,
        ROUND(AVG(success_rate), 2) AS avg_success_rate,
        ROUND(AVG(avg_response_time), 2) AS avg_response_time,
        SUM(duration_seconds) AS total_duration,
        ROUND(SUM(total_weibos) / NULLIF(SUM(duration_seconds), 0) * 60, 2) AS overall_speed
    FROM crawl_batch_log
    WHERE graduation_batch = 1
    AND DATE(start_time) BETWEEN COALESCE(p_start_date, '2020-01-01') 
                             AND COALESCE(p_end_date, CURDATE());
END//

-- -----------------------------------------------------------------------------
-- 存储过程4: sp_cleanup_old_logs - 清理旧日志
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_cleanup_old_logs(
    IN p_days_to_keep INT
)
BEGIN
    DECLARE v_cutoff_date DATETIME;
    DECLARE v_deleted_requests INT DEFAULT 0;
    DECLARE v_deleted_quality INT DEFAULT 0;
    
    SET v_cutoff_date = DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY);
    
    -- 清理请求日志（保留毕业设计数据）
    DELETE FROM crawl_request_log 
    WHERE request_time < v_cutoff_date
    AND batch_id NOT IN (SELECT batch_id FROM crawl_batch_log WHERE graduation_batch = 1);
    SET v_deleted_requests = ROW_COUNT();
    
    -- 清理质量日志
    DELETE FROM data_quality_log 
    WHERE check_time < v_cutoff_date
    AND graduation_check = 0;
    SET v_deleted_quality = ROW_COUNT();
    
    SELECT CONCAT('清理完成: 删除请求日志 ', v_deleted_requests, ' 条, 质量日志 ', v_deleted_quality, ' 条') AS result;
END//

-- -----------------------------------------------------------------------------
-- 存储过程5: sp_graduation_statistics - 生成毕业设计统计
-- -----------------------------------------------------------------------------
CREATE PROCEDURE sp_graduation_statistics()
BEGIN
    -- 基础统计
    SELECT '=== 毕业设计数据统计 ===' AS section;
    SELECT * FROM v_graduation_summary;
    
    -- 情感分布
    SELECT '=== 情感分布统计 ===' AS section;
    SELECT * FROM v_sentiment_distribution;
    
    -- 热门微博
    SELECT '=== TOP10热门微博 ===' AS section;
    SELECT * FROM v_top100_weibos LIMIT 10;
    
    -- 爬虫性能
    SELECT '=== 爬虫性能统计 ===' AS section;
    SELECT * FROM v_crawl_performance LIMIT 10;
    
    -- 数据质量
    SELECT '=== 数据质量趋势 ===' AS section;
    SELECT * FROM v_data_quality_trend LIMIT 7;
END//

DELIMITER ;


-- ============================================================================
-- 定时事件（自动清理旧日志）
-- ============================================================================

-- 启用事件调度器
SET GLOBAL event_scheduler = ON;

-- 创建每周清理事件
CREATE EVENT IF NOT EXISTS evt_weekly_cleanup
ON SCHEDULE EVERY 1 WEEK
STARTS CURRENT_TIMESTAMP
DO
    CALL sp_cleanup_old_logs(30);  -- 保留30天日志


-- ============================================================================
-- 完成提示
-- ============================================================================

SELECT '核心数据表创建完成！' AS message;
SELECT 
    TABLE_NAME AS '表名',
    TABLE_COMMENT AS '说明'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'weibo_sentiment_graduation'
AND TABLE_NAME IN ('weibo_core_data', 'sentiment_analysis_results', 
                   'dual_dimension_ranking', 'crawl_batch_log', 
                   'crawl_request_log', 'data_quality_log');
