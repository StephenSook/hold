#!/usr/bin/env python
"""
Task 4.2: a labeled simulation of a shooting day's set events against a running HOLD API.

    uv run python scripts/simulate_set_day.py --api http://localhost:8000 --delay 3
    uv run python scripts/simulate_set_day.py --api https://<cloud-run-url> --transport confluent

Solves the constructed demo, then sends actor_late, scene_dropped and weather_cover events with
source "simulation" and prints each re-solve's hold days and illegal days. Over HTTP the events
are POSTed to /api/set-events. Over Confluent (CONFLUENT_BOOTSTRAP, CONFLUENT_API_KEY and
CONFLUENT_API_SECRET in the environment) each event is produced on hold.set-events with no
job_id, the API's consumer re-solves it, and the verdicts are read back from hold.verdicts; the
round trip is timed from produce to the first verdict. Every event carries the simulation
label; nothing here is presented as a real set.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.hold.streaming import TOPIC_SET_EVENTS, TOPIC_VERDICTS, ConfluentConfig  # noqa: E402

# The client is httpx.Client from main() or the FastAPI TestClient from the tests; the two stop sharing a
# base class once httpx2 is installed beside httpx, so the parameter is typed Any and used as .get / .post.

DEFAULT_EVENTS: list[dict[str, Any]] = [
    {"kind": "actor_late", "payload": {"cast_id": "cB", "day_index": 1}, "source": "simulation"},
    {"kind": "scene_dropped", "payload": {"scene_id": "s6"}, "source": "simulation"},
    {"kind": "weather_cover", "payload": {"day_index": 2}, "source": "simulation"},
]


def _demo() -> dict[str, Any]:
    raw = json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _wait(client: Any, job_id: str, timeout_s: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body: dict[str, Any] = client.get(f"/api/jobs/{job_id}").json()
        if body["status"] in ("done", "failed"):
            return body
        time.sleep(0.2)
    raise TimeoutError(f"job {job_id} did not finish in {timeout_s:.0f}s")


def _summary(body: dict[str, Any]) -> dict[str, Any]:
    result = body.get("result") or {}
    used = {int(d) for d, ids in (body.get("day_scene_ids") or {}).items() if ids}
    verdicts = [v for v in result.get("pass1", []) if v["day"] in used]
    return {
        "status": body["status"],
        "hold_days": result.get("pass2", {}).get("hold_days"),
        "holding_cents": result.get("pass2", {}).get("holding_cents"),
        "illegal_days": sum(v["status"] == "ILLEGAL" for v in verdicts),
        "undetermined_days": sum(v["status"] == "UNDETERMINED" for v in verdicts),
        "pass2_status": result.get("pass2", {}).get("status"),
        "error": body.get("error"),
    }


def simulate(client: Any, events: list[dict[str, Any]] = DEFAULT_EVENTS, delay_s: float = 2.0, timeout_s: float = 120.0) -> dict[str, Any]:
    """Run the day over HTTP: baseline solve, then each event, waiting for its re-solve. Returns the report."""
    schedule, baseline = _baseline(client, timeout_s)
    report: dict[str, Any] = {"source": "simulation", "transport": "http", "constructed": bool(schedule.get("constructed")), "baseline": _summary(baseline), "steps": []}
    for event in events:
        time.sleep(delay_s)
        response = client.post("/api/set-events", json=event)
        response.raise_for_status()
        job = _wait(client, response.json()["job_id"], timeout_s)
        report["steps"].append({"kind": event["kind"], "payload": event["payload"], "change": response.json()["change"], **_summary(job)})
    return report


def _baseline(client: Any, timeout_s: float) -> tuple[dict[str, Any], dict[str, Any]]:
    schedule = _demo()
    posted = client.post("/api/solve", json=schedule)
    posted.raise_for_status()
    return schedule, _wait(client, posted.json()["job_id"], timeout_s)


def _await_assignment(consumer: Any, timeout_s: float) -> None:
    """A fresh consumer group reading from the latest offset sees nothing produced before its partitions
    are assigned, so no event is produced until the assignment exists."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        consumer.poll(0.5)
        if consumer.assignment():
            return
    raise TimeoutError(f"no partition assignment on {TOPIC_VERDICTS} in {timeout_s:.0f}s")


