-- migration_sha256: 336b0dcadd16837f8b06be5e9505c39a985f760d28737df4cc5be16b4d265fc4
-- Generated from the current tracked migration; ephemeral MySQL 8 only, WITHOUT --force.
-- This database must not exist beforehand; it contains only synthetic migration fixtures.
CREATE DATABASE w3_privacy_migration_verify_20261115;
USE w3_privacy_migration_verify_20261115;
CREATE TABLE treehole_post (
  id BIGINT PRIMARY KEY, user_id BIGINT NOT NULL, anonymous_id VARCHAR(64),
  content TEXT, created_at DATETIME, status INT NOT NULL DEFAULT 0, KEY idx_post_user(user_id)
) ENGINE=InnoDB;
INSERT INTO treehole_post VALUES
  (1,7,CONCAT('anon_v1_',REPEAT('A',43)),'synthetic-content-a',NOW(),0),
  (2,8,CONCAT('anon_v1_',REPEAT('B',43)),'synthetic-content-b',NOW(),0),
  (3,9,'obsolete-burned-alias','synthetic-burned-marker',NOW(),1),
  (4,10,NULL,'synthetic-burned-marker',NOW(),1);
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

INSERT INTO treehole_identity(post_id,user_id) VALUES(3,9);
DELIMITER //
CREATE PROCEDURE assert_w3(IN passed BOOLEAN, IN label_text VARCHAR(128))
BEGIN
  IF passed IS NULL OR NOT passed THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT=label_text; END IF;
END//
CREATE PROCEDURE expect_w3_rejection()
BEGIN
  DECLARE rejected BOOLEAN DEFAULT FALSE;
  BEGIN
    DECLARE CONTINUE HANDLER FOR SQLSTATE '45000' SET rejected=TRUE;
    CALL migrate_w3_treehole_identity();
  END;
  IF NOT rejected THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Expected rejection was not raised'; END IF;
END//
CREATE PROCEDURE expect_w3_sql_rejection()
BEGIN
  DECLARE rejected BOOLEAN DEFAULT FALSE;
  BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET rejected=TRUE;
    CALL migrate_w3_treehole_identity();
  END;
  IF NOT rejected THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Expected SQL failure was not raised'; END IF;
END//
CREATE PROCEDURE reset_w3_legacy()
BEGIN
  IF DATABASE() <> 'w3_privacy_migration_verify_20261115' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Wrong migration test database';
  END IF;
  DROP TABLE IF EXISTS migration_ddl_guard;
  DROP TABLE treehole_identity;
  DROP TABLE treehole_post;
  CREATE TABLE treehole_post (
    id BIGINT PRIMARY KEY, user_id BIGINT NOT NULL, anonymous_id VARCHAR(64),
    content TEXT, created_at DATETIME, status INT NOT NULL DEFAULT 0, KEY idx_post_user(user_id)
  ) ENGINE=InnoDB;
  CREATE TABLE treehole_identity (
    post_id BIGINT PRIMARY KEY, user_id BIGINT NOT NULL, created_at DATETIME,
    KEY idx_treehole_identity_user(user_id),
    CONSTRAINT fk_treehole_identity_post FOREIGN KEY(post_id) REFERENCES treehole_post(id)
  ) ENGINE=InnoDB;
END//
DELIMITER ;
-- 1: preserve active content/associations, clear already-burned associations and aliases.
CALL migrate_w3_treehole_identity();
CALL assert_w3((SELECT COUNT(*)=0 FROM information_schema.columns WHERE table_schema=DATABASE()
  AND table_name='treehole_post' AND column_name='user_id'),'legacy-column-not-removed');
CALL assert_w3((SELECT COUNT(*)=4 FROM treehole_post),'content-count-changed');
CALL assert_w3((SELECT content='synthetic-content-a' FROM treehole_post WHERE id=1),'active-content-changed');
CALL assert_w3((SELECT COUNT(*)=2 FROM treehole_identity WHERE (post_id=1 AND user_id=7)
  OR (post_id=2 AND user_id=8)),'active-mapping-not-preserved');
CALL assert_w3((SELECT COUNT(*)=2 FROM treehole_identity),'burned-mapping-not-removed');
CALL assert_w3((SELECT COUNT(*)=2 FROM treehole_post WHERE status=1 AND anonymous_id='burned'),
  'burned-alias-not-cleared');
