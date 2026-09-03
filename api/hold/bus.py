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
        self._subscribers: set[asyncio.Queue[Event]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self.history: deque[Event] = deque(maxlen=history)

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._loop = loop

    def subscribe(self) -> asyncio.Queue[Event]:
        """Call on the serving loop; binds the bus to it on first use."""
        queue: asyncio.Queue[Event] = asyncio.Queue()
        with self._lock:
            self._subscribers.add(queue)
            if self._loop is None:
                self._loop = asyncio.get_running_loop()
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: Event) -> None:
        """History is appended here, on the publishing thread, so a reader that sees the publisher's next
        write (a job's done flag) finds the event in replay; only the fan-out to live subscriber queues
        crosses to the serving loop (round seven, finding 3)."""
        with self._lock:
            self.history.append(event)
            targets = list(self._subscribers)
            loop = self._loop
        if not targets:
            return
        if loop is not None and loop.is_running() and not _on_loop(loop):
            loop.call_soon_threadsafe(self._fan_out, event, targets)
        else:
            self._fan_out(event, targets)

    @staticmethod
    def _fan_out(event: Event, targets: list[asyncio.Queue[Event]]) -> None:
        for queue in targets:
            queue.put_nowait(event)

    def replay(self, job_id: str | None) -> list[Event]:
        with self._lock:
            return [e for e in self.history if job_id is None or e.get("job_id") == job_id]

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()
            self.history.clear()
            self._loop = None


def _on_loop(loop: asyncio.AbstractEventLoop) -> bool:
    try:
        return asyncio.get_running_loop() is loop
    except RuntimeError:
        return False


BUS = EventBus()
