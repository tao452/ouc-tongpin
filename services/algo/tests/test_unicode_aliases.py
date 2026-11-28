import json

import pytest

from app.services.moderation import ModerationService
from app.services.targeted_matching import latin_boundary
from scripts.evaluate_candidate import ROOT

DATA = ROOT / "services/algo/app/data"


@pytest.fixture(scope="module")
def service():
    return ModerationService(DATA / "moderation-v3_9-candidate.json")


@pytest.mark.parametrize("neighbor", ["π", "Ж", "α", "δ", "é", "١", "_", "a", "9"])
def test_latin_boundary_keeps_unicode_identifier_neighbors(neighbor):
    assert not latin_boundary(neighbor + "shabi", 1, 6, "shabi")
    assert not latin_boundary("shabi" + neighbor, 0, 5, "shabi")


@pytest.mark.parametrize("neighbor", ["你", "𠮷", "。", " "])
def test_latin_boundary_retains_chinese_and_punctuation_neighbors(neighbor):
    assert latin_boundary(neighbor + "shabi", 1, 6, "shabi")
    assert latin_boundary("shabi" + neighbor, 0, 5, "shabi")


@pytest.mark.parametrize("token", ["shabi", "sha3bi1", "nongsini", "nong4si3ni3"])
def test_pinyin_and_numeric_tones_do_not_split_greek_identifiers(service, token):
    assert service.check("π" + token).hits == []
    assert service.check(token + "π").hits == []
    assert not service.check("你说" + token).passed


def test_registered_mixed_script_aliases_and_context_have_actual_expected_results(service):
    path = ROOT / "docs/qa/data/us24-development.v3_9.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 314
    for row in cases:
        result = service.check(row["text"])
        assert result.passed == (not row["blocked"]), row["id"]
        if row["expected_word"]:
            assert (row["expected_word"], row["expected_level"]) in {
                (h.word, h.level) for h in result.hits}, row["id"]
        else:
            assert result.hits == [], row["id"]


def test_visual_mapping_is_explicit_and_levels_and_previous_dictionary_are_preserved(service):
    before = json.loads((DATA / "moderation-v3_8-candidate.json").read_text(encoding="utf-8"))
    after = json.loads((DATA / "moderation-v3_9-candidate.json").read_text(encoding="utf-8"))
    assert len(after) == 132
    assert [(r["word"], r["level"]) for r in after] == [(r["word"], r["level"]) for r in before]
    changed = [i + 1 for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b]
    assert changed == [1, 2, 4, 15]
    assert sum(len(b.get("aliases", [])) - len(a.get("aliases", []))
               for a, b in zip(before, after, strict=True)) == 12
    assert ModerationService(DATA / "moderation-v3_8-candidate.json").check("ѕhаbі").hits == []
    assert ModerationService().check("ѕhаbі").hits == []
    # No automatic confusable alphabet is inferred from the twelve registrations.
    assert service.check("shαbi").hits == []
    assert len(service.check("ѕhаbі shаbi sһabi").hits) == 1


def test_deduplication_keeps_distinct_longer_entries_with_the_same_prefix(tmp_path):
    path = tmp_path / "prefixes.json"
    path.write_text(json.dumps([{"word": "辱骂", "level": "MEDIUM"},
                               {"word": "辱骂攻击", "level": "HIGH"}]), encoding="utf-8")
    result = ModerationService(path).check("辱骂。辱骂攻击")
    assert {(h.word, h.level) for h in result.hits} == {
        ("辱骂", "MEDIUM"), ("辱骂攻击", "HIGH")}
    assert not result.passed


def test_exempt_repeated_quotes_do_not_hide_a_later_unprotected_attack(service):
    quote = "举报：‘ѕhаbі’请处理。"
    assert service.check(quote * 5).hits == []
    result = service.check(quote * 5 + "ѕhаbі。nong4si3ni3")
    assert {h.word for h in result.hits} == {"傻逼", "弄死你"}
    assert not result.passed
