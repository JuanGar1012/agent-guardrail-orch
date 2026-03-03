from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

INCIDENT_TYPES = ("policy_block", "tool_failure", "timeout", "invalid_output")
INCIDENT_STATUSES = {"open", "mitigated", "closed"}


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_state (
                    request_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'open',
                    resolution_note TEXT NOT NULL DEFAULT '',
                    updated_ts TEXT NOT NULL
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
        start_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with self._connect() as conn:
            recurrence_rows = conn.execute(
                """
                SELECT event_type, COUNT(*) AS count
                FROM events
                WHERE event_type IN ({})
                  AND ts >= ?
                GROUP BY event_type
                """.format(placeholders),
                (*INCIDENT_TYPES, start_24h),
            ).fetchall()
            recurrence_map = {str(row["event_type"]): int(row["count"]) for row in recurrence_rows}

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

            id_list = [str(row["request_id"]) for row in request_ids]
            state_map = self._get_incident_state_map(id_list)
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

                incident_type = str(last_incident["event_type"])
                details = self._parse_details(last_incident["details"])
                linked_rules = self._extract_rule_links(incident_type, details)
                tool_name = self._extract_tool(incident_type, details)
                severity = self._severity_for_incident(incident_type, details)
                reason_summary = self._build_reason_summary(incident_type, details)
                state = state_map.get(request_id, {"status": "open", "resolution_note": ""})

                items.append(
                    {
                        "request_id": request_id,
                        "incident_type": incident_type,
                        "severity": severity,
                        "status": state["status"],
                        "resolution_note": state["resolution_note"],
                        "first_seen_ts": str(first_incident["ts"]),
                        "last_seen_ts": str(last_incident["ts"]),
                        "request_text": request_text,
                        "reason_summary": reason_summary,
                        "linked_rules": linked_rules,
                        "tool_name": tool_name,
                        "event_count": len(events),
                        "recurrence_count_24h": recurrence_map.get(incident_type, 0),
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
        state = self.get_incident_state(request_id)

        request_text = ""
        request_event = next((event for event in parsed_events if event["event_type"] == "request_received"), None)
        if request_event:
            request_text = str(request_event["details"].get("text", ""))

        incident_type = incident_events[-1]["event_type"] if incident_events else "unknown"
        latest_details = incident_events[-1]["details"] if incident_events else {}
        block_reasons = self._extract_block_reasons(incident_events)
        linked_rules = self._extract_rule_links(str(incident_type), latest_details)
        tool_name = self._extract_tool(str(incident_type), latest_details)

        return {
            "request_id": request_id,
            "found": True,
            "request_text": request_text,
            "incident_count": len(incident_events),
            "incident_types": sorted({event["event_type"] for event in incident_events}),
            "severity": self._severity_for_incident(str(incident_type), latest_details),
            "status": state["status"],
            "resolution_note": state["resolution_note"],
            "root_cause_summary": self._build_reason_summary(str(incident_type), latest_details),
            "linked_policy_rules": linked_rules,
            "tool_name": tool_name,
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
                  AND json_extract(details, '$.status') = 'success'
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

    def observability_snapshot(self, hours: int = 24) -> dict[str, Any]:
        window_hours = max(1, hours)
        start_ts = (datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=window_hours - 1)).isoformat()
        performance = self.performance_24h(window_hours)
        latency_values = self._latency_values_ms(start_ts)
        tool_distribution = self._tool_selection_distribution(start_ts)
        risk_distribution = self._risk_distribution(start_ts)
        precision_over_time = self._policy_precision_proxy_over_time(start_ts, performance)
        tool_heatmap = self._tool_error_heatmap(start_ts)
        fallback_trend = [{"hour": point["hour"], "fallback_requests": point["fallback_requests"]} for point in performance]

        return {
            "window_hours": window_hours,
            "latency_percentiles_ms": {
                "p50": self._percentile(latency_values, 50),
                "p95": self._percentile(latency_values, 95),
                "p99": self._percentile(latency_values, 99),
            },
            "tool_selection_distribution": tool_distribution,
            "risk_distribution_histogram": risk_distribution,
            "fallback_frequency_trend": fallback_trend,
            "policy_precision_proxy_over_time": precision_over_time,
            "tool_error_heatmap": tool_heatmap,
        }

    def set_incident_status(self, request_id: str, status: str, resolution_note: str = "") -> dict[str, Any]:
        normalized = status.strip().lower()
        if normalized not in INCIDENT_STATUSES:
            raise ValueError(f"Invalid incident status: {status}")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO incident_state (request_id, status, resolution_note, updated_ts)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(request_id)
                DO UPDATE SET status=excluded.status, resolution_note=excluded.resolution_note, updated_ts=excluded.updated_ts
                """,
                (request_id, normalized, resolution_note.strip(), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

        return self.get_incident_state(request_id)

    def get_incident_state(self, request_id: str) -> dict[str, str]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT status, resolution_note
                FROM incident_state
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
        if row is None:
            return {"status": "open", "resolution_note": ""}
        return {"status": str(row["status"]), "resolution_note": str(row["resolution_note"])}

    def clear_events(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()
            deleted = int(row["count"]) if row is not None else 0
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM incident_state")
            conn.commit()
        return deleted

    def _get_incident_state_map(self, request_ids: list[str]) -> dict[str, dict[str, str]]:
        if not request_ids:
            return {}
        placeholders = ",".join("?" for _ in request_ids)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT request_id, status, resolution_note
                FROM incident_state
                WHERE request_id IN ({})
                """.format(placeholders),
                request_ids,
            ).fetchall()
        return {
            str(row["request_id"]): {"status": str(row["status"]), "resolution_note": str(row["resolution_note"])}
            for row in rows
        }

    def _extract_block_reasons(self, incident_events: list[dict[str, Any]]) -> list[str]:
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
        return block_reasons

    def _extract_rule_links(self, event_type: str, details: dict[str, Any]) -> list[str]:
        if event_type != "policy_block":
            return []
        blocked = details.get("blocked_rules", [])
        if not isinstance(blocked, list):
            return []
        return [str(item) for item in blocked]

    def _extract_tool(self, event_type: str, details: dict[str, Any]) -> str:
        if event_type in {"tool_failure", "timeout"} and isinstance(details.get("tool"), str):
            return str(details["tool"])
        return ""

    def _severity_for_incident(self, event_type: str, details: dict[str, Any]) -> str:
        if event_type == "policy_block":
            rules = details.get("blocked_rules", [])
            text = " ".join(str(item) for item in rules) if isinstance(rules, list) else ""
            high_terms = ["malware", "drop table", "exfiltrate", "infiltrate", "unsafe"]
            return "high" if any(term in text for term in high_terms) else "medium"
        if event_type in {"tool_failure", "timeout"}:
            return "medium"
        if event_type == "invalid_output":
            return "low"
        return "low"

    def _build_reason_summary(self, event_type: str, details: dict[str, Any]) -> str:
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

    def _latency_values_ms(self, start_ts: str) -> list[float]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT request_id, ts, event_type
                FROM events
                WHERE event_type IN ('request_received', 'completed')
                  AND ts >= ?
                ORDER BY id ASC
                """,
                (start_ts,),
            ).fetchall()

        spans: dict[str, dict[str, datetime]] = defaultdict(dict)
        for row in rows:
            request_id = str(row["request_id"])
            ts = self._parse_ts(str(row["ts"]))
            if ts is None:
                continue
            event_type = str(row["event_type"])
            if event_type == "request_received" and "start" not in spans[request_id]:
                spans[request_id]["start"] = ts
            elif event_type == "completed":
                spans[request_id]["end"] = ts

        durations: list[float] = []
        for span in spans.values():
            if "start" in span and "end" in span and span["end"] >= span["start"]:
                durations.append((span["end"] - span["start"]).total_seconds() * 1000.0)
        return durations

    def _tool_selection_distribution(self, start_ts: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT details
                FROM events
                WHERE event_type = 'tool_attempt'
                  AND ts >= ?
                """,
                (start_ts,),
            ).fetchall()
        counts: dict[str, int] = defaultdict(int)
        for row in rows:
            details = self._parse_details(str(row["details"]))
            tool = details.get("tool")
            if isinstance(tool, str) and tool:
                counts[tool] += 1
        return [{"tool": tool, "count": count} for tool, count in sorted(counts.items(), key=lambda item: item[0])]

    def _risk_distribution(self, start_ts: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT details
                FROM events
                WHERE event_type = 'classified'
                  AND ts >= ?
                """,
                (start_ts,),
            ).fetchall()
        counts: dict[str, int] = defaultdict(int)
        for row in rows:
            details = self._parse_details(str(row["details"]))
            risk = details.get("risk")
            if isinstance(risk, str) and risk:
                counts[risk] += 1
        order = ["low", "medium", "high", "critical"]
        return [{"risk": risk, "count": counts.get(risk, 0)} for risk in order]

    def _policy_precision_proxy_over_time(self, start_ts: str, performance: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT substr(ts, 1, 13) AS hour_key, details
                FROM events
                WHERE event_type = 'policy_block'
                  AND ts >= ?
                """,
                (start_ts,),
            ).fetchall()
        blocked: dict[str, int] = defaultdict(int)
        blocked_unsafe: dict[str, int] = defaultdict(int)
        for row in rows:
            hour_key = str(row["hour_key"])
            details = self._parse_details(str(row["details"]))
            rules = details.get("blocked_rules", [])
            text = " ".join(str(rule) for rule in rules) if isinstance(rules, list) else ""
            blocked[hour_key] += 1
            if any(term in text for term in ["blocked_keyword", "blocked_intent:unsafe", "risk_cap_exceeded:unsafe"]):
                blocked_unsafe[hour_key] += 1

        result: list[dict[str, Any]] = []
        for point in performance:
            hour_key = str(point["hour"]).replace(" ", "T")[:13]
            total = blocked.get(hour_key, 0)
            precision = float(blocked_unsafe.get(hour_key, 0)) / float(total) if total > 0 else 0.0
            result.append({"hour": point["hour"], "precision_proxy": round(precision, 4), "policy_blocks": total})
        return result

    def _tool_error_heatmap(self, start_ts: str) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in ("tool_failure", "timeout"))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, details
                FROM events
                WHERE event_type IN ({})
                  AND ts >= ?
                """.format(placeholders),
                ("tool_failure", "timeout", start_ts),
            ).fetchall()
        counts: dict[tuple[str, str], int] = defaultdict(int)
        for row in rows:
            event_type = str(row["event_type"])
            details = self._parse_details(str(row["details"]))
            tool = str(details.get("tool", "unknown"))
            if event_type == "timeout":
                error_type = "timeout"
            else:
                error = str(details.get("error", "unknown"))
                error_type = self._normalize_error_type(error)
            counts[(tool, error_type)] += 1
        return [
            {"tool": tool, "error_type": error_type, "count": count}
            for (tool, error_type), count in sorted(counts.items(), key=lambda item: (item[0][0], item[0][1]))
        ]

    def _normalize_error_type(self, error: str) -> str:
        lowered = error.lower()
        if "division by zero" in lowered:
            return "division_by_zero"
        if "validation failed" in lowered:
            return "input_validation"
        if "unsupported expression" in lowered:
            return "unsupported_expression"
        return lowered.split(":")[-1].strip().replace(" ", "_")[:40] or "unknown"

    def _percentile(self, values: list[float], percentile: int) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return round(ordered[0], 2)
        k = (len(ordered) - 1) * (float(percentile) / 100.0)
        lower = int(k)
        upper = min(lower + 1, len(ordered) - 1)
        if lower == upper:
            return round(ordered[lower], 2)
        weight = k - lower
        return round((ordered[lower] * (1.0 - weight)) + (ordered[upper] * weight), 2)

    def _parse_details(self, raw: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _parse_ts(self, raw: str) -> datetime | None:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
