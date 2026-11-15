-- W3 / US-25. Run only against an explicitly selected database after backup.
-- Stop API writers and scheduled workers first; never run while posts can be created.
-- MySQL 8 client: mysql --database=ouc_tongpin < this-file.sql (password supplied securely).
-- Active content/identity associations are preserved; burned associations and aliases are cleared.
-- No shared database was modified to author this file.
-- MySQL DDL commits implicitly: if the final ALTER fails, the old user_id column and the
-- complete copied mapping both remain. Fix the DDL error and rerun; do not delete the data volume.

CREATE TABLE IF NOT EXISTS `treehole_identity` (
  `post_id`    BIGINT   NOT NULL,
  `user_id`    BIGINT   NOT NULL,
  `created_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`post_id`),
  KEY `idx_treehole_identity_user` (`user_id`),
  CONSTRAINT `fk_treehole_identity_post` FOREIGN KEY (`post_id`) REFERENCES `treehole_post` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP PROCEDURE IF EXISTS migrate_w3_treehole_identity;
DELIMITER //
CREATE PROCEDURE migrate_w3_treehole_identity()
migration: BEGIN
  DECLARE legacy_column INT DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SELECT COUNT(*) INTO legacy_column FROM information_schema.columns
    WHERE table_schema=DATABASE() AND table_name='treehole_post' AND column_name='user_id';
  -- Refuse ambiguous legacy values. Regenerate obsolete aliases with the configured
  -- application HMAC under a separately reviewed backfill before retrying this migration.
  IF legacy_column <> 0 THEN
    IF EXISTS (SELECT 1 FROM treehole_post WHERE COALESCE(status, 0) <> 1
               AND (user_id IS NULL OR user_id <= 0 OR anonymous_id IS NULL
               OR NOT REGEXP_LIKE(anonymous_id, '^anon_v1_[A-Za-z0-9_-]{43}$', 'c'))) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Invalid identity or obsolete alias; no legacy rows were changed';
    END IF;
    IF EXISTS (SELECT 1 FROM treehole_post p JOIN treehole_identity i ON i.post_id=p.id
               WHERE COALESCE(p.status, 0) <> 1 AND i.user_id <> p.user_id) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Conflicting identity mappings; no legacy rows were changed';
    END IF;
  END IF;

  START TRANSACTION;
  -- Already-burned posts have no remaining author association to migrate or require on rerun.
  DELETE i FROM treehole_identity i JOIN treehole_post p ON p.id=i.post_id WHERE p.status=1;
  UPDATE treehole_post SET anonymous_id='burned' WHERE status=1;
  IF legacy_column <> 0 THEN
    INSERT INTO treehole_identity(post_id, user_id, created_at)
      SELECT p.id, p.user_id, p.created_at FROM treehole_post p
      LEFT JOIN treehole_identity i ON i.post_id=p.id
      WHERE COALESCE(p.status, 0) <> 1 AND i.post_id IS NULL;
  END IF;
  IF EXISTS (SELECT 1 FROM treehole_post p LEFT JOIN treehole_identity i ON i.post_id=p.id
              WHERE COALESCE(p.status, 0) <> 1 AND i.post_id IS NULL) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Mapping verification failed; backfill rolled back';
  END IF;
  COMMIT;

  -- Drop only after each retained association was copied and verified.
  IF legacy_column <> 0 THEN
    ALTER TABLE treehole_post DROP COLUMN user_id, MODIFY COLUMN anonymous_id VARCHAR(64) NOT NULL;
  END IF;
END//
DELIMITER ;
CALL migrate_w3_treehole_identity();
DROP PROCEDURE migrate_w3_treehole_identity;

-- Counts only: do not export private identity rows to QA reports.
SELECT (SELECT COUNT(*) FROM treehole_post) AS post_count,
       (SELECT COUNT(*) FROM treehole_identity) AS private_mapping_count;