def _first_new_verdict(consumer: Any, seen_jobs: set[str], deadline: float) -> str:
    """The job_id of the first verdict on the topic that belongs to a job not seen before."""
    while time.monotonic() < deadline:
        message = consumer.poll(1.0)
        if message is None or message.error():
            continue
        payload = json.loads(message.value())
        job_id = payload.get("job_id")
        if payload.get("event") == "verdict" and job_id and job_id not in seen_jobs:
            return str(job_id)
    raise TimeoutError(f"no verdict for a new job arrived on {TOPIC_VERDICTS} before the deadline")


def _drain(consumer: Any, job_id: str, quiet_s: float = 1.0) -> int:
    """Count further verdicts for the job until the topic goes quiet."""
    count = 0
    while True:
        message = consumer.poll(quiet_s)
        if message is None:
            return count
        if message.error():
            continue
        if json.loads(message.value()).get("job_id") == job_id:
            count += 1


def simulate_confluent(
    client: Any,
    producer: Any,
    consumer: Any,
    events: list[dict[str, Any]] = DEFAULT_EVENTS,
    delay_s: float = 2.0,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """The same day over the cluster: baseline over HTTP (the API re-solves its latest schedule), then each
    event produced on hold.set-events and its verdicts read from hold.verdicts."""
    schedule, baseline = _baseline(client, timeout_s)
    report: dict[str, Any] = {"source": "simulation", "transport": "confluent", "constructed": bool(schedule.get("constructed")), "baseline": _summary(baseline), "steps": []}
    consumer.subscribe([TOPIC_VERDICTS])
    _await_assignment(consumer, timeout_s)
    seen_jobs: set[str] = set()
    try:
        for event in events:
            time.sleep(delay_s)
            started = time.monotonic()
            producer.produce(TOPIC_SET_EVENTS, key=event["kind"].encode("utf-8"), value=json.dumps(event, separators=(",", ":")).encode("utf-8"))
            producer.flush(10.0)
            job_id = _first_new_verdict(consumer, seen_jobs, started + timeout_s)
            round_trip_ms = round((time.monotonic() - started) * 1000, 1)
            seen_jobs.add(job_id)
            job = _wait(client, job_id, timeout_s)
            verdicts_on_topic = 1 + _drain(consumer, job_id)
            report["steps"].append({"kind": event["kind"], "payload": event["payload"], "job_id": job_id, "round_trip_ms": round_trip_ms, "verdicts_on_topic": verdicts_on_topic, **_summary(job)})
    finally:
        consumer.close()
    return report


def report_ok(report: dict[str, Any]) -> bool:
    """Success means every solve finished with a decided plan and no illegal or undetermined day."""
    runs = [report["baseline"], *report["steps"]]
    return all(
        r.get("status") == "done" and r.get("pass2_status") in ("OPTIMAL", "FEASIBLE") and not r.get("illegal_days") and not r.get("undetermined_days")
        for r in runs
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000", help="base URL of a running HOLD API")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between events, for the video's pacing")
    parser.add_argument("--transport", choices=("http", "confluent"), default="http", help="confluent needs the CONFLUENT_* variables")
    args = parser.parse_args()
    with httpx.Client(base_url=args.api, timeout=30.0) as client:
        if args.transport == "confluent":
            config = ConfluentConfig.from_env()
            if config is None:
                print("CONFLUENT_BOOTSTRAP, CONFLUENT_API_KEY and CONFLUENT_API_SECRET are needed for --transport confluent", file=sys.stderr)
                return 2
            from confluent_kafka import Consumer, Producer

            producer = Producer(config.client_config())
            consumer = Consumer({**config.client_config(), "group.id": f"hold-sim-{uuid.uuid4().hex[:8]}", "auto.offset.reset": "latest"})
            report = simulate_confluent(client, producer, consumer, delay_s=args.delay)
        else:
            report = simulate(client, delay_s=args.delay)
    print(json.dumps(report, indent=2))
    return 0 if report_ok(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
