"""Intake orchestration: input -> OSV lookup -> NormalizedAlert.

This is the single entry point downstream stages care about. OSV is the source
of truth for whether the package is vulnerable and for every derived field.
"""

from __future__ import annotations

import httpx

from ..config import Settings
from ..ecosystems import highest_version, max_severity
from ..models import NormalizedAlert, ScanRequest, Vulnerability
from .osv import OSVClient


def _build(
    req: ScanRequest, vulns: list[Vulnerability], alert_id: str | None
) -> NormalizedAlert:
    """Assemble a NormalizedAlert from a package's OSV vulns."""

    return NormalizedAlert(
        package=req.package,
        current_version=req.version,
        ecosystem=req.ecosystem,
        source="osv",
        vulnerable=bool(vulns),
        severity=max_severity([v.severity for v in vulns]),
        fixed_version=highest_version([v.fixed_version for v in vulns if v.fixed_version]),
        cve=next((v.cve for v in vulns if v.cve), None),
        vulnerabilities=vulns,
        alert_id=alert_id,
    )


async def normalize(
    req: ScanRequest,
    alert_id: str | None = None,
    *,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> NormalizedAlert:
    """Look one package up against OSV and build the normalized alert.

    `client` lets callers inject an httpx.AsyncClient (e.g. MockTransport in
    tests); otherwise the OSV client manages its own.
    """

    async with OSVClient(settings=settings, client=client) as osv:
        vulns = await osv.query(req)
    return _build(req, vulns, alert_id)


async def scan_many(
    reqs: list[ScanRequest],
    *,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[NormalizedAlert]:
    """Scan many packages over a single OSV connection (used by manifest scan)."""

    results: list[NormalizedAlert] = []
    async with OSVClient(settings=settings, client=client) as osv:
        for req in reqs:
            vulns = await osv.query(req)
            results.append(_build(req, vulns, alert_id=None))
    return results
