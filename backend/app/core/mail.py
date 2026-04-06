import logging
import os
import smtplib
from email.message import EmailMessage

from app.core.paths import ensure_env_loaded

ensure_env_loaded()

logger = logging.getLogger("uvicorn.error")


def should_expose_reset_code() -> bool:
    raw_value = os.getenv("AUTH_DEBUG_EXPOSE_RESET_CODE", "true")
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def send_password_reset_email(recipient_email: str, code: str, expires_minutes: int) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username or "no-reply@example.com").strip()
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}

    if not smtp_host:
        logger.warning(
            "SMTP 未配置，密码重置验证码仅记录到日志。 email=%s code=%s expires_in=%smin",
            recipient_email,
            code,
            expires_minutes,
        )
        return False

    message = EmailMessage()
    message["Subject"] = "企业知识平台密码重置验证码"
    message["From"] = smtp_from_email
    message["To"] = recipient_email
    message.set_content(
        (
            "您好，\n\n"
            f"您的密码重置验证码是：{code}\n"
            f"验证码将在 {expires_minutes} 分钟后失效。\n\n"
            "如果这不是您的操作，请忽略这封邮件。"
        )
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        if smtp_use_tls:
            server.starttls()
        if smtp_username:
            server.login(smtp_username, smtp_password)
        server.send_message(message)

    return True
