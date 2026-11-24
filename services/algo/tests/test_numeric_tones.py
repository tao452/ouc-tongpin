import pytest

from app.services.moderation import RECALL_DICTIONARY, ModerationService
from app.services.pronunciation import MAX_READINGS, numeric_tone_patterns

DICTIONARY = RECALL_DICTIONARY.with_name("moderation-v3_3-candidate.json")


@pytest.fixture(scope="module")
def service():
    return ModerationService(DICTIONARY)


@pytest.mark.parametrize("text,word", [
    ("cao4 ni3 ma1", "操你妈"), ("ＣＡＯ４．ＮＩ３．ＭＡ１", "操你妈"),
    ("sha3bi1", "傻逼"), ("sha3 bi1", "傻逼"), ("sha3-bi1", "傻逼"), ("sha3 bi", "傻逼"),
    ("qu4 si3", "去死"), ("zhong4 shang1", "我要重伤你"),
])
def test_numeric_tones_keep_the_canonical_mapping(service, text, word):
    if word == "我要重伤你":
        text = "wo3 yao4 " + text + " ni3"
    assert word in {h.word for h in service.check(text).hits}


@pytest.mark.parametrize("text", [
    "asbestos shabiography SHA256 sbatch q4_report",
    "xsha3bi1 sha3bi1x foo_sha3bi1 sha3bi1_bar",
    "sha3 b sha3b sha3bid bi1 zhong4shan1",
    "ca0 nima ca0-ni-ma sha b1", "shard3 bit1 shift4 binary1",
    "sha1bi sha1 bi sha3bi4 sha1-bi2", "cao2 ni3 ma1",
    "sha3abcdefghi bi1", "sha3.........bi1", "sha33bi1",
    "bai2 chi1 yi1 dun4 fan4", "qu4 si1 kao3", "qu4 si3 hai3",
    '举报：“sha3 bi1”请处理',
    '举报：“你就是鲨币”请处理',
    '举报：“你就是sha3 bi1”请处理',
    '举报：“你就是母狗”请处理',
    '举报：“sha3 bi1”请处理。举报：“cao4 ni3 ma1”请处理',
])
def test_incomplete_english_numbers_and_exact_benign_contexts_remain_clear(service, text):
    assert service.check(text).hits == []


def test_quote_exception_does_not_suppress_a_second_attack(service):
    result = service.check('举报：“sha3 bi1”请处理。cao4 ni3 ma1')
    assert [(h.word, h.level) for h in result.hits] == [("操你妈", "HIGH")]


@pytest.mark.parametrize("prefix", [
    '举报：“你就是鲨币”请处理。', '举报：“你就是sha3 bi1”请处理。',
    '举报：“你就是母狗”请处理。',
])
def test_targeted_quote_exemption_is_confined_to_its_span(service, prefix):
    assert not service.check(prefix + "操你妈").passed
    assert not service.known_targeted_quote("杀了你，你就是鲨币")


def test_tone_pattern_count_depends_on_readings_not_tone_products():
    patterns = numeric_tone_patterns("我要重伤你", ["wo yao chong shang ni"])
    assert len(patterns) == 2 <= MAX_READINGS
    assert patterns[0].fullmatch("wo3 yao4 zhong4 shang1 ni3")
    assert patterns[1].fullmatch("wo3 yao4 chong2 shang1 ni3")


def test_new_tone_policy_is_opt_in_and_old_dictionary_bytes_stay_usable():
    assert not ModerationService(RECALL_DICTIONARY).check("cao4 ni3 ma1").hits
    assert not ModerationService().check("cao4 ni3 ma1").hits


@pytest.mark.parametrize("readings", [
    ["cao0 ni3 ma1"], ["cao4 ni3"], ["wrong4 ni3 ma1"],
])
def test_invalid_explicit_tone_paths_cannot_enter_the_mapping(readings):
    with pytest.raises(ValueError, match="whole phrase"):
        numeric_tone_patterns("操你妈", tone_readings=readings)


def test_additional_tones_and_polyphone_paths_share_one_finite_reading_cap():
    explicit = [f"chong{a} chong{b}" for a, b in [(1, 1), (1, 2), (1, 3), (1, 4),
                                                (1, 5), (2, 1), (2, 3)]]
    with pytest.raises(ValueError, match="Too many"):
        numeric_tone_patterns("重重", ["zhong zhong"], explicit)


def test_quotation_cache_is_per_request_and_preserves_the_outside_attack(service, monkeypatch):
    original = service.known_targeted_quote
    calls = []

    def tracked(quote, budget):
        calls.append(quote)
        return original(quote, budget)

    monkeypatch.setattr(service, "known_targeted_quote", tracked)
    text = '举报：“你就是鲨币”请处理。' * 20
    assert service.check(text).hits == []
    assert calls == ["你就是鲨币"]
    assert not service.check(text + "操你妈").passed
    assert calls == ["你就是鲨币", "你就是鲨币"]
