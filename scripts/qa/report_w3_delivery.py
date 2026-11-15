"""Summarize same-revision W3 CI evidence; exit 0 only when all automated checks pass."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from run_w3_api_regression import ROOT, validate_output
from run_w3_load import save_report
from w3_delivery_checks import validate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("api", "pii", "load", "java"):
        parser.add_argument(f"--{name}-report", type=Path, required=True)
    parser.add_argument("--expected-revision", help="Defaults to this checkout's HEAD")
    parser.add_argument("--output", type=Path, required=True,
                        help="JSON output below the ignored qa-private directory")
    args = parser.parse_args(argv)
    try:
        paths = {name: getattr(args, f"{name}_report") for name in ("api", "pii", "load", "java")}
        output = args.output.resolve()
        if not output.is_relative_to((ROOT / "qa-private").resolve()):
            raise ValueError("Output must be in the private evidence directory")
        validate_output(output, list(paths.values()) + [Path(__file__)])
        raw = {name: path.read_bytes() for name, path in paths.items()}
        if any(len(value) > 8 * 1024 * 1024 for value in raw.values()):
            raise ValueError("Oversized report")
        reports = {name: json.loads(value) for name, value in raw.items()}
        revision = args.expected_revision or subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        result = validate(reports, revision)
        result.update(
            generated_at_utc=datetime.now(UTC).isoformat(),
            evidence_sha256={name: hashlib.sha256(value).hexdigest()
                             for name, value in raw.items()},
            generator_sha256={name: hashlib.sha256(Path(__file__).with_name(name)
                                                  .read_bytes()).hexdigest()
                              for name in ("report_w3_delivery.py", "w3_delivery_checks.py")},
        )
        save_report(output, result)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("W3 report rejected: incomplete, failed or inconsistent evidence", file=sys.stderr)
        return 1
    print(json.dumps({key: result[key] for key in
                      ("source_revision", "automated_checks_passed", "business_acceptance")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
