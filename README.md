# Agent Guardrails + Orchestration Control Plane

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Production-style AI orchestration system for local safety controls, deterministic routing, tool governance, failure handling, and observability.

This project is **Local-first and zero-cost by design.**

- Fully local execution
- No paid APIs required
- No cloud dependency required

## 1. Project Overview

This system implements a guarded AI request pipeline behind a FastAPI service and a React control plane.
It is designed to answer a practical AI engineering problem: how to run LLM-like workflows with explicit policy enforcement, operational telemetry, and reproducible evaluation loops.

Core behavior:
- Accept user requests through `/agent/run`
- Classify intent and risk
- Route to direct response, retrieval, or tool workflow
- Enforce policy rules before tool execution
- Validate response payloads against JSON Schema
- Fall back safely when policy/tool/validation checks fail
- Persist decision and incident events in SQLite for postmortem analysis

This architecture maps to modern LLM systems where orchestration reliability and safety constraints are as important as generation quality.

## 2. Key Capabilities

- Policy-driven request gating
  - Blocks unsafe keywords/intents and unauthorized tools before execution.
  - Solves governance and blast-radius control problems in agent systems.
- Intent/risk classification with routing hints
  - Supports deterministic heuristics with optional local Ollama classification.
  - Solves controllability and routing consistency.
- Tool orchestration with input schema validation and timeout handling
  - Tools (`doc_search`, `calculator`, `task_mock`) are strongly typed with Pydantic.
  - Solves malformed input and long-tail runtime fault handling.
- Structured output validation + repair/fallback
  - Output is checked against `config/output_schema.json`.
  - Solves malformed contracts between orchestrator and downstream consumers.
- Incident operations and observability
  - Captures policy blocks, tool failures, timeouts, invalid output, and status workflows.
  - Solves production debugging and remediation tracking.
- Reproducible local evaluation pipeline
  - Includes benchmark scenarios, reliability harness, metrics reports, and mitigation case studies.
  - Solves repeatable assessment of safety/reliability changes over time.

## 3. System Architecture

Major components:
- API layer: FastAPI endpoints for run, policy management, incidents, observability, reset.
- Orchestration core: classifier -> router -> policy engine -> tool runner -> output validator -> fallback manager.
- Tool layer: local tools with typed input contracts and bounded execution.
- Data layer: SQLite event store for timeline, trends, and operational metrics.
- Evaluation layer: scripts to run deterministic scenarios and produce reports.
- UI layer: React control plane for operations, policy tuning, incident response, and observability.

### Data Flow (ASCII Diagram)

```text
User / UI
   |
   v
[POST /agent/run]
   |
   v
[Classifier]
   |
   v
[Router]
   |
   v
[Policy Engine] ---- deny ----> [Fallback Manager] ----> [Safe Response]
   |
  allow
   |
   v
[Tool Runner or Direct Path]
   |
   v
[Output Validator]
   |            \
 valid           invalid after retries
   |              \
   v               v
[Success Response] [Fallback Manager -> Safe Response]
   |
   v
[SQLite Telemetry + Incident/Observability APIs]
```

Layer purpose:
- Classifier: determines intent/risk/route hint.
- Router: normalizes final route selection.
- Policy Engine: checks keyword, intent, risk-cap, and tool allowlist rules.
- Tool Runner: executes typed local tools with timeout boundaries.
- Output Validator: enforces contract integrity via JSON Schema.
- Fallback Manager: guarantees deterministic safe-mode output on failure.
- TelemetryDB: stores event trail used by incident feed/detail/trend and observability metrics.

## 4. Repository Structure

```text
app/
  api/          FastAPI routes for run, policies, incidents, observability, reset, health
  core/         Classifier, router, policy engine, orchestrator, validator, fallback, settings
  telemetry/    SQLite-backed event logging and incident/observability queries
  tools/        Local tools: corpus search, safe calculator, task workflow mock
  models/       Request/response schemas for API contracts
config/
  policies.yaml        Safety and tool-governance policy rules
  settings.yaml        Runtime configuration (timeouts, db path, optional Ollama)
  output_schema.json   JSON schema for response validation
data/
  corpus/       Local Markdown corpus for retrieval tests
  *.json        Generated evaluation and incident artifacts
frontend/
  src/          React + TypeScript control plane pages and API client
scripts/
  run_all.py                End-to-end verification pipeline
  reliability_harness.py    Failure-path scenarios (timeout/tool failure/malformed output)
  metrics_report.py         Deterministic benchmark scoring
  incident_report.py        Incident summary + remediation guidance
  case_study_infiltrate.py  Before/after mitigation evidence report
tests/
  pytest suite for policies, reliability, incidents, dashboard/observability, reset workflows
```

## 5. Installation and Local Setup

### Backend (Python)

Prerequisites:
- Python 3.11+ recommended
- Windows PowerShell commands shown below (adapt as needed for Linux/macOS)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run API:

```powershell
uvicorn app.main:app --reload
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

### Frontend (Optional Control Plane)

```powershell
cd frontend
cmd /c npm install
cmd /c npm run dev
```

URLs:
- API: `http://127.0.0.1:8000`
- UI: `http://127.0.0.1:5173`

### Verification and Reproducibility

Run tests:

```powershell
pytest -q
```

Run full local evaluation pipeline:

```powershell
python scripts/run_all.py
```

