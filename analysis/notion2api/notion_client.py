"""Notion AI API 客户端，封装认证、请求构建和响应解析。"""

import json
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

import httpx


def _fix_mojibake(text: str) -> str:
    """修复 UTF-8 被按 Latin-1 解码后的乱码。"""
    if "�" not in text and "Ã" not in text:
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
        return repaired if repaired else text
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

NOTION_API_BASE = "https://www.notion.so/api/v3"

# OpenAI 模型名 → Notion 内部代号
MODEL_MAP: dict[str, str | None] = {
    "notion-ai": None,
    "gpt-5.2": "oatmeal-cookie",
    "gpt-5.4": "oatmeal-cake",
    "sonnet-4.6": "almond-croissant-high",
    "sonnet-4.5": "anthropic-sonnet-alt-no-thinking",
    "opus-4.7": "avocado-froyo-high",
    "haiku-4.5": "anthropic-haiku-4.5",
    "gemini-3.1-pro": "galette-medium-thinking",
    "gemini-2.5-pro": "gemini-pro",
    "gemini-2.5-flash": "gemini-flash",
}

# Gemini 系列模型需要 markdown-chat 线程类型
MARKDOWN_CHAT_MODELS = {"galette-medium-thinking", "gemini-pro", "gemini-flash"}


def resolve_model(openai_model: str | None) -> str | None:
    """将 OpenAI 格式模型名解析为 Notion 内部代号。"""
    return MODEL_MAP.get(openai_model) if openai_model else None


def _is_markdown_chat_model(notion_model: str | None) -> bool:
    """判断模型是否使用 markdown-chat 线程类型。"""
    if not notion_model:
        return False
    return notion_model in MARKDOWN_CHAT_MODELS


def build_headers(config: dict) -> dict[str, str]:
    """构建请求头，包含 Cookie 认证信息。"""
    cookie_parts = [
        f"token_v2={config['token_v2']}",
        f"p_sync_session={json.dumps(config['p_sync_session'], separators=(',', ':'))}",
        f"notion_user_id={config['user_id']}",
        f"csrf={config['csrf']}",
        f"device_id={config['device_id']}",
        f"notion_browser_id={config['browser_id']}",
    ]
    return {
        "accept": "application/x-ndjson",
        "content-type": "application/json; charset=utf-8",
        "cookie": "; ".join(cookie_parts),
        "notion-audit-log-platform": "web",
        "notion-client-version": "23.13.20260417.0002",
        "x-notion-active-user-header": config["user_id"],
        "x-notion-space-id": config["space_id"],
        "origin": "https://www.notion.so",
        "referer": "https://www.notion.so/ai",
    }


def build_request_body(config: dict, user_message: str, notion_model: str | None) -> dict[str, Any]:
    """构建 Notion AI API 请求体。"""
    has_model = notion_model is not None

    ai_config: dict[str, Any] = {
        "type": "workflow",
        "enableCreateAndRunThread": True,
        "useWebSearch": False,
        "isHipaa": False,
        "yoloMode": False,
        "useReadOnlyMode": False,
        "writerMode": False,
        "modelFromUser": has_model,
        "isCustomAgent": False,
        "isCustomAgentBuilder": False,
        "isAgentResearchRequest": False,
        "isMobile": False,
        "searchScopes": [{"type": "everything"}],
    }
    if has_model:
        ai_config["model"] = notion_model

    thread_type = "markdown-chat" if _is_markdown_chat_model(notion_model) else "workflow"

    return {
        "traceId": str(uuid.uuid4()),
        "spaceId": config["space_id"],
        "transcript": [
            {"id": str(uuid.uuid4()), "type": "config", "value": ai_config},
            {
                "id": str(uuid.uuid4()),
                "type": "context",
                "value": {
                    "timezone": "Asia/Shanghai",
                    "userName": "User",
                    "userId": config["user_id"],
                    "userEmail": "",
                    "spaceName": "Workspace",
                    "spaceId": config["space_id"],
                    "spaceViewId": config["space_view_id"],
                    "currentDatetime": datetime.now(timezone.utc).isoformat(),
                    "surface": "ask_ai",
                },
            },
            {
                "id": str(uuid.uuid4()),
                "type": "user",
                "value": [[user_message]],
                "userId": config["user_id"],
                "createdAt": datetime.now(timezone.utc).isoformat(),
            },
        ],
        "threadId": str(uuid.uuid4()),
        "threadParentPointer": {
            "table": "space",
            "id": config["space_id"],
            "spaceId": config["space_id"],
        },
        "createThread": True,
        "debugOverrides": {
            "emitAgentSearchExtractedResults": True,
            "cachedInferences": {},
            "annotationInferences": {},
            "emitInferences": False,
        },
        "generateTitle": False,
        "saveAllThreadOperations": True,
        "setUnreadState": True,
        "createdSource": "ai_module",
        "threadType": thread_type,
        "isPartialTranscript": False,
        "asPatchResponse": True,
        "isUserInAnySalesAssistedSpace": False,
        "isSpaceSalesAssisted": False,
    }


