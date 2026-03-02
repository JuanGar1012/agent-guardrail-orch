from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError

from app.tools.calculator import CalculatorInput, run_calculator
from app.tools.doc_search import DocSearchInput, run_doc_search
from app.tools.task_mock import TaskInput, run_task_mock


class ToolExecutionError(Exception):
    pass


@dataclass(slots=True)
class ToolSpec:
    name: str
    input_model: type[BaseModel]
    runner: Callable[[BaseModel], Awaitable[dict[str, Any]]]


class ToolRunner:
    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.registry = {
            "doc_search": ToolSpec("doc_search", DocSearchInput, run_doc_search),
            "calculator": ToolSpec("calculator", CalculatorInput, run_calculator),
            "task_mock": ToolSpec("task_mock", TaskInput, run_task_mock),
        }

    def list_tools(self) -> list[str]:
        return sorted(self.registry.keys())

    async def run_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        spec = self.registry.get(name)
        if not spec:
            raise ToolExecutionError(f"Unknown tool: {name}")
        try:
            validated = spec.input_model.model_validate(args)
        except ValidationError as exc:
            raise ToolExecutionError(f"Input schema validation failed for {name}: {exc}") from exc

        try:
            result = await asyncio.wait_for(spec.runner(validated), timeout=self.timeout_seconds)
            return {"tool": name, "result": result}
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"Tool timeout: {name}") from exc
        except Exception as exc:
            raise ToolExecutionError(f"Tool execution failed for {name}: {exc}") from exc
