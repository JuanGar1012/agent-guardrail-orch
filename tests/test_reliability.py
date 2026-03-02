from __future__ import annotations


def test_tool_failure_triggers_fallback(client) -> None:
    response = client.post("/agent/run", json={"text": "calculate 1 / 0"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "safe_fallback"
    assert body["fallback_used"] is True
    assert "Tool failed" in body["message"]


def test_timeout_triggers_fallback(client) -> None:
    response = client.post(
        "/agent/run",
        json={
            "text": "create task with delay",
            "tool_args": {"action": "list", "simulate_delay_s": 5},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "safe_fallback"
    assert body["fallback_used"] is True
    assert "timeout" in body["message"].lower()


def test_malformed_output_repaired_or_falls_back(client) -> None:
    response = client.post("/agent/run", json={"text": "return malformed output"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"success", "safe_fallback"}
    assert "request_id" in body


def test_incidents_endpoint_reports_failures(client) -> None:
    client.post("/agent/run", json={"text": "calculate 1 / 0"})
    response = client.get("/agent/incidents")
    assert response.status_code == 200
    body = response.json()
    assert body["total_incidents"] >= 1
