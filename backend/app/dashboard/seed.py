"""Mock dashboard data shaped exactly like the Sentinel Figma.

Replace `build_payload()` later with data assembled from real intake /
remediation / validation outputs — the schema in `models.py` stays the same.
"""

from __future__ import annotations

from .models import (
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
    ValidationCheck,
    WhyThisPr,
)


def _pkg_diff(pkg: str, old: str, new: str) -> str:
    """A minimal package.json version-bump diff, for demoing 'View Diff'."""
    return (
        "diff --git a/package.json b/package.json\n"
        "--- a/package.json\n"
        "+++ b/package.json\n"
        "@@ -14,7 +14,7 @@\n"
        '   "dependencies": {\n'
        f'-    "{pkg}": "^{old}",\n'
        f'+    "{pkg}": "^{new}",\n'
        '     "react": "^18.2.0"\n'
        "   }\n"
    )


def _timeline(opened_done: bool, final: tuple[str, str, str, StepState]) -> list[TimelineStep]:
    """Standard 5-step pipeline timeline; the last step varies per PR status."""

    steps = [
        TimelineStep(label="Alert Received", timestamp="2026-06-24 09:14",
                     sublabel="OSV-2026-1142 detected", state=StepState.DONE),
        TimelineStep(label="Agent Analyzed", timestamp="09:14:12",
                     sublabel="Severity classified", state=StepState.DONE),
        TimelineStep(label="Fix Generated", timestamp="09:15:03",
                     sublabel="Patch strategy computed", state=StepState.DONE),
        TimelineStep(label="PR Opened", timestamp="09:16:22",
                     sublabel="PR created",
                     state=StepState.DONE if opened_done else StepState.CURRENT),
        TimelineStep(label=final[0], timestamp=final[1], sublabel=final[2], state=final[3]),
    ]
    return steps


