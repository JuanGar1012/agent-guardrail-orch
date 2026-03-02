from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    preferred_tool: str | None = None
    tool_args: dict[str, Any] | None = None


class PolicyDecisionView(BaseModel):
    allowed: bool
    reason: str
    blocked_rules: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)


class RunResponse(BaseModel):
    request_id: str
    status: str
    route: str
    intent: str
    risk: str
    message: str
    fallback_used: bool
    tool_results: dict[str, Any] = Field(default_factory=dict)
    policy: PolicyDecisionView
    errors: list[str] = Field(default_factory=list)


class IncidentSummary(BaseModel):
    total_incidents: int
    by_type: dict[str, int]
    recent_events: list[dict[str, Any]]
