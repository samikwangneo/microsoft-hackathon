"""Intake orchestration: input -> OSV lookup -> NormalizedAlert.

This is the single entry point downstream stages care about. OSV is the source
of truth for whether the package is vulnerable and for every derived field.
"""

from __future__ import annotations

import httpx

from ..config import Settings
from ..ecosystems import highest_version, max_severity
from ..models import NormalizedAlert, ScanRequest
from .osv import OSVClient


async def normalize(
    req: ScanRequest,
    alert_id: str | None = None,
    *,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> NormalizedAlert:
    """Look the package up against OSV and build the normalized alert.

    `client` lets callers inject an httpx.AsyncClient (e.g. MockTransport in
    tests); otherwise the OSV client manages its own.
    """

    async with OSVClient(settings=settings, client=client) as osv:
        vulns = await osv.query(req)

    severity = max_severity([v.severity for v in vulns])
    fixed_version = highest_version([v.fixed_version for v in vulns if v.fixed_version])
    cve = next((v.cve for v in vulns if v.cve), None)

    return NormalizedAlert(
        package=req.package,
        current_version=req.version,
        ecosystem=req.ecosystem,
        source="osv",
        vulnerable=bool(vulns),
        severity=severity,
        fixed_version=fixed_version,
        cve=cve,
        vulnerabilities=vulns,
        alert_id=alert_id,
    )
