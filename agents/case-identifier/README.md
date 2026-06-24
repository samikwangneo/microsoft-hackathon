# Case Identifier Agent

Owner: Madalina Stoicov

## Purpose

The Case Identifier Agent determines how a vulnerability should be remediated.

After the Summary Agent analyzes a vulnerability, this component classifies the alert into a remediation case and routes it to the appropriate workflow.

---

## Responsibilities

- Analyze vulnerability metadata
- Determine remediation strategy
- Route vulnerabilities to downstream services
- Generate justification for decisions
- Support future risk-based decision making

---

## Inputs

Example input:

```json
{
  "package": "lodash",
  "currentVersion": "4.17.20",
  "fixedVersion": "4.17.21",
  "severity": "HIGH",
  "summary": "Prototype pollution vulnerability detected."
}