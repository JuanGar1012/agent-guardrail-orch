from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def run_command(label: str, args: list[str]) -> dict[str, object]:
    start = time.time()
    completed = subprocess.run(args, capture_output=True, text=True)
    duration = round(time.time() - start, 3)
    result = {
        "label": label,
        "command": " ".join(args),
        "exit_code": completed.returncode,
        "duration_s": duration,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "ok": completed.returncode == 0,
    }
    return result


def summarize(results: list[dict[str, object]]) -> dict[str, object]:
    passed = sum(1 for item in results if bool(item["ok"]))
    return {
        "total_steps": len(results),
        "passed_steps": passed,
        "failed_steps": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def load_json(path: str) -> dict[str, object]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def build_eval_dossier(summary: dict[str, object]) -> dict[str, object]:
    metrics = load_json("data/metrics_summary.json")
    reliability = load_json("data/reliability_report.json")
    incidents = load_json("data/incident_summary.json")
    case_study = load_json("reports/case_study_infiltrate.json")

    dossier = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_all_summary": {
            "total_steps": summary.get("total_steps", 0),
            "passed_steps": summary.get("passed_steps", 0),
            "failed_steps": summary.get("failed_steps", 0),
            "all_passed": summary.get("all_passed", False),
        },
        "metrics": {
            "policy_precision_proxy": metrics.get("policy_precision_proxy", 0.0),
            "policy_recall_proxy": metrics.get("policy_recall_proxy", 0.0),
            "task_success_rate": metrics.get("task_success_rate", 0.0),
            "fallback_activation_rate": metrics.get("fallback_activation_rate", 0.0),
            "blocked_unsafe_actions_count": metrics.get("blocked_unsafe_actions_count", 0),
        },
        "reliability": {
            "scenarios_executed": reliability.get("scenarios_executed", 0),
            "results": reliability.get("results", []),
        },
        "incidents": {
            "total_incidents": incidents.get("total_incidents", 0),
            "by_type": incidents.get("by_type", {}),
        },
        "case_study": {
            "scenario": case_study.get("scenario", ""),
            "baseline_allowed": case_study.get("baseline", {}).get("allowed", False),
            "current_allowed": case_study.get("current", {}).get("allowed", False),
            "runtime_status": case_study.get("runtime_validation", {}).get("status", ""),
            "mitigation_verified": bool(
                case_study.get("baseline", {}).get("allowed", True) is True
                and case_study.get("current", {}).get("allowed", True) is False
                and case_study.get("runtime_validation", {}).get("policy_allowed", True) is False
            ),
        },
    }
    return dossier


def render_eval_markdown(dossier: dict[str, object]) -> str:
    run_all = dossier.get("run_all_summary", {})
    metrics = dossier.get("metrics", {})
    reliability = dossier.get("reliability", {})
    incidents = dossier.get("incidents", {})
    case_study = dossier.get("case_study", {})
    reliability_results = reliability.get("results", [])

    lines = [
        "# AI Safety Evaluation Dossier",
        "",
        f"- Generated at: {dossier.get('generated_at', '')}",
        f"- Run status: {'PASS' if run_all.get('all_passed') else 'FAIL'}",
        "",
        "## Pipeline Validation",
        f"- Total steps: {run_all.get('total_steps', 0)}",
        f"- Passed: {run_all.get('passed_steps', 0)}",
        f"- Failed: {run_all.get('failed_steps', 0)}",
        "",
        "## Safety and Reliability Metrics",
        f"- Policy precision proxy: {metrics.get('policy_precision_proxy', 0.0)}",
        f"- Policy recall proxy: {metrics.get('policy_recall_proxy', 0.0)}",
        f"- Task success rate: {metrics.get('task_success_rate', 0.0)}",
        f"- Fallback activation rate: {metrics.get('fallback_activation_rate', 0.0)}",
        f"- Blocked unsafe actions: {metrics.get('blocked_unsafe_actions_count', 0)}",
        "",
        "## Reliability Scenario Outcomes",
    ]

    if isinstance(reliability_results, list) and reliability_results:
        for result in reliability_results:
            scenario = result.get("scenario", "unknown")
            status = result.get("status", "unknown")
            fallback = result.get("fallback_used", False)
            lines.append(f"- {scenario}: status={status}, fallback_used={fallback}")
    else:
        lines.append("- No reliability scenario results found.")

    lines.extend(
        [
            "",
            "## Mitigation Case Study",
            f"- Scenario: {case_study.get('scenario', 'n/a')}",
            f"- Baseline allowed: {case_study.get('baseline_allowed', False)}",
            f"- Current allowed: {case_study.get('current_allowed', False)}",
            f"- Runtime status: {case_study.get('runtime_status', 'unknown')}",
            f"- Mitigation verified: {case_study.get('mitigation_verified', False)}",
            "",
            "## Incident Snapshot",
            f"- Total incidents: {incidents.get('total_incidents', 0)}",
        ]
    )
    by_type = incidents.get("by_type", {})
    if isinstance(by_type, dict) and by_type:
        for incident_type, count in sorted(by_type.items()):
            lines.append(f"- {incident_type}: {count}")
    else:
        lines.append("- No incident data captured.")

    lines.extend(
        [
            "",
            "## Evidence Artifacts",
            "- `data/metrics_summary.json`",
            "- `data/reliability_report.json`",
            "- `data/incident_summary.json`",
            "- `data/run_all_summary.json`",
            "- `reports/case_study_infiltrate.json`",
            "- `reports/case_study_infiltrate.md`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    python = sys.executable
    steps = [
        ("pytest", [python, "-m", "pytest", "-q"]),
        ("reliability_harness", [python, "scripts/reliability_harness.py"]),
        ("metrics_report", [python, "scripts/metrics_report.py"]),
        ("incident_report", [python, "scripts/incident_report.py"]),
        ("case_study_infiltrate", [python, "scripts/case_study_infiltrate.py"]),
    ]

    results: list[dict[str, object]] = []
    for label, args in steps:
        result = run_command(label, args)
        results.append(result)
        status = "PASS" if result["ok"] else "FAIL"
        print(f"[{status}] {label} ({result['duration_s']}s)")
        if result["stdout"]:
            print(result["stdout"])
        if result["stderr"]:
            print(result["stderr"])

    summary = summarize(results)
    Path("data/run_all_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    Path("reports").mkdir(parents=True, exist_ok=True)
    dossier = build_eval_dossier(summary)
    Path("reports/eval_dossier.json").write_text(json.dumps(dossier, indent=2), encoding="utf-8")
    Path("reports/eval_dossier.md").write_text(render_eval_markdown(dossier), encoding="utf-8")
    print("\nSummary:")
    print(json.dumps({k: summary[k] for k in ("total_steps", "passed_steps", "failed_steps", "all_passed")}, indent=2))
    print("Wrote data/run_all_summary.json")
    print("Wrote reports/eval_dossier.json and reports/eval_dossier.md")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
