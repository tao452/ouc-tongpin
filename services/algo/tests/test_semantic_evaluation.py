import json

import pytest

from scripts.evaluate_semantic import MODEL_FILES, run, summarize, verify_model


def test_semantic_threshold_tradeoff_does_not_turn_false_positives_into_passes():
    rows = [dict(label=1, probability=0.8), dict(label=1, probability=0.1),
            dict(label=0, probability=0.7), dict(label=0, probability=0.2)]
    loose = summarize(rows, 0.05)
    strict = summarize(rows, 0.75)
    assert loose["recall"] == 1 and loose["false_positive_rate"] == 1
    assert strict["recall"] == 0.5 and strict["false_positive_rate"] == 0
    assert not loose["broad_benchmark_thresholds_met"]
    assert not strict["broad_benchmark_thresholds_met"]


def test_untrusted_or_changed_model_files_are_rejected_before_loading(tmp_path):
    manifest = dict(files={}, trust_remote_code=True, revision="other")
    with pytest.raises(ValueError, match="Unexpected"):
        verify_model(tmp_path, manifest)
    manifest = dict(files={p: dict(bytes=0, sha256="0" * 64) for p in MODEL_FILES},
                    trust_remote_code=False, revision="614c097a485910d28beb75f60d90c61e3082b518")
    for name in MODEL_FILES:
        (tmp_path / name).write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="bytes"):
        verify_model(tmp_path, manifest)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="bytes"):
        run(tmp_path / "data.csv", tmp_path, path, tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()
