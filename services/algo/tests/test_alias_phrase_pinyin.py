import json

import pytest

from app.services.moderation import ModerationService
from scripts.evaluate_candidate import ROOT


@pytest.fixture(scope="module")
def service():
    return ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_12-candidate.json")


def test_selected_alias_forms_keep_their_canonical_mapping_and_context(service):
    path = ROOT / "docs/qa/data/us24-development.v3_12.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        result = service.check(row["text"])
        assert result.passed == (not row["blocked"]), row["id"]
        assert [h.model_dump() for h in result.hits] == row["expected_hits"], row["id"]


def custom_service(tmp_path, entry):
    path = tmp_path / "words.json"
    path.write_text(json.dumps([entry]), encoding="utf-8")
    return ModerationService(path)


@pytest.mark.parametrize("changes", [
    {"pinyin": False},
    {"pinyin_phrases": [{"phrase": "没有登记"}]},
    {"pinyin_phrases": [{"phrase": "我要揍你"}]},
    {"pinyin_phrases": [{"phrase": "wo yao da ni"}]},
    {"pinyin_phrases": [{"phrase": "我要打你"}, {"phrase": "我要打你"}]},
    {"pinyin_phrases": [{"phrase": "我要打你", "readings": [""]}]},
    {"pinyin_phrases": [{"phrase": "我要打你", "readings": ["a" * 129]}]},
    {"pinyin_phrases": [{"phrase": "我要打你", "readings": ["wo yao da"]}]},
    {"pinyin_phrases": [{"phrase": "我要打你", "readings": ["wo yao wrong ni"]}]},
    {"pinyin_phrases": [{"phrase": "我要打你", "tone_readings": ["wo3 yao4 da0 ni3"]}]},
    {"pinyin_phrases": [{"phrase": "我要打你", "extra": True}]},
    {"pinyin_phrases": [{"phrase": "我要打你", "tone_readings": ["wo3 yao4 da3 ni3"]}],
     "pinyin_tone_numbers": False},
    {"aliases": [], "targeted_aliases": ["我要打你"]},
    {"pinyin_phrases": [{"phrase": "我要打你"}] * 7},
])
def test_alias_phrase_schema_rejects_unmapped_or_unbounded_forms(tmp_path, changes):
    entry = dict(word="我要揍你", level="HIGH", aliases=["我要打你"], pinyin=True,
                 pinyin_tone_numbers=True, pinyin_phrases=[{"phrase": "我要打你"}])
    entry.update(changes)
    with pytest.raises(ValueError):
        custom_service(tmp_path, entry)


def test_aliases_share_the_parent_phoneme_path_limit(tmp_path):
    aliases = ["我要打你", "打断你腿", "给你一刀", "我就打你", "泼他硫酸"]
    entry = dict(word="重重", level="LOW", pinyin=True,
                 pinyin_readings=["zhong zhong", "zhong chong", "chong zhong"],
                 aliases=aliases, pinyin_phrases=[dict(phrase=s) for s in aliases])
    with pytest.raises(ValueError, match="Too many entry pinyin"):
        custom_service(tmp_path, entry)


def test_aliases_and_typo_keys_share_the_parent_compiled_key_limit(tmp_path):
    aliases = ["我要打你", "打断你腿", "给你一刀", "我就打你", "泼他硫酸", "全班嫌弃你"]
    entry = dict(word="测试", level="LOW", pinyin=True, aliases=aliases,
                 pinyin_phrases=[dict(phrase=s) for s in aliases],
                 pinyin_aliases=["zzone", "zztwo", "zzthree"])
    with pytest.raises(ValueError, match="Too many entry pinyin"):
        custom_service(tmp_path, entry)


def test_alias_numeric_tones_share_the_same_eight_path_limit(tmp_path):
    tones = [f"chong{a} chong{b}" for a, b in [
        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (2, 1), (2, 3)]]
    entry = dict(word="重重", level="LOW", pinyin=True, pinyin_tone_numbers=True,
                 pinyin_tone_readings=tones, aliases=["我要打你"],
                 pinyin_phrases=[dict(phrase="我要打你")])
    with pytest.raises(ValueError, match="Too many entry pinyin"):
        custom_service(tmp_path, entry)


def test_homophonic_aliases_cannot_hide_a_cross_rule_level_conflict(tmp_path):
    path = tmp_path / "conflict.json"
    path.write_text(json.dumps([
        dict(word="测试", level="LOW", aliases=["楚胜"], pinyin=True,
             pinyin_phrases=[dict(phrase="楚胜")]),
        dict(word="畜生", level="HIGH", pinyin=True),
    ]), encoding="utf-8")
    with pytest.raises(ValueError, match="Conflicting dictionary variants"):
        ModerationService(path)


def test_alias_prefix_and_typo_joining_are_distinct(tmp_path):
    service = custom_service(tmp_path, dict(
        word="我要揍你", level="HIGH", aliases=["再说我就打你"], pinyin=True,
        pinyin_tone_numbers=True, pinyin_aliases=["woyaozan"],
        pinyin_phrases=[dict(phrase="再说我就打你")]))
    assert "zai" in service.numeric_prefixes.values()
    assert not service.check("zai4 shuo1 wo3 jiu4 da3 ni3").passed
    assert not service.check("woyaozan").passed
    assert service.check("wo yao zan").hits == []


def test_long_denial_needs_a_complete_registered_pinyin_phrase(service):
    quote = "wang3 ni3 lian3 shang4 po1 liu2 suan1"
    assert len(quote) > 32
    assert service.check("我不会" + quote).hits == []
    assert not service.check("我不会" + quote + "才怪").passed
    assert not service.self_context("denial", "你" * 33)
    assert not service.self_context("denial", "this is an unrelated long English explanation")


def test_old_dictionary_does_not_enable_the_new_alias_phrases(service):
    text = "zai4 shuo1 wo3 jiu4 da3 ni3"
    old = ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_11-candidate.json")
    assert old.check(text).hits == []
    assert ModerationService().check(text).hits == []
    assert not service.check(text).passed
