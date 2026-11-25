"""Shared SMTP e-mail helper.

The same STARTTLS/send block was copy-pasted across the audio-to-text scripts
(3wh.py, test-api.py, whisper.py, mail/mail.py). Credentials come from env.
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config


def send_email(subject: str, body: str, recipients: list[str],
               html: bool = False) -> None:
    """Send an e-mail via the configured SMTP server (STARTTLS)."""
    msg = MIMEMultipart()
    msg["From"] = config.SMTP_LOGIN
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if html else "plain", "utf-8"))

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(config.SMTP_LOGIN, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_LOGIN, recipients, msg.as_string())
