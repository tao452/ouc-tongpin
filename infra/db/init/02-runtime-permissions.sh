#!/bin/sh
# Run by the MySQL entrypoint as administrator, after the schema exists.
# Password travels via environment, never SQL or command-line arguments.
set -eu
case "$MYSQL_USER" in ''|root|*[!A-Za-z0-9_]*) exit 1;; esac
case "$MYSQL_DATABASE" in ''|*[!A-Za-z0-9_]*) exit 1;; esac
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root "$MYSQL_DATABASE" <<SQL
REVOKE ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* FROM '$MYSQL_USER'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';
CREATE OR REPLACE SQL SECURITY DEFINER VIEW treehole_public AS
  SELECT id, anonymous_id, content, emotion_tag, created_at, expires_at
  FROM treehole_post
  WHERE deleted=0 AND status=0 AND expires_at > CURRENT_TIMESTAMP;
CREATE ROLE IF NOT EXISTS 'ouc_public_reader';
GRANT SELECT ON \`$MYSQL_DATABASE\`.treehole_public TO 'ouc_public_reader';
SQL
