import csv
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import evaluate_dataset as dataset  # noqa: E402
import evaluate_external as external  # noqa: E402
from external_corpus import load_corpus, metrics  # noqa: E402

ROOT = SCRIPTS.parents[2]
spec = importlib.util.spec_from_file_location("fetch_cold", ROOT / "scripts/qa/fetch_cold_test.py")
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


def corpus(tmp_path, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["", "split", "topic", "label", "fine-grained-label", "TEXT"])
    for number, (text, label) in enumerate(rows):
        writer.writerow([number, "test", "synthetic", label, "0", text])
    raw = stream.getvalue().encode()
    path = tmp_path / "test.csv"
    path.write_bytes(raw)
    return path, {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(rows)}


def test_full_corpus_accounting_keeps_duplicates_and_all_original_labels(tmp_path):
    path, manifest = corpus(tmp_path, [("same", "1"), ("same", "0"), ("", "0"),
                                      ("x" * 2001, "1"), ("ordinary", "0")])
    rows, accounting = load_corpus(path, manifest)
    assert [row["offensive"] for row in rows] == [True, False, False]
    assert accounting == {"upstream_rows": 5, "eligible_rows": 3, "excluded_rows": 2,
                          "exclusion_reasons": {"blank": 1, "over_2000_characters": 1},
                          "duplicate_rows_kept": 1}


def test_unknown_labels_or_changed_hash_are_rejected(tmp_path):
    path, manifest = corpus(tmp_path, [("synthetic", "2")])
    with pytest.raises(ValueError):
        load_corpus(path, manifest)
    path, manifest = corpus(tmp_path, [("synthetic", "1")])
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        load_corpus(path, manifest)


def test_counts_thresholds_and_wilson_intervals_are_real_not_rounded_to_pass():
    result = metrics({"tp": 2, "fp": 1, "tn": 3, "fn": 2})
    assert result["recall"] == 0.5
    assert result["false_positive_rate"] == 0.25
    assert result["precision"] == pytest.approx(2 / 3)
    assert result["recall_wilson95"][0] < 0.5 < result["recall_wilson95"][1]
    assert not result["broad_benchmark_thresholds_met"]
    assert metrics({"tp": 95, "fn": 5, "fp": 2, "tn": 98})[
        "broad_benchmark_thresholds_met"] is False


def test_candidate_recall_cannot_be_claimed_as_high_blocking_recall():
    class Service:
        dictionary_sha256 = "a" * 64

        def check(self, text):
            return SimpleNamespace(passed=True, hits=[SimpleNamespace(level="MEDIUM")])

    result = external.assess([
        {"text": "PRIVATE-SYNTHETIC-CONTENT", "offensive": True, "fine_label": "1"},
        {"text": "PRIVATE-SYNTHETIC-CONTENT", "offensive": False, "fine_label": "2"},
    ], Service())
    assert result["high_blocking"]["recall"] == 0
    assert result["any_level_candidate"]["recall"] == 1
    assert result["any_level_candidate"]["false_positive_rate"] == 1
    assert "PRIVATE" not in json.dumps(result)
    assert result["cases_with_each_hit_level"] == {"MEDIUM": 2}


class Response(io.BytesIO):
    def __init__(self, digest):
        super().__init__(json.dumps({"passed": True, "normalized": "private", "hits": []}).encode())
        self.headers = {"X-Moderation-Dictionary-SHA256": digest} if digest is not None else {}


@pytest.mark.parametrize("digest", [None, "invalid", "b" * 64])
def test_http_evaluation_rejects_missing_or_wrong_live_dictionary(monkeypatch, digest):
    monkeypatch.setattr(dataset.urllib.request, "urlopen", lambda *a, **k: Response(digest))
    with pytest.raises(ValueError):
        dataset.HttpModerationService("http://localhost:8000", "a" * 64).check("synthetic")


def test_http_dictionary_cannot_change_mid_evaluation(monkeypatch):
    responses = iter(["a" * 64, "b" * 64])
    monkeypatch.setattr(dataset.urllib.request, "urlopen",
                        lambda *a, **k: Response(next(responses)))
    service = dataset.HttpModerationService("http://localhost:8000")
    service.check("synthetic")
    with pytest.raises(ValueError):
        service.check("synthetic")


def test_explicit_broad_gate_fails_without_hiding_completed_diagnostics(monkeypatch, tmp_path):
    monkeypatch.setattr(external, "evaluate", lambda *a: {
        "accounting": {"eligible_rows": 5}, "starter": {"high_blocking": {}},
        "formal_v1": {"high_blocking": {"broad_benchmark_thresholds_met": False}}})
    arguments = ["data.csv", "--output", str(tmp_path / "report.json")]
    assert external.main(arguments) == 0
    assert external.main([*arguments, "--require-broad-thresholds"]) == 1


def test_evaluators_refuse_to_overwrite_inputs_before_running(tmp_path):
    path = tmp_path / "secret.csv"
    path.write_text("PRIVATE-SYNTHETIC", encoding="utf-8")
    with pytest.raises(ValueError):
        external.evaluate(path, path)
    assert path.read_text(encoding="utf-8") == "PRIVATE-SYNTHETIC"


def test_fetcher_rejects_changed_cache_and_public_raw_output(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    private = root / "qa-private"
    private.mkdir(parents=True)
    raw, license_data = b"synthetic-csv", b"synthetic-license"
    manifest = {"revision": "a" * 40, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "url": "https://raw.githubusercontent.com/thu-coai/COLDataset/" + "a" * 40
                       + "/COLDataset/test.csv", "name": "synthetic",
                "license_file": "LICENSE",
                "license_sha256": hashlib.sha256(license_data).hexdigest()}
    metadata = root / "manifest.json"
    metadata.write_text(json.dumps(manifest), encoding="utf-8")
    metadata.with_name("LICENSE").write_bytes(license_data)
    monkeypatch.setattr(fetcher, "ROOT", root)
    monkeypatch.setattr(fetcher, "MANIFEST", metadata)
    output = private / "test.csv"
    assert fetcher.fetch(output, lambda *a, **k: io.BytesIO(raw))["bytes"] == len(raw)
    assert output.read_bytes() == raw
    output.write_bytes(b"corrupt-private-cache")
    with pytest.raises(ValueError):
        fetcher.fetch(output)
    assert output.read_bytes() == b"corrupt-private-cache"
    with pytest.raises(ValueError):
        fetcher.fetch(root / "public.csv")
