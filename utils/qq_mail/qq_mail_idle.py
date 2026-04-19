"""
QQ 邮箱 IMAP IDLE 实时监听 + 发送邮件
功能：
  1. IMAP IDLE 实时监听新邮件（不轮询）
  2. 新邮件到达立即触发拉取
  3. 只获取发件人、主题、正文（不下载附件）
  4. 自动处理超时、自动重连
  5. 支持发送邮件
"""

import imaplib2
import email
import email.header
import time
import smtplib
import ssl
import threading
import queue
import traceback
import sys
import os
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ── 配置 ──────────────────────────────────────────────
try:
    from dotenv import load_dotenv

    _ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(_ENV_PATH)
except Exception:
    pass

IMAP_HOST     = os.getenv("QQ_MAIL_IMAP_HOST", "imap.qq.com")
IMAP_PORT     = int(os.getenv("QQ_MAIL_IMAP_PORT", "993"))
IMAP_USER     = os.getenv("QQ_MAIL_IMAP_USER", "")
IMAP_PASSWORD = os.getenv("QQ_MAIL_IMAP_PASSWORD", "")

SMTP_HOST        = os.getenv("QQ_MAIL_SMTP_HOST", "smtp.qq.com")
SMTP_PORT        = int(os.getenv("QQ_MAIL_SMTP_PORT", "587"))
SMTP_PORT_FB     = int(os.getenv("QQ_MAIL_SMTP_PORT_FB", "465"))
SMTP_USER        = os.getenv("QQ_MAIL_SMTP_USER", IMAP_USER)
SMTP_PASSWORD    = os.getenv("QQ_MAIL_SMTP_PASSWORD", IMAP_PASSWORD)

# IDLE 等待超时时间（RFC 要求最长 29 分钟）
IDLE_TIMEOUT  = 25 * 60   # 秒

# 重连配置
RECONNECT_DELAY   = 5     # 重连前等待秒数
MAX_RECONNECT_MSG = 10    # 最多连续重连次数，-1=无限

# ── 编码处理 ──────────────────────────────────────────
def decode_str(s):
    """安全解码 email 头部字符串"""
    if s is None:
        return ""
    parts = []
    for result, encoding in email.header.decode_header(s):
        if isinstance(result, bytes):
            charset = encoding if encoding and encoding.lower() != "unknown-8bit" else "utf-8"
            parts.append(result.decode(charset, errors="replace"))
        else:
            parts.append(result)
    return "".join(parts)


def extract_body(msg):
    """从 email.Message 提取正文（优先 text/plain，其次 text/html）"""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and "attachment" not in part.get("Content-Disposition", ""):
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace").strip()
        return ""
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace").strip()


