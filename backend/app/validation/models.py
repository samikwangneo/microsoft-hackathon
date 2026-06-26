"""Pydantic schemas for the validation service.

`ValidationReport` is the contract the validation service hands downstream (Git
Automation / the dashboard). It is a **superset** of
`contracts/validation_output.json` — it keeps that file's keys (`alert_id`,
`passed`, `tests_run`, `notes`) and adds a per-check `checks` list for the
dashboard's "Validation Checks" panel. Keep it backward-compatible.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import Ecosystem  # reuse intake's enum — values match OSV ids


class ValidationRequest(BaseModel):
    """Input: what the Remediation Engine hands us after bumping a version.

    `repository` is a path to a local checkout to build/test; when absent, the
    build/test checks are skipped and only the (repo-free) security re-scan runs.
    """

    alert_id: str | None = None
    ecosystem: Ecosystem = Ecosystem.NPM
    package: str = Field(..., min_length=1, examples=["lodash"])
    updated_version: str = Field(
        ..., min_length=1, description="Version the remediation upgraded TO"
    )
    previous_version: str | None = Field(
        None, description="Version upgraded FROM, for regression context"
    )
    repository: str | None = Field(
        None, description="Local checkout path to build/test; build skipped if absent"
    )


class CheckResult(BaseModel):
    """One validation check's outcome (security_scan, build, tests, ...)."""

    name: str = Field(..., examples=["security_scan", "build", "tests"])
    passed: bool
    details: str | None = None


class ValidationReport(BaseModel):
    """Validation's output contract. Superset of contracts/validation_output.json."""

    alert_id: str | None = None
    # Overall verdict — the AND of every check's `passed`.
    passed: bool
    tests_run: int = 0
    checks: list[CheckResult] = Field(default_factory=list)
    notes: str = ""
