# Vulnerability Intake Service

**Owner:** Samik Wangneo

## Purpose
Receive vulnerability notifications from GitHub and retrieve additional security information from OSV.

## Responsibilities
- GitHub alert ingestion
- OSV vulnerability lookup
- Data normalization
- Forwarding structured alerts to downstream agents

## Inputs
- GitHub Security Alert
- OSV API responses

## Outputs

```json
{
  "package": "lodash",
  "currentVersion": "4.17.20",
  "fixedVersion": "4.17.21",
  "severity": "HIGH",
  "cve": "CVE-XXXX",
  "source": "npm"
}