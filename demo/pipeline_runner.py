# Pipeline Runner for PatchPilot

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONTRACTS = ROOT / "contracts"

# Load JSON files from the contracts directory
def load_json(filename):
    with open(CONTRACTS / filename, "r") as f:
        return json.load(f)
    


# Build the dashboard payload
def build_dashboard_payload(notification, agent_output, validation):
    fix = agent_output.get("recommended_fix", {})

    return {
        "alertId": notification.get("alert_id"),
        "package": notification.get("package"),
        "severity": notification.get("severity"),
        "summary": agent_output.get("summary"),
        "recommendedFix": (
            f"Upgrade {fix.get('package')} "
            f"from {fix.get('from_version')} "
            f"to {fix.get('to_version')}"
        ),
        "validationPassed": validation.get("passed"),
        "prTitle": agent_output.get("pull_request", {}).get(
            "title",
            "No PR Generated"
        ),
        "prStatus": "Ready for Review"
    }

# Main function to run the pipeline
def main():
    print("\n===================================")
    print("PATCHPILOT DEMO PIPELINE")
    print("===================================\n")

    # Load the necessary JSON files
    notification = load_json("notification.json")

    print("[1] Notification Received")
    print(f"Package: {notification.get('package', 'Unknown')}")
    print(f"Severity: {notification.get('severity', 'Unknown')}\n")

    agent_output = load_json("agent_output.json")

    fix = agent_output.get("recommended_fix", {})

    # Extract the fix details
    package = fix.get("package", "Unknown")
    from_version = fix.get("from_version", "?")
    to_version = fix.get("to_version", "?")

    # Print the agent analysis
    print("[2] Agent Analysis Complete")
    print(f"Summary: {agent_output['summary']}")
    print(
        f"Fix: Upgrade {fix['package']} "
        f"from {fix['from_version']} "
        f"to {fix['to_version']}"
    )
    print()

    validation = load_json("validation_output.json")

    print("[3] Validation Complete")
    print(f"Passed: {validation['passed']}\n")

    dashboard_payload = build_dashboard_payload(
        notification,
        agent_output,
        validation,
    )

    # Write the dashboard payload to a JSON file
    with open(CONTRACTS / "dashboard_payload.json", "w") as f:
        json.dump(
            dashboard_payload,
            f,
            indent=2,
        )

    print("[4] Dashboard Payload Generated")
    print("dashboard_payload.json updated\n")
    print("Dashboard Preview:")
    print(json.dumps(dashboard_payload, indent=2))
    print()

    print("Pipeline Finished Successfully")


if __name__ == "__main__":
    main()