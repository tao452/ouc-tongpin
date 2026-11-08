"""Real HTTP checks against the running Compose stack, not mocked services."""
import json
import os
import urllib.error
import urllib.request

base = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8080")


def request(path, data=None):
    payload = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base + path, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


assert request("/")[0] == 200, "Admin page unavailable"
status, body = request("/api/moderation/check", {"text": "傻 逼"})
assert status == 200 and json.loads(body)["passed"] is False, "High-risk text not blocked"
status, body = request("/api/moderation/check", {"text": "一起去图书馆"})
assert status == 200 and json.loads(body)["passed"] is True, "Normal text blocked"
assert request("/api/moderation/check", {"text": " "})[0] == 422
status, body = request("/api/emotions/checkins")
assert status == 200 and "items" in json.loads(body), "Java API not reachable through gateway"
assert request("/internal/health")[0] == 404, "Internal health endpoint was exposed"
assert request("/api/moderation/check", {"text": "好" * 6000})[0] == 413
print("PASS: 7 stack HTTP checks (admin, Java, moderation, validation, routing, body limit)")
