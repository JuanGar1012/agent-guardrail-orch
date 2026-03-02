from __future__ import annotations

from functools import lru_cache

from app.core.classifier import RequestClassifier
from app.core.fallback_manager import FallbackManager
from app.core.orchestrator import AgentOrchestrator
from app.core.output_validator import OutputValidator
from app.core.policy_engine import PolicyEngine
from app.core.router import RequestRouter
from app.core.settings import AppSettings, load_settings
from app.core.tool_runner import ToolRunner
from app.telemetry.db import TelemetryDB
from app.telemetry.events import TelemetryService


@lru_cache
def get_settings() -> AppSettings:
    return load_settings()


@lru_cache
def get_orchestrator() -> AgentOrchestrator:
    settings = get_settings()
    telemetry = TelemetryService(TelemetryDB(settings.db_path))
    return AgentOrchestrator(
        settings=settings,
        classifier=RequestClassifier(settings),
        router=RequestRouter(),
        policy_engine=PolicyEngine("config/policies.yaml"),
        tool_runner=ToolRunner(timeout_seconds=settings.tool_timeout_seconds),
        output_validator=OutputValidator("config/output_schema.json"),
        fallback_manager=FallbackManager(),
        telemetry=telemetry,
    )
