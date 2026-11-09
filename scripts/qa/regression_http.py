"""HTTP regression evidence without input text, tokens, identities or response bodies."""

import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class Client:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.observations = []

    def request(self, path, payload=None, raw=None):
        data = (
            raw
            if raw is not None
            else (
                json.dumps(payload, ensure_ascii=False).encode("utf-8")
                if payload is not None
                else None
            )
        )
        request = urllib.request.Request(
            self.base + path, data=data, headers={"Content-Type": "application/json"}
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                status, content = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, content = error.code, error.read()
        try:
            body = json.loads(content)
        except ValueError:
            body = None
        observed = {
            "method": request.get_method(),
            "route": urllib.parse.urlsplit(path).path,
            "http_status": status,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
        }
        if isinstance(body, dict):
            observed["response_keys"] = sorted(body)
            for field in ("passed", "isNewUser", "needStudentVerify", "total", "streakDays"):
                if field in body:
                    observed[field] = body[field]
            if isinstance(body.get("hits"), list):
                observed["hit_levels"] = [hit.get("level") for hit in body["hits"]]
        self.observations.append(observed)
        return status, body


class Runner:
    def __init__(self, client):
        self.client = client
        self.results = []

    def run(self, identifier, check, scope="HTTP + isolated MySQL/Redis, demo user 1"):
        self.client.observations.clear()
        try:
            check()
            status, reason = "PASS", None
        except AssertionError as error:
            status, reason = "FAIL", str(error) or "Contract assertion failed"
        except (OSError, ValueError, TypeError, LookupError, subprocess.SubprocessError) as error:
            status, reason = "FAIL", type(error).__name__
        self.results.append(
            {
                "case_id": identifier,
                "status": status,
                "reason": reason,
                "execution_scope": scope,
                "observations": list(self.client.observations),
            }
        )

    def blocked(self, identifier, reason, observations=None):
        self.results.append(
            {
                "case_id": identifier,
                "status": "BLOCKED",
                "reason": reason,
                "execution_scope": "Dependency not implemented/approved",
                "observations": observations or [],
            }
        )
