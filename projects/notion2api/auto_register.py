"""
Notion 邮箱自动注册 + env 提取脚本。

依赖条件：
  1. js-reverse MCP 已连接并打开浏览器
  2. utils/qq_mail/qq_mail_idle.py 可用，IMAP 配置有效
  3. 已安装 imaplib2、python-dotenv

用法：
  python auto_register.py [--env-only]
    --env-only   跳过注册，仅从当前已登录浏览器页面重新提取 env

注册流程：
  1. 生成邮箱 posase{timestamp}@pid.im
  2. 打开注册页，输入邮箱，触发 OTP 发送
  3. 通过 QQ IMAP 拉取最新 Notion 验证码邮件
  4. 输入验证码完成登录
  5. 档案页：填名字（邮箱前缀），取消营销勾选
  6. 跳过邀请工作空间，创建新工作空间
  7. 用途页：选择"用于私人生活"
  8. 跳过桌面应用引导
  9. 进入主页后提取 Cookie + localStorage + 接口数据，写入 .env
"""

import sys
import io
import os
import re
import time
import urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 工具路径 ──────────────────────────────────────────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "utils", "qq_mail"))

# QQ 邮箱配置（直接复用 qq_mail_idle.py 中的常量）
from qq_mail_idle import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, fetch_latest_mail_to

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
SIGNUP_URL = "https://www.notion.so/signup?from=marketing&pathname=%2F"
OTP_WAIT_SECS = 90
PAGE_SETTLE_SECS = 3


# ── MCP 工具导入 ─────────────────────────────────────────
# 这些工具仅在 Claude Code MCP 上下文中可用，普通 Python 环境无法直接调用。
# 本脚本的正确执行方式：由 Claude Agent 通过 mcp__js-reverse 工具集调度。
try:
    from mcp__js_reverse__navigate_page import navigate_page
    from mcp__js_reverse__new_page import new_page
    from mcp__js_reverse__evaluate_script import evaluate_script
    from mcp__js_reverse__take_screenshot import take_screenshot
    from mcp__js_reverse__list_network_requests import list_network_requests
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def fetch_notion_otp(to_addr: str, sent_after: float, timeout: int = OTP_WAIT_SECS) -> str | None:
    """
    等待并提取发给 to_addr 的 Notion 验证码邮件中的 6 位 OTP。

    通过 sent_after 时间戳过滤，只接受 OTP 触发操作之后到达的邮件，
    避免历史旧验证码被误命中。

    参数：
        to_addr     收件邮箱地址
        sent_after  Unix 时间戳（秒），在此之前到达的邮件忽略
        timeout     最长等待秒数

    返回：
        6 位验证码字符串，或 None（超时未收到）
    """
    print(f"[IMAP] 等待发给 {to_addr} 的 Notion OTP（sent_after={sent_after:.0f}，最多 {timeout}s）...", flush=True)
    mail = fetch_latest_mail_to(
        to_addr=to_addr,
        sent_after=sent_after,
        sender_filter="notion",
        timeout=timeout,
        poll_interval=3,
    )
    if not mail:
        return None

    m = re.search(r"\b(\d{6})\b", mail["body"])
    if m:
        print(f"[IMAP] 主题: {mail['subject']} | 日期: {mail['date']} → 验证码: {m.group(1)}", flush=True)
        return m.group(1)
    return None


# ── 浏览器操作辅助 ────────────────────────────────────────

def _js_set_input(selector: str, value: str) -> str:
    """生成向输入框注入文本的 JS 代码（原型 setter + input/change 事件）。"""
    escaped = value.replace("'", "\\'")
    return f"""() => {{
  const input = document.querySelector('{selector}');
  if (!input) return {{ok: false, reason: 'no input: {selector}'}};
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, '{escaped}');
  input.dispatchEvent(new InputEvent('input', {{bubbles: true, data: '{escaped}', inputType: 'insertText'}}));
  input.dispatchEvent(new Event('change', {{bubbles: true}}));
  return {{ok: true, value: input.value}};
}}"""


def _js_click_button(text: str) -> str:
    """生成精确点击指定文本按钮的 JS 代码。"""
    escaped = text.replace("'", "\\'")
    return f"""() => {{
  const btn = Array.from(document.querySelectorAll('[role="button"], button'))
    .find(el => (el.innerText || '').trim() === '{escaped}');
  if (!btn) return {{ok: false, found: false}};
  btn.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true, view: window}}));
  return {{ok: true}};
}}"""


