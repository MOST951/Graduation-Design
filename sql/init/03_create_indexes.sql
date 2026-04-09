-- ===================================================================
-- 03_create_indexes.sql: Create Indexes for Performance
-- ===================================================================

USE `weibo_sentiment_db`;

-- --- Indexes for `users` table ---
-- Index on `username` is created automatically due to the UNIQUE constraint.
-- Index for searching by status and role.
CREATE INDEX `idx_users_status_roles` ON `users` (`status`, `roles`);

-- --- Indexes for `collection_tasks` table ---
-- Index for querying tasks by their status and type.
CREATE INDEX `idx_tasks_status_type` ON `collection_tasks` (`status`, `type`);
-- Index for soft delete queries.
CREATE INDEX `idx_tasks_is_deleted` ON `collection_tasks` (`is_deleted`);

-- --- Indexes for `sentiment_results` table ---
-- Foreign key constraint to link results back to a task.
ALTER TABLE `sentiment_results` ADD CONSTRAINT `fk_results_task_id` FOREIGN KEY (`task_id`) REFERENCES `collection_tasks`(`id`);
-- Index on `weibo_id` is created automatically due to the UNIQUE constraint.
-- Index for querying by sentiment label and score for analytics.
CREATE INDEX `idx_results_label_score` ON `sentiment_results` (`sentiment_label`, `sentiment_score`);
-- Index for querying by analysis time for time-series analysis.
CREATE INDEX `idx_results_analysis_time` ON `sentiment_results` (`analysis_time`);

-- --- Indexes for `system_configs` table ---
-- Index on `config_key` is created automatically due to the UNIQUE constraint.

-- --- Indexes for `operation_logs` table ---
-- Index for querying logs by user and operation type.
CREATE INDEX `idx_logs_user_operation` ON `operation_logs` (`user_id`, `operation_type`);
-- Index for querying logs by time range.
CREATE INDEX `idx_logs_create_time` ON `operation_logs` (`create_time`);
