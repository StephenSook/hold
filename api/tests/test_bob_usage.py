"""Tasks 3.13 and 5.12: /api/status.bob_usage serves the committed Bob evidence aggregate, never a live
count. The aggregate is docs/bob-evidence/bob-usage-evidence.json (the session-store export) plus the
trailer counts from docs/bob-evidence/ATTRIBUTION.md (regenerated from git history by
scripts/bob_attribution.sh)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.status import reset_cache

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "bob-evidence" / "bob-usage-evidence.json"
ATTRIBUTION = ROOT / "docs" / "bob-evidence" / "ATTRIBUTION.md"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HOLD_FAKE_EXTERNALS", "1")
    reset_cache()
    return TestClient(app)


def _committed_counts() -> tuple[int, int]:
    text = ATTRIBUTION.read_text(encoding="utf-8")
    total = int(re.search(r"^\| Total commits \| (\d+) \|", text, re.M).group(1))  # type: ignore[union-attr]
    bob = int(re.search(r"^\| Bob-authored commits \(Tool: IBM-Bob trailer\) \| (\d+) \|", text, re.M).group(1))  # type: ignore[union-attr]
    return total, bob


def test_status_serves_the_committed_bob_usage_aggregate(client: TestClient) -> None:
    usage = client.get("/api/status").json()["bob_usage"]
    committed = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert usage["task_count"] == committed["task_count"]
    assert usage["total_cost_usd"] == committed["total_cost_usd"]
    assert usage["generated_at"] == committed["generated_at"]
    assert usage["note"] == committed["note"]
    assert usage["source"] == "docs/bob-evidence/bob-usage-evidence.json"
    total, bob = _committed_counts()
    assert usage["commits_total"] == total and usage["commits_with_bob_trailer"] == bob
    assert usage["last_bob_commit"] == "f00aa11"
    assert "tasks" not in usage  # the aggregate, not the per-task list


def test_the_committed_export_is_internally_consistent() -> None:
    committed = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert committed["task_count"] == len(committed["tasks"])
    assert abs(sum(t["cost_usd"] for t in committed["tasks"]) - committed["total_cost_usd"]) < 0.01
    total, bob = _committed_counts()
    assert 0 < bob <= total
