import json

import pytest

from app.services.moderation import ModerationService
from app.services.normalization import normalize


@pytest.fixture(scope="module")
def service():
    return ModerationService()


@pytest.mark.parametrize("text", [
    "你是傻逼", "傻 逼", "傻*逼", "傻\u200b逼", "傻\n逼", "傻必", "煞笔", "沙比",
    "shabi", "ＳＨＡＢＩ", "sha bi", "s.h.a.b.i", "操你媽", "艹你妈", "caonima",
    "去死", "去-死", "qusi", "QU SI", "去\u2060死",
])
def test_high_risk_variants_are_blocked(service, text):
    result = service.check(text)
    assert result.passed is False
    assert any(hit.level == "HIGH" for hit in result.hits)


@pytest.mark.parametrize("text", [
    "今天很开心", "想找人一起去食堂", "一起学习Python", "明天下午打篮球", "需要有人听我说话",
    "这周压力有点大", "垃圾分类从我做起", "草泥马是一种网络称呼", "铅笔放在沙发旁",
    "shabilist", "typescript", "QU SInce", "上课记笔记", "可以一起复习吗", "", "😀",
    "去思考这个问题", "我想寻求帮助", "校园活动欢迎参加", "圖書館下午有空位",
])
def test_benign_text_is_allowed(service, text):
    assert service.check(text).passed is True


def test_levels_and_deduplication(service):
    result = service.check("垃圾，废物，傻逼，傻逼")
    assert [(h.word, h.level) for h in result.hits] == [
        ("傻逼", "HIGH"), ("废物", "MEDIUM"), ("垃圾", "LOW")
    ]
    assert service.check("廢物").passed is True
    assert service.check("垃圾").hits[0].level == "LOW"


def test_normalization_is_idempotent():
    value = normalize("廢物 ＡＢＣ\u200b，１２３！")
    assert value == "废物abc123"
    assert normalize(value) == value


def test_overlapping_words(tmp_path):
    path = tmp_path / "words.json"
    path.write_text(json.dumps([
        {"word": "测试", "level": "LOW"}, {"word": "测试词", "level": "HIGH"}
    ]), encoding="utf-8")
    assert len(ModerationService(path).check("测试词").hits) == 2


@pytest.mark.parametrize("entries", [
    [], {}, [{"word": "", "level": "LOW"}], [{"word": "词", "level": "INVALID"}],
    [{"word": "词", "level": "LOW", "aliases": ["***"]}],
    [{"word": "词", "level": "LOW"}, {"word": "词", "level": "HIGH"}],
    [{"word": "词", "level": "LOW", "aliases": ["字"]},
     {"word": "字", "level": "HIGH"}],
])
def test_bad_dictionary_fails_at_startup(tmp_path, entries):
    path = tmp_path / "words.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    with pytest.raises(ValueError):
        ModerationService(path)
