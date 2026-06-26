"""Unit tests for the intake -> Notification bridge (no network)."""

import pytest

from app.models import (
    Ecosystem,
    ManifestScanResult,
    NormalizedAlert,
    Severity,
    Vulnerability,
)
from app.orchestrator import bridge


def _alert(pkg: str, version: str, ecosystem: Ecosystem, vulns: list[Vulnerability]):
    return NormalizedAlert(
        package=pkg,
        current_version=version,
        ecosystem=ecosystem,
        vulnerable=bool(vulns),
        severity=max((v.severity for v in vulns), default=Severity.UNKNOWN),
        vulnerabilities=vulns,
    )


def _scan(results: list[NormalizedAlert], ecosystem: Ecosystem) -> ManifestScanResult:
    return ManifestScanResult(
        ecosystem=ecosystem,
        name="package.json",
        scanned=len(results),
        vulnerable_count=sum(1 for r in results if r.vulnerable),
        results=results,
    )


def test_npm_scan_maps_to_notification():
    vuln = Vulnerability(
        id="CVE-2020-8203", aliases=["CVE-2020-8203"], summary="Prototype pollution",
        severity=Severity.HIGH, fixed_version="4.17.21",
    )
    scan = _scan([_alert("lodash", "4.17.19", Ecosystem.NPM, [vuln])], Ecosystem.NPM)

    notif = bridge.to_notification(
        scan, repo_path="/tmp/repo", package_source_file="package.json", user_email="x@y.com"
    )

    assert str(notif.repo_path).endswith("repo")
    assert notif.user_email == "x@y.com"
    assert len(notif.packages) == 1
    pkg = notif.packages[0]
    assert (pkg.name, pkg.installed_version, pkg.ecosystem) == ("lodash", "4.17.19", "npm")
    assert pkg.vulnerabilities[0].id == "CVE-2020-8203"
    assert pkg.vulnerabilities[0].severity == "high"
    assert pkg.vulnerabilities[0].fixed_version == "4.17.21"


def test_pypi_maps_to_pip_and_moderate_to_medium():
    vuln = Vulnerability(id="GHSA-x", severity=Severity.MODERATE, summary="s")
    scan = _scan([_alert("jinja2", "2.10", Ecosystem.PYPI, [vuln])], Ecosystem.PYPI)
    notif = bridge.to_notification(scan, repo_path="/r", package_source_file="requirements.txt")
    assert notif.packages[0].ecosystem == "pip"
    assert notif.packages[0].vulnerabilities[0].severity == "medium"


def test_clean_packages_are_excluded():
    clean = _alert("safe-pkg", "1.0.0", Ecosystem.NPM, [])
    scan = _scan([clean], Ecosystem.NPM)
    notif = bridge.to_notification(scan, repo_path="/r", package_source_file="package.json")
    assert notif.packages == []


def test_nuget_is_unsupported():
    vuln = Vulnerability(id="CVE-x", severity=Severity.HIGH)
    scan = _scan([_alert("Newtonsoft.Json", "12.0.3", Ecosystem.NUGET, [vuln])], Ecosystem.NUGET)
    with pytest.raises(bridge.UnsupportedEcosystemError):
        bridge.to_notification(scan, repo_path="/r", package_source_file="x.csproj")
