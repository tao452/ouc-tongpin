"""Isolated CI database-role checks and transient runtime PII inputs. Never output values."""

import contextlib
import os
import re
import secrets
import subprocess
import tempfile
from pathlib import Path

from pii_scan import scan
from regression_http import expect
from regression_stack import Stack


def initialization_log_diagnostics(logs):
    return {
        "permissions_script_seen": "02-runtime-permissions.sh" in logs,
        "initialization_completed": "MySQL init process done" in logs,
        "mysql_error_codes": sorted(set(re.findall(r"ERROR (\d{4})", logs))),
        "connection_error": "Can't connect" in logs,
        "permission_error": "Permission denied" in logs,
        "interpreter_error": "bad interpreter" in logs or "not found" in logs,
        "missing_environment": [name for name in ("MYSQL_USER", "MYSQL_DATABASE",
                                                   "MYSQL_ROOT_PASSWORD")
                                if name + ": parameter not set" in logs],
    }


class PrivacyStack(Stack):
    def permission_diagnostics(self):
        """Counts and fixed flags only; never retain SQL, accounts or container logs."""
        counts = self.root_sql(
            "SELECT (SELECT COUNT(*) FROM mysql.user WHERE User='ouc_public_reader'),"
            "(SELECT COUNT(*) FROM information_schema.views "
            "WHERE table_schema=DATABASE() AND table_name='treehole_public')")
        logs = self.execute("logs", "--no-color", "mysql")
        return {"role_and_view_counts": [int(value) for value in counts.split()],
                **initialization_log_diagnostics(logs)}

    def root_sql(self, statement):
        command = [*self.command, "exec", "-T", "mysql", "sh", "-c",
                   ('MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -u root '
                   '-D "$MYSQL_DATABASE" --default-character-set=utf8mb4 '
                   '--batch --skip-column-names')]
        return subprocess.run(command, input=statement, check=True, capture_output=True,
                              text=True, timeout=30).stdout.strip()

    @contextlib.contextmanager
    def public_reader(self):
        user, password = "qa_reader_" + secrets.token_hex(4), secrets.token_hex(24)

        def query(statement):
            # Credentials enter a mode-600 temporary client file via stdin, not argv.
            shell = 'set -eu; umask 077; f=$(mktemp /tmp/ouc-us25-reader.XXXXXX); '
            shell += 'trap \'rm -f "$f"\' EXIT; cat > "$f"; '
            shell += 'mysql --defaults-extra-file="$f" -D "$MYSQL_DATABASE" '
            shell += '--default-character-set=utf8mb4 --batch --skip-column-names --execute "$1"'
            return subprocess.run([*self.command, "exec", "-T", "mysql", "sh", "-c",
                                   shell, "reader", statement],
                                  input=f"[client]\nuser={user}\npassword={password}\n",
                                  check=False, capture_output=True, text=True, timeout=30)
        try:
            self.root_sql(f"CREATE USER '{user}'@'localhost' IDENTIFIED BY '{password}';")
            self.root_sql(f"GRANT 'ouc_public_reader' TO '{user}'@'localhost';")
            self.root_sql(f"SET DEFAULT ROLE ALL TO '{user}'@'localhost';")
            yield query
        finally:
            self.root_sql(f"DROP USER IF EXISTS '{user}'@'localhost';")


def scan_runtime(stack, actors, public_material, secret_literals):
    alice, bob = actors
    student, phone = "SYNTHETICSTUDENT001", "13900001234"
    stack.sql(f"UPDATE auth SET student_no='{student}',phone='{phone}' "
              f"WHERE user_id={alice.user_id}")
    private = stack.sql("SELECT CONCAT('studentNo=',COALESCE(student_no,''),"
                        "' phone=',COALESCE(phone,''),' openid=',openid) FROM auth "
                        f"WHERE user_id IN ({alice.user_id},{bob.user_id})")
    logs = stack.execute("logs", "--no-color", "api", "web")
    expect(all(len(text.encode()) <= 4 * 1024 * 1024
               for text in (private, logs, public_material)), "Runtime material exceeds scan bound")
    public = public_material + "\n" + logs
    canaries = [student, phone, alice.token, bob.token, *secret_literals]
    expect(all(value not in public for value in canaries if value),
           "A private canary or configured credential appeared in public/runtime output")
    summaries = {}
    with tempfile.TemporaryDirectory(prefix="ouc-us25-pii-") as temporary:
        for name, text in (("private_auth", private), ("public_responses", public_material),
                           ("application_log", logs)):
            path = Path(temporary) / (name + ".txt")
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                           "w", encoding="utf-8") as output:
                output.write(text)
            result = scan([path])
            summaries[name] = {"lines_scanned": result["lines_scanned"],
                               "candidate_lines": len(result["findings"])}
    expect(summaries["private_auth"]["candidate_lines"] > 0,
           "Private-field positive control was not detected")
    expect(summaries["public_responses"]["candidate_lines"] == 0
           and summaries["application_log"]["candidate_lines"] == 0,
           "Public/log PII candidates require review")
    return {"channels": summaries, "private_positive_control_matched": True,
            "private_canary_leaks": 0, "raw_material_retained": False,
            "scope": "Real isolated API/MySQL/log output with synthetic identities; "
                     "not a live-user compliance or independent-review conclusion."}
