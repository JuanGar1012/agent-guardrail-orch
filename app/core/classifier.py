from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.core.settings import AppSettings


@dataclass(slots=True)
class ClassificationResult:
    intent: str
    risk: str
    reason: str
    route_hint: str


class RequestClassifier:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def classify(self, text: str) -> ClassificationResult:
        if self.settings.enable_ollama:
            result = self._classify_with_ollama(text)
            if result is not None:
                return result

        lowered = text.lower()
        unsafe_terms = [
            "delete system32",
            "exfiltrate",
            "infiltrate",
            "infiltration",
            "bypass policy",
            "drop table",
            "malware",
        ]
        if any(term in lowered for term in unsafe_terms):
            return ClassificationResult(
                intent="unsafe",
                risk="high",
                reason="Unsafe keyword matched.",
                route_hint="direct",
            )
        if any(word in lowered for word in ["search", "find in docs", "documentation", "corpus"]):
            return ClassificationResult(
                intent="search_docs",
                risk="low",
                reason="Retrieval language detected.",
                route_hint="retrieval",
            )
        if re.search(r"(\d+\s*[-+/*]\s*\d+)|\bcalculate\b|\bmath\b", lowered):
            return ClassificationResult(
                intent="math",
                risk="low",
                reason="Math expression/request detected.",
                route_hint="tool_workflow",
            )
        if any(word in lowered for word in ["task", "todo", "calendar", "schedule"]):
            return ClassificationResult(
                intent="task_manage",
                risk="medium",
                reason="Task/calendar workflow request detected.",
                route_hint="tool_workflow",
            )
        if any(word in lowered for word in ["password", "token", "secret", "private key"]):
            return ClassificationResult(
                intent="general",
                risk="high",
                reason="Sensitive-data context detected.",
                route_hint="direct",
            )
        return ClassificationResult(
            intent="general",
            risk="low",
            reason="Default general request.",
            route_hint="direct",
        )

    def _classify_with_ollama(self, text: str) -> ClassificationResult | None:
        prompt = (
            "Classify the request into intent in [general,search_docs,math,task_manage,unsafe], "
            "risk in [low,medium,high,critical], and route_hint in [direct,retrieval,tool_workflow]. "
            "Return JSON with keys intent,risk,reason,route_hint only.\n"
            f"Request: {text}"
        )
        payload = json.dumps(
            {
                "model": self.settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }
        ).encode("utf-8")
        url = f"{self.settings.ollama_host}/api/generate"
        request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=1.5) as response:
                body = json.loads(response.read().decode("utf-8"))
                parsed = json.loads(body.get("response", "{}"))
                return ClassificationResult(
                    intent=parsed.get("intent", "general"),
                    risk=parsed.get("risk", "medium"),
                    reason=parsed.get("reason", "Classifier fallback."),
                    route_hint=parsed.get("route_hint", "direct"),
                )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
            return None
