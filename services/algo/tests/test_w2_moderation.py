import json

import pytest

from app.services.moderation import ModerationService
from app.services.normalization import normalize


@pytest.fixture(scope="module")
def service():
    return ModerationService()


@pytest.mark.parametrize("text", [
    "shabi shabi", "你就是 shabi 啊", "say shabi now", "sha bi", "sha.b.i",
    "SHǍBĪ", "s.h.a.b.i", "qu si", "caonima caonima", "你这人 shǎbī！",
    "shabi和shabi", "sha\u0301bi", "shabi，去死海", "去死海，但是你去死",
    "去死胡同还说傻逼", "去死海，再去死，再去死海",
])
def test_obfuscated_and_repeated_high_terms_are_blocked(service, text):
    assert service.check(text).passed is False


@pytest.mark.parametrize("text", [
    "暑假去死海旅游", "先去死胡同看看路牌", "不要再去死记硬背",
    "我过去死记硬背，现在理解公式", "shabilist", "myshabi", "shabiword",
    "sha中文bi", "sha1bi", "QU SInce", "shallow bike", "trash bin",
])
def test_context_and_latin_word_boundaries_avoid_false_blocks(service, text):
    assert service.check(text).passed is True


def test_context_exceptions_are_local_to_the_matched_occurrence(service):
    assert service.check("去死海，再去死海").hits == []
    result = service.check("废物利用，但是你是废物")
    assert [(hit.word, hit.level) for hit in result.hits] == [("废物", "MEDIUM")]
    assert service.check("废物回收和废物管理").hits == []
    assert service.check("垃圾分类").hits[0].level == "LOW"


@pytest.mark.parametrize("phrase", ["", "***", "正常内容", "去死", "长" * 129 + "去死"])
def test_context_exceptions_cannot_disable_a_term_globally(tmp_path, phrase):
    path = tmp_path / "words.json"
    path.write_text(json.dumps([
        {"word": "去死", "level": "HIGH", "allow_phrases": [phrase]}
    ]), encoding="utf-8")
    with pytest.raises(ValueError):
        ModerationService(path)


def test_context_exception_for_one_term_does_not_allow_another(tmp_path):
    path = tmp_path / "words.json"
    path.write_text(json.dumps([
        {"word": "去死", "level": "HIGH", "allow_phrases": ["去死海"]},
        {"word": "死海", "level": "MEDIUM"},
    ]), encoding="utf-8")
    result = ModerationService(path).check("去死海")
    assert result.passed is True
    assert [(hit.word, hit.level) for hit in result.hits] == [("死海", "MEDIUM")]


def test_tone_normalization_is_idempotent():
    assert normalize("ＳＨǍＢĪ") == "shabi"
    assert normalize(normalize("ＳＨǍＢĪ")) == "shabi"
