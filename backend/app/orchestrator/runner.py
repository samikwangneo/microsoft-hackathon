"""Drive a full remediation run and expose its telemetry + result.

A run = intake scan (OSV) → bridge → patchpilot agents (edit/commit/PR/email).
The agents append structured events to a per-run JSONL log (PATCHPILOT_EVENT_LOG)
which the SSE endpoint tails for the live dashboard. The final RunResult is
mapped to a DashboardPayload.

Single-run-at-a-time is assumed (the event-log env var is process-global) — fine
for a demo.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..dashboard.models import DashboardPayload
from ..intake import manifests, service
from ..models import ManifestScanResult
from . import bridge
from .dashboard_map import build_dashboard_payload

# backend/runs/<run_id>.jsonl  (orchestrator -> app -> backend)
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"


@dataclass
class RunState:
    run_id: str
    repo_path: str
    status: str = "pending"  # pending|scanning|remediating|completed|failed
    event_log: Path = field(default=Path())
    error: str | None = None
    payload: DashboardPayload | None = None
    started_at: float = field(default_factory=time.time)


_RUNS: dict[str, RunState] = {}
_LATEST_COMPLETED: str | None = None


def get_run(run_id: str) -> RunState | None:
    return _RUNS.get(run_id)


def latest_payload() -> DashboardPayload | None:
    """The most recently completed run's dashboard payload, if any."""
    if _LATEST_COMPLETED and (state := _RUNS.get(_LATEST_COMPLETED)):
        return state.payload
    return None


def start_run(
    repo_path: str | Path,
    package_source_file: str,
    user_email: str,
    base_branch: str = "main",
) -> RunState:
    """Register a run and kick off its background execution task."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    state = RunState(
        run_id=run_id,
        repo_path=str(repo_path),
        event_log=RUNS_DIR / f"{run_id}.jsonl",
    )
    state.event_log.write_text("")  # so the SSE reader can open it immediately
    _RUNS[run_id] = state
    asyncio.create_task(
        _execute(state, Path(repo_path), package_source_file, user_email, base_branch)
    )
    return state


async def _execute(
    state: RunState,
    repo_path: Path,
    source_file: str,
    user_email: str,
    base_branch: str,
) -> None:
    global _LATEST_COMPLETED
    # Point telemetry at this run's log before importing/using the agents.
    os.environ["PATCHPILOT_EVENT_LOG"] = str(state.event_log)
    os.environ["PATCHPILOT_RUN_ID"] = state.run_id
    # telemetry has no model dependency — import it first so we can always emit.
    from patchpilot.telemetry import emit

    try:
        state.status = "scanning"
        emit("run_started", message=f"Scanning {source_file} against OSV", agent="orchestrator")
        content = (repo_path / source_file).read_text(encoding="utf-8")
        ecosystem, reqs, skipped = manifests.parse(source_file, content)
        results = await service.scan_many(reqs)
        scan = ManifestScanResult(
            ecosystem=ecosystem,
            name=source_file,
            scanned=len(results),
            vulnerable_count=sum(1 for r in results if r.vulnerable),
            results=results,
            skipped=skipped,
        )
        notification = bridge.to_notification(
            scan,
            repo_path=repo_path,
            package_source_file=source_file,
            user_email=user_email,
        )
        emit(
            "intake_complete",
            agent="orchestrator",
            message=f"{len(notification.packages)} vulnerable package(s) found",
            packages=[p.name for p in notification.packages],
        )

        if not notification.packages:
            state.payload = build_dashboard_payload(None, notification, repo_path.name)
            state.status = "completed"
            _LATEST_COMPLETED = state.run_id
            emit("run_complete", agent="orchestrator", message="No vulnerable packages")
            return

        # Import the agents only now (needs Azure creds); scan progress is
        # already streamed above, so credential errors surface cleanly here.
        from patchpilot.agents.summary import run_summary_agent

        state.status = "remediating"
        result = await run_summary_agent(notification, user_email, base_branch=base_branch)
        diff_text = ""
        if result.branch:
            from patchpilot.tools.git import diff_range

            diff_text = await diff_range(repo_path, base_branch, result.branch)
        state.payload = build_dashboard_payload(
            result, notification, repo_path.name, diff=diff_text
        )
        state.status = "completed"
        _LATEST_COMPLETED = state.run_id
        emit("run_complete", agent="orchestrator", message="Remediation complete", pr_url=result.pr_url)
    except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
        # Some exceptions (e.g. NotImplementedError) have an empty str(); always
        # include the type so the failure is diagnosable.
        detail = f"{type(exc).__name__}: {exc}".rstrip(": ")
        state.status = "failed"
        state.error = detail
        try:
            emit("run_failed", agent="orchestrator", message=detail)
        except Exception:  # noqa: BLE001
            pass
