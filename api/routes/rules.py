"""GET /api/rules and GET /api/bench (task 3.5): the registry with its verification counts and trust facts, and the residual run."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from api.hold.quotes import verify_rules
from api.hold.registry import load_rules
from api.hold.trust import NO_TRUST_STATUTE, trust_facts

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "rules"


@router.get("/api/rules")
async def rules() -> dict[str, Any]:
    records = [
        {**dataclasses.asdict(r), "valid_from": r.valid_from.isoformat(), "valid_to": r.valid_to.isoformat() if r.valid_to else None}
        for r in load_rules(RULES)
    ]
    problems, counts = verify_rules(RULES, RULES / "sources", RULES / "verification.json")
    trust = {
        state: {"percent": f.percent, "threshold_usd": f.threshold_usd, "record_ids": [r.id for r in f.records]}
        for state, f in trust_facts(RULES).items()
    }
    return {
        "records": records,
        "counts": counts,
        "verification_problems": [dataclasses.asdict(p) for p in problems],
        "trust": trust,
        "no_trust_statute": NO_TRUST_STATUTE,
    }


@router.get("/api/bench")
async def bench() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ROOT / "bench" / "results.json").read_text(encoding="utf-8"))
    return data
