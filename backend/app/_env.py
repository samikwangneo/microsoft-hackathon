"""Load the repo-root .env into the process environment (dependency-free).

The agents read Azure / SMTP credentials straight from os.environ, so the
backend must populate them before a run imports the agents. Existing environment
variables always win (so an explicit `export` overrides the file).
"""

from __future__ import annotations

import os
from pathlib import Path


def load_root_env() -> None:
    # backend/app/_env.py -> backend/app -> backend -> repo root
    root = Path(__file__).resolve().parents[2]
    for env_path in (root / ".env", root / "backend" / ".env"):
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
