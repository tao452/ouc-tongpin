"""Actual HTTP checks against an owned local score service and its public gateway."""

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


def local_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("Use an owned loopback test service")
    return value.rstrip("/")


def execute(base, gateway):
    base, gateway = local_url(base), local_url(gateway)
    records = []

    def call(name, host, path, payload, expected, check=None):
        raw = (payload if isinstance(payload, bytes)
               else json.dumps(payload, ensure_ascii=False).encode())
        request = urllib.request.Request(host + path, data=raw,
                                        headers={"Content-Type": "application/json"})
        started = time.perf_counter()
        try:
            response = urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read(131073)
            status = response.code
            text = content.decode("utf-8", errors="replace")
            body = (json.loads(text) if response.headers.get_content_type() == "application/json"
                    else text)
            fingerprint = response.headers.get("X-Score-Config-SHA256")
        row = dict(test=name, method="POST", path=path, expected_status=expected,
                   status_code=status, elapsed_ms=round((time.perf_counter()-started)*1000, 3),
                   request=payload if not isinstance(payload, bytes) else {
                       "synthetic_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
                   response=body, response_sha256=hashlib.sha256(content).hexdigest())
        try:
            assert status == expected, f"Expected {expected}, got {status}"
            if check:
                check(body, fingerprint)
            row["status"] = "PASS"
        except (AssertionError, KeyError, TypeError) as error:
            row.update(status="FAIL", reason=str(error))
        records.append(row)
        return body

    profile = {"emotion_vector": [1, 0, 0, 0, 0, 0], "interests": ["Python"],
               "availability": [{"start": "2026-12-01T10:00:00+08:00",
                                 "end": "2026-12-01T12:00:00+08:00"}],
               "location": {"lat": 36, "lng": 120}}
    candidate = {"id": "synthetic-a", **profile}

    def perfect(body, fingerprint):
        assert body["items"][0]["score"] == 100
        assert fingerprint == body["config_sha256"] and len(fingerprint) == 64
        assert body["fallback"] is False

    one = call("single-perfect", base, "/score", {"query": profile, "candidate": candidate},
               200, perfect)
    batch = call("batch-one", base, "/score", {"query": profile, "candidates": [candidate]},
                 200, perfect)
    if batch != one:
        records[-1].update(status="FAIL", reason="Single and batch response differ")
    offset_edge = {**profile, "availability": [{"start": "2026-12-01T10:00:00+18:00",
                                              "end": "2026-12-01T12:00:00+18:00"}]}
    call("legal-time-offset-edge", base, "/score", {"query": offset_edge,
         "candidate": {"id": "offset-edge", **offset_edge}}, 200, perfect)

    def zeros(body, _):
        assert [(x["id"], x["score"]) for x in body["items"]] == [("a", 0), ("z", 0)]

    call("missing-features", base, "/score", {"query": {}, "candidates": [
        {"id": "z"}, {"id": "a"}]}, 200, zeros)
    call("max-batch100", base, "/score", {"query": {}, "candidates": [
        {"id": str(i)} for i in range(100)]}, 200)
    for name, payload in [
        ("empty", {}), ("empty-batch", {"query": {}, "candidates": []}),
        ("duplicate", {"query": {}, "candidates": [candidate, candidate]}),
        ("over100", {"query": {}, "candidates": [{"id": str(i)} for i in range(101)]}),
        ("invalid-coordinate", {"query": {"location": {"lat": 90.1, "lng": 0}},
                                "candidate": candidate}),
        ("naive-time", {"query": {"availability": [{"start": "2026-12-01T09:00:00",
            "end": "2026-12-01T10:00:00"}]}, "candidate": candidate}),
        ("offset-minute-overflow", {"query": {"availability": [{
            "start": "2026-12-01T09:00:00+01:60", "end": "2026-12-02T10:00:00Z"}]},
            "candidate": candidate}),
        ("offset-out-of-range", {"query": {"availability": [{
            "start": "2026-12-01T09:00:00+19:00", "end": "2026-12-02T10:00:00Z"}]},
            "candidate": candidate}),
        ("utc-year-overflow", {"query": {"availability": [{
            "start": "0001-01-01T00:00:00+18:00", "end": "2026-12-02T10:00:00Z"}]},
            "candidate": candidate}),
    ]:
        call(name, base, "/score", payload, 400)
    call("score-body-limit", base, "/score", b"x" * 131073, 413)
    call("moderation-body-limit", base, "/api/moderation/check", b"x" * 16385, 413)
    call("internal-route-not-public", gateway, "/score", {"query": {}, "candidate": candidate}, 404)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18000")
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve earlier evidence; choose a new output path")
    records = execute(args.base_url, args.gateway_url)
    report = dict(source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"],
        text=True).strip(), executed_at_utc=datetime.now(UTC).isoformat(),
        scope="Actual HTTP to owned Docker; synthetic profiles only", results=records,
        passed=sum(x["status"] == "PASS" for x in records),
        failed=sum(x["status"] == "FAIL" for x in records))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["passed", "failed"]}))
    return int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
