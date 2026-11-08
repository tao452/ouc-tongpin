import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "evaluate_dataset", Path(__file__).resolve().parents[1] / "scripts/evaluate_dataset.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def write_samples(tmp_path, rows):
    path = tmp_path / "examples.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return path


def sample(number, text="你好", passed=True):
    return {"id": str(number), "text": text, "expected_passed": passed}


def test_confusion_matrix_has_known_counts():
    records = [sample(1, "傻逼", False), sample(2, "你好", True),
               sample(3, "你好", False), sample(4, "傻逼", True)]
    result = evaluation.evaluate(records, evaluation.ModerationService())
    assert result["confusion_matrix"] == {"tp": 1, "fp": 1, "tn": 1, "fn": 1}
    assert result["recall"] == result["false_positive_rate"] == 0.5
    assert result["thresholds_met_on_supplied_rows"] is False


@pytest.mark.parametrize("rows", [[], [sample(1), sample(1)], [sample(1, passed="true")],
                                     [{"id": "1"}], [sample(1, text=" ")], [None]])
def test_invalid_dataset_is_rejected(tmp_path, rows):
    with pytest.raises(ValueError):
        evaluation.load_samples(write_samples(tmp_path, rows))


def test_cli_success_failure_and_inconclusive(tmp_path, capsys):
    valid = write_samples(tmp_path, [sample(1), sample(2, "傻逼", False)])
    assert evaluation.main([str(valid)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["dataset_sha256"]) == 64
    assert len(result["dictionary_sha256"]) == 64
    assert "傻逼" not in json.dumps(result)
    assert evaluation.main([str(write_samples(tmp_path, [sample(1)]))]) == 2
    failing = write_samples(tmp_path, [sample(1), sample(2, "你好", False)])
    assert evaluation.main([str(failing)]) == 1
    assert evaluation.main([str(tmp_path / "missing")]) == 2


def test_invalid_cli_output_never_echoes_input(tmp_path, capsys):
    path = write_samples(tmp_path, [{"secret": "PRIVATE-VALUE"}])
    assert evaluation.main([str(path)]) == 2
    captured = capsys.readouterr()
    assert "PRIVATE-VALUE" not in captured.out + captured.err
