import json

import pytest

from app.services.moderation import ModerationService
from app.services.moderation_context import context_spans
from scripts.evaluate_candidate import ROOT, assess, development

DATA = ROOT / "services/algo/app/data"


@pytest.fixture(scope="module")
def candidate():
    return ModerationService(DATA / "moderation-v3_5-candidate.json")


def test_new_rules_cover_explicit_variants_and_retain_all_normal_context_cases(candidate):
    result = assess(development(ROOT / "docs/qa/data/us24-development.v3_5.jsonl"), candidate)
    assert result["count"] == 544
    assert result["mapping_failure_ids"] == result["decision_failure_ids"] == []
    assert result["any_level"]["confusion_matrix"] == dict(tp=304, fp=0, fn=0, tn=240)


@pytest.mark.parametrize("word", ["泼你硫酸", "捅你一刀", "骚扰到你退学", "堵到你不敢出门"])
def test_exact_denial_and_reported_reversal_do_not_hide_an_unquoted_attack(candidate, word):
    assert candidate.check("我不会" + word).hits == []
    assert word in {h.word for h in candidate.check("我不会" + word + "才怪").hits}
    report = f'举报：“我不会{word}才怪”请处理'
    assert candidate.check(report).hits == []
    assert word in {h.word for h in candidate.check(report + "。" + word).hits}


@pytest.mark.parametrize("word", ["杀了你", "泼你硫酸"])
def test_reversal_quote_recognition_requires_one_complete_known_token(candidate, word):
    assert candidate.known_targeted_quote("我不会" + word + "才怪")
    assert not candidate.known_targeted_quote("我不会" + word + "。捅你一刀才怪")
    assert word in {h.word for h in candidate.check("我不会" + word + "，如果你道歉").hits}


def test_new_version_extends_the_existing_dictionary_without_rewriting_old_rules():
    old = json.loads((DATA / "moderation-v3_4-candidate.json").read_text(encoding="utf-8"))
    new = json.loads((DATA / "moderation-v3_5-candidate.json").read_text(encoding="utf-8"))
    assert len(new) == 132 and new[:120] == old
    assert ModerationService().check("泼你硫酸").hits == []


def test_quote_recognition_cache_cannot_carry_a_rule_into_another_request():
    text = '举报：“杀了你”请处理。' * 3
    assert len(context_spans(text, {"杀了你"})) == 3
    assert context_spans(text, set()) == []
