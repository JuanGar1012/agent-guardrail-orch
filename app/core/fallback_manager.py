from __future__ import annotations

from app.core.policy_engine import PolicyDecision
from app.models.schemas import PolicyDecisionView, RunResponse


class FallbackManager:
    def safe_response(
        self,
        request_id: str,
        intent: str,
        risk: str,
        route: str,
        message: str,
        decision: PolicyDecision,
        errors: list[str] | None = None,
    ) -> RunResponse:
        return RunResponse(
            request_id=request_id,
            status="safe_fallback",
            route=route,
            intent=intent,
            risk=risk,
            message=message,
            fallback_used=True,
            policy=PolicyDecisionView(
                allowed=decision.allowed,
                reason=decision.reason,
                blocked_rules=decision.blocked_rules,
                allowed_tools=decision.allowed_tools,
            ),
            errors=errors or [],
        )
