import io
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import app as app_module
from app import (
    FIELDS,
    LABEL_REPORT_CROSS_CHECK_FIELDS,
    REPORT_COMPARE_FIELDS,
    REPORT_FIELDS,
    app as flask_app,
    build_compare_table,
    build_label_report_cross_check,
    build_report_compare_table,
    build_summary,
    cross_check_label_report,
    extract_field,
    extract_report_field,
    judge_difference,
)
import ai_clients
from ai_clients import AI_PLATFORM_CONFIG, call_ai_platform
from automation import deepseek_runner


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
    "样品规格",
    "判定依据",
    "签发日期",
    "CMA/CNAS资质结论",
    "标准必检项目清单",
    "报告项目匹配核对",
    "不合格及风险提示",
]

EXPECTED_REPORT_COMPARE_FIELDS = [
    "产品名称",
    "报告编号",
    "检验类别",
    "委托单位",
    "生产单位",
    "样品规格",
    "判定依据",
    "签发日期",
    "CMA/CNAS资质结论",
    "不合格及风险提示",
]

REPORT_TEXT = """产品名称：清爽橙汁饮料
报告编号：R20260508001
检验类别：委托检验
委托单位：示例贸易有限公司
生产单位：示例食品有限公司
样品规格：500mL/瓶
判定依据：GB/T 31121
签发日期：2026-05-08
CMA/CNAS资质结论：具备CMA资质
标准必检项目清单：感官、净含量、可溶性固形物、菌落总数、大肠菌群，需人工复核标准原文
报告项目匹配核对：报告项目与常见必检项目基本匹配，需人工复核标准原文
不合格及风险提示：1. 未发现明显风险，标准项目完整性仍需人工复核"""


def test_field_order_is_unified():
    assert FIELDS == EXPECTED_FIELDS


def test_report_field_order_is_unified():
    assert REPORT_FIELDS == EXPECTED_REPORT_FIELDS


def test_report_compare_field_order_is_unified():
    assert REPORT_COMPARE_FIELDS == EXPECTED_REPORT_COMPARE_FIELDS


def test_label_report_cross_check_field_order_is_unified():
    assert LABEL_REPORT_CROSS_CHECK_FIELDS == [
        ("产品名称", "产品名称", "产品名称"),
        ("生产企业", "生产单位", "生产主体"),
        ("委托企业", "委托单位", "委托主体"),
        ("净含量", "样品规格", "规格信息"),
        ("执行标准", "判定依据", "标准依据"),
    ]


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
    assert extract_report_field(REPORT_TEXT, "样品规格") == "500mL/瓶"
    assert extract_report_field(REPORT_TEXT, "判定依据") == "GB/T 31121"
    assert extract_report_field(REPORT_TEXT, "签发日期") == "2026-05-08"
    assert extract_report_field(REPORT_TEXT, "CMA/CNAS资质结论") == "具备CMA资质"


def test_report_risk_text_is_split_into_lines():
    text = "不合格及风险提示：1. 缺少检出限说明。2. 判定依据需复核。3. 需人工复核标准原文。"

    assert extract_report_field(text, "不合格及风险提示") == (
        "1. 缺少检出限说明。\n"
        "2. 判定依据需复核。\n"
        "3. 需人工复核标准原文。"
    )


def test_report_compare_table_order_matches_display_fields():
    table = build_report_compare_table(
        {
            "chatgpt": REPORT_TEXT,
            "deepseek": REPORT_TEXT,
            "tongyi": REPORT_TEXT,
            "doubao": REPORT_TEXT,
            "wenxin": REPORT_TEXT,
        }
    )

    assert [row["field"] for row in table] == EXPECTED_REPORT_COMPARE_FIELDS
    assert len(table) == 10
    assert table[-1]["field"] == "不合格及风险提示"


def test_report_compare_table_excludes_analysis_fields():
    table = build_report_compare_table(
        {
            "chatgpt": REPORT_TEXT,
            "deepseek": REPORT_TEXT,
            "tongyi": REPORT_TEXT,
            "doubao": REPORT_TEXT,
            "wenxin": REPORT_TEXT,
        }
    )
    fields = [row["field"] for row in table]

    assert "标准必检项目清单" not in fields
    assert "报告项目匹配核对" not in fields
    assert fields[-1] == "不合格及风险提示"
    assert "标准必检项目清单" in REPORT_FIELDS
    assert "报告项目匹配核对" in REPORT_FIELDS
    assert "不合格及风险提示" in REPORT_FIELDS


