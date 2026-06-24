# Validation Service

**Owner:** Israel Ogwu

## Purpose

The Validation Service is the safety check that runs **after** the Remediation
Engine bumps a dependency version but **before** a pull request is opened. It
builds and tests the target application against the proposed fix to confirm the
upgrade doesn't break anything, then emits a pass/fail report. This is what lets
PatchPilot open a PR with confidence instead of blindly bumping versions.

## Responsibilities

- Execute builds
- Run tests
- Verify remediation success
- Generate validation reports
- Provide deployment-confidence signals

## Inputs

```json
{
  "package": "lodash",
  "updatedVersion": "4.18.0",
  "repository": "demo-repo"
}
```

## Status

Not implemented yet — this is a placeholder spec. When built, it lives under
`backend/app/validation/` alongside the intake service.
