"""Task 3.6: GET /api/status, assembled once and cached, headline from docs/FACTS.json (D7)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.hold.facts import HEADLINE_FIELDS
from api.main import app
from api.routes.status import reset_cache

ROOT = Path(__file__).parents[2]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    reset_cache()
    return TestClient(app)


def test_status_shape(client: TestClient) -> None:
    body = client.get("/api/status").json()
    assert set(body["headline"]) == set(HEADLINE_FIELDS)
    assert body["headline_source"] == "docs/FACTS.json"
    assert body["computed_at"] and body["cache_ttl_s"] == 600
    runtime = body["runtime"]
    assert {"gemini_model", "gemini_location", "adk_version", "ortools_version", "confluent", "mode"} <= set(runtime)
    assert runtime["confluent"]["connected"] is False
    assert runtime["mode"] == "fake externals"
    assert runtime["ortools_version"] != "unknown"


def test_status_headline_is_the_committed_facts(client: TestClient) -> None:
    facts = json.loads((ROOT / "docs" / "FACTS.json").read_text())
    body = client.get("/api/status").json()
    assert body["headline"] == {k: facts[k] for k in HEADLINE_FIELDS}
    bench = json.loads((ROOT / "bench" / "results.json").read_text())
    assert body["benchmark_matched"] == bench["benchmark_matched"]
    assert body["benchmark_run_sha"] == bench["_run_sha"]


def test_status_is_cached_for_ten_minutes(client: TestClient) -> None:
    first = client.get("/api/status").json()
    second = client.get("/api/status").json()
    assert first["computed_at"] == second["computed_at"]
    reset_cache()
    assert client.get("/api/status").status_code == 200


def test_live_mode_is_named_only_when_extraction_can_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "0")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    reset_cache()
    runtime = TestClient(app).get("/api/status").json()["runtime"]
    assert runtime["mode"] == "unconfigured" and runtime["extraction"]["configured"] is False
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "hold-2026")
    reset_cache()
    runtime = TestClient(app).get("/api/status").json()["runtime"]
    assert runtime["mode"] == "live" and runtime["extraction"]["configured"] is True
    reset_cache()


def test_placeholder_secret_value_reads_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret Manager refuses an empty payload, so unset secrets carry the literal 'unset'."""
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    monkeypatch.setenv("CONFLUENT_BOOTSTRAP", "unset")
    reset_cache()
    assert TestClient(app).get("/api/status").json()["runtime"]["confluent"]["bootstrap_configured"] is False
    monkeypatch.setenv("CONFLUENT_BOOTSTRAP", "pkc-example.us-central1.gcp.confluent.cloud:9092")
    reset_cache()
    assert TestClient(app).get("/api/status").json()["runtime"]["confluent"]["bootstrap_configured"] is True
    reset_cache()


def test_status_note_describes_shipped_routes_not_pending_tasks(client: TestClient) -> None:
    """3.5 and 4.1 landed: the note names the routes that invoke Gemini and Confluent and no pending task."""
    note = client.get("/api/status").json()["runtime"]["note"]
    assert "once tasks" not in note
    assert "/api/extract" in note and "/api/set-events" in note


def test_the_status_note_names_every_route_that_invokes_the_model() -> None:
    """The sentence on /api/status is a claim, and it was false for two routes.

    It said Gemini is invoked by /api/extract, and stayed saying that after /api/ask and
    /api/interpret-event shipped, on the endpoint the judge page tells a judge to open. The
    sentence is generated from MODEL_ROUTES now, and this holds MODEL_ROUTES to the routes that
    actually reach the model: every module under api/routes that imports the agent runner must be
    named in it, and nothing else may be.
    """
    import ast

    from api.routes.status import MODEL_ROUTES

    routes_dir = Path(__file__).resolve().parents[1] / "routes"
    calls_the_model: set[str] = set()
    for module in sorted(routes_dir.glob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        # Importing the runner is not invoking the model: /api/status imports is_configured to
        # report whether the model COULD be called, which is the opposite of calling it. The
        # predicate is importing one of the three entry points that actually run an agent.
        entry_points = {"extract", "ask", "interpret_event"}
        invokes = any(
            isinstance(node, ast.ImportFrom)
            and (node.module or "").startswith("api.agents.hold_agent.runner")
            and any(alias.name in entry_points for alias in node.names)
            for node in ast.walk(tree)
        )
        if not invokes:
            continue
        for node in ast.walk(tree):
            # The decorator's first argument is the path, which is the thing the sentence names.
            for decorator in getattr(node, "decorator_list", []):
                if isinstance(decorator, ast.Call) and decorator.args and isinstance(decorator.args[0], ast.Constant):
                    path = decorator.args[0].value
                    if isinstance(path, str) and path.startswith("/api/"):
                        calls_the_model.add(path)

    assert calls_the_model, "no route was found importing the agent runner; this check walks the wrong tree"
    assert set(MODEL_ROUTES) == calls_the_model, (
        f"MODEL_ROUTES is {sorted(MODEL_ROUTES)} but the routes importing the agent runner are "
        f"{sorted(calls_the_model)}; the sentence on /api/status would be wrong"
    )