SELECT 'legacy_copy_separation_and_burned_cleanup' AS test_name, 'PASS' AS status;
-- 2: an unchanged new schema can be migrated repeatedly.
CALL migrate_w3_treehole_identity();
CALL assert_w3((SELECT COUNT(*)=2 FROM treehole_identity),'repeat-changed-mappings');
SELECT 'idempotent_repeat' AS test_name, 'PASS' AS status;
-- 3: migration may be repeated after a live burn removed another mapping.
UPDATE treehole_post SET status=1, anonymous_id='burned', content='synthetic-burned-marker' WHERE id=2;
DELETE FROM treehole_identity WHERE post_id=2;
CALL migrate_w3_treehole_identity();
CALL assert_w3((SELECT COUNT(*)=1 FROM treehole_identity),'repeat-recreated-burned-mapping');
SELECT 'repeat_after_live_burn_without_mapping' AS test_name, 'PASS' AS status;
-- 4: missing active mapping must fail without deleting the active content.
DELETE FROM treehole_identity WHERE post_id=1;
CALL expect_w3_rejection();
CALL assert_w3((SELECT COUNT(*)=4 FROM treehole_post),'missing-map-deleted-content');
SELECT 'missing_active_mapping_rejected' AS test_name, 'PASS' AS status;
-- 5: obsolete active aliases leave data and the legacy identity column untouched.
CALL reset_w3_legacy();
INSERT INTO treehole_post VALUES(1,7,'obsolete-user-7','synthetic-retained',NOW(),0);
CALL expect_w3_rejection();
CALL assert_w3((SELECT COUNT(*)=1 FROM information_schema.columns WHERE table_schema=DATABASE()
  AND table_name='treehole_post' AND column_name='user_id'),'rejection-removed-legacy-column');
CALL assert_w3((SELECT user_id=7 AND content='synthetic-retained' FROM treehole_post WHERE id=1),
  'rejection-changed-legacy-data');
CALL assert_w3((SELECT COUNT(*)=0 FROM treehole_identity),'rejection-partially-copied-mapping');
SELECT 'obsolete_active_alias_rejected_without_data_loss' AS test_name, 'PASS' AS status;
-- 6: conflicting active private association must never be overwritten.
CALL reset_w3_legacy();
INSERT INTO treehole_post VALUES(1,7,CONCAT('anon_v1_',REPEAT('A',43)),'synthetic-retained',NOW(),0);
INSERT INTO treehole_identity VALUES(1,8,NOW());
CALL expect_w3_rejection();
CALL assert_w3((SELECT user_id=7 FROM treehole_post WHERE id=1),'conflict-changed-legacy-user');
CALL assert_w3((SELECT user_id=8 FROM treehole_identity WHERE post_id=1),'conflict-overwrote-private-user');
SELECT 'conflicting_active_mapping_rejected_without_data_loss' AS test_name, 'PASS' AS status;
-- 7: a forced final DDL failure preserves copied mappings and the original identity column.
CALL reset_w3_legacy();
INSERT INTO treehole_post VALUES(1,7,CONCAT('anon_v1_',REPEAT('A',43)),'synthetic-retained',NOW(),0);
ALTER TABLE treehole_post ADD UNIQUE KEY migration_guard_pair(id,user_id);
CREATE TABLE migration_ddl_guard (
  post_id BIGINT, user_id BIGINT,
  CONSTRAINT migration_guard_fk FOREIGN KEY(post_id,user_id) REFERENCES treehole_post(id,user_id)
) ENGINE=InnoDB;
INSERT INTO migration_ddl_guard VALUES(1,7);
CALL expect_w3_sql_rejection();
CALL assert_w3((SELECT COUNT(*)=1 FROM information_schema.columns WHERE table_schema=DATABASE()
  AND table_name='treehole_post' AND column_name='user_id'),'ddl-failure-removed-legacy-column');
CALL assert_w3((SELECT user_id=7 FROM treehole_identity WHERE post_id=1),'ddl-failure-lost-private-copy');
DROP TABLE migration_ddl_guard;
CALL migrate_w3_treehole_identity();
CALL assert_w3((SELECT COUNT(*)=0 FROM information_schema.columns WHERE table_schema=DATABASE()
  AND table_name='treehole_post' AND column_name='user_id'),'ddl-retry-not-completed');
CALL assert_w3((SELECT COUNT(*)=1 FROM treehole_identity),'ddl-retry-changed-mappings');
SELECT 'final_ddl_failure_preserves_data_and_can_retry' AS test_name, 'PASS' AS status;
SELECT 'W3_MYSQL_MIGRATION_ALL_PASS' AS result;
