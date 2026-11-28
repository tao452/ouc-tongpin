import json

import pytest

from app.services.moderation import ModerationService
from scripts.evaluate_candidate import ROOT


@pytest.fixture(scope="module")
def service():
    return ModerationService(ROOT / "services/algo/app/data/moderation-v3_5-candidate.json")


def test_additional_normal_contexts_and_attack_controls_stay_in_the_same_dataset(service):
    path = ROOT / "docs/qa/data/us24-context-stress.v1.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 102 and sum(not row["offensive"] for row in rows) == 90
    assert all(bool(service.check(row["text"]).hits) == row["offensive"] for row in rows)


@pytest.mark.parametrize("left,right", [("'", "'"), ("‘", "’")])
@pytest.mark.parametrize("prefix,suffix", [
    ("举报：", "请处理"), ("有人威胁我：", "让我很害怕"),
    ("语言科普：", "是侮辱性表达"), ("不要对同学说", ""),
])
def test_extra_quote_pairs_remain_confined_to_an_explicit_template(
        service, left, right, prefix, suffix):
    report = prefix + left + "杀了你" + right + suffix
    assert service.check(report).hits == []
    assert not service.check(report + "。杀了你").passed
