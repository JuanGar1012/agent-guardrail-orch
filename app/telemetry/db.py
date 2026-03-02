from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TelemetryDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    step TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    details TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def log_event(
        self,
        request_id: str,
        step: str,
        event_type: str,
        success: bool,
        details: dict[str, Any],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (request_id, ts, step, event_type, success, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    datetime.now(timezone.utc).isoformat(),
                    step,
                    event_type,
                    1 if success else 0,
                    json.dumps(details, ensure_ascii=True),
                ),
            )
            conn.commit()

    def incident_summary(self, limit: int = 25) -> dict[str, Any]:
        incident_types = ("policy_block", "tool_failure", "timeout", "invalid_output")
        placeholders = ",".join("?" for _ in incident_types)
        with self._connect() as conn:
            grouped = conn.execute(
                f"""
                SELECT event_type, COUNT(*) AS count
                FROM events
                WHERE event_type IN ({placeholders})
                GROUP BY event_type
                """,
                incident_types,
            ).fetchall()
            total = sum(int(row["count"]) for row in grouped)
            recent = conn.execute(
                """
                SELECT request_id, ts, step, event_type, success, details
                FROM events
                WHERE event_type IN ({})
                ORDER BY id DESC
                LIMIT ?
                """.format(placeholders),
                (*incident_types, limit),
            ).fetchall()

        return {
            "total_incidents": total,
            "by_type": {str(row["event_type"]): int(row["count"]) for row in grouped},
            "recent_events": [
                {
                    "request_id": row["request_id"],
                    "ts": row["ts"],
                    "step": row["step"],
                    "event_type": row["event_type"],
                    "success": bool(row["success"]),
                    "details": json.loads(row["details"]),
                }
                for row in recent
            ],
        }
