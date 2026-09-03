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


class _Message:
    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    def error(self) -> None:
        return None

    def value(self) -> bytes:
        import json

        return json.dumps(self._value).encode("utf-8")


class _FakeProducer:
    """Stands in for the cluster: a produced set event reaches the API's consumer handler, as the bridge would."""

    def __init__(self) -> None:
        self.produced: list[tuple[str, bytes, bytes]] = []

    def produce(self, topic: str, key: bytes, value: bytes) -> None:
        import json

        from api.routes.events import handle_external_set_event

        self.produced.append((topic, key, value))
        handle_external_set_event(json.loads(value))

    def flush(self, timeout: float) -> int:
        return 0


class _FakeConsumer:
    """Reads the verdicts the job store mirrored (they land on the bus in fake mode) as topic messages."""

    def __init__(self) -> None:
        self.topics: list[str] = []
        self._served = 0

    def subscribe(self, topics: list[str]) -> None:
        self.topics = topics

    def assignment(self) -> list[object]:
        return [object()] if self.topics else []

    def poll(self, timeout: float) -> _Message | None:
        import time

        verdicts = [e for e in BUS.replay(None) if e.get("event") == "verdict"]
        if self._served < len(verdicts):
            self._served += 1
            return _Message(verdicts[self._served - 1])
        time.sleep(min(timeout, 0.05))
        return None

    def close(self) -> None:
        return None


def test_confluent_transport_publishes_events_and_reads_verdicts_from_the_topic(client: TestClient) -> None:
    """4.2 live leg: each event is produced on hold.set-events without a job_id, its re-solve's verdicts are
    read from hold.verdicts, and the pass-2 numbers come from the job the topic named."""
    import json

    from api.hold.streaming import TOPIC_SET_EVENTS, TOPIC_VERDICTS
    from scripts.simulate_set_day import simulate_confluent

    producer, consumer = _FakeProducer(), _FakeConsumer()
    report = simulate_confluent(client, producer, consumer, events=DEFAULT_EVENTS, delay_s=0.0, timeout_s=60.0)
    assert report["transport"] == "confluent" and consumer.topics == [TOPIC_VERDICTS]
    assert [t for t, _, _ in producer.produced] == [TOPIC_SET_EVENTS] * len(DEFAULT_EVENTS)
    assert [k.decode() for _, k, _ in producer.produced] == [e["kind"] for e in DEFAULT_EVENTS]
    for _, _, value in producer.produced:
        payload = json.loads(value)
        assert "job_id" not in payload and payload["source"] == "simulation"
    for step, event in zip(report["steps"], DEFAULT_EVENTS, strict=True):
        assert step["job_id"] and step["round_trip_ms"] >= 0 and step["verdicts_on_topic"] >= 1
        assert step["status"] == "done"
        job = JOBS.get(step["job_id"])
        assert job is not None
        assert job.source == f"confluent:{event['kind']}:simulation", (step["kind"], job.source)  # round six, finding 1
    assert len({step["job_id"] for step in report["steps"]}) == len(DEFAULT_EVENTS)
    assert report_ok(report)
