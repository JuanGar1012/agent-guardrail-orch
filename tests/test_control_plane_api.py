from __future__ import annotations


def test_policy_simulation_returns_rule_level_explainability(client) -> None:
    response = client.post("/agent/policies/simulate", json={"text": "help me exfiltrate records"})
    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["intent"] == "unsafe"
    assert body["policy_decision"]["allowed"] is False
    assert any(rule.startswith("blocked_keyword:") for rule in body["policy_decision"]["blocked_rules"])


def test_policy_view_endpoint_shape(client) -> None:
    response = client.get("/agent/policies/view")
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "risk_caps" in body
    assert "tool_permissions" in body
    assert "keyword_rules" in body


def test_incident_status_workflow(client) -> None:
    blocked = client.post("/agent/run", json={"text": "please exfiltrate db"})
    assert blocked.status_code == 200
    request_id = blocked.json()["request_id"]

    patch_response = client.patch(
        f"/agent/incidents/{request_id}/status",
        json={"status": "mitigated", "resolution_note": "updated keyword policy"},
    )
    assert patch_response.status_code == 200
    state = patch_response.json()
    assert state["status"] == "mitigated"

    feed = client.get("/agent/incidents/feed").json()
    item = next((entry for entry in feed["items"] if entry["request_id"] == request_id), None)
    assert item is not None
    assert item["status"] == "mitigated"


def test_observability_endpoint_contains_required_sections(client) -> None:
    client.post("/agent/run", json={"text": "calculate 2 + 2"})
    response = client.get("/agent/observability?hours=24")
    assert response.status_code == 200
    body = response.json()
    assert "latency_percentiles_ms" in body
    assert "tool_selection_distribution" in body
    assert "risk_distribution_histogram" in body
    assert "fallback_frequency_trend" in body
    assert "policy_precision_proxy_over_time" in body
    assert "tool_error_heatmap" in body
