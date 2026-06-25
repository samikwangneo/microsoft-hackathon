"""Pydantic schemas for the intake pipeline.

`NormalizedAlert` is the contract the intake service hands off to the
downstream Summary Agent / Case Identifier. Keep it stable.

Input shapes intake accepts:
- `ScannerAlert`     — the simplified scanner JSON (docs/examples/sample-alert.json).
- `GitHubDependabotAlert` — a tolerant subset of a real GitHub Dependabot alert.
- `ScanRequest`      — the minimal {ecosystem, package, version} OSV query input.

Per the locked design, OSV.dev is the source of truth: the alert only supplies
package + ecosystem + installed version; OSV decides everything else.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Ecosystem(str, Enum):
    """Ecosystems supported behind the pluggable parser interface.

    Values match OSV.dev's ecosystem identifiers exactly (case-sensitive) so
    they can be passed straight through to the OSV query API.
    """

    NPM = "npm"
    PYPI = "PyPI"
    NUGET = "NuGet"


class Severity(str, Enum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    """Minimal input to look a package up against OSV."""

    ecosystem: Ecosystem
    package: str = Field(..., min_length=1, examples=["lodash"])
    version: str = Field(..., min_length=1, examples=["4.17.19"])


class ScannerAlert(BaseModel):
    """The simplified scanner shape used in docs/examples/sample-alert.json.

    Tolerant by design: a scanner may omit the fixed version (OSV backfills it)
    and may not know the precise ecosystem (defaults to npm for the MVP).
    """

    alert_id: str | None = None
    package: str = Field(..., min_length=1)
    installed_version: str = Field(..., min_length=1)
    fixed_version: str | None = None
    ecosystem: Ecosystem = Ecosystem.NPM
    severity: str | None = None
    source: str | None = None
    created_at: datetime | None = None


# --- GitHub Dependabot alert (tolerant subset of the real REST/webhook shape) ---


class GHPackage(BaseModel):
    ecosystem: str  # GitHub's lowercase id, e.g. "npm", "pip", "nuget"
    name: str


class GHDependency(BaseModel):
    package: GHPackage
    manifest_path: str | None = None
    scope: str | None = None


class GHFirstPatchedVersion(BaseModel):
    identifier: str | None = None


class GHSecurityVulnerability(BaseModel):
    package: GHPackage | None = None
    severity: str | None = None
    vulnerable_version_range: str | None = None
    first_patched_version: GHFirstPatchedVersion | None = None


class GHIdentifier(BaseModel):
    type: str | None = None
    value: str | None = None


class GHSecurityAdvisory(BaseModel):
    ghsa_id: str | None = None
    cve_id: str | None = None
    summary: str | None = None
    severity: str | None = None
    identifiers: list[GHIdentifier] = Field(default_factory=list)


class GitHubDependabotAlert(BaseModel):
    """Tolerant subset of a GitHub Dependabot alert.

    GitHub alerts do NOT carry the installed version, so the caller must supply
    `installed_version` (see the locked design decision).
    """

    number: int | None = None
    state: str | None = None
    html_url: str | None = None
    created_at: datetime | None = None
    dependency: GHDependency
    security_vulnerability: GHSecurityVulnerability | None = None
    security_advisory: GHSecurityAdvisory | None = None
    # Caller-supplied: not part of GitHub's payload.
    installed_version: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


class Vulnerability(BaseModel):
    """A single vulnerability record distilled from OSV."""

    id: str = Field(..., description="OSV id, e.g. GHSA-... or PYSEC-...")
    aliases: list[str] = Field(default_factory=list, description="CVE / other ids")
    summary: str | None = None
    details: str | None = None
    severity: Severity = Severity.UNKNOWN
    cvss_vector: str | None = None
    fixed_version: str | None = Field(
        None, description="First version that resolves this vuln, if known"
    )
    references: list[str] = Field(default_factory=list)

    @property
    def cve(self) -> str | None:
        return next((a for a in self.aliases if a.upper().startswith("CVE-")), None)


class NormalizedAlert(BaseModel):
    """Intake's output contract handed to downstream agents."""

    package: str
    current_version: str
    ecosystem: Ecosystem
    source: str = "osv"
    vulnerable: bool
    # Highest severity across all matched vulns — drives Case Identifier routing.
    severity: Severity = Severity.UNKNOWN
    # Suggested target version: the highest fixed_version seen across vulns.
    fixed_version: str | None = None
    cve: str | None = None
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    alert_id: str | None = None


# ---------------------------------------------------------------------------
# Manifest scanning (scan a whole repo's package.json)
# ---------------------------------------------------------------------------


class ManifestFile(BaseModel):
    """A raw dependency file to scan, identified by filename.

    `filename` selects the parser (package.json, requirements.txt, *.csproj,
    packages.config); `content` is the file's raw text.
    """

    filename: str = Field(..., examples=["package.json", "requirements.txt"])
    content: str


class PackageJson(BaseModel):
    """A tolerant npm package.json — only the bits intake needs."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str | None = None
    version: str | None = None
    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(
        default_factory=dict, alias="devDependencies"
    )


class SkippedDependency(BaseModel):
    """A dependency intake couldn't scan (e.g. a range/tag, not a pinned version)."""

    package: str
    version_spec: str
    reason: str


class ManifestScanResult(BaseModel):
    """Result of scanning every dependency in a manifest."""

    ecosystem: Ecosystem
    name: str | None = None
    scanned: int
    vulnerable_count: int
    results: list[NormalizedAlert] = Field(default_factory=list)
    skipped: list[SkippedDependency] = Field(default_factory=list)
