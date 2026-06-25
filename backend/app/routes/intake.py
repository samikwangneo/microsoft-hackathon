"""Intake endpoints.

Single-package in, one `NormalizedAlert` out:
- POST /intake/scan    — raw {ecosystem, package, version} (OSV core).
- POST /intake/alert   — simplified scanner JSON (docs/examples/sample-alert.json).
- POST /intake/github  — a GitHub Dependabot alert (+ installed_version).

Whole-repo in, a `ManifestScanResult` out:
- POST /intake/manifest — a package.json; scans every pinned dependency.
"""

from __future__ import annotations

import json
from xml.etree import ElementTree

import httpx
from fastapi import APIRouter, HTTPException

from ..intake import manifests, parsers, service
from ..models import (
    GitHubDependabotAlert,
    ManifestFile,
    ManifestScanResult,
    NormalizedAlert,
    ScannerAlert,
    ScanRequest,
)

router = APIRouter(prefix="/intake", tags=["intake"])


def _osv_http_error(exc: httpx.HTTPError) -> HTTPException:
    """Translate an httpx error from OSV into an HTTP error for the client."""

    if isinstance(exc, httpx.HTTPStatusError):  # OSV returned a non-2xx
        return HTTPException(
            status_code=502, detail=f"OSV query failed: {exc.response.status_code}"
        )
    return HTTPException(status_code=504, detail=f"OSV unreachable: {exc}")


async def _normalize(req: ScanRequest, alert_id: str | None) -> NormalizedAlert:
    """Run the service, translating transport/upstream errors to HTTP."""

    try:
        return await service.normalize(req, alert_id)
    except httpx.HTTPError as exc:
        raise _osv_http_error(exc) from exc


@router.post("/scan", response_model=NormalizedAlert)
async def scan(req: ScanRequest) -> NormalizedAlert:
    """Query OSV directly for a package@version."""

    return await _normalize(req, alert_id=None)


@router.post("/alert", response_model=NormalizedAlert)
async def ingest_scanner_alert(alert: ScannerAlert) -> NormalizedAlert:
    """Ingest a simplified scanner alert (matches docs/examples/sample-alert.json)."""

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


@router.post("/manifest", response_model=ManifestScanResult)
async def scan_manifest(manifest: ManifestFile) -> ManifestScanResult:
    """Scan every pinned dependency in a manifest file against OSV.

    The parser is chosen by `filename`: package.json (npm), requirements.txt
    (PyPI), *.csproj / packages.config (NuGet). Dependencies whose version isn't
    a concrete pin (ranges, tags, MSBuild props) are reported under `skipped`
    rather than guessed at.
    """

    try:
        ecosystem, reqs, skipped = manifests.parse(manifest.filename, manifest.content)
    except ValueError as exc:  # unsupported manifest type
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (json.JSONDecodeError, ElementTree.ParseError) as exc:  # malformed file
        raise HTTPException(
            status_code=422, detail=f"Could not parse {manifest.filename}: {exc}"
        ) from exc

    try:
        results = await service.scan_many(reqs)
    except httpx.HTTPError as exc:
        raise _osv_http_error(exc) from exc

    return ManifestScanResult(
        ecosystem=ecosystem,
        name=manifest.filename,
        scanned=len(results),
        vulnerable_count=sum(1 for r in results if r.vulnerable),
        results=results,
        skipped=skipped,
    )
