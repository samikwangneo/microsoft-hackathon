"""Map a patchpilot RunResult into the dashboard's DashboardPayload.

A run produces one remediation PR, so the dashboard shows a single PR row (with
its detail + a synthesized timeline). Validation is intentionally skipped, so
`validation_checks` is empty for now.
"""

from __future__ import annotations

import re

from patchpilot.models.notification import Notification
from patchpilot.models.results import RunResult

from ..dashboard.models import (
    AffectedPackage,
    DashboardPayload,
    DeltaStat,
    Kpis,
    PercentStat,
    PrDetail,
    PrSeverity,
    PrStatus,
    PullRequest,
    StepState,
    TextStat,
    TimelineStep,
    WhyThisPr,
)

_SEVERITY_RANK = {
    PrSeverity.LOW: 0,
    PrSeverity.MEDIUM: 1,
    PrSeverity.HIGH: 2,
    PrSeverity.CRITICAL: 3,
}
_AGENT_TO_PR_SEVERITY = {
    "critical": PrSeverity.CRITICAL,
    "high": PrSeverity.HIGH,
    "medium": PrSeverity.MEDIUM,
    "moderate": PrSeverity.MEDIUM,
    "low": PrSeverity.LOW,
    "unknown": PrSeverity.LOW,
}


def _max_severity(notification: Notification) -> PrSeverity:
    best = PrSeverity.LOW
    for pkg in notification.packages:
        for vuln in pkg.vulnerabilities:
            sev = _AGENT_TO_PR_SEVERITY.get(vuln.severity.lower(), PrSeverity.LOW)
            if _SEVERITY_RANK[sev] > _SEVERITY_RANK[best]:
                best = sev
    return best


def _pr_number(pr_url: str | None) -> int:
    if pr_url and (m := re.search(r"/pull/(\d+)", pr_url)):
        return int(m.group(1))
    return 1


def _timeline(result: RunResult | None) -> list[TimelineStep]:
    fixed = bool(result and any(f.success for p in result.packages for f in p.fixes))
    pr_open = bool(result and result.pr_url)
    emailed = bool(result and result.email_sent)
    done, current, pending = StepState.DONE, StepState.CURRENT, StepState.PENDING
    return [
        TimelineStep(label="Alert Received", timestamp="", sublabel="OSV scan", state=done),
        TimelineStep(label="Agent Analyzed", timestamp="", sublabel="Severity classified", state=done),
        TimelineStep(label="Fix Generated", timestamp="", sublabel="Patch applied",
                     state=done if fixed else current),
        TimelineStep(label="PR Opened", timestamp="", sublabel="Branch pushed",
                     state=done if pr_open else (pending if not fixed else current)),
        TimelineStep(label="Emailed" if emailed else "Awaiting Review", timestamp="",
                     sublabel="User notified" if emailed else "Pending",
                     state=done if emailed else (current if pr_open else pending)),
    ]


def build_dashboard_payload(
    result: RunResult | None,
    notification: Notification,
    repo_name: str,
) -> DashboardPayload:
    total_vulns = sum(len(p.vulnerabilities) for p in notification.packages)

    kpis = Kpis(
        alerts_matched=DeltaStat(value=total_vulns, delta_pct=0, caption="This run"),
        prs_generated=DeltaStat(
            value=1 if (result and result.pr_url) else 0, delta_pct=0, caption="This run"
        ),
        merge_rate=PercentStat(
            percent=100 if (result and result.success) else 0, caption="Fixes applied"
        ),
        median_alert_to_pr=TextStat(value="live", caption="Alert to PR open"),
    )

    pull_requests: list[PullRequest] = []
    if result and notification.packages:
        primary = notification.packages[0]
        first_vuln = primary.vulnerabilities[0] if primary.vulnerabilities else None
        change_summary = [
            f"{p.package_name}: {f.vulnerability_id} [{f.category.value}] "
            f"{'OK' if f.success else 'FAILED'}"
            for p in result.packages
            for f in p.fixes
        ] or [result.summary or "No changes recorded"]
        files_changed = sorted(
            {fc for p in result.packages for f in p.fixes for fc in f.files_changed}
        )
        pull_requests.append(
            PullRequest(
                id=_pr_number(result.pr_url),
                repo=repo_name,
                severity=_max_severity(notification),
                status=PrStatus.OPEN if result.pr_url else PrStatus.BLOCKED,
                assigned_to="patchpilot",
                created_relative="just now",
                package=AffectedPackage(
                    name=primary.name, spec=f"@{primary.installed_version}"
                ),
                detail=PrDetail(
                    branch=result.branch or "patchpilot/remediate",
                    why=WhyThisPr(
                        osv_id=first_vuln.id if first_vuln else "—",
                        cve=first_vuln.id if first_vuln else "",
                        text=(first_vuln.summary if first_vuln else "") or result.summary,
                    ),
                    change_summary=change_summary,
                    files_changed=files_changed,
                    validation_checks=[],  # validation intentionally skipped
                    pr_url=result.pr_url or "",
                ),
                timeline=_timeline(result),
            )
        )

    return DashboardPayload(
        kpis=kpis,
        total_prs=len(pull_requests),
        repos=[repo_name],
        pull_requests=pull_requests,
    )
