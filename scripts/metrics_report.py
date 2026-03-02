from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def safe_div(n: float, d: float) -> float:
    if d == 0:
        return 0.0
    return round(n / d, 4)


def main() -> None:
    scenarios = json.loads(Path("scripts/benchmark_scenarios.json").read_text(encoding="utf-8"))
    client = TestClient(app)

    tp = fp = fn = tn = 0
    successes = 0
    fallback_count = 0
    blocked_unsafe_actions = 0
    detailed: list[dict[str, object]] = []

    for scenario in scenarios:
        response = client.post("/agent/run", json=scenario["payload"])
        body = response.json()
        blocked = body.get("status") == "safe_fallback" and body.get("policy", {}).get("allowed") is False
        expected_block = bool(scenario["expected_block"])

        if blocked and expected_block:
            tp += 1
            blocked_unsafe_actions += 1
        elif blocked and not expected_block:
            fp += 1
        elif (not blocked) and expected_block:
            fn += 1
        else:
            tn += 1

        succeeded = body.get("status") == "success"
        if succeeded:
            successes += 1
        if bool(body.get("fallback_used")):
            fallback_count += 1

        detailed.append(
            {
                "name": scenario["name"],
                "status": body.get("status"),
                "blocked": blocked,
                "expected_block": expected_block,
                "fallback_used": body.get("fallback_used"),
            }
        )

    total = len(scenarios)
    report = {
        "total_scenarios": total,
        "policy_precision_proxy": safe_div(tp, tp + fp),
        "policy_recall_proxy": safe_div(tp, tp + fn),
        "blocked_unsafe_actions_count": blocked_unsafe_actions,
        "task_success_rate": safe_div(successes, total),
        "fallback_activation_rate": safe_div(fallback_count, total),
        "confusion_matrix_proxy": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "scenario_results": detailed,
    }

    Path("data/metrics_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
