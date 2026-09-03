"""
Solve jobs (task 3.5). One worker thread runs pass 2 so the event loop never blocks and two
solves never race for the CPU; the solver's improving solutions become objective events on the
bus and each used day's pass-1 verdict becomes a verdict event when the job finishes.
"""
from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from api.hold.bus import BUS
from api.hold.pass2 import pass2, to_solve_result
from api.hold.schemas import ObjectiveEvent, ScheduleInput, SolveResult, VerdictEvent
from api.hold.streaming import BRIDGE, TOPIC_VERDICTS

JobStatus = Literal["queued", "running", "done", "failed"]


def solve_time_limit_s() -> float:
    return float(os.environ.get("HOLD_SOLVE_TIME_LIMIT_S", "60"))


@dataclass
class Job:
    id: str
    schedule: ScheduleInput
    source: str
    created_at: str
    status: JobStatus = "queued"
    result: SolveResult | None = None
    day_scene_ids: dict[int, list[str]] = field(default_factory=dict)
    error: str | None = None
    solve_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.id,
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at,
            "result": self.result.model_dump(mode="json") if self.result is not None else None,
            "day_scene_ids": {str(d): ids for d, ids in self.day_scene_ids.items()},
            "error": self.error,
            "solve_ms": self.solve_ms,
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hold-solve")

    def submit(self, schedule: ScheduleInput, source: str = "api") -> Job:
        job = Job(id=uuid.uuid4().hex[:12], schedule=schedule, source=source, created_at=datetime.now(UTC).replace(microsecond=0).isoformat())
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
        self._executor.submit(self._run, job)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def latest_done(self) -> Job | None:
        with self._lock:
            for job_id in reversed(self._order):
                job = self._jobs[job_id]
                if job.status == "done":
                    return job
        return None

    def latest_base(self) -> Job | None:
        """The schedule a new set event edits: the most recent job that has not failed, solved or not.
        A queued or running re-solve already carries its edited schedule, so events chain instead of
        each editing the last solved plan and the last finish winning (round five, finding 1)."""
        with self._lock:
            for job_id in reversed(self._order):
                job = self._jobs[job_id]
                if job.status != "failed":
                    return job
        return None

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._order.clear()

    def _run(self, job: Job) -> None:
        job.status = "running"

        def on_solution(value: int, bound: int, t_ms: float) -> None:
            BUS.publish(ObjectiveEvent(job_id=job.id, value=value, bound=bound, t_ms=int(t_ms)).model_dump(mode="json"))

        try:
            outcome = pass2(job.schedule, time_limit_s=solve_time_limit_s(), on_solution=on_solution)
            job.result = to_solve_result(outcome)
            job.day_scene_ids = dict(outcome.day_scene_ids)
            job.solve_ms = round(outcome.solve_ms, 1)
            job.status = "done"
            for p in outcome.pass1:
                if outcome.day_scene_ids.get(p.verdict.day):
                    verdict_event = VerdictEvent(job_id=job.id, verdict=p.verdict).model_dump(mode="json")
                    BUS.publish(verdict_event)
                    BRIDGE.publish(TOPIC_VERDICTS, job.id, verdict_event)
        except Exception as exc:  # the failure must reach the client, never a silent queued job
            job.error = f"{type(exc).__name__}: {exc}"
            job.status = "failed"
            BUS.publish({"event": "job", "job_id": job.id, "status": "failed", "error": job.error})


JOBS = JobStore()
