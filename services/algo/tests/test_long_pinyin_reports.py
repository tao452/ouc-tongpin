import pytest

from app.services.moderation import ModerationService
from app.services.moderation_context import (
    MAX_PINYIN_QUOTE_LENGTH,
    bounded_long_pinyin,
    context_spans,
)
from scripts.evaluate_candidate import ROOT

ATTACK = "wo3........yao4........yi1........qiang1........beng1........le5........ni3"
TONELESS_ATTACK = "wo........yao........yi........qiang........beng........le........ni"


@pytest.fixture(scope="module")
def service():
    return ModerationService(ROOT / "services/algo/app/data/moderation-v3_5-candidate.json")


@pytest.mark.parametrize("left,right", [
    ("“", "”"), ("「", "」"), ('"', '"'), ("'", "'"), ("‘", "’"),
])
@pytest.mark.parametrize("attack", [ATTACK, TONELESS_ATTACK])
def test_registered_long_pinyin_report_preserves_outside_threats(service, left, right, attack):
    report = f"举报：{left}{attack}{right}请处理"
    assert len(attack) > 64
    assert "我要一枪崩了你" in {h.word for h in service.check(attack).hits}
    assert service.check(report).hits == []
    assert not service.check(report + "。杀了你").passed
    assert not service.check(f"举报：{left}{attack}。杀了你{right}请处理").passed


@pytest.mark.parametrize("quote", [
    "x" * 65 + "杀了你", "杀" + "。" * 64 + "了你", "你觉得" + "a" * 65,
    "a" * 81, "a" + "_" * 64, "a" * (MAX_PINYIN_QUOTE_LENGTH + 1),
])
def test_longer_quotes_do_not_extend_hanzi_or_identifier_exemptions(quote):
    assert not bounded_long_pinyin(quote)
    assert context_spans(f"举报：'{quote}'请处理", {"杀了你"}) == []


def test_long_pinyin_shape_alone_does_not_make_a_known_word():
    quote = "abc1........" * 8
    assert bounded_long_pinyin(quote)
    assert context_spans(f"举报：'{quote}'请处理", set()) == []
    assert bounded_long_pinyin("你就是" + ATTACK)


def test_unknown_long_report_containing_a_threat_still_hits(service):
    quote = "this is an ordinary English explanation " * 2 + "杀了你"
    assert not service.check(f"举报：'{quote}'请处理").passed
