"""
The Confluent leg (task 4.1). Two topics: hold.set-events carries SetEvent messages, hold.verdicts
carries VerdictEvent messages (JSON, rules/events.schema.json). The API mirrors every set event it
handles onto the first topic with its job_id, and every verdict onto the second; a background
consumer re-solves set events published by anyone else (no job_id). `connected` is true only after
a real metadata call succeeded. Without a bootstrap, an API key and a secret, or under
HOLD_FAKE_EXTERNALS=1, the bridge does nothing and the in-process bus is the whole transport;
/api/status says which one is live. Secrets never appear in status or logs.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from api.hold.config import env_value
from api.hold.schemas import SetEvent

log = logging.getLogger(__name__)

TOPIC_SET_EVENTS = "hold.set-events"
TOPIC_VERDICTS = "hold.verdicts"
GROUP_ID = "hold-api"

ProducerFactory = Callable[[dict[str, Any]], Any]
ConsumerFactory = Callable[[dict[str, Any]], Any]
SetEventHandler = Callable[[dict[str, Any]], str | None]


@dataclass(frozen=True)
class ConfluentConfig:
    bootstrap: str
    api_key: str
    api_secret: str

    @classmethod
    def from_env(cls) -> ConfluentConfig | None:
        if os.environ.get("HOLD_FAKE_EXTERNALS", "0") == "1":
            return None
        bootstrap, key, secret = env_value("CONFLUENT_BOOTSTRAP"), env_value("CONFLUENT_API_KEY"), env_value("CONFLUENT_API_SECRET")
        if not (bootstrap and key and secret):
            return None
        return cls(bootstrap=bootstrap, api_key=key, api_secret=secret)

    def client_config(self) -> dict[str, Any]:
        return {
            "bootstrap.servers": self.bootstrap,
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "PLAIN",
            "sasl.username": self.api_key,
            "sasl.password": self.api_secret,
        }


def _real_producer(cfg: dict[str, Any]) -> Any:
    from confluent_kafka import Producer

    return Producer(cfg)


def _real_consumer(cfg: dict[str, Any]) -> Any:
    from confluent_kafka import Consumer

    return Consumer(cfg)


class ConfluentBridge:
    def __init__(
        self,
        config: ConfluentConfig | None,
        *,
        producer_factory: ProducerFactory | None = None,
        consumer_factory: ConsumerFactory | None = None,
        on_set_event: SetEventHandler | None = None,
        poll_timeout_s: float = 1.0,
    ) -> None:
        self.config = config
        self._producer_factory = producer_factory or _real_producer
        self._consumer_factory = consumer_factory or _real_consumer
        self.on_set_event = on_set_event
        self._poll_timeout_s = poll_timeout_s
        self.producer: Any = None
        self.consumer: Any = None
        self.connected = False
        self.last_error: str | None = None
        self.published = 0
        self.received = 0
        self.skipped = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Create the producer and prove the broker with a metadata call; then consume in a thread."""
        if self.config is None:
            return False
        try:
            self.producer = self._producer_factory(self.config.client_config())
            self.producer.list_topics(timeout=10.0)
            self.connected = True
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.connected = False
            log.warning("confluent: not connected (%s)", self.last_error)
            return False
        if self.on_set_event is not None:
            self._stop.clear()
            self._thread = threading.Thread(target=self._consume, name="hold-confluent-consumer", daemon=True)
            self._thread.start()
        return True

    def publish(self, topic: str, key: str, payload: dict[str, Any]) -> bool:
        if not self.connected or self.producer is None:
            return False
        try:
            self.producer.produce(topic, key=key.encode("utf-8"), value=json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            self.producer.poll(0)
        except Exception as exc:  # a broker hiccup must never fail the request that carried the event
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.warning("confluent: publish to %s failed (%s)", topic, self.last_error)
            return False
        with self._lock:
            self.published += 1
        return True

    def _consume(self) -> None:
        assert self.config is not None
        cfg = {**self.config.client_config(), "group.id": GROUP_ID, "auto.offset.reset": "latest", "enable.auto.commit": True}
        try:
            self.consumer = self._consumer_factory(cfg)
            self.consumer.subscribe([TOPIC_SET_EVENTS])
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.connected = False  # the loop is the transport; without a consumer the in-process bus is what runs
            log.warning("confluent: consumer did not start (%s)", self.last_error)
            return
        try:
            while not self._stop.is_set():
                message = self.consumer.poll(self._poll_timeout_s)
                if message is None:
                    continue
                if message.error():
                    self.last_error = str(message.error())  # librdkafka reconnects on its own; nothing to do but note it
                    continue
                self._handle(message.value())
        except Exception as exc:  # a dead loop must show on /api/status, never as a healthy transport (round five, finding 2)
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.connected = False
            log.warning("confluent: consumer died (%s)", self.last_error)
        try:
            self.consumer.close()
        except Exception as exc:
            log.warning("confluent: consumer close failed (%s)", exc)

    def _handle(self, raw: bytes) -> None:
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("message is not an object")
            if payload.get("job_id"):
                return  # the API mirrored its own event here; already solved
            SetEvent.model_validate(payload)
        except Exception as exc:  # log and skip, never die on a bad message
            with self._lock:
                self.skipped += 1
            log.warning("confluent: skipped a message on %s (%s: %s)", TOPIC_SET_EVENTS, type(exc).__name__, exc)
            return
        if self.on_set_event is None:
            return
        reason: str | None = None
        try:
            job_id = self.on_set_event(payload)
        except Exception as exc:  # refused by the handler (round five, finding 3)
            job_id, reason = None, f"{type(exc).__name__}: {exc}"
        if job_id is None:  # not applied: skipped, with the reason on status, never counted as handled
            self.last_error = reason or "no schedule to apply the event to; nothing solved since the API started"
            with self._lock:
                self.skipped += 1
            log.warning("confluent: set event not applied (%s)", self.last_error)
            return
        with self._lock:
            self.received += 1

    def status(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "bootstrap_configured": self.config is not None or env_value("CONFLUENT_BOOTSTRAP") is not None,  # live, so a placeholder reads as absent
            "transport": "confluent" if self.connected else "in-process",
            "topics": [TOPIC_SET_EVENTS, TOPIC_VERDICTS] if self.connected else [],
            "published": self.published,
            "received": self.received,
            "skipped": self.skipped,
            "last_error": self.last_error,
        }

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self.connected = False
        if self.producer is not None:
            try:
                self.producer.flush(5.0)
            except Exception as exc:
                log.warning("confluent: flush failed (%s)", exc)


BRIDGE = ConfluentBridge(ConfluentConfig.from_env())
