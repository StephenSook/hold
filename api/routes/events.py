"""
GET /api/events (SSE) and POST /api/set-events (task 3.5). Events come from the in-process bus;
task 4.1 adds the Confluent leg. A set-event edits the latest solved schedule, echoes itself on the
bus and queues a re-solve whose verdicts arrive as verdict events.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.hold.bus import BUS
from api.hold.jobs import JOBS
from api.hold.schemas import SetEvent
from api.hold.set_events import SetEventError, apply_set_event

router = APIRouter()
KEEPALIVE_S = 15.0


def _sse(event: dict[str, Any]) -> str:
    name = str(event.get("event", "message"))
    return f"event: {name}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"


async def _stream(job_id: str | None, replay: bool, limit: int | None, timeout_s: float | None) -> AsyncIterator[str]:
    """Events for one job or all jobs; replay sends the bus history first. limit ends the stream
    after that many events and timeout_s after that many seconds (both unbounded by default)."""
    queue = BUS.subscribe()
    sent = 0
    deadline = None if timeout_s is None else asyncio.get_running_loop().time() + timeout_s
    try:
        if replay:
            for event in BUS.replay(job_id):
                yield _sse(event)
                sent += 1
                if limit is not None and sent >= limit:
                    return
        while True:
            wait = KEEPALIVE_S if deadline is None else min(KEEPALIVE_S, deadline - asyncio.get_running_loop().time())
            if wait <= 0:
                return
            try:
                event = await asyncio.wait_for(queue.get(), timeout=wait)
            except TimeoutError:
                if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                    return
                yield ": keepalive\n\n"
                continue
            if job_id is None or event.get("job_id") == job_id:
                yield _sse(event)
                sent += 1
                if limit is not None and sent >= limit:
                    return
    finally:
        BUS.unsubscribe(queue)


@router.get("/api/events")
async def events(
    job_id: str | None = None, replay: bool = False, limit: int | None = None, timeout_s: float | None = None
) -> StreamingResponse:
    return StreamingResponse(
        _stream(job_id, replay, limit, timeout_s),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/set-events", status_code=202)
async def set_event(event: SetEvent) -> dict[str, Any]:
    base = JOBS.latest_done()
    if base is None:
        raise HTTPException(status_code=409, detail="no solved schedule to apply the event to; POST /api/solve first")
    try:
        edited, change = apply_set_event(base.schedule, event)
    except SetEventError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job = JOBS.submit(edited, source=f"set-event:{event.kind}:{event.source}")
    BUS.publish({**event.model_dump(mode="json"), "job_id": job.id, "base_job_id": base.id, "change": change, "transport": "in-process"})
    return {"job_id": job.id, "base_job_id": base.id, "change": change, "poll": f"/api/jobs/{job.id}"}
