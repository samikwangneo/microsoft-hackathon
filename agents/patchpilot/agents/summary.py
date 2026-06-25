"""Summary agent — the top tier, one per notification.

Responsibilities:
  1. Summarise the incoming vulnerability notification.
  2. Cut a new branch in the target repository.
  3. Dispatch a package agent per vulnerable package.
  4. Once every package is handled, open a pull request and email the user a
     summary of the changes and the PR.

It is the only tier that touches the repository's branch/PR lifecycle and the
outside world (email), keeping those side effects in one place.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext

from patchpilot.config import settings
from patchpilot.models.notification import Notification
from patchpilot.models.results import PackageResult, RunResult
from patchpilot.runner import AgentRunner
from patchpilot.tools import email as email_tool
from patchpilot.tools import git

_SYSTEM_PROMPT = """\
You are PatchPilot, the orchestrator for an automated supply-chain remediation
system. You receive a notification describing vulnerable packages in one
repository and drive the whole fix-and-PR workflow. When you write the PR and
the user email, refer to yourself as PatchPilot.

Workflow (do these in order):
1. Write a short situational summary of the notification (severities, packages,
   how many vulnerabilities).
2. Call create_branch once to create the remediation branch. The branch name is
   generated for you automatically, so you do not need to supply one.
3. Call fix_package once for EACH vulnerable package. Each call dispatches a
   package agent that classifies and fixes that package's vulnerabilities and
   commits them. Do this for every package before moving on.
4. After all packages are handled, call open_pr with a clear title and a body
   that summarises every fix (package, vulnerability, category, commit).
5. Call notify_user to email the requesting user a summary including the PR link.
6. Return a RunResult capturing the branch, PR URL, per-package results, and
   whether the email was sent.

Respect the `[turn-budget]` reminders. Do not skip the branch step before
fixing, and do not open the PR before all packages are fixed.
"""


@dataclass
class SummaryDeps:
    notification: Notification
    user_email: str
    base_branch: str
    branch: str | None = None
    package_results: list[PackageResult] = field(default_factory=list)
    pr_url: str | None = None
    email_sent: bool = False


summary_agent = Agent(
    model=settings.summary,
    deps_type=SummaryDeps,
    output_type=RunResult,
    system_prompt=_SYSTEM_PROMPT,
)
_runner = AgentRunner("summary", summary_agent, settings.max_summary_requests)


@summary_agent.tool
async def create_branch(ctx: RunContext[SummaryDeps], branch_name: str = "") -> str:
    """Create and switch to a remediation branch in the target repository.

    The branch name is generated deterministically (patchpilot/remediate-<UTC
    timestamp>); any name suggested by the model is ignored so branch names are
    always correctly dated and collision-free.
    """
    repo = ctx.deps.notification.repo_path
    branch = default_branch_name()
    msg = await git.create_branch(repo, branch)
    ctx.deps.branch = branch
    return f"{msg} (using generated branch name {branch}; ignored suggested {branch_name!r})"


@summary_agent.tool
async def fix_package(ctx: RunContext[SummaryDeps], package_name: str) -> str:
    """Dispatch a package agent to remediate one vulnerable package.

    The package must be one named in the notification. Returns a summary of the
    package's fixes.
    """
    from patchpilot.agents.package import run_package_agent

    notif = ctx.deps.notification
    package = next((p for p in notif.packages if p.name == package_name), None)
    if package is None:
        return (
            f"Error: no package named {package_name} in the notification. "
            f"Known packages: {[p.name for p in notif.packages]}"
        )

    result = await run_package_agent(
        repo_path=notif.repo_path,
        package=package,
        source_file=notif.package_source_file,
    )
    ctx.deps.package_results.append(result)

    fix_lines = "\n".join(
        f"    - {f.vulnerability_id} ({f.category.value}): "
        f"{'OK' if f.success else 'FAILED'} commit={f.commit_sha or 'none'}"
        for f in result.fixes
    )
    return (
        f"Package {package_name}: {'OK' if result.success else 'FAILED'}\n"
        f"{fix_lines}\n"
        f"  {result.summary}"
    )


@summary_agent.tool
async def open_pr(ctx: RunContext[SummaryDeps], title: str, body: str) -> str:
    """Push the remediation branch and open a pull request against the base branch."""
    if ctx.deps.branch is None:
        return "Error: create_branch must be called before open_pr."
    repo = ctx.deps.notification.repo_path
    opened, detail = await git.open_pull_request(
        repo, ctx.deps.branch, title, body, base=ctx.deps.base_branch
    )
    # `detail` is the PR URL on success, or a fallback compare URL / message.
    ctx.deps.pr_url = detail
    return f"{'PR opened' if opened else 'PR not opened via gh'}: {detail}"


@summary_agent.tool
def notify_user(ctx: RunContext[SummaryDeps], subject: str, body: str) -> str:
    """Email the requesting user a summary of the remediation and the PR link."""
    sent, detail = email_tool.send_email(ctx.deps.user_email, subject, body)
    ctx.deps.email_sent = sent
    return f"Email {'sent' if sent else 'failed'}: {detail}"


async def run_summary_agent(
    notification: Notification,
    user_email: str,
    base_branch: str = "main",
) -> RunResult:
    """Entry point — the orchestrator's single call into the agent hierarchy."""
    deps = SummaryDeps(
        notification=notification,
        user_email=user_email,
        base_branch=base_branch,
    )

    pkg_lines = "\n".join(
        f"  - {p.name} {p.installed_version} ({p.ecosystem}): "
        f"{len(p.vulnerabilities)} vulnerability(ies) "
        f"[{', '.join(v.severity for v in p.vulnerabilities)}]"
        for p in notification.packages
    )
    prompt = (
        f"Remediate the vulnerabilities in this repository.\n\n"
        f"Repository          : {notification.repo_path}\n"
        f"Package-source file : {notification.package_source_file}\n"
        f"Base branch         : {base_branch}\n"
        f"Requesting user     : {user_email}\n"
        f"Vulnerable packages ({len(notification.packages)}):\n{pkg_lines}\n\n"
        f"Summarise, create a branch, fix every package, open a PR, and email "
        f"the user. Return a RunResult."
    )

    result = await _runner.run(prompt, deps=deps)
    run_result: RunResult = result.output

    # Reconcile the model's reported result with the side effects we actually
    # performed via the deps, which are authoritative.
    run_result.branch = deps.branch or run_result.branch
    run_result.pr_url = deps.pr_url or run_result.pr_url
    run_result.email_sent = deps.email_sent or run_result.email_sent
    if deps.package_results:
        run_result.packages = deps.package_results
        run_result.success = all(p.success for p in deps.package_results)
    return run_result


def default_branch_name() -> str:
    return f"patchpilot/remediate-{time.strftime('%Y%m%d-%H%M%S')}"
