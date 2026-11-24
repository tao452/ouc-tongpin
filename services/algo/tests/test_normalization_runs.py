import unicodedata

import pytest

from app.services import normalization


def test_installed_t2s_rules_do_not_cross_non_hanzi_boundaries():
    # This invariant protects the optimization if the OpenCC data is upgraded.
    for _, _, words in normalization._converter.dict_cache.values():
        assert all(normalization._HANZI_RUN.fullmatch(key) for key in words)
        assert all(normalization._HANZI_RUN.fullmatch(value)
                   for choices in words.values() for value in choices.split())


@pytest.mark.parametrize(("text", "expected"), [
    ("乾隆說：頭髮很乾淨", "乾隆说:头发很干净"),
    ("abc繁體中文XYZ", "abc繁体中文xyz"),
    ("code=shаbiπ;繁體中文", "code=shаbiπ;繁体中文"),
    ("乾著急。乾著急", "干著急。干著急"),
    ("神𠮷。ＡＢＣ", "神𠮷。abc"),
    ("溫度20°C，硫酸H₂SO₄", "温度20°c,硫酸h2so4"),
])
def test_phrase_context_and_mixed_text_normalization_are_preserved(text, expected):
    assert normalization.canonicalize(text) == expected


def test_repeated_hanzi_runs_are_converted_once_per_invocation(monkeypatch):
    original = normalization._converter.convert
    calls = []

    def convert(value):
        calls.append(value)
        return original(value)

    monkeypatch.setattr(normalization._converter, "convert", convert)
    assert normalization.canonicalize("繁體。繁體。shаbiπ") == "繁体。繁体。shаbiπ"
    assert calls == ["繁體"]
    normalization.canonicalize("繁體")
    assert calls == ["繁體", "繁體"]  # No user-text cache survives the invocation.


def test_non_hanzi_input_keeps_nfkc_case_and_tone_processing_without_opencc(monkeypatch):
    def unexpected(_):
        raise AssertionError("OpenCC should not allocate parse trees for non-Hanzi input")

    monkeypatch.setattr(normalization._converter, "convert", unexpected)
    assert normalization.canonicalize("ＳＨĀＢÌπ ѕhаbі") == "shabiπ ѕhаbі"
    assert unicodedata.normalize("NFKC", "ѕhаbі") == "ѕhаbі"
