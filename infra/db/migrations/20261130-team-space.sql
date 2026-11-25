-- ============================================================
-- W6 / US-17 组队空间：组队表 + 成员表
-- 既有数据卷请手工执行本脚本；新环境由 01-schema.sql 自动建表。
-- 幂等：CREATE TABLE IF NOT EXISTS。
-- ============================================================
USE ouc_tongpin;

CREATE TABLE IF NOT EXISTS `team` (
  `id`                BIGINT       NOT NULL AUTO_INCREMENT,
  `name`              VARCHAR(32)  NOT NULL,
  `notice`            VARCHAR(200) DEFAULT NULL,
  `owner_user_id`     BIGINT       NOT NULL,
  `invite_code`       VARCHAR(16)  DEFAULT NULL,
  `invite_expires_at` DATETIME     DEFAULT NULL,
  `created_at`        DATETIME     DEFAULT NULL,
  `updated_at`        DATETIME     DEFAULT NULL,
  `deleted`           INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_team_owner` (`owner_user_id`),
  UNIQUE KEY `uk_team_invite_code` (`invite_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `team_member` (
  `id`         BIGINT      NOT NULL AUTO_INCREMENT,
  `team_id`    BIGINT      NOT NULL,
  `user_id`    BIGINT      NOT NULL,
  `role`       VARCHAR(16) NOT NULL DEFAULT 'MEMBER',
  `joined_at`  DATETIME    DEFAULT NULL,
  `deleted`    INT         NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_team_member` (`team_id`, `user_id`),
  KEY `idx_team_member_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
