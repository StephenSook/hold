# Spec: Phase 0 Scaffolds and Phase 1 Residual (solver-engine mode)

> Spec Kit artifact for HOLD. Owner: Stephen. Mode: solver-engine (tasks 0.5, 0.6, 0.8, 0.9,
> 0.13, 0.14, 0.15) and evidence-writer (0.7). Root files are edited in built-in Agent mode.

---

## What Phase 0 delivers (PLAN.md, Phase 0 table)

The repo exists, is public under Apache-2.0, and every subsequent task has a clean foundation to land on. Specifically:

- Task 0.5: git repo initialized, LICENSE, README stub, `.gitignore`, `PLAN.md`, public remote. `git ls-files` shows no PDF.
- Task 0.6: Bob `/init`; `.bob/custom_modes.yaml` with five write-scoped modes (solver-engine, agent-runtime, mobile-shell, frontend, evidence-writer) with the regexes from the Lanes section; per-mode `rules-*/AGENTS.md`; root `AGENTS.md`; `.bobignore`. Each mode refuses one file outside its scope and accepts one inside (all five tested).
- Task 0.8: Root `pyproject.toml` and `uv.lock` (Python 3.12; ortools, google-adk==2.6.3, google-genai, google-cloud-aiplatform, fastapi, uvicorn, pydantic, confluent-kafka, hypothesis, pytest, ruff, mypy pinned); `.env.example` listing all nine env vars; `api/__init__.py`. `uv sync` clean on a fresh clone.
- Task 0.9: CI skeleton: api (ruff, mypy, pytest hermetic, `fetch-depth: 0`), web (tsc, eslint, `vitest run`, build), gitleaks, em-dash gate over `git ls-files --cached --others --exclude-standard`, license guard; every gate bare; required checks set on `main`. A planted em-dash turns the gate red.
- Task 0.13: Evidence scripts: `scripts/export_bob_evidence.py` (read-only over `~/.bob/db/bob.db`, workspace-filtered, no message bodies) and `scripts/bob_attribution.sh`; first run committed under `docs/bob-evidence/`.
- Task 0.14: Lane-enforcement test and attribution test; the full allow/refuse matrix from PLAN.md; widening `frontend` to `docs/` goes red.
- Task 0.15: `api/hold/config.py` with one `GEMINI_MODEL` constant (a 3.x Flash id, not a 2.5 id); one test asserting the non-2.5 invariant.

## What Phase 1 delivers (PLAN.md, Phase 1 table)

The benchmark residual is proven at 8/8 in CI with no key and no account, and the Spec Kit artifacts for the solver feature are committed. Specifically:

- Task 0.7: `specs/001-solver/spec.md`, `plan.md`, `tasks.md` committed (this document and its siblings satisfy this).
- Task 1.1: 8 medium and 3 easy `.dzn` instances from `MiniZinc/minizinc-benchmarks/talent_scheduling/` with MIT LICENSE; `bench/optima.json`; identity test `total - holding == sum_j c_j * sum_{i in ia[j]} d_i` passes 8/8 with no solver.
- Task 1.2: `api/hold/instance.py` dzn parser to `Instance(num_scenes, num_actors, ia, c, d)`; tests on film116 parameters.
- Task 1.3: `api/hold/model.py` CP-SAT benchmark model: `pos`/`scene_at` with `AddInverse` plus `AddAllDifferent`; per-actor `first_j`, `last_j`; `onset[j][i]` reified; objective `holding = sum_j c_j * sum_{i not in ia[j]} d_i * onset[j][i]`; `symmetry_break: bool`; integer objective only; film116 OPTIMAL, holding 110, total 541.
- Task 1.4: Residual test: all 8 medium instances OPTIMAL, objective equals bound, matches `bench/optima.json`, 60 s cap per instance; writes `bench/results.json` with run SHA.
- Task 1.5: `api/hold/checker.py`: plain Python recompute of holding and total from a permutation; permutation validity assert; agrees with solver on 8/8; rejects a corrupted permutation.
- Task 1.6: Brute-force differential on easy/tiny and easy/small; Hypothesis properties; symmetry-break test.
- Task 1.7: CI `residual` job runs 1.1, 1.4, 1.5, 1.6 hermetically with no network and no key, 15-minute job timeout, uploads `bench/results.json`; README badge.
- Task 1.9: `api/hold/schemas.py` with `ScheduleInput`, `ExtractResult`, `Verdict`, `SolveResult`, SSE event models; committed JSON fixtures under `data/fixtures/contracts/`; tests validating fixtures against models.
- Task 1.10: Stub deploy: `api/main.py`, `Dockerfile` at repo root, `deploy.yml`. Public URL serves the board; `/api/status` 200 with a stub; `/judge` deep link loads.
- Task 1.12: Demo schedule JSON: constructed, labeled, cast letters, Georgia shoot with one California-resident minor; before-order with 7 hold days and 1 illegal day; sample call sheet as PNG and TXT.

## Acceptance criterion: Wednesday 22:00 gate

From PLAN.md: "Gate, Wed 22:00: residual 8/8 green in CI. If not, nothing else in Stephen's lane is built until it is. Deem's lane continues on fixtures."

Operationally: the GitHub Actions `residual` job on the merged SHA on `main` reports all conclusions as `success` (per CI rule 4: read the check-runs API, require every conclusion to be success). The job runs bare with no network and no key (CI rule 1). `bench/results.json` is uploaded as a job artifact. The README badge is green.

Nothing below this line unblocks until the gate is green.
