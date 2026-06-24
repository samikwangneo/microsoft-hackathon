"""Structured event logging.

Events are appended as JSON lines to the file named in SUPPLYFIX_EVENT_LOG.
If the variable is unset, emit() is a no-op, so telemetry is opt-in and never
interferes with normal runs.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


def emit(kind: str, *, agent: str | None = None, message: str | None = None, **data: Any) -> None:
    """Append a structured event when SUPPLYFIX_EVENT_LOG is configured."""
    target = os.environ.get("SUPPLYFIX_EVENT_LOG")
    if not target:
        return

    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "ts": time.time(),
        "kind": kind,
        "run_id": os.environ.get("SUPPLYFIX_RUN_ID"),
        "agent": agent,
        "message": message,
        "data": _jsonable(data),
    }
    try:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(event, default=str))
            f.write("\n")
    except OSError:
        return


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value, default=str)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(k): _jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_jsonable(v) for v in value]
        return str(value)
