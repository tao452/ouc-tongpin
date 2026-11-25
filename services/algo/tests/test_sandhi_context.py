import json

import pytest

from app.services.moderation import ModerationService
from app.services.pronunciation import MAX_READINGS, numeric_tone_patterns
from scripts.evaluate_candidate import ROOT


@pytest.fixture(scope="module")
def service():
    return ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_11-candidate.json")


def test_explicit_sandhi_paths_and_normal_context_regressions(service):
    path = ROOT / "docs/qa/data/us24-development.v3_11.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        result = service.check(row["text"])
        assert result.passed == (not row["blocked"]), row["id"]
        assert [hit.model_dump() for hit in result.hits] == row["expected_hits"], row["id"]


@pytest.mark.parametrize("template", [
    "请不要说“{}”伤害同学", "语言科普：“{}”是攻击表达",
])
def test_exact_context_keeps_outside_and_embedded_attacks(service, template):
    attack = "ni3 bu2 pei4 huo2 zhe5"
    assert service.check(template.format(attack)).hits == []
    assert not service.check(template.format(attack) + "。杀了你").passed
    assert not service.check("杀了你。" + template.format(attack)).passed
    assert not service.check(template.format(attack + "。杀了你")).passed
    assert not service.check(template.format("任意说明，" + attack)).passed


def test_quote_words_alone_do_not_exempt_or_change_the_s1_policy(service):
    assert not service.check("请不要说" + "ni3 bu2 pei4 huo2 zhe5").passed
    assert not service.check("语言科普：ni3 bu2 pei4 huo2 zhe5").passed
    medium = service.check("ni3 bu2 pei4 fa1 yan2")
    assert medium.passed
    assert [(h.word, h.level) for h in medium.hits] == [("你不配发言", "MEDIUM")]


def test_sandhi_paths_are_explicit_bounded_and_keep_rollback():
    path = ROOT / "services/algo/app/data/moderation-v3_11-candidate.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    assert len(entries) == 132
    for entry in entries:
        if entry.get("pinyin_tone_numbers"):
            patterns = numeric_tone_patterns(entry["word"], entry.get("pinyin_readings", []),
                                            entry.get("pinyin_tone_readings", []))
            assert len(patterns) <= MAX_READINGS
    old = ModerationService(path.with_name("moderation-v3_10-candidate.json"))
    assert old.check("ni3 bu2 pei4 huo2 zhe5").hits == []
    assert ModerationService().check("ni3 bu2 pei4 huo2 zhe5").hits == []
    assert not old.check("ni3 bu4 pei4 huo2 zhe5").passed
