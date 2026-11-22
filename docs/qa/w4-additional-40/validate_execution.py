"""Check design/evidence consistency; this command does not execute business tests."""

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def main():
    sys.path.insert(0, str(ROOT / "scripts/qa/w4_new40"))
    from buddy_rule_cases import load_rules, ready

    rules = load_rules()
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
        approved_rule = rules.get(case["id"])
        allowed = (
            {"title", "purpose", "preconditions", "expected"}
            if approved_rule and approved_rule["business"]["confirmed"]
            else set()
        )
        assert all(case[k] == old[k] for k in fixed if k not in allowed), case["id"]
        if approved_rule:
            assert case["rule_confirmation"] == approved_rule
            assert case["expected"]["approval"] == "BUSINESS_CONFIRMED_M1"
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
        assert case["actual_result"]["status"] == actual["status"]
        assert case["actual_result"]["source_commit"] == doc["execution_source_commit"]
        assert (
            case["actual_result"]["evidence_ref"]
            == doc["execution_results"] + "#" + case["id"]
        )
        if approved_rule and not ready(approved_rule):
            assert case["status"] == "NOT_RUN" and not case["executed"]
            assert (
                case["automation"]["implementation_status"] == "IMPLEMENTED_AWAITING_M5"
            )
            assert (ROOT / case["automation"]["implementation_file"]).is_file()
        else:
            assert actual["source_commit"] == doc["execution_source_commit"]
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
        "original38_business_fields_unchanged": True,
        "confirmed_rule_changes": {cid: rule["business"] for cid, rule in rules.items()},
        "historical_80_evidence_unchanged": True,
        "business_source_matches_execution_commit": True,
        "source_commit": doc["execution_source_commit"],
        "network_requests_executed_by_this_validator": 0,
        "actual_execution_report": doc["execution_results"],
    }
    output = ROOT / "qa-private/w4-design-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    )
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
