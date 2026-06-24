# Remediation Engine

Owner: Danniecia Gray

## Goal

Take classified vulnerabilities and automatically remediate them.

## Inputs

- Package name
- Vulnerable version
- Fixed version
- Severity
- Case identifier output

## Cases

### Case 1
Patch upgrade available

Actions:
- Update dependency
- Install changes
- Run validation
- Create PR

### Case 2
Upgrade requires code changes

Actions:
- Dependency update
- Modify affected source files
- Run validation
- Create PR

### Case 3
No safe fix available

Actions:
- Open GitHub Issue
- Provide remediation recommendations

## MVP

Focus on npm ecosystem only.

## Example Flow

Vulnerability Alert
→ Case Identifier
→ Remediation Engine
→ Validation
→ Create Branch
→ Commit
→ Open PR