"""Shared file-manipulation tools registered onto agents that edit the repo."""

from __future__ import annotations

from pydantic_ai import Agent

from supplyfix.tools.shell import edit_file, read_file, write_file


def register_file_tools(agent: Agent) -> None:
    """Attach read_file_tool, write_file_tool, and edit_file_tool to *agent*."""

    @agent.tool_plain
    def read_file_tool(path: str) -> str:
        """Read a text file from disk and return its contents."""
        return read_file(path)

    @agent.tool_plain
    def write_file_tool(path: str, content: str) -> str:
        """Write content to a file on disk, creating parent directories as needed."""
        return write_file(path, content)

    @agent.tool_plain
    def edit_file_tool(
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        """Replace an exact string in an existing text file.

        Errors if the string is not found, or if it matches more than once and
        replace_all is False. Add surrounding context to disambiguate, or set
        replace_all=True to replace every occurrence.
        """
        return edit_file(path, old_string, new_string, replace_all)
