"""Protect W3 evidence integrity: missing cases and unsupported PASS cannot be accepted."""

import copy
import importlib
import io
import json
from collections import Counter
from http.client import IncompleteRead
from pathlib import Path

import pytest


@pytest.fixture
def suite(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts/qa"))
    return importlib.import_module("run_w3_api_regression")


def result_fixture(suite):
    return [{"case_id": row["case_id"], "status": "PASS", "reason": None,
             "observations": [{"method": "POST", "http_status": 200}],
             "execution_scope": "unit fixture; not executed HTTP"}
            for row in suite.load_manifest()["cases"]]


def test_w3_manifest_has_three_modules_and_checkable_expectations(suite):
    manifest = suite.load_manifest()
    assert Counter(row["module"] for row in manifest["cases"]) == {
        "auth": 6, "checkin": 14, "treehole": 10}
    assert len({row["expectation"] + row["title"] for row in manifest["cases"]}) == 30


@pytest.mark.parametrize("fault", ["missing", "duplicate", "unexpected"])
def test_w3_manifest_rejects_incomplete_or_duplicate_ids(suite, tmp_path, fault):
    manifest = copy.deepcopy(suite.load_manifest())
    if fault == "missing":
        manifest["cases"].pop()
    elif fault == "duplicate":
        manifest["cases"][-1] = manifest["cases"][0]
    else:
        manifest["cases"][-1]["case_id"] = "W3-TREEHOLE-99"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="exact 30 unique"):
        suite.load_manifest(path)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "unsupported_pass", "blocked"])
def test_w3_results_reject_evidence_gaps(suite, fault):
    rows = result_fixture(suite)
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows[-1] = copy.deepcopy(rows[0])
    elif fault == "unsupported_pass":
        rows[0]["observations"] = []
    else:
        rows[0]["status"] = "BLOCKED"
    with pytest.raises(ValueError):
        suite.validate_results(rows, suite.load_manifest())


def test_w3_result_keeps_failures_instead_of_upgrading_them(suite):
    rows = result_fixture(suite)
    rows[0].update(status="FAIL", observations=[], reason="Contract assertion failed")
    result = suite.validate_results(rows, suite.load_manifest())
    assert next(row for row in result if row["case_id"] == rows[0]["case_id"])["status"] == "FAIL"


def test_w3_non_ci_execution_requires_explicit_disposable_stack(suite, monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(SystemExit) as error:
        suite.main(["--output", str(tmp_path / "report.json")])
    assert error.value.code == 2
    assert not (tmp_path / "report.json").exists()


def test_w3_registered_cases_match_manifest_without_executing_network(suite):
    class Registration:
        client = None

        def __init__(self):
            self.ids = []

        def run(self, identifier, check, *args):
            assert callable(check)
            self.ids.append(identifier)

    registration = Registration()
    suite.w3_api_auth.register(registration, None)
    suite.w3_api_checkin.register(registration, None, suite.date(2040, 1, 1))
    suite.w3_api_treehole.register(registration, None)
    assert len(registration.ids) == 30
    assert set(registration.ids) == suite.EXPECTED_IDS


def test_http_observations_keep_only_typed_scalars_and_fixed_levels(suite, monkeypatch):
    http = importlib.import_module("regression_http")

    class Response(io.BytesIO):
        status = 200

    body = {"passed": "PRIVATE-TOKEN", "isNewUser": True, "needStudentVerify": False,
            "total": True, "streakDays": -1,
            "hits": [{"level": "HIGH"}, {"level": "PRIVATE-TOKEN"}, None,
                     {"level": {"secret": "PRIVATE-TOKEN"}}]}
    monkeypatch.setattr(http.urllib.request, "urlopen",
                        lambda *args, **kwargs: Response(json.dumps(body).encode()))
    client = http.Client("http://localhost:8080")
    client.request("/api/auth/login", {"code": "synthetic"})
    observed = client.observations[-1]
    assert observed["isNewUser"] is True and observed["needStudentVerify"] is False
    assert observed["invalid_response_fields"] == {
        "passed": "str", "total": "bool", "streakDays": "int"}
    assert not {"passed", "total", "streakDays"} & observed.keys()
    assert observed["hit_levels"] == ["HIGH"]
    assert observed["invalid_hit_levels"] == 3
    assert "PRIVATE" not in json.dumps(observed)
    body.update(passed=True, total=0, streakDays=2)
    client.request("/api/auth/login", {"code": "synthetic"})
    assert client.observations[-1]["total"] == 0
    assert client.observations[-1]["streakDays"] == 2


def test_truncated_http_response_is_failed_without_aborting_later_cases(suite, monkeypatch):
    http = importlib.import_module("regression_http")

    class Response(io.BytesIO):
        status = 200

        def read(self):
            raise IncompleteRead(b"PRIVATE-PARTIAL-BODY")

    monkeypatch.setattr(http.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    runner = http.Runner(http.Client("http://localhost:8080"))
    runner.run("W3-AUTH-01", lambda: runner.client.request("/api/auth/login"))
    runner.run("W3-AUTH-02", lambda: runner.client.observations.append({"unit_fixture": True}))
    assert [row["status"] for row in runner.results] == ["FAIL", "PASS"]
    assert runner.results[0]["reason"] == "IncompleteRead"
    assert "PRIVATE" not in json.dumps(runner.results)


@pytest.mark.parametrize("target_kind", ["manifest", "code", "env", "compose"])
@pytest.mark.parametrize("alias", ["direct", "dotdot", "hardlink"])
def test_w3_output_cannot_replace_inputs_before_execution(
    suite, monkeypatch, tmp_path, capsys, target_kind, alias
):
    env_file = tmp_path / "PRIVATE-ENV"
    compose_file = tmp_path / "PRIVATE-COMPOSE"
    env_file.write_text("PRIVATE-CREDENTIAL", encoding="utf-8")
    compose_file.write_text("synthetic-config", encoding="utf-8")
    target = {"manifest": suite.MANIFEST, "code": Path(suite.__file__),
              "env": env_file, "compose": compose_file}[target_kind]
    original = target.read_bytes()
    output = target
    if alias == "dotdot":
        child = target.parent / "w3-path-alias"
        # Resolve normalizes this lexical alias without creating anything beside source files.
        output = child / ".." / target.name
    elif alias == "hardlink":
        output = tmp_path / "report.json"
        try:
            output.hardlink_to(target)
        except OSError:
            pytest.skip("Hardlinks are unavailable across these filesystem volumes")

    def forbidden(*args, **kwargs):
        pytest.fail("Unsafe output must be rejected before HTTP/storage execution")

    monkeypatch.setattr(suite, "execute", forbidden)
    assert suite.main(["--allow-disposable-stack", "--env-file", str(env_file),
                       "--compose-file", str(compose_file), "--output", str(output)]) == 2
    assert target.read_bytes() == original
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PRIVATE" not in captured.err


def test_w3_main_counts_failed_case_and_returns_one(suite, monkeypatch, tmp_path):
    rows = result_fixture(suite)
    rows[0].update(status="FAIL", reason="Contract assertion failed")
    rows = suite.validate_results(rows, suite.load_manifest())
    monkeypatch.setattr(suite, "execute", lambda *args: rows)
    monkeypatch.setattr(suite, "provenance", lambda: {"unit_fixture": True})
    output = tmp_path / "report.json"
    assert suite.main(["--allow-disposable-stack", "--output", str(output)]) == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status_counts"] == {"FAIL": 1, "PASS": 29}
