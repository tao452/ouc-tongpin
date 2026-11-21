"""Owned-stack transport and redacted evidence for the W4 execution suite."""

import hashlib
import http.client
import json
import os
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE_COMMIT = "99712e400ed725060ef8e0b3c44d699c5d1c14f2"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {
            k: "[REDACTED]"
            if any(
                s in k.lower()
                for s in ("token", "secret", "password", "authorization", "cookie")
            )
            else safe(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [safe(v) for v in value]
    return value


class Suite:
    def __init__(self, project, output):
        if not project.startswith("ouc-w4-"):
            raise ValueError("An owned ouc-w4- project is required")
        self.project, self.output = project, Path(output)
        self.run_id = uuid.uuid4().hex[:12]
        self.trace, self.results, self.lock = [], [], threading.Lock()
        self.env_path = ROOT / "qa-private/w4-closeout/.env"
        self.env = dict(
            line.split("=", 1)
            for line in self.env_path.read_text().splitlines()
            if "=" in line and not line.startswith("#")
        )
        self.base = int(self.env.get("WEB_PORT", "18085"))
        self.direct = int(self.env.get("W4_API_PORT", "18086"))
        prefix = ["wsl", "-u", "root", "-e"] if os.name == "nt" else []
        self.docker = [
            *prefix,
            "docker",
            "--host",
            os.environ.get(
                "W4_DOCKER_HOST",
                "unix:///var/run/ouc-w4-closeout.sock"
                if os.name == "nt"
                else "unix:///var/run/docker.sock",
            ),
        ]
        self.compose = [
            *self.docker,
            "compose",
            "--project-name",
            project,
            "--env-file",
            "qa-private/w4-closeout/.env",
            "-f",
            "infra/docker-compose.yml",
            "-f",
            "qa-private/w4-closeout/runtime.yml",
        ]

    def command(self, *args):
        result = subprocess.run(
            [*self.compose, *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900 if "--build" in args else 300 if "--wait" in args else 120,
            check=True,
        )
        return result.stdout.rstrip("\r\n")

    def sql(self, statement):
        result = self.command(
            "exec",
            "-T",
            "mysql",
            "sh",
            "-c",
            'MYSQL_PWD="$MYSQL_PASSWORD" exec mysql -u "$MYSQL_USER" '
            '-D "$MYSQL_DATABASE" --default-character-set=utf8mb4 '
            '--batch --skip-column-names "$@"',
            "mysql",
            "-e",
            statement,
        )
        self.record({"kind": "mysql", "query": statement, "output": result})
        return result

    def redis(self, *args):
        result = self.command(
            "exec",
            "-T",
            "redis",
            "sh",
            "-c",
            'REDISCLI_AUTH="$REDIS_PASSWORD" exec redis-cli --raw "$@"',
            "redis-cli",
            *map(str, args),
        )
        self.record({"kind": "redis", "arguments": list(args), "output": result})
        return result

    def record(self, value):
        with self.lock:
            self.trace.append(safe(value))

    def http(self, path, body=None, token=None, port=None, headers=None, method=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", port or self.base, timeout=25
        )
        data = (
            json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        )
        connection.putrequest(method or ("POST" if data is not None else "GET"), path)
        connection.putheader("Content-Type", "application/json")
        if token:
            connection.putheader("Authorization", "Bearer " + token)
        for key, value in headers or []:
            connection.putheader(key, value)
        if data is not None:
            connection.putheader("Content-Length", str(len(data)))
        connection.endheaders(data)
        response = connection.getresponse()
        raw, status = response.read(), response.status
        response_headers = dict(response.getheaders())
        connection.close()
        try:
            content = json.loads(raw)
        except ValueError:
            content = {"non_json_bytes": len(raw)}
        self.record(
            {
                "kind": "http",
                "port": port or self.base,
                "path": path,
                "method": method or ("POST" if data is not None else "GET"),
                "input": body,
                "header_names": [k for k, _ in headers or []],
                "authenticated": token is not None,
                "status": status,
                "response": content,
                "dictionary_sha256": response_headers.get(
                    "X-Moderation-Dictionary-SHA256"
                ),
            }
        )
        return status, content, response_headers

    def actor(self, code=None):
        status, body, _ = self.http(
            "/api/auth/login",
            {"code": code or "w4-" + self.run_id + "-" + uuid.uuid4().hex},
        )
        assert status == 200
        return {"id": int(body["userId"]), "token": body["token"]}

    def checkin(self, actor, day="2034-01-15", **changes):
        body = {"emotion": "HAPPY", "intensity": 3, "note": "first", "checkinDate": day}
        body.update(changes)
        return self.http("/api/emotions/checkins", body, actor["token"])

    def snapshot(self, actor):
        uid = int(actor["id"])
        return self.sql(
            "SELECT id,user_id,emotion,intensity,note,checkin_date,created_at "
            f"FROM checkin WHERE user_id={uid} ORDER BY id"
        )

    def buddy(self, actor, body=None):
        return self.http("/api/match/needs", body or self.need(), actor["token"])

    @staticmethod
    def need():
        return {
            "scene": "自习",
            "time": "2034-01-15T02:00:00Z",
            "location": {"address": "图书馆", "lat": 36.16, "lng": 120.4},
            "skillTags": ["高数"],
            "remark": "一起复习",
        }

    def buddy_count(self, actor):
        return int(
            self.sql(
                "SELECT COUNT(*) FROM buddy_demand WHERE user_id="
                + str(int(actor["id"]))
            )
        )

    def post(self, actor, content="w4 synthetic safe post", anonymous=True):
        return self.http(
            "/api/treehole/posts",
            {"content": content, "emotionTag": "CALM", "anonymous": anonymous},
            actor["token"],
        )

    def run(self, number, check):
        self.trace = []
        started = datetime.now(UTC).isoformat()
        try:
            check()
            status, reason = "PASS", None
        except AssertionError as error:
            status, reason = "FAIL", str(error) or "Assertion failed"
        except Exception as error:  # noqa: BLE001 - preserve per-case infrastructure failures as BLOCKED
            status, reason = "BLOCKED", type(error).__name__
        row = {
            "case_id": f"S1-{number:03}",
            "status": status,
            "reason": reason,
            "started_at": started,
            "finished_at": datetime.now(UTC).isoformat(),
            "source_commit": BASE_COMMIT,
            "executed": True,
            "scope": "real HTTP, owned MySQL8/Redis",
            "evidence": list(self.trace),
        }
        row["storage_observations"] = sorted(
            {e["kind"] for e in self.trace if e.get("kind") in {"mysql", "redis"}}
        )
        if number in {115, 116, 117, 119, 120}:
            row["storage_scope"] = "MySQL/Redis N/A; algorithm-only case"
        self.results.append(row)
        self.save()
        print(row["case_id"], status, reason or "", flush=True)

    def save(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_bytes(
            (
                json.dumps(
                    {
                        "project": self.project,
                        "source_commit": BASE_COMMIT,
                        "initial_empty_counts": getattr(self, "initial_counts", None),
                        "results": self.results,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            ).encode()
        )

    def require_empty(self):
        services = self.command("ps", "--format", "json")
        assert self.project in services
        counts = {
            table: int(self.sql(f"SELECT COUNT(*) FROM {table}"))
            for table in [
                "users",
                "auth",
                "checkin",
                "treehole_post",
                "treehole_identity",
                "treehole_archive",
                "buddy_demand",
            ]
        }
        assert not any(counts.values()), "A fresh empty database is required"
        assert int(self.redis("ZCARD", "treehole:burn_queue")) == 0
        return counts

    def parallel(self, jobs, workers=16):
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(job) for job in jobs]
            return [future.result(timeout=30) for future in futures]
