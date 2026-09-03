"""Task 4.2: the labeled set-day simulation drives the HTTP loop and reports every verdict flip."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.hold.bus import BUS
from api.hold.jobs import JOBS
from api.main import app
from scripts.simulate_set_day import DEFAULT_EVENTS, report_ok, simulate


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    monkeypatch.setenv("HOLD_SOLVE_TIME_LIMIT_S", "30")
    JOBS.clear()
    BUS.clear()
    return TestClient(app)


def test_simulation_runs_every_event_and_labels_its_source(client: TestClient) -> None:
    report = simulate(client, events=DEFAULT_EVENTS, delay_s=0.0)
    assert report["source"] == "simulation" and report["constructed"] is True
    assert [step["kind"] for step in report["steps"]] == [e["kind"] for e in DEFAULT_EVENTS]
    assert all(step["status"] == "done" for step in report["steps"]), report["steps"]
    assert report["baseline"]["hold_days"] == 0 and report["baseline"]["illegal_days"] == 0
    assert all("illegal_days" in step and "hold_days" in step for step in report["steps"])


def test_report_ok_refuses_failed_undetermined_or_illegal_runs() -> None:
    """Round four, finding 8: a done step with an UNDETERMINED solve or an illegal day is not a success."""
    good: dict[str, Any] = {"baseline": {"status": "done", "pass2_status": "OPTIMAL", "illegal_days": 0, "undetermined_days": 0}, "steps": [{"status": "done", "pass2_status": "OPTIMAL", "illegal_days": 0, "undetermined_days": 0}]}
    assert report_ok(good)
    assert not report_ok({**good, "baseline": {**good["baseline"], "status": "failed"}})
    assert not report_ok({**good, "steps": [{**good["steps"][0], "pass2_status": "UNDETERMINED"}]})
    assert not report_ok({**good, "steps": [{**good["steps"][0], "illegal_days": 2}]})
    assert not report_ok({**good, "steps": [{**good["steps"][0], "status": "failed"}]})
