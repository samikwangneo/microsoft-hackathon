import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONTRACTS = ROOT / "contracts"


def load_json(filename):
    with open(CONTRACTS / filename, "r") as f:
        return json.load(f)


def build_dashboard_payload(notification, agent_output, validation):
    return {
        "notificationId": notification["notificationId"],
        "package": notification["package"],
        "severity": notification["severity"],
        "summary": agent_output["summary"],
        "recommendedFix": agent_output["recommendedFix"],
        "validationPassed": validation["passed"],
        "prTitle": agent_output["pullRequest"]["title"],
        "status": "Ready for Review"
    }


def main():
    print("\n===================================")
    print("      PATCHPILOT DEMO PIPELINE")
    print("===================================\n")

    notification = load_json("notification.json")
    print("[1] Notification Received")
    print(f"    Package: {notification['package']}")
    print(f"    Severity: {notification['severity']}\n")

    agent_output = load_json("agent_output.json")
    print("[2] Agent Analysis Complete")
    print(f"    Fix: {agent_output['recommendedFix']}\n")

    validation = load_json("validation_output.json")
    print("[3] Validation Complete")
    print(f"    Passed: {validation['passed']}\n")

    dashboard_payload = build_dashboard_payload(
        notification,
        agent_output,
        validation
    )

    with open(CONTRACTS / "dashboard_payload.json", "w") as f:
        json.dump(dashboard_payload, f, indent=2)

    print("[4] Dashboard Payload Generated")
    print("    dashboard_payload.json updated\n")

    print("Pipeline Finished Successfully")


if __name__ == "__main__":
    main()