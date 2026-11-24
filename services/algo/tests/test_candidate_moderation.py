import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import moderation as mod
from app.services.normalization import normalize
from app.services.pronunciation import pronunciation_keys
from scripts.evaluate_candidate import assess, development, pcr, run

ROOT = Path(__file__).resolve().parents[3]
DEVELOPMENT = ROOT / "docs/qa/data/us24-development.v2.jsonl"


@pytest.fixture(scope="module")
def candidate():
    return mod.ModerationService(mod.CANDIDATE_DICTIONARY)


def test_development_contract_covers_mappings_and_retains_difficult_negatives(candidate):
    rows = development(DEVELOPMENT)
    result = assess(rows, candidate)
    assert result["high_blocking"]["recall"] >= .95
    assert result["high_blocking"]["false_positive_rate"] < .02
    assert result["mapping_failure_ids"] == []
    # Keep the original hard negative and its label after fixing its false hit.
    row = next(r for r in rows if r["id"] == "NEG-normal_pinyin-013")
    assert row["text"] == "ca0 nima" and not row["expected_word"]
    assert candidate.check(row["text"]).hits == []
    assert "NEG-normal_pinyin-013" not in result["decision_failure_ids"]
    assert "NEG-campus-004" in result["decision_failure_ids"]


@pytest.mark.parametrize("word, expected", [
    ("重伤", "zhongshang"), ("重庆", "chongqing"), ("银行", "yinhang"),
    ("行走", "xingzou"), ("恶心", "exin"), ("横着", "hengzhe"),
    ("弄死你", "nongsini"), ("狗杂种", "gouzazhong"),
])
def test_phrase_context_resolves_polyphones(word, expected):
    assert expected in pronunciation_keys(word)


def test_explicit_whole_phrase_readings_are_bounded_not_cartesian():
    keys = pronunciation_keys("重庆", ["zhong qing"])
    assert "chongqing" in keys and "zhongqing" in keys
    assert len(keys) <= 16
    assert "hangzou" not in pronunciation_keys("行走")
    assert normalize("nǚ nü nǜ") == "nvnvnv"


@pytest.mark.parametrize("word, readings, aliases", [
    ("重" * 17, [], []), ("行走", ["xing"], []), ("行走", ["foo zou"], []),
    ("重庆", [], ["x"]), ("重庆", [], ["x" * 65]),
    ("重庆", [], [f"variant{i}" for i in range(20)]),
])
def test_pronunciation_limits_fail_explicitly(word, readings, aliases):
    with pytest.raises(ValueError):
        pronunciation_keys(word, readings, aliases)


@pytest.mark.parametrize("text", [
    "wǒ yào zhòng shāng nǐ", "rang ni heng zhe chu qu", "sha3bi1", "shab1",
    "ｓｈａ３ｂｉ１", "ca0nima", "操尼玛", "去④", "去\u200d亖", "SHABII",
])
def test_candidate_variants_map_to_reviewed_standard(candidate, text):
    assert not candidate.check(text).passed


@pytest.mark.parametrize("text", [
    "qu si kao", "qu.si.kao", "qu si hai", "shabi_func", "foo_shabi", "shabi12",
    "12shabi", "sha1bi", "qu since", "shabilist", "nongsinice", "woyaochongshangni",
    "sha中文bi", "sha_ bi", "sha         bi", "chong qing", "yin hang", "xing zou",
])
def test_latin_boundaries_and_unrelated_pronunciations(candidate, text):
    assert candidate.check(text).passed


@pytest.mark.parametrize("benign, attack", [
    ('举报：“杀了你”请处理', '举报：“杀了你”请处理。杀了你'),
    ('不要对同学说“傻逼”', '不要对同学说“傻逼”。你是傻逼'),
    ('网络暴力讨论：“去死”属于攻击性言论', '网络暴力讨论：“去死”属于攻击性言论。去死'),
    ('我想去死，请帮帮我', '我想去死，请帮帮我。杀了你'),
    ('举报：“sha bi”请处理', '举报：“sha bi”请处理。sha bi'),
    ('qu si kao', 'qu si kao, qu si'),
])
def test_context_is_limited_to_exact_occurrence(candidate, benign, attack):
    assert candidate.check(benign).passed
    assert not candidate.check(attack).passed


@pytest.mark.parametrize("text", [
    '举报：杀了你请处理', '举报：“正常文本”请处理，杀了你', '杀了你，举报',
    '有人说“傻逼”', '举报：“傻逼，杀了你”请处理', '我需要帮助，杀了你',
])
def test_unrecognized_context_does_not_globally_disable_rules(candidate, text):
    assert not candidate.check(text).passed


def test_deduplication_performance_and_rollback(candidate):
    result = candidate.check("傻逼 shabi 傻批 " * 100)
    assert [(h.word, h.level) for h in result.hits] == [("傻逼", "HIGH")]
    assert len(candidate.pinyin) <= 70 * 16
    assert max(map(len, candidate.pinyin)) <= 64
    assert mod.ModerationService().check("我要重伤你").passed
    assert mod.ModerationService(mod.DEFAULT_DICTIONARY.with_name("words.json")).check(
        "你不配活着").passed
    with pytest.raises(ValueError):
        candidate.check("a" * 2001)


def test_time_budget_fails_closed_in_http(monkeypatch, candidate):
    monkeypatch.setattr(mod, "MATCH_BUDGET_SECONDS", -1)
    with pytest.raises(TimeoutError):
        candidate.check("正常")
    response = TestClient(app).post("/api/moderation/check", json={"text": "正常"})
    assert response.status_code == 503


@pytest.mark.parametrize("entries", [
    [{"word": "字", "level": "LOW"}, {"word": "字", "level": "LOW"}],
    [{"word": "重庆", "level": "HIGH", "pinyin_aliases": ["zhongqing"]}],
    [{"word": "重庆", "level": "HIGH", "pinyin": True, "pinyin_readings": ["x" * 129]}],
    [{"word": "去死", "level": "HIGH", "pinyin": True, "pinyin_allow_phrases": ["qu si"]}],
    [{"word": "去死", "level": "HIGH", "pinyin": True, "pinyin_allow_phrases": ["normal"]}],
    [{"word": "去死", "level": "HIGH", "pinyin": True, "pinyin_allow_phrases": ["qu si !"]}],
    [{"word": "重庆", "level": "HIGH", "pinyin": True},
     {"word": "重情", "level": "LOW", "pinyin": True, "pinyin_aliases": ["chongqing"]}],
])
def test_conflicts_and_unsafe_exemptions_rejected(tmp_path, entries):
    path = tmp_path / "words.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    with pytest.raises(ValueError):
        mod.ModerationService(path)


def test_external_accounting_does_not_exclude_failed_predictions(tmp_path):
    path = tmp_path / "pcr.json"
    values = [dict(text="hello", offensive_label=1, strategy="HR"),
              dict(text="hello", offensive_label=0, strategy="NR")]
    path.write_text(json.dumps(values), encoding="utf-8")
    manifest = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    bytes=path.stat().st_size, rows=2)
    rows, exclusions = pcr(path, manifest)
    assert len(rows) == 2 and exclusions == {}
    result = assess(rows, mod.ModerationService(), external=True)
    assert result["high_blocking"]["confusion_matrix"] == dict(tp=0, fp=0, fn=1, tn=1)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        pcr(path, manifest)


def test_evaluation_output_cannot_replace_development_dataset():
    before = DEVELOPMENT.read_bytes()
    with pytest.raises(ValueError):
        run(DEVELOPMENT, DEVELOPMENT)
    assert DEVELOPMENT.read_bytes() == before
