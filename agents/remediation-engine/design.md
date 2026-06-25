# Remediation Engine Design

## Purpose

The Remediation Engine receives a classified vulnerability from the
Case Identifier and performs the actions necessary to remediate it.

## Inputs

- Package name
- Current version
- Fixed version
- Severity
- Case type

## Outputs

- Updated dependency files
- Validation request
- Git branch
- Commit
- Pull Request draft
- GitHub issue (if remediation cannot be completed)

---

## Supported Cases

### Case 1: Patch Upgrade Available

Example:

lodash 4.17.20 -> 4.17.21

Actions:

1. Update dependency
2. Install updated package
3. Trigger validation
4. Create branch
5. Commit changes
6. Generate PR

### Case 2: Upgrade Requires Code Changes

Actions:

1. Update dependency
2. Identify affected source files
3. Modify code if possible
4. Trigger validation
5. Generate PR

### Case 3: No Safe Upgrade Exists

Actions:

1. Create GitHub Issue
2. Include vulnerability summary
3. Recommend next steps
``