# ── IDLE 监听器核心 ──────────────────────────────────
class QQMailIDLE:
    """
    使用 imaplib2 实现 IDLE 模式，实时监听 QQ 邮箱新邮件。
    线程安全，可随时注册/取消回调。
    """

    def __init__(self, host=IMAP_HOST, port=IMAP_PORT,
                 user=IMAP_USER, password=IMAP_PASSWORD):
        self.host     = host
        self.port     = port
        self.user     = user
        self.password = password

        self._lock       = threading.RLock()
        self._stop_event = threading.Event()
        self._thread     = None
        self._conn       = None
        self._callbacks  = []

    # ── 公开 API ───────────────────────────────────────

    def subscribe(self, callback):
        """注册新邮件回调，签名为 on_new_mail(sender, subject, body)"""
        with self._lock:
            self._callbacks.append(callback)

    def start(self):
        """启动后台 IDLE 监听线程"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="QQ-IDLE")
        self._thread.start()

    def stop(self):
        """停止监听线程"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)

    # ── 内部实现 ───────────────────────────────────────

    def _connect(self):
        """建立 IMAP over SSL 连接，并 SELECT INBOX"""
        conn = imaplib2.IMAP4_SSL(self.host, self.port)
        conn.login(self.user, self.password)
        status, _ = conn.select("INBOX")
        if status != "OK":
            conn.logout()
            raise RuntimeError(f"SELECT INBOX 失败: {status}")
        return conn

    def _fetch_new_emails(self, conn):
        """拉取所有 UNSEEN 邮件，逐条派发"""
        try:
            status, msg_ids = conn.search(None, "UNSEEN")
            if status != "OK":
                return
            ids = msg_ids[0].split()
            if not ids:
                return
            for mid in ids:
                try:
                    status, raw = conn.fetch(mid, "(RFC822)")
                    if status != "OK" or not raw or not raw[0]:
                        continue
                    msg = email.message_from_bytes(raw[0][1])
                    sender  = decode_str(msg.get("From", ""))
                    subject = decode_str(msg.get("Subject", ""))
                    body    = extract_body(msg)
                    self._dispatch(sender, subject, body)
                except Exception:
                    traceback.print_exc()
        except Exception:
            traceback.print_exc()

    def _dispatch(self, sender, subject, body):
        """派发邮件给所有回调"""
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(sender, subject, body)
            except Exception:
                traceback.print_exc()

    def _idle_loop(self, conn):
        """
        单次 IDLE 循环：
        conn.idle() 阻塞直到服务器推送新邮件或超时，
        返回后拉取新邮件，然后继续 IDLE。
        """
        while not self._stop_event.is_set():
            try:
                conn.idle(timeout=IDLE_TIMEOUT)
            except imaplib2.IMAP4.abort:
                raise
            except Exception:
                traceback.print_exc()
                raise

            if self._stop_event.is_set():
                break
            self._fetch_new_emails(conn)

    def _run(self):
        """后台线程主循环：连接 → IDLE → 异常重连 → 循环"""
        reconnect_count = 0
        while not self._stop_event.is_set():
            try:
                print("[IDLE] 连接 IMAP 服务器...")
                conn = self._connect()
                self._conn = conn
                reconnect_count = 0
                print("[IDLE] 已连接，开始 IDLE 监听...")

                # 首次拉取（连接前可能堆积的邮件）
                self._fetch_new_emails(conn)
                self._idle_loop(conn)

            except imaplib2.IMAP4.abort as e:
                reconnect_count += 1
                limit = str(reconnect_count)
                if MAX_RECONNECT_MSG > 0:
                    limit = f"{reconnect_count}/{MAX_RECONNECT_MSG}"
                print(f"[IDLE] 连接断开，{RECONNECT_DELAY}秒后重连... ({limit})")
                if MAX_RECONNECT_MSG > 0 and reconnect_count > MAX_RECONNECT_MSG:
                    print("[IDLE] 超过最大重连次数，退出。")
                    break
            except Exception:
                traceback.print_exc()
                reconnect_count += 1

            if self._conn:
                try:
                    self._conn.logout()
                except Exception:
                    pass
                self._conn = None

            if self._stop_event.is_set():
                break
            time.sleep(RECONNECT_DELAY)

        print("[IDLE] 监听线程已停止。")


# ── 按收件人查询最新邮件 ────────────────────────────────
def fetch_latest_mail_to(
    to_addr: str,
    sent_after: float | None = None,
    sender_filter: str | None = None,
    timeout: int = 90,
    poll_interval: int = 3,
    host: str = IMAP_HOST,
    port: int = IMAP_PORT,
    user: str = IMAP_USER,
    password: str = IMAP_PASSWORD,
) -> dict | None:
    """
    轮询 INBOX，返回发给 to_addr 的最新一封符合条件的邮件。

    参数：
        to_addr        目标收件邮箱地址，用于在邮件头 To 字段匹配
        sent_after     Unix 时间戳（秒），只返回此时间之后到达的邮件；
                       为 None 时不限制时间（取最新一封）
        sender_filter  发件人过滤关键词（域名或地址片段），为 None 时不过滤
        timeout        最长等待秒数，超时返回 None
        poll_interval  两次查询之间的等待秒数

    返回：
        dict 包含字段：
            sender  str   发件人
            subject str   主题
            body    str   纯文本正文
            date    str   邮件 Date 头原始值
            ts      float 邮件时间的 Unix 时间戳
        或 None（超时未找到）
    """
    import email.utils as eu

    def _connect():
        conn = imaplib2.IMAP4_SSL(host, port)
        conn.login(user, password)
        conn.select("INBOX")
        return conn

    def _search_and_match(conn) -> dict | None:
        # 按发件人过滤缩小搜索范围
        if sender_filter:
            status, ids = conn.search(None, "FROM", sender_filter)
        else:
            status, ids = conn.search(None, "ALL")
        if status != "OK" or not ids[0].strip():
            return None

        # 逆序遍历（最新在后）
        all_ids = ids[0].split()
        for mid in reversed(all_ids):
            try:
                s2, raw = conn.fetch(mid, "(RFC822)")
                if s2 != "OK" or not raw or not raw[0]:
                    continue
                msg = email.message_from_bytes(raw[0][1])

                # 收件人匹配
                to_header = decode_str(msg.get("To", ""))
                if to_addr.lower() not in to_header.lower():
                    continue

                # 时间过滤
                date_str = msg.get("Date", "")
                mail_ts: float = 0.0
                if date_str:
                    try:
                        mail_ts = eu.parsedate_to_datetime(date_str).timestamp()
                    except Exception:
                        pass
                if sent_after is not None and mail_ts < sent_after:
                    continue

                return {
                    "sender":  decode_str(msg.get("From", "")),
                    "subject": decode_str(msg.get("Subject", "")),
                    "body":    extract_body(msg),
                    "date":    date_str,
                    "ts":      mail_ts,
                }
            except Exception:
                traceback.print_exc()
        return None

    deadline = time.time() + timeout
    conn = None
    try:
        conn = _connect()
        while time.time() < deadline:
            result = _search_and_match(conn)
            if result:
                return result
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))
    except Exception:
        traceback.print_exc()
    finally:
        if conn:
            try:
                conn.logout()
            except Exception:
                pass
    return None


