from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.core.orchestrator import AgentOrchestrator
from app.dependencies import get_orchestrator
from app.models.schemas import IncidentSummary, RunRequest, RunResponse

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
    }
