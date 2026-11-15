"""Gate regressions use archived fixtures, never claim new HTTP/business execution."""

import copy
import importlib
import json
from pathlib import Path

import pytest

REVISION = "a" * 40


@pytest.fixture
def evidence(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "scripts/qa"))
    suite = importlib.import_module("w3_delivery_checks")
    directory = root / "docs/qa/evidence/w3-20261115"
    names = {"api": "w3-api-regression.json", "pii": "pii-baseline.json",
             "load": "w3-load.json", "java": "java-evidence.json"}
    reports = {key: json.loads((directory / name).read_text(encoding="utf-8"))
               for key, name in names.items()}
    for report in reports.values():
        report["source_commit"] = REVISION
        if "source_revision" in report:
            report["source_revision"] = REVISION
        report["working_tree_dirty"] = False
    for mapping in (reports["api"]["input_sha256"], reports["pii"]["code_sha256"]):
        mapping.update(dict.fromkeys(mapping, "f" * 64))
    reports["load"]["script_sha256"] = "f" * 64
    corpus_hash = suite.load_corpus(root / "docs/qa/data/pii-baseline.v1.json")[1]
    reports["pii"]["corpus_sha256"] = corpus_hash
    monkeypatch.setattr(suite, "source_hash", lambda revision, name:
                        corpus_hash if name.endswith("pii-baseline.v1.json") else "f" * 64)
    return suite, reports


def test_counts_are_recomputed_and_business_acceptance_stays_pending(evidence):
    suite, reports = evidence
    reports["pii"]["working_tree_dirty"] = True
    reports["api"]["results"][0]["observations"] = [{"token": "DO-NOT-COPY-THIS"}]
    result = suite.validate(reports, REVISION)
    assert result["checks"]["api_modules"] == {"auth": 6, "checkin": 14, "treehole": 10}
    assert result["checks"]["pii_documented_gaps"] == 6
    assert result["checks"]["privacy_junit_passed"] == 7
    assert result["automated_checks_passed"] is True
    assert result["business_acceptance"] is False
    assert result["evidence_working_tree_dirty"]["pii"] is True
    assert "DO-NOT-COPY-THIS" not in json.dumps(result)


@pytest.mark.parametrize("fault", [
    "mixed_revision", "wrong_code", "missing_api", "fake_api_count", "duplicate_pii",
    "pii_gap", "fake_pii_count", "privacy_skipped", "load_missing", "load_failed",
    "load_nan", "fake_latency", "production_claim",
])
def test_incomplete_failed_or_misleading_evidence_is_rejected(evidence, fault):
    suite, original = evidence
    reports = copy.deepcopy(original)
    if fault == "mixed_revision":
        reports["load"]["source_commit"] = "b" * 40
    elif fault == "wrong_code":
        key = next(iter(reports["api"]["input_sha256"]))
        reports["api"]["input_sha256"][key] = "0" * 64
    elif fault == "missing_api":
        reports["api"]["results"].pop()
    elif fault == "fake_api_count":
        reports["api"]["status_counts"]["PASS"] = 31
    elif fault == "duplicate_pii":
        reports["pii"]["results"][-1] = reports["pii"]["results"][0]
    elif fault == "pii_gap":
        row = next(row for row in reports["pii"]["results"] if row["kind"] == "out_of_scope")
        row["observed_rules"] = ["unexpected_rule"]
    elif fault == "fake_pii_count":
        reports["pii"]["expectations_matched"] = 61
    elif fault == "privacy_skipped":
        reports["java"]["catalogue_results"][0]["status"] = "BLOCKED"
    elif fault == "load_missing":
        reports["load"]["results"].pop()
    elif fault == "load_failed":
        reports["load"]["results"][0]["status"] = "FAIL"
    elif fault == "load_nan":
        reports["load"]["results"][0]["elapsed_ms"] = float("nan")
    elif fault == "fake_latency":
        reports["load"]["latency_ms"]["p95"] = 0
    else:
        reports["pii"]["production_acceptance"] = True
    with pytest.raises(ValueError):
        suite.validate(reports, REVISION)


def test_cli_refuses_to_overwrite_evidence_without_echoing_input(evidence, tmp_path, monkeypatch,
                                                               capsys):
    cli = importlib.import_module("report_w3_delivery")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    source = tmp_path / "qa-private/input.json"
    source.parent.mkdir()
    raw = '{"credential": "DO-NOT-PRINT"}'
    source.write_text(raw, encoding="utf-8")
    arguments = [item for name in ("api", "pii", "load", "java")
                 for item in (f"--{name}-report", str(source))]
    assert cli.main([*arguments, "--output", str(source)]) == 1
    assert source.read_text(encoding="utf-8") == raw
    assert "DO-NOT-PRINT" not in capsys.readouterr().err
