import json

import pytest

from app.services.moderation import RECALL_DICTIONARY, ModerationService
from scripts.evaluate_candidate import ROOT

CASES = json.loads((ROOT / "docs/qa/data/us24-self-help.v3.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[row["id"] for row in CASES])
def test_precise_self_help_context_only_protects_its_own_occurrence(case):
    service = ModerationService(RECALL_DICTIONARY.with_name("moderation-v3_3-candidate.json"))
    result = service.check(case["text"])
    assert result.passed == case["passed"]
    assert sorted([[h.word, h.level] for h in result.hits]) == sorted(case["hits"])
