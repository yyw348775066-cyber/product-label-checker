import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from ai_clients import call_all_ai_platforms


app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = "uploads"
REPORT_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "reports")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
REPORT_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["REPORT_UPLOAD_FOLDER"] = REPORT_UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_UPLOAD_FOLDER, exist_ok=True)


FIELDS = [
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


AI_PLATFORMS = [
    {"key": "chatgpt", "name": "ChatGPT"},
    {"key": "deepseek", "name": "DeepSeek"},
    {"key": "tongyi", "name": "通义千问"},
    {"key": "doubao", "name": "豆包"},
    {"key": "wenxin", "name": "文心一言"},
]


REPORT_FIELDS = [
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


REPORT_COMPARE_FIELDS = [
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


LABEL_REPORT_CROSS_CHECK_FIELDS = [
    ("产品名称", "产品名称", "产品名称"),
    ("生产企业", "生产单位", "生产主体"),
    ("委托企业", "委托单位", "委托主体"),
    ("净含量", "样品规格", "规格信息"),
    ("执行标准", "判定依据", "标准依据"),
]


FIELD_PATTERNS = {
    "产品名称": [
        r"(?:产品名称|品名|名称)\s*[:：]\s*(.+)",
    ],
    "执行标准": [
        r"(?:执行标准|产品标准号|标准号|标准)\s*[:：]\s*([A-Z0-9/T\.\- ]+)",
        r"\b(GB/T\s*\d+(?:\.\d+)?(?:-\d+)?|GB\s*\d+(?:\.\d+)?(?:-\d+)?|Q/[A-Z0-9\-\s]+)\b",
    ],
    "生产许可证": [
        r"(?:生产许可证|食品生产许可证编号|许可证编号|SC)\s*[:：]?\s*([A-Z0-9]{10,})",
        r"\b(SC\d{14})\b",
    ],
    "配料表": [
        r"(?:配料表|配料|原料)\s*[:：]\s*(.+)",
    ],
    "质量等级": [
        r"(?:质量等级|品质等级|等级)\s*[:：]\s*(.+)",
    ],
    "生产日期": [
        r"(?:生产日期|生产批号|批号|见喷码|见包装)\s*[:：]\s*(.+)",
        r"(?:生产日期|生产批号)\s*([0-9]{4}[年\-/\.][0-9]{1,2}[月\-/\.][0-9]{1,2}日?)",
    ],
    "保质期": [
        r"(?:保质期|保存期限|质保期)\s*[:：]\s*(.+)",
        r"保质期\s*(\d+\s*(?:天|个月|月|年))",
    ],
    "净含量": [
        r"(?:净含量|规格)\s*[:：]\s*(.+)",
        r"\b(\d+(?:\.\d+)?\s*(?:kg|g|克|千克|ml|mL|毫升|L|升))\b",
    ],
    "生产企业": [
        r"(?:生产企业|生产商|制造商|生产厂家|生产单位)\s*[:：]\s*(.+)",
    ],
    "生产企业地址": [
        r"(?:生产企业地址|生产地址|生产厂家地址|生产单位地址|地址)\s*[:：]\s*(.+)",
    ],
    "委托企业": [
        r"(?:委托企业|委托方|委托单位|委托商)\s*[:：]\s*(.+)",
    ],
    "委托企业地址": [
        r"(?:委托企业地址|委托方地址|委托单位地址|委托商地址)\s*[:：]\s*(.+)",
    ],
    "联系方式": [
        r"(?:联系方式|联系电话|电话|服务热线|客服电话|客服热线|网址|网站|邮箱|电子邮箱)\s*[:：]\s*(.+)",
    ],
    "贮存条件": [
        r"(?:贮存条件|储存条件|保存条件|贮藏条件|储藏条件)\s*[:：]\s*(.+)",
    ],
    "标签风险提示": [
        r"(?:标签风险提示|风险提示|问题|不符合|疑点|风险|建议)\s*[:：]\s*(.+)",
    ],
}

REPORT_FIELD_PATTERNS = {
    "产品名称": [
        r"(?:产品名称|样品名称|品名|名称)\s*[:：]\s*(.+)",
    ],
    "报告编号": [
        r"(?:报告编号|检验报告编号|报告号|编号)\s*[:：]\s*(.+)",
    ],
    "检验类别": [
        r"(?:检验类别|检验类型|检验性质|类别)\s*[:：]\s*(.+)",
    ],
    "委托单位": [
        r"(?:委托单位|委托方|送检单位|客户名称)\s*[:：]\s*(.+)",
    ],
    "生产单位": [
        r"(?:生产单位|生产企业|生产商|制造商)\s*[:：]\s*(.+)",
    ],
    "样品规格": [
        r"(?:样品规格|规格型号|规格|型号)\s*[:：]\s*(.+)",
    ],
    "判定依据": [
        r"(?:判定依据|评价依据|判定标准)\s*[:：]\s*(.+)",
    ],
    "签发日期": [
        r"(?:签发日期|签发时间|批准日期|报告日期|签发)\s*[:：]\s*(.+)",
    ],
    "CMA/CNAS资质结论": [
        r"(?:CMA/CNAS资质结论|CMA/CNAS资质信息|资质结论|资质信息|CMA|CNAS|资质认定)\s*[:：]\s*(.+)",
    ],
    "标准必检项目清单": [
        r"(?:标准必检项目清单|必检项目清单|标准项目清单|必检项目)\s*[:：]\s*(.+)",
    ],
    "报告项目匹配核对": [
        r"(?:报告项目匹配核对|项目匹配核对|报告项目审核|项目核对)\s*[:：]\s*(.+)",
    ],
    "不合格及风险提示": [
        r"(?:不合格及风险提示|不合格提示|报告风险提示|风险提示|不合格|风险)\s*[:：]\s*(.+)",
    ],
}

FIELD_ALIASES = {
    "产品名称": ["产品名称", "品名", "名称"],
    "执行标准": ["执行标准", "产品标准号", "标准号", "标准"],
    "生产许可证": ["生产许可证", "食品生产许可证编号", "许可证编号"],
    "配料表": ["配料表", "配料", "原料"],
    "质量等级": ["质量等级", "品质等级", "等级"],
    "生产日期": ["生产日期", "生产批号", "批号", "见喷码", "见包装"],
    "保质期": ["保质期", "保存期限", "质保期"],
    "净含量": ["净含量", "规格"],
    "生产企业": ["生产企业", "生产商", "制造商", "生产厂家", "生产单位"],
    "生产企业地址": ["生产企业地址", "生产地址", "生产厂家地址", "生产单位地址"],
    "委托企业": ["委托企业", "委托方", "委托单位", "委托商"],
    "委托企业地址": ["委托企业地址", "委托方地址", "委托单位地址", "委托商地址"],
    "联系方式": ["联系方式", "联系电话", "电话", "服务热线", "客服电话", "客服热线", "网址", "网站", "邮箱", "电子邮箱"],
    "贮存条件": ["贮存条件", "储存条件", "保存条件", "贮藏条件", "储藏条件"],
    "标签风险提示": ["标签风险提示", "风险提示", "问题", "不符合", "疑点", "风险", "建议"],
}

REPORT_FIELD_ALIASES = {
    "产品名称": ["产品名称", "样品名称", "品名", "名称"],
    "报告编号": ["报告编号", "检验报告编号", "报告号"],
    "检验类别": ["检验类别", "检验类型", "检验性质", "类别"],
    "委托单位": ["委托单位", "委托方", "送检单位", "客户名称"],
    "生产单位": ["生产单位", "生产企业", "生产商", "制造商"],
    "样品规格": ["样品规格", "规格型号", "规格", "型号"],
    "判定依据": ["判定依据", "评价依据", "判定标准"],
    "签发日期": ["签发日期", "签发时间", "批准日期", "报告日期"],
    "CMA/CNAS资质结论": ["CMA/CNAS资质结论", "CMA/CNAS资质信息", "资质结论", "资质信息", "CMA", "CNAS", "资质认定"],
    "标准必检项目清单": ["标准必检项目清单", "必检项目清单", "标准项目清单", "必检项目"],
    "报告项目匹配核对": ["报告项目匹配核对", "项目匹配核对", "报告项目审核", "项目核对"],
    "不合格及风险提示": ["不合格及风险提示", "不合格提示", "报告风险提示", "风险提示", "不合格", "风险"],
}

INVALID_RESULTS = {"未提取到", "未填写", "未看到", "未看见", "未看到CMA/CNAS资质"}
KEY_FIELDS = {"净含量", "执行标准", "配料表", "生产许可证", "标签风险提示"}
REPORT_KEY_FIELDS = {"判定依据", "CMA/CNAS资质结论", "标准必检项目清单", "报告项目匹配核对", "不合格及风险提示"}
LABEL_MISSING_RULES = {
    "生产许可证": "规则命中：未看到生产许可证，需重点复核",
    "联系方式": "规则命中：未看到联系方式，需重点复核",
    "贮存条件": "规则命中：未看到贮存条件，需重点复核",
}
REPORT_MISSING_RULES = {
    "CMA/CNAS资质结论": "规则命中：报告缺少 CMA/CNAS 资质结论，需重点复核",
    "判定依据": "规则命中：报告缺少判定依据，需重点复核",
    "签发日期": "规则命中：签发日期未看到，需重点复核",
}
REPORT_MISSING_RULES[REPORT_COMPARE_FIELDS[-1]] = (
    "规则命中：报告未看到检验结论或风险提示，需重点复核"
)
RISK_KEYWORDS = [
    "不符合",
    "风险",
    "缺失",
    "错误",
    "不一致",
    "建议复核",
    "未标注",
    "违法",
    "涉嫌",
]
NO_RISK_PHRASES = [
    "暂无明显风险",
    "暂未发现明显风险",
    "未发现明显风险",
    "未见明显风险",
    "无明显风险",
    "暂无风险",
    "未发现明显标签风险",
    "未发现明显风险",
    "未发现明显风险标准项目完整性仍需人工复核",
]


def allowed_file(filename, allowed_extensions=None):
    allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def make_safe_filename(filename, default_stem="label"):
    name = secure_filename(filename)
    if not name:
        extension = filename.rsplit(".", 1)[1].lower()
        name = f"{default_stem}.{extension}"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}_{name}"


def clean_value(value):
    value = re.sub(r"\s+", " ", value).strip(" ：:，,。.;；")
    return value or "未提取到"


def extract_quantity_value(value):
    match = re.search(
        r"(\d+(?:\.\d+)?\s*(?:kg|g|克|千克|ml|mL|毫升|L|升))",
        value,
        re.IGNORECASE,
    )
    if not match:
        return clean_value(value)

    return re.sub(r"\s+", "", match.group(1))


def normalize_cma_cnas_conclusion(value):
    value = clean_value(value)
    normalized = re.sub(r"\s+", "", value).upper()

    if any(missing_text in value for missing_text in INVALID_RESULTS):
        return "未看到CMA/CNAS资质"
    if "无法判断" in value:
        return "无法判断，需人工复核"

    has_cma = "CMA" in normalized
    has_cnas = "CNAS" in normalized
    if has_cma and has_cnas:
        return "同时具备CMA和CNAS资质"
    if has_cma:
        return "具备CMA资质"
    if has_cnas:
        return "具备CNAS资质"

    return value


def all_field_aliases(field_aliases_map=None):
    field_aliases_map = field_aliases_map or FIELD_ALIASES
    aliases = []
    for field_aliases in field_aliases_map.values():
        aliases.extend(field_aliases)
    return sorted(set(aliases), key=len, reverse=True)


def find_labeled_value(text, field, field_aliases_map=None, risk_field="标签风险提示"):
    field_aliases_map = field_aliases_map or FIELD_ALIASES
    aliases = sorted(field_aliases_map.get(field, []), key=len, reverse=True)
    if not aliases:
        return None

    alias_pattern = "|".join(re.escape(alias) for alias in aliases)
    label_match = re.search(rf"(?:{alias_pattern})\s*[:：]", text, re.IGNORECASE)
    if not label_match:
        return None

    start = label_match.end()
    next_alias_pattern = "|".join(re.escape(alias) for alias in all_field_aliases(field_aliases_map))
    next_label = re.search(rf"(?:{next_alias_pattern})\s*[:：]", text[start:], re.IGNORECASE)
    end = start + next_label.start() if next_label else len(text)

    if field == risk_field:
        return text[start:end].strip(" ：:，,;；") or "未提取到"

    value = text[start:end]
    if field == "净含量":
        return extract_quantity_value(value)
    if field == "CMA/CNAS资质结论":
        return normalize_cma_cnas_conclusion(value)

    return clean_value(value)


def format_risk_text(text):
    if not text:
        return "未提取到"

    text = str(text).strip()

    # 统一空白，但不要删除编号
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # 如果已经包含 1. / 1、 / （1） 这种编号，则只在编号前换行，不删除编号
    if re.search(r"(\d+[\.、]|（\d+）|\(\d+\))", text):
        text = re.sub(r"\s*(?=(?:\d+[\.、]|（\d+）|\(\d+\)))", "\n", text)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    # 如果没有编号，则按常见分隔符切分并自动补编号
    parts = re.split(r"[；;。]\s*", text)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) > 1:
        return "\n".join([f"{i+1}. {part}" for i, part in enumerate(parts)])

    return text


def extract_field_with_config(text, field, field_patterns, field_aliases, risk_field):
    if not text.strip():
        return "未填写"

    labeled_value = find_labeled_value(text, field, field_aliases, risk_field)
    if labeled_value:
        if field == risk_field:
            return format_risk_text(labeled_value)
        return labeled_value

    for pattern in field_patterns.get(field, []):
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = clean_value(match.group(1))
            if field == risk_field:
                return format_risk_text(value)
            if field == "净含量":
                return extract_quantity_value(value)
            if field == "CMA/CNAS资质结论":
                return normalize_cma_cnas_conclusion(value)
            return value

    return "未提取到"


def extract_field(text, field):
    return extract_field_with_config(text, field, FIELD_PATTERNS, FIELD_ALIASES, "标签风险提示")


def extract_report_field(text, field):
    return extract_field_with_config(
        text,
        field,
        REPORT_FIELD_PATTERNS,
        REPORT_FIELD_ALIASES,
        "不合格及风险提示",
    )


def is_valid_result(value):
    return value not in INVALID_RESULTS


def is_no_risk_statement(value):
    normalized = re.sub(r"\s+", "", value)
    return any(phrase in normalized for phrase in NO_RISK_PHRASES)


def normalize_for_compare(value, field=None):
    if not is_valid_result(value):
        return value

    if field in {"标签风险提示", "不合格及风险提示"} and is_no_risk_statement(value):
        return "无明显风险"

    normalized = re.sub(r"\s+", " ", value).strip()
    if field == "净含量":
        normalized = normalized.lower()
        normalized = normalized.replace("毫升", "ml")
        normalized = normalized.replace("千克", "kg")
        normalized = normalized.replace("克", "g")
        normalized = re.sub(r"\s+", "", normalized)
        return normalized.upper()

    looks_like_standard = bool(re.search(r"\b(?:GB|QB|Q|SB|NY|DB)[/-]?", normalized, re.IGNORECASE))
    if field == "执行标准" or (field is None and looks_like_standard):
        normalized = re.sub(r"\s+", "", normalized).upper()

    return normalized


def normalize_for_cross_check(value, field):
    if not is_valid_result(value):
        return value

    if field in {"净含量", "样品规格"}:
        return normalize_for_compare(extract_quantity_value(value), "净含量")
    if field in {"执行标准", "判定依据"}:
        return normalize_for_compare(value, "执行标准")

    return re.sub(r"\s+", "", value).strip()


def judge_difference(values, field=None):
    valid_values = [value for value in values if is_valid_result(value)]

    if not valid_values:
        return "均未提取到", "not-extracted"

    if len(valid_values) == 1:
        return "仅一个平台提取到，需复核", "warning"

    normalized_values = [normalize_for_compare(value, field) for value in valid_values]
    if len(set(normalized_values)) == 1:
        return "一致", "same"

    return "存在差异，需人工复核", "different"


def judge_cross_check(label_value, report_value, label_field, report_field):
    label_valid = is_valid_result(label_value)
    report_valid = is_valid_result(report_value)

    if not label_valid and not report_valid:
        return "双方均未看到", "not-extracted"
    if not label_valid:
        return "标签未看到，建议人工复核", "warning"
    if not report_valid:
        return "报告未看到，建议人工复核", "warning"

    normalized_label = normalize_for_cross_check(label_value, label_field)
    normalized_report = normalize_for_cross_check(report_value, report_field)
    if normalized_label == normalized_report:
        return "一致", "same"

    if "无法判断" in normalized_label or "无法判断" in normalized_report:
        return "无法判断，建议人工复核", "warning"

    return "不一致，建议人工复核", "different"


def resolve_cross_check_value(data, field, extractor):
    if isinstance(data, dict):
        value = data.get(field, "未提取到")
        return clean_value(str(value))

    return extractor(data or "", field)


def cross_check_label_report(label_data, report_data):
    table = []

    for label_field, report_field, field_name in LABEL_REPORT_CROSS_CHECK_FIELDS:
        label_value = resolve_cross_check_value(label_data, label_field, extract_field)
        report_value = resolve_cross_check_value(report_data, report_field, extract_report_field)
        result, row_class = judge_cross_check(label_value, report_value, label_field, report_field)
        table.append(
            {
                "item": field_name,
                "label_field": label_field,
                "report_field": report_field,
                "label_value": label_value,
                "report_value": report_value,
                "result": result,
                "note": "",
                "row_class": row_class,
            }
        )

    return table


def build_label_report_cross_check(label_text, report_text):
    return cross_check_label_report(label_text, report_text)


def has_risk_keyword(values):
    return any(
        keyword in value
        for value in values
        if not is_no_risk_statement(value)
        for keyword in RISK_KEYWORDS
    )


def apply_missing_field_rule(field, values, diff_result, missing_rules):
    if field in missing_rules and all(not is_valid_result(value) for value in values):
        return missing_rules[field]

    return diff_result


def is_rule_hit(diff_result):
    return diff_result.startswith("规则命中：")


def build_cell_classes(values, field, diff_result):
    classes = {platform["key"]: "" for platform in AI_PLATFORMS}
    valid_items = {
        key: normalize_for_compare(value, field)
        for key, value in values.items()
        if is_valid_result(value)
    }

    if diff_result == "存在风险提示，需重点复核":
        for key, value in values.items():
            if not is_no_risk_statement(value) and any(keyword in value for keyword in RISK_KEYWORDS):
                classes[key] = "cell-risk"
        return classes

    if diff_result != "存在差异，需人工复核" or not valid_items:
        return classes

    counts = {}
    for normalized in valid_items.values():
        counts[normalized] = counts.get(normalized, 0) + 1

    max_count = max(counts.values())
    for key, normalized in valid_items.items():
        if counts[normalized] < max_count or len(counts) == len(valid_items):
            classes[key] = "cell-different"

    return classes


def build_compare_table(results):
    table = []

    for field in FIELDS:
        values = {
            platform["key"]: extract_field(results.get(platform["key"], ""), field)
            for platform in AI_PLATFORMS
        }
        diff_result, row_class = judge_difference(values.values(), field)
        diff_result = apply_missing_field_rule(field, values.values(), diff_result, LABEL_MISSING_RULES)
        if field == "标签风险提示" and has_risk_keyword(values.values()):
            diff_result = "存在风险提示，需重点复核"

        needs_key_review = (field in KEY_FIELDS and diff_result != "一致") or is_rule_hit(diff_result)
        cell_classes = build_cell_classes(values, field, diff_result)

        table.append(
            {
                "field": field,
                **values,
                "diff_result": diff_result,
                "row_class": row_class,
                "is_key_field": field in KEY_FIELDS,
                "needs_key_review": needs_key_review,
                "cell_classes": cell_classes,
            }
        )

    return table


def build_report_compare_table(results):
    table = []

    for field in REPORT_COMPARE_FIELDS:
        values = {
            platform["key"]: extract_report_field(results.get(platform["key"], ""), field)
            for platform in AI_PLATFORMS
        }
        diff_result, row_class = judge_difference(values.values(), field)
        diff_result = apply_missing_field_rule(field, values.values(), diff_result, REPORT_MISSING_RULES)
        if field == "不合格及风险提示" and has_risk_keyword(values.values()):
            diff_result = "存在风险提示，需重点复核"

        needs_key_review = (field in REPORT_KEY_FIELDS and diff_result != "一致") or is_rule_hit(diff_result)
        cell_classes = build_cell_classes(values, field, diff_result)

        table.append(
            {
                "field": field,
                **values,
                "diff_result": diff_result,
                "row_class": row_class,
                "is_key_field": field in REPORT_KEY_FIELDS,
                "needs_key_review": needs_key_review,
                "cell_classes": cell_classes,
            }
        )

    return table


def build_summary(compare_table):
    summary = {
        "total": len(compare_table),
        "same": 0,
        "different": 0,
        "warning": 0,
        "not_extracted": 0,
        "key_review": 0,
        "suggestion": "",
        "suggestion_class": "neutral",
    }

    for row in compare_table:
        if row["needs_key_review"]:
            summary["key_review"] += 1

        if row["row_class"] == "same":
            summary["same"] += 1
        elif row["row_class"] == "different":
            summary["different"] += 1
        elif row["row_class"] == "warning":
            summary["warning"] += 1
        elif row["row_class"] == "not-extracted":
            summary["not_extracted"] += 1

    if summary["key_review"] > 0:
        summary["suggestion"] = "存在重点风险字段，建议优先人工复核执行标准、生产许可证、配料表或风险提示。"
        summary["suggestion_class"] = "danger"
    elif summary["not_extracted"] == summary["total"]:
        summary["suggestion"] = "未提取到有效字段，请检查粘贴内容或提示词。"
        summary["suggestion_class"] = "neutral"
    elif summary["different"] > 0:
        summary["suggestion"] = "存在关键信息差异，建议优先人工复核。"
        summary["suggestion_class"] = "danger"
    elif summary["warning"] > 0:
        summary["suggestion"] = "部分字段信息不足，建议补充核对。"
        summary["suggestion_class"] = "warning"
    elif summary["same"] == summary["total"]:
        summary["suggestion"] = "多平台结果基本一致，可进入下一步审核。"
        summary["suggestion_class"] = "success"
    else:
        summary["suggestion"] = "部分字段未提取到，建议结合原标签继续核对。"
        summary["suggestion_class"] = "neutral"

    return summary


def has_any_result(results):
    return any(value.strip() for value in results.values())


def first_filled_result(results):
    for value in results.values():
        if value.strip():
            return value.strip()

    return ""


@app.route("/", methods=["GET", "POST"])
def index():
    image_url = None
    compare_table = None
    summary = None
    report_compare_table = None
    report_summary = None
    error = None
    label_file_name = None
    report_error = None
    report_file_url = None
    report_file_name = None
    report_file_is_image = False
    ai_results = {platform["key"]: "" for platform in AI_PLATFORMS}
    report_results = {platform["key"]: "" for platform in AI_PLATFORMS}
    cross_label_text = ""
    cross_report_text = ""
    cross_check_table = None

    if request.method == "POST":
        audit_type = request.form.get("audit_type", "label")
        file = request.files.get("label_image")
        for platform in AI_PLATFORMS:
            ai_results[platform["key"]] = request.form.get(f"{platform['key']}_result", "").strip()
            report_results[platform["key"]] = request.form.get(f"report_{platform['key']}_result", "").strip()
        cross_label_text = request.form.get("cross_label_text", "").strip()
        cross_report_text = request.form.get("cross_report_text", "").strip()

        if audit_type == "label" and file and file.filename:
            if allowed_file(file.filename):
                filename = make_safe_filename(file.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
                image_url = url_for("static_upload", filename=filename)
                label_file_name = file.filename
            else:
                error = "仅支持 png、jpg、jpeg、webp 格式的图片。"

        if audit_type == "report":
            report_file = request.files.get("report_file")
            if report_file and report_file.filename:
                if allowed_file(report_file.filename, REPORT_ALLOWED_EXTENSIONS):
                    filename = make_safe_filename(report_file.filename, "report")
                    save_path = os.path.join(app.config["REPORT_UPLOAD_FOLDER"], filename)
                    report_file.save(save_path)
                    report_file_url = url_for("report_upload", filename=filename)
                    report_file_name = report_file.filename
                    report_file_is_image = filename.rsplit(".", 1)[1].lower() in {"png", "jpg", "jpeg"}
                else:
                    report_error = "仅支持 jpg、jpeg、png、pdf 格式的检验报告文件。"

            report_compare_table = build_report_compare_table(report_results)
            report_summary = build_summary(report_compare_table)
            if has_any_result(ai_results):
                compare_table = build_compare_table(ai_results)
                summary = build_summary(compare_table)
        elif audit_type == "cross":
            if not cross_label_text:
                cross_label_text = first_filled_result(ai_results)
            if not cross_report_text:
                cross_report_text = first_filled_result(report_results)
            cross_check_table = cross_check_label_report(cross_label_text, cross_report_text)
            if has_any_result(ai_results):
                compare_table = build_compare_table(ai_results)
                summary = build_summary(compare_table)
            if has_any_result(report_results):
                report_compare_table = build_report_compare_table(report_results)
                report_summary = build_summary(report_compare_table)
        else:
            compare_table = build_compare_table(ai_results)
            summary = build_summary(compare_table)
            if has_any_result(report_results):
                report_compare_table = build_report_compare_table(report_results)
                report_summary = build_summary(report_compare_table)

    return render_template(
        "index.html",
        image_url=image_url,
        label_file_name=label_file_name,
        compare_table=compare_table,
        summary=summary,
        report_compare_table=report_compare_table,
        report_summary=report_summary,
        ai_results=ai_results,
        report_results=report_results,
        report_file_url=report_file_url,
        report_file_name=report_file_name,
        report_file_is_image=report_file_is_image,
        cross_label_text=cross_label_text,
        cross_report_text=cross_report_text,
        cross_check_table=cross_check_table,
        ai_platforms=AI_PLATFORMS,
        error=error,
        report_error=report_error,
    )


@app.route("/uploads/<filename>")
def static_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/uploads/reports/<filename>")
def report_upload(filename):
    return send_from_directory(app.config["REPORT_UPLOAD_FOLDER"], filename)


@app.route("/api/run_label_ai", methods=["POST"])
def run_label_ai():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    image_path = data.get("image_path")

    return jsonify({"results": call_all_ai_platforms(prompt, image_path)})


@app.route("/api/run_report_ai", methods=["POST"])
def run_report_ai():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    image_path = data.get("image_path")

    return jsonify({"results": call_all_ai_platforms(prompt, image_path)})


@app.route("/automation/open_deepseek", methods=["POST"])
def open_deepseek_automation():
    runner_path = BASE_DIR / "automation" / "deepseek_runner.py"
    if not runner_path.exists():
        return jsonify({"success": False, "error": "DeepSeek自动化脚本不存在"}), 500

    try:
        subprocess.Popen(
            [sys.executable, str(runner_path)],
            cwd=str(BASE_DIR),
        )
    except OSError as error:
        return jsonify({"success": False, "error": f"DeepSeek启动失败：{error}"}), 500

    return jsonify({
        "success": True,
        "message": "DeepSeek 已打开，请上传文件并粘贴提示词",
    })


if __name__ == "__main__":
    app.run(debug=True)
