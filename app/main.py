from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_agent import router as agent_router
from app.api.routes_health import router as health_router

app = FastAPI(title="Agent Guardrails + Orchestration Starter", version="0.1.0")
app.include_router(health_router)
app.include_router(agent_router)
