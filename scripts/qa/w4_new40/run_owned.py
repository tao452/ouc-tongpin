"""Prepare a fresh owned stack, execute the W4 suite, and remove only its resources."""

import argparse
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

from assemble import assemble
from common import BASE_COMMIT, ROOT, Suite


def java(suite, folder):
    folder.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        **suite.env,
        "W4_REAL_STACK": "true",
        "W4_PROJECT": suite.project,
        "W4_ROOT": str(ROOT),
        "W4_COMPOSE": json.dumps(suite.compose),
        "W4_EVIDENCE_DIR": str(folder / "java-events"),
        "DB_URL": "jdbc:mysql://127.0.0.1:"
        + suite.env["MYSQL_PORT"]
        + "/ouc_tongpin?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai",
        "REDIS_HOST": "127.0.0.1",
        "REDIS_PORT": suite.env.get("W4_REDIS_PORT", "16386"),
        "MODERATION_BASE_URL": "http://127.0.0.1:" + str(suite.base),
        "PYTHONUTF8": "1",
    }
    suite.command("stop", "api")
    try:
        with (folder / "java.log").open("wb") as log:
            completed = subprocess.run(
                [
                    "mvn.cmd" if os.name == "nt" else "mvn",
                    "-B",
                    "-q",
                    "-Dtest=W4DatabaseCasesIT",
                    "test",
                ],
                cwd=ROOT / "services/api-server",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        return completed.returncode
    finally:
        suite.command(
            "up",
            "-d",
            "--no-build",
            "--pull",
            "never",
            "--wait",
            "--wait-timeout",
            "90",
            "api",
        )


def prepare(project):
    here = ROOT / "qa-private/w4-closeout"
    here.mkdir(parents=True, exist_ok=True)
    # Refuse to replace a developer's or another run's secrets.
    values = {
        "MYSQL_ROOT_PASSWORD": secrets.token_hex(24),
        "MYSQL_DATABASE": "ouc_tongpin",
        "MYSQL_USER": "tongpin",
        "MYSQL_PASSWORD": secrets.token_hex(24),
        "MYSQL_PORT": "13386",
        "REDIS_PASSWORD": secrets.token_hex(24),
        "ANON_ID_SECRET": secrets.token_hex(32),
        "JWT_SECRET": secrets.token_hex(32),
        "WX_MOCK_ENABLED": "true",
        "WEB_PORT": "18085",
        "W4_API_PORT": "18086",
        "W4_REDIS_PORT": "16386",
    }
    with (here / ".env").open("x", encoding="utf-8") as target:
        target.write("\n".join(k + "=" + v for k, v in values.items()) + "\n")
    (here / "runtime.yml").write_bytes(b"""services:
  api:
    ports:
      - "127.0.0.1:18086:8080"
  redis:
    ports: !override
      - "127.0.0.1:16386:6379"
""")
    suite = Suite(project, here / "http-results.json")
    for resource in ["container", "volume", "network"]:
        existing = subprocess.check_output(
            [
                *suite.docker,
                resource,
                "ls",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "-q",
            ],
            cwd=ROOT,
        )
        assert not existing.strip(), "Refuse to reuse an existing project's resources"
    return suite


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True)
    p.add_argument("--reuse-owned-empty-stack", action="store_true")
    p.add_argument("--java-only", action="store_true")
    p.add_argument("--keep-stack", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert a.project.startswith("ouc-w4-new40-")
    protected = [
        "services/api-server/src/main",
        "services/api-server/pom.xml",
        "services/algo",
        "infra/db",
        "apps/admin-web",
    ]
    assert not subprocess.check_output(
        ["git", "diff", BASE_COMMIT, "--", *protected], cwd=ROOT
    )
    folder = ROOT / "qa-private/w4-closeout"
    suite = (
        Suite(a.project, folder / "http-results.json")
        if (a.reuse_owned_empty_stack or a.java_only)
        else prepare(a.project)
    )
    try:
        if not (a.reuse_owned_empty_stack or a.java_only):
            # Build checked-out sources; even a partial launch is cleaned in finally.
            suite.command("up", "-d", "--build", "--wait", "--wait-timeout", "240")
        if a.java_only:
            return java(suite, folder)
        suite.require_empty()
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("run_http.py")),
                "--project",
                a.project,
                "--output",
                str(folder / "http-results.json"),
            ],
            check=True,
        )
        java(suite, folder)
        report = assemble(
            folder / "http-results.json",
            None,
            ROOT / "services/api-server/target/surefire-reports/"
            "TEST-com.ouctongpin.apiserver.w4.W4DatabaseCasesIT.xml",
            folder / "java-events",
            a.output,
        )
        return int(
            report["status_counts"]["FAIL"] > 0
            or report["status_counts"]["BLOCKED"] > 0
        )
    finally:
        if not a.keep_stack:
            records = suite.command("ps", "--format", "json")
            rows = [json.loads(line) for line in records.splitlines() if line.strip()]
            assert all(row["Project"] == a.project for row in rows)
            suite.command("down", "-v")


if __name__ == "__main__":
    raise SystemExit(main())
