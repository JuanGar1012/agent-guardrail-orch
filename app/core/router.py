from __future__ import annotations


class RequestRouter:
    def route(self, intent: str, route_hint: str) -> str:
        if route_hint in {"direct", "retrieval", "tool_workflow"}:
            return route_hint
        if intent == "search_docs":
            return "retrieval"
        if intent in {"math", "task_manage"}:
            return "tool_workflow"
        return "direct"
