import asyncio

import pytest
from fastapi.testclient import TestClient

from app.body_limit import BodyLimitMiddleware
from app.main import app


def test_service_limit_without_gateway():
    with TestClient(app) as client:
        response = client.post("/api/moderation/check", content=b"X" * 16385)
        assert response.status_code == 413
        assert response.json() == {"detail": "Invalid request"}
        assert client.get("/health").status_code == 200


def exchange(chunks, headers=(), *, disconnect=False, scope_type="http"):
    async def run():
        sent, read = [], []
        messages = [{"type": "http.request", "body": value, "more_body": i < len(chunks)-1}
                    for i, value in enumerate(chunks)]
        if disconnect:
            messages = [{"type": "http.disconnect"}]

        async def receive():
            message = messages.pop(0)
            read.append(message)
            return message

        async def send(message):
            sent.append(message)

        async def downstream(scope, receiver, sender):
            if scope["type"] == "http":
                body = b""
                while True:
                    message = await receiver()
                    body += message.get("body", b"")
                    if not message.get("more_body"):
                        break
                await sender({"type": "http.response.start", "status": 202})
                await sender({"type": "http.response.body", "body": str(len(body)).encode()})

        scope = {"type": scope_type, "method": "POST", "path": "/api/moderation/check",
                 "headers": headers}
        await BodyLimitMiddleware(downstream)(scope, receive, send)
        return sent, read
    return asyncio.run(run())


def test_chunked_body_is_bounded_and_not_forwarded():
    sent, _ = exchange([b"x" * 10000, b"x" * 7000])
    assert sent[0]["status"] == 413
    assert b"xxxxx" not in sent[-1]["body"]


def test_boundary_and_replay():
    sent, _ = exchange([b"x" * 8000, b"x" * 8384])
    assert sent[0]["status"] == 202
    assert sent[-1]["body"] == b"16384"


@pytest.mark.parametrize("headers,status", [
    ([(b"content-length", b"16385")], 413),
    ([(b"content-length", b"9" * 5000)], 413),
    ([(b"content-length", b"-1")], 400),
    ([(b"content-length", b"abc")], 400),
    ([(b"content-length", b"1"), (b"content-length", b"2")], 400),
])
def test_bad_length_header_rejected_before_reading(headers, status):
    sent, read = exchange([b"private"], headers)
    assert sent[0]["status"] == status
    assert read == []


def test_declared_length_does_not_bypass_actual_limit():
    sent, _ = exchange([b"x" * 16385], [(b"content-length", b"1")])
    assert sent[0]["status"] == 413
    sent, _ = exchange([b"x"], [(b"content-length", b"00001")])
    assert sent[0]["status"] == 202


def test_disconnect_and_non_http_scope():
    assert exchange([], disconnect=True)[0] == []
    assert exchange([], scope_type="lifespan")[0] == []
