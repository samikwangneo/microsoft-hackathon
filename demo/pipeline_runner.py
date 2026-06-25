import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

def load_json(name):
    with open(ROOT / "contracts" / name, "r") as f:
        return json.load(f)

def main():
    alert = load_json("alert.json")
    print("Alert received")

    agent = load_json("agent-output.json")
    print("Agent completed")

    validation = load_json("validation.json")
    print("Validation completed")

    dashboard = load_json("dashboard.json")
    print("Dashboard updated")

    print("\n=== SUMMARY ===")
    print(f"Package: {alert['package']}")
    print(f"Status: {dashboard['status']}")
    print(f"Validation Passed: {validation['passed']}")

if __name__ == "__main__":
    main()