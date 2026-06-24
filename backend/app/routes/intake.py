"""Intake endpoints.

Three ways in, one way out (`NormalizedAlert`):
- POST /intake/scan    — raw {ecosystem, package, version} (OSV core).
- POST /intake/alert   — simplified scanner JSON (examples/sample-alert.json).
- POST /intake/github  — a GitHub Dependabot alert (+ installed_version).
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from ..intake import parsers, service
from ..models import (
    GitHubDependabotAlert,
    NormalizedAlert,
    ScannerAlert,
    ScanRequest,
)

router = APIRouter(prefix="/intake", tags=["intake"])


async def _normalize(req: ScanRequest, alert_id: str | None) -> NormalizedAlert:
    """Run the service, translating transport/upstream errors to HTTP."""

    try:
        return await service.normalize(req, alert_id)
    except httpx.HTTPStatusError as exc:  # OSV returned a non-2xx
        raise HTTPException(
            status_code=502,
            detail=f"OSV query failed: {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:  # network/timeout
        raise HTTPException(status_code=504, detail=f"OSV unreachable: {exc}") from exc


@router.post("/scan", response_model=NormalizedAlert)
async def scan(req: ScanRequest) -> NormalizedAlert:
    """Query OSV directly for a package@version."""

    return await _normalize(req, alert_id=None)


@router.post("/alert", response_model=NormalizedAlert)
async def ingest_scanner_alert(alert: ScannerAlert) -> NormalizedAlert:
    """Ingest a simplified scanner alert (matches examples/sample-alert.json)."""

    req, alert_id = parsers.from_scanner_alert(alert)
    return await _normalize(req, alert_id)


@router.post("/github", response_model=NormalizedAlert)
async def ingest_github_alert(alert: GitHubDependabotAlert) -> NormalizedAlert:
    """Ingest a GitHub Dependabot alert (caller supplies installed_version)."""

    try:
        req, alert_id = parsers.from_github_alert(alert)
    except ValueError as exc:  # unsupported ecosystem
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _normalize(req, alert_id)
