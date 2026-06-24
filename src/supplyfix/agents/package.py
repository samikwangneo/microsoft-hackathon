"""Package agent — the middle tier, one per vulnerable package.

Responsibilities:
  1. Review the vulnerabilities reported for its package.
  2. Classify each one into a fix category (1 upgrade / 2 upgrade+code /
     3 downgrade) and synthesise a concrete fix description.
  3. Dispatch a vulnerability agent per vulnerability, passing those two pieces
     of information.
  4. Aggregate the results into a PackageResult and return to the summary agent.

The classification is the package agent's core judgement: it may inspect the
repo (read the package-source file, grep for usages) before deciding, since
whether a fix needs code changes depends on how the project uses the library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import Agent, RunContext

from supplyfix.config import settings
from supplyfix.models.notification import Package
from supplyfix.models.results import FixCategory, PackageResult, VulnFixResult
from supplyfix.runner import AgentRunner
from supplyfix.tools.shell import read_file, run_bash

_SYSTEM_PROMPT = """\
You coordinate fixing every vulnerability in ONE package of a repository.

For each reported vulnerability you must decide a FIX CATEGORY and write a FIX
DESCRIPTION, then dispatch a vulnerability agent to do the work via the
fix_vulnerability tool.

Fix categories:
- "upgrade" (Category 1): A fixed version exists and the upgrade is unlikely to
  break the project's code. Just bump the version and reinstall.
- "upgrade_with_code" (Category 2): A fixed version exists BUT the new version
  changes the API the project relies on, so project source code must be updated
  too. Choose this when the major version jumps or you see breaking-change signals.
- "downgrade" (Category 3): No fixed version is reported / no upstream fix
  exists. Pin to the safest known-good earlier version to avoid the vulnerable
  code path.

Workflow:
1. Read the package-source file to see the current declaration.
2. For Category-2 judgement, use inspect_repo to grep for how the project
   imports/uses the package. A larger version jump or heavy usage points to
   "upgrade_with_code". A patch/minor bump with light usage points to "upgrade".
3. For each vulnerability, call fix_vulnerability(vuln_id, category, fix_description).
   Write a fix_description that is specific and actionable: name the target
   version and, for Category 2, the kinds of call sites to update.
4. When every vulnerability is handled, return a PackageResult summarising the
   outcomes.

Respect the `[turn-budget]` reminders. Dispatch one vulnerability agent per
vulnerability; do not try to fix things yourself.
"""


@dataclass
class PackageDeps:
    repo_path: Path
    package: Package
    source_file: str
    fix_results: list[VulnFixResult] = field(default_factory=list)


package_agent = Agent(
    model=settings.package,
    deps_type=PackageDeps,
    output_type=PackageResult,
    system_prompt=_SYSTEM_PROMPT,
)
_runner = AgentRunner("package", package_agent, settings.max_package_requests)


@package_agent.tool
def read_source_file(ctx: RunContext[PackageDeps]) -> str:
    """Read the repository's package-source file (e.g. requirements.txt)."""
    path = ctx.deps.repo_path / ctx.deps.source_file
    return read_file(str(path))


@package_agent.tool
async def inspect_repo(ctx: RunContext[PackageDeps], command: str) -> str:
    """Run a read-only shell command in the repo to inform classification.

    Intended for inspection such as `grep -rn "import lodash" .` or
    `pip index versions <pkg>`. Returns exit code + output.
    """
    stdout, stderr, rc = await run_bash(command, cwd=str(ctx.deps.repo_path))
    parts = [f"[exit {rc}]"]
    if stdout:
        parts.append(stdout)
    if stderr:
        parts.append(stderr)
    return "\n".join(parts)[:6_000]


@package_agent.tool
async def fix_vulnerability(
    ctx: RunContext[PackageDeps],
    vulnerability_id: str,
    category: FixCategory,
    fix_description: str,
) -> str:
    """Dispatch a vulnerability agent to fix one vulnerability and commit it.

    Pass the chosen *category* and a concrete *fix_description*. Returns a
    summary of the fix including the commit SHA (or an error).
    """
    from supplyfix.agents.vulnerability import run_vulnerability_agent

    vuln = next(
        (v for v in ctx.deps.package.vulnerabilities if v.id == vulnerability_id),
        None,
    )
    if vuln is None:
        return (
            f"Error: no vulnerability with id {vulnerability_id} on package "
            f"{ctx.deps.package.name}. Known ids: "
            f"{[v.id for v in ctx.deps.package.vulnerabilities]}"
        )

    result = await run_vulnerability_agent(
        repo_path=ctx.deps.repo_path,
        package=ctx.deps.package,
        vulnerability=vuln,
        category=category,
        fix_description=fix_description,
        source_file=ctx.deps.source_file,
    )
    ctx.deps.fix_results.append(result)

    status = "OK" if result.success else "FAILED"
    return (
        f"[{status}] {vulnerability_id} ({category.value})\n"
        f"  commit : {result.commit_sha or 'none'}\n"
        f"  files  : {result.files_changed}\n"
        f"  summary: {result.summary}\n"
        f"  error  : {result.error or 'none'}"
    )


async def run_package_agent(repo_path: Path, package: Package, source_file: str) -> PackageResult:
    """Entry point called by the summary agent to remediate one package."""
    deps = PackageDeps(repo_path=repo_path, package=package, source_file=source_file)

    vuln_lines = "\n".join(
        f"  - {v.id} [{v.severity}] fixed_version={v.fixed_version or 'none'}: "
        f"{v.summary or v.details[:120]}"
        for v in package.vulnerabilities
    )
    prompt = (
        f"Remediate every vulnerability in this package.\n\n"
        f"Repository          : {repo_path}\n"
        f"Package-source file : {source_file}\n"
        f"Package             : {package.name} (installed {package.installed_version}, "
        f"ecosystem {package.ecosystem})\n"
        f"Vulnerabilities ({len(package.vulnerabilities)}):\n{vuln_lines}\n\n"
        f"Classify each vulnerability, then call fix_vulnerability for each one. "
        f"Return a PackageResult when done."
    )

    result = await _runner.run(prompt, deps=deps)
    pkg_result: PackageResult = result.output

    # Trust the dispatched fixes as the source of truth for what actually happened.
    if deps.fix_results:
        pkg_result.fixes = deps.fix_results
        pkg_result.success = all(f.success for f in deps.fix_results)
    pkg_result.package_name = package.name
    return pkg_result
