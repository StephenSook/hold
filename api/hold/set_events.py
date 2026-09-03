"""
Set events (task 3.5, task 4.1 adds the Confluent leg). Each event edits the last solved
schedule in a stated way and the result is re-solved:

- actor_late {cast_id, day_index}: the performer is unavailable that day (an availability
  constraint); a partial day is not modeled, and the response says so.
- scene_dropped {scene_id}: the scene and any precedence naming it are removed.
- weather_cover {day_index}: no exterior scene may shoot that day (a scene-level availability
  constraint per EXT scene); interiors may.
"""
from __future__ import annotations

from typing import Any

from api.hold.schemas import Constraint, ScheduleInput, SetEvent


class SetEventError(ValueError):
    """The payload names something the schedule does not have."""


def _int(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise SetEventError(f"payload.{key} must be an integer") from exc


def _str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SetEventError(f"payload.{key} must be a non-empty string")
    return value


def apply_set_event(schedule: ScheduleInput, event: SetEvent) -> tuple[ScheduleInput, str]:
    """Return the edited schedule and one sentence describing exactly what changed."""
    days = len(schedule.days)
    if event.kind == "scene_dropped":
        scene_id = _str(event.payload, "scene_id")
        if scene_id not in {s.id for s in schedule.scenes}:
            raise SetEventError(f"scene {scene_id!r} is not in the schedule")
        scenes = [s for s in schedule.scenes if s.id != scene_id]
        constraints = [c for c in schedule.constraints if scene_id not in (c.scene_id_a, c.scene_id_b)]
        return schedule.model_copy(update={"scenes": scenes, "constraints": constraints}), f"scene {scene_id} dropped"
    if event.kind == "actor_late":
        cast_id = _str(event.payload, "cast_id")
        day = _int(event.payload, "day_index")
        if cast_id not in {c.id for c in schedule.cast}:
            raise SetEventError(f"cast member {cast_id!r} is not in the schedule")
        if not 0 <= day < days:
            raise SetEventError(f"day_index {day} is outside 0..{days - 1}")
        cons = [*schedule.constraints, Constraint(type="availability", cast_id=cast_id, unavailable_day_indices=[day])]
        return schedule.model_copy(update={"constraints": cons}), f"{cast_id} unavailable on day {day} (a partial day is not modeled)"
    day = _int(event.payload, "day_index")
    if not 0 <= day < days:
        raise SetEventError(f"day_index {day} is outside 0..{days - 1}")
    exteriors = [s.id for s in schedule.scenes if s.int_ext == "EXT"]
    cons = [*schedule.constraints, *(Constraint(type="availability", scene_id_a=sid, unavailable_day_indices=[day]) for sid in exteriors)]
    return schedule.model_copy(update={"constraints": cons}), f"weather cover on day {day}: {len(exteriors)} exterior scene(s) moved off it"
