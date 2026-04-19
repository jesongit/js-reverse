import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple

from perplexity2api import DEFAULT_MODEL, PerplexityClient
from perplexity_metadata import PerplexityMetadataClient

HOST = os.getenv("PPLX_OPENAI_HOST", "127.0.0.1")
PORT = int(os.getenv("PPLX_OPENAI_PORT", "8012"))
API_KEY = os.getenv("PPLX_OPENAI_API_KEY", "")


def get_cookie() -> str:
    cookie = os.getenv("PPLX_COOKIE", "").strip()
    if not cookie:
        raise RuntimeError("缺少 PPLX_COOKIE 环境变量")
    return cookie


def build_client() -> PerplexityClient:
    model = os.getenv("PPLX_MODEL", DEFAULT_MODEL)
    return PerplexityClient(cookie=get_cookie(), model=model)


def build_metadata_client() -> PerplexityMetadataClient:
    return PerplexityMetadataClient(get_cookie())


def extract_prompt(messages: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            content = "\n".join(text_parts)
        parts.append(f"{role}: {content}".strip())
    return "\n".join(part for part in parts if part).strip()


def extract_responses_input(payload: Dict[str, Any]) -> str:
    value = payload.get("input", "")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        messages: List[Dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            role = item.get("role", "user")
            content = item.get("content", "")
            if isinstance(content, list):
                normalized: List[Dict[str, Any]] = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") in {"input_text", "text"}:
                        normalized.append({"type": "text", "text": str(block.get("text", ""))})
                messages.append({"role": role, "content": normalized})
            else:
                messages.append({"role": role, "content": str(content)})
        return extract_prompt(messages)
    return ""


def parse_final_text(raw_text: str) -> str:
    try:
        outer = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text
    if not isinstance(outer, list):
        return raw_text
    for item in reversed(outer):
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, dict):
            continue
        answer = content.get("answer")
        if not isinstance(answer, str):
            continue
        try:
            answer_json = json.loads(answer)
        except json.JSONDecodeError:
            return answer
        if isinstance(answer_json, dict) and isinstance(answer_json.get("answer"), str):
            return answer_json["answer"]
        return answer
    return raw_text


def build_chat_response(model: str, content: str, response_id: str) -> Dict[str, Any]:
    created = int(time.time())
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def build_responses_response(model: str, content: str, response_id: str) -> Dict[str, Any]:
    created = int(time.time())
    return {
        "id": response_id,
        "object": "response",
        "created_at": created,
        "status": "completed",
        "model": model,
        "output": [
            {
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": content,
                        "annotations": [],
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


def build_response_pair(path: str, payload: Dict[str, Any], result_text: str, requested_model: str, response_id: str) -> Tuple[bool, Dict[str, Any]]:
    if path == "/v1/responses":
        return bool(payload.get("stream")), build_responses_response(requested_model, result_text, response_id)
    return bool(payload.get("stream")), build_chat_response(requested_model, result_text, response_id)


def safe_metadata_call(func):
    try:
        return {"ok": True, "data": func()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class Handler(BaseHTTPRequestHandler):
    server_version = "PerplexityOpenAICompat/0.2"

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_headers(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

    def _write_sse(self, payload: Dict[str, Any]) -> None:
        chunk = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
        self.wfile.write(chunk)
        self.wfile.flush()

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _check_auth(self) -> bool:
        if not API_KEY:
            return True
        value = self.headers.get("Authorization", "")
        if value == f"Bearer {API_KEY}":
            return True
        self._send_json(401, {"error": {"message": "无效的 API Key", "type": "invalid_api_key"}})
        return False

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            if not self._check_auth():
                return
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {"id": "turbo", "object": "model", "owned_by": "perplexity"},
                        {"id": "sonar", "object": "model", "owned_by": "perplexity"},
                        {"id": "gpt4.1", "object": "model", "owned_by": "perplexity"},
                        {"id": "gpt4o", "object": "model", "owned_by": "perplexity"},
                    ],
                },
            )
            return
        if self.path == "/v1/perplexity/models":
            if not self._check_auth():
                return
            self._send_json(200, safe_metadata_call(lambda: build_metadata_client().get_models_config()))
            return
        if self.path == "/v1/perplexity/limits":
            if not self._check_auth():
                return
            client = build_metadata_client()
            self._send_json(
                200,
                {
                    "rate_limit_status": safe_metadata_call(client.get_rate_limit_status),
                    "free_queries": safe_metadata_call(client.get_free_queries),
                    "user_settings": safe_metadata_call(client.get_user_settings),
                },
            )
            return
        self._send_json(404, {"error": {"message": "Not found", "type": "invalid_request_error"}})

    def do_POST(self) -> None:
        if self.path not in {"/v1/chat/completions", "/v1/responses"}:
            self._send_json(404, {"error": {"message": "Not found", "type": "invalid_request_error"}})
            return
        if not self._check_auth():
            return
        try:
            payload = self._read_json()
            requested_model = str(payload.get("model") or DEFAULT_MODEL)
            if self.path == "/v1/responses":
                prompt = extract_responses_input(payload)
            else:
                messages = payload.get("messages") or []
                if not isinstance(messages, list) or not messages:
                    self._send_json(400, {"error": {"message": "messages 不能为空", "type": "invalid_request_error"}})
                    return
                prompt = extract_prompt(messages)
            if not prompt:
                self._send_json(400, {"error": {"message": "输入内容不能为空", "type": "invalid_request_error"}})
                return
            client = build_client()
            client.model = client.normalize_model(requested_model)
            result = client.ask(prompt)
            answer = parse_final_text(result.final_text)
            response_id = f"resp_{result.entry_uuid or uuid.uuid4().hex}" if self.path == "/v1/responses" else f"chatcmpl-{result.entry_uuid or uuid.uuid4().hex}"
            is_stream, response_payload = build_response_pair(self.path, payload, answer, requested_model, response_id)
            if is_stream:
                self._send_sse_headers()
                if self.path == "/v1/responses":
                    self._write_sse({"type": "response.created", "response": response_payload})
                    self._write_sse({"type": "response.output_text.delta", "delta": answer})
                    self._write_sse({"type": "response.completed", "response": response_payload})
                else:
                    self._write_sse(
                        {
                            "id": response_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": requested_model,
                            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                        }
                    )
                    self._write_sse(
                        {
                            "id": response_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": requested_model,
                            "choices": [{"index": 0, "delta": {"content": answer}, "finish_reason": None}],
                        }
                    )
                    self._write_sse(
                        {
                            "id": response_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": requested_model,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        }
                    )
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                return
            self._send_json(200, response_payload)
        except Exception as exc:
            self._send_json(500, {"error": {"message": str(exc), "type": "server_error"}})


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"listening on http://{HOST}:{PORT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
