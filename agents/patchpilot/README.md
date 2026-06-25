# PatchPilot — agentic supply-chain remediation

A three-tier hierarchy of [Pydantic AI](https://ai.pydantic.dev) agents that
takes a vulnerability notification, fixes the affected dependencies in a target
repository, and opens a pull request.

```
Summary agent            (one per notification)
    ├─ summarises the notification
    ├─ creates a remediation branch
    ├─ dispatches a Package agent per vulnerable package ──┐
    │                                                      │
    │   Package agent     (one per package)                │
    │       ├─ classifies each vulnerability into a fix    │
    │       │  category (1 upgrade / 2 upgrade+code /      │
    │       │  3 downgrade) + writes a fix description     │
    │       └─ dispatches a Vulnerability agent per vuln ──┤
    │                                                      │
    │           Vulnerability agent  (one per vuln)        │
    │               ├─ edits the repo per the category     │
    │               ├─ runs install/upgrade commands       │
    │               └─ git commits the fix ────────────────┘
    │
    ├─ opens the pull request
    └─ emails the user a summary
```

Each tier is a real LLM `Agent`; the lower tiers are invoked as **tools** of the
tier above (`fix_package` → package agent, `fix_vulnerability` → vulnerability
agent). Control returns up the chain as each tier returns its typed result.

## Fix categories

| Category | Name                | What the vulnerability agent does                         |
|----------|---------------------|-----------------------------------------------------------|
| 1        | `upgrade`           | Bump to the fixed version; edit source file + reinstall   |
| 2        | `upgrade_with_code` | Bump to the fixed version **and** adapt project code      |
| 3        | `downgrade`         | No upstream fix — pin to a safe earlier version           |

The package agent decides the category and synthesises the fix description; both
are passed down to the vulnerability agent.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
```

Optional configuration lives in `config.yaml` (copy from `config.yaml.example`)
to override model choices and per-agent request budgets.

## Run

```bash
python -m patchpilot \
  --notification examples/notification.json \
  --email you@example.com \
  --repo-path /path/to/target/repo
```

`--repo-path` overrides `repo_path` in the notification (handy for testing).
`--email` overrides the notification's `user_email`. `--base-branch` sets the
PR's base (default `main`).

### Notification format

See `examples/notification.json`. One repository, one package-source file, many
packages, each with many vulnerabilities:

```json
{
  "repo_path": "/path/to/repo",
  "package_source_file": "requirements.txt",
  "user_email": "you@example.com",
  "packages": [
    {
      "name": "requests",
      "installed_version": "2.19.1",
      "ecosystem": "pip",
      "vulnerabilities": [
        { "id": "CVE-...", "severity": "high", "summary": "...", "fixed_version": "2.20.0" }
      ]
    }
  ]
}
```

## Notes

- **Pull requests** use the GitHub CLI (`gh`) when present; otherwise the branch
  is pushed and a compare URL is returned so a PR can be opened manually.
- **Email**: the summary agent emails the requesting user the PR link and a
  per-fix summary (`tools/email.py`). Delivery is via SMTP — set
  `PATCHPILOT_SMTP_HOST` (and optionally `PATCHPILOT_SMTP_USER` /
  `PATCHPILOT_SMTP_PASSWORD`) to send; see `config.yaml.example` for all
  `PATCHPILOT_SMTP_*` settings. Every message is also recorded to `./outbox/`,
  which is the only behaviour when no SMTP host is configured (handy for demos).
- **Budgets**: every agent run is capped by a request limit and receives
  per-turn budget reminders, so runs terminate predictably.
- Set `PATCHPILOT_EVENT_LOG=path.jsonl` to capture a structured trace of every
  agent request, tool call, and tool return.
