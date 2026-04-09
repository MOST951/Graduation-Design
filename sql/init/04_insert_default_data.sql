-- ===================================================================
-- 04_insert_default_data.sql: Insert Initial Data
-- ===================================================================

USE `weibo_sentiment_db`;

-- --- Insert Default Admin User ---
-- Inserts a default administrator account.
-- 用户名: admin  密码: admin123
-- BCrypt hash generated for 'admin123'
INSERT INTO `users` (`username`, `password`, `email`, `roles`, `status`)
VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH', 'admin@example.com', 'ROLE_ADMIN,ROLE_USER', 'ACTIVE')
ON DUPLICATE KEY UPDATE `password` = '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH';

-- --- Insert Default System Configurations ---
-- Inserts essential system settings required for the application to function.
INSERT INTO `system_configs` (`config_key`, `config_value`, `config_type`, `description`, `editable`)
VALUES
('site.name', 'Weibo Sentiment Analysis Platform', 'STRING', 'The name of the website, displayed in the UI header.', TRUE),
('analysis.model.default', 'BERT', 'STRING', 'The default sentiment analysis model to use (e.g., BERT, RULE_BASED).', TRUE),
('task.default.max_records', '10000', 'INTEGER', 'The default maximum number of records for a new collection task.', TRUE),
('auth.jwt.expiration_days', '7', 'INTEGER', 'JWT token validity period in days.', FALSE),
('security.login.max_attempts', '5', 'INTEGER', 'Maximum number of failed login attempts before locking an account.', FALSE)
ON DUPLICATE KEY UPDATE `config_key` = VALUES(`config_key`);

-- --- Insert Sample Collection Task (Optional) ---
-- Inserts a sample data collection task for demonstration purposes.
INSERT INTO `collection_tasks` (`name`, `type`, `status`, `keywords`, `data_source`)
VALUES
('Sample Tech Keyword Watch', 'KEYWORD', 'PENDING', 'AI,Machine Learning,Big Data', 'Weibo')
ON DUPLICATE KEY UPDATE `name` = 'Sample Tech Keyword Watch';
