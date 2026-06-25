"""Schemas for the dashboard payload (mirrors frontend/src/types.ts)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PrSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PrStatus(str, Enum):
    OPEN = "OPEN"
    MERGED = "MERGED"
    BLOCKED = "BLOCKED"


class StepState(str, Enum):
    DONE = "done"
    CURRENT = "current"
    PENDING = "pending"


# --- KPI cards -------------------------------------------------------------


class DeltaStat(BaseModel):
    value: int
    delta_pct: int
    caption: str


class PercentStat(BaseModel):
    percent: int
    caption: str


class TextStat(BaseModel):
    value: str
    caption: str


class Kpis(BaseModel):
    alerts_matched: DeltaStat
    prs_generated: DeltaStat
    merge_rate: PercentStat
    median_alert_to_pr: TextStat


# --- Pull request + detail -------------------------------------------------


class AffectedPackage(BaseModel):
    name: str
    spec: str  # e.g. "<4.17.22"


class WhyThisPr(BaseModel):
    osv_id: str
    cve: str
    text: str


class ValidationCheck(BaseModel):
    label: str
    status: str  # e.g. "Passed"
    ok: bool = True


class PrDetail(BaseModel):
    branch: str
    why: WhyThisPr
    change_summary: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    validation_checks: list[ValidationCheck] = Field(default_factory=list)
    pr_url: str


class TimelineStep(BaseModel):
    label: str
    timestamp: str
    sublabel: str
    state: StepState


class PullRequest(BaseModel):
    id: int
    repo: str
    severity: PrSeverity
    status: PrStatus
    assigned_to: str
    created_relative: str
    package: AffectedPackage
    detail: PrDetail
    timeline: list[TimelineStep] = Field(default_factory=list)


# --- Top-level payload -----------------------------------------------------


class DashboardPayload(BaseModel):
    kpis: Kpis
    total_prs: int
    repos: list[str] = Field(default_factory=list)
    pull_requests: list[PullRequest] = Field(default_factory=list)
