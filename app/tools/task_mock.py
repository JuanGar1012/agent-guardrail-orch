from __future__ import annotations

import asyncio
from datetime import datetime

from pydantic import BaseModel, Field


class TaskInput(BaseModel):
    action: str = Field(pattern="^(create|list)$")
    title: str | None = Field(default=None, max_length=200)
    due_date: str | None = None
    simulate_delay_s: float = Field(default=0.0, ge=0.0, le=20.0)


TASKS: list[dict[str, str]] = []


async def run_task_mock(data: TaskInput) -> dict[str, object]:
    if data.simulate_delay_s:
        await asyncio.sleep(data.simulate_delay_s)

    if data.action == "list":
        return {"tasks": TASKS, "count": len(TASKS)}
    if not data.title:
        raise ValueError("title is required for create action")

    record = {
        "title": data.title,
        "due_date": data.due_date or "",
        "created_at": datetime.utcnow().isoformat(),
    }
    TASKS.append(record)
    return {"created": record, "count": len(TASKS)}
