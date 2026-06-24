# PatchPilot

PatchPilot is an agentic supply-chain security assistant.

## Workflow

GitHub Alert / OSV
↓
Summary Agent
↓
Case Identifier
↓
Remediation Engine
↓
Validation
↓
Git Automation
↓
Pull Request

## Team

See docs/team-roles.md

## MVP Scope

- Single ecosystem (npm)
- GitHub alert ingestion
- OSV enrichment
- Vulnerability classification
- Dependency remediation
- Validation
- Pull request generation

## RULES
Nobody commits directly to main.

Everyone creates:
    feature/samik-intake
    feature/madalina-agents
    feature/danniecia-remediation
    feature/israel-validation
    feature/es-frontend
All changes go through PRs.
