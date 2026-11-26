-- US-35 / PUT /api/user/profile. Run only against an explicitly selected database,
-- after backup and with API writes stopped. Never run while profiles can be written.
-- MySQL 8 client: mysql --database=ouc_tongpin < this-file.sql (password supplied securely).
-- Idempotent: safe to re-run. No data deletion; existing profiles are preserved.
-- No shared database was modified to author this file.

-- 1) Add bio to users if absent (kept idempotent via information_schema check).
DROP PROCEDURE IF EXISTS migrate_user_profile_bio;
DELIMITER //
CREATE PROCEDURE migrate_user_profile_bio()
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'users'
                   AND column_name = 'bio') THEN
    ALTER TABLE `users` ADD COLUMN `bio` VARCHAR(100) DEFAULT NULL AFTER `avatar`;
  END IF;
END//
CALL migrate_user_profile_bio()//
DROP PROCEDURE IF EXISTS migrate_user_profile_bio//
DELIMITER ;

-- 2) Create the tag association table (no-op if already present).
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
