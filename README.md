# PatchPilot

PatchPilot is an agentic supply-chain security assistant. It scans a local
repository manifest for vulnerable dependencies, runs a hierarchy of remediation
agents, opens a pull request, and surfaces progress in a dashboard.

## Current Integrated Flow

```text
Backend intake / OSV scan
-> backend orchestrator bridge
-> PatchPilot summary, package, and vulnerability agents
-> backend dashboard mapper
-> FastAPI /dashboard and /run endpoints
-> React dashboard
```

The live integration is code-model based, not driven by the sample JSON files in
`contracts/`. Agent results are defined in `agents/patchpilot/models/results.py`,
backend dashboard payloads in `backend/app/dashboard/models.py`, and frontend
types in `frontend/src/types.ts`.

## Project Layout

```text
agents/
    patchpilot/              Pydantic AI agent package and CLI
        agents/                Summary, package, and vulnerability agents
        models/                Agent input/output Pydantic models
        tools/                 Git, shell, email, and file-edit tools
    remediation-engine/      Earlier remediation design notes

backend/
    app/
        intake/                OSV client, parsers, and manifest scanning
        orchestrator/          Intake -> agent bridge, run state, dashboard mapping
        routes/                FastAPI routes for intake, dashboard, and runs
        dashboard/             Dashboard response models and seed fallback data
    tests/                   Backend and orchestrator tests

frontend/
    src/                     Vite/React dashboard UI
    package.json             Frontend scripts and dependencies

docs/                      Architecture, demo notes, roadmap, examples
demo/                      Proof-of-concept notes and old static pipeline demo
contracts/                 Legacy/static JSON demo artifacts
```

## Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt -e ".[dev]"

Push-Location frontend
npm ci
Pop-Location
```

Copy `.env.example` to `.env` when running the agent workflow. OSV intake works
without secrets, but live remediation requires model/provider configuration and
optional SMTP/GitHub settings.

## Run The Integrated App

Start the backend from `backend/`:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app
Pop-Location
```

On Windows, do not use `--reload` for remediation runs. Agent subprocesses use
`git` and package-manager commands, which require the Proactor event loop.

Start the frontend from `frontend/`:

```powershell
Push-Location frontend
npm run dev
Pop-Location
```

Open the Vite URL printed by the frontend. The dashboard reads from the backend
`/dashboard` endpoint and can start live remediation runs through `/run`.

## Backend API

Core endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health/version check |
| `POST` | `/intake/scan` | Scan one package/version with OSV |
| `POST` | `/intake/manifest` | Scan a manifest's pinned dependencies |
| `GET` | `/dashboard` | Latest completed run payload, or seed data |
| `POST` | `/run` | Start scan -> agents -> PR -> email workflow |
| `GET` | `/run/{run_id}` | Poll run status |
| `GET` | `/run/{run_id}/events` | Server-sent event stream for run telemetry |

See `backend/README.md` for detailed request examples and supported manifest
formats.

## Agents

The PatchPilot agent package lives in `agents/patchpilot` and is installed as an
editable package from the repository root.

Agent hierarchy:

```text
Summary agent
-> Package agent per vulnerable package
-> Vulnerability agent per vulnerability
```

The summary agent owns branch/PR/email orchestration. Package agents classify
fixes as `upgrade`, `upgrade_with_code`, or `downgrade`. Vulnerability agents edit
the target repository and commit each scoped fix.

CLI entry point:

```powershell
python -m patchpilot --notification path\to\notification.json --email you@example.com --repo-path path\to\target-repo
```

See `agents/patchpilot/README.md` for the standalone agent workflow.

## Tests And Checks

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests

Push-Location frontend
npm run build
Pop-Location
```

## Notes

- The integrated demo path is backend/orchestrator -> agents -> dashboard -> frontend.
- `contracts/` is retained for the old static demo pipeline and is not the live
    contract between the app layers.
- `demo/POC.md` captures historical proof-of-concept notes; use the integrated
    backend/frontend flow for current demos.
- Team ownership notes live in `docs/team-roles.md`.