def test_report_page_only_renders_requested_report_compare_fields():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.post(
        "/",
        data={
            "audit_type": "report",
            "report_chatgpt_result": REPORT_TEXT,
            "report_deepseek_result": REPORT_TEXT,
            "report_tongyi_result": REPORT_TEXT,
            "report_doubao_result": REPORT_TEXT,
            "report_wenxin_result": REPORT_TEXT,
        },
    )
    html = response.get_data(as_text=True)
    table_start = html.index('<table id="reportResultTable">')
    table_end = html.index("</table>", table_start)
    report_table = html[table_start:table_end]

    assert "标准必检项目清单" not in report_table
    assert "报告项目匹配核对" not in report_table
    assert "不合格及风险提示" in report_table
    assert report_table.rfind("不合格及风险提示") > report_table.rfind("CMA/CNAS资质结论")
    assert "标准分析区域" not in html
    assert "报告项目审核区域" not in html
    assert "风险提示区域" not in html


def test_label_report_cross_check_matches_same_core_fields():
    table = build_label_report_cross_check(STANDARD_TEXT, REPORT_TEXT)
    rows = {row["item"]: row for row in table}

    assert rows["产品名称"]["result"] == "一致"
    assert rows["标准依据"]["result"] == "一致"
    assert rows["生产主体"]["result"] == "一致"
    assert rows["规格信息"]["result"] == "一致"


def test_label_report_cross_check_flags_different_values():
    report_text = REPORT_TEXT.replace("清爽橙汁饮料", "苹果汁饮料")
    table = build_label_report_cross_check(STANDARD_TEXT, report_text)
    product_row = next(row for row in table if row["item"] == "产品名称")

    assert product_row["label_value"] == "清爽橙汁饮料"
    assert product_row["report_value"] == "苹果汁饮料"
    assert product_row["result"] == "不一致，建议人工复核"
    assert product_row["row_class"] == "different"


def test_label_report_cross_check_marks_missing_side_as_warning():
    table = build_label_report_cross_check("产品名称：清爽橙汁饮料", REPORT_TEXT)
    standard_row = next(row for row in table if row["item"] == "标准依据")

    assert standard_row["label_value"] == "未提取到"
    assert standard_row["report_value"] == "GB/T 31121"
    assert standard_row["result"] == "标签未看到，建议人工复核"
    assert standard_row["row_class"] == "warning"


def test_cross_check_label_report_product_name_same_returns_same():
    table = cross_check_label_report({"产品名称": "清爽橙汁饮料"}, {"产品名称": "清爽橙汁饮料"})
    product_row = next(row for row in table if row["item"] == "产品名称")

    assert product_row["result"] == "一致"


def test_cross_check_label_report_different_values_returns_review_suggestion():
    table = cross_check_label_report({"产品名称": "清爽橙汁饮料"}, {"产品名称": "苹果汁饮料"})
    product_row = next(row for row in table if row["item"] == "产品名称")

    assert product_row["result"] == "不一致，建议人工复核"


def test_cross_check_label_report_label_missing_returns_label_missing():
    table = cross_check_label_report({"产品名称": "未看到"}, {"产品名称": "清爽橙汁饮料"})
    product_row = next(row for row in table if row["item"] == "产品名称")

    assert product_row["result"] == "标签未看到，建议人工复核"


def test_cross_check_label_report_report_missing_returns_report_missing():
    table = cross_check_label_report({"产品名称": "清爽橙汁饮料"}, {"产品名称": "未看到"})
    product_row = next(row for row in table if row["item"] == "产品名称")

    assert product_row["result"] == "报告未看到，建议人工复核"


def test_cross_check_label_report_both_missing_returns_both_missing():
    table = cross_check_label_report({"产品名称": "未看到"}, {"产品名称": "未看到"})
    product_row = next(row for row in table if row["item"] == "产品名称")

    assert product_row["result"] == "双方均未看到"


