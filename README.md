# Agent Guardrails + Orchestration Starter

Production-style FastAPI scaffold for a local-only (zero API cost) agent system with policy guardrails, tool controls, structured-output validation, fallback behavior, and SQLite audit telemetry.

## Stack
- Python + FastAPI
- SQLite audit/event store
- Local tools only
- Optional local LLM classification via Ollama (`config/settings.yaml`)

## Project Structure
```text
app/
  api/
    routes_agent.py
    routes_health.py
  core/
    classifier.py
    router.py
    policy_engine.py
    tool_runner.py
    output_validator.py
    fallback_manager.py
    orchestrator.py
    settings.py
  telemetry/
    db.py
    events.py
  tools/
    doc_search.py
    calculator.py
    task_mock.py
config/
  policies.yaml
  settings.yaml
  output_schema.json
data/
  corpus/*.md
scripts/
  reliability_harness.py
  benchmark_scenarios.json
  metrics_report.py
  incident_report.py
  run_all.py
frontend/
  src/App.tsx
  src/lib/api.ts
  src/components/ThemeToggle.tsx
  src/styles/index.css
  package.json
tests/
  test_policies.py
  test_reliability.py
```

## Architecture Diagram
```mermaid
flowchart TD
    A[/POST /agent/run/] --> B[Classifier]
    B --> C[Router]
    C --> D[Policy Engine]
    D -->|deny| E[Fallback Manager]
    D -->|allow| F{Route}
    F -->|direct| G[Direct Response Builder]
    F -->|retrieval| H[Tool Runner: doc_search]
    F -->|tool_workflow| I[Tool Runner: calculator/task_mock]
    H --> J[Output Validator]
    I --> J
    G --> J
    J -->|invalid+retry fail| E
    J -->|valid| K[Response]
    B --> L[(SQLite Telemetry)]
    C --> L
    D --> L
    H --> L
    I --> L
    J --> L
    E --> L
```

## Setup (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run API
```powershell
uvicorn app.main:app --reload
```

Expected startup snippet:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Quick Endpoint Checks
```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/agent/policies
```

Expected `/health` snippet:
```json
{"status":"ok"}
```

## Tests
```powershell
pytest -q
```

Expected snippet:
```text
7 passed
```

## One-Command Verification (Python)
```powershell
python scripts/run_all.py
```

Runs in order:
- tests
- reliability harness
- metrics report
- incident summary report

Writes `data/run_all_summary.json`.

## Reliability Harness
```powershell
python scripts/reliability_harness.py
```

Writes `data/reliability_report.json`.

## Metrics Report
```powershell
python scripts/metrics_report.py
```

Writes `data/metrics_summary.json` with:
- `policy_precision_proxy`
- `policy_recall_proxy`
- `blocked_unsafe_actions_count`
- `task_success_rate`
- `fallback_activation_rate`

## Incident Summary Report
```powershell
python scripts/incident_report.py
```

Writes:
- `data/incident_summary.json`
- `data/incident_summary.md`

## Frontend (React + Tailwind)
Open a second terminal:

```powershell
cd frontend
cmd /c npm install
cmd /c npm run dev
```

Frontend URL:
```text
http://127.0.0.1:5173
```

Frontend includes:
- Incident Explorer with per-request incident drill-down (`why blocked/failed`, timeline, and raw event details)
- Interactive rolling 24-hour performance charts (throughput/outcomes + incident type distribution)
- One-click `Reset Data` control to return runtime state to a first-run baseline

Backend URL (keep API running):
```text
http://127.0.0.1:8000
```

Optional API base override:
```powershell
copy .env.example .env
```

## API Endpoints
- `POST /agent/run`
- `POST /agent/reset`
- `GET /agent/policies`
- `GET /agent/incidents`
- `GET /agent/incidents/feed`
- `GET /agent/incidents/{request_id}`
- `GET /agent/dashboard`
- `GET /health`

## Replace These Placeholders
- Policies: edit `config/policies.yaml`
  - Replace keyword lists, risk caps, and intent-to-tool mapping with your real policy.
- Tools: extend `app/tools/` and register in `app/core/tool_runner.py`
  - Replace mock `task_mock` behavior with real local workflow logic.
- Classifier behavior: tune `app/core/classifier.py`
  - Replace heuristics with stronger local model prompts/rubrics.
- Benchmark scenarios: update `scripts/benchmark_scenarios.json`
  - Replace starter scenarios with your own domain-safe and adversarial set.
- Corpus: replace `data/corpus/*.md`
  - Add realistic local docs for retrieval benchmarking.

## Tradeoffs (Minimal Dependency Design)
- Heuristic-first classification is deterministic and cheap, but less nuanced than stronger local model setups.
- SQLite telemetry is local and portable, but not intended for high-write distributed systems.
- JSON schema enforcement improves safety; strict schemas can increase fallback rate until prompts/tool outputs are tuned.
