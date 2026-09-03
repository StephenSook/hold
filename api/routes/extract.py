"""
POST /api/extract (task 3.5). Under HOLD_FAKE_EXTERNALS=1 the golden fixture is returned and says
so in its notes. The live path runs the ADK agent (task 3.1) through a Runner with a hard timeout
and one model call per request (task 3.3), and only when Vertex AI is configured; otherwise the
route refuses with 503 rather than pretending (wired-or-cut).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.agents.hold_agent.runner import EXTRACT_TIMEOUT_S, ExtractionError, is_configured
from api.agents.hold_agent.runner import extract as run_extract
from api.hold.schemas import ExtractResult

router = APIRouter()
log = logging.getLogger(__name__)
_FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "contracts" / "extract-result.json"


class ExtractRequest(BaseModel):
    text: str = ""
    image_base64: str | None = None
    mime_type: str = "image/png"


@router.post("/api/extract")
async def extract(request: ExtractRequest) -> ExtractResult:
    if os.environ.get("HOLD_FAKE_EXTERNALS", "0") == "1":
        fixture = ExtractResult.model_validate(json.loads(_FIXTURE.read_text(encoding="utf-8")))
        return fixture.model_copy(update={"notes": f"fixture: HOLD_FAKE_EXTERNALS=1, no model was called ({fixture.notes})".rstrip(" ()")})
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="extraction not configured: GOOGLE_CLOUD_PROJECT is unset (PLAN.md task 0.1); the task 3.1 agent runs only with Vertex AI credentials",
        )
    image = base64.b64decode(request.image_base64) if request.image_base64 else None
    try:
        return await run_extract(request.text, image, request.mime_type, timeout_s=EXTRACT_TIMEOUT_S)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=f"extraction exceeded {EXTRACT_TIMEOUT_S:.0f} s") from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # the caller sees the failure class, never a blank 500; the message stays in the log
        log.exception("extraction failed")
        code = getattr(exc, "code", None)
        where = f" (upstream status {code})" if isinstance(code, int) else ""
        raise HTTPException(status_code=502, detail=f"extraction failed: {type(exc).__name__}{where}; details are in the service log") from exc
