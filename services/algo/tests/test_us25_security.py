"""Exercise transient PII scanning and credential-safe runtime helpers offline."""

import base64
import hashlib
import hmac
import importlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "scripts/qa"))
    return (importlib.import_module("us25_privacy_runtime"),
            importlib.import_module("us25_security_cases"))


def test_signed_negative_fixtures_keep_real_signature_and_change_only_claims(modules):
    _, cases = modules
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
    actor = SimpleNamespace(token=encode({"alg": "HS256"}) + "." + encode({"sub": "7"}) + ".x")
    key = "private-fixture-key-not-a-real-runtime-key"
    token = cases.signed_claims(actor, key, exp=1)
    header, payload, signature = token.split(".")
    expected = hmac.new(key.encode(), (header + "." + payload).encode(), hashlib.sha256).digest()
    assert base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)) == expected
    assert json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))) == {
        "sub": "7", "exp": 1}


class RuntimeFixture:
    def sql(self, statement):
        if statement.startswith("UPDATE"):
            return ""
        return "studentNo=SYNTHETICSTUDENT001 phone=13900001234 openid=anon_v1_fixture"

    def execute(self, *args):
        return "Safe runtime output without credentials"


def test_runtime_scan_preserves_positive_control_without_retaining_private_values(modules):
    runtime, _ = modules
    actors = [SimpleNamespace(user_id=n, token=f"PRIVATE-TOKEN-{n}") for n in (1, 2)]
    report = runtime.scan_runtime(RuntimeFixture(), actors, '{"items":[]}', ["PRIVATE-SECRET"])
    assert report["private_positive_control_matched"] is True
    assert report["channels"]["private_auth"]["candidate_lines"] == 1
    assert report["channels"]["public_responses"]["candidate_lines"] == 0
    assert report["raw_material_retained"] is False
    text = json.dumps(report)
    for private in ("13900001234", "SYNTHETICSTUDENT001", "PRIVATE-TOKEN", "PRIVATE-SECRET"):
        assert private not in text


@pytest.mark.parametrize("leak", ["13900001234", "PRIVATE-TOKEN-1", "PRIVATE-SECRET"])
def test_runtime_canary_leaks_fail_with_no_value_in_error(modules, leak):
    runtime, _ = modules
    actors = [SimpleNamespace(user_id=n, token=f"PRIVATE-TOKEN-{n}") for n in (1, 2)]
    with pytest.raises(AssertionError) as error:
        runtime.scan_runtime(RuntimeFixture(), actors, leak, ["PRIVATE-SECRET"])
    assert leak not in str(error.value)


def test_reader_password_uses_stdin_and_private_file_not_argv(modules, monkeypatch):
    runtime, _ = modules
    statements, calls = [], []
    stack = runtime.PrivacyStack()
    monkeypatch.setattr(stack, "root_sql", lambda sql: statements.append(sql))
    monkeypatch.setattr(runtime.secrets, "token_hex", lambda length: "f" * (length * 2))

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="1", stderr="")
    monkeypatch.setattr(runtime.subprocess, "run", run)
    with stack.public_reader() as query:
        assert query("SELECT COUNT(*) FROM treehole_public").stdout == "1"
    command, arguments = calls[0]
    assert "f" * 48 not in " ".join(command)
    assert "password=" + "f" * 48 in arguments["input"]
    assert "umask 077" in " ".join(command)
    assert statements[-1].startswith("DROP USER IF EXISTS")


def test_failed_setup_report_contains_only_safe_diagnostics(modules, monkeypatch, tmp_path, capsys):
    main = importlib.import_module("run_us25_security")
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    (tmp_path / ".env").write_text("WX_MOCK_ENABLED=true\nJWT_SECRET=PRIVATE-SECRET\n")

    def failure(base, values, diagnostics):
        diagnostics["stage"] = "database_reader_setup"
        raise subprocess.CalledProcessError(1, ["PRIVATE-SQL"], stderr="ERROR 1396 PRIVATE-SECRET")
    monkeypatch.setattr(main, "execute", failure)
    output = tmp_path / "qa-private/report.json"
    assert main.main(["--output", str(output)]) == 2
    report = json.loads(output.read_text())
    assert report["verification_complete"] is False
    assert report["failure_stage"] == "database_reader_setup"
    assert report["mysql_error_code"] == "1396"
    assert "PRIVATE" not in output.read_text() + capsys.readouterr().err


def test_initialization_diagnostics_exclude_container_log_material(modules, monkeypatch):
    runtime, _ = modules
    stack = runtime.PrivacyStack()
    monkeypatch.setattr(stack, "root_sql", lambda sql: "0\t0")
    monkeypatch.setattr(stack, "execute", lambda *args:
                        "running 02-runtime-permissions.sh ERROR 2002 PRIVATE-SECRET Can't connect")
    report = stack.permission_diagnostics()
    assert report["role_and_view_counts"] == [0, 0]
    assert report["mysql_error_codes"] == ["2002"]
    assert report["connection_error"] is True
    assert "PRIVATE" not in json.dumps(report)
