import importlib
import io
import json
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def load(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/qa"))
    return importlib.import_module("run_w3_load")


class Response(io.BytesIO):
    status = 200


def test_real_workers_overlap_and_report_contains_no_response_content(load, monkeypatch, tmp_path):
    active, maximum = 0, 0
    lock = threading.Lock()

    def respond(request, timeout):
        nonlocal active, maximum
        assert request.method == "GET"
        assert request.full_url.endswith(load.ENDPOINT)
        with lock:
            active += 1
            maximum = max(maximum, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return Response(b'{"items":[{"note":"PRIVATE-RESPONSE"}],"total":1}')

    monkeypatch.setattr(load, "urlopen", respond)
    output = tmp_path / "report.json"
    assert load.main(["--requests", "8", "--concurrency", "4", "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert maximum > 1
    assert report["requests"] == len(report["results"]) == 8
    assert report["status_counts"] == {"PASS": 8}
    assert report["error_rate"] == 0
    assert report["requests_per_second"] > 0
    assert report["latency_ms"]["p50"] <= report["latency_ms"]["p95"]
    assert report["latency_ms"]["p95"] <= report["latency_ms"]["p99"]
    assert len(report["script_sha256"]) == 64
    assert report["executed_at_utc"].endswith("+00:00")
    assert "PRIVATE-RESPONSE" not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "response,expected",
    [
        (b"PRIVATE-NOT-JSON", "invalid_json"),
        (b'{"items":[],"total":true}', "invalid_structure"),
        (b'{"items":[],"total":1}', "invalid_structure"),
        (b'{"items":{},"total":0}', "invalid_structure"),
        (b"X" * (1024 * 1024 + 1), "response_too_large"),
    ],
)
def test_invalid_success_responses_are_failures(load, monkeypatch, response, expected):
    monkeypatch.setattr(load, "urlopen", lambda *args, **kwargs: Response(response))
    result = load.request_once("http://localhost:8080/", 1, 1)
    assert result["status"] == "FAIL"
    assert result["error"] == expected
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("kind", ["http", "transport"])
def test_failed_requests_save_metrics_without_url_or_error_body(load, monkeypatch, tmp_path, kind):
    def fail(*args, **kwargs):
        if kind == "http":
            raise HTTPError("http://PRIVATE-URL", 503, "PRIVATE-ERROR", {}, io.BytesIO(b"PRIVATE"))
        raise URLError("PRIVATE-TRANSPORT-ERROR")

    monkeypatch.setattr(load, "urlopen", fail)
    output = tmp_path / "report.json"
    assert load.main(["--requests", "2", "--concurrency", "2", "--output", str(output)]) == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status_counts"] == {"FAIL": 2}
    assert report["error_rate"] == 1
    assert "PRIVATE" not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "arguments",
    [
        ["--base-url", "https://example.com/PRIVATE"],
        ["--base-url", "http://PRIVATE@localhost:8080"],
        ["--base-url", "http://localhost:8080/?token=PRIVATE"],
        ["--base-url", "http://localhost:70000"],
        ["--requests", "0"],
        ["--requests", "1001"],
        ["--concurrency", "51"],
        ["--timeout", "nan"],
        ["--timeout", "31"],
        ["--requests", "PRIVATE"],
    ],
)
def test_bad_parameters_never_send_requests(load, monkeypatch, tmp_path, capsys, arguments):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid parameters must not send a request")

    monkeypatch.setattr(load, "urlopen", forbidden)
    output = tmp_path / "report.json"
    assert load.main([*arguments, "--output", str(output)]) == 2
    assert not output.exists()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PRIVATE" not in captured.err


def test_output_error_and_code_collision_return_two(load, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        load, "urlopen", lambda *args, **kwargs: Response(b'{"items":[],"total":0}')
    )
    parent = tmp_path / "not-directory"
    parent.write_text("original", encoding="utf-8")
    arguments = ["--requests", "1", "--concurrency", "1"]
    assert load.main([*arguments, "--output", str(parent / "report.json")]) == 2
    assert parent.read_text(encoding="utf-8") == "original"
    source = Path(load.__file__)
    original = source.read_bytes()
    assert load.main([*arguments, "--output", str(source)]) == 2
    assert source.read_bytes() == original
    assert capsys.readouterr().out == ""


def test_redirect_handler_refuses_remote_redirect(load):
    handler = load.NoRedirect()
    assert handler.redirect_request(None, None, 302, "", {}, "https://example.com") is None


def test_latency_percentiles_use_nearest_rank(load):
    timings = list(range(20, 0, -1))
    assert [load.percentile(timings, p) for p in (0.50, 0.95, 0.99)] == [10, 19, 20]
