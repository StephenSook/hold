"""The FastAPI app must import and serve: a route annotation FastAPI rejects would crash uvicorn at startup."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_app_imports_and_the_spa_fallback_answers() -> None:
    from api.main import app

    client = TestClient(app)
    response = client.get("/judge")
    assert response.status_code in (200, 503)  # 200 with web/dist built, 503 with the plain JSON notice
    if response.status_code == 503:
        assert "web/dist" in response.json()["detail"]


def test_assets_mount_tolerates_a_dist_without_an_assets_dir(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A placeholder web/dist (index.html only, no assets/) must not crash the app at import."""
    from fastapi import FastAPI

    from api.main import _mount_assets

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>HOLD</title>")
    assert _mount_assets(FastAPI(), dist) is False
    (dist / "assets").mkdir()
    assert _mount_assets(FastAPI(), dist) is True
    assert _mount_assets(FastAPI(), tmp_path / "missing") is False
