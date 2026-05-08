import os
import re
from datetime import datetime

from flask import Flask, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


FIELDS = [
    "产品名称",
    "执行标准",
    "生产许可证",
    "配料表",
    "保质期",
    "净含量",
    "生产企业",
    "标签风险提示",
]


AI_PLATFORMS = [
    {"key": "chatgpt", "name": "ChatGPT"},
    {"key": "deepseek", "name": "DeepSeek"},
    {"key": "tongyi", "name": "通义千问"},
    {"key": "doubao", "name": "豆包"},
    {"key": "wenxin", "name": "文心一言"},
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
    "保质期": [
        r"(?:保质期|保存期限|质保期)\s*[:：]\s*(.+)",
        r"保质期\s*(\d+\s*(?:天|个月|月|年))",
    ],
    "净含量": [
        r"(?:净含量|规格)\s*[:：]\s*(.+)",
        r"\b(\d+(?:\.\d+)?\s*(?:kg|g|克|千克|ml|mL|毫升|L|升))\b",
    ],
    "生产企业": [
        r"(?:生产企业|生产商|制造商|委托方|受委托方|生产厂家|生产单位)\s*[:：]\s*(.+)",
    ],
    "标签风险提示": [
        r"(?:标签风险提示|风险提示|问题|不符合|疑点|风险|建议)\s*[:：]\s*(.+)",
    ],
}

FIELD_ALIASES = {
    "产品名称": ["产品名称", "品名", "名称"],
    "执行标准": ["执行标准", "产品标准号", "标准号", "标准"],
    "生产许可证": ["生产许可证", "食品生产许可证编号", "许可证编号"],
    "配料表": ["配料表", "配料", "原料"],
    "保质期": ["保质期", "保存期限", "质保期"],
    "净含量": ["净含量", "规格"],
    "生产企业": ["生产企业", "生产商", "制造商", "委托方", "受委托方", "生产厂家", "生产单位"],
    "标签风险提示": ["标签风险提示", "风险提示", "问题", "不符合", "疑点", "风险", "建议"],
}

INVALID_RESULTS = {"未提取到", "未填写", "未看到", "未看见"}
KEY_FIELDS = {"执行标准", "生产许可证", "配料表", "标签风险提示"}
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
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def make_safe_filename(filename):
    name = secure_filename(filename)
    if not name:
        extension = filename.rsplit(".", 1)[1].lower()
        name = f"label.{extension}"
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


def all_field_aliases():
    aliases = []
    for field_aliases in FIELD_ALIASES.values():
        aliases.extend(field_aliases)
    return sorted(set(aliases), key=len, reverse=True)


def find_labeled_value(text, field):
    aliases = sorted(FIELD_ALIASES.get(field, []), key=len, reverse=True)
    if not aliases:
        return None

    alias_pattern = "|".join(re.escape(alias) for alias in aliases)
    label_match = re.search(rf"(?:{alias_pattern})\s*[:：]", text, re.IGNORECASE)
    if not label_match:
        return None

    start = label_match.end()
    next_alias_pattern = "|".join(re.escape(alias) for alias in all_field_aliases())
    next_label = re.search(rf"(?:{next_alias_pattern})\s*[:：]", text[start:], re.IGNORECASE)
    end = start + next_label.start() if next_label else len(text)

    if field == "标签风险提示":
        return text[start:end].strip(" ：:，,;；") or "未提取到"

    value = text[start:end]
    if field == "净含量":
        return extract_quantity_value(value)

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


def extract_field(text, field):
    if not text.strip():
        return "未填写"

    labeled_value = find_labeled_value(text, field)
    if labeled_value:
        if field == "标签风险提示":
            return format_risk_text(labeled_value)
        return labeled_value

    for pattern in FIELD_PATTERNS.get(field, []):
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = clean_value(match.group(1))
            if field == "标签风险提示":
                return format_risk_text(value)
            if field == "净含量":
                return extract_quantity_value(value)
            return value

    return "未提取到"


def is_valid_result(value):
    return value not in INVALID_RESULTS


def is_no_risk_statement(value):
    normalized = re.sub(r"\s+", "", value)
    return any(phrase in normalized for phrase in NO_RISK_PHRASES)


def normalize_for_compare(value, field=None):
    if not is_valid_result(value):
        return value

    if field == "标签风险提示" and is_no_risk_statement(value):
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


def has_risk_keyword(values):
    return any(
        keyword in value
        for value in values
        if not is_no_risk_statement(value)
        for keyword in RISK_KEYWORDS
    )


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
        if field == "标签风险提示" and has_risk_keyword(values.values()):
            diff_result = "存在风险提示，需重点复核"

        needs_key_review = field in KEY_FIELDS and diff_result != "一致"
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


@app.route("/", methods=["GET", "POST"])
def index():
    image_url = None
    compare_table = None
    summary = None
    error = None
    ai_results = {platform["key"]: "" for platform in AI_PLATFORMS}

    if request.method == "POST":
        file = request.files.get("label_image")

        if file and file.filename:
            if allowed_file(file.filename):
                filename = make_safe_filename(file.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
                image_url = url_for("static_upload", filename=filename)
            else:
                error = "仅支持 png、jpg、jpeg、webp 格式的图片。"

        for platform in AI_PLATFORMS:
            field_name = f"{platform['key']}_result"
            ai_results[platform["key"]] = request.form.get(field_name, "").strip()

        compare_table = build_compare_table(ai_results)
        summary = build_summary(compare_table)

    return render_template(
        "index.html",
        image_url=image_url,
        compare_table=compare_table,
        summary=summary,
        ai_results=ai_results,
        ai_platforms=AI_PLATFORMS,
        error=error,
    )


@app.route("/uploads/<filename>")
def static_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
