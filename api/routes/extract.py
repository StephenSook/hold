"""
POST /api/extract (task 3.5). Under HOLD_FAKE_EXTERNALS=1 the golden fixture is returned and says
so in its notes. The live path is the ADK Runner from task 3.1; until it exists the route refuses
with 503 rather than pretending (wired-or-cut).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.hold.schemas import ExtractResult

router = APIRouter()
_FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "contracts" / "extract-result.json"


class ExtractRequest(BaseModel):
    text: str = ""
    image_base64: str | None = None


@router.post("/api/extract")
async def extract(request: ExtractRequest) -> ExtractResult:
    if os.environ.get("HOLD_FAKE_EXTERNALS", "0") == "1":
        fixture = ExtractResult.model_validate(json.loads(_FIXTURE.read_text(encoding="utf-8")))
        return fixture.model_copy(update={"notes": f"fixture: HOLD_FAKE_EXTERNALS=1, no model was called ({fixture.notes})".rstrip(" ()")})
    raise HTTPException(status_code=503, detail="extraction agent not configured: task 3.1 (ADK Runner) has not landed")
