"""Git automation helpers, scoped to a single repository checkout.

All functions are async and shell out to git (and optionally the GitHub CLI)
inside the given repo path. They return small, structured results so the agents
can reason about success/failure without parsing raw git output.
"""

from __future__ import annotations

from pathlib import Path

from supplyfix.tools.shell import run_command


async def _git(repo: Path, *args: str, timeout: int = 60) -> tuple[str, str, int]:
    return await run_command("git", ["-C", str(repo), *args], timeout=timeout)


async def current_branch(repo: Path) -> str:
    out, _, _ = await _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip()


async def create_branch(repo: Path, branch: str) -> str:
    """Create and switch to *branch* (or switch to it if it already exists)."""
    out, err, rc = await _git(repo, "checkout", "-b", branch)
    if rc != 0:
        # Branch may already exist — try a plain checkout.
        out2, err2, rc2 = await _git(repo, "checkout", branch)
        if rc2 != 0:
            return f"Error creating branch {branch}: {err or err2}".strip()
        return f"Switched to existing branch {branch}"
    return f"Created and switched to branch {branch}"


async def has_changes(repo: Path) -> bool:
    out, _, _ = await _git(repo, "status", "--porcelain")
    return bool(out.strip())


async def changed_files(repo: Path) -> list[str]:
    out, _, _ = await _git(repo, "status", "--porcelain")
    files: list[str] = []
    for line in out.splitlines():
        # porcelain format: "XY <path>"
        path = line[3:].strip() if len(line) > 3 else line.strip()
        if path:
            files.append(path)
    return files


async def commit_all(repo: Path, message: str) -> tuple[bool, str]:
    """Stage every change and commit. Returns (committed, sha_or_error)."""
    if not await has_changes(repo):
        return False, "no changes to commit"
    _, add_err, add_rc = await _git(repo, "add", "-A")
    if add_rc != 0:
        return False, f"git add failed: {add_err}"
    _, commit_err, commit_rc = await _git(repo, "commit", "-m", message)
    if commit_rc != 0:
        return False, f"git commit failed: {commit_err}"
    sha, _, _ = await _git(repo, "rev-parse", "HEAD")
    return True, sha.strip()


async def push_branch(repo: Path, branch: str) -> tuple[bool, str]:
    out, err, rc = await _git(repo, "push", "-u", "origin", branch, timeout=120)
    if rc != 0:
        return False, (err or out).strip()
    return True, (out or err).strip()


async def _remote_compare_url(repo: Path, branch: str) -> str | None:
    """Best-effort GitHub compare URL derived from origin, for when gh is absent."""
    out, _, rc = await _git(repo, "remote", "get-url", "origin")
    if rc != 0:
        return None
    url = out.strip()
    if url.startswith("git@"):  # git@github.com:owner/repo.git
        url = url.replace(":", "/").replace("git@", "https://")
    if url.endswith(".git"):
        url = url[:-4]
    return f"{url}/compare/{branch}?expand=1"


async def open_pull_request(
    repo: Path,
    branch: str,
    title: str,
    body: str,
    base: str = "main",
) -> tuple[bool, str]:
    """Push the branch and open a PR.

    Uses the GitHub CLI (`gh`) when available. If `gh` is not installed or the
    push has no remote, falls back to returning a compare URL the user can open
    manually — so the run still produces a usable artifact.
    """
    pushed, push_msg = await push_branch(repo, branch)

    # Try gh first.
    gh_check, _, gh_rc = await run_command("bash", ["-c", "command -v gh"])
    if gh_rc == 0:
        out, err, rc = await run_command(
            "gh",
            [
                "pr", "create",
                "--title", title,
                "--body", body,
                "--base", base,
                "--head", branch,
            ],
            cwd=str(repo),
            timeout=120,
        )
        if rc == 0 and out.strip():
            return True, out.strip()
        # gh failed; fall through to compare URL.
        fallback = await _remote_compare_url(repo, branch)
        detail = (err or out).strip()
        if fallback:
            return False, f"gh pr create failed ({detail}); open manually: {fallback}"
        return False, f"gh pr create failed: {detail}"

    # No gh — return a compare URL if we can.
    fallback = await _remote_compare_url(repo, branch)
    if fallback and pushed:
        return False, f"gh not installed; branch pushed. Open a PR at: {fallback}"
    if fallback:
        return False, f"gh not installed and push failed ({push_msg}). Compare URL: {fallback}"
    return False, f"Cannot open PR: gh not installed and no usable remote ({push_msg})"
