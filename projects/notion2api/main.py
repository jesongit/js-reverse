"""Notion AI → OpenAI 兼容 API 代理服务。"""

import os
import sys
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from notion_client import MODEL_MAP, chat_complete, resolve_model, stream_chat

if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()


def get_config() -> dict:
    """从环境变量构建 Notion 认证配置。"""
    p_sync = os.getenv("NOTION_P_SYNC_SESSION", "{}")
    return {
        "token_v2": os.getenv("NOTION_TOKEN_V2", ""),
        "p_sync_session": p_sync if isinstance(p_sync, dict) else __import__("json").loads(p_sync),
        "space_id": os.getenv("NOTION_SPACE_ID", ""),
        "user_id": os.getenv("NOTION_USER_ID", ""),
        "space_view_id": os.getenv("NOTION_SPACE_VIEW_ID", ""),
        "csrf": os.getenv("NOTION_CSRF", ""),
        "device_id": os.getenv("NOTION_DEVICE_ID", ""),
        "browser_id": os.getenv("NOTION_BROWSER_ID", ""),
    }


API_KEY = os.getenv("API_KEY")
PORT = int(os.getenv("PORT", "3000"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print(f"Notion2API 服务已启动: http://localhost:{PORT}")
    print(f"API 地址: http://localhost:{PORT}/v1/chat/completions")
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """API Key 认证中间件。"""
    if not API_KEY:
        return await call_next(request)

    auth = request.headers.get("authorization", "")
    if auth == f"Bearer {API_KEY}":
        return await call_next(request)

    return JSONResponse(
        status_code=401,
        content={"error": {"message": "无效的 API Key", "type": "auth_error"}},
    )


def messages_to_user_message(messages: list[dict]) -> str:
    """将 OpenAI messages 数组转换为单条用户消息。"""
    if len(messages) == 1 and messages[0]["role"] == "user":
        return messages[0]["content"]

    parts = []
    for msg in messages:
        content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
        if msg["role"] == "system":
            parts.append(f"[System]: {content}")
        elif msg["role"] == "user":
            parts.append(f"[User]: {content}")
        elif msg["role"] == "assistant":
            parts.append(f"[Assistant]: {content}")
    return "\n\n".join(parts)


def generate_chat_id() -> str:
    return "chatcmpl-" + uuid.uuid4().hex[:24]


def get_model_owner(model_id: str) -> str:
    """根据模型名前缀判断归属方。"""
    if model_id.startswith("gpt"):
        return "openai"
    if model_id.startswith(("sonnet", "opus", "haiku")):
        return "anthropic"
    if model_id.startswith("gemini"):
        return "google"
    return "notion"


@app.get("/v1/models")
async def list_models():
    """获取模型列表。"""
    import time
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": mid, "object": "model", "created": created, "owned_by": get_model_owner(mid)}
            for mid in MODEL_MAP
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Chat Completions 接口，兼容 OpenAI 格式。"""
    try:
        body = await request.json()
    except UnicodeDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "请求体必须为 UTF-8 编码的 JSON", "type": "invalid_request_error"}},
        )
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    req_model = body.get("model", "notion-ai")

    if not messages:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "messages 不能为空", "type": "invalid_request_error"}},
        )

    config = get_config()
    user_message = messages_to_user_message(messages)
    notion_model = resolve_model(req_model)
    chat_id = generate_chat_id()

    import time
    created = int(time.time())

    if stream:
        return EventSourceResponse(
            _stream_generator(chat_id, created, config, req_model, user_message, notion_model),
        )

    # 非流式
    try:
        result = await chat_complete(config, user_message, notion_model)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"message": str(e), "type": "api_error"}},
        )

    resp: dict = {
        "id": chat_id,
        "object": "chat.completion",
        "created": created,
        "model": req_model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result["text"]},
            "finish_reason": "stop",
        }],
    }
    if result["usage"]:
        resp["usage"] = {
            "prompt_tokens": result["usage"].get("inputTokens", 0),
            "completion_tokens": result["usage"].get("outputTokens", 0),
            "total_tokens": result["usage"].get("inputTokens", 0) + result["usage"].get("outputTokens", 0),
        }
    return resp


async def _stream_generator(chat_id, created, config, req_model, user_message, notion_model):
    """SSE 事件生成器。"""
    import json

    # 首个事件：角色声明
    yield {
        "data": json.dumps({
            "id": chat_id, "object": "chat.completion.chunk", "created": created, "model": req_model,
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
        }),
    }

    try:
        total_usage = None
        async for chunk in stream_chat(config, user_message, notion_model):
            if chunk.get("text"):
                yield {
                    "data": json.dumps({
                        "id": chat_id, "object": "chat.completion.chunk", "created": created, "model": req_model,
                        "choices": [{"index": 0, "delta": {"content": chunk["text"]}, "finish_reason": None}],
                    }),
                }
            if chunk.get("done") and chunk.get("usage"):
                total_usage = chunk["usage"]

        # 结束事件
        end_data: dict = {
            "id": chat_id, "object": "chat.completion.chunk", "created": created, "model": req_model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        if total_usage:
            end_data["usage"] = {
                "prompt_tokens": total_usage.get("inputTokens", 0),
                "completion_tokens": total_usage.get("outputTokens", 0),
                "total_tokens": total_usage.get("inputTokens", 0) + total_usage.get("outputTokens", 0),
            }
        yield {"data": json.dumps(end_data)}
    except Exception as e:
        yield {
            "data": json.dumps({"error": {"message": str(e), "type": "api_error"}}),
        }

    yield {"data": "[DONE]"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
