# HOLD Phase 2 Implementation Plan

> **For agentic workers:** Read PLAN.md at repo root first. Every task number
> here maps to a row in PLAN.md. Locked decisions D1-D17 are never re-litigated.

**Goal:** Build Layer B (the verdict): rules registry, CA/GA/SAG-AFTRA rule
YAMLs, the plain-Python legality checker extended for real rules, and the
CP-SAT pass-1 legality solver. Gate: pass 1 returns correct rule ids on five
fixture days by Thu Sep 4 22:00.

**Architecture:** Three layers that must stay independent:
1. `rules/*.yaml` - static data, verbatim quotes, source URLs (D4)
2. `api/hold/registry.py` - loader, temporal validity, schema enforcement
3. `api/hold/checker.py` - plain Python enumerator (D13, no OR-Tools)
4. `api/hold/legality.py` + `api/hold/solve.py` - CP-SAT pass 1 with assumptions

**Tech Stack:** Python 3.12, pydantic v2, OR-Tools CP-SAT, pytest, ruff, mypy

## Global Constraints

- No em-dashes anywhere (CI gate).
- `uv run pytest` not `python -m pytest`.
- Stage named paths only, never `git add -A`.
- `Tool: IBM-Bob` trailer on every commit.
- Test count in every engine commit subject.
- No legal value ships without verbatim quote + citation + source URL + dates (D4).
- Louisiana caps are refused not guessed.
- One logical change per commit, subject 100 chars or fewer.

---

## Current State (as of 2026-09-04 session start)

**Committed and green:**
- 88 tests passing locally (88 = Phase 0 + Phase 1 solver/checker/residual)
- CI residual job: 8/8 OPTIMAL (badge green on main)
- `api/main.py`, `Dockerfile`, `.github/workflows/deploy.yml` committed (8f5deee)
- `data/demo/hold-demo.json`, `data/demo/before-order.json`,
  `data/demo/samples/callsheet-day3.{png,txt}` - created but NOT YET COMMITTED

**Next immediate action:** commit data/demo/ files (task 1.12).

---

## Sub-Task 1: Commit task 1.12 demo files

**Status:** [ ] pending

**Intent:** The demo schedule files exist on disk but were not committed before the
previous session ended. Must be staged and committed to unblock Phase 2.

**Expected Outcomes:** `data/demo/` is in git; `hold-demo.json` validates against
`ScheduleInput`; PLAN.md task 1.12 flipped to DONE.

**Todo List:**
- [ ] Verify `data/demo/hold-demo.json` validates: `uv run python -c "import json; from api.hold.schemas import ScheduleInput; ScheduleInput.model_validate({k:v for k,v in json.load(open('data/demo/hold-demo.json')).items() if not k.startswith('_')})"`
- [ ] `bash scripts/no_em_dash.sh` - confirm clean
- [ ] `git ls-files | grep -iE '\.pdf$|\.env$|^private/'` - expect nothing
- [ ] `git add data/demo/hold-demo.json data/demo/before-order.json data/demo/samples/callsheet-day3.png data/demo/samples/callsheet-day3.txt`
- [ ] `git commit --trailer "Tool: IBM-Bob" -m "feat(demo): constructed schedule 10 scenes 4 cast GA minor, callsheet day3, 7 hold days"`
- [ ] Update PLAN.md: task 1.12 -> DONE with commit SHA
- [ ] `git add PLAN.md && git commit --trailer "Tool: IBM-Bob" -m "status: 1.12 DONE"`
- [ ] `git push`

**Relevant Context:** `data/demo/hold-demo.json` has `_note` key that must be
stripped before `ScheduleInput.model_validate()`. 4 cast members (A,B,C,M where
M is 14-year-old CA resident). 7 shoot days. Day 3 (index 3) is school day with
21:30 wrap - the illegal day the solver must fix.

---

## Sub-Task 2: Task 2.1 - Rules registry

**Status:** [ ] pending

**Intent:** Define the schema that ALL rule YAMLs must conform to, and the Python
loader that rejects any record missing a citation or quote. This is the foundation
every subsequent rules task builds on.

**Files:**
- Create: `rules/schema.json`
- Create: `api/hold/registry.py`
- Create: `api/tests/test_registry.py`
- Create: `rules/` directory

