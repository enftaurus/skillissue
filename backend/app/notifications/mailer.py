"""
Outbound email over SMTP (STARTTLS on 587, implicit TLS on 465). Credentials come from settings only and are never
logged. Sending runs in a worker thread so the API event loop isn't blocked.
"""
import asyncio
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Optional

from backend.app.core.config import settings
from backend.app.core.logging import logger


@dataclass
class SendResult:
    sent: bool
    detail: str = ""


def mail_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)


def _send_sync(to: str, subject: str, text: str, html: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    msg["To"] = to
    msg["Message-ID"] = make_msgid(domain=settings.SMTP_FROM_EMAIL.split("@")[-1] or None)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    ctx = ssl.create_default_context()
    if int(settings.SMTP_PORT) == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ctx, timeout=20) as s:
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)


async def send_email(to: str, subject: str, text: str, html: str) -> SendResult:
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("ALLOW_TEST_EMAIL"):
        return SendResult(False, "disabled in tests")  # never mail real people from the test suite
    if not mail_configured():
        return SendResult(False, "email is not configured on this server")
    try:
        await asyncio.to_thread(_send_sync, to, subject, text, html)
        logger.info(f"Email sent: '{subject}'")
        return SendResult(True)
    except smtplib.SMTPAuthenticationError:
        logger.warning("SMTP authentication failed (check SMTP_USER / SMTP_PASSWORD)")
        return SendResult(False, "the mail server rejected the login")
    except Exception as e:
        logger.warning(f"Email send failed: {type(e).__name__}")
        return SendResult(False, f"could not send email ({type(e).__name__})")
