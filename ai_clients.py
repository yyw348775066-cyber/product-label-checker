import os

import requests


DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
AI_SYSTEM_PROMPT = "你是食品标签和检验报告审核助手"

AI_PLATFORM_CONFIG = {
    "chatgpt": {
        "name": "ChatGPT",
        "env_keys": ["OPENAI_API_KEY"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_keys": ["DEEPSEEK_API_KEY"],
    },
    "tongyi": {
        "name": "通义千问",
        "env_keys": ["DASHSCOPE_API_KEY"],
    },
    "doubao": {
        "name": "豆包",
        "env_keys": ["DOUBAO_API_KEY"],
    },
    "wenxin": {
        "name": "文心一言",
        "env_keys": ["QIANFAN_API_KEY", "QIANFAN_SECRET_KEY"],
    },
}


def build_ai_result(platform_key, success=False, content="", error=""):
    config = AI_PLATFORM_CONFIG.get(platform_key, {})
    return {
        "platform": config.get("name", platform_key),
        "success": success,
        "content": content,
        "error": error,
    }


def missing_env_keys(platform_key):
    config = AI_PLATFORM_CONFIG.get(platform_key)
    if not config:
        return []

    return [env_key for env_key in config["env_keys"] if not os.getenv(env_key)]


def ensure_platform_ready(platform_key):
    if platform_key not in AI_PLATFORM_CONFIG:
        return build_ai_result(platform_key, error="未知AI平台")

    if missing_env_keys(platform_key):
        return build_ai_result(platform_key, error="未配置对应API Key")

    return None


def call_openai(prompt, image_path=None):
    ready_result = ensure_platform_ready("chatgpt")
    if ready_result:
        return ready_result

    return build_ai_result("chatgpt", error="OpenAI API调用尚未启用")


def call_deepseek(prompt, image_path=None):
    ready_result = ensure_platform_ready("deepseek")
    if ready_result:
        return ready_result

    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
    except requests.RequestException as error:
        return build_ai_result("deepseek", error=f"DeepSeek网络请求失败：{error}")

    if response.status_code != 200:
        return build_ai_result(
            "deepseek",
            error=f"DeepSeek API返回非200：{response.status_code} {response.text}",
        )

    try:
        data = response.json()
    except ValueError as error:
        return build_ai_result("deepseek", error=f"DeepSeek响应JSON解析失败：{error}")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return build_ai_result("deepseek", error="DeepSeek返回内容为空")

    content = str(content).strip()
    if not content:
        return build_ai_result("deepseek", error="DeepSeek返回内容为空")

    return build_ai_result("deepseek", success=True, content=content)


def call_qwen(prompt, image_path=None):
    ready_result = ensure_platform_ready("tongyi")
    if ready_result:
        return ready_result

    return build_ai_result("tongyi", error="通义千问 API调用尚未启用")


def call_doubao(prompt, image_path=None):
    ready_result = ensure_platform_ready("doubao")
    if ready_result:
        return ready_result

    return build_ai_result("doubao", error="豆包 API调用尚未启用")


def call_qianfan(prompt, image_path=None):
    ready_result = ensure_platform_ready("wenxin")
    if ready_result:
        return ready_result

    return build_ai_result("wenxin", error="文心一言 API调用尚未启用")


AI_PLATFORM_CALLERS = {
    "chatgpt": call_openai,
    "deepseek": call_deepseek,
    "tongyi": call_qwen,
    "doubao": call_doubao,
    "wenxin": call_qianfan,
}


def call_ai_platform(platform, prompt, image_path=None):
    caller = AI_PLATFORM_CALLERS.get(platform)
    if not caller:
        return build_ai_result(platform, error="未知AI平台")

    try:
        return caller(prompt, image_path)
    except Exception as error:
        return build_ai_result(platform, error=str(error) or "API调用失败")


def call_all_ai_platforms(prompt, image_path=None):
    return {
        platform_key: call_ai_platform(platform_key, prompt, image_path)
        for platform_key in AI_PLATFORM_CONFIG
    }