**Expected Outcomes:** Loader rejects a record missing `citation` or `quote`.
`test_registry.py` green.

**Todo List:**
- [ ] Create `rules/` directory
- [ ] Write `rules/schema.json` with fields: `id, jurisdiction, authority, citation, title, quote, source_url, valid_from, valid_to, params, verified, note`
- [ ] Write `api/hold/registry.py`: `load_rules(path, shooting_date)` -> `list[RuleRecord]`; rejects missing citation/quote; filters by `valid_from <= shooting_date <= valid_to`
- [ ] Write `api/tests/test_registry.py`: test rejects missing citation, rejects missing quote, loads valid record, filters by date
- [ ] `uv run ruff check api/ && uv run mypy api/ --ignore-missing-imports`
- [ ] `uv run pytest api/tests/test_registry.py -v`
- [ ] Commit: `feat(rules): registry schema + loader, N tests`

---

## Sub-Task 3: Task 2.3 - Georgia rules YAML

**Status:** [ ] pending

**Intent:** Georgia rules first because the demo schedule shoots in GA with a
CA-resident minor. GA rules go in before CA because the checker needs GA to
validate the demo's illegal day.

**Files:**
- Create: `rules/ga.yaml`

**Expected Outcomes:** Every record has `quote` and `source_url`. Loader accepts
the file. The illegal day in the demo (school night wrap 21:30 > 22:00) maps to
`GA_300_7_1_03_school_night_curfew`.

**Key rules to encode (from PLAN.md 2.3):**
- `300-7-1-.03` hours by age: 9-16: 10h at location, 5h work, 22:00 school night, 00:00 non-school
- 16-18: 12h, 8h, 00:00, 02:00
- 05:00 earliest call for all minors
- 6 consecutive days max
- 12h turnaround when working during school hours
- `.09` studio teacher 1:10
- `.04` child labor coordinator 1:10

**Source URL:** `https://rules.sos.ga.gov/gac/300-7-1` (Official Georgia Rules)

**Todo List:**
- [ ] Draft `rules/ga.yaml` with all records above, each with verbatim quote
- [ ] `uv run python -c "from api.hold.registry import load_rules; ..."` to verify loader accepts it
- [ ] Commit: `feat(rules): GA child performer rules 300-7-1, N records`

---

## Sub-Task 4: Task 2.2 - California rules YAML

**Status:** [ ] pending

**Files:** Create `rules/ca.yaml`

**Key rules (PLAN.md 2.2):**
- `8 CCR 11760(a)-(f)` hour tables by age
- `11760(i)` 12-hour turnaround
- `LC 1308.7` curfew: no work before 05:00 or after 22:00 before school day; 00:30 before non-school
- `11755.1/11755.2` teacher ratios
- `11761` meal within 6 hours
- 8h and 48h caps
- DLSE "subtract 6 hours" as separately flagged layer

**Source URLs:** `https://leginfo.legislature.ca.gov/` (CA Labor Code), `https://www.dir.ca.gov/` (8 CCR)

**Todo List:**
- [ ] Draft `rules/ca.yaml` with all records, verbatim quotes
- [ ] Verify loader accepts it
- [ ] Commit: `feat(rules): CA child performer rules 8CCR 11760 LC 1308.7, N records`

---

## Sub-Task 5: Task 2.4 - SAG-AFTRA minors YAML

**Status:** [ ] pending

**Files:** Create `rules/sag_minors.yaml`

**Key rules (PLAN.md 2.4):**
- Young Performers Handbook: p.17 precedence (cumulative jurisdiction), p.22 12h turnaround before school day, p.23 infant restriction nationwide
- 2026 chaperone-to-under-16 change
- Cumulative jurisdiction clause: 8 CCR 11756 + GA 300-7-1-.01

**Todo List:**
- [ ] Draft `rules/sag_minors.yaml`
- [ ] Verify loader accepts it
- [ ] Commit: `feat(rules): SAG-AFTRA minors handbook rules, N records`

---

## Sub-Task 6: Task 2.5 - SAG-AFTRA rates + penalties.py

**Status:** [ ] pending

