"""
Shared contracts for HOLD.
Owner: Stephen. Consumers: Deem (web app), agent (ADK), solver, checker.

CONTRACT changes must be announced in PLAN.md Shared Contracts before committing.
Commit prefix: CONTRACT:
"""
from __future__ import annotations

from datetime import date, time
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Scene and cast types
# ---------------------------------------------------------------------------


class Scene(BaseModel):
    id: str
    number: int
    int_ext: Literal["INT", "EXT"]
    day_night: Literal["DAY", "NIGHT"]
    set: str
    pages_eighths: int = Field(ge=1)
    cast_ids: list[str]
    location_id: str


class CastMember(BaseModel):
    id: str
    letter: str  # single letter: A, B, C ... used in fixtures instead of real names
    age: int | None = None  # None for adult cast (no minor rules apply)
    resident_state: str | None = None  # two-letter state code; None = unknown
    day_rate_cents: int = Field(ge=0)
    rate_tier: Literal["low_budget", "moderate_low", "ultra_low", "other"]


class ShootDay(BaseModel):
    date: date
    call: time
    wrap: time
    school_day: bool
    # The following calendar day is a school day (curfew and 5 a.m. floor trigger). None means
    # derive from the next shoot day when it is the next calendar date, else assume True and
    # label the assumption on the verdict.
    school_night: bool | None = None


class Constraint(BaseModel):
    type: Literal["availability", "precedence"]
    cast_id: str | None = None
    scene_id_a: str | None = None
    scene_id_b: str | None = None
    unavailable_day_indices: list[int] | None = None  # 0-based indices into days list


class Jurisdiction(BaseModel):
    shoot_state: Literal["CA", "GA", "other"]


class ScheduleInput(BaseModel):
    """
    The top-level input to the HOLD solver and extractor.
    `constructed: true` when the data is demo/test data, not a real production.
    Always display this flag to end users.
    """
    scenes: list[Scene]
    cast: list[CastMember]
    days: list[ShootDay]
    constraints: list[Constraint] = Field(default_factory=list)
    jurisdiction: Jurisdiction
    constructed: bool  # must be True for demo data; shown in the UI
    # Under the SAG-AFTRA low-budget agreements consecutive employment (paid hold days) applies
    # only on overnight locations; the Basic Agreement pays it everywhere.
    overnight_location: bool = False

    @model_validator(mode="after")
    def _days_chronological(self) -> ScheduleInput:
        """Consumers read days by list position (turnaround, worked-date fallback, pass-2 hold days)."""
        for prev, nxt in zip(self.days, self.days[1:], strict=False):
            if nxt.date <= prev.date:
                raise ValueError(f"days must be in chronological order with unique dates: {prev.date} is followed by {nxt.date}")
        return self


# ---------------------------------------------------------------------------
# Extraction result (Gemini -> ScheduleInput)
# ---------------------------------------------------------------------------


class ExtractResult(BaseModel):
    """
    Output of the ADK agent extraction step.
    status='ok': schedule is fully populated and ready for human confirmation.
    status='needs_clarification': schedule is None; questions lists what is missing.
    A human must confirm before the solver runs.
    """
    status: Literal["ok", "needs_clarification"]
    schedule: ScheduleInput | None = None
    questions: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def _status_matches_payload(self) -> ExtractResult:
        """ok carries a schedule; needs_clarification carries questions and no schedule."""
        if self.status == "ok" and self.schedule is None:
            raise ValueError("status ok requires a schedule")
        if self.status == "needs_clarification" and (self.schedule is not None or not self.questions):
            raise ValueError("status needs_clarification requires questions and no schedule")
        return self


# ---------------------------------------------------------------------------
# Verdict (legality check result)
# ---------------------------------------------------------------------------


