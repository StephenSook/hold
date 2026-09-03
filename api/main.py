"""
HOLD FastAPI application entry point.

Task 1.10 deploy shell; tasks 3.5 and 3.6 mount the routes from api/routes/.
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

from api.routes.events import router as events_router
from api.routes.extract import router as extract_router
from api.routes.rules import router as rules_router
from api.routes.solve import router as solve_router
from api.routes.status import router as status_router

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
# API routes. Registered before the SPA catch-all so /api/* never falls through.
# ---------------------------------------------------------------------------

for _router in (status_router, solve_router, events_router, extract_router, rules_router):
    app.include_router(_router)


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


def _mount_assets(application: FastAPI, dist: Path) -> bool:
    """Serve /assets/... from web/dist/assets when the built web app is present. A placeholder
    dist with only index.html (the image built before the web app exists) mounts nothing."""
    assets = dist / "assets"
    if not assets.is_dir():
        return False
    application.mount("/assets", StaticFiles(directory=str(assets)), name="assets")
    return True


_mount_assets(app, _DIST)


@app.get("/{full_path:path}", response_model=None)  # a Response union is not a response model
async def spa_fallback(full_path: str) -> FileResponse | JSONResponse:
    """Serve index.html for all non-/api paths (HashRouter SPA)."""
    return _spa_response()
