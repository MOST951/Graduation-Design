-- ===================================================================
-- 01_create_database.sql: Create Database and User
-- ===================================================================
-- This script should be run by a user with administrative privileges (e.g., root).

-- Create the database with utf8mb4 character set for full Unicode support (including emojis).
CREATE DATABASE IF NOT EXISTS `weibo_sentiment_db`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- Create a dedicated user for the application to enhance security.
-- IMPORTANT: Replace 'YourSecurePassword' with a strong, unique password in a production environment.
CREATE USER 'weibo_user'@'%' IDENTIFIED BY 'YourSecurePassword';

-- Grant all necessary privileges to the new user on the application's database.
GRANT ALL PRIVILEGES ON `weibo_sentiment_db`.* TO 'weibo_user'@'%';

-- Apply the privilege changes immediately.
FLUSH PRIVILEGES;
