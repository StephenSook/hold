"""The judge walk against the deployed URL. Network-marked: CI runs `-m "not network"`; run it by hand
with `uv run pytest -m network api/tests/test_e2e_live.py`. This is the one-command answer to
"does the thing a judge opens still work"."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
FACTS = json.loads((ROOT / "docs" / "FACTS.json").read_text(encoding="utf-8"))
URL = os.environ.get("HOLD_URL", "https://hold-fwmdq7fc3q-uc.a.run.app")

pytestmark = pytest.mark.network


def _get(path: str, timeout_s: float = 60.0) -> tuple[int, str]:
    request = urllib.request.Request(f"{URL}{path}", headers={"User-Agent": "HOLD e2e"})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return response.status, response.read().decode("utf-8", "ignore")


def _post(path: str, payload: dict[str, Any], timeout_s: float = 120.0) -> dict[str, Any]:
    request = urllib.request.Request(f"{URL}{path}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return dict(json.loads(response.read()))


def _demo() -> dict[str, Any]:
    raw = json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _wait(job_id: str, timeout_s: float = 180.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        _, body = _get(f"/api/jobs/{job_id}")
        job = json.loads(body)
        if job["status"] in ("done", "failed"):
            assert job["status"] == "done", job.get("error")
            return dict(job)
        time.sleep(1.0)
    raise AssertionError(f"job {job_id} did not finish in {timeout_s:.0f}s on {URL}")


def test_the_deployed_url_walks_the_judge_path() -> None:
    status_code, raw = _get("/api/status")
    assert status_code == 200
    status = json.loads(raw)
    assert status["headline"]["benchmark_matched"] == FACTS["benchmark_matched"]
    assert status["runtime"]["mode"] in ("live", "fake externals")
    assert status["bob_usage"]["available"] is True

    assert _get("/api/docs")[0] == 200
    documented = set(json.loads(_get("/openapi.json")[1])["paths"])
    assert {"/api/status", "/api/solve", "/api/events", "/api/set-events", "/api/rules", "/api/bench"} <= documented

    job_id = _post("/api/solve", _demo())["job_id"]
    solved = _wait(job_id)
    assert solved["result"]["pass2"]["hold_days"] == FACTS["hold_days_after"]
    used = {int(d) for d, ids in solved["day_scene_ids"].items() if ids}
    assert all(v["status"] == "LEGAL" for v in solved["result"]["pass1"] if v["day"] in used)

    # Two events without waiting: the second must chain onto a plan that is still solving, which is
    # the case a "latest solved job" base silently reverts (round five, finding 1; round ten, finding 3).
    event = _post("/api/set-events", {"kind": "scene_dropped", "payload": {"scene_id": "s3"}, "source": "ui"})
    assert event["base_job_id"] == job_id and event["transport"] in ("confluent", "in-process")
    # A day the minor actually works, so the post-condition cannot hold by accident (round eleven).
    scene_cast = {s["id"]: s["cast_ids"] for s in _demo()["scenes"]}
    worked = sorted(int(d) for d, ids in solved["day_scene_ids"].items() if any("cM" in scene_cast[s] for s in ids))
    assert worked, "the minor works no day in the deployed plan, so actor_late would prove nothing"
    late_day = worked[0]
    late = _post("/api/set-events", {"kind": "actor_late", "payload": {"cast_id": "cM", "day_index": late_day}, "source": "ui"})
    assert late["base_job_id"] == event["job_id"], "the deployed service did not chain the second event"
    resolved = _wait(late["job_id"])
    assert "s3" not in {s for ids in resolved["day_scene_ids"].values() for s in ids}
    still_on = [s for s in resolved["day_scene_ids"].get(str(late_day), []) if "cM" in scene_cast[s]]
    assert not still_on, f"the deployed plan still works the minor on day {late_day}: {still_on}"

    _, stream = _get(f"/api/events?job_id={job_id}&replay=true&limit=40&timeout_s=8", timeout_s=60)
    events = [json.loads(line[len("data: ") :]) for line in stream.splitlines() if line.startswith("data: ")]
    assert [e for e in events if e.get("event") == "verdict"], "no verdict replayed for the solve"
    assert len(events) == len({json.dumps(e, sort_keys=True) for e in events}), "an event was delivered twice"

    rules = json.loads(_get("/api/rules")[1])
    assert rules["counts"]["unverifiable"] == 0 and rules["verification_problems"] == []
    assert json.loads(_get("/api/bench")[1])["benchmark_matched"] == FACTS["benchmark_matched"]
