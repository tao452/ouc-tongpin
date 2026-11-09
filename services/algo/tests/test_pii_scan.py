import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "pii_scan", Path(__file__).resolve().parents[3] / "scripts/qa/pii_scan.py"
)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


@pytest.mark.parametrize(
    "text,rule",
    [
        ("phone=13800000000", "phone"),
        ("identity=11000020000101000X", "identity_number"),
        ('{"studentId":"202600000001"}', "student_field"),
        ("student_id=abcdef123", "student_field"),
        ("test@example.com", "email"),
        ('{"token":"abcdef123"}', "credential_field"),
        ("Authorization: Bearer abc.def.ghi", "authorization"),
    ],
)
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


@pytest.mark.parametrize(
    "text,rule",
    [
        ("phone=+8613800000000", "phone"),
        ("phone=008613800000000", "phone"),
        ("phone=8613800000000", "phone"),
        ("student_no=202600000001", "student_field"),
        ("studentNo=SYNTH2026001", "student_field"),
        ("学号：202600000001", "student_field"),
        ("open_id=synthetic-openid", "credential_field"),
        ("sessionKey=synthetic-session", "credential_field"),
        ("apiKey=synthetic-api", "credential_field"),
    ],
)
def test_common_export_field_variants(tmp_path, text, rule):
    path = tmp_path / "synthetic.txt"
    path.write_text(text, encoding="utf-8")
    assert rule in scanner.scan([path])["findings"][0]["rules"]


@pytest.mark.parametrize(
    "text",
    [
        "notstudentId=202600000001",
        "notsecret=synthetic-value",
        "NotBearer synthetic-value",
    ],
)
def test_similar_field_prefixes_do_not_match(tmp_path, text):
    path = tmp_path / "synthetic.txt"
    path.write_text(text, encoding="utf-8")
    assert scanner.scan([path])["findings"] == []


def test_saved_report_has_no_values_or_paths(tmp_path, capsys):
    source = tmp_path / "PRIVATE-FILENAME.txt"
    source.write_text("token=PRIVATE-SYNTHETIC-VALUE", encoding="utf-8")
    output = tmp_path / "report.json"
    assert scanner.main([str(source), "--output", str(output)]) == 1
    content = output.read_text(encoding="utf-8") + capsys.readouterr().out
    assert "PRIVATE-FILENAME" not in content
    assert "PRIVATE-SYNTHETIC-VALUE" not in content


def test_unwritable_report_is_an_error(tmp_path, capsys):
    source = tmp_path / "synthetic.txt"
    source.write_text("status=200", encoding="utf-8")
    parent = tmp_path / "file-not-directory"
    parent.write_text("fixture", encoding="utf-8")
    assert scanner.main([str(source), "--output", str(parent / "report.json")]) == 2
    assert capsys.readouterr().out == ""