class ViolationRecord(BaseModel):
    """One violated rule on one shooting day."""
    rule_id: str
    citation: str      # e.g. "8 CCR 11760(e)"
    title: str         # short human-readable rule name
    limit: str         # e.g. "8 hours work per day"
    computed: str      # e.g. "9.5 hours work"
    over_by: str       # e.g. "1.5 hours"
    quote: str         # verbatim sentence from the statute
    source_url: str    # deep link to the source
    jurisdiction: str  # "CA", "GA", "SAG-AFTRA", etc.


class Verdict(BaseModel):
    """
    Legality verdict for one shooting day.
    violations: filled by the checker (complete enumeration).
    core_rule_ids: filled by the solver pass-1 (sufficient infeasibility core).
    witness: the legal call sheet when status='LEGAL'.
    """
    status: Literal["LEGAL", "ILLEGAL", "UNDETERMINED"]
    day: int  # 0-based index into ScheduleInput.days
    violations: list[ViolationRecord] = Field(default_factory=list)
    core_rule_ids: list[str] = Field(default_factory=list)
    witness: dict[str, object] | None = None
    reason: str = ""  # one sentence for the card: why UNDETERMINED, or how the core reads


# ---------------------------------------------------------------------------
# Solve result (full output of the two-pass solver)
# ---------------------------------------------------------------------------


class Pass2Result(BaseModel):
    """
    Result of the cost-minimization pass (pass 2).
    status='OPTIMAL': proven minimum cost.
    status='FEASIBLE': best found within time limit, with bound.
    status='UNDETERMINED': infeasible with the hard rules; reasons lists the
    violated rule ids (from assumptions pass).
    D3: optimality is claimed only on the benchmark model; this is always
    'FEASIBLE' or 'UNDETERMINED' for the extended model unless the instance
    is tiny.
    """
    order: list[int]  # scene indices in shoot order
    status: Literal["OPTIMAL", "FEASIBLE", "UNDETERMINED"]
    holding_cents: int = Field(ge=0)
    total_cents: int = Field(ge=0)
    bound: int  # solver's lower bound on total_cents
    hold_days: int = Field(ge=0)
    penalties_cents: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)  # violated rule ids if UNDETERMINED


class CheckerResult(BaseModel):
    """Whether the independent checker agrees with the solver on the solved schedule."""
    agrees: bool
    note: str = ""


class BenchmarkResult(BaseModel):
    """Residual against one benchmark instance."""
    instance: str
    published: int   # optima from DOI 10.1145/1401.5869 Table 10
    ours: int        # our solver's result
    residual: int    # ours - published (0 = matches)


class SolveResult(BaseModel):
    """
    Top-level output of a full HOLD solve.
    pass1: per-day verdicts from the legality pass.
    pass2: the optimized schedule.
    checker: agreement check.
    benchmark: present only when running against a benchmark instance.
    """
    pass1: list[Verdict]
    pass2: Pass2Result
    checker: CheckerResult
    benchmark: BenchmarkResult | None = None


# ---------------------------------------------------------------------------
# SSE event models (streamed from GET /api/events)
# ---------------------------------------------------------------------------


class ObjectiveEvent(BaseModel):
    """Emitted by the solver callback as new incumbent solutions are found."""
    event: Annotated[str, Field(default="objective")] = "objective"
    job_id: str
    value: int   # current best objective (holding_cents)
    bound: int   # current lower bound
    t_ms: int    # milliseconds since solve start


class VerdictEvent(BaseModel):
    """Emitted when a day's verdict is computed or updated."""
    event: Annotated[str, Field(default="verdict")] = "verdict"
    job_id: str
    verdict: Verdict


class SetEvent(BaseModel):
    """
    Emitted when an on-set event (actor late, scene dropped, weather cover)
    triggers a re-solve.
    source='ui': user action; source='simulation': simulate_set_day.py script.
    """
    event: Annotated[str, Field(default="set-event")] = "set-event"
    kind: Literal["actor_late", "scene_dropped", "weather_cover"]
    payload: dict[str, object]
    source: Literal["ui", "simulation"]