# ── 发送邮件 ─────────────────────────────────────────
def send_email(to_addr, subject, body, html=False):
    """
    通过 QQ 邮箱 SMTP 发送邮件，自动尝试 587(STARTTLS) → 465(SSL)。
    """
    msg = MIMEMultipart()
    msg["From"]    = IMAP_USER
    msg["To"]      = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if html else "plain", "utf-8"))

    last_err = None
    for port in (SMTP_PORT, SMTP_PORT_FB):
        try:
            if port == 465:
                # SSL 直连
                with smtplib.SMTP_SSL(SMTP_HOST, port, timeout=15) as server:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(IMAP_USER, [to_addr], msg.as_string())
            else:
                # STARTTLS
                with smtplib.SMTP(SMTP_HOST, port, timeout=15) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(IMAP_USER, [to_addr], msg.as_string())
            print(f"[SMTP] 邮件已发送至 {to_addr}（端口 {port}）: {subject}")
            return
        except Exception as e:
            last_err = e
            print(f"[SMTP] 端口 {port} 失败: {e}")

    raise RuntimeError(f"SMTP 发送失败（已尝试 587/465）: {last_err}")


# ── 自测试 ───────────────────────────────────────────
def self_test():
    """发送测试邮件 → IDLE 监听验证"""
    print("\n" + "="*50)
    print("QQ 邮箱 IDLE 自测")
    print("="*50)

    mail_queue = queue.Queue()

    def on_new_mail(sender, subject, body):
        preview = body[:120].replace("\n", " ")
        mail_queue.put((sender, subject, preview))

    listener = QQMailIDLE()
    listener.subscribe(on_new_mail)
    listener.start()

    time.sleep(3)   # 等待连接稳定

    test_subject = f"IDLE 自测邮件 {time.strftime('%H:%M:%S')}"
    test_body    = (
        f"这是一封自动发送的测试邮件。\n"
        f"发送时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"如果收到此邮件，说明 IDLE 监听功能正常。"
    )
    print(f"\n[SMTP] 发送测试邮件...")
    send_email(IMAP_USER, test_subject, test_body)

    print("[IDLE] 等待新邮件到达（最多 90 秒）...")
    try:
        sender, subject, preview = mail_queue.get(timeout=90)
        print("\n✅ 成功接收新邮件！")
        print(f"   发件人: {sender}")
        print(f"   主题  : {subject}")
        print(f"   预览  : {preview}")
    except queue.Empty:
        print("\n⚠️  90 秒内未收到邮件（可能邮件已读过或 IDLE 未触发），请手动检查收件箱。")

    listener.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        self_test()
    else:
        print("用法：")
        print("  python qq_mail_idle.py --test   # 自测（发送+监听）")
        print("  python qq_mail_idle.py          # 仅启动监听（需先注册回调）")
        print()
        print("示例代码（监听模式）：")
        print("""
    from qq_mail_idle import QQMailIDLE

    def on_new_mail(sender, subject, body):
        print(f"来自: {sender}")
        print(f"主题: {subject}")
        print(f"正文（前200字）: {body[:200]}")

    listener = QQMailIDLE()
    listener.subscribe(on_new_mail)
    listener.start()
    input("按回车停止...")
    listener.stop()
""")