def clean_content(text: str) -> str:
    """清除 Notion 内部格式标签和思考过程标签。"""
    cleaned = text
    # Notion 语言标注标签
    cleaned = re.sub(r'<lang\s+primary="[^"]*"\s*/?>', '', cleaned)
    cleaned = cleaned.replace('</lang>', '')
    # XML 思考过程标签
    cleaned = re.sub(r'<thinking>[\s\S]*?</thinking>', '', cleaned)
    cleaned = re.sub(r'<thought>[\s\S]*?</thought>', '', cleaned)
    cleaned = re.sub(r'<think[\s\S]*?</think\s*>', '', cleaned)

    # Gemini 思考文本清理：连续 **英文标题**\n\n... 块后跟实际回答
    think_pattern = re.compile(r'\*\*([A-Z][^*]+ing[^*]*)\*\*\n\n([\s\S]*?)\n\n')
    last_end = 0
    for m in think_pattern.finditer(cleaned):
        if re.match(r"^[A-Za-z\s,.\-!?']+$", m.group(1)):
            last_end = m.end()
        else:
            break
    if 0 < last_end < len(cleaned):
        cleaned = cleaned[last_end:]

    return _fix_mojibake(cleaned.strip())


def _extract_from_record_map(record_map: dict) -> dict | None:
    """从 record-map 中提取最终文本和 usage。"""
    thread_message = record_map.get("thread_message")
    if not thread_message:
        return None
    for msg in thread_message.values():
        step = msg.get("value", {}).get("value", {}).get("step", {})
        if step.get("type") == "agent-inference":
            text = clean_content(
                "".join(v.get("content", "") for v in step.get("value", []))
            )
            usage = None
            if step.get("inputTokens") is not None:
                usage = {"inputTokens": step["inputTokens"], "outputTokens": step["outputTokens"]}
            return {"text": text, "usage": usage, "model": step.get("model")}
    return None


def parse_response(ndjson_text: str) -> dict:
    """解析 NDJSON 响应，提取最终结果。"""
    clean_text = ""
    usage = None
    model = "notion-ai"

    for line in ndjson_text.splitlines():
        line = line.strip()
        if not line:
            continue
        result = parse_stream_line(line)
        if not result:
            continue
        if result["text"] is not None:
            clean_text = result["text"]
        if result["usage"]:
            usage = result["usage"]
        if result["model"]:
            model = result["model"]

    return {"text": clean_content(clean_text), "usage": usage, "model": model}


def parse_stream_line(line: str) -> dict | None:
    """解析单行 NDJSON 事件。"""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None

    text = None
    usage = None
    model = None

    if payload.get("type") == "markdown-chat" and payload.get("data"):
        data = payload["data"]
        if isinstance(data, str):
            data = json.loads(data)
        if data.get("markdown") is not None:
            text = data["markdown"]
            if data.get("inputTokens") is not None:
                usage = {"inputTokens": data["inputTokens"], "outputTokens": data["outputTokens"]}
                model = data.get("model")

    if payload.get("type") == "record-map":
        result = _extract_from_record_map(payload.get("recordMap", {}))
        if result:
            text = result["text"]
            usage = result["usage"]
            model = result["model"]

    if text is None and not usage and not model:
        return None
    return {"text": text, "usage": usage, "model": model}


async def call_notion_api(config: dict, user_message: str, notion_model: str | None) -> httpx.Response:
    """调用 Notion AI API。"""
    body = build_request_body(config, user_message, notion_model)
    headers = build_headers(config)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{NOTION_API_BASE}/runInferenceTranscript",
            headers=headers,
            json=body,
        )
    resp.raise_for_status()
    return resp


async def iter_notion_stream(
    config: dict,
    user_message: str,
    notion_model: str | None,
) -> AsyncGenerator[dict, None]:
    """流式读取 Notion NDJSON 响应。"""
    body = build_request_body(config, user_message, notion_model)
    headers = build_headers(config)
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{NOTION_API_BASE}/runInferenceTranscript",
            headers=headers,
            json=body,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                result = parse_stream_line(line)
                if result:
                    yield result


async def stream_chat(config: dict, user_message: str, notion_model: str | None):
    """真实流式调用。"""
    emitted_text = ""
    final_usage = None
    final_model = "notion-ai"

    async for chunk in iter_notion_stream(config, user_message, notion_model):
        if chunk["usage"]:
            final_usage = chunk["usage"]
        if chunk["model"]:
            final_model = chunk["model"]
        if chunk["text"] is None:
            continue

        current_text = clean_content(chunk["text"])
        if not current_text.startswith(emitted_text):
            if current_text:
                emitted_text = current_text
                yield {"text": current_text, "done": False}
            continue

        delta = current_text[len(emitted_text):]
        emitted_text = current_text
        if delta:
            yield {"text": delta, "done": False}

    yield {"text": "", "done": True, "usage": final_usage, "model": final_model}


async def chat_complete(config: dict, user_message: str, notion_model: str | None) -> dict:
    """非流式调用。"""
    resp = await call_notion_api(config, user_message, notion_model)
    return parse_response(resp.text)
