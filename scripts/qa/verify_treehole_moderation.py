"""Verify moderation before MySQL/Redis writes in a disposable CI Compose stack.

Temporarily stops and restores the algorithm container to exercise real dependency failure.
Run only in the isolated test environment; never point this at a shared deployment.
"""
import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def verify(base_url):
    command = ["docker", "compose", "--env-file", ".env", "-f", "infra/docker-compose.yml"]
    results = []

    def execute(*arguments):
        return subprocess.run(command + list(arguments), check=True, capture_output=True,
                              text=True, timeout=90).stdout.strip()

    def snapshot():
        rows = execute("exec", "-T", "mysql", "sh", "-c",
                       'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u "$MYSQL_USER" '
                       '-D "$MYSQL_DATABASE" --batch --skip-column-names '
                       '-e "SELECT COUNT(*) FROM treehole_post"')
        queued = execute("exec", "-T", "redis", "sh", "-c",
                         'REDISCLI_AUTH="$REDIS_PASSWORD" '
                         'redis-cli ZCARD treehole:burn_queue')
        return {"mysql_rows": int(rows), "redis_queue_entries": int(queued)}

    def publish(text):
        body = json.dumps({"content": text, "emotionTag": "CALM", "anonymous": True}).encode()
        request = urllib.request.Request(base_url.rstrip("/") + "/api/treehole/posts",
                                         data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def run(name, check):
        try:
            observed = check()
            results.append({"case": name, "status": "PASS", "observations": observed})
        except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as error:
            results.append({"case": name, "status": "FAIL", "reason": type(error).__name__})

    def allowed(text):
        before = snapshot()
        status, response = publish(text)
        after = snapshot()
        assert status == 201
        assert response["content"] == text
        assert after == {key: value + 1 for key, value in before.items()}
        return {"http_status": status, "before": before, "after": after}

    def denied(text, expected_status):
        before = snapshot()
        status, response = publish(text)
        after = snapshot()
        assert status == expected_status and response["code"] == expected_status
        assert text not in json.dumps(response, ensure_ascii=False)
        assert after == before
        return {"http_status": status, "before": before, "after": after}

    run("normal_persists_once", lambda: allowed("W2合成用例：一起去图书馆"))
    run("high_never_persists", lambda: denied("W2合成用例：你是傻逼", 422))
    run("medium_remains_allowed", lambda: allowed("W2合成用例：你是废物"))
    run("low_remains_allowed", lambda: allowed("W2合成用例：垃圾分类"))
    run("benign_context_remains_allowed", lambda: allowed("W2合成用例：暑假去死海旅游"))

    def unavailable():
        try:
            execute("stop", "algo")
            return denied("W2合成用例：审核服务故障时不可写入", 503)
        finally:
            execute("up", "-d", "--wait", "--wait-timeout", "60", "algo")

    run("unavailable_never_persists", unavailable)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true":
        parser.error("This command requires a disposable GitHub Actions Compose environment")
    results = verify(os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8080"))
    report = {
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "scope": "Disposable CI MySQL/Redis/Java/FastAPI stack; synthetic data, demo user 1; "
                 "not JWT, privacy, or product-policy acceptance.",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(content, encoding="utf-8")
    failed = sum(row["status"] == "FAIL" for row in results)
    print(json.dumps({"executed": len(results), "failed": failed}))
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
