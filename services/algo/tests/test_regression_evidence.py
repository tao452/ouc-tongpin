import importlib
import io
import json
from pathlib import Path

import pytest


@pytest.fixture
def qa(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts/qa"))
    return importlib.import_module


def reports():
    external = {*range(69, 76), 77, 78, 79}
    rows = [{"case_id": f"S1-{n:03}", "status": "BLOCKED", "reason": "synthetic test dependency",
             "observations": [], "execution_scope": "unit fixture", "priority": "P0"}
            for n in range(1, 81)]
    common = {"source_commit": "synthetic-revision"}
    http = {**common, "catalogue_results": [r for n, r in enumerate(rows, 1) if n not in external],
            "executed_at_utc": "2026-11-09T00:00:00+00:00", "scope": "unit fixture",
            "contract_sha256": "synthetic-hash", "supplemental_results": []}
    java = {**common, "catalogue_results": rows[68:75], "java_test_totals": {"tests": 7}}
    stack = {**common, "results": rows[76:79], "scope": "unit fixture"}
    return http, java, stack


def test_evidence_merge_requires_same_revision(qa):
    http, java, stack = reports()
    java["source_commit"] = "other-revision"
    with pytest.raises(ValueError, match="different revisions"):
        qa("record_regression").merge(http, java, stack)


def test_evidence_merge_rejects_missing_case(qa):
    http, java, stack = reports()
    http["catalogue_results"].pop()
    with pytest.raises(ValueError, match="80 unique"):
        qa("record_regression").merge(http, java, stack)


def test_pass_cannot_be_created_without_observations(qa):
    http, java, stack = reports()
    http["catalogue_results"][0]["status"] = "PASS"
    with pytest.raises(ValueError, match="actual observations"):
        qa("record_regression").merge(http, java, stack)


def test_blocked_cases_remain_blocked_after_merge(qa):
    result = qa("record_regression").merge(*reports())
    assert result["status_counts"] == {"BLOCKED": 80}
    assert sum(sum(counts.values()) for counts in result["priority_counts"].values()) == 80


def test_junit_collector_preserves_failure_and_skip_without_console_output(qa, tmp_path):
    cases = []
    for n in range(69, 76):
        outcome = "<failure/>" if n == 69 else "<skipped/>" if n == 70 else ""
        cases.append(f'<testcase name="S1_{n:03}_fixture">{outcome}</testcase>')
    xml = ('<testsuite tests="7" failures="1" errors="0" skipped="1">' + "".join(cases)
           + "<system-out>PRIVATE-CONSOLE</system-out></testsuite>")
    (tmp_path / "TEST-fixture.xml").write_text(xml, encoding="utf-8")
    result = qa("collect_java_evidence").collect(tmp_path)
    assert [row["status"] for row in result["catalogue_results"][:2]] == ["FAIL", "BLOCKED"]
    assert "PRIVATE-CONSOLE" not in json.dumps(result)


def test_http_evidence_does_not_contain_tokens_or_identity_values(qa, monkeypatch):
    module = qa("regression_http")
    response = io.BytesIO(json.dumps({"token": "PRIVATE-TOKEN", "userId": "PRIVATE-ID",
                                    "isNewUser": True}).encode())
    response.status = 200
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: response)
    client = module.Client("http://fixture.invalid")
    client.request("/api/auth/login", {"code": "PRIVATE-INPUT"})
    result = json.dumps(client.observations)
    assert all(value not in result for value in ("PRIVATE-TOKEN", "PRIVATE-ID", "PRIVATE-INPUT"))


def test_unreachable_selected_service_is_a_failure(qa):
    module = qa("regression_http")
    runner = module.Runner(module.Client("http://fixture.invalid"))

    def unreachable():
        raise OSError("PRIVATE-CONNECTION-DETAIL")
    runner.run("fixture", unreachable)
    assert runner.results[0]["status"] == "FAIL"
    assert "PRIVATE-CONNECTION-DETAIL" not in json.dumps(runner.results)
