"""Extract structured results from actual JUnit XML; omit console output and synthetic PII."""

import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def collect(directory):
    reports = sorted(directory.glob("TEST-*.xml"))
    if not reports:
        raise ValueError("JUnit reports missing")
    results, suites = [], []
    for path in reports:
        suite = ET.parse(path).getroot()
        suites.append(
            {key: int(suite.get(key, 0)) for key in ("tests", "failures", "errors", "skipped")}
        )
        for case in suite.findall("testcase"):
            match = re.match(r"S1_(0(?:69|7[0-5]))_", case.get("name", ""))
            if not match:
                continue
            status = (
                "FAIL"
                if case.find("failure") is not None or case.find("error") is not None
                else ("BLOCKED" if case.find("skipped") is not None else "PASS")
            )
            results.append(
                {
                    "case_id": "S1-" + match[1],
                    "status": status,
                    "priority": "P0",
                    "execution_scope": "Actual Java JUnit; synthetic HMAC/logging fixtures only",
                    "observations": [
                        {
                            "junit_report": path.name,
                            "junit_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "test_method": case.get("name"),
                        }
                    ],
                    "reason": None if status == "PASS" else "JUnit failure/error/skip",
                }
            )
    if {row["case_id"] for row in results} != {f"S1-{n:03}" for n in range(69, 76)} or len(
        results
    ) != 7:
        raise ValueError("Missing or duplicate privacy JUnit result")
    totals = {
        key: sum(suite[key] for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    return {"java_test_totals": totals, "catalogue_results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = collect(args.reports)
    result.update(
        executed_at_utc=datetime.now(UTC).isoformat(),
        source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["java_test_totals"]))
    return int(result["java_test_totals"]["failures"] + result["java_test_totals"]["errors"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
