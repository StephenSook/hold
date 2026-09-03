"""
Task 3.6: the headline numbers, written once by a real run (PLAN.md D7).

compute_facts() runs the constructed before plan through pass 1 and the plain-Python recount,
the demo through pass 2, reads bench/results.json and the rules verification, and returns every
field docs/FACTS.json carries. scripts/facts.py writes the file; api/tests/test_facts.py
recomputes the deterministic fields, so a hand edit fails CI; headline_mismatches() holds the
README and docs to the same numbers, digits or spelled out.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from api.hold.pass2 import hold_days_paid, pass2, recount_hold_days
from api.hold.penalties import hold_day_cost_cents
from api.hold.quotes import verify_rules
from api.hold.schemas import ScheduleInput
from api.hold.solve import pass1_schedule
from api.hold.trust import trust_facts

HEADLINE_FIELDS: tuple[str, ...] = (
    "hold_days_before", "hold_days_after", "payroll_removed_usd", "illegal_days_before",
    "illegal_days_after", "benchmark_matched", "solve_ms", "adk_eval",
)
# Fields a fresh run must reproduce exactly (solve_ms and run_sha vary run to run). The residual
# run's own SHA is not recorded here: bench/results.json is rewritten by every test run and
# /api/status serves it live; FACTS keeps the matched count, which is what the headline claims.
DETERMINISTIC_FIELDS: tuple[str, ...] = (
    "hold_days_before", "hold_days_after", "payroll_removed_usd", "payroll_removed_cents",
    "illegal_days_before", "illegal_days_after", "undetermined_days_before", "benchmark_matched",
    "pass2_status", "checker_agrees", "rules",
)


def load_schedule(path: Path) -> ScheduleInput:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ScheduleInput.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})


def git_sha(root: Path) -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


def load_adk_eval(root: Path) -> dict[str, Any] | None:
    """The recorded adk eval summary (docs/adk_eval.json, written by scripts/adk_eval.py), or None."""
    path = root / "docs" / "adk_eval.json"
    if not path.exists():
        return None
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def compute_facts(root: Path, time_limit_s: float = 60.0) -> dict[str, Any]:
    """Every FACTS.json field from a real run over data/demo. One worker, so the run is repeatable."""
    rules_dir = root / "rules"
    schedule = load_schedule(root / "data" / "demo" / "hold-demo.json")
    before = json.loads((root / "data" / "demo" / "before-order.json").read_text(encoding="utf-8"))
    before_map = {int(k): list(v) for k, v in before["day_scene_ids"].items()}
    full_before = {d: before_map.get(d, []) for d in range(len(schedule.days))}

    # The before plan: hold days and cost by the plain-Python recount, legality by pass 1.
    paid = hold_days_paid(schedule)
    held = recount_hold_days(schedule, before_map)
    cast_by_id = {c.id: c for c in schedule.cast}
    holding_before_cents = sum(
        hold_day_cost_cents(cast_by_id[cid], d, rules_dir) for cid, dates in held.items() if paid[cid] for d in dates
    )
    verdicts_before = pass1_schedule(schedule, day_scene_ids=full_before, time_limit_s=time_limit_s)
    statuses_before = [v.verdict.status for v in verdicts_before if before_map.get(v.verdict.day)]

    # The after plan: pass 2, re-judged by pass 1 inside pass2().
    outcome = pass2(schedule, rules_dir=rules_dir, time_limit_s=time_limit_s, num_workers=1)
    used = [p for p in outcome.pass1 if outcome.day_scene_ids.get(p.verdict.day)]
    payroll_removed_cents = holding_before_cents - outcome.result.holding_cents

    bench = json.loads((root / "bench" / "results.json").read_text(encoding="utf-8"))
    problems, counts = verify_rules(rules_dir, rules_dir / "sources", rules_dir / "verification.json")
    if problems:
        raise RuntimeError("rules verification is not clean; FACTS refuses to be written: " + "; ".join(f"{p.record_id}: {p.what}" for p in problems[:5]))

    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "run_sha": git_sha(root),
        "written_by": "scripts/facts.py (PLAN.md D7: no headline number is typed by hand)",
        "demo_file": "data/demo/hold-demo.json",
        "before_file": "data/demo/before-order.json",
        "constructed": bool(schedule.constructed),
        "overnight_location": bool(schedule.overnight_location),
        "hold_days_before": sum(len(v) for v in held.values()),
        "hold_days_after": outcome.result.hold_days,
        "payroll_removed_cents": payroll_removed_cents,
        "payroll_removed_usd": round(payroll_removed_cents / 100, 2),
        "holding_before_cents": holding_before_cents,
        "holding_after_cents": outcome.result.holding_cents,
        "illegal_days_before": sum(s == "ILLEGAL" for s in statuses_before),
        "undetermined_days_before": sum(s == "UNDETERMINED" for s in statuses_before),
        "illegal_days_after": sum(p.verdict.status == "ILLEGAL" for p in used),
        "benchmark_matched": bench["benchmark_matched"],
        "solve_ms": round(outcome.solve_ms, 1),
        "pass2_status": outcome.result.status,
        "checker_agrees": bool(outcome.checker.agrees),
        "adk_eval": load_adk_eval(root),
        "adk_eval_note": "recorded by scripts/adk_eval.py from a real adk eval run" if load_adk_eval(root) else "task 3.4 has not run; null until a real adk eval score is recorded",
        "rules": {
            "records": counts["records"],
            "verified": counts["verified"],
            "unverifiable": counts["unverifiable"],
            "assumed_params": counts["assumed_params"],
            "trust_states": sorted(trust_facts(rules_dir)),
        },
    }


# ---------------------------------------------------------------------------
# README and docs are held to FACTS: "four hold days", "4 hold days", "$1,234.50 of payroll", "8/8"
# ---------------------------------------------------------------------------

_NUM_WORDS = {
    "zero": 0, "no": 0, "none": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
_HOLD = re.compile(r"\b([A-Za-z]+|\d+)\s+hold[- ]days?\b", re.IGNORECASE)
_ILLEGAL = re.compile(r"\b([A-Za-z]+|\d+)\s+illegal[- ]days?\b", re.IGNORECASE)
_BENCH = re.compile(r"\b(\d+/\d+)\b")
_MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")


def _numeral(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    return _NUM_WORDS.get(token.lower())


def headline_mismatches(text: str, facts: dict[str, Any], allow_usd: Iterable[float]) -> list[str]:
    """Every sentence that states a hold-day, illegal-day, benchmark or payroll figure must state
    the FACTS figure. Dollar amounts in allow_usd (rules-sourced rates) are exempt."""
    allowed = {float(a) for a in allow_usd}
    hold_ok = {int(facts["hold_days_before"]), int(facts["hold_days_after"])}
    illegal_ok = {int(facts["illegal_days_before"]), int(facts["illegal_days_after"])}
    out: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        for pattern, ok, label in ((_HOLD, hold_ok, "hold days"), (_ILLEGAL, illegal_ok, "illegal days")):
            for m in pattern.finditer(sentence):
                n = _numeral(m.group(1))
                if n is not None and n not in ok:
                    out.append(f"{label} stated as {n}, FACTS says {sorted(ok)}: {sentence.strip()[:120]}")
        if re.search(r"benchmark|instances|matched", sentence, re.IGNORECASE):
            for m in _BENCH.finditer(sentence):
                if m.group(1) != facts["benchmark_matched"]:
                    out.append(f"benchmark stated as {m.group(1)}, FACTS says {facts['benchmark_matched']}: {sentence.strip()[:120]}")
        if re.search(r"payroll|hold|removed|saved", sentence, re.IGNORECASE):
            for m in _MONEY.finditer(sentence):
                amount = float(m.group(1).replace(",", ""))
                if amount != float(facts["payroll_removed_usd"]) and amount not in allowed:
                    out.append(f"dollar figure {amount:g} is neither payroll_removed_usd nor a rules-sourced rate: {sentence.strip()[:120]}")
    return out
