"""
Task 3.5: the HTTP loop under HOLD_FAKE_EXTERNALS=1. Solve runs on a one-worker thread pool, never
the event loop; objective and verdict events reach /api/events; a set-event re-solves in process;
/api/status answers while a solve is running; extraction is refused in live mode until task 3.1.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.hold.bus import BUS
from api.hold.jobs import JOBS
from api.main import app

ROOT = Path(__file__).parents[2]
DEMO = ROOT / "data" / "demo" / "hold-demo.json"


def _demo() -> dict[str, Any]:
    raw = json.loads(DEMO.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    monkeypatch.setenv("HOLD_SOLVE_TIME_LIMIT_S", "30")
    JOBS.clear()
    BUS.clear()
    return TestClient(app)


def _wait(client: TestClient, job_id: str, timeout_s: float = 90.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body: dict[str, Any] = client.get(f"/api/jobs/{job_id}").json()
        if body["status"] in ("done", "failed"):
            return body
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} did not finish in {timeout_s}s")


def test_solve_job_round_trip_and_status_answers_mid_solve(client: TestClient) -> None:
    posted = client.post("/api/solve", json=_demo())
    assert posted.status_code == 202, posted.text
    job_id = posted.json()["job_id"]
    assert client.get("/api/status").status_code == 200  # never blocked by the solve
    body = _wait(client, job_id)
    assert body["status"] == "done", body.get("error")
    result = body["result"]
    assert result["pass2"]["status"] == "OPTIMAL" and result["pass2"]["hold_days"] == 0
    assert result["checker"]["agrees"] is True
    assert all(v["status"] == "LEGAL" for v in result["pass1"] if v["day"] in {int(d) for d in body["day_scene_ids"]})
    assert client.get("/api/jobs/nope").status_code == 404


def _events(body: str) -> dict[str, list[dict[str, Any]]]:
    seen: dict[str, list[dict[str, Any]]] = {}
    event = ""
    for line in body.splitlines():
        if line.startswith("event: "):
            event = line[len("event: "):]
        elif line.startswith("data: "):
            seen.setdefault(event, []).append(json.loads(line[len("data: "):]))
    return seen


def test_events_carry_objective_and_verdicts(client: TestClient) -> None:
    """The test client returns a response only when the app finishes, so the stream is bounded by limit."""
    job_id = client.post("/api/solve", json=_demo()).json()["job_id"]
    _wait(client, job_id)
    response = client.get(f"/api/events?job_id={job_id}&replay=true&limit=2")
    assert response.headers["content-type"].startswith("text/event-stream")
    seen = _events(response.text)
    assert sum(len(v) for v in seen.values()) == 2
    objective = seen["objective"]
    assert objective and all(e["job_id"] == job_id for e in objective)
    assert "t_ms" in objective[0] and "bound" in objective[0]
    full = _events(client.get(f"/api/events?job_id={job_id}&replay=true&timeout_s=0.2").text)
    assert full["objective"][-1]["value"] == 0
    assert full["verdict"] and all(e["verdict"]["status"] == "LEGAL" for e in full["verdict"])
    assert _events(client.get("/api/events?job_id=nope&replay=true&timeout_s=0.1").text) == {}


def test_set_event_re_solves_in_process(client: TestClient) -> None:
    first = client.post("/api/solve", json=_demo()).json()["job_id"]
    _wait(client, first)
    dropped = client.post("/api/set-events", json={"kind": "scene_dropped", "payload": {"scene_id": "s3"}, "source": "ui"})
    assert dropped.status_code == 202, dropped.text
    second = dropped.json()["job_id"]
    assert second != first
    body = _wait(client, second)
    assert body["status"] == "done", body.get("error")
    assert len(body["result"]["pass2"]["order"]) == 9
    late = client.post("/api/set-events", json={"kind": "actor_late", "payload": {"cast_id": "cM", "day_index": 0}, "source": "simulation"})
    assert late.status_code == 202, late.text
    body = _wait(client, late.json()["job_id"])
    assert body["status"] == "done", body.get("error")
    minor_scenes = {s["id"] for s in _demo()["scenes"] if "cM" in s["cast_ids"]}
    assert not set(body["day_scene_ids"].get("0", [])) & minor_scenes  # the late performer shoots nothing on day 0
    cover = client.post("/api/set-events", json={"kind": "weather_cover", "payload": {"day_index": 1}, "source": "ui"})
    assert cover.status_code == 202, cover.text
    body = _wait(client, cover.json()["job_id"])
    assert body["status"] == "done", body.get("error")
    bad = client.post("/api/set-events", json={"kind": "scene_dropped", "payload": {"scene_id": "s99"}, "source": "ui"})
    assert bad.status_code == 422


def test_extract_is_fixture_in_fake_mode_and_refused_live(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    fake = client.post("/api/extract", json={"text": "INT. POLICE STATION - DAY"})
    assert fake.status_code == 200 and fake.json()["status"] == "ok"
    assert fake.json()["notes"].startswith("fixture")
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "0")
    live = client.post("/api/extract", json={"text": "INT. POLICE STATION - DAY"})
    assert live.status_code == 503 and "GOOGLE_CLOUD_PROJECT" in live.json()["detail"]


def test_rules_and_bench_routes(client: TestClient) -> None:
    rules = client.get("/api/rules").json()
    assert rules["counts"]["records"] == len(rules["records"]) >= 63
    assert set(rules["trust"]) == {"CA", "NY", "IL", "LA", "NM"} and "GA" in rules["no_trust_statute"]
    assert all(r["quote"] for r in rules["records"])
    bench = client.get("/api/bench").json()
    assert bench["benchmark_matched"] == json.loads((ROOT / "bench" / "results.json").read_text())["benchmark_matched"]
