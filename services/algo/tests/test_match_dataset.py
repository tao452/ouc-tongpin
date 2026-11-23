import gzip
import hashlib
import importlib.util
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "match_dataset", ROOT / "services/algo/scripts/generate_match_dataset.py")
dataset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dataset)


def test_synthetic5000_reproducible_accounting_without_splitting_query_groups():
    rows = dataset.generate()
    raw, packed = dataset.encode(rows)
    repeated_raw, repeated_packed = dataset.encode(dataset.generate())
    assert raw == repeated_raw and packed == repeated_packed
    assert gzip.decompress(packed) == raw
    assert len(rows) == 5000 and len({row["candidate"]["id"] for row in rows}) == 5000
    assert len({row["query_id"] for row in rows}) == 100
    assert Counter(row["split"] for row in rows) == {
        "train": 3000, "development": 1000, "test": 1000}
    by_query = {}
    for row in rows:
        assert 0 <= row["relevance"] <= 3
        by_query.setdefault(row["query_id"], set()).add(row["split"])
    assert all(len(splits) == 1 for splits in by_query.values())
    assert {row["cohort"] for row in rows} == {
        "complete", "missing_emotion", "missing_interests", "missing_time", "missing_location"}
    alternate, _ = dataset.encode(dataset.generate(99))
    assert hashlib.sha256(raw).digest() != hashlib.sha256(alternate).digest()


def test_synthetic_labels_follow_frozen_thresholds_and_retain_missing_evidence():
    good = {"time_jaccard": 1, "distance_m": 0, "emotion_similarity": 1, "interest_jaccard": 1}
    assert dataset.relevance(good) == 3
    assert dataset.relevance({**good, "time_jaccard": 0}) == 0
    assert dataset.relevance({**good, "distance_m": None}) == 0
    assert dataset.relevance({**good, "distance_m": 15000.1}) == 0
    assert dataset.relevance({**good, "emotion_similarity": 0}) == 2
    assert dataset.relevance({"time_jaccard": .1, "distance_m": 6000,
                             "emotion_similarity": 0, "interest_jaccard": 1}) == 1
    assert dataset.relevance({"time_jaccard": .1, "distance_m": 6000,
                             "emotion_similarity": 0, "interest_jaccard": 0}) == 0
