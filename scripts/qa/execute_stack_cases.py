"""Collect actual Compose/gateway evidence on an isolated CI runner."""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    command = ["docker", "compose", "--env-file", ".env", "-f", "infra/docker-compose.yml"]

    def run(number, check):
        try:
            observed = check()
            status, reason = "PASS", None
        except (AssertionError, OSError, ValueError, subprocess.SubprocessError) as error:
            observed = {}
            status, reason = "FAIL", type(error).__name__
        results.append({"case_id": f"S1-{number:03d}", "status": status,
                        "observations": observed, "reason": reason})

    def config():
        valid = subprocess.run(command + ["config", "-q"], capture_output=True, text=True)
        invalid = subprocess.run(command + ["config", "-q"], capture_output=True, text=True,
                                 env={**os.environ, "ANON_ID_SECRET": ""})
        assert valid.returncode == 0 and invalid.returncode != 0
        assert "ANON_ID_SECRET" in invalid.stderr
        secrets = [line.split("=", 1)[1].strip() for line in Path(".env").read_text().splitlines()
                   if "=" in line and any(key in line.split("=", 1)[0]
                                          for key in ("PASSWORD", "SECRET"))]
        combined = valid.stdout + valid.stderr + invalid.stdout + invalid.stderr
        assert all(secret not in combined for secret in secrets if len(secret) >= 12)
        return {"valid_config_exit": valid.returncode, "missing_secret_exit": invalid.returncode,
                "missing_variable": "ANON_ID_SECRET", "no_secret_value_in_output": True}

    run(77, config)

    def health():
        ps = subprocess.run(command + ["ps", "--format", "json"], capture_output=True,
                            text=True, check=True)
        try:
            data = json.loads(ps.stdout)
            rows = data if isinstance(data, list) else [data]
        except ValueError:
            rows = [json.loads(line) for line in ps.stdout.splitlines() if line.strip()]
        services = {row["Service"]: {"state": row["State"], "health": row.get("Health")}
                    for row in rows}
        assert set(services) == {"mysql", "redis", "api", "algo", "web"}
        assert all(row["state"] == "running" and row["health"] == "healthy"
                   for row in services.values())
        return services

    run(78, health)

    def smoke():
        result = subprocess.run([sys.executable, "scripts/e2e/foundation-smoke.py"],
                                capture_output=True, text=True)
        assert result.returncode == 0 and "PASS: 7 stack HTTP checks" in result.stdout
        return {"exit_code": result.returncode, "http_checks_passed": 7}

    run(79, smoke)

    def gateway_body():
        base = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8080")
        request = urllib.request.Request(base + "/api/moderation/check", data=b"x" * 16385,
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        assert status == 413
        return {"gateway_http_status": status,
                "scope": "gateway only; direct check recorded separately"}

    run(68, gateway_body)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report = {"executed_at_utc": datetime.now(UTC).isoformat(), "source_commit": source,
              "scope": "Linux CI isolated Compose stack", "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(content, encoding="utf-8")
    print(json.dumps({"executed": len(results),
                      "failed": sum(row["status"] == "FAIL" for row in results)}))
    return int(any(row["status"] == "FAIL" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
