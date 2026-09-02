"""
HOLD FastAPI application entry point.

Task 1.10: stub deploy.
- API routes are mounted first; all /api/* paths are handled here.
- A catch-all GET serves web/dist/index.html for non-/api paths (SPA fallback).
- CORS allows capacitor://localhost, http://localhost, https://localhost, and the
  Cloud Run origin (read from HOLD_ORIGIN env var; omitted if unset).

The ADK API server is never mounted (D12). ADK runs through a Runner behind
our own routes (api/routes/).
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# CORS origins
# ---------------------------------------------------------------------------

_ALWAYS_ALLOWED = [
    "capacitor://localhost",
    "http://localhost",
    "https://localhost",
    "http://localhost:5173",   # Vite dev server
    "http://localhost:8000",   # uvicorn local
]

_cloud_run_origin = os.environ.get("HOLD_ORIGIN", "")
_ORIGINS: list[str] = _ALWAYS_ALLOWED + (
    [_cloud_run_origin] if _cloud_run_origin else []
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="HOLD", version="0.1.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routes (stub - full routes added in Phase 3 task 3.5)
# ---------------------------------------------------------------------------


@app.get("/api/status")
async def status() -> JSONResponse:
    """
    Stub status endpoint.
    Shape frozen by PLAN.md Shared Contracts; full implementation in task 3.6.
    Returns enough for the CI web-check and /judge skeleton to render.
    """
    return JSONResponse(
        {
            "benchmark_matched": "8/8",
            "mode": "stub",
            "runtime": {
                "gemini_model": os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
                "adk_version": "2.6.3",
                "ortools_version": "9.11",
                "confluent": {"connected": False},
            },
        }
    )


# ---------------------------------------------------------------------------
# Static file serving (SPA fallback)
# Web dist is built by the Node stage in the Dockerfile.
# In development (no dist/), the catch-all returns a 503.
# ---------------------------------------------------------------------------

_DIST = Path(__file__).parent.parent / "web" / "dist"


def _spa_response() -> FileResponse | JSONResponse:
    index = _DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse(
        {"detail": "web/dist not built; run npm run build in web/"},
        status_code=503,
    )


if _DIST.is_dir():
    # Mount assets so /assets/... serves from web/dist/assets/
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str) -> FileResponse | JSONResponse:
    """Serve index.html for all non-/api paths (HashRouter SPA)."""
    return _spa_response()
