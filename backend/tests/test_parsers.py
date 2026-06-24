"""Unit tests for input parsing and ecosystem mapping (no network)."""

import json
from pathlib import Path

import pytest

from app.ecosystems import github_to_osv, highest_version, max_severity
from app.intake import parsers
from app.models import (
    Ecosystem,
    GitHubDependabotAlert,
    ScannerAlert,
    Severity,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_github_to_osv_mapping():
    assert github_to_osv("npm") is Ecosystem.NPM
    assert github_to_osv("pip") is Ecosystem.PYPI
    assert github_to_osv("nuget") is Ecosystem.NUGET
    assert github_to_osv("NuGet") is Ecosystem.NUGET  # case-insensitive input


def test_github_to_osv_unsupported_raises():
    with pytest.raises(ValueError):
        github_to_osv("maven")


def test_scanner_alert_parses_to_scan_request():
    alert = ScannerAlert(
        alert_id="ALERT-2026-0001",
        package="lodash",
        installed_version="4.17.19",
        fixed_version="4.17.21",
    )
    req, alert_id = parsers.from_scanner_alert(alert)
    assert req.ecosystem is Ecosystem.NPM
    assert req.package == "lodash"
    assert req.version == "4.17.19"
    assert alert_id == "ALERT-2026-0001"


def test_github_alert_parses_with_supplied_version():
    raw = json.loads((FIXTURES / "github_alert.json").read_text())
    alert = GitHubDependabotAlert.model_validate(raw)
    req, alert_id = parsers.from_github_alert(alert)
    assert req.ecosystem is Ecosystem.NPM
    assert req.package == "lodash"
    assert req.version == "4.17.19"  # the caller-supplied installed_version
    assert alert_id == "GHSA-jf85-cpcp-j695"


def test_max_severity_picks_strongest():
    assert max_severity([Severity.LOW, Severity.CRITICAL, Severity.HIGH]) is Severity.CRITICAL
    assert max_severity([]) is Severity.UNKNOWN


def test_highest_version_orders_numerically():
    assert highest_version(["4.17.9", "4.17.21", "4.17.10"]) == "4.17.21"
    assert highest_version([]) is None
