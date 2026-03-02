from __future__ import annotations

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
