from __future__ import annotations

from typing import Any

from app.telemetry.db import TelemetryDB


class TelemetryService:
    def __init__(self, db: TelemetryDB) -> None:
        self.db = db

    def log(self, request_id: str, step: str, event_type: str, success: bool, details: dict[str, Any]) -> None:
        self.db.log_event(request_id=request_id, step=step, event_type=event_type, success=success, details=details)

    def get_incidents(self) -> dict[str, Any]:
        return self.db.incident_summary()
