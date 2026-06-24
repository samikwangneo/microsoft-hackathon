# Summary Agent
Owner: Madalina Stoicov 

## Purpose 
The Summary Agent converts raw vulnerability information into concise, human-readable security summaries. 

Its goal is to provide developers with quick situational awareness before remediation begins. --- 

## Responsibilities 
- Summarize vulnerabilities 
- Explain severity 
- Explain security impact 
- Recommend remediation actions 
- Generate developer-friendly outputs 
--- 

## Inputs 
Example input: 

```json 
{ "package": "lodash", 
"severity": "HIGH", 
"currentVersion": "4.17.20", 
"fixedVersion": "4.17.21", 
"cve": "CVE-XXXX" }
