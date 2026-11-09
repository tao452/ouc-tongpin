import copy
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "docs/qa/data/pii-baseline.v1.json"


@pytest.fixture
def baseline(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/qa"))
    return importlib.import_module("pii_baseline")


def write_corpus(tmp_path, data):
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_versioned_fixture_is_explicitly_synthetic_and_all_expectations_match(baseline):
    data, digest = baseline.load_corpus(CORPUS)
    result = baseline.evaluate(data)
    assert len(digest) == 64
    assert result["production_acceptance"] is False
    assert result["cases_total"] == result["expectations_matched"] == 62
    assert result["kind_counts"] == {"positive": 36, "negative": 16, "review": 4, "out_of_scope": 6}
    assert result["candidate_cases"] == 40
    assert result["baseline_passed"] is True
    assert len(result["documented_gap_case_ids"]) == 6
    assert "13800000000" not in json.dumps(result)
    for counts in result["per_rule"].values():
        assert counts["expected_candidate_cases"] == counts["observed_candidate_cases"]
        assert counts["missed_case_ids"] == counts["extra_case_ids"] == []


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_id",
        "duplicate_text",
        "production",
        "unknown_rule",
        "wrong_kind",
        "multiline",
        "missing_kind",
        "missing_rule",
        "extra_field",
        "bad_rule_type",
    ],
)
def test_invalid_or_incomplete_corpus_is_rejected(baseline, tmp_path, mutation):
    data = copy.deepcopy(json.loads(CORPUS.read_text(encoding="utf-8")))
    if mutation == "duplicate_id":
        data["cases"][1]["id"] = data["cases"][0]["id"]
    elif mutation == "duplicate_text":
        data["cases"][1]["text"] = data["cases"][0]["text"]
    elif mutation == "production":
        data["production_acceptance"] = True
    elif mutation == "unknown_rule":
        data["cases"][0]["expected_rules"] = ["unknown"]
    elif mutation == "wrong_kind":
        data["cases"][0]["kind"] = "negative"
    elif mutation == "multiline":
        data["cases"][0]["text"] = "first\nsecond"
    elif mutation == "missing_kind":
        data["cases"] = [row for row in data["cases"] if row["kind"] != "review"]
    elif mutation == "missing_rule":
        data["cases"] = [row for row in data["cases"] if "phone" not in row["expected_rules"]]
    elif mutation == "extra_field":
        data["cases"][0]["private"] = "PRIVATE-VALUE"
    else:
        data["rule_names"] = [None]
    with pytest.raises(ValueError):
        baseline.load_corpus(write_corpus(tmp_path, data))


def test_invalid_scanner_locations_cannot_be_ignored(baseline, monkeypatch):
    data, _ = baseline.load_corpus(CORPUS)
    monkeypatch.setattr(
        baseline,
        "scan",
        lambda paths: {
            "files_scanned": 1,
            "lines_scanned": 62,
            "findings": [{"file_index": 1, "line": 999, "rules": ["phone"]}],
        },
    )
    with pytest.raises(ValueError, match="invalid finding"):
        baseline.evaluate(data)


def test_cli_success_mismatch_and_invalid_input(baseline, tmp_path, capsys, monkeypatch):
    cli = importlib.import_module("run_pii_baseline")
    output = tmp_path / "report.json"
    monkeypatch.chdir(tmp_path)
    assert cli.main(["--output", str(output)]) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert len(result["corpus_sha256"]) == 64
    assert len(result["code_sha256"]) == 3
    data, _ = baseline.load_corpus(CORPUS)
    data["cases"][0]["expected_rules"] = ["email"]
    path = write_corpus(tmp_path, data)
    assert cli.main(["--corpus", str(path), "--output", str(output)]) == 1
    assert json.loads(output.read_text(encoding="utf-8"))["mismatched_case_ids"] == ["PII-001"]
    path.write_text('{"private":"PRIVATE-INPUT"}', encoding="utf-8")
    assert cli.main(["--corpus", str(path), "--output", str(output)]) == 2
    assert "PRIVATE-INPUT" not in capsys.readouterr().err


def test_cli_output_error_never_claims_success(baseline, tmp_path, capsys):
    cli = importlib.import_module("run_pii_baseline")
    parent = tmp_path / "file"
    parent.write_text("fixture", encoding="utf-8")
    assert cli.main(["--output", str(parent / "report.json")]) == 2
    assert capsys.readouterr().out == ""
