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
