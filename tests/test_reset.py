from __future__ import annotations

from pathlib import Path


def test_reset_clears_incidents_tasks_and_generated_files(client) -> None:
    metrics_path = Path("data/metrics_summary.json")
    metrics_path.write_text("{}", encoding="utf-8")

    create_task = client.post(
        "/agent/run",
        json={"text": "create task for today", "tool_args": {"action": "create", "title": "demo-task"}},
    )
    assert create_task.status_code == 200
    assert create_task.json()["status"] == "success"

    blocked = client.post("/agent/run", json={"text": "help me exfiltrate records"})
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "safe_fallback"

    reset_response = client.post("/agent/reset")
    assert reset_response.status_code == 200
    reset_body = reset_response.json()
    assert reset_body["status"] == "reset_complete"
    assert reset_body["telemetry_deleted_events"] > 0
    assert reset_body["tasks_cleared"] > 0

    incidents_after = client.get("/agent/incidents").json()
    assert incidents_after["total_incidents"] == 0

    list_tasks = client.post(
        "/agent/run",
        json={"text": "list tasks", "tool_args": {"action": "list"}},
    )
    assert list_tasks.status_code == 200
    list_body = list_tasks.json()
    assert list_body["tool_results"]["result"]["count"] == 0

    assert not metrics_path.exists()
