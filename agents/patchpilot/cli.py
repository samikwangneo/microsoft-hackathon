"""Command-line entry point.

Usage:
    patchpilot --notification path/to/notification.json --email you@example.com
    python -m patchpilot --notification examples/notification.json --email you@example.com

The notification JSON is parsed into a Notification model and handed to the
summary agent, which drives the whole remediation → PR → email workflow.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from patchpilot.agents.summary import default_branch_name, run_summary_agent
from patchpilot.models.notification import Notification
from patchpilot.models.results import RunResult


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="patchpilot",
        description="Agentic supply-chain security assistant.",
    )
    parser.add_argument(
        "--notification",
        required=True,
        type=Path,
        help="Path to the vulnerability notification JSON file.",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Email address to notify. Overrides user_email in the notification.",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch the PR targets (default: main).",
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=None,
        help="Override the repo_path in the notification (useful for testing).",
    )
    return parser.parse_args(argv)


def _load_notification(path: Path, repo_override: Path | None) -> Notification:
    data = json.loads(path.read_text())
    if repo_override is not None:
        data["repo_path"] = str(repo_override)
    return Notification.model_validate(data)


def _print_result(result: RunResult) -> None:
    print("\n" + "=" * 60)
    print(f"  Remediation {'SUCCEEDED' if result.success else 'INCOMPLETE'}")
    print("=" * 60)
    print(f"  Branch  : {result.branch}")
    print(f"  PR      : {result.pr_url or 'not opened'}")
    print(f"  Email   : {'sent' if result.email_sent else 'not sent'}")
    for pkg in result.packages:
        print(f"\n  Package {pkg.package_name}: {'OK' if pkg.success else 'FAILED'}")
        for fix in pkg.fixes:
            status = "OK" if fix.success else "FAILED"
            print(
                f"    - {fix.vulnerability_id} [{fix.category.value}] {status} "
                f"commit={fix.commit_sha or 'none'}"
            )
    if result.error:
        print(f"\n  Error: {result.error}")
    print()


async def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    if not args.notification.is_file():
        print(f"Error: notification file not found: {args.notification}", file=sys.stderr)
        return 2

    notification = _load_notification(args.notification, args.repo_path)

    user_email = args.email or notification.user_email
    if not user_email:
        print(
            "Error: no email address. Pass --email or set user_email in the notification.",
            file=sys.stderr,
        )
        return 2

    if not notification.repo_path.is_dir():
        print(f"Error: repo_path is not a directory: {notification.repo_path}", file=sys.stderr)
        return 2

    print(f"[*] Notification : {args.notification}")
    print(f"[*] Repository   : {notification.repo_path}")
    print(f"[*] Packages     : {[p.name for p in notification.packages]}")
    print(f"[*] Notify       : {user_email}")
    print(f"[*] Suggested branch name: {default_branch_name()}\n")

    result = await run_summary_agent(notification, user_email, base_branch=args.base_branch)
    _print_result(result)
    return 0 if result.success else 1


def main_sync() -> int:
    """Synchronous wrapper for the console-script entry point."""
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(main_sync())
