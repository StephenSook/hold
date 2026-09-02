# Tasks: Phase 0 and Phase 1 Execution Order

> Spec Kit artifact for HOLD. Owner: Stephen.
> Each entry: task id, test file(s), "Done means" (verbatim from PLAN.md), commit subject.

---

## Execution order

The order below is the only safe order. D1 (Proof before pixels) and the Wednesday 22:00 gate
mean that 1.3, 1.4, 1.5, 1.6, 1.7 are on the critical path and nothing else in Stephen's lane
is built until 1.7 is green. Tasks 1.9, 1.10, 1.12 are non-blocking and can be done after the
gate closes (or in parallel with 1.7 if a second context is available).

---

### 1. Task 0.5: Repo init

Test file: none (verified by git commands and GitHub UI)

Done means (PLAN.md verbatim): "GitHub About shows Apache-2.0; `git ls-files` shows no PDF"

Commit subject: `chore: init repo, Apache-2.0, README stub, .gitignore, PLAN.md`
(no `--trailer "Tool: IBM-Bob"` if Stephen authors; trailer added if Bob authors the diff)

---

### 2. Task 0.6: Bob init and modes

Test file: `api/tests/test_bob_lane_enforcement.py` (created in task 0.14 but the lanes it
tests come from the yaml written here; 0.6 is done when the yaml exists and the modes match
the Lanes section - 0.14 provides the automated verification)

Done means (PLAN.md verbatim): "Each mode refuses one file outside its scope and accepts one
inside (all five tested)"

Commit subject: `chore: Bob init, five write-scoped modes, AGENTS.md, .bobignore`

---

### 3. Task 0.8: Python scaffold

Test file: none for this task directly; `uv sync` is the test

Done means (PLAN.md verbatim): "`uv sync` clean on a fresh clone"

Commit subject: `chore: root pyproject.toml, uv.lock, .env.example, api/__init__`

---

### 4. Task 0.9: CI skeleton

Test file: CI itself is the test; a planted em-dash is the acceptance trigger

Done means (PLAN.md verbatim): "Green on main; a planted em-dash in an untracked file turns it
red; branch protection lists the jobs"

Commit subject: `ci: skeleton - ruff, mypy, pytest, vitest, gitleaks, em-dash gate, license guard`

---

### 5. Task 0.13: Evidence scripts

Test file: `api/tests/test_bob_attribution.py` (checks the output exists)

Done means (PLAN.md verbatim): "Both files present after one run; trailer count reported"

Commit subject: `chore(evidence): export_bob_evidence.py, bob_attribution.sh, first run`

---

### 6. Task 0.14: Lane-enforcement and attribution tests

Test file: `api/tests/test_bob_lane_enforcement.py`, `api/tests/test_bob_attribution.py`

Done means (PLAN.md verbatim): "Green; widening `frontend` to `docs/` goes red"

Commit subject: `test(evidence): lane-enforcement and attribution tests, 2 tests`

---

### 7. Task 0.15: Gemini model pin

Test file: `api/tests/test_config.py`

Done means (PLAN.md verbatim): "One constant, one test asserting it is not a 2.5 id"

Commit subject: `chore: pin GEMINI_MODEL to 3.x Flash, config.py, 1 test`

---

### 8. Task 0.7: Spec Kit (this document)

Test file: filesystem check that `spec.md`, `plan.md`, `tasks.md` exist under `specs/001-phase0-and-solver/`

Done means (PLAN.md verbatim): "`spec.md`, `plan.md`, `tasks.md` exist"

Commit subject: `docs(specs): 001-phase0-and-solver spec kit, plan, tasks`
(with `--trailer "Tool: IBM-Bob"` since Bob authored)

---

### 9. Task 1.9: Contracts and schemas

Test file: `api/tests/test_schemas.py`

Done means (PLAN.md verbatim): "Fixtures validate against the models; Deem imports them"

Commit subject: `CONTRACT: schemas.py ScheduleInput ExtractResult Verdict SolveResult, 4 fixtures`
(CONTRACT prefix because this is a shared contract per PLAN.md coordination protocol)

---

### 10. Task 1.10: Stub deploy

Test file: manual verification - logged-out browser, `/api/status` 200, `/judge` loads

