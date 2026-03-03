from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.orchestrator import AgentOrchestrator
from app.dependencies import get_orchestrator
from app.models.schemas import (
    IncidentStatusUpdateRequest,
    IncidentSummary,
    PolicySimulationRequest,
    PolicyUpdateRequest,
    RunRequest,
    RunResponse,
)
from app.tools.task_mock import TASKS

router = APIRouter(prefix="/agent", tags=["agent"])


def _suggest_tool(intent: str, route: str, preferred_tool: str | None) -> str | None:
    if preferred_tool:
        return preferred_tool
    if route == "retrieval":
        return "doc_search"
    if route == "tool_workflow" and intent == "math":
        return "calculator"
    if route == "tool_workflow" and intent == "task_manage":
        return "task_mock"
    return None


@router.post("/run", response_model=RunResponse)
async def run_agent(
    payload: RunRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> RunResponse:
    return await orchestrator.run(payload)


@router.get("/policies")
def get_policies(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, Any]:
    return orchestrator.policy_engine.raw_policy


@router.put("/policies")
def update_policies(payload: PolicyUpdateRequest, orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, Any]:
    updated = orchestrator.policy_engine.replace_policy(payload.policy)
    return {"status": "updated", "policy": updated}


@router.get("/policies/view")
def get_policy_view(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, Any]:
    policy = orchestrator.policy_engine.raw_policy
    tool_permissions = policy.get("tool_permissions", {})
    risk_caps = policy.get("intent_risk_caps", {})
    keywords = policy.get("blocked_keywords", [])
    return {
        "summary": {
            "allowed_tool_count": len(policy.get("allowed_tools", [])),
            "blocked_intent_count": len(policy.get("blocked_intents", [])),
            "blocked_keyword_count": len(keywords),
        },
        "risk_caps": [{"intent": intent, "max_risk": cap} for intent, cap in sorted(risk_caps.items())],
        "tool_permissions": [{"intent": intent, "tools": tools} for intent, tools in sorted(tool_permissions.items())],
        "keyword_rules": [{"keyword": keyword, "category": "unsafe_pattern"} for keyword in keywords],
    }


@router.post("/policies/simulate")
def simulate_policy(
    payload: PolicySimulationRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    classification = orchestrator.classifier.classify(payload.text)
    route = orchestrator.router.route(classification.intent, classification.route_hint)
    decision = orchestrator.policy_engine.evaluate(
        text=payload.text,
        intent=classification.intent,
        risk=classification.risk,
        preferred_tool=payload.preferred_tool,
    )
    suggested_tool = _suggest_tool(classification.intent, route, payload.preferred_tool)
    return {
        "classification": {
            "intent": classification.intent,
            "risk": classification.risk,
            "reason": classification.reason,
            "route_hint": classification.route_hint,
        },
        "route": route,
        "suggested_tool": suggested_tool,
        "policy_decision": {
            "allowed": decision.allowed,
            "reason": decision.reason,
            "blocked_rules": decision.blocked_rules,
            "allowed_tools": decision.allowed_tools,
        },
    }


@router.get("/incidents", response_model=IncidentSummary)
def get_incidents(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> IncidentSummary:
    summary = orchestrator.telemetry.get_incidents()
    return IncidentSummary.model_validate(summary)


@router.get("/incidents/feed")
def get_incident_feed(orchestrator: AgentOrchestrator = Depends(get_orchestrator), limit: int = 50) -> dict[str, Any]:
    safe_limit = min(max(limit, 1), 200)
    return {"items": orchestrator.telemetry.get_incident_feed(limit=safe_limit)}


@router.get("/incidents/{request_id}")
def get_incident_detail(request_id: str, orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, Any]:
    detail = orchestrator.telemetry.get_incident_detail(request_id=request_id)
    if not bool(detail.get("found", False)):
        raise HTTPException(status_code=404, detail=f"No incident request found for request_id={request_id}")
    return detail


@router.patch("/incidents/{request_id}/status")
def update_incident_status(
    request_id: str,
    payload: IncidentStatusUpdateRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, Any]:
    detail = orchestrator.telemetry.get_incident_detail(request_id=request_id)
    if not bool(detail.get("found", False)):
        raise HTTPException(status_code=404, detail=f"No incident request found for request_id={request_id}")
    state = orchestrator.telemetry.update_incident_status(
        request_id=request_id,
        status=payload.status,
        resolution_note=payload.resolution_note,
    )
    return {"request_id": request_id, **state}


@router.get("/observability")
def get_observability(orchestrator: AgentOrchestrator = Depends(get_orchestrator), hours: int = 24) -> dict[str, Any]:
    safe_hours = min(max(hours, 1), 168)
    return orchestrator.telemetry.get_observability_snapshot(hours=safe_hours)


@router.get("/dashboard")
def get_dashboard(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, Any]:
    metrics_path = Path("data/metrics_summary.json")
    metrics_summary: dict[str, Any] = {}
    if metrics_path.exists():
        try:
            metrics_summary = json.loads(metrics_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metrics_summary = {}

    return {
        "metrics_summary": metrics_summary,
        "incident_summary": orchestrator.telemetry.get_incidents(),
        "incident_trends": orchestrator.telemetry.get_incident_trends(days=7),
        "incident_feed": orchestrator.telemetry.get_incident_feed(limit=20),
        "performance_24h": orchestrator.telemetry.get_performance_24h(hours=24),
        "observability": orchestrator.telemetry.get_observability_snapshot(hours=24),
    }


@router.post("/reset")
def reset_application_state(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, Any]:
    telemetry_deleted = orchestrator.telemetry.clear_all_events()
    task_count = len(TASKS)
    TASKS.clear()

    cleanup_targets = [
        Path("data/metrics_summary.json"),
        Path("data/reliability_report.json"),
        Path("data/incident_summary.json"),
        Path("data/incident_summary.md"),
        Path("data/run_all_summary.json"),
    ]
    deleted_files: list[str] = []
    for target in cleanup_targets:
        if target.exists():
            target.unlink()
            deleted_files.append(str(target).replace("\\", "/"))

    return {
        "status": "reset_complete",
        "telemetry_deleted_events": telemetry_deleted,
        "tasks_cleared": task_count,
        "deleted_files": deleted_files,
    }
