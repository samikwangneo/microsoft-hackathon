"""Output models — what each agent tier returns up the chain."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FixCategory(str, Enum):
    """How a vulnerability is remediated. Decided by the package agent."""

    # Category 1: bump to a fixed version; usually just a package-source edit
    # plus an install/upgrade. No project code changes required.
    UPGRADE = "upgrade"

    # Category 2: bump to a fixed version AND adapt project code to the new
    # (often breaking) library API. The most involved category.
    UPGRADE_WITH_CODE = "upgrade_with_code"

    # Category 3: no fix is available upstream, so pin/downgrade to the safest
    # known-good version to remove the vulnerable code path.
    DOWNGRADE = "downgrade"


class VulnFixResult(BaseModel):
    """Result of one vulnerability agent fixing one vulnerability."""

    vulnerability_id: str
    category: FixCategory
    success: bool
    summary: str = Field(description="Human-readable description of what was changed")
    commit_sha: str | None = None
    files_changed: list[str] = Field(default_factory=list)
    error: str | None = None


class PackageResult(BaseModel):
    """Aggregated result of remediating one package's vulnerabilities."""

    package_name: str
    success: bool
    summary: str = ""
    fixes: list[VulnFixResult] = Field(default_factory=list)


class RunResult(BaseModel):
    """Top-level result returned by the summary agent / orchestrator."""

    branch: str | None = None
    success: bool = False
    summary: str = ""
    packages: list[PackageResult] = Field(default_factory=list)
    pr_url: str | None = None
    email_sent: bool = False
    error: str | None = None
