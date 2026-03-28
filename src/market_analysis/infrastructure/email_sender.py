"""SMTP email sender implementation.

Sends emails with PDF report attachments using the standard library.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SmtpSettings:
    """SMTP connection settings."""

    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    sender_email: str = ""


def send_email_with_attachment(
    *,
    settings: SmtpSettings,
    recipients: list[str],
    subject: str,
    body: str,
    attachment_name: str,
    attachment_data: bytes,
) -> None:
    """Send an email with a single PDF attachment.

    Args:
        settings: SMTP server configuration.
        recipients: List of email addresses to send to.
        subject: Email subject line.
        body: Plain text email body.
        attachment_name: Filename for the attachment.
        attachment_data: Raw bytes of the PDF file.

    Raises:
        smtplib.SMTPException: On any SMTP error.
        ValueError: If recipients list is empty or sender not configured.
    """
    if not recipients:
        raise ValueError("No recipients provided")
    if not settings.sender_email:
        raise ValueError("Sender email not configured (MA_SMTP_SENDER_EMAIL)")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.sender_email
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    msg.add_attachment(
        attachment_data,
        maintype="application",
        subtype="pdf",
        filename=attachment_name,
    )

    logger.info(
        "Sending email to %d recipient(s) via %s:%d",
        len(recipients),
        settings.host,
        settings.port,
    )

    with smtplib.SMTP(settings.host, settings.port) as server:
        if settings.use_tls:
            server.starttls()
        if settings.username and settings.password:
            server.login(settings.username, settings.password)
        server.send_message(msg)

    logger.info("Email sent successfully to %s", recipients)
