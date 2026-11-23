import math
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from match.features import distance_m, features, interest_jaccard, time_jaccard
from match.metrics import ndcg
from match.models import Location, Profile, TimeSlot, Weights


def slots(*pairs):
    return [TimeSlot(start=datetime.fromisoformat(a), end=datetime.fromisoformat(b))
            for a, b in pairs]


def test_tag_jaccard_normalizes_without_turning_programming_tags_into_other_words():
    assert interest_jaccard([" ＰＹＴＨＯＮ ", "Python", "跑步"], ["python", "摄影"]) == 1 / 3
    assert interest_jaccard(["C++"], ["C"]) == 0
    assert interest_jaccard([], []) == 0
    assert interest_jaccard(["  "], ["  "]) == 0


def test_time_union_merges_duplicate_overlap_and_compares_absolute_instants():
    a = slots(("2026-12-01T10:00+08:00", "2026-12-01T12:00+08:00"),
              ("2026-12-01T11:00+08:00", "2026-12-01T13:00+08:00"))
    b = slots(("2026-12-01T03:00+00:00", "2026-12-01T05:00+00:00"))
    assert time_jaccard(a, b) == pytest.approx(2 / 3)
    assert time_jaccard(b, a) == time_jaccard(a, b)
    touching = slots(("2026-12-01T13:00+08:00", "2026-12-01T14:00+08:00"))
    assert time_jaccard(a, touching) == 0
    assert time_jaccard([], []) == 0


@pytest.mark.parametrize("start,end", [
    ("2026-12-01T10:00", "2026-12-01T12:00"),
    ("2026-12-01T12:00Z", "2026-12-01T11:00Z"),
    ("2026-12-01T12:00Z", "2026-12-01T12:00Z"),
    (0, 100), (True, False),
])
def test_invalid_times_rejected(start, end):
    with pytest.raises(ValidationError):
        TimeSlot(start=start, end=end)


def test_spherical_distance_handles_poles_antimeridian_and_decay():
    origin = Location(lat=0.0, lng=0.0)
    east = Location(lat=0.0, lng=1.0)
    assert distance_m(origin, origin) == 0
    assert distance_m(origin, east) == pytest.approx(111195.08, abs=0.1)
    assert distance_m(Location(lat=90.0, lng=-180.0), Location(lat=90.0, lng=180.0)) < 1e-6
    assert distance_m(Location(lat=0.0, lng=-180.0), Location(lat=0.0, lng=180.0)) < 1e-6
    a = Profile(location=origin)
    near = features(a, Profile(location=Location(lat=0.0, lng=0.01)))
    far = features(a, Profile(location=east))
    assert 0 <= far["distance_decay"] < near["distance_decay"] <= 1


def test_emotion_similarity_zero_missing_and_complement_are_bounded():
    a = Profile(emotion_vector=[1, 0, 0, 0, 0, 0])
    same = features(a, a)
    other = features(a, Profile(emotion_vector=[0, 1, 0, 0, 0, 0]))
    assert same["emotion_similarity"] == 1 and same["emotion_complement"] == 0
    assert other["emotion_similarity"] == 0 and other["emotion_complement"] == 1
    missing = features(a, Profile(emotion_vector=[0] * 6))
    assert missing["emotion_similarity"] == missing["emotion_complement"] == 0
    assert not missing["available"]["emotion"]
    assert missing["distance_m"] is None and missing["distance_decay"] == 0


@pytest.mark.parametrize("change", [
    {"emotion_vector": [1] * 5}, {"emotion_vector": [math.nan] * 6},
    {"emotion_vector": [math.inf] * 6}, {"emotion_vector": [-0.1] * 6},
    {"location": {"lat": 90.000001, "lng": 0}},
    {"location": {"lat": 0, "lng": -180.000001}},
    {"location": {"lat": 0}}, {"interests": ["x"] * 33},
    {"interests": ["x" * 33]}, {"studentId": "SYNTHETIC-PRIVATE"},
])
def test_feature_input_rejects_unbounded_or_nonfinite_values(change):
    with pytest.raises(ValidationError):
        Profile.model_validate(change)


def test_utc_datetime_inputs_supported_without_losing_endpoints():
    start = datetime(2026, 12, 1, tzinfo=UTC)
    slot = TimeSlot(start=start, end=start.replace(hour=1))
    assert slot.start == start


def test_weight_sum_must_be_exactly_one_and_nonnegative():
    with pytest.raises(ValidationError):
        Weights(emotion=1.0, interests=1.0, time=0.0, distance=0.0)
    with pytest.raises(ValidationError):
        Weights(emotion=-0.1, interests=0.6, time=0.25, distance=0.25)


def test_ndcg_hand_calculation_and_ties_across_cutoff():
    assert ndcg([3, 2, 0], [3, 2, 1]) == 1
    expected = (2 + 3 / math.log2(3)) / (3 + 2 / math.log2(3))
    assert ndcg([3, 2, 0], [2, 3, 1]) == pytest.approx(expected)
    assert ndcg([3, 0, 0], [1, 1, 1], k=1) == pytest.approx(1 / 3)
    assert ndcg([0, 3, 0], [1, 1, 1], k=1) == pytest.approx(1 / 3)
    assert ndcg([0, 0], [3, 2]) == 0
    assert ndcg([2, 2], [0, 0]) == 1


@pytest.mark.parametrize("labels,scores,k", [
    ([], [], 10), ([1], [], 10), ([1], [1], 0), ([1], [1], True),
    ([-1], [1], 10), ([1], [math.nan], 10), ([math.inf], [1], 10),
])
def test_ndcg_rejects_invalid_metric_inputs(labels, scores, k):
    with pytest.raises(ValueError):
        ndcg(labels, scores, k)
