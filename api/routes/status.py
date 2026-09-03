"""
Task 3.6: GET /api/status. Assembled once, cached ten minutes with computed_at. The headline
comes from docs/FACTS.json (PLAN.md D7: nobody types a headline number); the benchmark figure
from bench/results.json with its run SHA; runtime names the configured model, region and library
versions and says plainly that this endpoint invokes no model and no broker.
"""
from __future__ import annotations

import importlib.metadata
import json
import os
import re
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from api.agents.hold_agent.runner import is_configured
from api.hold.config import ADK_VERSION, GEMINI_MODEL, GOOGLE_CLOUD_LOCATION
from api.hold.facts import HEADLINE_FIELDS
from api.hold.streaming import BRIDGE

ROOT = Path(__file__).resolve().parents[2]
CACHE_TTL_S = 600.0

router = APIRouter()
_lock = threading.Lock()
_cached: dict[str, Any] | None = None
_cached_at: float = 0.0


def _version(distribution: str, fallback: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return fallback


def build_status() -> dict[str, Any]:
    facts = json.loads((ROOT / "docs" / "FACTS.json").read_text(encoding="utf-8"))
    bench = json.loads((ROOT / "bench" / "results.json").read_text(encoding="utf-8"))
    fake = os.environ.get("HOLD_FAKE_EXTERNALS", "0") == "1"
    configured = is_configured()
    mode = "fake externals" if fake else ("live" if configured else "unconfigured")
    return {
        "computed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "cache_ttl_s": int(CACHE_TTL_S),
        "headline": {k: facts.get(k) for k in HEADLINE_FIELDS},
        "headline_source": "docs/FACTS.json",
        "bob_usage": bob_usage(),
        "facts_generated_at": facts.get("generated_at"),
        "facts_run_sha": facts.get("run_sha"),
        "constructed": bool(facts.get("constructed", True)),
        "benchmark_matched": bench.get("benchmark_matched"),
        "benchmark_run_sha": bench.get("_run_sha"),
        "runtime": {
            "gemini_model": os.environ.get("GEMINI_MODEL", GEMINI_MODEL),
            "gemini_location": os.environ.get("GOOGLE_CLOUD_LOCATION", GOOGLE_CLOUD_LOCATION),
            "adk_version": _version("google-adk", ADK_VERSION),
            "ortools_version": _version("ortools", "unknown"),
            "confluent": BRIDGE.status(),
            "mode": mode,
            "extraction": {
                "configured": configured,
                "reason": None if configured else ("HOLD_FAKE_EXTERNALS=1: fixtures answer /api/extract" if fake else "GOOGLE_CLOUD_PROJECT unset: /api/extract answers 503"),
            },
            "invoked_by_this_endpoint": [],
            "note": "This endpoint reads committed files and invokes no model and no broker; Gemini is invoked by "
            "/api/extract and Confluent by /api/set-events.",
        },
    }


def bob_usage() -> dict[str, Any]:
    """The committed Bob evidence aggregate (tasks 3.13 and 5.12): the session-store export's totals and
    the trailer counts ATTRIBUTION.md records from git history. Never a live count."""
    export = json.loads((ROOT / "docs" / "bob-evidence" / "bob-usage-evidence.json").read_text(encoding="utf-8"))
    attribution = (ROOT / "docs" / "bob-evidence" / "ATTRIBUTION.md").read_text(encoding="utf-8")

    def row(label: str) -> str | None:
        found = re.search(rf"^\| {re.escape(label)} \| ([^|]+) \|", attribution, re.M)
        return found.group(1).strip() if found else None

    total, bob = row("Total commits"), row("Bob-authored commits (Tool: IBM-Bob trailer)")
    return {
        "source": "docs/bob-evidence/bob-usage-evidence.json",
        "generated_at": export.get("generated_at"),
        "task_count": export.get("task_count"),
        "total_cost_usd": export.get("total_cost_usd"),
        "note": export.get("note"),
        "commits_total": int(total) if total else None,
        "commits_with_bob_trailer": int(bob) if bob else None,
        "last_bob_commit": row("Last Bob-authored commit"),
        "attribution_source": "docs/bob-evidence/ATTRIBUTION.md",
    }


def cached_status() -> dict[str, Any]:
    """The headline and versions are cached; the streaming transport and its counters are live."""
    global _cached, _cached_at
    with _lock:
        now = time.monotonic()
        if _cached is None or now - _cached_at >= CACHE_TTL_S:
            _cached, _cached_at = build_status(), now
        payload = dict(_cached)
    payload["runtime"] = {**payload["runtime"], "confluent": BRIDGE.status()}
    return payload


def reset_cache() -> None:
    global _cached, _cached_at
    with _lock:
        _cached, _cached_at = None, 0.0


@router.get("/api/status")
async def status() -> dict[str, Any]:
    return cached_status()