Generated artifacts:
- `data/reliability_report.json`
- `data/metrics_summary.json`
- `data/incident_summary.json`
- `data/run_all_summary.json`
- `reports/eval_dossier.json`
- `reports/case_study_infiltrate.json`

All commands run locally with open-source tooling only.

## 6. Example Usage

Example input:

```json
{
  "text": "calculate 6 * 7"
}
```

Example processing path:
1. Classifier identifies `intent=math`, `risk=low`, `route_hint=tool_workflow`.
2. Router selects `tool_workflow`.
3. Policy engine validates intent risk cap and tool allowlist.
4. Tool runner executes `calculator`.
5. Output validator checks schema contract.
6. API returns structured success response and logs all steps to telemetry.

Example output shape:

```json
{
  "request_id": "uuid",
  "status": "success",
  "route": "tool_workflow",
  "intent": "math",
  "risk": "low",
  "fallback_used": false,
  "tool_results": {
    "tool": "calculator",
    "result": { "expression": "6 * 7", "result": 42.0 }
  },
  "policy": {
    "allowed": true,
    "reason": "Request allowed by policy.",
    "blocked_rules": [],
    "allowed_tools": ["calculator"]
  },
  "errors": []
}
```

Unsafe input behavior example:
- Input containing `exfiltrate` or `infiltrate` is policy-blocked.
- System returns `status="safe_fallback"` with explicit blocked rule evidence.

## 7. AI Evaluation Methodology

Evaluation is intentionally deterministic and scriptable:
- `scripts/benchmark_scenarios.json` defines expected safety outcomes.
- `scripts/metrics_report.py` computes confusion-matrix proxy and aggregate KPIs.
- `scripts/reliability_harness.py` exercises failure modes (tool failure, timeout, malformed output).
- `scripts/case_study_infiltrate.py` validates mitigation effectiveness with before/after evidence.
- `scripts/run_all.py` runs the entire pipeline and emits dossier artifacts.

Tracked metrics:
- `policy_precision_proxy`
- `policy_recall_proxy`
- `blocked_unsafe_actions_count`
- `task_success_rate`
- `fallback_activation_rate`
- Confusion matrix proxy (`tp`, `fp`, `fn`, `tn`)
- Observability metrics from telemetry:
  - latency percentiles (`p50`, `p95`, `p99`)
  - tool selection distribution
  - risk histogram
  - fallback trend over time
  - policy precision proxy over time
  - tool error heatmap

This structure demonstrates engineering rigor by separating:
- correctness expectations (scenario definitions)
- runtime behavior (telemetry events)
- summary metrics (report artifacts)

## 8. Guardrails and Safety Mechanisms

Safety controls implemented in code:
- Keyword and intent blocks (`config/policies.yaml`, `PolicyEngine`)
- Intent-level risk caps (e.g., disallow high-risk outcomes for capped intents)
- Tool allowlist + per-intent tool permissions
- Preferred-tool authorization checks (`tool_not_allowed`, `tool_not_allowlisted`)
- Pydantic input validation for all tool calls
- Tool timeout enforcement (`asyncio.wait_for`)
- JSON Schema output validation with limited repair attempts
- Safe fallback response for policy blocks, tool failures, timeouts, and invalid output
- Full event logging for every decision step and incident-type extraction

Prompt-injection and unsafe-output posture:
- Requests are not executed as arbitrary shell/code tools.
- Tool selection is constrained by explicit policy intersection.
- Unsafe language patterns are classified and blocked early.
- Structured output contract prevents malformed response payloads from passing through.

## 9. Failure Modes and Limitations

Known limitations and tradeoffs:
- Retrieval is lexical term-count matching over local Markdown corpus, not semantic vector retrieval.
- Heuristic classification can miss nuanced unsafe intent phrasing outside current term coverage.
- Optional Ollama classification has a short timeout and may fall back to heuristics frequently.
- SQLite event store is appropriate for local/single-node usage, not high-write distributed workloads.
- Policy precision/recall are proxy metrics based on synthetic scenarios, not ground-truth human labeling at scale.
- Strict output schema can increase fallback rate if payload builders drift from schema contracts.
- Timeout thresholds are fixed and may require environment-specific tuning.

## 10. Future Improvements

High-value next steps:
- Add semantic embeddings + vector retrieval with reranking (still local-only stack).
- Expand adversarial benchmark dataset with mutation-based prompt variants.
- Add per-intent calibration and confidence scoring in classifier outputs.
- Introduce tool-level circuit breakers and retry budget policies.
- Add policy versioning + signed change history for auditability.
- Add richer incident triage workflows (owner assignment, SLA timers).
- Extend observability with request-cost proxies and workload class segmentation.
- Add packaging for reproducible local deployment profiles (dev/test/demo presets).

## 11. Why This Project Matters for AI Engineering

This project demonstrates practical AI engineering competencies expected in production-oriented roles:
- LLM/agent system design with explicit control-flow and policy gates
- Safety engineering beyond prompt text (policy, typed tools, schema validation, fallback)
- Reliability engineering for failure-path handling and incident operations
- Evaluation discipline with deterministic scenarios and machine-generated evidence artifacts
- Backend integration patterns (FastAPI, dependency injection, contracts, orchestration)
- Operational telemetry and observability mindset
- Local-first, reproducible AI workflow design without paid API lock-in

It is intentionally built as a realistic control-plane system, not a toy single-prompt demo.

## 12. License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for details.
