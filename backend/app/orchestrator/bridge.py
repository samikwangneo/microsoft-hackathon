"""Convert intake's normalized output into the agents' Notification input.

Intake (OSV) produces `ManifestScanResult` / `NormalizedAlert`; the patchpilot
agents consume a `Notification`. This module is the single seam between the two,
including the ecosystem-id translation (OSV → agent install commands).
"""

from __future__ import annotations

from pathlib import Path

from patchpilot.models.notification import Notification, Package
from patchpilot.models.notification import Vulnerability as AgentVuln

from ..models import Ecosystem, ManifestScanResult, NormalizedAlert, Severity

# OSV ecosystem id → the id the agents' install/upgrade commands understand.
# Agents support pip / npm / yarn only; NuGet has no agent install path yet.
_ECOSYSTEM_TO_AGENT: dict[Ecosystem, str] = {
    Ecosystem.NPM: "npm",
    Ecosystem.PYPI: "pip",
}

# Intake severity enum → the lowercase labels the agent prompts expect.
_SEVERITY_TO_AGENT: dict[Severity, str] = {
    Severity.CRITICAL: "critical",
    Severity.HIGH: "high",
    Severity.MODERATE: "medium",
    Severity.LOW: "low",
    Severity.UNKNOWN: "unknown",
}


class UnsupportedEcosystemError(ValueError):
    """Raised when a scanned ecosystem has no agent remediation path (e.g. NuGet)."""


def _alert_to_package(alert: NormalizedAlert) -> Package:
    agent_ecosystem = _ECOSYSTEM_TO_AGENT.get(alert.ecosystem)
    if agent_ecosystem is None:
        raise UnsupportedEcosystemError(
            f"{alert.ecosystem.value} has no agent remediation path "
            f"(supported: {', '.join(sorted(_ECOSYSTEM_TO_AGENT.values()))})"
        )
    vulns = [
        AgentVuln(
            id=v.id,
            severity=_SEVERITY_TO_AGENT.get(v.severity, "unknown"),
            summary=v.summary or "",
            details=v.details or "",
            fixed_version=v.fixed_version,
            references=v.references,
        )
        for v in alert.vulnerabilities
    ]
    return Package(
        name=alert.package,
        installed_version=alert.current_version,
        ecosystem=agent_ecosystem,
        vulnerabilities=vulns,
    )


def to_notification(
    scan: ManifestScanResult,
    *,
    repo_path: Path | str,
    package_source_file: str,
    user_email: str | None = None,
) -> Notification:
    """Build a `Notification` from a manifest scan (only vulnerable packages)."""

    packages = [
        _alert_to_package(alert) for alert in scan.results if alert.vulnerable
    ]
    return Notification(
        repo_path=Path(repo_path),
        package_source_file=package_source_file,
        packages=packages,
        user_email=user_email,
    )
