-- ===================================================================
-- 02_create_tables.sql: Create Table Structures
-- ===================================================================

USE `weibo_sentiment_db`;

-- Table: users - Stores user account information.
CREATE TABLE IF NOT EXISTS `users` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary Key',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Unique username for login',
    `password` VARCHAR(255) NOT NULL COMMENT 'Hashed password',
    `email` VARCHAR(100) UNIQUE COMMENT 'User email, can be used for login or notifications',
    `phone` VARCHAR(20) UNIQUE COMMENT 'User phone number',
    `avatar` VARCHAR(255) DEFAULT NULL COMMENT 'URL to user avatar image',
    `roles` VARCHAR(100) NOT NULL DEFAULT 'ROLE_USER' COMMENT 'Comma-separated list of user roles (e.g., ROLE_USER,ROLE_ADMIN)',
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT 'Account status: 1=Active, 2=Locked, 3=Disabled',
    `last_login_time` DATETIME DEFAULT NULL COMMENT 'Timestamp of the last successful login',
    `login_fail_count` INT NOT NULL DEFAULT 0 COMMENT 'Count of consecutive failed login attempts',
    `version` INT NOT NULL DEFAULT 1 COMMENT 'Data version for optimistic locking',
    `is_deleted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Flag for soft delete',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp of creation',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Timestamp of last update'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User accounts table';

-- Table: collection_tasks - Manages data collection tasks.
CREATE TABLE IF NOT EXISTS `collection_tasks` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary Key',
    `name` VARCHAR(100) NOT NULL COMMENT 'Name of the collection task',
    `type` VARCHAR(50) NOT NULL COMMENT 'Task type (e.g., KEYWORD, USER_TIMELINE)',
    `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT 'Task status: PENDING, RUNNING, COMPLETED, FAILED, PAUSED',
    `progress` DECIMAL(5, 2) NOT NULL DEFAULT 0.00 COMMENT 'Task completion progress (0.00 to 100.00)',
    `keywords` TEXT COMMENT 'Keywords or criteria for data collection',
    `start_time` DATETIME COMMENT 'Scheduled start time for the task',
    `end_time` DATETIME COMMENT 'Scheduled end time for the task',
    `schedule_config` VARCHAR(255) COMMENT 'Scheduling configuration (e.g., CRON expression)',
    `data_source` VARCHAR(50) NOT NULL DEFAULT 'Weibo' COMMENT 'Source of the data (e.g., Weibo, Twitter)',
    `output_format` VARCHAR(20) DEFAULT 'DATABASE' COMMENT 'Output format (e.g., DATABASE, CSV, JSON)',
    `max_records` BIGINT DEFAULT 0 COMMENT 'Maximum number of records to collect (0 for unlimited)',
    `version` INT NOT NULL DEFAULT 1 COMMENT 'Data version for optimistic locking',
    `is_deleted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Flag for soft delete',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp of creation',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Timestamp of last update'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Data collection tasks table';

-- Table: sentiment_results - Stores the results of sentiment analysis.
CREATE TABLE IF NOT EXISTS `sentiment_results` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary Key',
    `task_id` BIGINT NOT NULL COMMENT 'Foreign key linking to the collection task',
    `weibo_id` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Unique ID of the Weibo post',
    `content` TEXT NOT NULL COMMENT 'Original content of the Weibo post',
    `clean_content` TEXT COMMENT 'Cleaned content used for analysis',
    `sentiment_score` DECIMAL(10, 8) NOT NULL COMMENT 'Calculated sentiment score',
    `sentiment_label` VARCHAR(20) NOT NULL COMMENT 'Sentiment label (e.g., Positive, Negative, Neutral)',
    `confidence` DECIMAL(5, 4) COMMENT 'Confidence level of the analysis (0.0000 to 1.0000)',
    `keywords` VARCHAR(255) COMMENT 'Extracted keywords from the content',
    `features` JSON COMMENT 'Additional features or metadata from the analysis',
    `hotness_score` INT DEFAULT 0 COMMENT 'Calculated hotness or popularity score',
    `analysis_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp when the analysis was performed',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp of creation'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sentiment analysis results table';

-- Table: system_configs - Stores system-level configurations.
CREATE TABLE IF NOT EXISTS `system_configs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary Key',
    `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique key for the configuration setting',
    `config_value` TEXT COMMENT 'Value of the configuration setting',
    `config_type` VARCHAR(50) DEFAULT 'STRING' COMMENT 'Data type of the value (e.g., STRING, INTEGER, BOOLEAN, JSON)',
    `description` VARCHAR(255) COMMENT 'Description of what the configuration does',
    `editable` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Whether this config can be changed via UI',
    `visible` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Whether this config is visible in the UI',
    `version` INT NOT NULL DEFAULT 1 COMMENT 'Data version for optimistic locking',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp of creation',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Timestamp of last update'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='System configurations table';

-- Table: operation_logs - Records user and system operations.
CREATE TABLE IF NOT EXISTS `operation_logs` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary Key',
    `user_id` BIGINT COMMENT 'ID of the user who performed the operation (null for system operations)',
    `operation_type` VARCHAR(50) NOT NULL COMMENT 'Type of operation (e.g., LOGIN, CREATE_TASK, UPDATE_CONFIG)',
    `operation_content` TEXT COMMENT 'Detailed content or description of the operation',
    `ip_address` VARCHAR(45) COMMENT 'IP address of the client',
    `user_agent` VARCHAR(255) COMMENT 'User agent string of the client',
    `result` VARCHAR(20) NOT NULL DEFAULT 'SUCCESS' COMMENT 'Result of the operation (SUCCESS, FAILURE)',
    `error_message` TEXT COMMENT 'Error message if the operation failed',
    `cost_time` INT COMMENT 'Time taken for the operation in milliseconds',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp of the operation'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User and system operation logs';
