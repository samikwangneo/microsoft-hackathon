"""Email notification.

For now this is a lightweight recorder: it prints the message and writes it to a
local outbox so the end-to-end run always produces an artifact. Real delivery
(SMTP / sendmail) can be swapped in later behind the same `send_email` signature
— a scripts/send_email.sh stub already exists for that purpose.
"""

from __future__ import annotations

import time
from pathlib import Path


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Record an outgoing email. Returns (sent, detail)."""
    outbox = Path.cwd() / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = outbox / f"email-{stamp}.txt"
    message = f"To: {to}\nSubject: {subject}\n\n{body}\n"
    path.write_text(message)

    print("\n=== EMAIL ===")
    print(message)
    print("=============\n")
    return True, f"recorded to {path}"
