"""PatchPilot — an agentic supply-chain security assistant.

A three-tier hierarchy of Pydantic AI agents remediates vulnerable
dependencies and opens a pull request:

    Summary agent        (one per notification)
        └─ Package agent  (one or more per vulnerable package)
            └─ Vulnerability agent  (one per vulnerability fix)

The summary agent summarises the incoming notification, cuts a branch, and
dispatches package agents. Each package agent classifies every vulnerability
into a fix category and dispatches vulnerability agents that make the actual
code/dependency changes and commit. When everything is done the summary agent
opens the PR and emails the user.
"""

__version__ = "0.1.0"
