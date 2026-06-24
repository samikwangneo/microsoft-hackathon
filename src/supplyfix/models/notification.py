"""Input models — the vulnerability notification fed to the summary agent.

A notification describes a single repository whose one package-source file
(e.g. requirements.txt or package.json) declares one or more packages, each of
which may carry one or more vulnerabilities. This mirrors the shape of a real
dependency-scanner / GitHub Dependabot / OSV alert digest, but is provided as a
plain JSON file so the system can run without wiring up a live alert source.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class Vulnerability(BaseModel):
    """A single reported vulnerability against one package."""

    id: str = Field(description="Advisory identifier, e.g. CVE-2021-23337 or GHSA-xxxx")
    severity: str = "unknown"  # critical | high | medium | low | unknown
    summary: str = ""
    details: str = ""
    # The version that resolves the issue, if the scanner suggests one. May be
    # absent (Category 3 — no fix available, requiring a downgrade decision).
    fixed_version: str | None = None
    references: list[str] = Field(default_factory=list)


class Package(BaseModel):
    """A vulnerable package declared in the repository's package-source file."""

    name: str
    installed_version: str
    # Package ecosystem; drives which install/upgrade commands the agents use.
    ecosystem: str = "pip"  # pip | npm | yarn
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)


class Notification(BaseModel):
    """The full notification for one repository."""

    repo_path: Path = Field(description="Absolute path to the local checkout to remediate")
    package_source_file: str = Field(
        description="Path to the package-source file, relative to repo_path "
        "(e.g. requirements.txt, package.json)"
    )
    packages: list[Package] = Field(default_factory=list)
    # Optional fallback address; the CLI --email flag takes precedence.
    user_email: str | None = None
