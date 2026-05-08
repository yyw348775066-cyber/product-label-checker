import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from app import build_compare_table, build_summary, extract_field, judge_difference


STANDARD_TEXT = """产品名称：清爽橙汁饮料
执行标准：GB/T 31121
生产许可证：SC12345678901234
配料表：水、白砂糖、浓缩橙汁、柠檬酸
保质期：12个月
净含量：500mL
生产企业：示例食品有限公司
标签风险提示：暂无明显风险"""


def test_extract_product_name_from_standard_format():
    assert extract_field(STANDARD_TEXT, "产品名称") == "清爽橙汁饮料"


def test_extract_standard_code_from_standard_format():
    assert extract_field(STANDARD_TEXT, "执行标准") == "GB/T 31121"


def test_extract_production_license_from_standard_format():
    assert extract_field(STANDARD_TEXT, "生产许可证") == "SC12345678901234"


def test_extract_fields_from_compact_text():
    text = "产品名称：苹果汁饮料 执行标准：GB/T 31121 生产许可证：SC12345678901234 配料表：水、糖 保质期：12个月 净含量：500mL"

    assert extract_field(text, "产品名称") == "苹果汁饮料"
    assert extract_field(text, "执行标准") == "GB/T 31121"
    assert extract_field(text, "配料表") == "水、糖"
    assert extract_field(text, "保质期") == "12个月"
    assert extract_field(text, "净含量") == "500mL"


def test_extract_net_content_from_spec_with_package_suffix():
    text = "产品名称：苹果汁饮料 规格：500ml/瓶"

    assert extract_field(text, "净含量") == "500ml"


def test_judge_difference_when_results_are_same():
    result, row_class = judge_difference(["A", "A", "A"])

    assert result == "一致"
    assert row_class == "same"


def test_judge_difference_when_results_are_different():
    result, row_class = judge_difference(["A", "B", "A"])

    assert result == "存在差异，需人工复核"
    assert row_class == "different"


def test_judge_difference_when_all_not_extracted():
    result, row_class = judge_difference(["未提取到", "未填写", "未提取到"])

    assert result == "均未提取到"
    assert row_class == "not-extracted"


def test_judge_difference_treats_not_seen_as_not_extracted():
    result, row_class = judge_difference(["未看到", "未填写", "未看见"])

    assert result == "均未提取到"
    assert row_class == "not-extracted"


def test_judge_difference_when_only_one_platform_has_result():
    result, row_class = judge_difference(["A", "未提取到", "未填写"])

    assert result == "仅一个平台提取到，需复核"
    assert row_class == "warning"


def test_judge_difference_ignores_spaces_for_standard_codes():
    result, row_class = judge_difference(["QB/T2686", "QB/T 2686"], "执行标准")

    assert result == "一致"
    assert row_class == "same"


def test_judge_difference_normalizes_net_content_units():
    result, row_class = judge_difference(["500ml", "500 mL", "500毫升"], "净含量")

    assert result == "一致"
    assert row_class == "same"


def test_risk_text_is_split_into_lines():
    text = "标签风险提示：1. 配料表缺失；2. 净含量字体较小；3. 建议复核执行标准。"

    assert extract_field(text, "标签风险提示") == "1. 配料表缺失；\n2. 净含量字体较小；\n3. 建议复核执行标准。"


def test_risk_text_keeps_numbered_dot_segments():
    text = "标签风险提示：1. 执行标准需复核。2. 生产许可证未清晰显示。3. 配料表需人工确认。"

    assert extract_field(text, "标签风险提示") == "1. 执行标准需复核。\n2. 生产许可证未清晰显示。\n3. 配料表需人工确认。"


def test_risk_text_preserves_existing_multiline_numbering():
    text = """标签风险提示：
1. 未标注净含量，不符合 GB 7718 强制标注要求。
2. 执行标准号未标注完整版本号。
3. 营养成分表中碳水化合物标注为 0g/100g。"""

    assert extract_field(text, "标签风险提示") == (
        "1. 未标注净含量，不符合 GB 7718 强制标注要求。\n"
        "2. 执行标准号未标注完整版本号。\n"
        "3. 营养成分表中碳水化合物标注为 0g/100g。"
    )


def test_risk_text_keeps_numbered_chinese_comma_segments():
    text = "标签风险提示：1、执行标准需复核；2、生产许可证未清晰显示；3、配料表需人工确认。"

    assert extract_field(text, "标签风险提示") == "1、执行标准需复核；\n2、生产许可证未清晰显示；\n3、配料表需人工确认。"


def test_risk_text_keeps_parenthesized_number_segments():
    text = "标签风险提示：（1）执行标准需复核。（2）生产许可证未清晰显示。（3）配料表需人工确认。"

    assert extract_field(text, "标签风险提示") == "（1）执行标准需复核。\n（2）生产许可证未清晰显示。\n（3）配料表需人工确认。"


def test_compare_table_marks_only_different_standard_cell():
    table = build_compare_table(
        {
            "chatgpt": "执行标准：QB/T2686",
            "deepseek": "执行标准：QB/T 2686",
            "tongyi": "执行标准：QB/T 2687",
            "doubao": "执行标准：QB/T2686",
            "wenxin": "执行标准：QB/T2686",
        }
    )
    standard_row = next(row for row in table if row["field"] == "执行标准")

    assert standard_row["diff_result"] == "存在差异，需人工复核"
    assert standard_row["cell_classes"]["tongyi"] == "cell-different"
    assert standard_row["cell_classes"]["chatgpt"] == ""
    assert standard_row["cell_classes"]["deepseek"] == ""


def test_compare_table_does_not_mark_clear_no_risk_statement_as_risk():
    table = build_compare_table(
        {
            "chatgpt": "标签风险提示：暂无明显风险",
            "deepseek": "标签风险提示：暂未发现明显风险",
            "tongyi": "标签风险提示：未发现明显风险",
            "doubao": "标签风险提示：无明显风险",
            "wenxin": "标签风险提示：暂无风险",
        }
    )
    risk_row = next(row for row in table if row["field"] == "标签风险提示")

    assert risk_row["diff_result"] == "一致"
    assert risk_row["needs_key_review"] is False
    assert all(cell_class != "cell-risk" for cell_class in risk_row["cell_classes"].values())


def test_build_summary_counts_compare_table_statuses():
    compare_table = build_compare_table(
        {
            "chatgpt": "产品名称：A",
            "deepseek": "产品名称：A",
            "tongyi": "产品名称：A",
            "doubao": "产品名称：A",
            "wenxin": "产品名称：A",
        }
    )
    summary = build_summary(compare_table)

    assert summary["total"] == 8
    assert summary["same"] == 1
    assert summary["not_extracted"] == 7
    assert summary["warning"] == 0
    assert summary["different"] == 0
