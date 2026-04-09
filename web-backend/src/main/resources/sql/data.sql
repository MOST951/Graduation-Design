-- Initial data script
-- Note: Passwords are encrypted using BCrypt. The plain text for the passwords below is 'password'.
-- In a real production environment, these should be replaced with strong, securely generated hashes.

INSERT INTO users (username, password, email, roles, status) VALUES 
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'admin@weibo.com', 'ROLE_ADMIN,ROLE_USER', 'ACTIVE'),
('user', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'user@weibo.com', 'ROLE_USER', 'ACTIVE');

-- Sample collection task for the regular user (user_id = 2)
INSERT INTO collection_task (task_name, keywords, status, user_id) VALUES 
('Initial Topic Analysis', 'Spring Boot,Java,Microservices', 'PENDING', 2);
