"""Security re-scan: confirm the upgraded version is clean per OSV.

This is the repo-free half of validation. After the Remediation Engine bumps a
dependency, we re-query OSV (reusing the intake service) for the *upgraded*
version and pass only if OSV reports it not vulnerable — i.e. the fix actually
resolved the vuln and introduced no known new one.
"""

from __future__ import annotations

import httpx

from ..config import Settings
from ..intake.service import normalize
from ..models import ScanRequest
from .models import CheckResult, ValidationRequest


async def security_rescan(
    req: ValidationRequest,
    *,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> CheckResult:
    """Re-scan req.package@req.updated_version against OSV; pass if clean.

    `client` lets callers inject an httpx.AsyncClient (e.g. MockTransport in
    tests); it is threaded straight through to the intake service.
    """

    scan = ScanRequest(
        ecosystem=req.ecosystem, package=req.package, version=req.updated_version
    )
    result = await normalize(scan, settings=settings, client=client)

    target = f"{req.package}@{req.updated_version}"
    if result.vulnerable:
        details = (
            f"{target} still vulnerable "
            f"(severity={result.severity.value}, fix={result.fixed_version})"
        )
    else:
        details = f"{target} clean per OSV"
    return CheckResult(name="security_scan", passed=not result.vulnerable, details=details)
