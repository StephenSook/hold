"""
The three tools the HOLD agent may call (task 3.1). Each takes plain JSON, returns a plain dict,
and answers a bad input with an error naming the field instead of raising, so the model sees what
to fix. They wrap pass 1 (task 2.7), pass 2 (task 2.8) and the registry (task 2.1).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from api.hold.pass2 import pass2, to_solve_result
from api.hold.registry import load_rules
from api.hold.schemas import ScheduleInput
from api.hold.solve import pass1_day

_RULES = Path(__file__).resolve().parents[3] / "rules"


def _time_limit() -> float:
    return float(os.environ.get("HOLD_SOLVE_TIME_LIMIT_S", "60"))


def _schedule(schedule: dict[str, Any]) -> ScheduleInput | dict[str, Any]:
    try:
        return ScheduleInput.model_validate(schedule)
    except ValidationError as exc:
        first = exc.errors()[0]
        return {"error": "invalid schedule", "field": "schedule." + ".".join(str(p) for p in first["loc"]), "detail": first["msg"]}


def check_legality(schedule: dict[str, Any], day_index: int) -> dict[str, Any]:
    """Judge one shooting day of a ScheduleInput against child-performer law and the SAG-AFTRA rules.

    Args:
        schedule: a HOLD ScheduleInput object (scenes, cast, days, constraints, jurisdiction, constructed).
        day_index: the 0-based index of the day to judge.

    Returns:
        The Verdict: status LEGAL, ILLEGAL or UNDETERMINED, violations (rule id, citation, limit,
        computed value, verbatim quote, source URL), core_rule_ids, witness and reason.
    """
    parsed = _schedule(schedule)
    if isinstance(parsed, dict):
        return parsed
    if not 0 <= day_index < len(parsed.days):
        return {"error": f"day_index must be between 0 and {len(parsed.days) - 1}", "field": "day_index"}
    result = pass1_day(parsed, day_index, time_limit_s=_time_limit())
    return {**result.verdict.model_dump(mode="json"), "note": result.note}


def optimize_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    """Find the cheapest legal scene order and day assignment (pass 2), then re-judge every day.

    Args:
        schedule: a HOLD ScheduleInput object.

    Returns:
        A SolveResult (pass1 verdicts per day, pass2 order, status OPTIMAL, FEASIBLE or
        UNDETERMINED, holding cents, hold days, checker agreement) plus day_scene_ids.
    """
    parsed = _schedule(schedule)
    if isinstance(parsed, dict):
        return parsed
    outcome = pass2(parsed, time_limit_s=_time_limit())
    return {
        **to_solve_result(outcome).model_dump(mode="json"),
        "day_scene_ids": {str(d): ids for d, ids in outcome.day_scene_ids.items()},
        "paid_hold_days": outcome.paid_hold_days,
        "note": outcome.note,
    }


def lookup_rule(rule_id: str) -> dict[str, Any]:
    """Return one rule record by id: citation, title, the verbatim quote, source URL, params and note.

    Args:
        rule_id: a rule id such as GA_300_7_1_03_earliest_call.
    """
    records = {r.id: r for r in load_rules(_RULES)}
    record = records.get(rule_id)
    if record is None:
        return {"error": f"unknown rule id {rule_id!r}", "field": "rule_id", "known_ids": sorted(records)}
    return {
        "id": record.id,
        "jurisdiction": record.jurisdiction,
        "authority": record.authority,
        "citation": record.citation,
        "title": record.title,
        "quote": record.quote,
        "source_url": record.source_url,
        "valid_from": record.valid_from.isoformat(),
        "valid_to": record.valid_to.isoformat() if record.valid_to else None,
        "params": record.params,
        "verified": record.verified,
        "note": record.note,
    }
