import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import cloudscraper

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.qq_mail.qq_mail_idle import fetch_latest_mail_to

BASE_URL = "https://www.perplexity.ai"
DEFAULT_SOURCE = "default"
DEFAULT_VERSION = "2.18"
DEFAULT_REFERER = f"{BASE_URL}/onboarding/org/create"
OTP_PATTERN = re.compile(r"\b(\d{6})\b")


@dataclass
class MailCodeResult:
    code: str
    subject: str
    sender: str
    body: str


@dataclass
class OtpSubmitResult:
    status_code: int
    headers: Dict[str, Any]
    data: Dict[str, Any]
    redirect_url: Optional[str]


class PerplexityRegisterClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.scraper.headers.update(
            {
                "origin": BASE_URL,
                "referer": DEFAULT_REFERER,
            }
        )

    def _params(self) -> Dict[str, str]:
        return {"version": DEFAULT_VERSION, "source": DEFAULT_SOURCE}

    def get_login_details(self, email: str) -> Dict[str, Any]:
        response = self.scraper.post(
            f"{BASE_URL}/rest/enterprise/organization/login/details",
            params=self._params(),
            json={"email": email},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_providers(self) -> Dict[str, Any]:
        response = self.scraper.get(
            f"{BASE_URL}/api/auth/providers",
            params=self._params(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_csrf_token(self) -> str:
        response = self.scraper.get(
            f"{BASE_URL}/api/auth/csrf",
            params=self._params(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        token = response.json().get("csrfToken", "")
        if not token:
            raise RuntimeError("未获取到 csrfToken")
        return token

    def send_email_code(self, email: str, redirect_url: str = "/onboarding/org/create") -> Dict[str, Any]:
        self.get_providers()
        csrf_token = self.get_csrf_token()
        response = self.scraper.post(
            f"{BASE_URL}/api/auth/signin/email",
            params=self._params(),
            data={
                "email": email,
                "callbackUrl": redirect_url,
                "csrfToken": csrf_token,
                "json": "true",
                "useNumericOtp": "true",
            },
            timeout=self.timeout,
            allow_redirects=False,
        )
        content_type = response.headers.get("content-type", "")
        data: Dict[str, Any]
        if "application/json" in content_type:
            data = response.json()
        else:
            data = {"text": response.text}
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "data": data,
            "cookies": self.scraper.cookies.get_dict(),
        }

    def submit_otp(
        self,
        email: str,
        otp: str,
        redirect_url: str = "/onboarding/org/create",
        login_source: str = "organization-onboarding",
    ) -> OtpSubmitResult:
        response = self.scraper.post(
            f"{BASE_URL}/api/auth/otp-redirect-link",
            headers={"content-type": "application/json"},
            data=json.dumps(
                {
                    "email": email.lower(),
                    "otp": otp,
                    "redirectUrl": redirect_url,
                    "emailLoginMethod": "web-otp",
                    "loginSource": login_source,
                }
            ),
            timeout=self.timeout,
            allow_redirects=False,
        )
        content_type = response.headers.get("content-type", "")
        data: Dict[str, Any]
        if "application/json" in content_type:
            data = response.json()
        else:
            data = {"text": response.text}
        redirect_value = data.get("redirect") if isinstance(data, dict) else None
        return OtpSubmitResult(
            status_code=response.status_code,
            headers=dict(response.headers),
            data=data,
            redirect_url=redirect_value,
        )


def extract_code_from_text(text: str) -> Optional[str]:
    match = OTP_PATTERN.search(text)
    return match.group(1) if match else None


def wait_for_email_code(email: str, sent_after: float, timeout: int, sender_filter: Optional[str]) -> MailCodeResult:
    mail = fetch_latest_mail_to(
        to_addr=email,
        sent_after=sent_after,
        sender_filter=sender_filter,
        timeout=timeout,
        poll_interval=3,
    )
    if not mail:
        raise TimeoutError("在等待时间内未收到验证码邮件")
    combined = "\n".join([mail.get("subject", ""), mail.get("body", "")])
    code = extract_code_from_text(combined)
    if not code:
        raise RuntimeError("已收到邮件，但未从主题或正文中提取到 6 位验证码")
    return MailCodeResult(
        code=code,
        subject=mail.get("subject", ""),
        sender=mail.get("sender", ""),
        body=mail.get("body", ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Perplexity 注册流程验证脚本")
    parser.add_argument("email", help="接收验证码的邮箱")
    parser.add_argument("--mail-timeout", type=int, default=120, help="等待邮件秒数")
    parser.add_argument("--mail-sender-filter", default="perplexity", help="收码时的发件人过滤关键词")
    parser.add_argument("--skip-mail", action="store_true", help="仅验证当前阶段，不等待邮件")
    parser.add_argument("--otp", help="直接提交指定验证码")
    parser.add_argument("--hybrid", action="store_true", help="启用最小浏览器参与模式，手动完成发码后由脚本继续收码和提交验证码")
    parser.add_argument("--manual-code", action="store_true", help="不连接 QQ 邮箱，改为手动输入验证码")
    args = parser.parse_args()

    client = PerplexityRegisterClient()
    login_details = client.get_login_details(args.email)
    print("[login_details]", login_details)

    sent_after = time.time()
    if args.hybrid:
        print("[hybrid] 请在浏览器中打开 https://www.perplexity.ai/onboarding/org/create")
        print(f"[hybrid] 请手动输入邮箱并点击继续使用电子邮件: {args.email}")
        print("[hybrid] 完成发码后，回到终端等待邮件与提交验证码。")
        sent_after = time.time() - 30
    else:
        send_result = client.send_email_code(args.email)
        print("[send_email_code]", send_result["status_code"], send_result["data"])
        if send_result["status_code"] != 200:
            print("[warning] 发码接口未成功，当前脚本只完成链路验证与错误落盘。")
            return 1

    if args.skip_mail:
        return 0

    otp_code = args.otp
    if not otp_code and args.manual_code:
        otp_code = input("请输入验证码: ").strip()
    if not otp_code:
        mail_result = wait_for_email_code(
            email=args.email,
            sent_after=sent_after,
            timeout=args.mail_timeout,
            sender_filter=args.mail_sender_filter or None,
        )
        print("[mail_subject]", mail_result.subject)
        print("[mail_sender]", mail_result.sender)
        print("[mail_code]", mail_result.code)
        otp_code = mail_result.code

    otp_result = client.submit_otp(args.email, otp_code)
    print("[submit_otp]", otp_result.status_code, otp_result.data)
    if otp_result.redirect_url:
        print("[redirect_url]", otp_result.redirect_url)
    return 0 if otp_result.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
