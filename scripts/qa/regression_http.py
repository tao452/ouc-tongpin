"""HTTP regression evidence without input text, tokens, identities or response bodies."""

import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.client import HTTPException


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class Client:
    def __init__(self, base, token=None, user_id=None):
        self.base = base.rstrip("/")
        self.token, self.user_id = token, user_id
        self.observations = []

    def authenticate(self, code=None):
        status, body = self.request("/api/auth/login", {"code": code or "qa-" + uuid.uuid4().hex})
        expect(status == 200 and isinstance(body, dict), "Isolated identity login failed")
        expect(isinstance(body.get("token"), str) and str(body.get("userId", "")).isdigit(),
               "Login must return a token and server identity")
        self.token, self.user_id = body["token"], int(body["userId"])
        return self

    def request(self, path, payload=None, raw=None, headers=None, method=None):
        data = (
            raw
            if raw is not None
            else (
                json.dumps(payload, ensure_ascii=False).encode("utf-8")
                if payload is not None
                else None
            )
        )
        request_headers = {"Content-Type": "application/json"}
        if self.token is not None:
            request_headers["Authorization"] = "Bearer " + self.token
        request_headers.update(headers or {})
        request = urllib.request.Request(self.base + path, data=data, headers=request_headers,
                                         method=method)
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
                    value = body[field]
                    valid = (
                        type(value) is bool
                        if field in {"passed", "isNewUser", "needStudentVerify"}
                        else type(value) is int and value >= 0
                    )
                    if valid:
                        observed[field] = value
                    else:
                        invalid = observed.setdefault("invalid_response_fields", {})
                        invalid[field] = type(value).__name__
            if isinstance(body.get("hits"), list):
                observed["hit_levels"] = []
                invalid = 0
                for hit in body["hits"]:
                    level = hit.get("level") if isinstance(hit, dict) else None
                    if isinstance(level, str) and level in {"HIGH", "MEDIUM", "LOW"}:
                        observed["hit_levels"].append(level)
                    else:
                        invalid += 1
                if invalid:
                    observed["invalid_hit_levels"] = invalid
        self.observations.append(observed)
        return status, body


class Runner:
    def __init__(self, client):
        self.client = client
        self.results = []

    def run(self, identifier, check,
            scope="HTTP + isolated MySQL/Redis, authenticated test account"):
        self.client.observations.clear()
        try:
            check()
            status, reason = "PASS", None
        except AssertionError as error:
            status, reason = "FAIL", str(error) or "Contract assertion failed"
        except (
            OSError, HTTPException, ValueError, TypeError, LookupError, subprocess.SubprocessError
        ) as error:
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