def test_cross_check_page_renders_cross_check_table():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.post(
        "/",
        data={
            "audit_type": "cross",
            "cross_label_text": STANDARD_TEXT,
            "cross_report_text": REPORT_TEXT,
        },
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "标签 vs 检验报告交叉核对" in html
    assert 'id="crossCheckTable"' in html
    assert "核对项目" in html
    assert "标签信息" in html
    assert "报告信息" in html
    assert "标准依据" in html


def test_label_compare_post_keeps_report_result():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()
    data = {"audit_type": "label"}
    for platform in ["chatgpt", "deepseek", "tongyi", "doubao", "wenxin"]:
        data[f"{platform}_result"] = STANDARD_TEXT
        data[f"report_{platform}_result"] = REPORT_TEXT

    response = client.post("/", data=data)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="labelResultTable"' in html
    assert 'id="reportResultTable"' in html
    assert "字段对比表" in html
    assert "报告字段对比表" in html


def test_report_compare_post_keeps_label_result():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()
    data = {"audit_type": "report"}
    for platform in ["chatgpt", "deepseek", "tongyi", "doubao", "wenxin"]:
        data[f"{platform}_result"] = STANDARD_TEXT
        data[f"report_{platform}_result"] = REPORT_TEXT

    response = client.post("/", data=data)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="labelResultTable"' in html
    assert 'id="reportResultTable"' in html
    assert "字段对比表" in html
    assert "报告字段对比表" in html


def test_cross_check_post_reads_saved_label_and_report_results():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()
    data = {"audit_type": "cross"}
    for platform in ["chatgpt", "deepseek", "tongyi", "doubao", "wenxin"]:
        data[f"{platform}_result"] = STANDARD_TEXT
        data[f"report_{platform}_result"] = REPORT_TEXT

    response = client.post("/", data=data)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="labelResultTable"' in html
    assert 'id="reportResultTable"' in html
    assert 'id="crossCheckTable"' in html
    assert "产品名称" in html
    assert "标准依据" in html


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
            "chatgpt": "CMA/CNAS资质结论：未看到CMA/CNAS资质",
            "deepseek": "CMA/CNAS资质结论：未看到CMA/CNAS资质",
            "tongyi": "CMA/CNAS资质结论：未看到CMA/CNAS资质",
            "doubao": "CMA/CNAS资质结论：未看到CMA/CNAS资质",
            "wenxin": "CMA/CNAS资质结论：未看到CMA/CNAS资质",
        }
    )
    cma_row = next(row for row in table if row["field"] == "CMA/CNAS资质结论")

    assert cma_row["diff_result"] == "规则命中：报告缺少 CMA/CNAS 资质结论，需重点复核"
    assert cma_row["row_class"] == "not-extracted"
    assert cma_row["needs_key_review"] is True


def test_report_compare_table_hits_missing_conclusion_rule():
    table = build_report_compare_table({})
    conclusion_field = REPORT_COMPARE_FIELDS[-1]
    conclusion_row = next(row for row in table if row["field"] == conclusion_field)

    assert conclusion_row["diff_result"] == app_module.REPORT_MISSING_RULES[conclusion_field]
    assert conclusion_row["row_class"] == "not-extracted"
    assert conclusion_row["needs_key_review"] is True


def test_extract_cma_cnas_conclusion_from_detailed_text():
    assert extract_report_field("CMA/CNAS资质结论：同时具备CMA和CNAS资质", "CMA/CNAS资质结论") == "同时具备CMA和CNAS资质"
    assert extract_report_field("CMA/CNAS资质信息：CMA资质编号：2026000000", "CMA/CNAS资质结论") == "具备CMA资质"
    assert extract_report_field("CMA/CNAS资质结论：未看到", "CMA/CNAS资质结论") == "未看到CMA/CNAS资质"


def test_index_page_shows_report_upload_area():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "第三方检验报告上传" in html
    assert 'name="report_file"' in html
    assert ".pdf" in html


def test_action_buttons_are_not_default_submit_buttons():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert 'type="submit"' not in html
    assert 'id="labelCompareButton"' in html
    assert 'id="reportCompareButton"' in html
    assert 'id="crossCheckButton"' in html
    assert 'id="labelCompareButton">生成对比表格' in html
    assert 'id="reportCompareButton">生成报告对比表格' in html
    assert 'id="crossCheckButton">生成交叉核对表' in html


def test_page_preserves_current_position_without_auto_scroll_targets():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "preservedScrollPosition" in html
    assert 'submitModuleForm("labelAuditForm")' in html
    assert 'submitModuleForm("reportAuditForm")' in html
    assert 'submitModuleForm("crossCheckForm")' in html
    assert "scrollIntoView" not in html
    assert "pendingScrollTarget" not in html
    assert "window.location" not in html
    assert "location.reload" not in html
    assert "scrollTo(0, 0)" not in html


def test_ai_platform_missing_key_returns_clear_error(monkeypatch):
    for config in AI_PLATFORM_CONFIG.values():
        for env_key in config["env_keys"]:
            monkeypatch.delenv(env_key, raising=False)

    result = call_ai_platform("chatgpt", "test prompt")

    assert result == {
        "platform": "ChatGPT",
        "success": False,
        "content": "",
        "error": "未配置对应API Key",
    }


