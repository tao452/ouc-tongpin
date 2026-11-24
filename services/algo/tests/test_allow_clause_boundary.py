import pytest

from app.services.moderation import RECALL_DICTIONARY, ModerationService
from app.services.moderation_context import context_view


@pytest.fixture(scope="module")
def service():
    return ModerationService(RECALL_DICTIONARY.with_name("moderation-v3_3-candidate.json"))


@pytest.mark.parametrize("separator", [
    ",", "，", "。", ".", "\n", "\u2028", "\u2029", "：", "\x00",
])
def test_literal_benign_phrase_cannot_bridge_a_clause_to_hide_a_threat(service, separator):
    assert not service.check("你去死" + separator + "海边是好地方").passed
    result = service.check("你真是废物" + separator + "利用别人")
    assert [(h.word, h.level) for h in result.hits] == [("废物", "MEDIUM")]


@pytest.mark.parametrize("separator", [",", "，", "。", ". ", "\n", "\u2028"])
def test_pinyin_exception_cannot_bridge_sentence_boundaries(service, separator):
    assert not service.check("ni qu si" + separator + "hai bian deng ni").passed


@pytest.mark.parametrize("text", [
    "去死海旅游", "去 死 海旅游", "去\t死海旅游", "废物利用", "qu si hai", "qu.si.hai", "qu-si-hai",
    "qu.si.kao", "bai.chi.yi.dun.fan", "我想去死.请帮帮我", "我想qu.si，请帮帮我",
])
def test_precise_normal_phrases_and_self_help_keep_their_own_scope(service, text):
    assert service.check(text).hits == []


def test_context_view_preserves_offsets_and_only_disambiguates_explicit_separators():
    text = "去死.海 qu.si.hai\u2028我想去死"
    view = context_view(text)
    assert len(view) == len(text)
    assert view == "去死。海 qu.si.hai\n我想去死"
