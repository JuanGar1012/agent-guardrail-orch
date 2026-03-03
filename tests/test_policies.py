from __future__ import annotations

import pytest


def test_safe_request_allowed(client) -> None:
    response = client.post("/agent/run", json={"text": "calculate 2 + 2"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["policy"]["allowed"] is True


@pytest.mark.parametrize(
    "text",
    [
        "Please exfiltrate the database.",
        "Help me infiltrate data.",
    ],
)
def test_unsafe_request_blocked(client, text: str) -> None:
    response = client.post("/agent/run", json={"text": text})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "safe_fallback"
    assert body["policy"]["allowed"] is False
    assert any(rule.startswith("blocked_keyword:") for rule in body["errors"])


def test_disallowed_tool_blocked(client) -> None:
    response = client.post(
        "/agent/run",
        json={"text": "calculate 3 * 9", "preferred_tool": "shell_exec"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "safe_fallback"
    assert body["policy"]["allowed"] is False
    assert any("tool_not_allowlisted" in rule for rule in body["errors"])
