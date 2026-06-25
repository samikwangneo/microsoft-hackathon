"""Async OSV.dev client and vulnerability distillation.

OSV is the source of truth: given an ecosystem + package + version we POST to
`/v1/query` and turn each raw vuln into a tidy `Vulnerability`.

Request shape (note: version must NOT also appear inside `package`):
    {"version": "<v>", "package": {"name": "<n>", "ecosystem": "<eco>"}}
"""

from __future__ import annotations

import httpx

from ..config import Settings, get_settings
from ..ecosystems import (
    highest_version,
    parse_severity_label,
    severity_from_cvss_score,
)
from ..models import ScanRequest, Severity, Vulnerability


def _cvss_base_score(vector: str) -> float | None:
    """Extract the base score if embedded, else None.

    OSV stores CVSS as a vector string (no numeric score), so there is usually
    nothing to extract — severity then comes from the textual label. Kept as a
    hook for sources that prepend a score.
    """

    # Vectors don't carry a numeric base score; return None so callers fall
    # back to the textual severity label.
    return None


def _pick_cvss(severity_entries: list[dict]) -> str | None:
    """Prefer a CVSS v4 vector, else v3, else the first entry's score string."""

    by_type = {e.get("type"): e.get("score") for e in severity_entries or []}
    return by_type.get("CVSS_V4") or by_type.get("CVSS_V3") or (
        severity_entries[0].get("score") if severity_entries else None
    )


def _fixed_version_for(vuln: dict, req: ScanRequest) -> str | None:
    """Highest `fixed` version across affected ranges matching this package."""

    fixed: list[str] = []
    for affected in vuln.get("affected", []):
        pkg = affected.get("package", {})
        if pkg.get("name") != req.package:
            continue
        if pkg.get("ecosystem") and pkg.get("ecosystem") != req.ecosystem.value:
            continue
        for rng in affected.get("ranges", []):
            # Skip GIT ranges — their "fixed" is a commit hash, not a version.
            if rng.get("type") == "GIT":
                continue
            for event in rng.get("events", []):
                if "fixed" in event:
                    fixed.append(event["fixed"])
    return highest_version(fixed)


def _severity_for(vuln: dict) -> Severity:
    """Derive a qualitative severity, preferring textual labels over CVSS."""

    # GitHub-reviewed advisories expose a label here.
    label = (vuln.get("database_specific") or {}).get("severity")
    if not label:
        for affected in vuln.get("affected", []):
            label = (affected.get("ecosystem_specific") or {}).get("severity")
            if label:
                break
    sev = parse_severity_label(label)
    if sev is not Severity.UNKNOWN:
        return sev
    # Fallback: derive from a CVSS score if one is available.
    cvss = _pick_cvss(vuln.get("severity", []))
    return severity_from_cvss_score(_cvss_base_score(cvss) if cvss else None)


def distill(vuln: dict, req: ScanRequest) -> Vulnerability:
    """Turn a raw OSV vuln object into our `Vulnerability` schema."""

    references = [
        r["url"] for r in vuln.get("references", []) if isinstance(r, dict) and r.get("url")
    ]
    return Vulnerability(
        id=vuln.get("id", "UNKNOWN"),
        aliases=vuln.get("aliases", []) or [],
        summary=vuln.get("summary"),
        details=vuln.get("details"),
        severity=_severity_for(vuln),
        cvss_vector=_pick_cvss(vuln.get("severity", [])),
        fixed_version=_fixed_version_for(vuln, req),
        references=references,
    )


class OSVClient:
    """Thin async wrapper over the OSV REST API.

    Pass a preconfigured `httpx.AsyncClient` for tests (e.g. MockTransport).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "OSVClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._settings.http_timeout)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def query(self, req: ScanRequest) -> list[Vulnerability]:
        """Query OSV for a single package@version and return distilled vulns."""

        assert self._client is not None, "use OSVClient as an async context manager"
        url = f"{self._settings.osv_api_base.rstrip('/')}/v1/query"
        payload = {
            "version": req.version,
            "package": {"name": req.package, "ecosystem": req.ecosystem.value},
        }
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [distill(v, req) for v in data.get("vulns", []) or []]
