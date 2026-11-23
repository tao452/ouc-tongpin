import copy
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import scoring
from match.scorer import DEFAULT_CONFIG, Scorer, ScoreTimeout

client = TestClient(app)


def payload():
    profile = {"emotion_vector": [1, 0, 0, 0, 0, 0], "interests": ["Python"],
               "availability": [{"start": "2026-12-01T10:00:00+08:00",
                                 "end": "2026-12-01T12:00:00+08:00"}],
               "location": {"lat": 36.0, "lng": 120.0}}
    return {"query": profile, "candidate": {"id": "candidate-a", **copy.deepcopy(profile)}}


def test_single_and_batch_score_have_same_result_and_version():
    single = payload()
    response = client.post("/score", json=single)
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["score"] == 100
    assert body["config_sha256"] == response.headers["X-Score-Config-SHA256"]
    batch = {"query": single["query"], "candidates": [single["candidate"]]}
    assert client.post("/score", json=batch).json() == body
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_features_do_not_invent_similarity_and_ties_are_stable():
    body = client.post("/score", json={
        "query": {}, "candidates": [{"id": "b"}, {"id": "a"}]}).json()
    assert [(row["id"], row["score"]) for row in body["items"]] == [("a", 0), ("b", 0)]
    assert body["fallback"] is False


@pytest.mark.parametrize("body", [
    {}, {"query": {}}, {"query": {}, "candidates": []},
    {"query": {}, "candidate": {"id": "x"}, "candidates": [{"id": "y"}]},
    {"query": {}, "candidates": [{"id": "x"}, {"id": "x"}]},
    {"query": {}, "candidate": {"id": "PRIVATE SYNTHETIC INPUT"}},
    {"query": {}, "candidates": [{"id": str(i)} for i in range(101)]},
    {"query": {}, "candidate": None},
    {"query": {}, "candidate": {"id": "x"}, "candidates": None},
])
def test_score_bad_request_is_400_without_echoing_private_inputs(body):
    response = client.post("/score", json=body)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid request"}


def test_batch100_and_scoring_body_limit_preserve_moderation_limit():
    body = {"query": {}, "candidates": [{"id": str(i)} for i in range(100)]}
    assert len(client.post("/score", json=body).json()["items"]) == 100
    assert client.post("/score", content=b"x" * 131073).status_code == 413
    assert client.post("/api/moderation/check", content=b"x" * 16385).status_code == 413
    large_valid = {"query": {}, "candidates": [
        {"id": str(i), "interests": [str(j) + "x" * 30 for j in range(6)]} for i in range(100)]}
    assert 16384 < len(json.dumps(large_valid).encode()) < 131072
    assert client.post("/score", json=large_valid).status_code == 200


def test_compute_budget_returns503_without_partial_ranking(monkeypatch):
    def unavailable(request):
        raise ScoreTimeout("private internal details")

    monkeypatch.setattr(scoring.scorer, "score", unavailable)
    response = client.post("/score", json=payload())
    assert response.status_code == 503
    assert response.json() == {"detail": "Scoring temporarily unavailable"}


def test_service_enforces_compute_budget(monkeypatch):
    from match import scorer
    from match.models import ScoreRequest

    ticks = iter([0, 0.06])
    monkeypatch.setattr(scorer.time, "perf_counter", lambda: next(ticks))
    with pytest.raises(ScoreTimeout):
        Scorer().score(ScoreRequest.model_validate(payload()))


def test_config_is_explicit_validated_and_attested(tmp_path, monkeypatch):
    config = json.loads(DEFAULT_CONFIG.read_bytes())
    config["weights"] = {"emotion": 0.0, "interests": 1.0, "time": 0.0, "distance": 0.0}
    path = tmp_path / "weights.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("MATCH_WEIGHT_CONFIG_PATH", str(path))
    assert Scorer().config.weights.interests == 1.0
    monkeypatch.setenv("MATCH_WEIGHT_CONFIG_PATH", str(path.with_name("missing.json")))
    with pytest.raises(FileNotFoundError):
        Scorer()
