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
