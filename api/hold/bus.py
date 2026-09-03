"""
In-process event bus (task 3.5). Also the HOLD_FAKE_EXTERNALS=1 path; task 4.1 adds the Confluent
producer and consumer beside it and /api/status reports which is live.

publish() is safe from any thread: when an event loop is bound the event is handed to it with
call_soon_threadsafe, otherwise it is delivered synchronously. Subscribers are asyncio queues
created on the loop that serves /api/events. A bounded history lets a late subscriber replay.
"""
from __future__ import annotations

import asyncio
import threading
from collections import deque
from typing import Any

Event = dict[str, Any]


class EventBus:
    def __init__(self, history: int = 500) -> None:
        self._subscribers: set[asyncio.Queue[tuple[int, Event]]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self.history: deque[tuple[int, Event]] = deque(maxlen=history)
        self._seq = 0  # every event is numbered as it enters history, so a replay and the live
        # stream can agree on what has already been delivered (round eight, finding 1)

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._loop = loop

    def subscribe(self) -> asyncio.Queue[tuple[int, Event]]:
        """Call on the serving loop; binds the bus to it on first use. Each item is (sequence, event)."""
        queue: asyncio.Queue[tuple[int, Event]] = asyncio.Queue()
        with self._lock:
            self._subscribers.add(queue)
            if self._loop is None:
                self._loop = asyncio.get_running_loop()
        return queue

    def unsubscribe(self, queue: asyncio.Queue[tuple[int, Event]]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: Event) -> None:
        """History is appended here, on the publishing thread, so a reader that sees the publisher's next
        write (a job's done flag) finds the event in replay; only the fan-out to live subscriber queues
        crosses to the serving loop (round seven, finding 3)."""
        with self._lock:
            self._seq += 1
            item = (self._seq, event)
            self.history.append(item)
            targets = list(self._subscribers)
            loop = self._loop
        if not targets:
            return
        if loop is not None and loop.is_running() and not _on_loop(loop):
            loop.call_soon_threadsafe(self._fan_out, item, targets)
        else:
            self._fan_out(item, targets)

    @staticmethod
    def _fan_out(item: tuple[int, Event], targets: list[asyncio.Queue[tuple[int, Event]]]) -> None:
        for queue in targets:
            queue.put_nowait(item)

    def replay(self, job_id: str | None) -> list[Event]:
        return [event for _, event in self.replay_seq(job_id)]

    def replay_seq(self, job_id: str | None) -> list[tuple[int, Event]]:
        """History with each event's sequence number, so a stream knows what it has already sent."""
        with self._lock:
            return [(seq, e) for seq, e in self.history if job_id is None or e.get("job_id") == job_id]

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()
            self.history.clear()
            self._seq = 0
            self._loop = None


def _on_loop(loop: asyncio.AbstractEventLoop) -> bool:
    try:
        return asyncio.get_running_loop() is loop
    except RuntimeError:
        return False


BUS = EventBus()
