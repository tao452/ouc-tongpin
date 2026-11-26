CREATE TABLE users (id BIGINT AUTO_INCREMENT PRIMARY KEY, nickname VARCHAR(64), avatar VARCHAR(512),
 bio VARCHAR(100), created_at TIMESTAMP, updated_at TIMESTAMP, deleted INT DEFAULT 0);
CREATE TABLE user_tag (id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT NOT NULL,
 tag_type VARCHAR(16) NOT NULL, tag_name VARCHAR(24) NOT NULL, created_at TIMESTAMP,
 UNIQUE(user_id, tag_type, tag_name), FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE auth (id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT NOT NULL,
 openid VARCHAR(64) UNIQUE, student_no VARCHAR(32), phone VARCHAR(20), created_at TIMESTAMP);
CREATE TABLE checkin (id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT NOT NULL,
 emotion VARCHAR(16), intensity INT, note VARCHAR(100), checkin_date DATE, created_at TIMESTAMP,
 UNIQUE(user_id, checkin_date));
CREATE TABLE treehole_post (id BIGINT AUTO_INCREMENT PRIMARY KEY, anonymous_id VARCHAR(64),
 content TEXT, emotion_tag VARCHAR(16), anonymous INT, is_burn_after_read INT, status INT,
 created_at TIMESTAMP, expires_at TIMESTAMP, deleted INT);
CREATE TABLE treehole_identity (post_id BIGINT PRIMARY KEY, user_id BIGINT NOT NULL,
 created_at TIMESTAMP, FOREIGN KEY(post_id) REFERENCES treehole_post(id));
CREATE TABLE buddy_demand (id BIGINT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT, scene VARCHAR(64),
 event_time TIMESTAMP, location_address VARCHAR(255), latitude DECIMAL(10,6), longitude DECIMAL(10,6),
 skill_tags VARCHAR(512), remark VARCHAR(200), status VARCHAR(16), created_at TIMESTAMP, deleted INT);
