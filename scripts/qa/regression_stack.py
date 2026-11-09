"""Fixtures confined to the disposable Compose project created by the CI workflow."""

import subprocess

from regression_http import expect


class Stack:
    command = ("docker", "compose", "--env-file", ".env", "-f", "infra/docker-compose.yml")

    def execute(self, *arguments):
        return subprocess.run(
            [*self.command, *arguments], check=True, capture_output=True, text=True, timeout=60
        ).stdout.strip()

    def sql(self, statement):
        # SQL is passed as a process argument, never interpolated into shell source.
        shell = (
            'MYSQL_PWD="$MYSQL_PASSWORD" exec mysql -u "$MYSQL_USER" '
            '-D "$MYSQL_DATABASE" --batch --skip-column-names "$@"'
        )
        return self.execute(
            "exec", "-T", "mysql", "sh", "-c", shell, "mysql", "--execute", statement
        )

    def count(self, table):
        expect(
            table in {"checkin", "treehole_post", "treehole_archive", "users", "auth"},
            "Unknown fixture table",
        )
        return int(self.sql(f"SELECT COUNT(*) FROM {table}"))

    def redis(self, *arguments):
        shell = 'REDISCLI_AUTH="$REDIS_PASSWORD" exec redis-cli --raw "$@"'
        return self.execute("exec", "-T", "redis", "sh", "-c", shell, "redis-cli", *arguments)

    def snapshot(self):
        return {
            "database_rows": self.count("treehole_post"),
            "queue_entries": int(self.redis("ZCARD", "treehole:burn_queue")),
        }

    def direct_body_limit(self):
        code = (
            "import urllib.request,urllib.error\n"
            "request=urllib.request.Request('http://127.0.0.1:8000/api/moderation/check',"
            "data=b'x'*16385,headers={'Content-Type':'application/json'})\n"
            "try:\n"
            " response=urllib.request.urlopen(request,timeout=10)\n"
            " print(response.status)\n"
            "except urllib.error.HTTPError as error: print(error.code)\n"
        )
        return int(self.execute("exec", "-T", "algo", "python", "-c", code))
