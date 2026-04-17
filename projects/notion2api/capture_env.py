"""从浏览器抓取 Notion AI 请求并更新本地 .env。

用法：
    python capture_env.py

前置条件：
1. 已启动并连接 js-reverse MCP
2. 浏览器中已登录 Notion
3. 当前页面可访问 https://www.notion.so/ai
"""

import json
import os
import urllib.parse

from dotenv import dotenv_values
from mcp__js_reverse__list_breakpoints import list_breakpoints  # type: ignore
from mcp__js_reverse__break_on_xhr import break_on_xhr  # type: ignore
from mcp__js_reverse__navigate_page import navigate_page  # type: ignore
from mcp__js_reverse__evaluate_script import evaluate_script  # type: ignore
from mcp__js_reverse__get_paused_info import get_paused_info  # type: ignore
from mcp__js_reverse__pause_or_resume import pause_or_resume  # type: ignore
from mcp__js_reverse__list_network_requests import list_network_requests  # type: ignore

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def parse_cookie_header(cookie_header: str) -> dict[str, str]:
    """将 Cookie 头解析为字典。"""
    result = {}
    for item in cookie_header.split("; "):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key] = urllib.parse.unquote(value)
    return result


def write_env(values: dict[str, str]) -> None:
    """更新 .env 文件中的关键字段。"""
    current = dict(dotenv_values(ENV_PATH)) if os.path.exists(ENV_PATH) else {}
    current.update(values)
    lines = [
        "# Notion 认证信息（浏览器重新获取）",
        f"NOTION_TOKEN_V2={current.get('NOTION_TOKEN_V2', '')}",
        f"NOTION_P_SYNC_SESSION={current.get('NOTION_P_SYNC_SESSION', '')}",
        f"NOTION_SPACE_ID={current.get('NOTION_SPACE_ID', '')}",
        f"NOTION_USER_ID={current.get('NOTION_USER_ID', '')}",
        f"NOTION_SPACE_VIEW_ID={current.get('NOTION_SPACE_VIEW_ID', '')}",
        f"NOTION_CSRF={current.get('NOTION_CSRF', '')}",
        f"NOTION_DEVICE_ID={current.get('NOTION_DEVICE_ID', '')}",
        f"NOTION_BROWSER_ID={current.get('NOTION_BROWSER_ID', '')}",
        "",
        "# 服务配置",
        f"PORT={current.get('PORT', '3000')}",
        f"API_KEY={current.get('API_KEY', 'sk-notion2api')}",
        "",
    ]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    """触发一次 Notion AI 请求并提取 env。"""
    break_on_xhr(url="runInferenceTranscript")
    navigate_page(type="url", url="https://www.notion.so/ai", timeout=15000)

    evaluate_script(
        mainWorld=True,
        function="""() => {
          const editable = document.querySelector('[contenteditable="true"]');
          if (!editable) return {ok:false};
          const text = '你好，用一句话介绍自己';
          editable.focus();
          editable.textContent = text;
          editable.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
          const send = [...document.querySelectorAll('button, [role="button"]')].find(el => (el.getAttribute('aria-label') || '').includes('提交 AI 消息'));
          if (!send) return {ok:false};
          send.click();
          return {ok:true};
        }""",
    )

    get_paused_info(includeScopes=False)
    pause_or_resume()

    req = list_network_requests(pageSize=20, includePreservedRequests=True, urlFilter="runInferenceTranscript")
    header_text = req.get("text", "") if isinstance(req, dict) else str(req)
    if "cookie:" not in header_text:
        raise RuntimeError("未抓到 runInferenceTranscript 请求")

    cookie_line = next(line for line in header_text.splitlines() if line.startswith("- cookie:"))
    cookie_header = cookie_line.split(":", 1)[1]
    cookies = parse_cookie_header(cookie_header)

    body_line_index = header_text.find('### Request Body')
    body_json = {}
    if body_line_index != -1:
        body_text = header_text[body_line_index:].splitlines()[1]
        body_json = json.loads(body_text)

    values = {
        "NOTION_TOKEN_V2": cookies.get("token_v2", ""),
        "NOTION_P_SYNC_SESSION": cookies.get("p_sync_session", ""),
        "NOTION_SPACE_ID": body_json.get("spaceId", ""),
        "NOTION_USER_ID": cookies.get("notion_user_id", ""),
        "NOTION_SPACE_VIEW_ID": body_json.get("transcript", [{}, {"value": {}}])[1].get("value", {}).get("spaceViewId", ""),
        "NOTION_CSRF": cookies.get("csrf", ""),
        "NOTION_DEVICE_ID": cookies.get("device_id", ""),
        "NOTION_BROWSER_ID": cookies.get("notion_browser_id", ""),
    }
    write_env(values)
    print("已更新 .env")


if __name__ == "__main__":
    main()
