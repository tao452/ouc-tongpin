import json
from collections import Counter
from pathlib import Path


def test_manual_catalogue_design_completeness():
    path = Path(__file__).resolve().parents[3] / "docs/qa/s1-test-cases.json"
    catalogue = json.loads(path.read_text(encoding="utf-8"))
    cases = catalogue["cases"]
    assert len(cases) >= 80
    assert len({case["id"] for case in cases}) == len(cases)
    assert set(case["module"] for case in cases) == {
        "auth", "checkin", "treehole", "needs", "moderation", "privacy", "infra"}
    for case in cases:
        for field in ("id", "title", "preconditions", "steps", "expected"):
            assert isinstance(case[field], str) and case[field].strip()
        assert type(case["issue"]) is int
        assert case["status"] in {"NOT_RUN", "PASS", "FAIL", "BLOCKED"}
        if case["status"] in {"PASS", "FAIL"}:
            assert case["evidence"], "Executed cases need independently recorded evidence"
        if case["status"] == "NOT_RUN":
            assert case["evidence"] is None
    assert dict(Counter(case["status"] for case in cases)) == catalogue["status_counts"]
