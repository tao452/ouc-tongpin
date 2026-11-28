import json

from app.services.moderation import ModerationService
from scripts.evaluate_candidate import ROOT, assess, development


def test_complete_target_forms_cover_the_development_contract_without_partial_word_hits():
    data = ROOT / "services/algo/app/data"
    candidate = ModerationService(data / "moderation-v3_4-candidate.json")
    rows = development(ROOT / "docs/qa/data/us24-development.v3_4.jsonl")
    result = assess(rows, candidate)
    assert result["count"] == 890
    assert result["mapping_failure_ids"] == []
    assert result["decision_failure_ids"] == []
    assert result["any_level"]["confusion_matrix"] == dict(tp=490, fp=0, fn=0, tn=400)


def test_expansion_preserves_every_existing_word_level_alias_and_rollback_path():
    data = ROOT / "services/algo/app/data"
    old = json.loads((data / "moderation-v3_3-candidate.json").read_text(encoding="utf-8"))
    new = json.loads((data / "moderation-v3_4-candidate.json").read_text(encoding="utf-8"))
    assert len(old) == len(new) == 120
    changed = 0
    for before, after in zip(old, new, strict=True):
        if before != after:
            changed += 1
            assert after == {**before, "pinyin": True, "pinyin_tone_numbers": True}
    assert changed == 35
    assert ModerationService().check("ni ge nao tan").hits == []
    assert ModerationService(data / "moderation-v3_3-candidate.json").check(
        "ni ge nao tan").hits == []
    assert [h.word for h in ModerationService(data / "moderation-v3_4-candidate.json").check(
        "ni ge nao tan").hits] == ["你个脑瘫"]
