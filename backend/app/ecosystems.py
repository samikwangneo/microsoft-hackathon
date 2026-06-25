"""Ecosystem mapping and severity / version helpers.

GitHub Dependabot alerts use lowercase ecosystem ids (`npm`, `pip`, `nuget`)
that differ from OSV.dev's case-sensitive ids (`npm`, `PyPI`, `NuGet`). The
intake parsers translate via `github_to_osv`.
"""

from __future__ import annotations

import re

from .models import Ecosystem, Severity

# GitHub Dependabot ecosystem id -> OSV ecosystem. MVP covers three; others
# raise so we fail loudly rather than silently mis-route a vuln lookup.
_GITHUB_TO_OSV: dict[str, Ecosystem] = {
    "npm": Ecosystem.NPM,
    "pip": Ecosystem.PYPI,
    "nuget": Ecosystem.NUGET,
}


def github_to_osv(github_ecosystem: str) -> Ecosystem:
    """Map a GitHub ecosystem id to its OSV equivalent.

    Raises ValueError for ecosystems outside the MVP scope.
    """

    key = (github_ecosystem or "").strip().lower()
    try:
        return _GITHUB_TO_OSV[key]
    except KeyError:
        supported = ", ".join(sorted(_GITHUB_TO_OSV))
        raise ValueError(
            f"Unsupported GitHub ecosystem {github_ecosystem!r}; "
            f"MVP supports: {supported}"
        ) from None


# Ordered weakest -> strongest, for ranking and aggregation.
_SEVERITY_ORDER: list[Severity] = [
    Severity.UNKNOWN,
    Severity.LOW,
    Severity.MODERATE,
    Severity.HIGH,
    Severity.CRITICAL,
]
_SEVERITY_RANK = {s: i for i, s in enumerate(_SEVERITY_ORDER)}

# Normalize the various labels OSV / GitHub use to our enum. GitHub uses
# "moderate"; some sources use "medium".
_SEVERITY_ALIASES: dict[str, Severity] = {
    "low": Severity.LOW,
    "moderate": Severity.MODERATE,
    "medium": Severity.MODERATE,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


def parse_severity_label(label: str | None) -> Severity:
    """Coerce a free-form severity label into the Severity enum."""

    if not label:
        return Severity.UNKNOWN
    return _SEVERITY_ALIASES.get(label.strip().lower(), Severity.UNKNOWN)


def max_severity(severities: list[Severity]) -> Severity:
    """Return the strongest severity in the list (UNKNOWN if empty)."""

    if not severities:
        return Severity.UNKNOWN
    return max(severities, key=lambda s: _SEVERITY_RANK[s])


# CVSS base-score -> qualitative bucket (CVSS v3.x rating scale), used as a
# fallback when no textual severity label is present.
def severity_from_cvss_score(score: float | None) -> Severity:
    if score is None:
        return Severity.UNKNOWN
    if score >= 9.0:
        return Severity.CRITICAL
    if score >= 7.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MODERATE
    if score > 0.0:
        return Severity.LOW
    return Severity.UNKNOWN


_VERSION_PART = re.compile(r"\d+|[a-zA-Z]+")


def _version_key(version: str) -> tuple:
    """A best-effort comparable key for ordering version strings.

    Not a full SemVer implementation — splits into numeric and alpha runs so
    that e.g. 4.17.21 > 4.17.9. Good enough to pick the highest `fixed` event.
    """

    parts = _VERSION_PART.findall(version or "")
    key: list[tuple[int, int, str]] = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p), ""))  # numeric sorts before alpha
        else:
            key.append((1, 0, p))
    return tuple(key)


def highest_version(versions: list[str]) -> str | None:
    """Return the highest version from a list, or None if empty."""

    candidates = [v for v in versions if v]
    if not candidates:
        return None
    return max(candidates, key=_version_key)
