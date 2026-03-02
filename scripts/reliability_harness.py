from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def main() -> None:
    scenarios = [
        {"name": "tool_failure", "payload": {"text": "calculate 1 / 0"}},
        {
            "name": "timeout",
            "payload": {"text": "list tasks", "tool_args": {"action": "list", "simulate_delay_s": 5}},
        },
        {"name": "malformed_output", "payload": {"text": "please generate malformed output"}},
        {"name": "safe_request", "payload": {"text": "calculate 6 * 7"}},
    ]
    results: list[dict[str, object]] = []

    client = TestClient(app)
    for scenario in scenarios:
        response = client.post("/agent/run", json=scenario["payload"])
        body = response.json()
        results.append(
            {
                "scenario": scenario["name"],
                "http_status": response.status_code,
                "status": body.get("status"),
                "fallback_used": body.get("fallback_used"),
                "errors": body.get("errors", []),
            }
        )

    output = {"scenarios_executed": len(results), "results": results}
    Path("data/reliability_report.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
