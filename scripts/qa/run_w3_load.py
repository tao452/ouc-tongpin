"""Measure a small read-only HTTP workload against the local development stack."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from regression_http import Client

ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = "/api/emotions/checkins?from=2031-01-01&to=2031-01-31"
MAX_RESPONSE_BYTES = 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ParameterParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("Invalid load-check parameters")


# Keep even a local redirect or a configured proxy from sending this workload elsewhere.
urlopen = build_opener(ProxyHandler({}), NoRedirect()).open


def validate(args):
    parts = urlsplit(args.base_url)
    if (
        parts.scheme not in {"http", "https"}
        or parts.hostname not in {"127.0.0.1", "localhost"}
        or parts.username is not None
        or parts.password is not None
        or parts.path not in {"", "/"}
        or parts.query
        or parts.fragment
        or (parts.port is not None and not 1 <= parts.port <= 65535)
        or not 1 <= args.requests <= 1000
        or not 1 <= args.concurrency <= min(50, args.requests)
        or not math.isfinite(args.timeout)
        or not 0 < args.timeout <= 30
    ):
        raise ValueError("Invalid load-check parameters")
    source = Path(__file__).resolve()
    if args.output.resolve() == source or (
        args.output.exists() and args.output.samefile(source)
    ):
        raise ValueError("Output conflicts with load-check code")
    return f"{parts.scheme}://{parts.netloc}{ENDPOINT}"


def request_once(url, timeout, request_id, token=None):
    started = time.perf_counter()
    status, error = None, None
    try:
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            if status != 200:
                error = "http_status"
            else:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    error = "response_too_large"
                else:
                    try:
                        data = json.loads(body.decode("utf-8"))
                    except (UnicodeError, ValueError):
                        error = "invalid_json"
                    else:
                        if (
                            not isinstance(data, dict)
                            or not isinstance(data.get("items"), list)
                            or type(data.get("total")) is not int
                            or data["total"] != len(data["items"])
                        ):
                            error = "invalid_structure"
    except HTTPError as exc:
        status, error = exc.code, "http_status"
        exc.close()
    except (OSError, HTTPException, ValueError):
        error = "transport_error"
    return {
        "request_id": request_id,
        "status": "PASS" if error is None else "FAIL",
        "http_status": status,
        "error": error,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 6),
    }


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * fraction) - 1]


def source_metadata():
    result = {
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_revision": None,
        "working_tree_dirty": None,
    }
    try:
        result["source_revision"] = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).strip()
        result["working_tree_dirty"] = bool(
            subprocess.check_output(
                ["git", "-C", str(ROOT), "status", "--porcelain"],
                text=True,
                timeout=5,
                stderr=subprocess.DEVNULL,
            ).strip()
        )
    except (OSError, subprocess.SubprocessError):
        pass
    return result


def execute(url, requests, concurrency, timeout, token=None):
    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(
            executor.map(lambda index: request_once(url, timeout, index, token),
                         range(1, requests + 1))
        )
    duration = max(time.perf_counter() - started, 1e-9)
    passed = sum(row["status"] == "PASS" for row in results)
    timings = [row["elapsed_ms"] for row in results]
    return {
        "started_at_utc": started_at,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        **source_metadata(),
        "scope": "Small local development demonstration using read-only check-in queries. "
        "Not acceptance evidence for 500/1000 concurrent users, production capacity, "
        "real WeChat login, or multi-user authorization.",
        "endpoint": ENDPOINT,
        "requests": requests,
        "concurrency": concurrency,
        "timeout_seconds": timeout,
        "duration_seconds": round(duration, 6),
        "requests_per_second": round(requests / duration, 6),
        "successful_requests_per_second": round(passed / duration, 6),
        "status_counts": dict(Counter(row["status"] for row in results)),
        "error_rate": (requests - passed) / requests,
        "percentile_method": "nearest_rank; request service time excludes executor queue wait",
        "latency_ms": {
            "p50": percentile(timings, 0.50),
            "p95": percentile(timings, 0.95),
            "p99": percentile(timings, 0.99),
        },
        "results": results,
    }


def save_report(output, report):
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, prefix=".w3-load-", delete=False
        ) as target:
            temporary = Path(target.name)
            json.dump(report, target, ensure_ascii=False, indent=2)
            target.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = ParameterParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--login", action="store_true",
                        help="Use a fixture login on the isolated stack")
    try:
        args = parser.parse_args(argv)
        url = validate(args)
        token = Client(args.base_url).authenticate().token if args.login else None
        report = execute(url, args.requests, args.concurrency, args.timeout, token)
        save_report(args.output, report)
    except (OSError, ValueError, TypeError):
        print("Load check failed: parameters or output are invalid", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "requests", "concurrency", "requests_per_second", "error_rate", "latency_ms"
                )
            }
        )
    )
    return int(report["error_rate"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
