"""
Notion 邮箱自动注册 + 多账号 env 管理脚本（Playwright 方案）。

依赖条件：
  1. pip install -r requirements.txt
  2. playwright install chromium
  3. utils/qq_mail/qq_mail_idle.py 可用，IMAP 配置有效

用法：
  python auto_register.py register [--export]
  python auto_register.py refresh --account <account_id> [--export]
  python auto_register.py export --account <account_id>
  python auto_register.py list
"""

import sys
import io
import os
import re
import time
import json
import argparse
import urllib.parse
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PROJECT_ROOT))
sys.path.insert(0, os.path.join(_REPO_ROOT, "utils", "qq_mail"))

from qq_mail_idle import fetch_latest_mail_to

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ACCOUNTS_DIR = BASE_DIR / "accounts"
SIGNUP_URL = "https://www.notion.so/signup?from=marketing&pathname=%2F"
HOME_URL = "https://www.notion.so/"
OTP_WAIT_SECS = 120
SETTLE_SECS = 3
HEADLESS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)
HEADLESS_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]
HEADLESS_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
"""


def fetch_notion_otp(to_addr: str, sent_after: float, timeout: int = OTP_WAIT_SECS) -> str | None:
    """
    等待并提取发给 to_addr 的 Notion 验证码邮件中的 6 位 OTP。

    参数：
        to_addr     收件邮箱地址
        sent_after  Unix 时间戳（秒），此前到达的邮件忽略
        timeout     最长等待秒数

    返回：6 位验证码字符串，或 None（超时未收到）
    """
    print(f"[IMAP] 等待 Notion OTP → {to_addr}（最多 {timeout}s）...", flush=True)
    mail = fetch_latest_mail_to(
        to_addr=to_addr,
        sent_after=max(sent_after - 5, 0),
        sender_filter="notion",
        timeout=timeout,
        poll_interval=3,
    )
    if not mail:
        return None
    m = re.search(r"\b(\d{6})\b", mail["body"])
    if m:
        print(f"[IMAP] {mail['subject']} → 验证码: {m.group(1)}", flush=True)
        return m.group(1)
    return None


def _write_env(values: dict[str, str]) -> None:
    """更新项目根 .env 文件中的关键字段。"""
    try:
        from dotenv import dotenv_values
        current = dict(dotenv_values(ENV_PATH)) if ENV_PATH.exists() else {}
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
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[env] 已写入 {ENV_PATH}", flush=True)


def _account_dir(account_id: str) -> Path:
    return ACCOUNTS_DIR / account_id


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _js_set_input(selector: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
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
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"""() => {{
  const buttons = Array.from(document.querySelectorAll('[role="button"], button, input[type="submit"]'));
  const normalize = value => (value || '').replace(/\\s+/g, ' ').trim();
  const aliases = {{
    '继续': ['继续', 'Continue'],
    '暂时跳过': ['暂时跳过', 'Skip for now'],
    '创建新工作空间': ['创建新工作空间', 'Create a new workspace'],
  }};
  const targets = (aliases['{escaped}'] || ['{escaped}']).map(normalize);
  const labelOf = el => normalize(el.innerText || el.value || el.getAttribute('aria-label'));
  const btn = buttons.find(el => targets.includes(labelOf(el)))
    || buttons.find(el => targets.some(target => labelOf(el).includes(target)));
  if (!btn) return {{ok: false, found: false, candidates: buttons.slice(0, 20).map(labelOf)}};
  btn.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true, view: window}}));
  return {{ok: true, clicked: labelOf(btn)}};
}}"""


def _js_click_button_contains(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("'", "\\'")
    return f"""() => {{
  const btn = Array.from(document.querySelectorAll('[role="button"], button'))
    .find(el => (el.innerText || '').trim().includes('{escaped}'));
  if (!btn) return {{ok: false, found: false}};
  btn.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true, view: window}}));
  return {{ok: true, clicked: (btn.innerText || '').trim().slice(0, 60)}};
}}"""


def _js_uncheck_marketing() -> str:
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
    return """() => ({
  url: location.href,
  body: document.body.innerText.slice(0, 800)
})"""


def _ensure_ok(result: dict, message: str) -> None:
    if not isinstance(result, dict) or not result.get("ok"):
        raise RuntimeError(f"{message}: {result}")


def _launch_browser(p, headless: bool):
    return p.chromium.launch(headless=headless, args=HEADLESS_LAUNCH_ARGS if headless else [])


def _new_context(browser, headless: bool, storage_state: str | None = None):
    kwargs = {"locale": "zh-CN"}
    if storage_state:
        kwargs["storage_state"] = storage_state
    if headless:
        kwargs["user_agent"] = HEADLESS_USER_AGENT
    return browser.new_context(**kwargs)


def _new_page(context, headless: bool):
    page = context.new_page()
    if headless:
        page.add_init_script(HEADLESS_INIT_SCRIPT)
    return page


def _advance_onboarding(page, account_id: str) -> None:
    state = page.evaluate(_js_get_page_state())
    body = state.get("body", "") if isinstance(state, dict) else ""

    if "Customize your profile" in body or "Your name" in body:
        _ensure_ok(page.evaluate(_js_set_input('input[type="text"]', account_id)), "名字输入失败")
        page.evaluate(_js_uncheck_marketing())
        _ensure_ok(page.evaluate(_js_click_button("继续")), "档案页继续失败")
        time.sleep(SETTLE_SECS)

    if "自定义你的档案" in body or "你的名字" in body:
        _ensure_ok(page.evaluate(_js_set_input('input[type="text"]', account_id)), "名字输入失败")
        page.evaluate(_js_uncheck_marketing())
        _ensure_ok(page.evaluate(_js_click_button("继续")), "档案页继续失败")
        time.sleep(SETTLE_SECS)

    state = page.evaluate(_js_get_page_state())
    body = state.get("body", "") if isinstance(state, dict) else ""
    if "加入团队或创建工作空间" in body:
        _ensure_ok(page.evaluate(_js_click_button("创建新工作空间")), "创建新工作空间失败")
        time.sleep(SETTLE_SECS)

    state = page.evaluate(_js_get_page_state())
    body = state.get("body", "") if isinstance(state, dict) else ""
    if "你想如何使用 Notion" in body:
        page.evaluate(_js_uncheck_marketing())
        _ensure_ok(page.evaluate(_js_click_button_contains("用于私人生活")), "用途选择失败")
        time.sleep(1)
        _ensure_ok(page.evaluate(_js_click_button("继续")), "用途页继续失败")
        time.sleep(SETTLE_SECS)

    state = page.evaluate(_js_get_page_state())
    body = state.get("body", "") if isinstance(state, dict) else ""
    if "你的团队中还有谁" in body or "邀请你的团队" in body or "添加更多成员或批量邀请" in body:
        _ensure_ok(page.evaluate(_js_click_button("继续")), "邀请成员页继续失败")
        time.sleep(SETTLE_SECS)

    state = page.evaluate(_js_get_page_state())
    body = state.get("body", "") if isinstance(state, dict) else ""
    if "选择方案" in body:
        _ensure_ok(page.evaluate(_js_click_button("继续")), "方案页继续失败")
        time.sleep(SETTLE_SECS)

    state = page.evaluate(_js_get_page_state())
    body = state.get("body", "") if isinstance(state, dict) else ""
    if "暂时跳过" in body:
        _ensure_ok(page.evaluate(_js_click_button("暂时跳过")), "跳过桌面应用失败")
        time.sleep(SETTLE_SECS)


def _extract_env(page, context) -> dict[str, str]:
    cookies = {c["name"]: c["value"] for c in context.cookies()}

    time.sleep(3)

    state_data = page.evaluate("""() => {
      const result = {
        spaceViewId: null,
        spaceId: null,
        pathname: location.pathname,
        href: location.href,
        localStorageKeys: Object.keys(localStorage),
      };

      const normalizeId = (value) => {
        if (!value || typeof value !== 'string') return null;
        const clean = value.trim();
        if (/^[0-9a-f]{32}$/i.test(clean)) {
          return `${clean.slice(0, 8)}-${clean.slice(8, 12)}-${clean.slice(12, 16)}-${clean.slice(16, 20)}-${clean.slice(20)}`;
        }
        if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(clean)) {
          return clean;
        }
        return null;
      };

      const visit = (value, key = '') => {
        if (result.spaceId && result.spaceViewId) return;
        if (typeof value === 'string') {
          const normalized = normalizeId(value);
          const lowerKey = key.toLowerCase();
          if (normalized) {
            if (!result.spaceViewId && lowerKey.includes('spaceview')) result.spaceViewId = normalized;
            else if (!result.spaceId && (lowerKey.includes('spaceid') || lowerKey.includes('space_id') || lowerKey.includes('space'))) result.spaceId = normalized;
          }
          if (value.startsWith('{') || value.startsWith('[')) {
            try {
              visit(JSON.parse(value), key);
            } catch (e) {}
          }
          return;
        }
        if (Array.isArray(value)) {
          for (const item of value) visit(item, key);
          return;
        }
        if (!value || typeof value !== 'object') return;
        for (const [childKey, childValue] of Object.entries(value)) {
          const normalized = typeof childValue === 'string' ? normalizeId(childValue) : null;
          const lowerChildKey = childKey.toLowerCase();
          if (normalized) {
            if (!result.spaceViewId && lowerChildKey.includes('spaceview')) result.spaceViewId = normalized;
            else if (!result.spaceId && (lowerChildKey === 'id' || lowerChildKey.includes('spaceid') || lowerChildKey.includes('space_id') || lowerChildKey === 'space')) result.spaceId = normalized;
          }
          visit(childValue, childKey);
        }
      };

      const directKeys = [
        ['LRU:KeyValueStore2:lastVisitedRouteSpaceViewId', 'spaceViewId'],
        ['LRU:KeyValueStore2:lastVisitedRouteSpaceId', 'spaceId'],
      ];
      for (const [key, field] of directKeys) {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        try {
          result[field] = normalizeId(JSON.parse(raw).value) || result[field];
        } catch (e) {}
      }

      for (const k of Object.keys(localStorage)) {
        const raw = localStorage.getItem(k);
        if (!raw) continue;
        visit(raw, k);
      }

      const stores = [
        window?.__consoleStore?.getState?.(),
        window?.store?.getState?.(),
        window?.notionStore?.getState?.(),
      ];
      for (const store of stores) {
        if (!store) continue;
        visit(store, 'store');
        const currentSpace = store.currentSpace;
        if (currentSpace && !result.spaceId && typeof currentSpace.id === 'string') {
          result.spaceId = normalizeId(currentSpace.id) || result.spaceId;
        }
        if (currentSpace && !result.spaceViewId && typeof currentSpace.spaceViewId === 'string') {
          result.spaceViewId = normalizeId(currentSpace.spaceViewId) || result.spaceViewId;
        }
      }

      return result;
    }""") or {}

    api_space_id = ""
    api_space_view_id = ""
    try:
        api_data = page.evaluate("""async () => {
          const calls = [
            ['/api/v3/getSpacesInitial', {}],
            ['/api/v3/loadUserContent', {}],
          ];
          const results = [];
          for (const [url, payload] of calls) {
            try {
              const resp = await fetch(url, {
                method: 'POST',
                headers: {'content-type': 'application/json'},
                body: JSON.stringify(payload),
                credentials: 'include'
              });
              results.push(await resp.json());
            } catch (e) {}
          }
          return results;
        }""")
        if isinstance(api_data, list):
            for item in api_data:
                if not isinstance(item, dict):
                    continue
                record_map = item.get("recordMap", {})
                spaces = record_map.get("space", {}) if isinstance(record_map, dict) else {}
                space_views = record_map.get("space_view", {}) if isinstance(record_map, dict) else {}
                if not api_space_id and spaces:
                    api_space_id = next(iter(spaces))
                if not api_space_view_id and space_views:
                    api_space_view_id = next(iter(space_views))

                users = item.get("users", {})
                if isinstance(users, dict):
                    for user_data in users.values():
                        if not isinstance(user_data, dict):
                            continue
                        user_root = user_data.get("user_root", {})
                        if not isinstance(user_root, dict):
                            continue
                        for root_entry in user_root.values():
                            value_wrapper = root_entry.get("value", {}) if isinstance(root_entry, dict) else {}
                            inner_value = value_wrapper.get("value", {}) if isinstance(value_wrapper, dict) else {}
                            if not api_space_view_id:
                                space_views_list = inner_value.get("space_views", [])
                                if isinstance(space_views_list, list) and space_views_list:
                                    api_space_view_id = space_views_list[0]
                            if not api_space_id:
                                pointers = inner_value.get("space_view_pointers", [])
                                if isinstance(pointers, list):
                                    for pointer in pointers:
                                        if isinstance(pointer, dict) and pointer.get("spaceId"):
                                            api_space_id = pointer.get("spaceId")
                                            if not api_space_view_id and pointer.get("id"):
                                                api_space_view_id = pointer.get("id")
                                            break
    except Exception:
        pass

    path_space_id = ""
    pathname = state_data.get("pathname", "")
    m = re.search(r"/[a-zA-Z0-9-]+/([0-9a-f]{32})(?:\?|$)", pathname)
    if m:
        raw = m.group(1)
        path_space_id = f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"

    def _uc(v: str) -> str:
        return urllib.parse.unquote(v) if v else ""

    values = {
        "NOTION_TOKEN_V2": _uc(cookies.get("token_v2", "")),
        "NOTION_P_SYNC_SESSION": _uc(cookies.get("p_sync_session", "")),
        "NOTION_SPACE_ID": api_space_id or state_data.get("spaceId") or path_space_id or "",
        "NOTION_USER_ID": _uc(cookies.get("notion_user_id", "")),
        "NOTION_SPACE_VIEW_ID": api_space_view_id or state_data.get("spaceViewId") or "",
        "NOTION_CSRF": _uc(cookies.get("csrf", "")),
        "NOTION_DEVICE_ID": _uc(cookies.get("device_id", "")),
        "NOTION_BROWSER_ID": _uc(cookies.get("notion_browser_id", "")),
    }

    for k, v in values.items():
        status = "✓" if v else "✗"
        print(f"  {status} {k}: {v[:40]}{'...' if len(v) > 40 else ''}", flush=True)
    return values


def _save_account(account_id: str, email_addr: str, values: dict[str, str], context) -> None:
    account_dir = _account_dir(account_id)
    account_dir.mkdir(parents=True, exist_ok=True)

    state_path = account_dir / "state.json"
    env_path = account_dir / "env.json"
    meta_path = account_dir / "meta.json"

    context.storage_state(path=str(state_path))
    _write_json(env_path, values)

    old_meta = _read_json(meta_path)
    meta = {
        "account_id": account_id,
        "email": email_addr,
        "user_id": values.get("NOTION_USER_ID", ""),
        "space_id": values.get("NOTION_SPACE_ID", ""),
        "space_view_id": values.get("NOTION_SPACE_VIEW_ID", ""),
        "created_at": old_meta.get("created_at") or datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _write_json(meta_path, meta)
    print(f"[account] 已保存账号目录: {account_dir}", flush=True)


def _run_register(export_root: bool, headless: bool) -> None:
    ts = str(int(time.time()))
    email_addr = f"posase{ts}@example.test"
    account_id = f"posase{ts}"
    print(f"[注册] 邮箱: {email_addr}", flush=True)

    with sync_playwright() as p:
        browser = _launch_browser(p, headless)
        context = _new_context(browser, headless)
        page = _new_page(context, headless)
        page.goto(SIGNUP_URL, wait_until="domcontentloaded")
        time.sleep(SETTLE_SECS)

        _ensure_ok(page.evaluate(_js_set_input('input[type="email"]', email_addr)), "邮箱输入失败")
        time.sleep(1)

        otp_sent_at = time.time()
        _ensure_ok(page.evaluate(_js_click_button("继续")), "继续按钮点击失败")
        time.sleep(8)

        otp = fetch_notion_otp(email_addr, otp_sent_at)
        if not otp:
            raise RuntimeError("超时：未收到 Notion 验证码邮件")
        print(f"[注册] 验证码: {otp}", flush=True)

        time.sleep(2)
        result = page.evaluate(_js_set_input('input[placeholder="输入验证码"]', otp))
        if not isinstance(result, dict) or not result.get("ok"):
            _ensure_ok(page.evaluate(_js_set_input('input[type="text"]', otp)), "验证码输入失败")

        _ensure_ok(page.evaluate(_js_click_button("继续")), "验证码提交失败")
        time.sleep(SETTLE_SECS)

        _advance_onboarding(page, account_id)

        page.goto(HOME_URL, wait_until="domcontentloaded")
        time.sleep(5)

        values = _extract_env(page, context)
        _save_account(account_id, email_addr, values, context)
        browser.close()

    _run_refresh(account_id=account_id, export_root=export_root, headless=headless)


def _run_refresh(account_id: str, export_root: bool, headless: bool) -> None:
    account_dir = _account_dir(account_id)
    state_path = account_dir / "state.json"
    meta_path = account_dir / "meta.json"
    if not state_path.exists():
        raise RuntimeError(f"账号不存在或缺少状态文件: {state_path}")

    meta = _read_json(meta_path)
    email_addr = meta.get("email", account_id)
    print(f"[refresh] 账号: {account_id} ({email_addr})", flush=True)

    with sync_playwright() as p:
        browser = _launch_browser(p, headless)
        context = _new_context(browser, headless, storage_state=str(state_path))
        page = _new_page(context, headless)
        page.goto(HOME_URL, wait_until="domcontentloaded")
        time.sleep(5)
        _advance_onboarding(page, account_id)

        values = _extract_env(page, context)
        _save_account(account_id, email_addr, values, context)
        if export_root:
            _write_env(values)

        browser.close()


def _run_export(account_id: str) -> None:
    env_path = _account_dir(account_id) / "env.json"
    if not env_path.exists():
        raise RuntimeError(f"账号不存在或缺少 env 文件: {env_path}")
    values = _read_json(env_path)
    _write_env(values)
    print(f"[export] 已导出账号 {account_id} 到项目根 .env", flush=True)


def _run_list() -> None:
    if not ACCOUNTS_DIR.exists():
        print("[list] 暂无账号", flush=True)
        return

    found = False
    for account_dir in sorted(ACCOUNTS_DIR.iterdir()):
        if not account_dir.is_dir():
            continue
        meta = _read_json(account_dir / "meta.json")
        print(
            f"- account={account_dir.name} | email={meta.get('email', '')} | "
            f"user_id={meta.get('user_id', '')} | space_id={meta.get('space_id', '')} | "
            f"updated_at={meta.get('updated_at', '')}",
            flush=True,
        )
        found = True
    if not found:
        print("[list] 暂无账号", flush=True)


def main() -> None:
    ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="Notion 账号自动注册 + 多账号 env 管理（Playwright）")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser("register", help="注册一个新账号")
    register_parser.add_argument("--export", action="store_true", help="注册完成后导出到项目根 .env")
    register_parser.add_argument("--headless", action="store_true", help="使用无头浏览器运行，适合 Linux 服务器")

    refresh_parser = subparsers.add_parser("refresh", help="刷新指定账号的 env")
    refresh_parser.add_argument("--account", required=True, help="账号 ID")
    refresh_parser.add_argument("--export", action="store_true", help="刷新完成后导出到项目根 .env")
    refresh_parser.add_argument("--headless", action="store_true", help="使用无头浏览器运行，适合 Linux 服务器")

    export_parser = subparsers.add_parser("export", help="导出指定账号到项目根 .env")
    export_parser.add_argument("--account", required=True, help="账号 ID")

    subparsers.add_parser("list", help="列出已有账号")

    args = parser.parse_args()

    if args.command == "register":
        _run_register(export_root=args.export, headless=args.headless)
    elif args.command == "refresh":
        _run_refresh(account_id=args.account, export_root=args.export, headless=args.headless)
    elif args.command == "export":
        _run_export(account_id=args.account)
    elif args.command == "list":
        _run_list()


if __name__ == "__main__":
    main()