Done means (PLAN.md verbatim): "Public URL serves the board; `/api/status` 200 with a stub;
`/judge` deep link loads"

Commit subject: `feat(deploy): stub main.py, Dockerfile, deploy.yml with Cloud Run flags`

---

### 11. Task 1.1: Benchmark instances

Test file: `api/tests/test_bench_identity.py`

Done means (PLAN.md verbatim): "11 instances present; identity green on 8/8"

Commit subject: `chore(bench): 8 medium + 3 easy dzn instances, MIT LICENSE, optima.json, identity test, 8 tests`
(test count in subject: CI rule and PLAN.md Bob evidence requirement)

---

### 12. Task 1.2: dzn parser

Test file: `api/tests/test_instance.py`

Done means (PLAN.md verbatim): "Green"

Commit subject: `feat(solver): dzn parser Instance dataclass, 4 tests`

---

### 13. Task 1.3: CP-SAT benchmark model (CRITICAL PATH)

Test file: `api/tests/test_model_smoke.py`

Done means (PLAN.md verbatim): "film116 OPTIMAL, holding 110, total 541; times recorded in Notes"

Commit subject: `feat(solver): CP-SAT benchmark model pos/scene_at onset objective symmetry_break, 1 test`

Note: After this task, record the film116 solve time in PLAN.md task 1.3 Notes, commit as:
`status: 1.3 DONE 2026-09-03 HH:MM Stephen`

---

### 14. Task 1.4: Residual test (CRITICAL PATH - gate)

Test file: `api/tests/test_residual.py`

Done means (PLAN.md verbatim): "8/8 green locally under the cap"

Commit subject: `test(solver): residual 8/8 medium instances OPTIMAL vs optima.json, 8 tests`

---

### 15. Task 1.5: Independent checker (CRITICAL PATH)

Test file: `api/tests/test_checker.py`

Done means (PLAN.md verbatim): "Green"

Commit subject: `feat(solver): independent checker recompute holding/total, 3 tests`

---

### 16. Task 1.6: Brute force and properties (CRITICAL PATH)

Test file: `api/tests/test_bruteforce.py`, `api/tests/test_props.py`, `api/tests/test_symmetry.py`

Done means (PLAN.md verbatim): "Green"

Commit subject: `test(solver): brute-force differential, Hypothesis props, symmetry-break, N tests`
(fill N with actual test count at commit time)

---

### 17. Task 1.7: CI residual job (CRITICAL PATH - gate completion)

Test file: CI check-runs API on `main` (the job itself is the test)

Done means (PLAN.md verbatim): "Badge green on main"

Commit subject: `ci: add residual job 15-min timeout, badge in README`

After this commit and a green CI run, the Wednesday 22:00 gate is satisfied.
Record in PLAN.md: `status: 1.7 DONE 2026-09-03 HH:MM Stephen - gate green`

---

### 18. Task 1.12: Demo schedule

Test file: validation against `ScheduleInput` schema in `api/tests/test_schemas.py` (add
a parametrized case loading `data/demo/hold-demo.json`)

Done means (PLAN.md verbatim): "Validates against `ScheduleInput`; loads in the UI"

Commit subject: `data(demo): hold-demo.json before-order.json callsheet PNG+TXT, constructed labeled`

---

## Critical path summary

```
0.5 -> 0.6 -> 0.8 -> 0.9 -> [0.13, 0.14, 0.15] -> 0.7 -> 1.9 -> 1.1 -> 1.2 -> 1.3 -> 1.4 -> 1.5 -> 1.6 -> 1.7 (GATE)
                                                           |
                                                        1.10 (non-blocking, can run parallel after 0.8)
                                                           |
                                                        1.12 (after 1.9)
```

The gate is task 1.7: CI residual job green on `main` by Wednesday 22:00.
Nothing else in Stephen's lane moves until that badge is green.

---

## PLAN.md status commit protocol

For each task, before starting:
```
status: <task_id> WIP <yyyy-mm-dd> <HH:MM> Stephen
```
After finishing:
```
status: <task_id> DONE <yyyy-mm-dd> <HH:MM> Stephen
```
These are atomic commits touching only PLAN.md, no code bundled.
