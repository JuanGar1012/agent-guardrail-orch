from __future__ import annotations

import uuid
from typing import Any

from app.core.classifier import RequestClassifier
from app.core.fallback_manager import FallbackManager
from app.core.output_validator import OutputValidator
from app.core.policy_engine import PolicyDecision, PolicyEngine
from app.core.router import RequestRouter
from app.core.settings import AppSettings
from app.core.tool_runner import ToolExecutionError, ToolRunner
from app.models.schemas import PolicyDecisionView, RunRequest, RunResponse
from app.telemetry.events import TelemetryService


class AgentOrchestrator:
    def __init__(
        self,
        settings: AppSettings,
        classifier: RequestClassifier,
        router: RequestRouter,
        policy_engine: PolicyEngine,
        tool_runner: ToolRunner,
        output_validator: OutputValidator,
        fallback_manager: FallbackManager,
        telemetry: TelemetryService,
    ) -> None:
        self.settings = settings
        self.classifier = classifier
        self.router = router
        self.policy_engine = policy_engine
        self.tool_runner = tool_runner
        self.output_validator = output_validator
        self.fallback_manager = fallback_manager
        self.telemetry = telemetry

    async def run(self, request: RunRequest) -> RunResponse:
        request_id = str(uuid.uuid4())
        self.telemetry.log(request_id, "request", "request_received", True, {"text": request.text})
        classification = self.classifier.classify(request.text)
        self.telemetry.log(
            request_id,
            "classification",
            "classified",
            True,
            {"intent": classification.intent, "risk": classification.risk, "reason": classification.reason},
        )
        route = self.router.route(classification.intent, classification.route_hint)
        self.telemetry.log(request_id, "routing", "route_selected", True, {"route": route})

        decision = self.policy_engine.evaluate(
            text=request.text,
            intent=classification.intent,
            risk=classification.risk,
            preferred_tool=request.preferred_tool,
        )
        self.telemetry.log(
            request_id,
            "policy",
            "policy_decision",
            decision.allowed,
            {
                "allowed": decision.allowed,
                "reason": decision.reason,
                "blocked_rules": decision.blocked_rules,
                "allowed_tools": decision.allowed_tools,
            },
        )
        if not decision.allowed:
            self.telemetry.log(
                request_id,
                "policy",
                "policy_block",
                False,
                {"blocked_rules": decision.blocked_rules},
            )
            return self.fallback_manager.safe_response(
                request_id=request_id,
                intent=classification.intent,
                risk=classification.risk,
                route=route,
                message="Request blocked by safety policy.",
                decision=decision,
                errors=decision.blocked_rules,
            )

        tool_name = self._choose_tool(route, classification.intent, request.preferred_tool)
        tool_results: dict[str, Any] = {}
        fallback_errors: list[str] = []
        if tool_name:
            tool_args = self._build_tool_args(tool_name, request)
            try:
                self.telemetry.log(request_id, "tool", "tool_attempt", True, {"tool": tool_name, "args": tool_args})
                tool_results = await self.tool_runner.run_tool(tool_name, tool_args)
                self.telemetry.log(
                    request_id,
                    "tool",
                    "tool_success",
                    True,
                    {"tool": tool_name, "result": tool_results.get("result", {})},
                )
            except TimeoutError as exc:
                self.telemetry.log(request_id, "tool", "timeout", False, {"tool": tool_name, "error": str(exc)})
                return self.fallback_manager.safe_response(
                    request_id=request_id,
                    intent=classification.intent,
                    risk=classification.risk,
                    route=route,
                    message="Tool timeout occurred; returned safe-mode response.",
                    decision=decision,
                    errors=[str(exc)],
                )
            except ToolExecutionError as exc:
                self.telemetry.log(
                    request_id,
                    "tool",
                    "tool_failure",
                    False,
                    {"tool": tool_name, "error": str(exc)},
                )
                return self.fallback_manager.safe_response(
                    request_id=request_id,
                    intent=classification.intent,
                    risk=classification.risk,
                    route=route,
                    message="Tool failed; returned safe-mode response.",
                    decision=decision,
                    errors=[str(exc)],
                )

        payload = self._build_output_payload(
            request=request,
            intent=classification.intent,
            risk=classification.risk,
            route=route,
            tool_results=tool_results,
            decision=decision,
            request_id=request_id,
            errors=fallback_errors,
        )
        validation_errors = self.output_validator.validate(payload)
        retries = 0
        while validation_errors and retries < self.settings.output_validation_retries:
            retries += 1
            self.telemetry.log(
                request_id,
                "validation",
                "invalid_output",
                False,
                {"errors": validation_errors, "retry": retries},
            )
            payload = self._repair_output_payload(payload)
            validation_errors = self.output_validator.validate(payload)

        if validation_errors:
            self.telemetry.log(
                request_id,
                "validation",
                "invalid_output",
                False,
                {"errors": validation_errors, "retry": retries},
            )
            return self.fallback_manager.safe_response(
                request_id=request_id,
                intent=classification.intent,
                risk=classification.risk,
                route=route,
                message="Generated response failed output schema validation.",
                decision=decision,
                errors=validation_errors,
            )

        self.telemetry.log(request_id, "outcome", "completed", True, {"status": payload["status"]})
        return RunResponse.model_validate(payload)

    def _choose_tool(self, route: str, intent: str, preferred_tool: str | None) -> str | None:
        if preferred_tool:
            return preferred_tool
        if route == "retrieval":
            return "doc_search"
        if route == "tool_workflow" and intent == "math":
            return "calculator"
        if route == "tool_workflow" and intent == "task_manage":
            return "task_mock"
        return None

    def _build_tool_args(self, tool_name: str, request: RunRequest) -> dict[str, Any]:
        if request.tool_args:
            return request.tool_args
        if tool_name == "doc_search":
            return {"query": request.text, "top_k": 3}
        if tool_name == "calculator":
            return {"expression": request.text.replace("calculate", "").strip()}
        if tool_name == "task_mock":
            return {"action": "list"}
        return {}

    def _build_output_payload(
        self,
        request: RunRequest,
        intent: str,
        risk: str,
        route: str,
        tool_results: dict[str, Any],
        decision: PolicyDecision,
        request_id: str,
        errors: list[str],
    ) -> dict[str, Any]:
        if "malformed output" in request.text.lower():
            return {"request_id": request_id, "status": "success"}

        message = "Request completed."
        if tool_results:
            message = f"Request completed via {tool_results.get('tool', 'tool')}."
        return {
            "request_id": request_id,
            "status": "success",
            "route": route,
            "intent": intent,
            "risk": risk,
            "message": message,
            "fallback_used": False,
            "tool_results": tool_results,
            "policy": {
                "allowed": decision.allowed,
                "reason": decision.reason,
                "blocked_rules": decision.blocked_rules,
                "allowed_tools": decision.allowed_tools,
            },
            "errors": errors,
        }

    def _repair_output_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        repaired = dict(payload)
        repaired.setdefault("route", "direct")
        repaired.setdefault("intent", "general")
        repaired.setdefault("risk", "medium")
        repaired.setdefault("message", "Repaired response payload.")
        repaired.setdefault("fallback_used", False)
        repaired.setdefault("tool_results", {})
        repaired.setdefault(
            "policy",
            PolicyDecisionView(
                allowed=True,
                reason="Auto-repaired output payload.",
                blocked_rules=[],
                allowed_tools=[],
            ).model_dump(),
        )
        repaired.setdefault("errors", [])
        return repaired
