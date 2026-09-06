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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.hold.jobs import JOBS
from api.hold.mcp_server import MOUNT as _mcp_mount
from api.hold.streaming import BRIDGE
from api.routes.ask import router as ask_router
from api.routes.events import handle_external_set_event
from api.routes.events import router as events_router
from api.routes.extract import router as extract_router
from api.routes.interpret import router as interpret_router
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

@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Start the Confluent bridge when it is configured (metadata call proves the broker); the
    in-process bus needs nothing. Stop it on shutdown.

    The MCP session manager runs here too. A Starlette app mounted inside another app does not get
    its own lifespan run, so mounting the MCP transport without this gives a route that exists,
    answers, and fails on every call, which is worse than not having it.
    """
    BRIDGE.on_set_event = handle_external_set_event
    BRIDGE.is_own_job = lambda job_id: JOBS.get(job_id) is not None
    BRIDGE.start()
    try:
        async with _mcp_mount.running():
            yield
    finally:
        BRIDGE.stop()


app = FastAPI(title="HOLD", version="0.1.0", docs_url="/api/docs", lifespan=_lifespan)

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

for _router in (status_router, solve_router, events_router, extract_router, ask_router, interpret_router, rules_router):
    app.include_router(_router)

# HOLD's own MCP server, on the deployed origin, so the solver can be driven by any MCP client
# rather than only by this app. Mounted before the SPA catch-all, which would otherwise answer
# /mcp with index.html and hand a JSON-RPC client an HTML page.
app.mount("/mcp", _mcp_mount)


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


def _dist_file(full_path: str, dist: Path | None = None) -> Path | None:
    """
    The file in web/dist this path names, or None.

    Vite emits more than assets/ at the root of dist: registerSW.js, sw.js,
    manifest.webmanifest, favicon.svg and the PWA icons all sit beside index.html. Mounting only
    /assets sent every one of them to the catch-all below, which answered index.html with
    content-type text/html, and the browser then parsed HTML as JavaScript and threw
    "SyntaxError: Unexpected token '<'" on every route. CI was green throughout: the bug lives
    between a correct build and a correct server, so only the deployed origin shows it.

    The resolve-then-contains check is what makes this safe to serve from a user-supplied path:
    a request for ../../etc/passwd resolves outside dist and is refused.

    `dist` is injectable so the decision can be tested without a built web app. The CI job that
    runs pytest does not build the web app, so a test that needed one would skip in CI, and a
    skipped guard is a false green.
    """
    root = (dist or _DIST).resolve()
    if not full_path:
        return None
    try:
        candidate = (root / full_path).resolve()
        candidate.relative_to(root)
        # is_file() belongs inside the try. It stats the path, and a request for a segment longer
        # than the filesystem allows raises ENAMETOOLONG rather than answering False, which turned
        # a nonsense URL into a 500 on the one origin a judge opens. Found by a property test
        # generating path segments, not by reading the code.
        return candidate if candidate.is_file() else None
    except (ValueError, OSError):
        return None


# HEAD is listed explicitly. Starlette adds it beside GET on its own routes, but a FastAPI
# route does not, so every path this serves, which is the site root, the judge page and every
# static asset, answered 405 to a HEAD request. Browsers never noticed. Link unfurlers, uptime
# monitors and link checkers ask with HEAD first, so the one URL on the README read as broken
# to everything that checks a link without opening it.
@app.api_route(  # a Response union is not a response model
    "/{full_path:path}", methods=["GET", "HEAD"], response_model=None
)
async def spa_fallback(full_path: str) -> FileResponse | JSONResponse:
    """Serve a real file from web/dist when the path names one, else index.html (HashRouter SPA)."""
    found = _dist_file(full_path)
    if found is not None:
        return FileResponse(str(found))
    return _spa_response()
