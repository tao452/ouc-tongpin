from pathlib import Path

import pytest

from app.services.moderation import ModerationService
from scripts.evaluate_candidate import ROOT, assess, development


@pytest.fixture(scope="module")
def context_candidate():
    return ModerationService(Path(__file__).resolve().parents[1]
                             / "app/data/moderation-v3_1-candidate.json")


def test_exact_local_self_help_no_longer_adds_an_abuse_hit(context_candidate):
    result = context_candidate.check("我觉得自己一无是处，我是不是废物，想求助")
    assert result.passed and result.hits == []


@pytest.mark.parametrize("attack", ["你是个废物", "你就是鲨币", "杀了你"])
def test_help_exemption_does_not_hide_a_separate_attack(context_candidate, attack):
    result = context_candidate.check("我是不是废物，想求助。" + attack)
    assert result.hits
    assert result.passed == (attack == "你是个废物")


def test_help_keyword_alone_is_not_a_global_allowlist(context_candidate):
    result = context_candidate.check("我想求助，你是个废物，杀了你")
    assert not result.passed
    assert "废物" in {h.word for h in result.hits}


def test_unchanged_development_ids_and_labels_remain_in_evaluation(context_candidate):
    result = assess(development(ROOT / "docs/qa/data/us24-development.v3.jsonl"),
                    context_candidate)
    assert result["count"] == 406
    assert result["mapping_failure_ids"] == []
    assert result["decision_failure_ids"] == []
    assert result["any_level"]["confusion_matrix"]["fp"] == 0
