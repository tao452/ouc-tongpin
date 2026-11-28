import pytest

from scripts.evaluate_setox import parse_native, summarize_native


@pytest.mark.parametrize("response", [
    "", "分析：正常内容", "可能正常内容", "不安全内容", "正常内容\n不安全内容",
    "不安全内容\n风险类别：其他", "正常内容\n风险类别：贬损攻击",
    "不安全内容\n风险类别：贬损攻击|敏感话题", "<tool_call>{}</tool_call>",
])
def test_ambiguous_native_output_is_an_error_instead_of_a_safe_prediction(response):
    with pytest.raises(ValueError):
        parse_native(response)


def test_native_unsafe_category_does_not_become_s1_high_or_broad_offense():
    assert parse_native("正常内容")["offense_score"] == 0
    assert parse_native("不安全内容\n风险类别：贬损攻击")["offense_score"] == 100
    result = parse_native("不安全内容\n风险类别：敏感话题")
    assert result["native_unsafe"] and result["offense_score"] == 0
    assert "level" not in result


def test_only_registered_native_category_synonym_is_normalized_and_raw_label_is_retained():
    result = parse_native("不安全内容\n风险类别：辱骂攻击")
    assert result["native_category_raw"] == "辱骂攻击"
    assert result["native_category"] == "贬损攻击"
    assert result["offense_score"] == 100
    with pytest.raises(ValueError):
        parse_native("不安全内容\n风险类别：可能有辱骂攻击")


def test_failed_native_inference_stays_in_both_confusion_matrices():
    rows = [dict(id="p", cohort="PCR", label=1, error="ValueError"),
            dict(id="n", cohort="PCR", label=0, offense_score=0, native_unsafe=True,
                 literal_any=False),
            dict(id="c", cohort="controls", label=0, error="TimeoutError")]
    results = summarize_native(rows)
    assert results["native_attack"]["model"]["1"]["pcr"]["confusion_matrix"]["fn"] == 1
    assert results["native_all_unsafe"]["model"]["1"]["pcr"]["confusion_matrix"]["fp"] == 1
    assert not results["native_attack"]["literal_or_model"]["1"]["development_gate_met"]