def test_ai_platform_returns_unified_structure_without_key(monkeypatch):
    for config in AI_PLATFORM_CONFIG.values():
        for env_key in config["env_keys"]:
            monkeypatch.delenv(env_key, raising=False)

    result = call_ai_platform("deepseek", "test prompt")

    assert set(result.keys()) == {"platform", "success", "content", "error"}
    assert result["platform"] == "DeepSeek"
    assert result["success"] is False
    assert result["content"] == ""
    assert result["error"] == "未配置对应API Key"


class FakeDeepSeekResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self.payload = payload
        self.text = text

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload

        return self.payload


def test_deepseek_success_returns_unified_structure(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeDeepSeekResponse(
            payload={
                "choices": [
                    {
                        "message": {
                            "content": "产品名称：测试产品",
                        }
                    }
                ]
            }
        )

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai_clients.requests, "post", fake_post)

    result = call_ai_platform("deepseek", "请审核")

    assert result == {
        "platform": "DeepSeek",
        "success": True,
        "content": "产品名称：测试产品",
        "error": "",
    }
    assert captured["url"] == ai_clients.DEEPSEEK_API_URL
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "deepseek-chat"
    assert captured["json"]["messages"][0] == {
        "role": "system",
        "content": "你是食品标签和检验报告审核助手",
    }
    assert captured["json"]["messages"][1] == {"role": "user", "content": "请审核"}


def test_deepseek_network_error_does_not_crash(monkeypatch):
    def fake_post(url, headers, json, timeout):
        raise ai_clients.requests.RequestException("network down")

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai_clients.requests, "post", fake_post)

    result = call_ai_platform("deepseek", "请审核")

    assert result["platform"] == "DeepSeek"
    assert result["success"] is False
    assert result["content"] == ""
    assert "DeepSeek网络请求失败" in result["error"]


def test_deepseek_non_200_returns_error(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeDeepSeekResponse(status_code=401, text="unauthorized")

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai_clients.requests, "post", fake_post)

    result = call_ai_platform("deepseek", "请审核")

    assert result["success"] is False
    assert result["error"] == "DeepSeek API返回非200：401 unauthorized"


def test_deepseek_invalid_json_returns_error(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeDeepSeekResponse(payload=ValueError("bad json"))

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai_clients.requests, "post", fake_post)

    result = call_ai_platform("deepseek", "请审核")

    assert result["success"] is False
    assert "DeepSeek响应JSON解析失败" in result["error"]


