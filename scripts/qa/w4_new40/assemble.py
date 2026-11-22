"""Join actual HTTP and JUnit evidence without converting skips into passes."""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from buddy_rule_cases import RULE_FILE, load_rules, ready
from common import BASE_COMMIT, ROOT, safe


def assemble(http, retest, junit, events, output, first_attempt=None):
    raw = json.loads(Path(http).read_bytes())
    rows = {r["case_id"]: r for r in raw["results"]}
    attempts = [{"name": "initial_http", "results": raw["results"]}]
    if retest:
        repeated = json.loads(Path(retest).read_bytes())["results"]
        attempts.append({"name": "selected_http_retest", "results": repeated})
        for row in repeated:
            rows[row["case_id"]] = row
    suite = ET.parse(junit).getroot()
    for case in suite.iter("testcase"):
        if not case.get("name", "").startswith("S1_"):
            continue
        cid = case.get("name").replace("_", "-")
        failure = case.find("failure")
        error = case.find("error")
        status = (
            "BLOCKED"
            if case.find("skipped") is not None
            else ("FAIL" if failure is not None or error is not None else "PASS")
        )
        detail_path = Path(events) / (cid + ".json")
        details = json.loads(detail_path.read_bytes()) if detail_path.exists() else {}
        rows[cid] = {
            "case_id": cid,
            "status": status,
            "executed": status != "BLOCKED",
            "scope": "instance unit"
            if cid == "S1-085"
            else (
                "MockMvc security chain + real MySQL"
                if cid == "S1-087"
                else "service integration + real MySQL8/Redis; network HTTP N/A"
            ),
            "http_transport": "MockMvc" if cid == "S1-087" else "N/A",
            "source_commit": BASE_COMMIT,
            "duration_seconds": float(case.get("time", 0)),
            "started_at": details.get("started_at_utc"),
            "finished_at": details.get("finished_at_utc"),
            "evidence": details.get("events", []),
            "reason": (
                failure.get("message")
                if failure is not None
                else error.get("message")
                if error is not None
                else None
            ),
        }
        assert status != "PASS" or rows[cid]["evidence"], (
            "PASS needs actual observations"
        )
    expected = {f"S1-{n:03}" for n in range(81, 121)}
    assert set(rows) == expected, set(rows) ^ expected
    rules = raw.get("rule_confirmations") or load_rules()
    for cid, rule in rules.items():
        if ready(rule):
            assert rows[cid]["status"] != "NOT_RUN", (
                "Confirmed case needs an actual attempt"
            )
        else:
            assert rows[cid]["status"] == "NOT_RUN" and not rows[cid]["executed"]
    first = []
    if first_attempt:
        for c in ET.parse(first_attempt).getroot().iter("testcase"):
            first.append(
                {
                    "case_id": c.get("name", "").replace("_", "-"),
                    "status": "ERROR"
                    if c.find("error") is not None
                    else "FAIL"
                    if c.find("failure") is not None
                    else "PASS",
                    "scope": "first harness attempt; retained separately",
                }
            )
    counts = Counter(row["status"] for row in rows.values())
    sources = [
        *Path(__file__).parent.glob("*.py"),
        ROOT / "services/api-server/src/test/java/"
        "com/ouctongpin/apiserver/w4/W4DatabaseCasesIT.java",
        RULE_FILE,
    ]
    report = {
        "source_commit": BASE_COMMIT,
        "project": raw["project"],
        "initial_empty_counts": raw.get("initial_empty_counts"),
        "case_count": 40,
        "status_counts": {k: counts[k] for k in ["PASS", "FAIL", "BLOCKED", "NOT_RUN"]},
        "results": [rows[cid] for cid in sorted(rows)],
        "attempt_history": attempts,
        "first_java_attempt": first,
        "fixture_repairs": [
            "Windows subprocess and UTF-8 file decoding",
            "MyBatis spy delegates to a real SqlSession mapper",
            "owned guard DDL uses a dedicated root JDBC connection",
        ]
        if first_attempt
        else [],
        "rule_decisions": {
            cid: "M1_M5_CONFIRMED" if ready(rule) else "M1_CONFIRMED_M5_PENDING"
            for cid, rule in rules.items()
        },
        "rule_confirmations": rules,
        "source_sha256": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sources
        },
        "production_acceptance": False,
        "independent_m3_reproduction": "PENDING",
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(
        (json.dumps(safe(report), ensure_ascii=False, indent=2) + "\n").encode()
    )
    print(json.dumps(report["status_counts"]))
    return report


def main():
    p = argparse.ArgumentParser()
    for name in ["http", "junit", "events", "output"]:
        p.add_argument("--" + name, required=True)
    p.add_argument("--retest")
    p.add_argument("--first-attempt")
    a = p.parse_args()
    assemble(a.http, a.retest, a.junit, a.events, a.output, a.first_attempt)


if __name__ == "__main__":
    main()
