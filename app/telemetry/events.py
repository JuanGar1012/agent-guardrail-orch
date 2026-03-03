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

    def get_incident_trends(self, days: int = 7) -> list[dict[str, Any]]:
        return self.db.incident_trends(days=days)

    def get_incident_feed(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.db.incident_feed(limit=limit)

    def get_incident_detail(self, request_id: str) -> dict[str, Any]:
        return self.db.incident_detail(request_id=request_id)

    def get_performance_24h(self, hours: int = 24) -> list[dict[str, Any]]:
        return self.db.performance_24h(hours=hours)

    def clear_all_events(self) -> int:
        return self.db.clear_events()