def _js_click_button_contains(text: str) -> str:
    """生成点击包含指定文本按钮的 JS 代码。"""
    escaped = text.replace("'", "\\'")
    return f"""() => {{
  const btn = Array.from(document.querySelectorAll('[role="button"], button'))
    .find(el => (el.innerText || '').trim().includes('{escaped}'));
  if (!btn) return {{ok: false, found: false}};
  btn.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true, view: window}}));
  return {{ok: true, clicked: (btn.innerText || '').trim().slice(0, 60)}};
}}"""


def _js_uncheck_marketing() -> str:
    """生成取消营销勾选框的 JS 代码。"""
    return """() => {
  const checkbox = document.querySelector('input[type="checkbox"]');
  if (!checkbox) return {found: false};
  const wasChecked = checkbox.checked;
  if (checkbox.checked) {
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event('input', {bubbles: true}));
    checkbox.dispatchEvent(new Event('change', {bubbles: true}));
  }
  return {found: true, wasChecked, nowChecked: checkbox.checked};
}"""


def _js_get_page_state() -> str:
    """生成读取当前页面 URL 和正文文本的 JS 代码。"""
    return """() => ({
  url: location.href,
  body: document.body.innerText.slice(0, 500)
})"""


# ── env 写入 ─────────────────────────────────────────────

def _parse_cookie_str(cookie_str: str) -> dict[str, str]:
    """解析 document.cookie 格式的 Cookie 字符串。"""
    result = {}
    for pair in cookie_str.split("; "):
        idx = pair.find("=")
        if idx > 0:
            result[pair[:idx]] = urllib.parse.unquote(pair[idx + 1:])
    return result


