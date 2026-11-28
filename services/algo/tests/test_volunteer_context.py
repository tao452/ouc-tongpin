import json

import pytest
from pydantic import ValidationError

from app.models.dictionary import DictionaryEntry
from app.services.moderation import ModerationService
from scripts.evaluate_candidate import ROOT

DATA = ROOT / "services/algo/app/data"


@pytest.fixture(scope="module")
def service():
    return ModerationService(DATA / "moderation-v3_8-candidate.json")


def test_exact_volunteer_phrases_can_reference_a_registered_targeted_alias():
    DictionaryEntry(word="你个智障", level="MEDIUM", targeted_aliases=["智障"],
                    allow_phrases=["智障人士服务中心的志愿者"])
    for phrase in ["智障", "关爱人士服务中心的志愿者"]:
        with pytest.raises(ValidationError):
            DictionaryEntry(word="你个智障", level="MEDIUM", targeted_aliases=["智障"],
                            allow_phrases=[phrase])


def test_volunteer_context_and_mapped_hanzi_cases_have_actual_expected_decisions(service):
    path = ROOT / "docs/qa/data/us24-development.v3_8.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(cases) == 68
    for row in cases:
        result = service.check(row["text"])
        assert result.passed == (not row["blocked"]), row["id"]
        if row["expected_word"]:
            assert (row["expected_word"], row["expected_level"]) in {
                (h.word, h.level) for h in result.hits}, row["id"]
        else:
            assert result.hits == [], row["id"]


def test_the_exemption_does_not_bridge_clauses_or_remove_a_full_direct_insult(service):
    for text in ["你是智障。人士服务中心的志愿者", "你个智障人士服务中心的志愿者"]:
        assert "你个智障" in {h.word for h in service.check(text).hits}
    assert not service.check("室友是智障人士服务中心的志愿者。杀了你").passed


def test_new_candidate_changes_only_two_entries_and_preserves_all_risk_levels():
    original = json.loads((DATA / "moderation-v3_5-candidate.json").read_text(encoding="utf-8"))
    current = json.loads((DATA / "moderation-v3_8-candidate.json").read_text(encoding="utf-8"))
    assert len(current) == 132
    changed = [i + 1 for i, (a, b) in enumerate(zip(original, current, strict=True)) if a != b]
    assert changed == [77, 78]
    assert [(r["word"], r["level"]) for r in original] == [(r["word"], r["level"]) for r in current]
    assert ModerationService().check("你个脑摊").hits == []
