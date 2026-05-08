import io
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from app import (
    FIELDS,
    REPORT_FIELDS,
    app as flask_app,
    build_compare_table,
    build_report_compare_table,
    build_summary,
    extract_field,
    extract_report_field,
    judge_difference,
)


STANDARD_TEXT = """产品名称：清爽橙汁饮料
净含量：500mL
执行标准：GB/T 31121
配料表：水、白砂糖、浓缩橙汁、柠檬酸
质量等级：未看到
生产日期：见瓶身喷码
保质期：12个月
生产企业：示例食品有限公司
生产企业地址：广东省广州市示例路1号
生产许可证：SC12345678901234
委托企业：未看到
委托企业地址：未看到
联系方式：400-123-4567
贮存条件：常温保存，避免阳光直射
标签风险提示：未发现明显标签风险"""


EXPECTED_FIELDS = [
    "产品名称",
    "净含量",
    "执行标准",
    "配料表",
    "质量等级",
    "生产日期",
    "保质期",
    "生产企业",
    "生产企业地址",
    "生产许可证",
    "委托企业",
    "委托企业地址",
    "联系方式",
    "贮存条件",
    "标签风险提示",
]

EXPECTED_REPORT_FIELDS = [
    "产品名称",
    "报告编号",
    "检验类别",
    "委托单位",
    "生产单位",
    "执行标准",
    "样品规格",
    "检验依据",
    "判定依据",
    "签发日期",
    "检验机构",
    "CMA/CNAS资质信息",
    "标准必检项目清单",
    "报告项目匹配核对",
    "不合格及风险提示",
]

REPORT_TEXT = """产品名称：清爽橙汁饮料
报告编号：R20260508001
检验类别：委托检验
委托单位：示例贸易有限公司
生产单位：示例食品有限公司
执行标准：GB/T 31121
样品规格：500mL/瓶
检验依据：GB 5009 系列方法
判定依据：GB/T 31121
签发日期：2026-05-08
检验机构：示例检测技术有限公司
CMA/CNAS资质信息：CMA资质编号：2026000000
标准必检项目清单：感官、净含量、可溶性固形物、菌落总数、大肠菌群，需人工复核标准原文
报告项目匹配核对：报告项目与常见必检项目基本匹配，需人工复核标准原文
不合格及风险提示：1. 未发现明显风险，标准项目完整性仍需人工复核"""


def test_field_order_is_unified():
    assert FIELDS == EXPECTED_FIELDS


def test_report_field_order_is_unified():
    assert REPORT_FIELDS == EXPECTED_REPORT_FIELDS


def test_extract_product_name_from_standard_format():
    assert extract_field(STANDARD_TEXT, "产品名称") == "清爽橙汁饮料"


def test_extract_standard_code_from_standard_format():
    assert extract_field(STANDARD_TEXT, "执行标准") == "GB/T 31121"


def test_extract_production_license_from_standard_format():
    assert extract_field(STANDARD_TEXT, "生产许可证") == "SC12345678901234"


def test_extract_report_fields_from_standard_format():
    assert extract_report_field(REPORT_TEXT, "产品名称") == "清爽橙汁饮料"
    assert extract_report_field(REPORT_TEXT, "报告编号") == "R20260508001"
    assert extract_report_field(REPORT_TEXT, "检验类别") == "委托检验"
    assert extract_report_field(REPORT_TEXT, "委托单位") == "示例贸易有限公司"
    assert extract_report_field(REPORT_TEXT, "生产单位") == "示例食品有限公司"
    assert extract_report_field(REPORT_TEXT, "执行标准") == "GB/T 31121"
    assert extract_report_field(REPORT_TEXT, "样品规格") == "500mL/瓶"
    assert extract_report_field(REPORT_TEXT, "检验依据") == "GB 5009 系列方法"
    assert extract_report_field(REPORT_TEXT, "判定依据") == "GB/T 31121"
    assert extract_report_field(REPORT_TEXT, "签发日期") == "2026-05-08"
    assert extract_report_field(REPORT_TEXT, "检验机构") == "示例检测技术有限公司"
    assert extract_report_field(REPORT_TEXT, "CMA/CNAS资质信息") == "CMA资质编号：2026000000"


def test_report_risk_text_is_split_into_lines():
    text = "不合格及风险提示：1. 缺少检出限说明。2. 判定依据需复核。3. 需人工复核标准原文。"

    assert extract_report_field(text, "不合格及风险提示") == (
        "1. 缺少检出限说明。\n"
        "2. 判定依据需复核。\n"
        "3. 需人工复核标准原文。"
    )


