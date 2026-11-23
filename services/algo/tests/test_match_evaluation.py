import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import ndcg_score

from match.metrics import ndcg

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "docs/algorithms/data/us12-synthetic.v1.jsonl.gz"
MANIFEST = DATA.with_name("us12-synthetic.v1.validation-v1_1.manifest.json")
spec = importlib.util.spec_from_file_location(
    "match_evaluation", ROOT / "services/algo/scripts/evaluate_match.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


@pytest.mark.parametrize(("labels", "scores"), [
    ([0, 0, 0], [3, 1, 1]), ([3, 1, 0], [1, 1, 1]),
    ([0, 2, 3, 1], [4, 3, 2, 1]), ([0, 1, 3, 2], [1, 2, 2, 2]),
])
def test_ndcg_matches_pinned_sklearn_including_cross_boundary_ties(labels, scores):
    assert ndcg(labels, scores, k=2) == pytest.approx(
        ndcg_score(np.array([labels]), np.array([scores]), k=2), abs=1e-12)


def test_frozen_fixture_has_no_exclusions_and_refuses_overwrite_or_tampering(tmp_path):
    output = tmp_path / "result.json"
    report = evaluation.evaluate(DATA, MANIFEST, output)
    assert report["rows"] == 5000 and report["queries"] == 100
    assert report["reference_metric_crosschecks"] == 200
    assert report["excluded_rows"] == 0 and report["business_acceptance"] is False
    assert sum(row["queries"] for row in report["split_metrics"].values()) == 100
    assert sum(row["zero_gain_queries"] for row in report["split_metrics"].values()) == 20
    original = output.read_bytes()
    with pytest.raises(ValueError, match="Keep prior reports"):
        evaluation.evaluate(DATA, MANIFEST, output)
    assert output.read_bytes() == original
    changed = tmp_path / "changed.gz"
    changed.write_bytes(DATA.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="hash changed"):
        evaluation.load(changed, MANIFEST)
    metadata = json.loads(MANIFEST.read_bytes())
    metadata["feature_code_sha256"]["services/algo/match/models.py"] = "0" * 64
    invalid = tmp_path / "manifest.json"
    invalid.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="Frozen feature/schema"):
        evaluation.load(DATA, invalid)