**Files:**
- Create: `rules/sag_rates.yaml`
- Create: `api/hold/penalties.py`
- Create: `api/tests/test_penalties.py`

**Key rates (PLAN.md 2.5, all integer cents):**
- Low Budget: $810/day = 81000 cents, $2812/week = 281200 cents
- Moderate Low: $449.05/day = 44905 cents
- Ultra Low: $249/day = 24900 cents
- P&H: 21% through 2026-09-05, 22% from 2026-09-06
- Hold day at full daily rate

**Expected Outcomes:** Hand calculation on `data/demo/hold-demo.json` matches
`penalties.py` output to the cent.

**Todo List:**
- [ ] Write `rules/sag_rates.yaml` with every figure, source URL, cycle dates
- [ ] Write `api/hold/penalties.py`: `hold_day_cost(cast, shooting_date) -> int` (cents)
- [ ] Write `api/tests/test_penalties.py`: hand-verify at least 2 rate tiers
- [ ] Commit: `feat(rules): SAG-AFTRA rates yaml + penalties.py, N tests`

---

## Sub-Task 7: Task 2.9 - Checker extended for legality

**Status:** [ ] pending

**Intent:** Extend `api/hold/checker.py` to enumerate EVERY violation over a
concrete timeline. This is D13: the checker is the source of truth for violations.
It must NOT use OR-Tools. It works on the demo schedule's illegal day.

**Files:**
- Modify: `api/hold/checker.py`
- Create: `api/tests/test_legality.py`
- Create: `data/fixtures/illegal-days/` with fixture JSONs

**Expected Outcomes:** A fixture day with three violations lists three. Agrees
with pass 1 on fixture days. No OR-Tools import.

**Todo List:**
- [ ] Add `check_legality(schedule, day_index, rules) -> list[ViolationRecord]` to checker.py
- [ ] Create 5 fixture day JSONs under `data/fixtures/illegal-days/`
- [ ] Write `api/tests/test_legality.py`: each fixture returns expected violation IDs
- [ ] Commit: `feat(solver): checker legality enumeration, N tests`

---

## Sub-Task 8: Task 2.7 - Pass 1 legality solver

**Status:** [ ] pending

**Intent:** CP-SAT pass 1 with `add_assumptions`. Order and day assignment fixed;
times free. Each rule is a named BoolVar. INFEASIBLE -> `sufficient_assumptions_for_infeasibility()` -> rule IDs. FEASIBLE -> LEGAL with witness.

**Files:**
- Create: `api/hold/legality.py`
- Modify: `api/hold/solve.py`
- Create: `api/tests/test_pass1.py`

**Expected Outcomes:** Five fixture days return INFEASIBLE with expected rule IDs
in the core. One legal day returns FEASIBLE.

**Todo List:**
- [ ] Write `api/hold/legality.py`: `check_day_legality(schedule, day_index, rules) -> Verdict`
- [ ] Write `api/tests/test_pass1.py`: five illegal fixtures + one legal
- [ ] `uv run pytest api/tests/test_pass1.py -v`
- [ ] Commit: `feat(solver): pass1 legality CP-SAT assumptions, N tests`

---

## Sub-Task 9: Task 2.10 - Quote verification (Thu version)

**Status:** [ ] pending

**Files:**
- Create: `rules/sources/` snapshots
- Create: `rules/verification.json`
- Create: `api/tests/test_quotes.py`

**Expected Outcomes:** CI test fails if any rule record lacks a verification status.
UNVERIFIABLE records labeled, not counted.

**Todo List:**
- [ ] Create `rules/sources/` with text snapshots of each source URL
- [ ] Write `rules/verification.json`
- [ ] Write `api/tests/test_quotes.py`: substring check every quote against its snapshot
- [ ] Commit: `feat(rules): quote snapshots + verification, N tests`

---

## Gate Check (Thu Sep 4 22:00)

Before calling Phase 2 done:
- [ ] `uv run pytest api/ -q` - all tests green
- [ ] `uv run ruff check api/ && uv run mypy api/ --ignore-missing-imports` - clean
- [ ] `bash scripts/no_em_dash.sh` - clean
- [ ] Pass 1 returns correct rule IDs on all 5 fixture illegal days
- [ ] `git push` and CI all-green on main
