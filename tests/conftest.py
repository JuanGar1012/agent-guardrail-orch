from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_orchestrator
from app.main import app
from app.tools.task_mock import TASKS


@pytest.fixture(autouse=True)
def reset_state() -> None:
    get_orchestrator.cache_clear()
    TASKS.clear()

    cleanup_targets = [
        Path("data/metrics_summary.json"),
        Path("data/reliability_report.json"),
        Path("data/incident_summary.json"),
        Path("data/incident_summary.md"),
        Path("data/run_all_summary.json"),
    ]
    for target in cleanup_targets:
        if target.exists():
            try:
                target.unlink()
            except PermissionError:
                pass

    db_path = Path("data/telemetry.db")
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute("DELETE FROM events")
                conn.commit()
        except sqlite3.OperationalError:
            pass


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
