-- ============================================================
-- OUC同频 V0.1 数据库初始化脚本
-- 由 docker-compose 的 mysql 服务在【首次启动】时自动执行
--   (挂载到 /docker-entrypoint-initdb.d)
-- 幂等：所有 CREATE TABLE 使用 IF NOT EXISTS，重复执行不报错。
-- 字符集 utf8mb4(支持 emoji)，引擎 InnoDB。
--
-- 注意：MySQL 官方镜像仅在「数据目录为空(首次初始化)」时才执行本目录脚本。
--   既有数据卷应使用 migrations/ 中对应升级脚本，先备份并检查数据。
--   不要通过删除数据卷来升级共享或有保留价值的数据库。
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
  `bio`        VARCHAR(100) DEFAULT NULL,
  `created_at` DATETIME     DEFAULT NULL,
  `updated_at` DATETIME     DEFAULT NULL,
  `deleted`    INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户兴趣/技能标签（US-35 PUT /api/user/profile；JSON 数组拆行，按类型 + 值去重）
CREATE TABLE IF NOT EXISTS `user_tag` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`    BIGINT       NOT NULL,
  `tag_type`   VARCHAR(16)  NOT NULL,
  `tag_name`   VARCHAR(24)  NOT NULL,
  `created_at` DATETIME     DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_tag` (`user_id`, `tag_type`, `tag_name`),
  KEY `idx_user_tag_user` (`user_id`),
  CONSTRAINT `fk_user_tag_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
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
  UNIQUE KEY `uk_auth_openid` (`openid`)
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
  `anonymous_id`        VARCHAR(64)  NOT NULL,
  `content`             TEXT,
  `emotion_tag`         VARCHAR(16)  DEFAULT NULL,
  `anonymous`           INT          NOT NULL DEFAULT 0,
  `is_burn_after_read`  INT          NOT NULL DEFAULT 0,
  `status`              INT          NOT NULL DEFAULT 0,
  `created_at`          DATETIME     DEFAULT NULL,
  `expires_at`          DATETIME     DEFAULT NULL,
  `deleted`             INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_post_status_expire` (`status`, `expires_at`),
  KEY `idx_post_emotion` (`emotion_tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 私有身份映射：公开内容表不再保存内部 user_id。仅后端身份处理路径读取。
-- 表的独立访问权限由部署管理员配置，不向管理端列表或公开 API 暴露。
CREATE TABLE IF NOT EXISTS `treehole_identity` (
  `post_id`    BIGINT   NOT NULL,
  `user_id`    BIGINT   NOT NULL,
  `created_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`post_id`),
  KEY `idx_treehole_identity_user` (`user_id`),
  CONSTRAINT `fk_treehole_identity_post` FOREIGN KEY (`post_id`) REFERENCES `treehole_post` (`id`)
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

-- 搭子需求表（US-10 / POST /api/match/needs）
-- 只存发布内容；列表 / 筛选 / 排序属 V1.0 #12，暂无 GET 契约。
CREATE TABLE IF NOT EXISTS `buddy_demand` (
  `id`               BIGINT        NOT NULL AUTO_INCREMENT,
  `user_id`          BIGINT        NOT NULL,
  `scene`            VARCHAR(64)   DEFAULT NULL,
  `event_time`       DATETIME      DEFAULT NULL,
  `location_address` VARCHAR(255)  DEFAULT NULL,
  `latitude`         DECIMAL(10,6) DEFAULT NULL,
  `longitude`        DECIMAL(10,6) DEFAULT NULL,
  `skill_tags`       VARCHAR(512)  DEFAULT NULL,
  `remark`           VARCHAR(200)  DEFAULT NULL,
  `status`           VARCHAR(16)   NOT NULL DEFAULT 'OPEN',
  `created_at`       DATETIME      DEFAULT NULL,
  `deleted`          INT           NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_need_user` (`user_id`),
  KEY `idx_need_status_created` (`status`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 组队空间表（W6 / US-17）
-- 邀请码 7 天有效；撤销后 invite_code 置 NULL，与“码不存在”同义。
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

-- 组队成员表（一人一队：user 维度由业务层约束，team_id+user_id 唯一防重）
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
