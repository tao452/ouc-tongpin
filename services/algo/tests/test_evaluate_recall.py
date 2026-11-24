import json

import pytest

from scripts.evaluate_candidate import sha
from scripts.evaluate_recall import ROOT, load_external, main, run


@pytest.fixture
def external(tmp_path):
    data = tmp_path / "data.csv"
    data.write_text("text,toxic,expression\n你好,0,0\n你就是鲨币,1,1\n", encoding="utf-8")
    manifest = dict(format="csv", sha256=sha(data), bytes=data.stat().st_size, rows=2,
                    name="TEST", text_column="text", label_column="toxic",
                    group_column="expression", previously_used=False)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return data, manifest, path


def test_external_confusion_counts_and_no_evidence_overwrite(external, tmp_path):
    data, _, path = external
    out = tmp_path / "report.json"
    result = run(data, out, path)
    assert result["candidate"]["high_blocking"]["confusion_matrix"] == dict(
        tp=1, fp=0, fn=0, tn=1)
    assert result["scope"] == "development_or_historical"
    assert result["production_acceptance"] is False
    with pytest.raises(FileExistsError):
        run(data, out, path)


def test_blind_evaluation_requires_exact_frozen_rules_and_unused_data(external, tmp_path):
    data, manifest, path = external
    with pytest.raises(ValueError, match="changed"):
        run(data, tmp_path / "bad.json", path, frozen=True)
    first = run(data, tmp_path / "dev.json", path)
    manifest["frozen_artifacts"] = first["frozen_artifacts"]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    result = run(data, tmp_path / "sealed.json", path, frozen=True)
    assert result["scope"] == "new_external_once"
    manifest["previously_used"] = True
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Previously used"):
        run(data, tmp_path / "reuse.json", path, frozen=True)


@pytest.mark.parametrize("update", [
    {"sha256": "0" * 64}, {"rows": 3}, {"bytes": 0},
])
def test_invalid_seal_is_rejected(external, update):
    data, manifest, _ = external
    manifest.update(update)
    with pytest.raises(ValueError):
        load_external(data, manifest)


@pytest.mark.parametrize("body", ["text,toxic\nx,2\n", "text,toxic\n,0\n",
                                  "text,toxic\n" + "x" * 2001 + ",1\n"])
def test_bad_labels_and_out_of_contract_rows_are_never_silently_removed(tmp_path, body):
    data = tmp_path / "bad.csv"
    data.write_text(body, encoding="utf-8")
    manifest = dict(format="csv", name="TEST", sha256=sha(data), bytes=data.stat().st_size,
                    text_column="text", label_column="toxic", rows=1)
    with pytest.raises(ValueError):
        load_external(data, manifest)


@pytest.mark.parametrize("url", ["https://example.com", "http://user@localhost",
                                 "http://127.0.0.1/path"])
def test_external_rows_are_not_sent_to_a_shared_or_remote_service(external, tmp_path, url):
    data, _, path = external
    with pytest.raises(ValueError, match="local"):
        run(data, tmp_path / "out.json", path, base_url=url)


def test_metric_failure_returns_nonzero_instead_of_diagnostic_success(tmp_path, capsys):
    data = tmp_path / "data.csv"
    data.write_text("text,toxic\n你好,1\n再见,0\n", encoding="utf-8")
    manifest = dict(format="csv", name="TEST", sha256=sha(data), bytes=data.stat().st_size,
                    text_column="text", label_column="toxic", rows=2)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert main([str(data), "--manifest", str(path), "--output", str(tmp_path / "fail.json"),
                 "--require-broad-thresholds"]) == 1
    report = json.loads((tmp_path / "fail.json").read_text(encoding="utf-8"))
    assert report["candidate"]["high_blocking"]["confusion_matrix"]["fn"] == 1
    assert main(["missing.csv", "--output", str(tmp_path / "missing.json")]) == 2


def test_development_mode_keeps_known_false_positive(external, tmp_path):
    result = run(ROOT / "docs/qa/data/us24-development.v3.jsonl", tmp_path / "dev.json")
    assert "R3-NEG-020" in result["candidate"]["decision_failure_ids"]
