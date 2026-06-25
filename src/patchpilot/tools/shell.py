"""Shell execution and file utilities for agent tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Sequence


async def _communicate_with_timeout(
    proc: asyncio.subprocess.Process,
    timeout: int,
    timeout_message: str,
    stdin_data: bytes | None = None,
) -> tuple[str, str, int]:
    communicate_task = asyncio.create_task(proc.communicate(stdin_data))
    try:
        stdout, stderr = await asyncio.wait_for(asyncio.shield(communicate_task), timeout=timeout)
        return _decode(stdout), _decode(stderr), proc.returncode
    except asyncio.TimeoutError:
        if proc.returncode is None:
            proc.kill()
        stdout, stderr = await communicate_task
        stderr_text = _decode(stderr)
        stderr_text = f"{stderr_text}\n{timeout_message}" if stderr_text else timeout_message
        return _decode(stdout), stderr_text, -1


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


async def run_command(
    command: str,
    args: Sequence[str] = (),
    timeout: int = 120,
    cwd: str | None = None,
) -> tuple[str, str, int]:
    """Run a binary with arguments and return (stdout, stderr, returncode)."""
    proc = await asyncio.create_subprocess_exec(
        command,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    return await _communicate_with_timeout(proc, timeout, f"'{command}' timed out after {timeout}s")


async def run_bash(
    command: str,
    timeout: int = 120,
    cwd: str | None = None,
) -> tuple[str, str, int]:
    """Run a shell command via bash and return (stdout, stderr, returncode)."""
    proc = await asyncio.create_subprocess_exec(
        "bash",
        "-c",
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    return await _communicate_with_timeout(proc, timeout, f"Command timed out after {timeout}s")


def read_file(path: str) -> str:
    """Read a text file and return its contents, or an error string."""
    try:
        return Path(path).read_text()
    except Exception as e:  # noqa: BLE001 — surfaced to the agent as a string
        return f"Error reading {path}: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:  # noqa: BLE001
        return f"Error writing {path}: {e}"


def edit_file(
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    """Replace an exact string in an existing text file.

    Errors if old_string is not found, or if it matches more than once and
    replace_all is False (add surrounding context, or set replace_all=True).
    """
    try:
        content = Path(path).read_text(errors="strict")
    except UnicodeDecodeError:
        return f"Error: {path} appears to be a binary file — edit_file is text-only"
    except Exception as e:  # noqa: BLE001
        return f"Error reading {path}: {e}"

    count = content.count(old_string)
    if count == 0:
        return f"Error: string not found in {path}"
    if count > 1 and not replace_all:
        return (
            f"Error: found {count} matches in {path} — provide more surrounding "
            f"context to make the match unique, or set replace_all=True"
        )

    new_content = content.replace(old_string, new_string, -1 if replace_all else 1)
    try:
        Path(path).write_text(new_content)
    except Exception as e:  # noqa: BLE001
        return f"Error writing {path}: {e}"

    replaced = count if replace_all else 1
    return f"Edited {path}: replaced {replaced} occurrence(s)"
