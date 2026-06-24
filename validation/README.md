# Validation

'''md
Owner: Israel Ogwu

## Purpose
The Validation Service verifies that remediation changes do not break the target application before a pull request is created. 
---

## Responsibilities 
- Execute builds 
- Run tests 
- Verify remediation success 
- Generate validation reports 
- Provide deployment confidence signals
---

## Inputs
Example:

'''json
{
    "package": "lodash",
    "updatedVersion": "4.17.21",
    "repository": "demo-repo"
    
}