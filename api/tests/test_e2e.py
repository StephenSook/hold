"""End to end over the API surface, in process, in the order JUDGE.md tells a judge to walk it.
Hermetic: no key, no account, fixtures answer extraction. Every number asserted here comes from
docs/FACTS.json, so a solver regression fails this test as well as the FACTS check."""
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
from api.routes.status import reset_cache

ROOT = Path(__file__).resolve().parents[2]
FACTS = json.loads((ROOT / "docs" / "FACTS.json").read_text(encoding="utf-8"))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    monkeypatch.setenv("HOLD_SOLVE_TIME_LIMIT_S", "60")
    JOBS.clear()
    BUS.clear()
    reset_cache()
    return TestClient(app)


def _demo() -> dict[str, Any]:
    raw = json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _wait(client: TestClient, job_id: str, timeout_s: float = 120.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body: dict[str, Any] = client.get(f"/api/jobs/{job_id}").json()
        if body["status"] in ("done", "failed"):
            assert body["status"] == "done", body.get("error")
            return body
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish in {timeout_s:.0f}s")


def test_judge_walkthrough_end_to_end(client: TestClient) -> None:
    # Step 1: the status page, self-reported, with the committed headline.
    status = client.get("/api/status")
    assert status.status_code == 200
    body = status.json()
    assert body["headline"]["hold_days_before"] == FACTS["hold_days_before"]
    assert body["headline"]["benchmark_matched"] == FACTS["benchmark_matched"]
    assert body["runtime"]["mode"] == "fake externals"

    # Step 2: the routes a judge is pointed at are documented and reachable.
    assert client.get("/api/docs").status_code == 200
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    documented = set(schema.json()["paths"])
    assert {"/api/status", "/api/solve", "/api/jobs/{job_id}", "/api/events", "/api/set-events", "/api/extract", "/api/rules", "/api/bench"} <= documented

    # Step 3: a real solve of the constructed demo, by the shipped solver.
    job_id = client.post("/api/solve", json=_demo()).json()["job_id"]
    solved = _wait(client, job_id)
    pass2 = solved["result"]["pass2"]
    assert pass2["status"] in ("OPTIMAL", "FEASIBLE")
    assert pass2["hold_days"] == FACTS["hold_days_after"] == 0
    used_days = {int(d) for d, ids in solved["day_scene_ids"].items() if ids}
    verdicts = [v for v in solved["result"]["pass1"] if v["day"] in used_days]
    assert verdicts and all(v["status"] == "LEGAL" for v in verdicts), [v["status"] for v in verdicts]

    # Step 4: the hand-built order the demo improves on is the recorded one, and FACTS agrees with it.
    before = json.loads((ROOT / "data" / "demo" / "before-order.json").read_text(encoding="utf-8"))
    assert before["hold_days"] == FACTS["hold_days_before"]
    assert before["illegal_days"] == FACTS["illegal_days_before"]

    # Step 5: set events chain. The second is fired without waiting, so it must build on a plan that is
    # still solving; that is the case a "latest solved job" base silently reverts (round five, finding 1).
    dropped = client.post("/api/set-events", json={"kind": "scene_dropped", "payload": {"scene_id": "s3"}, "source": "ui"})
    assert dropped.status_code == 202, dropped.text
    assert dropped.json()["base_job_id"] == job_id
    late = client.post("/api/set-events", json={"kind": "actor_late", "payload": {"cast_id": "cM", "day_index": 0}, "source": "ui"})
    assert late.status_code == 202, late.text
    assert late.json()["base_job_id"] == dropped.json()["job_id"], "the second event did not chain onto the first"
    resolved = _wait(client, late.json()["job_id"])
    assert "s3" not in {s for ids in resolved["day_scene_ids"].values() for s in ids}, "the dropped scene came back"
    chained = client.get(f"/api/jobs/{late.json()['job_id']}").json()
    assert chained["source"].endswith("actor_late:ui")
    # Assert what the event did, not only that a job appeared: a no-op actor_late kept this green.
    from api.hold.jobs import JOBS

    job = JOBS.get(late.json()["job_id"])
    assert job is not None
    assert any(c.type == "availability" and c.cast_id == "cM" and 0 in (c.unavailable_day_indices or []) for c in job.schedule.constraints), "actor_late left no availability constraint"
    assert "cM" not in {c for sid in resolved["day_scene_ids"].get("0", []) for c in next(s.cast_ids for s in job.schedule.scenes if s.id == sid)}, "the late minor is still on day 0"

    # Step 6: the replayed stream carries the objective and one verdict per shot day, never twice.
    stream = client.get(f"/api/events?job_id={job_id}&replay=true&limit=50&timeout_s=5")
    assert stream.status_code == 200
    events = [json.loads(line[len("data: ") :]) for line in stream.text.splitlines() if line.startswith("data: ")]
    kinds = [e.get("event") for e in events]
    assert "objective" in kinds and kinds.count("verdict") == len(used_days), kinds
    assert len(events) == len({json.dumps(e, sort_keys=True) for e in events}), "an event was delivered twice"

    # Step 7: the registry and the benchmark are served from the committed files.
    rules = client.get("/api/rules").json()
    assert rules["counts"]["records"] == len(rules["records"]) >= 60
    assert rules["counts"]["unverifiable"] == 0 and rules["verification_problems"] == []
    assert any(r["id"].startswith("GA_300_7_1_03") for r in rules["records"])
    assert "GA" in rules["no_trust_statute"] and set(rules["trust"]) >= {"CA", "NY", "IL", "LA", "NM"}
    bench = client.get("/api/bench").json()
    assert bench["benchmark_matched"] == FACTS["benchmark_matched"]

    # Step 8: extraction answers from the recorded fixture while externals are faked. This proves the
    # route is wired, not that the model extracted anything: in fake mode the fixture is returned
    # whatever the body says. The model's own behaviour is covered by the network-marked goldens.
    extracted = client.post("/api/extract", json={"text": (ROOT / "data" / "demo" / "samples" / "callsheet-day3.txt").read_text(encoding="utf-8")})
    assert extracted.status_code == 200 and extracted.json()["status"] == "ok"
    from api.hold.schemas import ExtractResult

    fixture = ExtractResult.model_validate_json((ROOT / "data" / "fixtures" / "contracts" / "extract-result.json").read_text(encoding="utf-8"))
    answer = extracted.json()
    # Compare the parsed models: the committed fixture predates two schema fields, and the route
    # serialises their defaults, so raw JSON differs while the schedule is the same schedule.
    assert ExtractResult.model_validate(answer).schedule == fixture.schedule, "fake mode must answer with the committed contract fixture"
    assert "no model was called" in (answer.get("notes") or ""), "a fixture answer must say it is one"


def test_an_illegal_day_names_its_rule_with_the_statute_sentence(client: TestClient) -> None:
    """The verdict is the product's claim: an illegal day must carry the citation and the words."""
    from api.hold.schemas import ScheduleInput
    from api.hold.solve import pass1_schedule

    fixture = json.loads((ROOT / "data" / "fixtures" / "illegal-days" / "ga-location-hours.json").read_text(encoding="utf-8"))
    schedule = ScheduleInput.model_validate({k: v for k, v in fixture.items() if not k.startswith("_")})
    verdicts = pass1_schedule(schedule, day_scene_ids={int(k): v for k, v in fixture["_day_scene_ids"].items()})
    day = verdicts[fixture["_check_day_index"]].verdict
    assert day.status == "ILLEGAL"
    assert day.violations, "an illegal day with no violation names nothing"
    first = day.violations[0]
    assert first.rule_id and first.citation and first.quote.strip()
    assert first.limit is not None and first.computed is not None
    assert first.source_url.startswith("http")
