from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

INCIDENT_TYPES = ("policy_block", "tool_failure", "timeout", "invalid_output")


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
        placeholders = ",".join("?" for _ in INCIDENT_TYPES)
        with self._connect() as conn:
            grouped = conn.execute(
                f"""
                SELECT event_type, COUNT(*) AS count
                FROM events
                WHERE event_type IN ({placeholders})
                GROUP BY event_type
                """,
                INCIDENT_TYPES,
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
                (*INCIDENT_TYPES, limit),
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
                    "details": self._parse_details(row["details"]),
                }
                for row in recent
            ],
        }

    def incident_trends(self, days: int = 7) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in INCIDENT_TYPES)
        start_ts = (datetime.now(timezone.utc) - timedelta(days=max(1, days) - 1)).isoformat()

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT substr(ts, 1, 10) AS day, event_type, COUNT(*) AS count
                FROM events
                WHERE event_type IN ({})
                  AND ts >= ?
                GROUP BY substr(ts, 1, 10), event_type
                ORDER BY day ASC
                """.format(placeholders),
                (*INCIDENT_TYPES, start_ts),
            ).fetchall()

        return [
            {"day": str(row["day"]), "event_type": str(row["event_type"]), "count": int(row["count"])}
            for row in rows
        ]

    def incident_feed(self, limit: int = 50) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in INCIDENT_TYPES)
        with self._connect() as conn:
            request_ids = conn.execute(
                """
                SELECT request_id, MAX(id) AS latest_id
                FROM events
                WHERE event_type IN ({})
                GROUP BY request_id
                ORDER BY latest_id DESC
                LIMIT ?
                """.format(placeholders),
                (*INCIDENT_TYPES, limit),
            ).fetchall()

            items: list[dict[str, Any]] = []
            for row in request_ids:
                request_id = str(row["request_id"])
                events = conn.execute(
                    """
                    SELECT id, ts, step, event_type, success, details
                    FROM events
                    WHERE request_id = ?
                    ORDER BY id ASC
                    """,
                    (request_id,),
                ).fetchall()
                if not events:
                    continue

                incident_events = [event for event in events if str(event["event_type"]) in INCIDENT_TYPES]
                if not incident_events:
                    continue

                first_incident = incident_events[0]
                last_incident = incident_events[-1]
                request_text = ""
                for event in events:
                    if str(event["event_type"]) == "request_received":
                        details = self._parse_details(event["details"])
                        request_text = str(details.get("text", ""))
                        break

                reason_summary = self._build_reason_summary(last_incident["event_type"], last_incident["details"])
                items.append(
                    {
                        "request_id": request_id,
                        "incident_type": str(last_incident["event_type"]),
                        "first_seen_ts": str(first_incident["ts"]),
                        "last_seen_ts": str(last_incident["ts"]),
                        "request_text": request_text,
                        "reason_summary": reason_summary,
                        "event_count": len(events),
                        "incident_events": [
                            {
                                "ts": str(event["ts"]),
                                "event_type": str(event["event_type"]),
                                "step": str(event["step"]),
                                "details": self._parse_details(event["details"]),
                            }
                            for event in incident_events
                        ],
                    }
                )
        return items

    def incident_detail(self, request_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            events = conn.execute(
                """
                SELECT id, ts, step, event_type, success, details
                FROM events
                WHERE request_id = ?
                ORDER BY id ASC
                """,
                (request_id,),
            ).fetchall()

        if not events:
            return {"request_id": request_id, "found": False}

        parsed_events = [
            {
                "id": int(event["id"]),
                "ts": str(event["ts"]),
                "step": str(event["step"]),
                "event_type": str(event["event_type"]),
                "success": bool(event["success"]),
                "details": self._parse_details(event["details"]),
            }
            for event in events
        ]
        incident_events = [event for event in parsed_events if event["event_type"] in INCIDENT_TYPES]
        request_text = ""
        request_event = next((event for event in parsed_events if event["event_type"] == "request_received"), None)
        if request_event:
            request_text = str(request_event["details"].get("text", ""))

        block_reasons: list[str] = []
        for event in incident_events:
            details = event["details"]
            if event["event_type"] == "policy_block":
                rules = details.get("blocked_rules", [])
                if isinstance(rules, list):
                    block_reasons.extend(str(rule) for rule in rules)
            elif "error" in details:
                block_reasons.append(str(details["error"]))
            elif "errors" in details and isinstance(details["errors"], list):
                block_reasons.extend(str(item) for item in details["errors"])

        return {
            "request_id": request_id,
            "found": True,
            "request_text": request_text,
            "incident_count": len(incident_events),
            "incident_types": sorted({event["event_type"] for event in incident_events}),
            "block_reasons": block_reasons,
            "timeline": parsed_events,
        }

    def performance_24h(self, hours: int = 24) -> list[dict[str, Any]]:
        window_hours = max(1, hours)
        now_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        start_hour = now_hour - timedelta(hours=window_hours - 1)
        start_ts = start_hour.isoformat()

        buckets: dict[str, dict[str, Any]] = {}
        for offset in range(window_hours):
            hour = start_hour + timedelta(hours=offset)
            key = hour.strftime("%Y-%m-%dT%H")
            buckets[key] = {
                "hour": hour.strftime("%Y-%m-%d %H:00"),
                "requests": 0,
                "successful": 0,
                "fallback_requests": 0,
                "policy_blocks": 0,
                "tool_failures": 0,
                "timeouts": 0,
                "invalid_outputs": 0,
            }

        placeholders = ",".join("?" for _ in INCIDENT_TYPES)
        with self._connect() as conn:
            request_rows = conn.execute(
                """
                SELECT substr(ts, 1, 13) AS hour_key, COUNT(*) AS count
                FROM events
                WHERE event_type = 'request_received'
                  AND ts >= ?
                GROUP BY substr(ts, 1, 13)
                """,
                (start_ts,),
            ).fetchall()
            for row in request_rows:
                key = str(row["hour_key"])
                if key in buckets:
                    buckets[key]["requests"] = int(row["count"])

            success_rows = conn.execute(
                """
                SELECT substr(ts, 1, 13) AS hour_key, COUNT(*) AS count
                FROM events
                WHERE event_type = 'completed'
                  AND ts >= ?
                GROUP BY substr(ts, 1, 13)
                """,
                (start_ts,),
            ).fetchall()
            for row in success_rows:
                key = str(row["hour_key"])
                if key in buckets:
                    buckets[key]["successful"] = int(row["count"])

            incident_rows = conn.execute(
                """
                SELECT substr(ts, 1, 13) AS hour_key, event_type, COUNT(*) AS count
                FROM events
                WHERE event_type IN ({})
                  AND ts >= ?
                GROUP BY substr(ts, 1, 13), event_type
                """.format(placeholders),
                (*INCIDENT_TYPES, start_ts),
            ).fetchall()
            for row in incident_rows:
                key = str(row["hour_key"])
                event_type = str(row["event_type"])
                count = int(row["count"])
                if key not in buckets:
                    continue
                if event_type == "policy_block":
                    buckets[key]["policy_blocks"] = count
                elif event_type == "tool_failure":
                    buckets[key]["tool_failures"] = count
                elif event_type == "timeout":
                    buckets[key]["timeouts"] = count
                elif event_type == "invalid_output":
                    buckets[key]["invalid_outputs"] = count

            fallback_rows = conn.execute(
                """
                SELECT substr(first_ts, 1, 13) AS hour_key, COUNT(*) AS count
                FROM (
                    SELECT request_id, MIN(ts) AS first_ts
                    FROM events
                    WHERE event_type IN ({})
                      AND ts >= ?
                    GROUP BY request_id
                )
                GROUP BY substr(first_ts, 1, 13)
                """.format(placeholders),
                (*INCIDENT_TYPES, start_ts),
            ).fetchall()
            for row in fallback_rows:
                key = str(row["hour_key"])
                if key in buckets:
                    buckets[key]["fallback_requests"] = int(row["count"])

        return [buckets[key] for key in sorted(buckets.keys())]

    def clear_events(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()
            deleted = int(row["count"]) if row is not None else 0
            conn.execute("DELETE FROM events")
            conn.commit()
        return deleted

    def _parse_details(self, raw: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _build_reason_summary(self, event_type: str, raw_details: str) -> str:
        details = self._parse_details(raw_details)
        if event_type == "policy_block":
            blocked = details.get("blocked_rules", [])
            if isinstance(blocked, list) and blocked:
                return ", ".join(str(item) for item in blocked)
            return "Request blocked by policy."
        if "error" in details:
            return str(details.get("error"))
        if "errors" in details and isinstance(details["errors"], list) and details["errors"]:
            return ", ".join(str(item) for item in details["errors"][:3])
        return "Incident captured."
