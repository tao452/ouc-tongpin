import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_contract():
    assert client.get("/health").json() == {"status": "ok"}
    data = client.post("/api/moderation/check", json={"text": "傻 逼"}).json()
    assert data == {"passed": False, "normalized": "傻逼",
                    "hits": [{"word": "傻逼", "level": "HIGH"}]}
    assert client.post("/api/moderation/check", json={"text": "你好"}).json()["passed"]


@pytest.mark.parametrize("payload", [
    {}, {"text": ""}, {"text": " "}, {"text": None}, {"text": 123}, {"text": []},
    {"text": "a" * 2001}, {"text": "hello", "studentId": "TEST-STUDENT-001"},
])
def test_invalid_input_is_rejected_without_echoing_content(payload):
    response = client.post("/api/moderation/check", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request"}


def test_malformed_json():
    assert client.post("/api/moderation/check", content=b"{",
                       headers={"Content-Type": "application/json"}).status_code == 422


def test_length_boundary_and_repeatability():
    payload = {"text": "好" * 2000}
    first = client.post("/api/moderation/check", json=payload)
    assert first.status_code == 200
    assert first.json() == client.post("/api/moderation/check", json=payload).json()


def test_wrong_method():
    assert client.get("/api/moderation/check").status_code == 405


def test_implementation_matches_repository_contract():
    from pathlib import Path

    import yaml

    contract = yaml.safe_load((Path(__file__).resolve().parents[3]
                               / "packages/contract/openapi.yaml").read_text(encoding="utf-8"))
    operation = contract["paths"]["/api/moderation/check"]["post"]
    schema = operation["requestBody"]["content"]["application/json"]["schema"]
    live = client.get("/openapi.json").json()["components"]["schemas"]["ModerationRequest"]
    assert schema["required"] == live["required"]
    assert schema["additionalProperties"] == live["additionalProperties"]
    for field in ("minLength", "maxLength"):
        assert schema["properties"]["text"][field] == live["properties"]["text"][field]
    response = client.post("/api/moderation/check", json={"text": "hi"}).json()
    expected = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert set(response) == set(expected["properties"])
