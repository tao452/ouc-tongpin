import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import moderation as router
from app.services import moderation as mod
from app.services.targeted_matching import has_target, homophone_spans
from scripts.evaluate_candidate import ROOT, assess, development


@pytest.fixture(scope="module")
def expanded():
    return mod.ModerationService(mod.RECALL_DICTIONARY)


@pytest.mark.parametrize("text,word,level", [
    ("你就是鲨币", "傻逼", "HIGH"),
    ("你这煞币", "傻逼", "HIGH"),
    ("你就是沸物", "废物", "MEDIUM"),
    ("你是仁渣", "人渣", "MEDIUM"),
    ("N M S L", "你妈死了", "HIGH"),
    ("ｎｍｓｌ", "你妈死了", "HIGH"),
    ("你是SB", "傻逼", "HIGH"),
    ("你就是q4", "去死", "HIGH"),
    ("你个智涨", "你个智障", "MEDIUM"),
    ("我一枪崩了你", "我要一枪崩了你", "HIGH"),
    ("你就是废柴", "废物", "MEDIUM"),
])
def test_added_forms_retain_the_canonical_word_and_s1_policy(expanded, text, word, level):
    result = expanded.check(text)
    assert (word, level) in [(h.word, h.level) for h in result.hits]
    assert result.passed == (level != "HIGH")


@pytest.mark.parametrize("text", [
    "USB BSB ASBESTOS sbatch q4_report nmsl_func NMSList xNMSL",
    "sb s13 q4 鲨币 沸物 仁渣",  # Ambiguous forms without a local target.
    "这块纱布在医务室，你的纱布已经放好了",
    "公狗绝育，母狗产后护理，鸡把米吃完了",
    "脑瘫患者需要帮助，智力障碍服务需要完善",
    "你是脑瘫康复项目的志愿者吗",
    "你是废物利用活动的志愿者吗",
    "我抑郁了，不想活了，想求助",
    "我想去死，请帮帮我",
    "你是，鲨币",  # Phonetic matching never joins punctuation-separated runs.
    "你在研究：鲨币这个名字",
])
def test_normal_language_identity_words_and_self_help_are_not_blocked(expanded, text):
    assert expanded.check(text).passed


def test_target_does_not_cross_sentence_or_unbounded_gap(expanded):
    for text in ["你。sb", "你说的是这些正常的文字" * 5 + "sb", "你不是。鲨币"]:
        assert expanded.check(text).hits == []
    assert not has_target("你" + "真" * 20, 21)


def test_local_report_exemption_does_not_hide_a_second_attack(expanded):
    assert expanded.check('举报：“你妈死了”请处理').passed
    assert not expanded.check('举报：“你妈死了”请处理。你就是鲨币').passed
    assert expanded.check('语言科普：“支那猪”是侮辱性表达').passed


def test_old_files_and_explicit_rollback_are_preserved(expanded):
    data = ROOT / "services/algo/app/data"
    expected = {
        "moderation-v1.json": "6dc578db29748a9714e810fe56b00045726fabb2b891b6ab0b8246bfec51cb0a",
        "moderation-v2-candidate.json": (
            "f60881fbd4a0692bcb65e41f6299ce6e77c4a842d05bacfdbdc053e149983fdd"),
    }
    for name, digest in expected.items():
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == digest
    assert mod.ModerationService().check("你就是鲨币").passed
    assert mod.ModerationService(mod.CANDIDATE_DICTIONARY).check("你就是鲨币").passed
    assert not expanded.check("你就是鲨币").passed


def test_all_new_development_samples_and_hard_negatives_remain_in_counts(expanded):
    rows = development(ROOT / "docs/qa/data/us24-development.v3.jsonl")
    result = assess(rows, expanded)
    assert result["count"] == len(rows)
    assert result["mapping_failure_ids"] == []
    assert result["high_blocking"]["thresholds_met_on_supplied_rows"]
    # General rule-hit accuracy is independently reported; no relabelling of old negatives.
    assert any(r["id"] == "R3-NEG-020" for r in rows)


def test_deduplication_and_bounded_work(expanded):
    result = expanded.check("你就是鲨币，你是sb，你是煞币。" * 80)
    assert len([h for h in result.hits if h.word == "傻逼"]) == 1
    assert not expanded.check("你就是鲨币" + "中文" * 997).passed


def test_budget_interrupts_phonetic_matching_and_http_fails_closed(monkeypatch, expanded):
    monkeypatch.setattr(router, "service", expanded)
    monkeypatch.setattr(mod, "MATCH_BUDGET_SECONDS", -1)
    response = TestClient(app).post("/api/moderation/check", json={"text": "你就是鲨币"})
    assert response.status_code == 503
    assert "hits" not in response.json()


@pytest.mark.parametrize("row", [
    {"word": "人渣", "level": "MEDIUM", "hanzi_homophone": True},
    {"word": "字", "level": "LOW", "targeted_aliases": ["字"]},
    {"word": "字", "level": "LOW", "targeted_aliases": ["词", "詞"]},
    {"word": "字", "level": "LOW", "targeted_aliases": [""]},
])
def test_invalid_or_conflicting_new_configuration_is_rejected(tmp_path, row):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps([row]), encoding="utf-8")
    with pytest.raises(ValueError):
        mod.ModerationService(path)


def test_phonetic_alignment_guard(monkeypatch):
    monkeypatch.setattr("app.services.targeted_matching.pinyin", lambda *a, **kw: [])
    assert list(homophone_spans("你就是鲨币", {}, lambda: None)) == []


def test_target_requirement_applies_to_pinyin_too(tmp_path):
    path = tmp_path / "targeted.json"
    path.write_text(json.dumps([dict(word="人渣", level="MEDIUM", pinyin=True,
                                     target_required=True)]), encoding="utf-8")
    service = mod.ModerationService(path)
    assert service.check("ren zha").hits == []
    assert service.check("你是ren zha").hits[0].word == "人渣"
