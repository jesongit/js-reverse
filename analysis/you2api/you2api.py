#!/usr/bin/env python3
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlencode

import requests


class YouClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("YOU_BASE_URL", "https://you.com")
        self.model_name = os.getenv("YOU_MODEL_NAME", "gpt_5_1_instant")
        self.timeout = int(os.getenv("YOU_TIMEOUT", "120"))
        self.default_headers = self._load_json_env("YOU_HEADERS", {})
        self.default_cookies = self._load_json_env("YOU_COOKIES", {})
        self.default_payload = self._load_json_env("YOU_DEFAULT_PAYLOAD", {})
        self.chat_endpoint = os.getenv("YOU_CHAT_ENDPOINT", "")
        self.search_build_id = os.getenv("YOU_SEARCH_BUILD_ID", "1138057")
        self.search_locale = os.getenv("YOU_SEARCH_LOCALE", "en-US")
        self.search_path = os.getenv(
            "YOU_SEARCH_PATH",
            f"/_next/data/{self.search_build_id}/{self.search_locale}/search.json",
        )
        self.streaming_path = os.getenv("YOU_STREAMING_PATH", "/api/streamingSearch")
        self.saved_streaming_path = os.getenv("YOU_SAVED_STREAMING_PATH", "/api/streamingSavedChat")
        self.default_tbm = os.getenv("YOU_SEARCH_TBM", "youchat")
        self.default_chat_mode = os.getenv("YOU_CHAT_MODE", "custom")
        self.default_nonce = os.getenv("YOU_NONCE", "")
        self.default_cid = os.getenv("YOU_CID", "")
        self.default_page = os.getenv("YOU_PAGE", "1")
        self.default_count = os.getenv("YOU_COUNT", "10")
        self.default_safe_search = os.getenv("YOU_SAFE_SEARCH", "moderate")
        self.default_sources = os.getenv("YOU_SOURCES", "web")
        self.default_selected_ai_model = os.getenv("YOU_SELECTED_AI_MODEL", self.model_name)
        self.default_is_new_chat = os.getenv("YOU_IS_NEW_CHAT", "true")
        self.default_past_chat_length = os.getenv("YOU_PAST_CHAT_LENGTH", "0")
        self.default_query_trace_id = os.getenv("YOU_QUERY_TRACE_ID", "")
        self.default_trace_id = os.getenv("YOU_TRACE_ID", "")
        self.default_conversation_turn_id = os.getenv("YOU_CONVERSATION_TURN_ID", "")
        self.default_chat_id = os.getenv("YOU_CHAT_ID", "")
        self.default_cached_chat_id = os.getenv("YOU_CACHED_CHAT_ID", "")
        self.default_project_id = os.getenv("YOU_PROJECT_ID", "")
        self.default_omit_repeated_context = os.getenv("YOU_OMIT_REPEATED_CONTEXT", "true")
        self.default_nested_updates = os.getenv("YOU_USE_NESTED_YOUCHAT_UPDATES", "true")
        self.default_editable_workflow = os.getenv("YOU_ENABLE_EDITABLE_WORKFLOW", "true")
        self.default_agent_clarification = os.getenv("YOU_ENABLE_AGENT_CLARIFICATION_QUESTIONS", "true")
        self.default_upstream_mode = os.getenv("YOU_UPSTREAM_MODE", "search")
        self.session = requests.Session()

    @staticmethod
    def _load_json_env(name: str, default: dict[str, Any]) -> dict[str, Any]:
        raw = os.getenv(name)
        if not raw:
            return default
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{name} 必须是 JSON 对象")
        return value

    @staticmethod
    def _normalize_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "\n".join(part for part in parts if part)
        return ""

    def _build_messages(self, body: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        messages = body.get("messages") or []
        user_message = ""
        history: list[dict[str, str]] = []
        for item in messages:
            role = item.get("role", "user")
            content = self._normalize_content(item.get("content"))
            history.append({"role": role, "content": content})
            if role == "user":
                user_message = content
        return user_message, history

    def build_payload(self, body: dict[str, Any]) -> dict[str, Any]:
        user_message, history = self._build_messages(body)
        payload = dict(self.default_payload)
        payload.setdefault("query", user_message)
        payload.setdefault("messages", history)
        payload.setdefault("stream", bool(body.get("stream")))
        payload.setdefault("model", body.get("model") or self.model_name)
        return payload

    @staticmethod
    def _stringify_bool(value: bool) -> str:
        return "true" if value else "false"

    @staticmethod
    def _json_compact(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def _build_chat_history_pairs(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        pairs: list[dict[str, str]] = []
        current_question = ""
        for item in history:
            role = item.get("role")
            content = item.get("content", "")
            if role == "user":
                if current_question:
                    pairs.append({"question": current_question, "answer": ""})
                current_question = content
            elif role == "assistant" and current_question:
                pairs.append({"question": current_question, "answer": content})
                current_question = ""
        return pairs

    def _build_search_params(self, body: dict[str, Any]) -> dict[str, str]:
        payload = self.build_payload(body)
        query = payload.get("query", "")
        if not query:
            raise ValueError("缺少用户消息，无法构造 you.com 搜索请求")
        params = {
            "q": query,
            "tbm": os.getenv("YOU_SEARCH_TBM", self.default_tbm),
        }
        cid = body.get("you_cid") or self.default_cid
        if cid:
            params["cid"] = cid
        chat_mode = body.get("you_chat_mode") or self.default_chat_mode
        if chat_mode:
            params["chatMode"] = chat_mode
        nonce = body.get("you_nonce") or self.default_nonce
        if nonce:
            params["nonce"] = nonce
        for key, value in self.default_payload.items():
            if isinstance(value, (str, int, float, bool)):
                params.setdefault(key, str(value).lower() if isinstance(value, bool) else str(value))
        return params

    def _build_streaming_request(self, body: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, Any]]:
        payload = self.build_payload(body)
        query = payload.get("query", "")
        history = payload.get("messages") or []
        if not query:
            raise ValueError("缺少用户消息，无法构造 you.com 流式请求")
        chat_history = self._build_chat_history_pairs(history)
        is_new_chat = str(body.get("you_is_new_chat", self.default_is_new_chat)).lower()
        endpoint = self.saved_streaming_path if is_new_chat == "false" else self.streaming_path
        params = {
            "q": query,
            "page": str(body.get("you_page") or self.default_page),
            "count": str(body.get("you_count") or self.default_count),
            "safeSearch": str(body.get("you_safe_search") or self.default_safe_search),
            "chatId": str(body.get("you_chat_id") or self.default_chat_id),
            "conversationTurnId": str(body.get("you_conversation_turn_id") or self.default_conversation_turn_id),
            "cachedChatId": str(body.get("you_cached_chat_id") or self.default_cached_chat_id),
            "isNewChat": is_new_chat,
            "pastChatLength": str(body.get("you_past_chat_length") or len(chat_history) or self.default_past_chat_length),
            "selectedChatMode": str(body.get("you_chat_mode") or self.default_chat_mode),
            "selectedAiModel": str(body.get("you_selected_ai_model") or payload.get("model") or self.default_selected_ai_model),
            "sources": str(body.get("you_sources") or self.default_sources),
            "queryTraceId": str(body.get("you_query_trace_id") or self.default_query_trace_id),
            "traceId": str(body.get("you_trace_id") or self.default_trace_id),
            "project_id": str(body.get("you_project_id") or self.default_project_id),
            "omitRepeatedContext": str(body.get("you_omit_repeated_context") or self.default_omit_repeated_context),
            "enable_editable_workflow": str(body.get("you_enable_editable_workflow") or self.default_editable_workflow),
            "use_nested_youchat_updates": str(body.get("you_use_nested_youchat_updates") or self.default_nested_updates),
            "enable_agent_clarification_questions": str(body.get("you_enable_agent_clarification_questions") or self.default_agent_clarification),
        }
        cid = body.get("you_cid") or self.default_cid
        if cid:
            params["cid"] = cid
        nonce = body.get("you_nonce") or self.default_nonce
        if nonce:
            params["nonce"] = nonce
        chat_payload = chat_history[:-1] if chat_history and chat_history[-1].get("answer", "") == "" and chat_history[-1].get("question") == query else chat_history
        request_body: dict[str, Any] = {
            "query": query,
            "chat": self._json_compact(chat_payload),
        }
        submitted_workflow_steps = body.get("you_submitted_workflow_steps")
        if submitted_workflow_steps is not None:
            request_body["submittedWorkflowSteps"] = submitted_workflow_steps
        knowledge_base = body.get("you_knowledge_base")
        if knowledge_base is not None:
            request_body["knowledgeBase"] = knowledge_base
        return endpoint, {key: value for key, value in params.items() if value != ""}, request_body

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        headers = dict(self.default_headers)
        extra_headers = kwargs.pop("headers", None)
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)
        cookies = dict(self.default_cookies)
        extra_cookies = kwargs.pop("cookies", None)
        if isinstance(extra_cookies, dict):
            cookies.update(extra_cookies)
        response = self.session.request(
            method,
            self.base_url + path,
            headers=headers,
            cookies=cookies,
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def chat(self, body: dict[str, Any]) -> tuple[str, str]:
        if self.chat_endpoint:
            payload = self.build_payload(body)
            response = self._request("POST", self.chat_endpoint, json=payload)
            text = response.text
            return self._extract_text(text), text
        upstream_mode = str(body.get("you_upstream_mode") or self.default_upstream_mode).lower()
        if upstream_mode == "streaming":
            endpoint, params, request_body = self._build_streaming_request(body)
            headers = {"content-type": "application/json", "accept": "text/event-stream"}
            response = self._request("POST", endpoint, params=params, json=request_body, headers=headers)
            text = response.text
            return self._extract_streaming_text(text), text
        params = self._build_search_params(body)
        response = self._request("GET", self.search_path, params=params)
        text = response.text
        return self._extract_text(text), text

    def stream_chat(self, body: dict[str, Any]):
        answer, _ = self.chat(body)
        if not answer:
            return
        for chunk in self._split_text(answer):
            yield chunk

    @staticmethod
    def _split_text(text: str, chunk_size: int = 40):
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]

    @staticmethod
    def _extract_text(raw: str) -> str:
        stripped = raw.strip()
        if not stripped:
            return ""
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
        return YouClient._extract_from_data(data) or stripped

    @staticmethod
    def _extract_from_data(data: Any) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            for item in data:
                result = YouClient._extract_from_data(item)
                if result:
                    return result
            return ""
        if not isinstance(data, dict):
            return ""
        for key in (
            "answer",
            "youChatAnswer",
            "text",
            "content",
            "response",
            "description",
            "snippet",
            "markdown",
            "body",
        ):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        message = data.get("message")
        if isinstance(message, dict):
            result = YouClient._extract_from_data(message)
            if result:
                return result
        props = data.get("pageProps") or data.get("props")
        if isinstance(props, dict):
            for key in (
                "answer",
                "result",
                "results",
                "response",
                "serverResponse",
                "initialReduxState",
                "state",
            ):
                result = YouClient._extract_from_data(props.get(key))
                if result:
                    return result
        for value in data.values():
            result = YouClient._extract_from_data(value)
            if result:
                return result
        return ""

    @staticmethod
    def _extract_sse_text(line: str) -> str:
        value = line
        if value.startswith("data:"):
            value = value[5:].strip()
        if not value or value == "[DONE]":
            return ""
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return value
        return YouClient._extract_from_data(data)

    @staticmethod
    def _extract_streaming_text(raw: str) -> str:
        parts: list[str] = []
        for line in raw.splitlines():
            text = YouClient._extract_sse_text(line)
            if text:
                parts.append(text)
        return "".join(parts).strip()

    def get_model_id(self) -> str:
        return self.model_name

    def get_upstream_mode(self, body: dict[str, Any]) -> str:
        if self.chat_endpoint:
            return "custom_endpoint"
        upstream_mode = str(body.get("you_upstream_mode") or self.default_upstream_mode).lower()
        return "streaming_search" if upstream_mode == "streaming" else "search_json"

    def get_search_url(self, body: dict[str, Any]) -> str | None:
        if self.chat_endpoint or self.get_upstream_mode(body) != "search_json":
            return None
        return f"{self.base_url}{self.search_path}?{urlencode(self._build_search_params(body))}"

    def get_streaming_url(self, body: dict[str, Any]) -> str | None:
        if self.chat_endpoint or self.get_upstream_mode(body) != "streaming_search":
            return None
        endpoint, params, _ = self._build_streaming_request(body)
        return f"{self.base_url}{endpoint}?{urlencode(params)}"


class OpenAIHandler(BaseHTTPRequestHandler):
    client = YouClient()
    server_version = "you2api/0.2"

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._send_json(200, {
                "object": "list",
                "data": [
                    {
                        "id": self.client.get_model_id(),
                        "object": "model",
                        "created": 0,
                        "owned_by": "you.com",
                    }
                ],
            })
            return
        self._send_json(404, {"error": {"message": "Not found", "type": "invalid_request_error"}})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "Not found", "type": "invalid_request_error"}})
            return
        try:
            body = self._read_json_body()
            if body.get("stream"):
                self._handle_stream(body)
                return
            answer, raw = self.client.chat(body)
            self._send_json(200, self._build_chat_response(body, answer, raw))
        except requests.HTTPError as exc:
            message = exc.response.text if exc.response is not None else str(exc)
            status = exc.response.status_code if exc.response is not None else 502
            self._send_json(status, {"error": {"message": message, "type": "upstream_error"}})
        except Exception as exc:
            self._send_json(400, {"error": {"message": str(exc), "type": "invalid_request_error"}})

    def _handle_stream(self, body: dict[str, Any]) -> None:
        response_id = f"chatcmpl-{uuid.uuid4().hex}"
        model = body.get("model") or self.client.get_model_id()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        for chunk in self.client.stream_chat(body):
            if not chunk:
                continue
            data = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None,
                    }
                ],
            }
            self.wfile.write(f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.flush()
        done = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        self.wfile.write(f"data: {json.dumps(done, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _build_chat_response(self, body: dict[str, Any], answer: str, raw: str) -> dict[str, Any]:
        prompt_tokens = len(json.dumps(body, ensure_ascii=False))
        completion_tokens = len(answer)
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model") or self.client.get_model_id(),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "raw_upstream": raw,
            "upstream_hint": {
                "mode": self.client.get_upstream_mode(body),
                "search_url": self.client.get_search_url(body),
                "streaming_url": self.client.get_streaming_url(body),
            },
        }

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(raw or "{}")
        if not isinstance(data, dict):
            raise ValueError("请求体必须是 JSON 对象")
        return data

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), OpenAIHandler)
    print(f"you2api running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
