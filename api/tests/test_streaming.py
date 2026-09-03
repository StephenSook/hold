"""
Task 4.1: the Confluent leg, tested against fakes (CI has no broker). connected is true only after
a real metadata call; the in-process bus stays the fallback; a message from another producer on
hold.set-events re-solves; a mirrored or malformed message is skipped; verdicts go to hold.verdicts.
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
from api.hold.streaming import TOPIC_SET_EVENTS, TOPIC_VERDICTS, ConfluentBridge, ConfluentConfig
from api.main import app

ROOT = Path(__file__).parents[2]
CONFIG = ConfluentConfig(bootstrap="pkc-test.us-central1.gcp.confluent.cloud:9092", api_key="k", api_secret="s")


class FakeProducer:
    def __init__(self, cfg: dict[str, Any], *, fail_metadata: bool = False) -> None:
        self.cfg = cfg
        self.fail_metadata = fail_metadata
        self.messages: list[tuple[str, str, dict[str, Any]]] = []
        self.flushed = False

    def list_topics(self, timeout: float = 0) -> object:
        if self.fail_metadata:
            raise RuntimeError("broker unreachable")
        return object()

    def produce(self, topic: str, key: bytes, value: bytes) -> None:
        self.messages.append((topic, key.decode(), json.loads(value)))

    def poll(self, timeout: float = 0) -> int:
        return 0

    def flush(self, timeout: float = 0) -> int:
        self.flushed = True
        return 0


class FakeMessage:
    def __init__(self, value: bytes, error: object | None = None) -> None:
        self._value, self._error = value, error

    def value(self) -> bytes:
        return self._value

    def error(self) -> object | None:
        return self._error


class FakeConsumer:
    def __init__(self, cfg: dict[str, Any], messages: list[FakeMessage]) -> None:
        self.cfg = cfg
        self.queue = list(messages)
        self.subscribed: list[str] = []
        self.closed = False

    def subscribe(self, topics: list[str]) -> None:
        self.subscribed = topics

    def poll(self, timeout: float) -> FakeMessage | None:
        return self.queue.pop(0) if self.queue else None

    def close(self) -> None:
        self.closed = True


def test_unconfigured_bridge_is_the_in_process_fallback() -> None:
    bridge = ConfluentBridge(None)
    assert bridge.start() is False
    assert bridge.publish(TOPIC_VERDICTS, "j", {"event": "verdict"}) is False
    status = bridge.status()
    assert status["connected"] is False and status["bootstrap_configured"] is False and status["transport"] == "in-process"


def test_connected_only_after_a_real_metadata_call() -> None:
    down = ConfluentBridge(CONFIG, producer_factory=lambda cfg: FakeProducer(cfg, fail_metadata=True))
    assert down.start() is False and down.connected is False and "broker unreachable" in (down.last_error or "")
    assert down.status()["transport"] == "in-process" and down.status()["bootstrap_configured"] is True
    up = ConfluentBridge(CONFIG, producer_factory=FakeProducer)
    assert up.start() is True and up.connected is True and up.status()["transport"] == "confluent"
    assert up.status()["topics"] == [TOPIC_SET_EVENTS, TOPIC_VERDICTS]
    assert "sasl.password" not in json.dumps(up.status())  # secrets never leave the process
    up.stop()


def test_publish_carries_the_json_payload_keyed_by_job() -> None:
    bridge = ConfluentBridge(CONFIG, producer_factory=FakeProducer)
    bridge.start()
    assert bridge.publish(TOPIC_VERDICTS, "job1", {"event": "verdict", "job_id": "job1"}) is True
    producer = bridge.producer
    assert isinstance(producer, FakeProducer)
    assert producer.messages == [(TOPIC_VERDICTS, "job1", {"event": "verdict", "job_id": "job1"})]
    assert bridge.status()["published"] == 1
    bridge.stop()
    assert producer.flushed


def test_consumer_re_solves_external_events_and_skips_mirrored_and_bad_ones() -> None:
    external = {"event": "set-event", "kind": "scene_dropped", "payload": {"scene_id": "s6"}, "source": "simulation"}
    mirrored = {**external, "job_id": "already-solved"}
    messages = [FakeMessage(b"not json"), FakeMessage(json.dumps(mirrored).encode()), FakeMessage(json.dumps({"kind": "unknown"}).encode()), FakeMessage(json.dumps(external).encode())]
    handled: list[dict[str, Any]] = []

    def handler(payload: dict[str, Any]) -> str:
        handled.append(payload)
        return "job2"

    bridge = ConfluentBridge(
        CONFIG, producer_factory=FakeProducer, consumer_factory=lambda cfg: FakeConsumer(cfg, messages),
        on_set_event=handler, poll_timeout_s=0.01,
    )
    assert bridge.start() is True
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and bridge.status()["received"] < 1:
        time.sleep(0.02)
    bridge.stop()
    assert handled == [external]
    status = bridge.status()
    assert status["received"] == 1 and status["skipped"] == 2  # bad JSON and the unknown kind; the mirrored one is ignored silently
    consumer = bridge.consumer
    assert isinstance(consumer, FakeConsumer) and consumer.subscribed == [TOPIC_SET_EVENTS] and consumer.closed
    assert consumer.cfg["auto.offset.reset"] == "latest" and consumer.cfg["group.id"]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    monkeypatch.setenv("HOLD_SOLVE_TIME_LIMIT_S", "30")
    JOBS.clear()
    BUS.clear()
    return TestClient(app)


def test_status_names_the_transport(client: TestClient) -> None:
    from api.routes.status import reset_cache

    reset_cache()
    confluent = client.get("/api/status").json()["runtime"]["confluent"]
    assert confluent["connected"] is False and confluent["transport"] == "in-process"


def test_set_event_route_mirrors_to_the_broker_when_connected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import api.routes.events as events_route

    bridge = ConfluentBridge(CONFIG, producer_factory=FakeProducer)
    bridge.start()
    monkeypatch.setattr(events_route, "BRIDGE", bridge)
    demo = json.loads((ROOT / "data" / "demo" / "hold-demo.json").read_text())
    job_id = client.post("/api/solve", json={k: v for k, v in demo.items() if not k.startswith("_")}).json()["job_id"]
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline and client.get(f"/api/jobs/{job_id}").json()["status"] not in ("done", "failed"):
        time.sleep(0.1)
    response = client.post("/api/set-events", json={"kind": "scene_dropped", "payload": {"scene_id": "s6"}, "source": "ui"})
    assert response.status_code == 202 and response.json()["transport"] == "confluent"
    producer = bridge.producer
    assert isinstance(producer, FakeProducer)
    topics = [m[0] for m in producer.messages]
    assert TOPIC_SET_EVENTS in topics
    mirrored = next(m for m in producer.messages if m[0] == TOPIC_SET_EVENTS)
    assert mirrored[2]["job_id"] == response.json()["job_id"] and mirrored[2]["kind"] == "scene_dropped"
    bridge.stop()


def test_events_schema_is_generated_from_the_models() -> None:
    from scripts.events_schema import render

    committed = json.loads((ROOT / "rules" / "events.schema.json").read_text())
    assert committed == json.loads(render())
    assert set(committed["definitions"]) == {"SetEvent", "VerdictEvent"}


def test_status_reports_the_bridge_live_even_when_the_headline_is_cached(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The headline may be cached for ten minutes; the transport and its counters are read on every call."""
    import api.routes.status as status_route
    from api.routes.status import reset_cache

    reset_cache()
    first = client.get("/api/status").json()
    assert first["runtime"]["confluent"]["transport"] == "in-process"
    bridge = ConfluentBridge(CONFIG, producer_factory=FakeProducer)
    bridge.start()
    bridge.publish(TOPIC_VERDICTS, "j", {"event": "verdict"})
    monkeypatch.setattr(status_route, "BRIDGE", bridge)
    second = client.get("/api/status").json()
    assert second["computed_at"] == first["computed_at"]  # headline still cached
    assert second["runtime"]["confluent"]["transport"] == "confluent" and second["runtime"]["confluent"]["published"] == 1
    bridge.stop()
