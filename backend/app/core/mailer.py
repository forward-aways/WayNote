"""邮件发送（标准库 smtplib，零新依赖）。

设计见 .deepcode/ADR-20261009-Waynote-email-code-auth.md §6.6。

纪律：
- **绝不把验证码写进日志**（只在邮件正文里出现）；日志只记录收件人与用途
- 未配置 SMTP 时抛 MailerError，由接口映射为明确错误（不静默降级）
- 465 端口走 SMTP_SSL；587 端口走 STARTTLS
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("mailer")

PURPOSE_LABEL = {"login": "登录", "register": "注册", "reset": "重置密码"}


class MailerError(RuntimeError):
    """发信失败（未配置 / 网络 / 认证 / 收件人被拒）。"""


def send_email_code(*, to: str, code: str, purpose: str, ttl_minutes: int) -> None:
    """发送验证码邮件；失败抛 MailerError（调用方据此拒绝请求，不落码）。"""
    if not settings.smtp_configured:
        raise MailerError("SMTP 未配置")

    action = PURPOSE_LABEL.get(purpose, "验证")
    subject = f"途笺 WayNote {action}验证码"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, settings.mail_from))
    message["To"] = to
    message.set_content(_text_body(code, action, ttl_minutes))
    message.add_alternative(_html_body(code, action, ttl_minutes), subtype="html")

    context = ssl.create_default_context()
    timeout = settings.smtp_timeout_seconds
    try:
        if settings.smtp_starttls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout) as server:
                server.starttls(context=context)
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=timeout, context=context
            ) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
    except (smtplib.SMTPException, OSError, ssl.SSLError) as exc:
        # 只记异常类型，绝不记授权码/验证码
        log.error(
            "发信失败 purpose=%s to=%s error=%s",
            purpose,
            to,
            exc.__class__.__name__,
            extra={"event": "auth.email_code.send_failed", "purpose": purpose},
        )
        raise MailerError(f"发送失败（{exc.__class__.__name__}）") from exc

    log.info(
        "验证码邮件已投递 purpose=%s to=%s",
        purpose,
        to,
        extra={"event": "auth.email_code.delivered", "purpose": purpose},
    )


def _text_body(code: str, action: str, ttl_minutes: int) -> str:
    return (
        f"你的{action}验证码是：{code}\n\n"
        f"有效期 {ttl_minutes} 分钟，请勿转发给他人。\n"
        "如果这不是你本人的操作，忽略本邮件即可。\n\n"
        "—— 途笺 WayNote"
    )


def _html_body(code: str, action: str, ttl_minutes: int) -> str:
    return f"""\
<div style="font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;background:#f2f8f5;padding:24px">
  <div style="max-width:420px;margin:0 auto;background:#ffffff;border-radius:16px;padding:28px 24px">
    <p style="margin:0 0 8px;color:#5b6b62;font-size:13px">途笺 WayNote · {action}验证码</p>
    <p style="margin:0 0 16px;color:#052a1b;font-size:34px;font-weight:700;letter-spacing:6px">{code}</p>
    <p style="margin:0;color:#5b6b62;font-size:13px;line-height:1.7">
      {ttl_minutes} 分钟内有效，请勿转发给他人。<br>
      如果这不是你本人的操作，忽略本邮件即可。
    </p>
  </div>
</div>
"""
