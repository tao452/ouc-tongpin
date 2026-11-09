"""Run every currently executable catalogue HTTP case on a disposable CI Compose stack."""

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import regression_auth
import regression_checkin
import regression_moderation
import regression_treehole
from regression_http import Client, Runner
from regression_plan import EXTERNAL, priority, register_blocked
from regression_stack import Stack


def execute(base):
    client, stack = Client(base), Stack()
    runner = Runner(client)
    for module in (regression_auth, regression_checkin, regression_treehole, regression_moderation):
        module.register(runner, stack)
    register_blocked(runner)
    identifiers = [result["case_id"] for result in runner.results]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate executed case identifier")
    expected = {f"S1-{n:03}" for n in range(1, 81) if n not in EXTERNAL}
    if {i for i in identifiers if i.startswith("S1-")} != expected:
        raise ValueError("Missing or unexpected catalogue result")
    for result in runner.results:
        result["priority"] = (
            priority(result["case_id"]) if result["case_id"].startswith("S1-") else "P0"
        )
    return sorted(runner.results, key=lambda result: result["case_id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true":
        parser.error("Requires the disposable GitHub Actions Compose environment")
    results = execute(args.base_url)
    report = {
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "scope": "Real HTTP + MySQL/Redis, disposable CI stack, synthetic inputs, demo user 1. "
        "Mock code2session is not real WeChat/JWT authorization acceptance.",
        "contract_sha256": hashlib.sha256(
            Path("packages/contract/openapi.yaml").read_bytes()
        ).hexdigest(),
        "catalogue_results": [row for row in results if row["case_id"].startswith("S1-")],
        "supplemental_results": [row for row in results if not row["case_id"].startswith("S1-")],
        "other_evidence": {f"S1-{n:03}": scope for n, scope in EXTERNAL.items()},
        "status_counts": dict(Counter(row["status"] for row in results)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {
                "catalogue_rows": len(report["catalogue_results"]),
                "supplemental_rows": len(report["supplemental_results"]),
                "status_counts": report["status_counts"],
            }
        )
    )
    return int(any(row["status"] == "FAIL" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
