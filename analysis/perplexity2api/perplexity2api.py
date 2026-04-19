import argparse
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional

import requests

BASE_URL = "https://www.perplexity.ai"
API_VERSION = "2.18"
DEFAULT_MODEL = "turbo"
DEFAULT_SOURCE = "default"
DEFAULT_HEADERS = {
    "accept": "text/event-stream",
    "content-type": "application/json",
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
}
SUPPORTED_BLOCK_USE_CASES = [
    "answer_modes",
    "media_items",
    "knowledge_cards",
    "inline_entity_cards",
    "place_widgets",
    "finance_widgets",
    "prediction_market_widgets",
    "sports_widgets",
    "flight_status_widgets",
    "news_widgets",
    "shopping_widgets",
    "jobs_widgets",
    "search_result_widgets",
    "inline_images",
    "inline_assets",
    "placeholder_cards",
    "diff_blocks",
    "inline_knowledge_cards",
    "entity_group_v2",
    "refinement_filters",
    "canvas_mode",
    "maps_preview",
    "answer_tabs",
    "price_comparison_widgets",
    "preserve_latex",
    "generic_onboarding_widgets",
    "in_context_suggestions",
    "pending_followups",
    "inline_claims",
    "unified_assets",
    "workflow_steps",
    "background_agents",
]
MODEL_ALIASES = {
    "auto": "turbo",
    "turbo": "turbo",
    "sonar": "sonar",
    "gpt-4.1": "gpt4.1",
    "gpt-4o": "gpt4o",
    "claude-3.7-sonnet": "claude2",
    "claude-sonnet-4": "sonar-reasoning-pro",
    "r1-1776": "r1_1776",
    "o3-mini": "o3-mini",
    "grok-2": "grok-2",
    "gemini-2.5-pro": "gemini2.5pro",
}


@dataclass
class AskResult:
    thread_slug: Optional[str]
    thread_url: Optional[str]
    entry_uuid: Optional[str]
    frontend_uuid: str
    frontend_context_uuid: str
    final_text: str
    events: List[Dict[str, Any]]
    chunks: List[str]


