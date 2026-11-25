import json

import pytest

from app.services.moderation import ModerationService, _inside_phrase, _phrase_index
from scripts.evaluate_candidate import ROOT


def test_precise_normal_phrases_retain_occurrence_and_rule_scope():
    service = ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_10-candidate.json")
    dataset = ROOT / "docs/qa/data/us24-development.v3_10.jsonl"
    for line in dataset.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        response = service.check(row["text"])
        assert response.passed == (not row["blocked"]), row["id"]
        assert [hit.model_dump() for hit in response.hits] == row["expected_hits"], row["id"]


@pytest.mark.parametrize("spans", [
    [], [(2, 5)], [(1, 3), (3, 5)], [(2, 7), (4, 5)],
    [(1, 4), (3, 6)], [(6, 8), (0, 2), (1, 5)], [(2, 4), (2, 8), (3, 6)],
])
def test_phrase_index_preserves_individual_phrase_containment(spans):
    index = _phrase_index(spans)
    for left in range(10):
        for right in range(left + 1, 11):
            assert _inside_phrase(index, left, right) == any(
                start <= left and right <= end for start, end in spans)


def test_streaming_pinyin_retains_tail_after_64_tokens():
    service = ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_10-candidate.json")
    assert not service.check("z " * 997 + "shabi.").passed
    assert service.check("sha " + "x " * 600 + "bi").hits == []


def test_hanzi_homophone_exemptions_preserve_canonical_offsets():
    service = ModerationService(
        ROOT / "services/algo/app/data/moderation-v3_10-candidate.json")
    assert service.check("你这砂比参数填写完整。").hits == []
    assert not service.check("你这砂比参数填写完整。你是鲨币。").passed
