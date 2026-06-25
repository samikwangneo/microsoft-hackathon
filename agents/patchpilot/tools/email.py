"""Email notification.

Delivers the remediation summary (PR link + per-fix results) to the requesting
user. Every message is also recorded to a local outbox for auditing.

Delivery is via SMTP, configured through ``PATCHPILOT_SMTP_*`` settings
(see ``config.py``). The approach mirrors a plain ``smtplib`` + ``MIMEMultipart``
send with STARTTLS and optional login: leave ``PATCHPILOT_SMTP_USER`` /
``PATCHPILOT_SMTP_PASSWORD`` unset to use an IP-allowlisted relay such as
``smtp-relay.gmail.com`` that needs no authentication. When no SMTP host is
configured, the message is recorded to the outbox only (handy for local demos).
"""

from __future__ import annotations

import html
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

from patchpilot.config import settings

_URL_RE = re.compile(r"(https?://[^\s<>\"]+)")


def _record_outbox(to: str, subject: str, body: str) -> Path:
    """Write the message to ./outbox for auditing and return its path."""
    outbox = Path.cwd() / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = outbox / f"email-{stamp}.txt"
    path.write_text(f"To: {to}\nSubject: {subject}\n\n{body}\n")
    return path


def _body_to_html(body: str) -> str:
    """Render the plain-text body as simple HTML with clickable links."""
    escaped = html.escape(body)
    linked = _URL_RE.sub(r'<a href="\1">\1</a>', escaped)
    paragraph = linked.replace("\n", "<br>")
    return f"<html><body><p>{paragraph}</p></body></html>"


def _build_message(to: str, subject: str, body: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = (
        formataddr((settings.smtp_from_name, settings.smtp_from))
        if settings.smtp_from_name
        else settings.smtp_from
    )
    msg["To"] = to
    msg["Subject"] = subject
    if settings.smtp_reply_to:
        msg["Reply-To"] = settings.smtp_reply_to
    # Per RFC 2046 the last alternative is preferred, so attach HTML last.
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(_body_to_html(body), "html"))
    return msg


def _send_smtp(to: str, msg: MIMEMultipart, *, retries: int = 3, retry_delay: int = 10) -> str:
    """Send via SMTP with retry/reconnect. Returns a detail string on success,
    or raises the last exception on repeated failure."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
            try:
                if settings.smtp_starttls:
                    server.starttls()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_from, [to], msg.as_string())
            finally:
                server.quit()
            return f"sent to {to} via {settings.smtp_host}:{settings.smtp_port}"
        except Exception as e:  # noqa: BLE001 — retry on any SMTP/connection error
            last_err = e
            if attempt < retries:
                time.sleep(retry_delay)
    raise last_err  # type: ignore[misc]


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Deliver an email and record it to the outbox. Returns (sent, detail)."""
    path = _record_outbox(to, subject, body)

    print("\n=== EMAIL ===")
    print(f"To: {to}\nSubject: {subject}\n\n{body}")
    print("=============\n")

    if not settings.smtp_host:
        return True, f"recorded to {path} (set PATCHPILOT_SMTP_HOST to send)"

    msg = _build_message(to, subject, body)
    try:
        detail = _send_smtp(to, msg)
        return True, f"{detail} (recorded to {path})"
    except Exception as e:  # noqa: BLE001 — surface delivery failure to the agent
        return False, f"SMTP delivery failed: {e} (recorded to {path})"
