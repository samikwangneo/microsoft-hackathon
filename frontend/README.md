# Frontend
Owner: Es Lee 

## Purpose 
The Frontend Dashboard provides a visual interface for viewing vulnerabilities, remediation actions, validation results, and generated pull requests. 

---

## Responsibilities
- Display alerts 
- Display remediation progress 
- Display validation results 
- Display generated pull requests 
- Improve demo experience

## Data Sources
- Summary Agent output 
- Case Identifier output 
- Validation output 
- Pull request metadata

## Dashboard Views 


### Alert View
Shows: 
- Package Name 
- Severity 
- Vulnerability Summary 
- Current Version 
- Fixed Version

---

### Workflow View
Shows:

'''text

Alert Received 
    ↓ 
Summary Generated 
    ↓ 
Case Identified 
    ↓ 
Remediation Executed 
    ↓ 
Validation Passed 
    ↓ 
Pull Request Created
    