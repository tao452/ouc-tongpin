-- ============================================================
-- OUC同频 V0.1 数据库初始化脚本
-- 由 docker-compose 的 mysql 服务在【首次启动】时自动执行
--   (挂载到 /docker-entrypoint-initdb.d)
-- 幂等：所有 CREATE TABLE 使用 IF NOT EXISTS，重复执行不报错。
-- 字符集 utf8mb4(支持 emoji)，引擎 InnoDB。
--
-- 注意：MySQL 官方镜像仅在「数据目录为空(首次初始化)」时才执行本目录脚本。
--   若此前已 docker compose up 过(mysql-data 卷非空)，需先
--   `docker compose down -v` 清掉卷再 `docker compose up` 才会重新建表。
-- ============================================================

CREATE DATABASE IF NOT EXISTS ouc_tongpin
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE ouc_tongpin;

-- 用户表（表名用 users 避开 MySQL 保留字 user）
CREATE TABLE IF NOT EXISTS `users` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `nickname`   VARCHAR(64)  DEFAULT NULL,
  `avatar`     VARCHAR(512) DEFAULT NULL,
  `created_at` DATETIME     DEFAULT NULL,
  `updated_at` DATETIME     DEFAULT NULL,
  `deleted`    INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 认证/绑定表（微信 openid、学号、手机号）
CREATE TABLE IF NOT EXISTS `auth` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`    BIGINT       NOT NULL,
  `openid`     VARCHAR(64)  DEFAULT NULL,
  `student_no` VARCHAR(32)  DEFAULT NULL,
  `phone`      VARCHAR(20)  DEFAULT NULL,
  `created_at` DATETIME     DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_auth_user_id` (`user_id`),
  KEY `idx_auth_openid` (`openid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 每日情绪打卡表
CREATE TABLE IF NOT EXISTS `checkin` (
  `id`           BIGINT      NOT NULL AUTO_INCREMENT,
  `user_id`      BIGINT      NOT NULL,
  `emotion`      VARCHAR(16) DEFAULT NULL,
  `intensity`    INT         DEFAULT NULL,
  `note`         VARCHAR(100) DEFAULT NULL,
  `checkin_date` DATE        DEFAULT NULL,
  `created_at`   DATETIME    DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_checkin_user` (`user_id`),
  UNIQUE KEY `uk_checkin_user_date` (`user_id`, `checkin_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 树洞帖子表
CREATE TABLE IF NOT EXISTS `treehole_post` (
  `id`                  BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`             BIGINT       NOT NULL,
  `anonymous_id`        VARCHAR(64)  DEFAULT NULL,
  `content`             TEXT,
  `emotion_tag`         VARCHAR(16)  DEFAULT NULL,
  `anonymous`           INT          NOT NULL DEFAULT 0,
  `is_burn_after_read`  INT          NOT NULL DEFAULT 0,
  `status`              INT          NOT NULL DEFAULT 0,
  `created_at`          DATETIME     DEFAULT NULL,
  `expires_at`          DATETIME     DEFAULT NULL,
  `deleted`             INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_post_user` (`user_id`),
  KEY `idx_post_status_expire` (`status`, `expires_at`),
  KEY `idx_post_emotion` (`emotion_tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 树洞焚毁留档表（仅存内容哈希，不存明文）
CREATE TABLE IF NOT EXISTS `treehole_archive` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT,
  `post_id`      BIGINT       NOT NULL,
  `content_hash` VARCHAR(64)  DEFAULT NULL,
  `created_at`   DATETIME     DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_archive_post` (`post_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
