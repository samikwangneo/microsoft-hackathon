"""Validation service tests.

Step 1 covers the output contract guard; orchestration tests are added in Step 4.
"""

import json
from pathlib import Path

from app.validation.models import CheckResult, ValidationReport

# contracts/ lives at the repo root: tests -> backend -> repo root.
_CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "validation_output.json"


def test_report_is_superset_of_dashboard_contract():
    """ValidationReport must keep every key the demo/dashboard contract expects."""
    expected_keys = set(json.loads(_CONTRACT.read_text()))

    report = ValidationReport(
        alert_id="OSV-001",
        passed=True,
        tests_run=5,
        checks=[CheckResult(name="security_scan", passed=True, details="clean")],
        notes="Validation successful",
    )
    dumped = report.model_dump()

    missing = expected_keys - dumped.keys()
    assert not missing, f"ValidationReport dropped contract keys: {missing}"
