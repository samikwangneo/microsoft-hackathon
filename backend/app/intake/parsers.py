"""Translate the accepted input formats into a uniform `ScanRequest`.

Both the simplified scanner alert and the GitHub Dependabot alert collapse to
the same `(ScanRequest, alert_id)` pair the service needs to query OSV.
"""

from __future__ import annotations

from ..ecosystems import github_to_osv
from ..models import GitHubDependabotAlert, ScannerAlert, ScanRequest


def from_scanner_alert(alert: ScannerAlert) -> tuple[ScanRequest, str | None]:
    """Map the simplified scanner JSON (sample-alert.json) to a ScanRequest."""

    req = ScanRequest(
        ecosystem=alert.ecosystem,
        package=alert.package,
        version=alert.installed_version,
    )
    return req, alert.alert_id


def from_github_alert(alert: GitHubDependabotAlert) -> tuple[ScanRequest, str | None]:
    """Map a GitHub Dependabot alert to a ScanRequest.

    Uses the caller-supplied `installed_version` (GitHub omits it) and maps the
    lowercase GitHub ecosystem id to OSV's.
    """

    ecosystem = github_to_osv(alert.dependency.package.ecosystem)
    req = ScanRequest(
        ecosystem=ecosystem,
        package=alert.dependency.package.name,
        version=alert.installed_version,
    )
    alert_id = alert.security_advisory.ghsa_id if alert.security_advisory else None
    if alert_id is None and alert.number is not None:
        alert_id = f"GH-{alert.number}"
    return req, alert_id
