"""Check design/evidence consistency; this command does not execute business tests."""

import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def main():
    doc = read(ROOT / "docs/qa/w4-additional-40-test-cases.json")
    snapshot = read(HERE / "design-20261118.snapshot.json")
    report = read(ROOT / doc["execution_results"])
    cases = doc["cases"]
    assert len(cases) == 40 and [c["id"] for c in cases] == [
        f"S1-{n:03}" for n in range(81, 121)
    ]
    fixed = [
        "id",
        "group",
        "module",
        "title",
        "purpose",
        "priority",
        "preconditions",
        "inputs",
        "steps",
        "expected",
        "related_original_ids",
        "existing_coverage",
        "coverage_delta",
        "source_refs",
    ]
    text = (ROOT / "docs/qa/W4-新增40条测试用例设计.md").read_text(encoding="utf-8")
    blocks = list(re.finditer(r"^## (S1-\d{3}) (.+)$", text, re.MULTILINE))
    assert len(blocks) == 40
    results = {r["case_id"]: r for r in report["results"]}
    assert len(results) == 40
    for index, (case, old) in enumerate(zip(cases, snapshot["cases"], strict=True)):
        assert all(case[k] == old[k] for k in fixed), case["id"]
        assert (
            blocks[index].group(1) == case["id"]
            and blocks[index].group(2) == case["title"]
        )
        block = text[
            blocks[index].end() : blocks[index + 1].start()
            if index + 1 < len(blocks)
            else len(text)
        ]
        assert "状态：" + case["status"] + "；" in block
        assert all(
            s in block
            for s in [
                case["purpose"],
                *case["preconditions"],
                *case["steps"],
                *case["expected"]["assertions"],
            ]
        )
        actual = results[case["id"]]
        assert case["status"] == actual["status"]
        if case["id"] in ["S1-113", "S1-114"]:
            assert (
                case["status"] == "NOT_RUN"
                and not case["executed"]
                and case["expected"]["approval"] == "PENDING"
            )
        else:
            assert case["executed"] and actual["evidence"]
            assert (
                case["automation"]["implementation_status"]
                == "IMPLEMENTED_AND_EXECUTED"
            )
            assert (ROOT / case["automation"]["implementation_file"]).is_file()
            assert actual["started_at"] and actual["finished_at"]
    counts = Counter(c["status"] for c in cases)
    assert (
        doc["status_counts"]
        == report["status_counts"]
        == {k: counts[k] for k in ["PASS", "FAIL", "BLOCKED", "NOT_RUN"]}
    )
    for name, digest in read(HERE / "baseline-manifest.json")[
        "original_80_and_history_git_blob_sha256"
    ].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert not subprocess.check_output(
        [
            "git",
            "diff",
            doc["execution_source_commit"],
            "--",
            "apps",
            "infra",
            "packages",
            "services/api-server/src/main",
            "services/api-server/pom.xml",
            "services/algo",
        ],
        cwd=ROOT,
    )
    value = {
        "artifact_type": "DESIGN_EXECUTION_INDEX_VALIDATION",
        "status": "PASS",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "status_counts": doc["status_counts"],
        "design_business_fields_unchanged": True,
        "historical_80_evidence_unchanged": True,
        "business_source_matches_99712e4": True,
        "network_requests_executed_by_this_validator": 0,
        "actual_execution_report": doc["execution_results"],
    }
    output = ROOT / "docs/qa/evidence/w4-additional-40/20261122/design-validation.json"
    output.write_bytes(
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    )
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
