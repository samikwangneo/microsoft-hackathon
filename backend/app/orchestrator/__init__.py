"""Orchestrator — wires intake (OSV) → the patchpilot agents → dashboard.

`bridge` converts intake's normalized output into the agents' Notification
input; `runner` drives a full remediation run and exposes its telemetry; and
`dashboard_map` turns the agents' RunResult into the dashboard payload.
"""
