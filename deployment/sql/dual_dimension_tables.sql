-- ============================================================
-- 情感-热度双维度排序模型 数据库表设计
-- 数据库: weibo_sentiment
-- 作者: 毕业设计
-- 日期: 2024-12
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS weibo_sentiment 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE weibo_sentiment;

-- ============================================================
-- 1. 微博用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS weibo_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    user_id VARCHAR(64) NOT NULL COMMENT '微博用户ID',
    screen_name VARCHAR(100) COMMENT '用户昵称',
    followers_count INT DEFAULT 0 COMMENT '粉丝数',
    friends_count INT DEFAULT 0 COMMENT '关注数',
    statuses_count INT DEFAULT 0 COMMENT '微博数',
    verified TINYINT(1) DEFAULT 0 COMMENT '是否认证 0-否 1-是',
    verified_type TINYINT DEFAULT -1 COMMENT '认证类型 -1:未认证 0:个人 1:企业 2:政府 3:媒体',
    verified_reason VARCHAR(255) COMMENT '认证原因',
    description TEXT COMMENT '用户简介',
    gender VARCHAR(10) COMMENT '性别',
    location VARCHAR(100) COMMENT '所在地',
    profile_url VARCHAR(255) COMMENT '主页链接',
    avatar_url VARCHAR(255) COMMENT '头像链接',
    influence_score DECIMAL(10,4) DEFAULT 0 COMMENT '影响力得分',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_user_id (user_id),
    INDEX idx_followers (followers_count),
    INDEX idx_verified (verified, verified_type),
    INDEX idx_influence (influence_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微博用户表';


-- ============================================================
-- 2. 微博帖子表
-- ============================================================
CREATE TABLE IF NOT EXISTS weibo_post (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博ID',
    mid VARCHAR(64) COMMENT '微博MID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    text TEXT NOT NULL COMMENT '微博正文',
    text_length INT COMMENT '文本长度',
    source VARCHAR(100) COMMENT '来源设备',
    
    -- 互动数据
    reposts_count INT DEFAULT 0 COMMENT '转发数',
    comments_count INT DEFAULT 0 COMMENT '评论数',
    attitudes_count INT DEFAULT 0 COMMENT '点赞数',
    
    -- 媒体数据
    pics_count INT DEFAULT 0 COMMENT '图片数量',
    has_video TINYINT(1) DEFAULT 0 COMMENT '是否有视频',
    
    -- 时间数据
    publish_time DATETIME NOT NULL COMMENT '发布时间',
    crawl_time DATETIME COMMENT '爬取时间',
    
    -- 关键词和话题
    keywords VARCHAR(500) COMMENT '关键词(JSON数组)',
    topics VARCHAR(500) COMMENT '话题标签(JSON数组)',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_weibo_id (weibo_id),
    INDEX idx_user_id (user_id),
    INDEX idx_publish_time (publish_time),
    INDEX idx_reposts (reposts_count),
    INDEX idx_comments (comments_count),
    INDEX idx_attitudes (attitudes_count),
    
    FOREIGN KEY (user_id) REFERENCES weibo_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='微博帖子表';


-- ============================================================
-- 3. 情感分析结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS sentiment_result (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博ID',
    
    -- 情感分析结果
    sentiment_polarity VARCHAR(20) NOT NULL COMMENT '情感极性: positive/neutral/negative',
    sentiment_score DECIMAL(6,4) NOT NULL COMMENT '情感得分 [-1, 1]',
    sentiment_intensity DECIMAL(6,2) NOT NULL COMMENT '情感强度 [0, 100]',
    
    -- 分析方法
    analysis_method VARCHAR(50) DEFAULT 'lexicon' COMMENT '分析方法: lexicon/bert/hybrid',
    lexicon_score DECIMAL(6,4) COMMENT '词典方法得分',
    dl_score DECIMAL(6,4) COMMENT '深度学习得分',
    dl_confidence DECIMAL(6,4) COMMENT '深度学习置信度',
    
    -- 细粒度情绪(JSON格式)
    emotions JSON COMMENT '细粒度情绪分布',
    
    -- 关键情感词
    sentiment_words VARCHAR(500) COMMENT '情感关键词(JSON数组)',
    
    analysis_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '分析时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    UNIQUE KEY uk_weibo_id (weibo_id),
    INDEX idx_polarity (sentiment_polarity),
    INDEX idx_score (sentiment_score),
    INDEX idx_intensity (sentiment_intensity),
    INDEX idx_method (analysis_method),
    
    FOREIGN KEY (weibo_id) REFERENCES weibo_post(weibo_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情感分析结果表';


-- ============================================================
-- 4. 热度计算结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS heat_result (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博ID',
    
    -- 热度得分
    heat_score DECIMAL(10,4) NOT NULL COMMENT '热度综合得分',
    interaction_score DECIMAL(10,4) COMMENT '互动得分',
    
    -- 各因子得分
    time_decay_factor DECIMAL(6,4) COMMENT '时间衰减因子',
    influence_factor DECIMAL(6,4) COMMENT '用户影响力因子',
    
    -- 归一化得分
    heat_normalized DECIMAL(6,4) COMMENT '归一化热度 [0, 1]',
    
    -- 计算参数
    repost_weight DECIMAL(4,2) DEFAULT 3.0 COMMENT '转发权重',
    comment_weight DECIMAL(4,2) DEFAULT 2.0 COMMENT '评论权重',
    like_weight DECIMAL(4,2) DEFAULT 1.0 COMMENT '点赞权重',
    decay_half_life DECIMAL(6,2) DEFAULT 24.0 COMMENT '衰减半衰期(小时)',
    
    reference_time DATETIME COMMENT '参考时间点',
    calculation_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    UNIQUE KEY uk_weibo_id (weibo_id),
    INDEX idx_heat_score (heat_score),
    INDEX idx_heat_normalized (heat_normalized),
    
    FOREIGN KEY (weibo_id) REFERENCES weibo_post(weibo_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='热度计算结果表';


-- ============================================================
-- 5. 双维度排序结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS dual_dimension_result (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    weibo_id VARCHAR(64) NOT NULL COMMENT '微博ID',
    task_id VARCHAR(64) COMMENT '分析任务ID',
    
    -- 双维度得分
    dual_score DECIMAL(6,4) NOT NULL COMMENT '双维度综合得分 [0, 1]',
    sentiment_normalized DECIMAL(6,4) COMMENT '归一化情感得分 [0, 1]',
    heat_normalized DECIMAL(6,4) COMMENT '归一化热度得分 [0, 1]',
    
    -- 四象限分类
    quadrant VARCHAR(50) NOT NULL COMMENT '四象限分类',
    quadrant_label VARCHAR(50) COMMENT '四象限中文标签',
    
    -- 排名
    rank_position INT COMMENT '排名位置',
    rank_percentile DECIMAL(6,4) COMMENT '排名百分位',
    
    -- 权重配置
    sentiment_weight DECIMAL(4,2) DEFAULT 0.5 COMMENT '情感权重 α',
    heat_weight DECIMAL(4,2) DEFAULT 0.5 COMMENT '热度权重 β',
    
    -- 阈值配置
    sentiment_threshold DECIMAL(4,2) DEFAULT 0.5 COMMENT '情感阈值',
    heat_threshold DECIMAL(4,2) DEFAULT 0.5 COMMENT '热度阈值',
    
    calculation_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    UNIQUE KEY uk_weibo_task (weibo_id, task_id),
    INDEX idx_dual_score (dual_score),
    INDEX idx_quadrant (quadrant),
    INDEX idx_rank (rank_position),
    INDEX idx_task (task_id),
    
    FOREIGN KEY (weibo_id) REFERENCES weibo_post(weibo_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='双维度排序结果表';


-- ============================================================
-- 6. 分析任务表
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    task_name VARCHAR(100) COMMENT '任务名称',
    task_type VARCHAR(50) DEFAULT 'dual_dimension' COMMENT '任务类型',
    
    -- 任务状态
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/running/completed/failed',
    progress INT DEFAULT 0 COMMENT '进度百分比',
    
    -- 任务配置(JSON)
    config JSON COMMENT '任务配置参数',
    
    -- 数据范围
    data_source VARCHAR(50) COMMENT '数据来源',
    start_time DATETIME COMMENT '数据开始时间',
    end_time DATETIME COMMENT '数据结束时间',
    keywords VARCHAR(500) COMMENT '关键词列表',
    
    -- 统计信息
    total_count INT DEFAULT 0 COMMENT '总数据量',
    processed_count INT DEFAULT 0 COMMENT '已处理数量',
    success_count INT DEFAULT 0 COMMENT '成功数量',
    failed_count INT DEFAULT 0 COMMENT '失败数量',
    
    -- 结果统计(JSON)
    result_statistics JSON COMMENT '结果统计信息',
    
    -- 时间信息
    scheduled_time DATETIME COMMENT '计划执行时间',
    start_execution_time DATETIME COMMENT '开始执行时间',
    end_execution_time DATETIME COMMENT '结束执行时间',
    
    error_message TEXT COMMENT '错误信息',
    
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_type (task_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析任务表';


-- ============================================================
-- 7. 模型配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS model_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    config_name VARCHAR(100) NOT NULL COMMENT '配置名称',
    config_type VARCHAR(50) DEFAULT 'dual_dimension' COMMENT '配置类型',
    is_default TINYINT(1) DEFAULT 0 COMMENT '是否默认配置',
    
    -- 情感维度配置
    sentiment_weight DECIMAL(4,2) DEFAULT 0.5 COMMENT '情感权重',
    use_deep_learning TINYINT(1) DEFAULT 1 COMMENT '是否使用深度学习',
    lexicon_weight DECIMAL(4,2) DEFAULT 0.4 COMMENT '词典方法权重',
    dl_weight DECIMAL(4,2) DEFAULT 0.6 COMMENT '深度学习权重',
    
    -- 热度维度配置
    heat_weight DECIMAL(4,2) DEFAULT 0.5 COMMENT '热度权重',
    repost_weight DECIMAL(4,2) DEFAULT 3.0 COMMENT '转发权重',
    comment_weight DECIMAL(4,2) DEFAULT 2.0 COMMENT '评论权重',
    like_weight DECIMAL(4,2) DEFAULT 1.0 COMMENT '点赞权重',
    
    -- 时间衰减配置
    time_decay_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用时间衰减',
    decay_half_life_hours DECIMAL(6,2) DEFAULT 24.0 COMMENT '衰减半衰期',
    
    -- 影响力配置
    influence_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用影响力因子',
    follower_log_base DECIMAL(4,2) DEFAULT 10.0 COMMENT '粉丝数对数底数',
    verified_bonus DECIMAL(4,2) DEFAULT 1.5 COMMENT '认证用户加成',
    
    -- 四象限阈值
    sentiment_threshold DECIMAL(4,2) DEFAULT 0.5 COMMENT '情感阈值',
    heat_threshold DECIMAL(4,2) DEFAULT 0.5 COMMENT '热度阈值',
    
    -- 归一化配置
    max_heat_value DECIMAL(12,2) DEFAULT 100000.0 COMMENT '热度归一化最大值',
    
    description TEXT COMMENT '配置描述',
    
    created_by VARCHAR(64) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_config_name (config_name),
    INDEX idx_type (config_type),
    INDEX idx_default (is_default)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型配置表';


-- ============================================================
-- 8. 四象限统计表
-- ============================================================
CREATE TABLE IF NOT EXISTS quadrant_statistics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    statistics_time DATETIME NOT NULL COMMENT '统计时间',
    
    -- 各象限统计
    high_sentiment_high_heat_count INT DEFAULT 0 COMMENT '高情感高热度数量',
    high_sentiment_high_heat_ratio DECIMAL(6,4) DEFAULT 0 COMMENT '高情感高热度占比',
    
    high_sentiment_low_heat_count INT DEFAULT 0 COMMENT '高情感低热度数量',
    high_sentiment_low_heat_ratio DECIMAL(6,4) DEFAULT 0 COMMENT '高情感低热度占比',
    
    low_sentiment_high_heat_count INT DEFAULT 0 COMMENT '低情感高热度数量',
    low_sentiment_high_heat_ratio DECIMAL(6,4) DEFAULT 0 COMMENT '低情感高热度占比',
    
    low_sentiment_low_heat_count INT DEFAULT 0 COMMENT '低情感低热度数量',
    low_sentiment_low_heat_ratio DECIMAL(6,4) DEFAULT 0 COMMENT '低情感低热度占比',
    
    -- 汇总统计
    total_count INT DEFAULT 0 COMMENT '总数量',
    avg_dual_score DECIMAL(6,4) COMMENT '平均双维度得分',
    avg_sentiment_score DECIMAL(6,4) COMMENT '平均情感得分',
    avg_heat_score DECIMAL(10,4) COMMENT '平均热度得分',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_task (task_id),
    INDEX idx_time (statistics_time),
    
    FOREIGN KEY (task_id) REFERENCES analysis_task(task_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='四象限统计表';


-- ============================================================
-- 初始化默认配置
-- ============================================================
INSERT INTO model_config (
    config_name, config_type, is_default,
    sentiment_weight, heat_weight,
    repost_weight, comment_weight, like_weight,
    time_decay_enabled, decay_half_life_hours,
    influence_enabled, verified_bonus,
    sentiment_threshold, heat_threshold,
    description
) VALUES (
    '默认配置', 'dual_dimension', 1,
    0.5, 0.5,
    3.0, 2.0, 1.0,
    1, 24.0,
    1, 1.5,
    0.5, 0.5,
    '系统默认的双维度排序配置'
), (
    '情感优先', 'dual_dimension', 0,
    0.7, 0.3,
    3.0, 2.0, 1.0,
    1, 24.0,
    1, 1.5,
    0.5, 0.5,
    '侧重情感分析的配置，适用于舆情监控'
), (
    '热度优先', 'dual_dimension', 0,
    0.3, 0.7,
    3.0, 2.0, 1.0,
    1, 12.0,
    1, 1.8,
    0.5, 0.5,
    '侧重热度分析的配置，适用于热点追踪'
);


-- ============================================================
-- 创建视图：双维度分析综合视图
-- ============================================================
CREATE OR REPLACE VIEW v_dual_dimension_analysis AS
SELECT 
    p.weibo_id,
    p.text,
    p.publish_time,
    p.reposts_count,
    p.comments_count,
    p.attitudes_count,
    u.screen_name AS user_name,
    u.followers_count,
    u.verified,
    u.verified_type,
    s.sentiment_polarity,
    s.sentiment_score,
    s.sentiment_intensity,
    h.heat_score,
    h.heat_normalized,
    h.time_decay_factor,
    h.influence_factor,
    d.dual_score,
    d.quadrant,
    d.rank_position
FROM weibo_post p
LEFT JOIN weibo_user u ON p.user_id = u.user_id
LEFT JOIN sentiment_result s ON p.weibo_id = s.weibo_id
LEFT JOIN heat_result h ON p.weibo_id = h.weibo_id
LEFT JOIN dual_dimension_result d ON p.weibo_id = d.weibo_id;


-- ============================================================
-- 创建存储过程：获取四象限分布
-- ============================================================
DELIMITER //

CREATE PROCEDURE sp_get_quadrant_distribution(
    IN p_task_id VARCHAR(64),
    IN p_start_time DATETIME,
    IN p_end_time DATETIME
)
BEGIN
    SELECT 
        quadrant,
        COUNT(*) AS count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage,
        ROUND(AVG(dual_score), 4) AS avg_dual_score,
        ROUND(AVG(sentiment_normalized), 4) AS avg_sentiment,
        ROUND(AVG(heat_normalized), 4) AS avg_heat
    FROM dual_dimension_result d
    JOIN weibo_post p ON d.weibo_id = p.weibo_id
    WHERE (p_task_id IS NULL OR d.task_id = p_task_id)
      AND (p_start_time IS NULL OR p.publish_time >= p_start_time)
      AND (p_end_time IS NULL OR p.publish_time <= p_end_time)
    GROUP BY quadrant
    ORDER BY 
        CASE quadrant
            WHEN 'high_sentiment_high_heat' THEN 1
            WHEN 'high_sentiment_low_heat' THEN 2
            WHEN 'low_sentiment_high_heat' THEN 3
            WHEN 'low_sentiment_low_heat' THEN 4
        END;
END //

DELIMITER ;


-- ============================================================
-- 创建存储过程：获取Top-N排名
-- ============================================================
DELIMITER //

CREATE PROCEDURE sp_get_top_ranked(
    IN p_task_id VARCHAR(64),
    IN p_limit INT,
    IN p_quadrant VARCHAR(50)
)
BEGIN
    SELECT 
        d.rank_position,
        p.weibo_id,
        SUBSTRING(p.text, 1, 100) AS text_preview,
        u.screen_name AS user_name,
        u.followers_count,
        d.dual_score,
        d.sentiment_normalized,
        d.heat_normalized,
        d.quadrant,
        s.sentiment_polarity,
        p.reposts_count,
        p.comments_count,
        p.attitudes_count,
        p.publish_time
    FROM dual_dimension_result d
    JOIN weibo_post p ON d.weibo_id = p.weibo_id
    JOIN weibo_user u ON p.user_id = u.user_id
    LEFT JOIN sentiment_result s ON p.weibo_id = s.weibo_id
    WHERE (p_task_id IS NULL OR d.task_id = p_task_id)
      AND (p_quadrant IS NULL OR d.quadrant = p_quadrant)
    ORDER BY d.dual_score DESC
    LIMIT p_limit;
END //

DELIMITER ;


-- 完成提示
SELECT '数据库表创建完成！' AS message;
