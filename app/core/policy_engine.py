from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    blocked_rules: list[str]
    allowed_tools: list[str]


class PolicyEngine:
    def __init__(self, policy_path: str | Path = "config/policies.yaml") -> None:
        self.policy_path = Path(policy_path)
        self.raw_policy = self._load_policy()

    def _load_policy(self) -> dict[str, Any]:
        with self.policy_path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    def replace_policy(self, new_policy: dict[str, Any]) -> dict[str, Any]:
        with self.policy_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(new_policy, fh, sort_keys=False)
        self.raw_policy = new_policy
        return self.raw_policy

    def evaluate(
        self,
        text: str,
        intent: str,
        risk: str,
        preferred_tool: str | None = None,
    ) -> PolicyDecision:
        blocked_rules: list[str] = []
        lowered = text.lower()
        blocked_keywords = self.raw_policy.get("blocked_keywords", [])
        for keyword in blocked_keywords:
            if keyword.lower() in lowered:
                blocked_rules.append(f"blocked_keyword:{keyword}")

        blocked_intents = set(self.raw_policy.get("blocked_intents", []))
        if intent in blocked_intents:
            blocked_rules.append(f"blocked_intent:{intent}")

        intent_caps = self.raw_policy.get("intent_risk_caps", {})
        max_risk = intent_caps.get(intent, "high")
        if RISK_ORDER.get(risk, 3) > RISK_ORDER.get(max_risk, 2):
            blocked_rules.append(f"risk_cap_exceeded:{intent}:{max_risk}")

        global_allowlist = set(self.raw_policy.get("allowed_tools", []))
        intent_tools = set(self.raw_policy.get("tool_permissions", {}).get(intent, []))
        allowed_tools = sorted(global_allowlist.intersection(intent_tools)) if intent_tools else sorted(global_allowlist)

        if preferred_tool is not None and preferred_tool not in allowed_tools:
            blocked_rules.append(f"tool_not_allowed:{preferred_tool}")
        if preferred_tool is not None and preferred_tool not in global_allowlist:
            blocked_rules.append(f"tool_not_allowlisted:{preferred_tool}")

        if blocked_rules:
            return PolicyDecision(
                allowed=False,
                reason="Request blocked by policy rules.",
                blocked_rules=blocked_rules,
                allowed_tools=allowed_tools,
            )

        return PolicyDecision(
            allowed=True,
            reason="Request allowed by policy.",
            blocked_rules=[],
            allowed_tools=allowed_tools,
        )
