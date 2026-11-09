"""Merge actual HTTP, JUnit and Compose evidence into the 80-case catalogue."""

import argparse
import json
from collections import Counter
from pathlib import Path

from regression_plan import priority


def merge(http, java, stack):
    revisions = {report["source_commit"] for report in (http, java, stack)}
    if len(revisions) != 1:
        raise ValueError("Cannot merge evidence from different revisions")
    rows = list(http["catalogue_results"]) + list(java["catalogue_results"])
    for result in stack["results"]:
        if result["case_id"] not in {"S1-077", "S1-078", "S1-079"}:
            continue
        rows.append(
            {**result, "execution_scope": stack["scope"], "priority": priority(result["case_id"])}
        )
    if len(rows) != 80 or {row["case_id"] for row in rows} != {f"S1-{n:03}" for n in range(1, 81)}:
        raise ValueError("Exactly 80 unique catalogue results are required")
    for row in rows:
        if row["status"] not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError("Unsupported result status")
        if row["status"] == "PASS" and not row["observations"]:
            raise ValueError("PASS requires actual observations")
        if row["status"] == "BLOCKED" and not row.get("reason"):
            raise ValueError("BLOCKED requires a concrete reason")
    return {
        "source_commit": revisions.pop(),
        "executed_at_utc": http["executed_at_utc"],
        "scope": http["scope"],
        "contract_sha256": http["contract_sha256"],
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "priority_counts": {
            level: dict(Counter(row["status"] for row in rows if priority(row["case_id"]) == level))
            for level in ("P0", "P1")
        },
        "java_test_totals": java["java_test_totals"],
        "supplemental_results": http["supplemental_results"],
        "results": sorted(rows, key=lambda row: row["case_id"]),
    }


def write_compact(path, header, array_name, rows):
    lines = [
        "{",
        *(
            f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},"
            for key, value in header.items()
        ),
        f'  "{array_name}": [',
    ]
    lines += [
        "    " + json.dumps(row, ensure_ascii=False) + ("," if i + 1 < len(rows) else "")
        for i, row in enumerate(rows)
    ]
    lines += ["  ]", "}", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("http", "java", "stack", "output", "catalogue"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    reports = [
        json.loads(path.read_text(encoding="utf-8")) for path in (args.http, args.java, args.stack)
    ]
    report = merge(*reports)
    write_compact(
        args.output,
        {k: v for k, v in report.items() if k != "results"},
        "results",
        report["results"],
    )
    catalogue = json.loads(args.catalogue.read_text(encoding="utf-8"))
    indexed = {row["case_id"]: row for row in report["results"]}
    if {case["id"] for case in catalogue["cases"]} != indexed.keys():
        raise ValueError("Catalogue IDs differ from executed report")
    evidence = args.output.resolve().relative_to(Path.cwd().resolve()).as_posix()
    for case in catalogue["cases"]:
        actual = indexed[case["id"]]
        case.update(
            status=actual["status"],
            priority=priority(case["id"]),
            execution_scope=actual["execution_scope"],
            evidence={"records": [{"file": evidence, "case_id": case["id"]}]},
        )
        if actual["status"] == "BLOCKED":
            case["blocked_reason"] = actual["reason"]
        else:
            case.pop("blocked_reason", None)
    write_compact(
        args.catalogue,
        {"scope": report["scope"], "status_counts": report["status_counts"]},
        "cases",
        catalogue["cases"],
    )
    print(
        json.dumps(
            {"status_counts": report["status_counts"], "priority_counts": report["priority_counts"]}
        )
    )
    return int(report["status_counts"].get("FAIL", 0) > 0)


if __name__ == "__main__":
    raise SystemExit(main())
