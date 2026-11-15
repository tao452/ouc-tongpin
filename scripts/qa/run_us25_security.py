"""Twenty identity/authorization/PII checks on the disposable Actions stack only."""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from regression_http import Client, Runner, expect
from run_w3_api_regression import ROOT, validate_output
from run_w3_load import save_report
from us25_privacy_runtime import PrivacyStack, scan_runtime
from us25_security_cases import register


def execute(base, values):
    stack = PrivacyStack()
    code = "us25-a-" + secrets.token_hex(12)
    runner = Runner(Client(base).authenticate(code))
    actors, material, private_codes = register(runner, stack, values["JWT_SECRET"])
    with stack.public_reader() as read:
        def public_view():
            result = read("SELECT COUNT(*) FROM treehole_public")
            expect(result.returncode == 0 and int(result.stdout.strip()) > 0,
                   "Restricted reader could not access the public projection")
            runner.client.observations.append({"public_projection_read_allowed": True})
        runner.run("US25-17", public_view)

        def private_tables():
            for table in ("auth", "users", "treehole_identity", "treehole_post"):
                result = read(f"SELECT * FROM {table} LIMIT 1")
                expect(result.returncode != 0 and "1142" in result.stderr,
                       "Restricted reader could query a private or underlying table")
            runner.client.observations.append({"private_table_queries_denied": 4})
        runner.run("US25-18", private_tables)

    def deny_application_ddl():
        table = "qa_us25_" + secrets.token_hex(4)
        try:
            try:
                stack.sql(f"CREATE TABLE {table} (id INT)")
            except subprocess.CalledProcessError as error:
                expect("1142" in error.stderr or "1044" in error.stderr,
                       "Application DDL failed for an unexpected reason")
                runner.client.observations.append({"application_ddl_denied": True})
                return
            raise AssertionError("Application database account retains DDL privileges")
        finally:
            stack.root_sql(f"DROP TABLE IF EXISTS {table}")
    runner.run("US25-19", deny_application_ddl)

    runtime_pii = {}

    def pii():
        literals = [value for name, value in values.items()
                    if ("SECRET" in name or "PASSWORD" in name) and len(value) >= 16]
        runtime_pii.update(scan_runtime(stack, actors, "\n".join(material),
                                        [code, *private_codes, *literals]))
        runner.client.observations.append(runtime_pii)
    runner.run("US25-20", pii)
    expect(len(runner.results) == 20 and {row["case_id"] for row in runner.results}
           == {f"US25-{number:02}" for number in range(1, 21)}, "Incomplete security suite")
    return runner.results, runtime_pii


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if os.environ.get("GITHUB_ACTIONS") != "true":
        parser.error("Requires an owned disposable GitHub Actions Compose stack")
    try:
        sources = [ROOT / f"scripts/qa/{name}.py" for name in
                   ("run_us25_security", "us25_security_cases", "us25_privacy_runtime",
                    "regression_http", "regression_stack", "pii_scan")]
        env_file = ROOT / ".env"
        validate_output(args.output, [*sources, env_file])
        values = dict(line.split("=", 1) for line in env_file.read_text().splitlines()
                      if "=" in line and not line.startswith("#"))
        expect(values.get("WX_MOCK_ENABLED") == "true", "CI fixture provider must be explicit")
        results, pii = execute("http://127.0.0.1:8080", values)
        passed = all(row["status"] == "PASS" for row in results)
        report = {"suite": "us25-security-v1", "executed_at_utc": datetime.now(UTC).isoformat(),
                  "source_commit": subprocess.check_output(
                      ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "code_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(
                                      path.read_bytes()).hexdigest() for path in sources},
                  "scope": "Real isolated services/MySQL/JWT with synthetic identity provider; "
                           "no live WeChat or real-user privacy acceptance claim.",
                  "technical_security_checks_passed": passed,
                  "live_wechat_verified": False, "independent_business_review": "pending",
                  "production_acceptance": False, "runtime_pii_scan": pii,
                  "status_counts": dict(Counter(row["status"] for row in results)),
                  "results": results}
        save_report(args.output, report)
    except (OSError, ValueError, TypeError, KeyError, AssertionError, subprocess.SubprocessError):
        print("US25 verification failed: invalid input, environment or evidence", file=sys.stderr)
        return 2
    print(json.dumps({"status_counts": report["status_counts"],
                      "technical_security_checks_passed": passed, "production_acceptance": False}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