PULL_REQUESTS: list[PullRequest] = [
    PullRequest(
        id=482, repo="web-checkout-service", severity=PrSeverity.HIGH,
        status=PrStatus.OPEN, assigned_to="j.smith", created_relative="2h ago",
        package=AffectedPackage(name="lodash", spec="<4.17.22"),
        detail=PrDetail(
            branch="web-checkout-service",
            why=WhyThisPr(
                osv_id="OSV-2026-1142", cve="CVE-2026-19841",
                text=("Lodash prototype pollution vulnerability allows malicious "
                      "input to override Object.prototype properties. Severity: "
                      "High. CVE: CVE-2026-19841."),
            ),
            change_summary=[
                "lodash 4.17.19 → 4.17.22",
                "lockfile regenerated",
                "security notes updated",
                "regression test added",
            ],
            files_changed=["package.json", "package-lock.json", "SECURITY.md", "lodash.test.js"],
            validation_checks=[
                ValidationCheck(label="CI/CD Pipeline", status="Passed", ok=True),
                ValidationCheck(label="No new vulns", status="Passed", ok=True),
            ],
            pr_url="https://github.com/acme/web-checkout-service/pull/482",
            diff=_pkg_diff("lodash", "4.17.19", "4.17.22"),
        ),
        timeline=_timeline(True, ("Awaiting Review", "Now", "1 reviewer pending", StepState.CURRENT)),
    ),
    PullRequest(
        id=481, repo="api-gateway", severity=PrSeverity.MEDIUM,
        status=PrStatus.MERGED, assigned_to="a.lee", created_relative="5h ago",
        package=AffectedPackage(name="axios", spec="<1.6.8"),
        detail=PrDetail(
            branch="api-gateway",
            why=WhyThisPr(
                osv_id="OSV-2026-0931", cve="CVE-2026-18112",
                text=("Axios follows cross-site redirects and can leak the "
                      "Authorization header to a third-party host. Severity: Medium."),
            ),
            change_summary=["axios 1.6.2 → 1.6.8", "lockfile regenerated", "security notes updated"],
            files_changed=["package.json", "package-lock.json"],
            validation_checks=[
                ValidationCheck(label="CI/CD Pipeline", status="Passed", ok=True),
                ValidationCheck(label="No new vulns", status="Passed", ok=True),
            ],
            pr_url="https://github.com/acme/api-gateway/pull/481",
            diff=_pkg_diff("axios", "1.6.2", "1.6.8"),
        ),
        timeline=_timeline(True, ("Merged", "5h ago", "Merged by a.lee", StepState.DONE)),
    ),
    PullRequest(
        id=480, repo="auth-service", severity=PrSeverity.CRITICAL,
        status=PrStatus.BLOCKED, assigned_to="m.nguyen", created_relative="1d ago",
        package=AffectedPackage(name="express", spec="<4.19.2"),
        detail=PrDetail(
            branch="auth-service",
            why=WhyThisPr(
                osv_id="OSV-2026-0455", cve="CVE-2026-15901",
                text=("Express is vulnerable to an open redirect via malformed URLs "
                      "in the location header. Severity: Critical."),
            ),
            change_summary=["express 4.18.2 → 4.19.2", "breaking change in router middleware"],
            files_changed=["package.json", "package-lock.json", "src/router.js"],
            validation_checks=[
                ValidationCheck(label="CI/CD Pipeline", status="Failed", ok=False),
                ValidationCheck(label="No new vulns", status="Passed", ok=True),
            ],
            pr_url="https://github.com/acme/auth-service/pull/480",
            diff=_pkg_diff("express", "4.18.2", "4.19.2"),
        ),
        timeline=_timeline(True, ("Blocked", "1d ago", "CI failed — needs code change", StepState.CURRENT)),
    ),
    PullRequest(
        id=479, repo="data-pipeline", severity=PrSeverity.LOW,
        status=PrStatus.MERGED, assigned_to="k.patel", created_relative="2d ago",
        package=AffectedPackage(name="json5", spec="<2.2.3"),
        detail=PrDetail(
            branch="data-pipeline",
            why=WhyThisPr(
                osv_id="OSV-2026-0210", cve="CVE-2022-46175",
                text=("json5 parse is vulnerable to prototype pollution via crafted "
                      "input. Severity: Low."),
            ),
            change_summary=["json5 2.2.1 → 2.2.3", "lockfile regenerated"],
            files_changed=["package.json", "package-lock.json"],
            validation_checks=[
                ValidationCheck(label="CI/CD Pipeline", status="Passed", ok=True),
                ValidationCheck(label="No new vulns", status="Passed", ok=True),
            ],
            pr_url="https://github.com/acme/data-pipeline/pull/479",
            diff=_pkg_diff("json5", "2.2.1", "2.2.3"),
        ),
        timeline=_timeline(True, ("Merged", "2d ago", "Merged by k.patel", StepState.DONE)),
    ),
    PullRequest(
        id=478, repo="web-checkout-service", severity=PrSeverity.HIGH,
        status=PrStatus.OPEN, assigned_to="j.smith", created_relative="2d ago",
        package=AffectedPackage(name="semver", spec="<7.5.2"),
        detail=PrDetail(
            branch="web-checkout-service",
            why=WhyThisPr(
                osv_id="OSV-2026-0188", cve="CVE-2022-25883",
                text=("semver is vulnerable to ReDoS through the range parser. "
                      "Severity: High."),
            ),
            change_summary=["semver 7.5.1 → 7.5.2", "lockfile regenerated", "regression test added"],
            files_changed=["package.json", "package-lock.json", "semver.test.js"],
            validation_checks=[
                ValidationCheck(label="CI/CD Pipeline", status="Passed", ok=True),
                ValidationCheck(label="No new vulns", status="Passed", ok=True),
            ],
            pr_url="https://github.com/acme/web-checkout-service/pull/478",
            diff=_pkg_diff("semver", "7.5.1", "7.5.2"),
        ),
        timeline=_timeline(True, ("Awaiting Review", "Now", "2 reviewers pending", StepState.CURRENT)),
    ),
    PullRequest(
        id=477, repo="ml-inference", severity=PrSeverity.MEDIUM,
        status=PrStatus.OPEN, assigned_to="r.chen", created_relative="3d ago",
        package=AffectedPackage(name="tough-cookie", spec="<4.1.3"),
        detail=PrDetail(
            branch="ml-inference",
            why=WhyThisPr(
                osv_id="OSV-2026-0099", cve="CVE-2023-26136",
                text=("tough-cookie is vulnerable to prototype pollution in cookie "
                      "memstore. Severity: Medium."),
            ),
            change_summary=["tough-cookie 4.1.2 → 4.1.3", "lockfile regenerated"],
            files_changed=["package.json", "package-lock.json"],
            validation_checks=[
                ValidationCheck(label="CI/CD Pipeline", status="Passed", ok=True),
                ValidationCheck(label="No new vulns", status="Passed", ok=True),
            ],
            pr_url="https://github.com/acme/ml-inference/pull/477",
            diff=_pkg_diff("tough-cookie", "4.1.2", "4.1.3"),
        ),
        timeline=_timeline(True, ("Awaiting Review", "Now", "1 reviewer pending", StepState.CURRENT)),
    ),
]


def build_payload() -> DashboardPayload:
    repos = sorted({pr.repo for pr in PULL_REQUESTS})
    return DashboardPayload(
        kpis=Kpis(
            alerts_matched=DeltaStat(value=47, delta_pct=12, caption="This week"),
            prs_generated=DeltaStat(value=31, delta_pct=8, caption="Auto-created"),
            merge_rate=PercentStat(percent=68, caption="Of generated PRs"),
            median_alert_to_pr=TextStat(value="4.2 min", caption="Alert to PR open"),
        ),
        total_prs=31,
        repos=repos,
        pull_requests=PULL_REQUESTS,
    )
