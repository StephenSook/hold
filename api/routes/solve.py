"""POST /api/solve and GET /api/jobs/{id} (task 3.5). The solve runs on the job store's single worker thread."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from api.hold.jobs import JOBS
from api.hold.schemas import ScheduleInput

router = APIRouter()


@router.post("/api/solve", status_code=202)
async def solve(schedule: ScheduleInput) -> dict[str, Any]:
    job = JOBS.submit(schedule, source="api")
    return {"job_id": job.id, "status": job.status, "poll": f"/api/jobs/{job.id}", "events": f"/api/events?job_id={job.id}&replay=true"}


@router.get("/api/jobs/{job_id}")
async def job(job_id: str) -> dict[str, Any]:
    found = JOBS.get(job_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"no job {job_id!r}")
    return found.to_dict()