def _write_env(values: dict[str, str]) -> None:
    """更新 .env 文件中的关键字段。"""
    try:
        from dotenv import dotenv_values
        current = dict(dotenv_values(ENV_PATH)) if os.path.exists(ENV_PATH) else {}
    except ImportError:
        current = {}
    current.update(values)

    lines = [
        "# Notion 认证信息（自动注册获取）",
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
    print(f"[env] 已写入 {ENV_PATH}", flush=True)


# ── env 提取 ─────────────────────────────────────────────

def extract_env_from_browser() -> dict[str, str]:
    """
    从当前浏览器页面提取 Notion env 参数。
    需要页面已登录，且网络请求历史中包含 getSpacesInitial。

    返回：包含所有 env 字段的字典
    """
    # 从页面 Cookie 提取
    js_cookies = """() => {
      const cookies = {};
      document.cookie.split('; ').forEach(pair => {
        const idx = pair.indexOf('=');
        if (idx > 0) cookies[pair.slice(0, idx)] = pair.slice(idx + 1);
      });
      return cookies;
    }"""
    cookie_result = evaluate_script(mainWorld=True, function=js_cookies)
    raw_cookies = cookie_result if isinstance(cookie_result, dict) else {}

    def _uc(v):
        return urllib.parse.unquote(v) if v else ""

    # 从 localStorage 提取 spaceViewId
    js_ls = """() => {
      const sv = localStorage.getItem('LRU:KeyValueStore2:lastVisitedRouteSpaceViewId');
      const si = localStorage.getItem('LRU:KeyValueStore2:lastVisitedRouteSpaceId');
      if (sv) {
        try { return {spaceViewId: JSON.parse(sv).value, spaceId: si ? JSON.parse(si).value : null}; } catch(e) {}
      }
      // 备用：从 sidebar state 读取
      for (const k of Object.keys(localStorage)) {
        if (k.includes('notion-sidebar-sidebar-state')) {
          try {
            const v = JSON.parse(localStorage.getItem(k));
            const sv2 = v.value && v.value.spaceViewId;
            const si2 = v.value && v.value.spaceId;
            if (sv2) return {spaceViewId: sv2, spaceId: si2};
          } catch(e) {}
        }
      }
      return {spaceViewId: null, spaceId: null};
    }"""
    ls_result = evaluate_script(mainWorld=True, function=js_ls)
    ls_data = ls_result if isinstance(ls_result, dict) else {}

    # 从网络请求提取 spaceId（备用）
    space_id = (
        ls_data.get("spaceId")
        or _uc(raw_cookies.get("x-notion-space-id", ""))
    )

    # 从 getSpacesInitial 请求头读取 x-notion-space-id
    try:
        req_data = list_network_requests(
            urlFilter="getSpacesInitial", pageSize=3, includePreservedRequests=True
        )
        req_text = req_data.get("text", "") if isinstance(req_data, dict) else str(req_data)
        for line in req_text.splitlines():
            if "x-notion-space-id:" in line:
                space_id = space_id or line.split(":", 1)[1].strip()
    except Exception:
        pass

    token_v2 = _uc(raw_cookies.get("token_v2", ""))
    p_sync = _uc(raw_cookies.get("p_sync_session", ""))
    user_id = _uc(raw_cookies.get("notion_user_id", ""))
    csrf = _uc(raw_cookies.get("csrf", ""))
    device_id = _uc(raw_cookies.get("device_id", ""))
    browser_id = _uc(raw_cookies.get("notion_browser_id", ""))
    space_view_id = ls_data.get("spaceViewId") or ""

    values = {
        "NOTION_TOKEN_V2": token_v2,
        "NOTION_P_SYNC_SESSION": p_sync,
        "NOTION_SPACE_ID": space_id or "",
        "NOTION_USER_ID": user_id,
        "NOTION_SPACE_VIEW_ID": space_view_id,
        "NOTION_CSRF": csrf,
        "NOTION_DEVICE_ID": device_id,
        "NOTION_BROWSER_ID": browser_id,
    }

    for k, v in values.items():
        status = "✓" if v else "✗"
        print(f"  {status} {k}: {v[:40]}{'...' if len(v) > 40 else ''}", flush=True)

    return values


# ── 主流程 ────────────────────────────────────────────────

def register_and_extract_env() -> dict[str, str]:
    """
    完整自动注册 + env 提取流程。

    返回：提取到的 env 字段字典
    """
    ts = str(int(time.time()))
    email_addr = f"posase{ts}@pid.im"
    username = f"posase{ts}"
    print(f"[注册] 邮箱: {email_addr}", flush=True)

    # 1. 打开注册页
    print("[注册] 打开注册页...", flush=True)
    new_page(url=SIGNUP_URL)
    time.sleep(PAGE_SETTLE_SECS)

    # 2. 输入邮箱
    print("[注册] 输入邮箱...", flush=True)
    result = evaluate_script(mainWorld=True, function=_js_set_input('input[type="email"]', email_addr))
    if not (isinstance(result, dict) and result.get("ok")):
        raise RuntimeError(f"邮箱输入失败: {result}")

    # 3. 点继续，触发 OTP 发送；记录发送时间用于过滤历史邮件
    print("[注册] 点击继续，触发验证码发送...", flush=True)
    time.sleep(1)
    otp_sent_at = time.time()
    result = evaluate_script(mainWorld=True, function=_js_click_button("继续"))
    if not (isinstance(result, dict) and result.get("ok")):
        raise RuntimeError(f"继续按钮点击失败: {result}")

    # 4. 等待验证码（只接受 sent_after 之后到达的邮件，过滤历史旧码）
    otp = fetch_notion_otp(to_addr=email_addr, sent_after=otp_sent_at, timeout=OTP_WAIT_SECS)
    if not otp:
        raise RuntimeError("超时：未收到 Notion 验证码邮件")
    print(f"[注册] 收到验证码: {otp}", flush=True)

    # 6. 输入验证码
    print("[注册] 输入验证码...", flush=True)
    time.sleep(2)
    result = evaluate_script(mainWorld=True, function=_js_set_input('input[placeholder="输入验证码"]', otp))
    if not (isinstance(result, dict) and result.get("ok")):
        # 备用选择器
        result = evaluate_script(mainWorld=True, function=_js_set_input('input[type="text"]', otp))
    if not (isinstance(result, dict) and result.get("ok")):
        raise RuntimeError(f"验证码输入失败: {result}")

    result = evaluate_script(mainWorld=True, function=_js_click_button("继续"))
    if not (isinstance(result, dict) and result.get("ok")):
        raise RuntimeError(f"验证码提交失败: {result}")

    # 7. 等待 onboarding 页加载
    print("[注册] 等待 onboarding 档案页...", flush=True)
    time.sleep(PAGE_SETTLE_SECS)

    state = evaluate_script(mainWorld=True, function=_js_get_page_state())
    print(f"[注册] 当前页面: {state.get('url') if isinstance(state, dict) else state}", flush=True)

    # 8. 档案页：填名字 + 取消营销勾选
    if "onboarding" in (state.get("url", "") if isinstance(state, dict) else ""):
        body_text = state.get("body", "") if isinstance(state, dict) else ""
        if "自定义你的档案" in body_text or "你的名字" in body_text:
            print("[注册] 档案页：填写名字...", flush=True)
            result = evaluate_script(mainWorld=True, function=_js_set_input('input[type="text"]', username))
            if not (isinstance(result, dict) and result.get("ok")):
                # 名字冲突时使用随机后缀
                import random, string
                rand_suffix = "".join(random.choices(string.ascii_lowercase, k=4))
                username_alt = f"posase{rand_suffix}"
                evaluate_script(mainWorld=True, function=_js_set_input('input[type="text"]', username_alt))
                print(f"[注册] 名字冲突，改用: {username_alt}", flush=True)

            print("[注册] 取消营销勾选...", flush=True)
            evaluate_script(mainWorld=True, function=_js_uncheck_marketing())

            evaluate_script(mainWorld=True, function=_js_click_button("继续"))
            time.sleep(PAGE_SETTLE_SECS)

    # 9. 团队/工作空间页：创建新工作空间
    state = evaluate_script(mainWorld=True, function=_js_get_page_state())
    body_text = state.get("body", "") if isinstance(state, dict) else ""
    if "加入团队或创建工作空间" in body_text:
        print("[注册] 工作空间页：点击创建新工作空间...", flush=True)
        result = evaluate_script(mainWorld=True, function=_js_click_button("创建新工作空间"))
        if not (isinstance(result, dict) and result.get("ok")):
            raise RuntimeError("创建新工作空间按钮点击失败")
        time.sleep(PAGE_SETTLE_SECS)

    # 10. 用途页：选"用于私人生活" + 取消营销勾选 + 继续
    state = evaluate_script(mainWorld=True, function=_js_get_page_state())
    body_text = state.get("body", "") if isinstance(state, dict) else ""
    if "你想如何使用 Notion" in body_text:
        print("[注册] 用途页：选择私人生活...", flush=True)
        evaluate_script(mainWorld=True, function=_js_uncheck_marketing())
        result = evaluate_script(mainWorld=True, function=_js_click_button_contains("用于私人生活"))
        print(f"[注册] 点击结果: {result}", flush=True)
        time.sleep(1)
        evaluate_script(mainWorld=True, function=_js_click_button("继续"))
        time.sleep(PAGE_SETTLE_SECS)

    # 11. 桌面应用引导：暂时跳过
    state = evaluate_script(mainWorld=True, function=_js_get_page_state())
    body_text = state.get("body", "") if isinstance(state, dict) else ""
    if "暂时跳过" in body_text:
        print("[注册] 桌面应用引导：暂时跳过...", flush=True)
        evaluate_script(mainWorld=True, function=_js_click_button("暂时跳过"))
        time.sleep(PAGE_SETTLE_SECS)

    # 12. 等待主页完全加载
    print("[注册] 等待主页加载...", flush=True)
    time.sleep(5)

    state = evaluate_script(mainWorld=True, function=_js_get_page_state())
    print(f"[注册] 最终页面: {state.get('url') if isinstance(state, dict) else state}", flush=True)

    # 13. 提取 env
    print("[注册] 提取 env 参数...", flush=True)
    values = extract_env_from_browser()
    _write_env(values)
    return values


def env_only() -> dict[str, str]:
    """仅从当前浏览器页面提取 env，跳过注册流程。"""
    print("[env-only] 从当前浏览器页面提取 env...", flush=True)
    values = extract_env_from_browser()
    _write_env(values)
    return values


if __name__ == "__main__":
    if not MCP_AVAILABLE:
        print("错误：此脚本需要在 Claude Code MCP 上下文中运行，MCP 工具不可用。", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--env-only":
        env_only()
    else:
        register_and_extract_env()