def test_deepseek_empty_content_returns_error(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeDeepSeekResponse(payload={"choices": [{"message": {"content": "  "}}]})

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(ai_clients.requests, "post", fake_post)

    result = call_ai_platform("deepseek", "请审核")

    assert result["success"] is False
    assert result["error"] == "DeepSeek返回内容为空"


def test_label_ai_api_route_returns_errors_without_keys(monkeypatch):
    for config in AI_PLATFORM_CONFIG.values():
        for env_key in config["env_keys"]:
            monkeypatch.delenv(env_key, raising=False)

    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.post("/api/run_label_ai", json={"prompt": "标签提示词"})
    data = response.get_json()

    assert response.status_code == 200
    assert set(data["results"].keys()) == set(AI_PLATFORM_CONFIG.keys())
    assert all(result["success"] is False for result in data["results"].values())
    assert all(result["error"] == "未配置对应API Key" for result in data["results"].values())


def test_report_ai_api_route_returns_errors_without_keys(monkeypatch):
    for config in AI_PLATFORM_CONFIG.values():
        for env_key in config["env_keys"]:
            monkeypatch.delenv(env_key, raising=False)

    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.post("/api/run_report_ai", json={"prompt": "报告提示词"})
    data = response.get_json()

    assert response.status_code == 200
    assert set(data["results"].keys()) == set(AI_PLATFORM_CONFIG.keys())
    assert all(result["success"] is False for result in data["results"].values())
    assert all(result["error"] == "未配置对应API Key" for result in data["results"].values())


def test_index_page_shows_ai_api_buttons():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert 'id="run_label_ai_button"' in html
    assert 'id="run_report_ai_button"' in html
    assert "/api/run_label_ai" in html
    assert "/api/run_report_ai" in html


def test_deepseek_runner_file_exists():
    runner_path = ROOT_DIR / "automation" / "deepseek_runner.py"

    assert runner_path.exists()


def test_deepseek_runner_core_functions_are_importable():
    assert deepseek_runner.DEEPSEEK_CHAT_URL == "https://chat.deepseek.com/"
    assert deepseek_runner.DEEPSEEK_BROWSER_DATA_DIR == (
        ROOT_DIR / "automation" / "browser_data" / "deepseek"
    )
    assert callable(deepseek_runner.ensure_deepseek_browser_data_dir)
    assert callable(deepseek_runner.open_deepseek_with_persistent_context)


def test_deepseek_helper_buttons_are_near_platform_inputs():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "打开 DeepSeek" in html
    assert "复制标签审核提示词" in html
    assert "复制检验报告审核提示词" in html
    assert 'class="small-button deepseek-open-button" type="button"' in html
    assert 'class="small-button deepseek-copy-label-prompt-button" type="button"' in html
    assert 'class="small-button deepseek-copy-report-prompt-button" type="button"' in html
    label_deepseek_start = html.index('for="deepseek_result"')
    label_deepseek_end = html.index('id="deepseek_result"', label_deepseek_start)
    report_deepseek_start = html.index('for="report_deepseek_result"')
    report_deepseek_end = html.index('id="report_deepseek_result"', report_deepseek_start)

    assert "打开 DeepSeek" in html[label_deepseek_start:label_deepseek_end]
    assert "复制标签审核提示词" in html[label_deepseek_start:label_deepseek_end]
    assert "打开 DeepSeek" in html[report_deepseek_start:report_deepseek_end]
    assert "复制检验报告审核提示词" in html[report_deepseek_start:report_deepseek_end]


def test_deepseek_helper_shows_manual_file_instructions():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "当前标签文件：" in html
    assert "尚未上传标签图片" in html
    assert "在 DeepSeek 网页中上传当前标签图片" in html
    assert "点击生成标签对比表" in html
    assert "当前报告文件：" in html
    assert "尚未上传检验报告" in html
    assert "在 DeepSeek 网页中上传当前检验报告" in html
    assert "点击生成报告对比表" in html


def test_file_inputs_update_deepseek_current_file_names():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert 'id="label_current_file_name"' in html
    assert 'id="report_current_file_name"' in html
    assert 'fileInput.addEventListener("change"' in html
    assert 'bindCurrentFileName("label_image", "label_current_file_name", "尚未上传标签图片")' in html
    assert 'bindCurrentFileName("report_file", "report_current_file_name", "尚未上传检验报告")' in html


def test_open_deepseek_route_starts_runner_without_blocking(monkeypatch):
    captured = {}

    class FakeProcess:
        pass

    def fake_popen(args, cwd):
        captured["args"] = args
        captured["cwd"] = cwd
        return FakeProcess()

    monkeypatch.setattr(app_module.subprocess, "Popen", fake_popen)
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.post("/automation/open_deepseek")
    data = response.get_json()

    assert response.status_code == 200
    assert data == {
        "success": True,
        "message": "DeepSeek 已打开，请上传文件并粘贴提示词",
    }
    assert captured["args"][0] == sys.executable
    assert captured["args"][1].endswith("automation\\deepseek_runner.py") or captured["args"][1].endswith("automation/deepseek_runner.py")
    assert captured["cwd"] == str(ROOT_DIR)


def test_report_prompt_excludes_removed_fields():
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)
    prompt_start = html.index('<textarea class="prompt-box" id="report_prompt" readonly>')
    prompt_end = html.index("</textarea>", prompt_start)
    report_prompt = html[prompt_start:prompt_end]

    assert "执行标准" not in report_prompt
    assert "检验依据" not in report_prompt
    assert "检验机构" not in report_prompt
    assert "CMA/CNAS资质信息" not in report_prompt
    assert "CMA/CNAS资质结论" in report_prompt


def test_label_upload_file_name_is_shown_in_deepseek_helper(tmp_path):
    old_upload_folder = flask_app.config["UPLOAD_FOLDER"]
    flask_app.config["TESTING"] = True
    flask_app.config["UPLOAD_FOLDER"] = str(tmp_path)
    client = flask_app.test_client()

    try:
        response = client.post(
            "/",
            data={
                "audit_type": "label",
                "label_image": (io.BytesIO(b"fake image"), "label-sample.png"),
            },
            content_type="multipart/form-data",
        )
    finally:
        flask_app.config["UPLOAD_FOLDER"] = old_upload_folder

    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "当前标签文件：" in html
    assert "label-sample.png" in html
    label_file_start = html.index('id="label_current_file_name"')
    label_file_end = html.index("</span>", label_file_start)
    label_file_hint = html[label_file_start:label_file_end]

    assert "label-sample.png" in label_file_hint
    assert "尚未上传标签图片" not in label_file_hint


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
