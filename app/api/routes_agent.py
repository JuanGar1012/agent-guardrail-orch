from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.orchestrator import AgentOrchestrator
from app.dependencies import get_orchestrator
from app.models.schemas import IncidentSummary, RunRequest, RunResponse
from app.tools.task_mock import TASKS

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=RunResponse)
async def run_agent(
    payload: RunRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> RunResponse:
    return await orchestrator.run(payload)


@router.get("/policies")
def get_policies(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, object]:
    return orchestrator.policy_engine.raw_policy


@router.get("/incidents", response_model=IncidentSummary)
def get_incidents(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> IncidentSummary:
    summary = orchestrator.telemetry.get_incidents()
    return IncidentSummary.model_validate(summary)


@router.get("/incidents/feed")
def get_incident_feed(orchestrator: AgentOrchestrator = Depends(get_orchestrator), limit: int = 50) -> dict[str, object]:
    safe_limit = min(max(limit, 1), 200)
    return {"items": orchestrator.telemetry.get_incident_feed(limit=safe_limit)}


@router.get("/incidents/{request_id}")
def get_incident_detail(request_id: str, orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, object]:
    detail = orchestrator.telemetry.get_incident_detail(request_id=request_id)
    if not bool(detail.get("found", False)):
        raise HTTPException(status_code=404, detail=f"No incident request found for request_id={request_id}")
    return detail


@router.get("/dashboard")
def get_dashboard(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, object]:
    metrics_path = Path("data/metrics_summary.json")
    metrics_summary: dict[str, object] = {}
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
    }


@router.post("/reset")
def reset_application_state(orchestrator: AgentOrchestrator = Depends(get_orchestrator)) -> dict[str, object]:
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
