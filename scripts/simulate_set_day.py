#!/usr/bin/env python
"""
Task 4.2: a labeled simulation of a shooting day's set events against a running HOLD API.

    uv run python scripts/simulate_set_day.py --api http://localhost:8000 --delay 3

Solves the constructed demo, then posts actor_late, scene_dropped and weather_cover events with
source "simulation" and prints each re-solve's hold days and illegal days. Every event carries
the simulation label on the bus (and on the Confluent topic once task 4.1 lands); nothing here
is presented as a real set.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_EVENTS: list[dict[str, Any]] = [
    {"kind": "actor_late", "payload": {"cast_id": "cB", "day_index": 1}, "source": "simulation"},
    {"kind": "scene_dropped", "payload": {"scene_id": "s6"}, "source": "simulation"},
    {"kind": "weather_cover", "payload": {"day_index": 2}, "source": "simulation"},
]


def _demo() -> dict[str, Any]:
    raw = json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _wait(client: httpx.Client, job_id: str, timeout_s: float) -> dict[str, Any]:
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


def simulate(client: httpx.Client, events: list[dict[str, Any]] = DEFAULT_EVENTS, delay_s: float = 2.0, timeout_s: float = 120.0) -> dict[str, Any]:
    """Run the day: baseline solve, then each event, waiting for its re-solve. Returns the report."""
    schedule = _demo()
    posted = client.post("/api/solve", json=schedule)
    posted.raise_for_status()
    baseline = _wait(client, posted.json()["job_id"], timeout_s)
    report: dict[str, Any] = {"source": "simulation", "constructed": bool(schedule.get("constructed")), "baseline": _summary(baseline), "steps": []}
    for event in events:
        time.sleep(delay_s)
        response = client.post("/api/set-events", json=event)
        response.raise_for_status()
        job = _wait(client, response.json()["job_id"], timeout_s)
        report["steps"].append({"kind": event["kind"], "payload": event["payload"], "change": response.json()["change"], **_summary(job)})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8000", help="base URL of a running HOLD API")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between events, for the video's pacing")
    args = parser.parse_args()
    with httpx.Client(base_url=args.api, timeout=30.0) as client:
        report = simulate(client, delay_s=args.delay)
    print(json.dumps(report, indent=2))
    return 0 if all(step["status"] == "done" for step in report["steps"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
