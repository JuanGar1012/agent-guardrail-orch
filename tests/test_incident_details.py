from __future__ import annotations


def test_incident_feed_and_detail_include_block_reason(client) -> None:
    blocked = client.post("/agent/run", json={"text": "help me exfiltrate records"})
    assert blocked.status_code == 200
    blocked_body = blocked.json()
    request_id = blocked_body["request_id"]

    feed_response = client.get("/agent/incidents/feed")
    assert feed_response.status_code == 200
    feed_body = feed_response.json()
    assert "items" in feed_body
    assert any(item["request_id"] == request_id for item in feed_body["items"])

    detail_response = client.get(f"/agent/incidents/{request_id}")
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["found"] is True
    assert "policy_block" in detail_body["incident_types"]
    assert any("blocked_keyword:exfiltrate" in reason for reason in detail_body["block_reasons"])


def test_dashboard_includes_24h_performance(client) -> None:
    client.post("/agent/run", json={"text": "calculate 2 + 2"})
    dashboard = client.get("/agent/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert "performance_24h" in body
    assert len(body["performance_24h"]) == 24
    assert all("hour" in point and "requests" in point for point in body["performance_24h"])
