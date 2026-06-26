"""Remediation run endpoints.

- POST /run               start a run (scan → agents → PR), returns run_id
- GET  /run/{id}          run status
- GET  /run/{id}/events   Server-Sent Events stream of the run's telemetry
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..orchestrator import runner

router = APIRouter(prefix="/run", tags=["run"])


class RunRequest(BaseModel):
    repo_path: str = Field(..., description="Absolute path to the local repo checkout")
    package_source_file: str = Field("package.json", description="Manifest, relative to repo")
    email: str = Field(..., description="Address to notify with the PR summary")
    base_branch: str = "main"


class RunAccepted(BaseModel):
    run_id: str
    status: str


@router.post("", response_model=RunAccepted)
async def start_run(req: RunRequest) -> RunAccepted:
    repo = Path(req.repo_path)
    if not repo.is_dir():
        raise HTTPException(422, f"repo_path is not a directory: {req.repo_path}")
    if not (repo / req.package_source_file).is_file():
        raise HTTPException(422, f"manifest not found: {req.package_source_file}")
    state = runner.start_run(req.repo_path, req.package_source_file, req.email, req.base_branch)
    return RunAccepted(run_id=state.run_id, status=state.status)


@router.get("/{run_id}")
async def run_status(run_id: str) -> dict:
    state = runner.get_run(run_id)
    if state is None:
        raise HTTPException(404, "unknown run_id")
    return {"run_id": state.run_id, "status": state.status, "error": state.error}


@router.get("/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    state = runner.get_run(run_id)
    if state is None:
        raise HTTPException(404, "unknown run_id")

    async def stream():
        pos = 0
        while True:
            text = state.event_log.read_text(encoding="utf-8") if state.event_log.exists() else ""
            if len(text) > pos:
                for line in text[pos:].splitlines():
                    if line.strip():
                        yield f"data: {line}\n\n"
                pos = len(text)
            if state.status in ("completed", "failed"):
                yield f"event: end\ndata: {{\"status\": \"{state.status}\"}}\n\n"
                return
            await asyncio.sleep(0.4)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
