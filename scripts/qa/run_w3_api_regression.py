"""Execute the 30 W3 login/check-in/treehole cases on a disposable Compose stack.

Standard-library only. Run from any directory with --output; non-CI execution
requires --allow-disposable-stack because the HTTP cases create synthetic rows.
"""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import w3_api_auth
import w3_api_checkin
import w3_api_treehole
from regression_http import Client, Runner
from regression_stack import Stack

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/qa/data/w3-api-cases.v1.json"
EXPECTED_IDS = {
    *(f"W3-AUTH-{n:02}" for n in range(1, 7)),
    *(f"W3-CHECKIN-{n:02}" for n in range(1, 15)),
    *(f"W3-TREEHOLE-{n:02}" for n in range(1, 11)),
}
INPUT_FILES = [MANIFEST, ROOT / "packages/contract/openapi.yaml",
               *(Path(__file__).with_name(name) for name in (
                   "run_w3_api_regression.py", "w3_api_auth.py", "w3_api_checkin.py",
                   "w3_api_treehole.py", "regression_http.py", "regression_stack.py"))]


def validate_output(output, protected):
    for source in protected:
        if output.resolve() == source.resolve() or (
            output.exists() and source.exists() and output.samefile(source)
        ):
            raise ValueError("Output conflicts with an input or code file")


def load_manifest(path=MANIFEST):
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = manifest.get("cases", [])
    if len(rows) != 30 or {row.get("case_id") for row in rows} != EXPECTED_IDS:
        raise ValueError("W3 manifest must contain the exact 30 unique case IDs")
    for row in rows:
        expected_module = row["case_id"].split("-")[1].lower()
        if row.get("module") != expected_module:
            raise ValueError("Case module does not match its ID")
        if not all(isinstance(row.get(key), str) and row[key].strip()
                   for key in ("title", "expectation")):
            raise ValueError("Every W3 case needs a title and a checkable expectation")
    return manifest


def validate_results(results, manifest):
    identifiers = [row["case_id"] for row in results]
    if len(identifiers) != 30 or set(identifiers) != EXPECTED_IDS:
        raise ValueError("W3 execution did not produce the exact 30 unique case IDs")
    expected = {row["case_id"]: row for row in manifest["cases"]}
    for row in results:
        if row["status"] not in {"PASS", "FAIL"}:
            raise ValueError("Executable W3 cases must report PASS or FAIL")
        if row["status"] == "PASS" and not row.get("observations"):
            raise ValueError("PASS requires actual HTTP/storage observations")
        row.update({key: expected[row["case_id"]][key]
                    for key in ("module", "title", "expectation")})
    return sorted(results, key=lambda row: row["case_id"])


def execute(base_url, stack, manifest):
    runner = Runner(Client(base_url).authenticate())
    start_date = date(2040, 1, 1) + timedelta(days=secrets.randbelow(900_000))
    w3_api_auth.register(runner, stack)
    w3_api_checkin.register(runner, stack, start_date)
    w3_api_treehole.register(runner, stack)
    return validate_results(runner.results, manifest)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provenance():
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip())
    return {
        "source_commit": commit, "working_tree_dirty": dirty,
        "input_sha256": {path.relative_to(ROOT).as_posix(): sha256(path) for path in INPUT_FILES},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--compose-file", type=Path, action="append",
                        help="Compose file(s), defaults to infra/docker-compose.yml")
    parser.add_argument("--project-name", help="Explicit disposable Compose project name")
    parser.add_argument("--allow-disposable-stack", action="store_true",
                        help="Confirm a local stack is disposable; permits synthetic writes")
    args = parser.parse_args(argv)
    if os.environ.get("GITHUB_ACTIONS") != "true" and not args.allow_disposable_stack:
        parser.error("Non-CI execution requires --allow-disposable-stack on an isolated test stack")
    try:
        output = args.output.resolve()
        env_file = args.env_file.resolve()
        compose_files = [path.resolve() for path in (args.compose_file or
                                                    [ROOT / "infra/docker-compose.yml"])]
        validate_output(output, [*INPUT_FILES, env_file, *compose_files])
    except (OSError, ValueError):
        print("W3 regression failed: output or input paths are invalid", file=sys.stderr)
        return 2
    stack = Stack()
    command = ["docker", "compose", "--env-file", str(env_file)]
    for path in compose_files:
        command.extend(("-f", str(path)))
    if args.project_name:
        command.extend(("--project-name", args.project_name))
    stack.command = tuple(command)
    manifest = load_manifest()
    results = execute(args.base_url, stack, manifest)
    report = {"suite": manifest["version"], "executed_at_utc": datetime.now(UTC).isoformat(),
              **provenance(), "scope": manifest["scope"],
              "limitations": manifest["limitations"], "results": results,
              "status_counts": dict(Counter(row["status"] for row in results)),
              "module_counts": dict(Counter(row["module"] for row in results))}
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        print("W3 regression failed: output is not writable", file=sys.stderr)
        return 2
    print(json.dumps({key: report[key] for key in ("suite", "status_counts", "module_counts")}))
    return int(any(row["status"] != "PASS" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
