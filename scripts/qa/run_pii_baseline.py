"""Reproduce the synthetic PII baseline and save an input-redacted report."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from pii_baseline import evaluate, load_corpus

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "docs/qa/data/pii-baseline.v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data, corpus_hash = load_corpus(args.corpus)
        report = evaluate(data)
        files = [
            "scripts/qa/pii_scan.py",
            "scripts/qa/pii_baseline.py",
            "scripts/qa/run_pii_baseline.py",
        ]
        report.update(
            {
                "executed_at_utc": datetime.now(UTC).isoformat(),
                "python_version": platform.python_version(),
                "corpus_sha256": corpus_hash,
                "code_sha256": {
                    name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files
                },
            }
        )
        try:
            report["source_revision"] = subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                text=True,
                timeout=5,
                stderr=subprocess.DEVNULL,
            ).strip()
            report["working_tree_dirty"] = bool(
                subprocess.check_output(
                    ["git", "-C", str(ROOT), "status", "--porcelain"],
                    text=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL,
                ).strip()
            )
        except (OSError, subprocess.SubprocessError):
            report["source_revision"] = None
            report["working_tree_dirty"] = None
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Keep the committed report readable while retaining one result per line.
        header = {key: value for key, value in report.items() if key != "results"}
        lines = [
            "{",
            *(f"  {json.dumps(key)}: {json.dumps(value)}," for key, value in header.items()),
            '  "results": [',
        ]
        lines += [
            "    " + json.dumps(row) + ("," if i + 1 < len(report["results"]) else "")
            for i, row in enumerate(report["results"])
        ]
        args.output.write_text("\n".join([*lines, "  ]", "}", ""]), encoding="utf-8")
    except (OSError, ValueError, TypeError):
        print("Baseline failed: input, scanner result or output is invalid", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "cases_total",
                    "kind_counts",
                    "candidate_cases",
                    "expectations_matched",
                    "mismatched_case_ids",
                    "baseline_passed",
                    "production_acceptance",
                )
            }
        )
    )
    return 0 if report["baseline_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