def test_report_compare_table_order_matches_csv_rows():
    table = build_report_compare_table(
        {
            "chatgpt": REPORT_TEXT,
            "deepseek": REPORT_TEXT,
            "tongyi": REPORT_TEXT,
            "doubao": REPORT_TEXT,
            "wenxin": REPORT_TEXT,
        }
    )

    assert [row["field"] for row in table] == EXPECTED_REPORT_FIELDS


def test_extract_new_fields_from_standard_format():
    assert extract_field(STANDARD_TEXT, "质量等级") == "未看到"
    assert extract_field(STANDARD_TEXT, "生产日期") == "见瓶身喷码"
    assert extract_field(STANDARD_TEXT, "生产企业地址") == "广东省广州市示例路1号"
    assert extract_field(STANDARD_TEXT, "委托企业") == "未看到"
    assert extract_field(STANDARD_TEXT, "委托企业地址") == "未看到"
    assert extract_field(STANDARD_TEXT, "联系方式") == "400-123-4567"
    assert extract_field(STANDARD_TEXT, "贮存条件") == "常温保存，避免阳光直射"


def test_extract_fields_from_compact_text():
    text = "产品名称：苹果汁饮料 净含量：500mL 执行标准：GB/T 31121 配料表：水、糖 质量等级：未看到 生产日期：见喷码 保质期：12个月 生产企业：示例食品有限公司 生产企业地址：示例地址 生产许可证：SC12345678901234 委托企业：未看到 委托企业地址：未看到 联系方式：400-000-0000 贮存条件：常温保存"

    assert extract_field(text, "产品名称") == "苹果汁饮料"
    assert extract_field(text, "执行标准") == "GB/T 31121"
    assert extract_field(text, "配料表") == "水、糖"
    assert extract_field(text, "保质期") == "12个月"
    assert extract_field(text, "净含量") == "500mL"
    assert extract_field(text, "生产企业地址") == "示例地址"
    assert extract_field(text, "联系方式") == "400-000-0000"


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


def test_compare_table_hits_missing_license_rule():
    table = build_compare_table(
        {
            "chatgpt": "生产许可证：未看到",
            "deepseek": "生产许可证：未看到",
            "tongyi": "生产许可证：未看到",
            "doubao": "生产许可证：未看到",
            "wenxin": "生产许可证：未看到",
        }
    )
    license_row = next(row for row in table if row["field"] == "生产许可证")

    assert license_row["diff_result"] == "规则命中：未看到生产许可证，需重点复核"
    assert license_row["row_class"] == "not-extracted"
    assert license_row["needs_key_review"] is True


def test_report_compare_table_hits_missing_cma_rule():
    table = build_report_compare_table(
        {
            "chatgpt": "CMA/CNAS资质信息：未看到",
            "deepseek": "CMA/CNAS资质信息：未看到",
            "tongyi": "CMA/CNAS资质信息：未看到",
            "doubao": "CMA/CNAS资质信息：未看到",
            "wenxin": "CMA/CNAS资质信息：未看到",
        }
    )
    cma_row = next(row for row in table if row["field"] == "CMA/CNAS资质信息")

    assert cma_row["diff_result"] == "规则命中：报告缺少 CMA/CNAS 资质信息，需重点复核"
    assert cma_row["row_class"] == "not-extracted"
    assert cma_row["needs_key_review"] is True


def test_index_page_shows_report_upload_area():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "第三方检验报告上传" in html
    assert 'name="report_file"' in html
    assert ".pdf" in html


def test_report_pdf_upload_is_saved_to_report_folder(tmp_path):
    old_report_folder = flask_app.config["REPORT_UPLOAD_FOLDER"]
    flask_app.config["TESTING"] = True
    flask_app.config["REPORT_UPLOAD_FOLDER"] = str(tmp_path)
    client = flask_app.test_client()

    try:
        response = client.post(
            "/",
            data={
                "audit_type": "report",
                "report_file": (io.BytesIO(b"%PDF-1.4 test"), "sample.pdf"),
            },
            content_type="multipart/form-data",
        )
    finally:
        flask_app.config["REPORT_UPLOAD_FOLDER"] = old_report_folder

    saved_files = list(tmp_path.glob("*_sample.pdf"))
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert len(saved_files) == 1
    assert "已上传：" in html
    assert "sample.pdf" in html


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

    assert [row["field"] for row in compare_table] == EXPECTED_FIELDS
    assert summary["total"] == 15
    assert summary["same"] == 1
    assert summary["not_extracted"] == 14
    assert summary["warning"] == 0
    assert summary["different"] == 0