class PerplexityClient:
    def __init__(
        self,
        cookie: str,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        source: str = DEFAULT_SOURCE,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session.headers["cookie"] = cookie.strip()
        self.timeout = timeout
        self.source = source
        self.model = self.normalize_model(model)
        self.rum_session_id = str(uuid.uuid4())
        self.visitor_id = self._get_cookie_value(cookie, "pplx.visitor-id")
        self.session_id = self._get_cookie_value(cookie, "pplx.session-id")

    @staticmethod
    def _get_cookie_value(cookie: str, name: str) -> Optional[str]:
        prefix = f"{name}="
        for part in cookie.split(";"):
            item = part.strip()
            if item.startswith(prefix):
                return item[len(prefix):]
        return None

    @staticmethod
    def normalize_model(model: str) -> str:
        lowered = model.strip().lower()
        return MODEL_ALIASES.get(lowered, model)

    def _build_params(
        self,
        prompt: str,
        *,
        frontend_uuid: Optional[str] = None,
        frontend_context_uuid: Optional[str] = None,
        thread_frontend_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "attachments": [],
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "search_focus": "internet",
            "sources": ["web"],
            "frontend_uuid": frontend_uuid or str(uuid.uuid4()),
            "frontend_context_uuid": frontend_context_uuid or str(uuid.uuid4()),
            "mode": "concise",
            "model_preference": self.model,
            "prompt_source": "home",
            "query_source": self.source,
            "is_incognito": False,
            "use_schematized_api": True,
            "send_back_text_in_streaming_api": False,
            "supported_block_use_cases": SUPPORTED_BLOCK_USE_CASES,
            "read_write_token": thread_frontend_uuid,
            "version": API_VERSION,
            "source": self.source,
            "query_str": prompt,
        }

    def _iter_sse(self, response: requests.Response) -> Iterator[Dict[str, Any]]:
        event_name = "message"
        data_lines: List[str] = []
        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip("\r")
            if not line:
                if data_lines:
                    data = "\n".join(data_lines)
                    yield {"event": event_name, "data": data}
                    event_name = "message"
                    data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_name = line[6:].strip() or "message"
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            yield {"event": event_name, "data": "\n".join(data_lines)}

    def ask(self, prompt: str) -> AskResult:
        params = self._build_params(prompt)
        frontend_uuid = params["frontend_uuid"]
        frontend_context_uuid = params["frontend_context_uuid"]
        body = {k: v for k, v in params.items() if v is not None and k not in {"version", "source", "query_str"}}
        body["query_str"] = prompt.strip()
        query = {
            "version": API_VERSION,
            "source": self.source,
            "rum_session_id": self.rum_session_id,
        }
        response = self.session.post(
            f"{BASE_URL}/rest/sse/perplexity_ask",
            params=query,
            json=body,
            stream=True,
            timeout=self.timeout,
        )
        response.raise_for_status()
        events: List[Dict[str, Any]] = []
        chunks: List[str] = []
        final_text = ""
        thread_slug: Optional[str] = None
        entry_uuid: Optional[str] = None
        for event in self._iter_sse(response):
            parsed: Any
            try:
                parsed = json.loads(event["data"])
            except json.JSONDecodeError:
                parsed = event["data"]
            events.append({"event": event["event"], "data": parsed})
            if isinstance(parsed, dict):
                if parsed.get("text") and isinstance(parsed["text"], str):
                    final_text = parsed["text"]
                if parsed.get("backend_uuid") and parsed["backend_uuid"] not in {"DEFAULT_SEARCH_PLACEHOLDER", "CLIENT_SEARCH_PLACEHOLDER"}:
                    entry_uuid = parsed["backend_uuid"]
                if parsed.get("thread_url_slug"):
                    thread_slug = parsed["thread_url_slug"]
                for block in parsed.get("blocks") or []:
                    markdown = (((block or {}).get("markdown") or {}).get("content"))
                    if isinstance(markdown, str):
                        chunks.append(markdown)
            if event["event"] in {"done", "completed"}:
                break
        if not final_text and chunks:
            final_text = chunks[-1]
        thread_url = f"{BASE_URL}/search/{thread_slug}" if thread_slug else None
        return AskResult(
            thread_slug=thread_slug,
            thread_url=thread_url,
            entry_uuid=entry_uuid,
            frontend_uuid=frontend_uuid,
            frontend_context_uuid=frontend_context_uuid,
            final_text=final_text,
            events=events,
            chunks=chunks,
        )

    def get_thread(self, thread_slug: str) -> Dict[str, Any]:
        params: List[tuple[str, Any]] = [
            ("with_parent_info", "true"),
            ("with_schematized_response", "true"),
            ("version", API_VERSION),
            ("source", self.source),
            ("limit", 10),
            ("offset", 0),
            ("from_first", "true"),
        ]
        for item in SUPPORTED_BLOCK_USE_CASES:
            params.append(("supported_block_use_cases", item))
        response = self.session.get(
            f"{BASE_URL}/rest/thread/{thread_slug}",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


def load_cookie(args: argparse.Namespace) -> str:
    if args.cookie:
        return args.cookie
    env_cookie = os.getenv("PPLX_COOKIE", "").strip()
    if env_cookie:
        return env_cookie
    raise SystemExit("缺少 Cookie，请通过 --cookie 或环境变量 PPLX_COOKIE 提供")


def main() -> int:
    parser = argparse.ArgumentParser(description="Perplexity 网页会话转 OpenAI 风格分析辅助脚本")
    parser.add_argument("prompt", help="要发送的问题")
    parser.add_argument("--cookie", help="浏览器 Cookie 字符串")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型别名或原始 model_preference")
    parser.add_argument("--thread-slug", help="只拉取已有线程详情，不发起新问题")
    parser.add_argument("--dump-events", help="把 SSE 事件保存到 JSON 文件")
    parser.add_argument("--dump-thread", help="把线程详情保存到 JSON 文件")
    args = parser.parse_args()

    cookie = load_cookie(args)
    client = PerplexityClient(cookie=cookie, model=args.model)

    if args.thread_slug:
        thread = client.get_thread(args.thread_slug)
        print(json.dumps(thread, ensure_ascii=False, indent=2))
        if args.dump_thread:
            with open(args.dump_thread, "w", encoding="utf-8") as f:
                json.dump(thread, f, ensure_ascii=False, indent=2)
        return 0

    result = client.ask(args.prompt)
    output = {
        "thread_slug": result.thread_slug,
        "thread_url": result.thread_url,
        "entry_uuid": result.entry_uuid,
        "frontend_uuid": result.frontend_uuid,
        "frontend_context_uuid": result.frontend_context_uuid,
        "final_text": result.final_text,
        "chunk_count": len(result.chunks),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if args.dump_events:
        with open(args.dump_events, "w", encoding="utf-8") as f:
            json.dump(result.events, f, ensure_ascii=False, indent=2)

    if result.thread_slug and args.dump_thread:
        thread = client.get_thread(result.thread_slug)
        with open(args.dump_thread, "w", encoding="utf-8") as f:
            json.dump(thread, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
