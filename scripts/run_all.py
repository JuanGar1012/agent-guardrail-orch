from __future__ import annotations

import json
import subprocess
import sys
import time
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


def main() -> int:
    python = sys.executable
    steps = [
        ("pytest", [python, "-m", "pytest", "-q"]),
        ("reliability_harness", [python, "scripts/reliability_harness.py"]),
        ("metrics_report", [python, "scripts/metrics_report.py"]),
        ("incident_report", [python, "scripts/incident_report.py"]),
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
    print("\nSummary:")
    print(json.dumps({k: summary[k] for k in ("total_steps", "passed_steps", "failed_steps", "all_passed")}, indent=2))
    print("Wrote data/run_all_summary.json")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
