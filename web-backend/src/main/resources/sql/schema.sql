-- Drop tables if they exist to ensure a clean state
DROP TABLE IF EXISTS system_log;
DROP TABLE IF EXISTS sentiment_result;
DROP TABLE IF EXISTS collection_task;
DROP TABLE IF EXISTS users;

-- User table
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE,
    roles VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Data Collection Task table
CREATE TABLE collection_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(255) NOT NULL,
    keywords TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    user_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Sentiment Analysis Result table
CREATE TABLE sentiment_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT,
    weibo_id VARCHAR(50) NOT NULL UNIQUE,
    content TEXT,
    sentiment VARCHAR(20),
    confidence DOUBLE,
    publish_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES collection_task(id)
);

-- System Log table
CREATE TABLE system_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    operation VARCHAR(255),
    method VARCHAR(255),
    params TEXT,
    execution_time BIGINT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
