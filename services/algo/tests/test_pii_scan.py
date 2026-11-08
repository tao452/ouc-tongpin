import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "pii_scan", Path(__file__).resolve().parents[3] / "scripts/qa/pii_scan.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


@pytest.mark.parametrize("text,rule", [
    ("phone=13800000000", "phone"), ("identity=11000020000101000X", "identity_number"),
    ('{"studentId":"202600000001"}', "student_field"), ("student_id=abcdef123", "student_field"),
    ("test@example.com", "email"), ('{"token":"abcdef123"}', "credential_field"),
    ("Authorization: Bearer abc.def.ghi", "authorization"),
])
def test_finds_candidates_without_echoing_values(tmp_path, text, rule):
    path = tmp_path / "sample.txt"
    path.write_text(text, encoding="utf-8")
    result = scanner.scan([path])
    assert rule in result["findings"][0]["rules"]
    assert text not in json.dumps(result)
    assert result["findings"][0]["line"] == 1


def test_clean_and_masked_values(tmp_path, capsys):
    path = tmp_path / "sample.txt"
    path.write_text("status=200 duration=30ms\ntoken=[REDACTED]\n", encoding="utf-8")
    assert scanner.main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "no_rule_matches"
    path.write_text("phone=13800000000", encoding="utf-8")
    assert scanner.main([str(path)]) == 1
    assert "13800000000" not in capsys.readouterr().out


def test_failed_scan_never_claims_pass(tmp_path, capsys):
    assert scanner.main([str(tmp_path / "missing")]) == 2
    assert capsys.readouterr().out == ""
    path = tmp_path / "binary.txt"
    path.write_bytes(b"\0")
    assert scanner.main([str(path)]) == 2
    path.write_bytes(b"\xff")
    assert scanner.main([str(path)]) == 2
