from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import load_settings
from app.telemetry.db import TelemetryDB


REMEDIATION_GUIDANCE = {
    "policy_block": "Refine intent/risk classification and review deny rules for false positives.",
    "tool_failure": "Harden tool input handling, add tool-level retries, and expand schema constraints.",
    "timeout": "Tune tool timeout thresholds and add degraded-mode branch for slow tools.",
    "invalid_output": "Tighten output formatting prompts/contracts and increase repair retries cautiously.",
}


def render_markdown(summary: dict[str, object]) -> str:
    by_type = summary.get("by_type", {})
    recent_events = summary.get("recent_events", [])

    lines = [
        "# Incident Summary Report",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Total incidents: {summary.get('total_incidents', 0)}",
        "",
        "## Incident Counts",
    ]

    if not by_type:
        lines.extend(["- No incidents recorded.", ""])
    else:
        for incident_type, count in sorted(by_type.items()):
            lines.append(f"- {incident_type}: {count}")
        lines.append("")

    lines.append("## Remediation Loop Suggestions")
    if not by_type:
        lines.append("- Keep running adversarial scenarios to exercise guardrails.")
    else:
        for incident_type in sorted(by_type.keys()):
            guidance = REMEDIATION_GUIDANCE.get(
                incident_type, "Review logs and add a targeted remediation playbook."
            )
            lines.append(f"- {incident_type}: {guidance}")
    lines.append("")

    lines.append("## Recent Incident Events")
    lines.append("| request_id | ts | step | event_type | success |")
    lines.append("|---|---|---|---|---|")
    if not recent_events:
        lines.append("| - | - | - | - | - |")
    else:
        for event in recent_events:
            lines.append(
                "| {request_id} | {ts} | {step} | {event_type} | {success} |".format(
                    request_id=event.get("request_id", "-"),
                    ts=event.get("ts", "-"),
                    step=event.get("step", "-"),
                    event_type=event.get("event_type", "-"),
                    success=event.get("success", "-"),
                )
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    settings = load_settings()
    db = TelemetryDB(settings.db_path)
    summary = db.incident_summary(limit=25)

    Path("data/incident_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown = render_markdown(summary)
    Path("data/incident_summary.md").write_text(markdown, encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print("\nWrote data/incident_summary.json and data/incident_summary.md")


if __name__ == "__main__":
    main()
