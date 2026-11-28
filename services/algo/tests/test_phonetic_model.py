import pytest

from scripts.evaluate_phonetic_model import grounded_hints


def hint(source, reading, certainty="possible"):
    return dict(source=source, reading=reading, certainty=certainty)


def test_reconstruction_hypotheses_are_grounded_and_deduplicated_without_rewriting_text():
    text = "你就是沸柴"
    value = dict(replacements=[hint("沸柴", "废柴"), hint("沸柴", "废柴")])
    assert grounded_hints(value, text) == [
        dict(source="沸柴", reading="废柴", certainty="possible", span=[3, 5])]
    assert text == "你就是沸柴"
    assert grounded_hints(dict(replacements=[]), text) == []


@pytest.mark.parametrize("value", [
    dict(replacements=[hint("sb", "傻逼")]),
    dict(replacements=[hint("missing", "词")]),
    dict(replacements=[hint("", "词")]),
    dict(replacements=[hint("沸柴", "词" * 33)]),
    dict(replacements=[hint("沸柴", "废柴", "approved")]),
    dict(replacements=[hint("沸柴", "废柴")] * 5),
    dict(replacements="not a list"),
    dict(replacements=[], extra=True),
])
def test_ungrounded_or_unbounded_hints_cannot_become_model_evidence(value):
    with pytest.raises(ValueError):
        grounded_hints(value, "asbestos 沸柴")


def test_english_boundary_selects_the_complete_occurrence_not_identifier_internals():
    text = "foo_sb sb sbatch"
    result = grounded_hints(dict(replacements=[hint("sb", "傻逼")]), text)
    assert result[0]["span"] == [7, 9]
