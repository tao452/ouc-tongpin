-- Run on an authorized existing database, after backup and with API writes stopped.
-- No identity/data deletion: duplicate legacy identifiers require operator review.
DELIMITER //
DROP PROCEDURE IF EXISTS migrate_auth_identity_unique//
CREATE PROCEDURE migrate_auth_identity_unique()
BEGIN
  IF EXISTS (SELECT openid FROM auth WHERE openid IS NOT NULL
             GROUP BY openid HAVING COUNT(*) > 1) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Duplicate auth identities require review';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                 WHERE table_schema=DATABASE() AND table_name='auth'
                 AND index_name='uk_auth_openid' AND non_unique=0) THEN
    ALTER TABLE auth ADD UNIQUE KEY uk_auth_openid (openid);
  END IF;
END//
CALL migrate_auth_identity_unique()//
DROP PROCEDURE migrate_auth_identity_unique//
DELIMITER ;
