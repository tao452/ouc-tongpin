import json

from app.services.moderation import ModerationService
from scripts.evaluate_candidate import ROOT


def test_normal_homophones_keep_per_rule_and_per_occurrence_scope():
    service = ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_13-candidate.json")
    fixture = ROOT / "docs/qa/data/us24-development.v3_13.jsonl"
    for line in fixture.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        result = service.check(row["text"])
        assert result.passed == (not row["blocked"]), row["id"]
        assert [hit.model_dump() for hit in result.hits] == row["expected_hits"], row["id"]


def test_normal_phone_and_food_phrases_do_not_disable_the_parent_rules():
    service = ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_13-candidate.json")
    for text in ["wo yao da ni", "gei ni yi dao", "da duan ni tui"]:
        assert not service.check(text).passed
    assert service.check("我要打你电话").hits == []
    assert service.check("gei ni yi dao ti").hits == []
    assert not service.check("我要打你。电话明天再说").passed
    assert not service.check("wo yao da ni dian hua，wo yao da ni").passed
    assert not service.check("gei ni yi dao ti，gei ni yi dao").passed
