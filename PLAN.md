# HOLD: Plan and Coordination

> Living status doc for Stephen and Deem. Updated on every task change and pushed to `main`. Single source of truth for who is working on what. Atomic commits: never bundle a status change with code.

**Project:** HOLD, a film shooting-schedule optimizer that computes the provably cheapest scene order and proves every shooting day legal against child-performer statutes and SAG-AFTRA rules, naming every violated rule with its citation when a day is not.
**Team:** **Stephen** (solver, rules, agent, streaming, API, native shells, CI, submission) and **Deem** (web app, stripboard, verdict UI, mobile day view, PWA, design)
**Hackathon:** Agentic Cinema: The Blockbuster Hackathon, IBM partner track
**Deadline:** Tuesday September 9, 2026, 2:00 PM PT (5:00 PM EDT). The submission is complete and in submitted state by Monday September 8, 21:00 ET, then edited until the deadline.
**Repo:** `github.com/StephenSook/hold`, public from commit one, Apache-2.0
**Primary dev tool:** IBM Bob 2.1 (track requirement). Both of us sign up through the hackathon's IBM resources link so usage is attributed to this entry.

Legend: DONE, WIP, TODO, BLOCKED, CUT
**Stale lock TTL: 4 hours.** A WIP task without a fresh timestamp in Notes is claimable.
**Coordination is manual.** No hooks, no CLI helper. Edit this file by hand, commit only `PLAN.md`, push.

---

## In scope and out of scope

**In scope:** the benchmark residual (8 medium instances); California, Georgia and SAG-AFTRA rules; Coogan facts for five states; one constructed labeled demo schedule; Gemini extraction of a call sheet or plain English; one Confluent re-solve-on-event loop; hosted web app, PWA, Android APK, iOS TestFlight; the three-minute video.

**Out of scope, stated so nobody builds it:** New York, Louisiana and any other jurisdiction (Louisiana caps are unverified and the registry refuses them); user accounts and multi-production persistence; on-device solving (OR-Tools is x86_64 only); Model Armor; Schema Registry unless the streaming loop closes early; Movie Magic or StudioBinder file import (proprietary formats); any industry-wide savings claim.

---

## Repo hygiene (both of us, every commit)

- Commit under your own git identity. The only trailer this repo uses is `Tool: IBM-Bob` on Bob-authored commits, added at commit time. No co-author trailers.
- No editor or assistant config in the repo; it is all gitignored. Check `git status` before every commit anyway. `.bob/`, `AGENTS.md` and `specs/` ARE committed: they are the Bob evidence.
- Stage named paths only. Never `git add -A`. Run `git ls-files | grep -iE '\.pdf$|\.env$|^private/'` before every push and expect nothing. The one PDF-free exception is none: sample documents under `data/demo/samples/` are PNG and TXT.
- No research material, no third-party contact details, ever.
- Secrets: none in the repo, none in `.bob/mcp.json` (Bob stores values literally). Cloud Run reads Secret Manager; CI uses Workload Identity Federation, no JSON keys.
- No em-dashes anywhere: code, comments, commit messages, product copy, docs, this file. Colon for elaboration, comma or parentheses for an aside, period for a clause break, hyphen for a range. Empty table cells read `n/a`. The one exemption is `rules/sources/`, verbatim third-party snapshots whose punctuation is the publisher's; a quote copied from one writes the source's em dash as a hyphen and the quote checker treats the two as equal.
- `main` is protected: the CI checks are required, so a red push cannot land.

---

## IBM Bob evidence protocol (both of us, from day 0)

Bob usage is a track gate and a judged artifact. The evidence is recorded while building, never reconstructed after.

1. **Sign up through the hackathon's IBM resources link** (both accounts). Record plan tier and starting balance in task 0.2 Notes.
2. **Commit `.bob/`, `AGENTS.md` and `specs/`.** Five write-scoped custom modes (`solver-engine`, `agent-runtime`, `mobile-shell`, `frontend`, `evidence-writer`), rules per mode, skills, real Plan-mode outputs under `.bob/plans/`, Spec Kit artifacts under `specs/`. `.bob/mcp.json` carries no secrets.
3. **Trailer on every Bob-authored commit:** `git commit --trailer "Tool: IBM-Bob"`. Never added afterwards. Test count in the subject of every engine commit (`feat(solver): pass-1 assumptions, 41 tests`).
4. **Export the session store at every phase boundary:** `uv run python scripts/export_bob_evidence.py` writes `docs/bob-evidence/bob-usage-evidence.json` (counts, tokens, cost, attribution counts; no message bodies). Commit it. The store can be lost to a crash; the committed JSON survives.
5. **Screenshots at fixed points, both accounts:** day 0, end of each phase, and at exhaustion. Gauge (hover, top-right of the Bob panel), Settings > General, and the IBM console usage page if available. Redact account identifiers only. Name: `docs/bob-evidence/bobcoins-<member>-<yyyymmdd>-<phase>.png`. When an account hits zero, that screenshot is the exhaustion record and gets its own row in the README spend table.
6. **Self-referential MCP loop:** `.bob/mcp.json` registers HOLD's own MCP server (`api/hold/mcp_server.py`: `solve_schedule`, `check_legality`, `lookup_rule`, `run_residual`) so Bob calls the solver while building it.
7. **`/review` audits:** Bob's `/review` on `api/hold/` and `api/agents/` in Phase 5; SARIF committed under `security/`.
8. **Generated attribution:** `scripts/bob_attribution.sh` writes `docs/bob-evidence/ATTRIBUTION.md` (trailer count, modes, scopes, skills, rules, MCP tools, evidence files). CI asserts it is current.
9. **Lane enforcement as a test:** `api/tests/test_bob_lane_enforcement.py` asserts the allow/refuse table over the shipped regexes. One real refusal recorded with its commit SHA in `docs/bob-evidence/lane-enforcement.md`.
10. **Build trace as a test:** `docs/bob-evidence/build-trace.md` from `git log --reverse --format='%ad %s' --date=format:'%H:%M'`; `api/tests/test_bob_usage.py` verifies each named commit exists with matching subject and time. CI checks out with `fetch-depth: 0`.
11. **Honesty log:** any evidence row not captured gets a dated statement of absence. No reconstructed transcripts, ever.
12. **`/api/status.bob_usage`** serves the aggregate (Friday) and the build trace (Sunday); the README "How IBM Bob was used" section holds the evidence-to-location table, per-account spend rows, human/AI boundary, and the engineering incident log with SHAs.

---

## The product in two sentences

We take the list of scenes and who is in each one, and we compute the cheapest possible order to shoot them in. Not a good order, the provably cheapest one. Then we check every day against child-performer law and the union contract and tell you whether it is legal, and if it is not, every rule you broke and where each one is written down.

### The three things on screen

1. **The residual.** Our CP-SAT solver against the published proven optima of the academic talent-scheduling benchmark (8 instances, MIT-licensed data): difference 0, re-run on every push in CI with no key and no account.
2. **The dollars.** A realistic schedule (constructed and labeled) with hold days and penalties disappearing, the published SAG-AFTRA rate card on screen so anyone with a calculator can check.
3. **The verdict.** An illegal day names every violated rule: citation, limit, computed value, over-by, the verbatim sentence from the statute, a deep link.

### Honesty panel (ships on `/judge` and in the README)

- Two panels, never one blended number: optimality is proven on the benchmark model; the extended model reports "best found" with the solver's bound.
- The demo schedule is constructed and says so on the UI. No public corpus of real stripboards was found (searched 2026-08-27 to 2026-09-02).
- The infeasibility core from the solver is sufficient, not minimal, and may omit co-occurring violations (OR-Tools `ortools/sat/docs/troubleshooting.md`). The independent checker lists every violation; the core explains why no legal timing exists.
- No industry-wide savings figure is published; we do not invent one.
- The solver runs on the server. The phone displays and caches.
- Louisiana hour caps are unverified and the registry refuses them rather than guessing.
- Streaming: "connected at submission time; live state at `/api/status`".

---

## Judging criteria and the surface that answers each

| Criterion | Surface | Owner |
|---|---|---|
| Technological Implementation | CI residual badge (no key), `/api/status` self-reporting models invoked, streaming state and solver version, ADK trace and adk eval on video, two-pass CP-SAT with the checker as complete enumerator | Stephen |
| Design | Real stripboard with drag, day-break banners, boneyard, 1-second animated reorder, verdict card, mobile single-day view at AAA contrast, PWA + APK + TestFlight | Deem |
| Potential Impact | Sourced rate card and hold-day rule, five-state trust facts, cumulative jurisdiction, anonymized practitioner quote if obtained (or the plain statement that none was), Georgia production counts | Stephen |
| Quality of the Idea | None of the five schedulers checked on 2026-09-02 (Movie Magic, StudioBinder, Yamdu, Gorilla, Celtx) minimizes hold cost or encodes minor hour caps as constraints; rules-as-code with citation and effective date | both |

**The headline number** is written once by a real run into `docs/FACTS.json` (`hold_days_before`, `hold_days_after`, `payroll_removed_usd`, `illegal_days_before`, `illegal_days_after`, `benchmark_matched`, `solve_ms`, `adk_eval`). README, `/judge`, the video narration and the submission read from that file. Nobody types a headline number by hand.

---

## Status Dashboard

Columns: # | Task | Files | Owner | Status | Deps | Done means | Notes. The lock lives in Notes (`WIP 2026-09-03 14:10 Stephen`).

### Phase 0: Accounts, repo, Bob evidence, scaffolds (Tue Sep 2 evening, about 6 hours)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 0.1 | Verify identities (`gcloud auth list`, `gh api user`, Devpost whoami all one person); create GCP project `hold-2026`; link billing (trial or card); enable Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Vertex AI; create the Workload Identity Federation pool, provider and deploy service account with `run.admin`, `iam.serviceAccountUser`, `artifactregistry.writer`, `secretmanager.secretAccessor` | n/a | Stephen | TODO | n/a | `gcloud config get-value project` prints `hold-2026`; billing active; WIF provider id recorded in Notes | n/a |
| 0.2 | Bob trial signups for BOTH people through the hackathon IBM resources link; plan tier and Bobcoin balance recorded here; upgrade to Pro+ or budget overage ($0.50 per coin) | n/a | both | TODO | n/a | Both gauges visible; balances logged in Notes | n/a |
| 0.3 | Confluent Cloud signup through the hackathon link; Basic cluster in the Cloud Run region; API key created; stored in Secret Manager only; Confluent CLI installed | n/a | Stephen | TODO | 0.1 | `confluent kafka topic list` works; no key in the repo | n/a |
| 0.4 | Devpost project draft, track IBM, Deem invited as team member | n/a | Stephen | TODO | n/a | Draft visible to both | n/a |
| 0.5 | Repo: `git init`, Apache-2.0 LICENSE (unmodified), README stub, `.gitignore`, this file as commit one, public remote | `LICENSE`, `README.md`, `.gitignore`, `PLAN.md` | Stephen | DONE | n/a | GitHub About shows Apache-2.0; `git ls-files` shows no PDF | bce0bd7 |
| 0.6 | Bob `/init`; `.bob/custom_modes.yaml` with the five write-scoped modes (regexes in the Lanes section); `.bob/rules-*/AGENTS.md`; root `AGENTS.md`; `.bobignore` | `.bob/**`, `AGENTS.md`, `.bobignore` | Stephen | DONE | 0.5 | Each mode refuses one file outside its scope and accepts one inside (all five tested) | db5250b, 14/14 lane checks pass |
| 0.8 | Root `pyproject.toml` + `uv.lock` (Python 3.12; ortools, google-adk==2.6.3, google-genai, google-cloud-aiplatform, fastapi, uvicorn, pydantic, confluent-kafka, hypothesis, pytest, ruff, mypy pinned); `.env.example` listing `GEMINI_MODEL`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_ENTERPRISE`, `CONFLUENT_BOOTSTRAP`, `CONFLUENT_API_KEY`, `CONFLUENT_API_SECRET`, `VITE_API_BASE`, `HOLD_FAKE_EXTERNALS` | `pyproject.toml`, `uv.lock`, `.env.example`, `api/__init__.py` | Stephen | DONE | 0.5 | `uv sync` clean on a fresh clone | 171a1dc |
| 0.10 | Web scaffold: Vite + React + TypeScript + Tailwind v4 + shadcn/ui + dnd-kit + Motion + TanStack Query + vite-plugin-pwa; HashRouter; `base: './'`; `apiUrl()` helper reading `VITE_API_BASE`; `npm run test` maps to `vitest run` excluding `tests/e2e` | `web/**` | Deem | TODO | 0.5 | `npm run build` and `npm run test` clean; tokens file committed | n/a |
| 0.11 | App Store Connect: confirm the Developer Program is active and record the Team ID; bundle id `com.stephensookra.hold`; app record; `ITSAppUsesNonExemptEncryption` NO; Test Information (description, feedback email) filled | n/a | Stephen | TODO | n/a | App record exists; Team ID in Notes | n/a |
| 0.12 | Day-0 usage screenshots, both accounts (gauge, Settings > General) | `docs/bob-evidence/bobcoins-stephen-20260902-p0.png`, `docs/bob-evidence/bobcoins-deem-20260902-p0.png` | both | TODO | 0.2 | Files committed, identifiers redacted, figures and dates intact | n/a |
| 0.15 | Pin `GEMINI_MODEL` and `GOOGLE_CLOUD_LOCATION` from the Model Garden today (a 3.x Flash id; 2.5 retires 2026-10-16 per the Vertex AI release notes); record the id, its retirement date and the source URL here | `api/hold/config.py` | Stephen | DONE | 0.1 | One constant, one test asserting it is not a 2.5 id | 573a5b3, gemini-3.1-flash-lite |
| 0.16 | Five practitioner outreach emails sent from Stephen's own account (drafts are local, never committed) | n/a | Stephen | DONE | n/a | Sent; replies anonymized on every surface | Sent 2026-09-02 14:34 ET; log in private/outreach-drafts.md; check for bounces within a day |

### Phase 1: Layer A, the residual (Wed Sep 3)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 0.7 | Spec Kit init; `specify`, `plan`, `tasks` for the solver feature committed under `specs/` | `specs/001-solver/**`, `.bob/skills/**` | Stephen | DONE | 0.6 | `spec.md`, `plan.md`, `tasks.md` exist | 93b6511 |
| 0.9 | CI skeleton: api (ruff, mypy, pytest hermetic, `fetch-depth: 0`), web (tsc, eslint, `vitest run`, build), gitleaks, em-dash gate over `git ls-files --cached --others --exclude-standard`, license guard; every gate bare; required checks set on `main` | `.github/workflows/ci.yml`, `scripts/no_em_dash.sh` | Stephen | DONE | 0.5, 0.8, 0.10 | Green on main; a planted em-dash in an untracked file turns it red; branch protection lists the jobs | 24142d1 |
| 0.13 | Evidence scripts: `scripts/export_bob_evidence.py` (read-only over `~/.bob/db/bob.db`, workspace-filtered, no message bodies) and `scripts/bob_attribution.sh`; first run committed | `scripts/export_bob_evidence.py`, `scripts/bob_attribution.sh`, `docs/bob-evidence/bob-usage-evidence.json`, `docs/bob-evidence/ATTRIBUTION.md` | Stephen | DONE | 0.6, 0.8 | Both files present after one run; trailer count reported | a8a883d |
| 0.14 | Lane-enforcement and attribution tests (regexes parsed from the yaml text, no PyYAML): frontend refuses `api/hold/model.py`, `web/android/x`, `docs/bob-evidence/x`, allows `web/src/board/x.tsx`, `docs/design/x`; solver-engine allows `api/tests/test_x.py`, `api/routes/status.py`, refuses `web/src/x`; mobile-shell allows `web/src/native/notify.ts`, refuses `web/src/board/x`; evidence-writer allows `README.md`, `docs/FACTS.json`, `specs/001/spec.md`, refuses `docs/design/x` | `api/tests/test_bob_lane_enforcement.py`, `api/tests/test_bob_attribution.py` | Stephen | DONE | 0.8, 0.13 | Green; widening `frontend` to `docs/` goes red | cfe1ac2, 24/24 pass |
| 1.9 | Contracts first: `api/hold/schemas.py` (`ScheduleInput`, `ExtractResult`, `Verdict`, `SolveResult`, SSE event models) plus committed JSON fixtures Deem builds against | `api/hold/schemas.py`, `data/fixtures/contracts/*.json`, `api/tests/test_schemas.py` | Stephen | DONE | 0.8 | Fixtures validate against the models; Deem imports them | 4239213, 10 tests |
| 1.10 | Stub deploy, not gated on the residual: `api/main.py` (plain FastAPI; API routes first; catch-all GET serves `web/dist/index.html` for non-`/api` paths; CORS for `capacitor://localhost`, `http://localhost`, `https://localhost`, the Cloud Run origin); `Dockerfile` at repo root (Node stage builds `web/`, Python stage copies `web/dist`); `deploy.yml` with `--no-cpu-throttling --min-instances=1 --max-instances=1 --cpu=2 --memory=2Gi --concurrency=80 --timeout=3600 --session-affinity`; verify from a logged-out browser (fresh-project GFE 404 trap) | `api/main.py`, `Dockerfile`, `.github/workflows/deploy.yml` | Stephen | WIP | 0.1, 0.9, 0.10 | Public URL serves the board; `/api/status` 200 with a stub; `/judge` deep link loads | WIP 2026-09-04 Stephen - files committed 8f5deee; blocked on 0.1 (GCP project) for live URL |
| 1.1 | Copy the 8 `medium/` and 3 `easy/` `.dzn` instances from `MiniZinc/minizinc-benchmarks/talent_scheduling/` with the MIT LICENSE; `bench/optima.json` (total and holding per instance, DOI 1401.5869 Table 10); identity test: `total - holding == sum_j c_j * sum_{i in ia[j]} d_i` for all 8, no solver | `bench/**`, `api/tests/test_bench_identity.py` | Stephen | DONE | 0.8 | 11 instances present; identity green on 8/8 | f9d8bcc, 11 files |
| 1.2 | dzn parser -> `Instance(num_scenes, num_actors, ia, c, d)`; tests on film116 (19, 8, c=[10,4,5,5,5,40,4,20], d[9]=2) | `api/hold/instance.py`, `api/tests/test_instance.py` | Stephen | DONE | 1.1 | Green | f9d8bcc, 9 tests |
| 1.3 | CP-SAT benchmark model: `pos`/`scene_at` with `AddInverse` (+ `AddAllDifferent`); per-actor `first_j`, `last_j`; `onset[j][i]` reified from `first_j <= pos[i] <= last_j`; objective `holding = sum_j c_j * sum_{i not in ia[j]} d_i * onset[j][i]` (constant coefficients), `total = holding + fixed`; `symmetry_break: bool` parameter; integer objective only; measure solve time per instance | `api/hold/model.py`, `api/tests/test_model_smoke.py` | Stephen | DONE | 1.2 | film116 OPTIMAL, holding 110, total 541; times recorded in Notes | a649706, ~75ms |
| 1.4 | Residual test over all 8: OPTIMAL, `objective == best_objective_bound`, holding and total equal to `bench/optima.json`; 60 s cap per instance; writes `bench/results.json` with the run SHA. If an instance misses the cap, add the redundant bound `span_j >= sum_{i in ia[j]} d_i` first; the honest path is `benchmark_matched: "7/8"` with the instance named | `api/tests/test_residual.py`, `bench/results.json` | Stephen | DONE | 1.3 | 8/8 green locally under the cap | 32508a2, 37s |
| 1.5 | Independent checker (plain Python): recompute holding and total from a permutation; assert permutation validity; equal to the solver on 8/8; rejects a corrupted permutation | `api/hold/checker.py`, `api/tests/test_checker.py` | Stephen | DONE | 1.3 | Green | 32508a2, 12 tests |
| 1.6 | Brute-force differential on `easy/tiny` and `easy/small`; Hypothesis properties (always a permutation, cost >= trivial lower bound); symmetry-break test (tiny precedence instance solved with the flag on and off gives equal cost) | `api/tests/test_bruteforce.py`, `api/tests/test_props.py`, `api/tests/test_symmetry.py` | Stephen | DONE | 1.5 | Green | 32508a2, 7 tests |
| 1.7 | CI job `residual` runs 1.1, 1.4, 1.5, 1.6 with no network and no key, 15-minute job timeout, uploads `bench/results.json`; README badge | `.github/workflows/ci.yml`, `README.md` | Stephen | DONE | 1.4, 1.6 | Badge green on main | d117b5b |
| 1.12 | Demo schedule JSON, started Wednesday evening, handed to Deem: constructed, labeled, cast letters; Georgia shoot with one California-resident minor; one-hour time-boxed search for a public-domain or CC-BY live-action screenplay for the scene list, else construct; the "before" order with 7 hold days and 1 illegal day; the sample call sheet as PNG and TXT (never PDF) | `data/demo/hold-demo.json`, `data/demo/before-order.json`, `data/demo/samples/callsheet-day3.png`, `data/demo/samples/callsheet-day3.txt` | Stephen | DONE | 1.9 | Validates against `ScheduleInput`; loads in the UI | 13f0933, 10 scenes 4 cast minor M age 14 CA |
| 1.8 | Stripboard: colored strips (INT day white, EXT day yellow, INT night blue, EXT night green), scene number, INT/EXT, set, D/N, page count in eighths, cast letters; day-break banners with totals; boneyard; dnd-kit drag | `web/src/board/**` | Deem | TODO | 0.10, 1.9 | Renders the contract fixture; drag reorders | n/a |
| 1.13 | Motion layout animation for the solved reorder (about 1 second), then a static before/after panel with two dollar totals and the delta | `web/src/board/Reorder.tsx`, `web/src/board/BeforeAfter.tsx` | Deem | TODO | 1.8 | Plays from a fixture; static frame is screenshot-ready | n/a |
| 2.14 | `/judge` skeleton: numbered itinerary, live figures from `/api/status`, benchmark table, links block | `web/src/judge/**` | Deem | TODO | 1.10 | Renders against the stub deploy | n/a |

**Gate, Wed 22:00:** residual 8/8 green in CI. If not, nothing else in Stephen's lane is built until it is. Deem's lane continues on fixtures.

### Phase 2: Layer B, the verdict (Thu Sep 4)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 2.1 | Rules registry schema (`id, jurisdiction, authority, citation, title, quote, source_url, valid_from, valid_to, params, verified, note`) and loader with temporal validity keyed to the shooting date | `rules/schema.json`, `api/hold/registry.py`, `api/tests/test_registry.py` | Stephen | DONE | 0.8 | Loader rejects a record missing citation or quote | 3b856a3, 12 tests |
| 2.2 | California: 8 CCR 11760(a) to (f) tables, 11760(i) 12-hour turnaround, LC 1308.7 curfew (no work before 5 a.m. or after 10 p.m. before a school day; 12:30 a.m. before a non-school day), 11755.1 and 11755.2 teacher ratios (1:10 in session, 1:20 otherwise), 11761 meal within 6 hours, 8-hour and 48-hour caps; the DLSE "subtract 6 hours" policy as a separately flagged layer | `rules/ca.yaml` | Stephen | DONE | 2.1 | Every record has a verbatim quote and source URL | 650b30f, 11 rules |
| 2.3 | Georgia: Rule 300-7-1-.03 Schedule of Hours (9 to 16: 10 h at location, 5 h work, 10 p.m. school night, midnight non-school; 16 to 18: 12 h, 8 h, midnight, 2 a.m.), 5 a.m. earliest, 6 consecutive days, 12-hour turnaround when working during school hours, .09 studio teacher 1:10, .04 child labor coordinator 1:10 | `rules/ga.yaml` | Stephen | DONE | 2.1 | Same bar | 650b30f, 12 rules |
| 2.4 | SAG-AFTRA minors: Young Performers Handbook tables, p.17 precedence rule, p.22 12-hour turnaround before a school day, p.23 infant restriction observed nationwide; 2026 chaperone-to-under-16 change; cumulative jurisdiction (8 CCR 11756 + GA 300-7-1-.01) | `rules/sag_minors.yaml` | Stephen | DONE | 2.1 | Same bar | 650b30f, 4 rules |
| 2.5 | SAG-AFTRA rates, hold-day half: Low Budget $810/day and $2,812/week, Moderate Low $449.05, Ultra Low $249, P&H 21% rising to 22% on 2026-09-06, hold day at full rate; integer cents, stated rounding; every figure with source URL and cycle dates, re-verified against the ratified 2026 agreement before it renders | `rules/sag_rates.yaml`, `api/hold/penalties.py`, `api/tests/test_penalties.py` | Stephen | DONE | 2.1, 1.12 | A hand calculation on `data/demo/hold-demo.json` matches the code to the cent | 650b30f, 7 tests; rates re-sourced 2026-09-02 22:18 to the 7/1/2026 minimums ($834 / $2,896 LBA, $449 / $1,560 MPA, $257 UPA), P&H 22% from 9/6/2026, in 0feb489 |
| 2.7 | Pass 1: order and day assignment fixed; call time, scene starts and meal placement free within the day window; each rule a hard constraint gated by a named BoolVar (`CA_11760e_work_cap`); `add_assumptions`; `num_workers=1`; no objective; INFEASIBLE -> `sufficient_assumptions_for_infeasibility()` -> registry -> reasons; FEASIBLE -> LEGAL with the legal call sheet as witness; five fixture days (single and multi-violation) | `api/hold/legality.py`, `api/hold/solve.py`, `data/fixtures/illegal-days/*.json`, `api/tests/test_pass1.py` | Stephen | DONE | 2.2, 2.3, 2.4, 1.12 | Five fixture days: INFEASIBLE with the expected rule ids in the core; one legal day FEASIBLE | 23c699b, 24 tests, 2026-09-02 21:27; six illegal plus one legal fixture days supersede five; core = rules that alone make the day impossible (joint-only cores labeled); GA and SAG turnaround gate on the checked day being a school day; meal rule is timing-only |
| 2.8 | Pass 2: rules as plain hard constraints on the extended model, `symmetry_break=False`, holding objective plus penalty terms, `num_workers = os.cpu_count()` in production, time limit, OPTIMAL vs FEASIBLE with bound; on INFEASIBLE re-run with rule literals as assumptions and return UNDETERMINED with reasons | `api/hold/solve.py`, `api/tests/test_pass2.py` | Stephen | DONE | 2.7, 1.3 | `data/demo/hold-demo.json` returns 0 hold days, 0 illegal days; the two panels are separate fields | d611fce, 10 tests, 2026-09-02 22:33; demo 0 hold days 0 illegal days OPTIMAL, before plan computes to 4 hold days and 1 illegal day; hold days paid only on an overnight location under the low-budget tiers |
| 2.9 | Checker enumerates EVERY violation over the concrete timeline without OR-Tools and is the source of truth for the verdict card; agrees with pass 1 on the fixture days (core is a subset of the checker's list) and with pass 2 on the solved schedule; this task stands on its own if 2.7 is cut | `api/hold/legality_checker.py`, `api/tests/test_legality.py` | Stephen | DONE | 1.5, 2.2, 2.3, 2.4, 1.12 | Green; 18 tests, demo day 3 flags 4 violations | e7ec7db, 18 tests |
| 2.10 | Quote check, Thursday version: substring test of every `quote` against a committed text snapshot per source under `rules/sources/` with a hash; `rules/verification.json`; CI test fails (never skips) if any record lacks a status | `rules/sources/**`, `rules/verification.json`, `api/tests/test_quotes.py` | Stephen | DONE | 2.4 | CI log shows PASSED; UNVERIFIABLE records labeled, not counted | 0feb489, 2026-09-02 22:18; 54 records, 53 VERIFIED against committed snapshots, 1 UNVERIFIABLE (sagaftra.org blocks scripts); previous quotes were composed, CA table and SAG rates corrected, hold-day claim conditioned on overnight location (see rules/sag_rates.yaml) |
| 2.15 | Phase 2 boundary: session-store export, screenshots both accounts, ATTRIBUTION regenerated | `docs/bob-evidence/**` | both | TODO | 0.13 | Committed with dates | n/a |
| 3.8 | Capacitor 8 scaffold (evening, no features): `npx cap add ios android`; privacy manifest (`NSPrivacyAccessedAPICategoryUserDefaults`, CA92.1); camera and notification usage strings; icons (1024 px, no alpha) and splash; `VITE_API_BASE` set to the Cloud Run URL for `cap sync` builds | `web/android/**`, `web/ios/**`, `web/capacitor.config.ts` | Stephen | TODO | 0.10, 1.10 | Both projects build and launch on simulator and emulator and reach `/api/status` | n/a |
| 2.12 | Verdict card UI: LEGAL / ILLEGAL / UNDETERMINED banner (color + text + icon), every violated rule with citation, limit, computed, over-by, verbatim quote, deep link; progressive disclosure | `web/src/verdict/**` | Deem | TODO | 1.9 | Renders from the `Verdict` fixture | n/a |
| 2.13 | Import screen: upload PNG, PDF or text; show `ExtractResult` (draft form, or the clarifying questions); Confirm button; nothing solves until confirmed | `web/src/import/**` | Deem | TODO | 1.9 | Works against the fixture | n/a |
| 3.10 | Mobile single-day view: verdict banner on top, scene cards, tap to expand, AAA 7:1 contrast on verdict and primary text, 64 to 76 dp primary targets in the thumb zone, color plus text plus icon for status | `web/src/day/**` | Deem | TODO | 2.12 | Renders at 390 px in WebKit and Chromium | n/a |

**Gate, Thu 22:00:** pass 1 returns the expected rule ids on the five fixture days. If not, Layer B ships as checker-only (2.9), labeled as such, and 2.7 is CUT with the reason recorded.

### Phase 3: Agent, streaming, production, mobile (Fri Sep 5)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 3.1 | ADK agent: `root_agent = LlmAgent(model=GEMINI_MODEL, output_schema=ExtractResult, tools=[check_legality, optimize_schedule, lookup_rule])` on google-adk 2.6.3 (output_schema and tools together is documented for this version); `GOOGLE_GENAI_USE_ENTERPRISE=True`; the three tools wrap 2.7 (or 2.9 if 2.7 was cut), 2.8 and 2.1 | `api/agents/hold_agent/agent.py`, `api/agents/hold_agent/__init__.py` | Stephen | TODO | 0.15, 2.8, 2.9 | The sample call sheet PNG extracts into a valid `ExtractResult` with `status: ok` | n/a |
| 3.2 | Structured extraction: multimodal (PNG, PDF, text) into `ScheduleInput`; natural-language constraints ("actor C unavailable days 1 to 3", "scene 7 before scene 2") into typed constraints; ambiguity returns `needs_clarification` with questions, never a guess; golden-file tests on three sample documents; under `HOLD_FAKE_EXTERNALS=1` extraction returns the golden fixture without calling Gemini | `api/agents/hold_agent/prompts.py`, `data/demo/samples/*`, `api/tests/test_extract.py` | Stephen | TODO | 3.1 | Three golden files pass; an ambiguous sample returns questions; fake mode returns the fixture | n/a |
| 3.3 | Guardrails: `before_tool_callback` allowlists the three tools and validates arguments with Pydantic; the agent never accepts a schedule (human Confirm in the UI); `/api/extract` has a 30 s timeout and one Gemini call per request | `api/agents/hold_agent/callbacks.py` | Stephen | TODO | 3.1 | An invalid tool argument is refused with a named field | n/a |
| 3.5 | Routes: `POST /api/solve` (ThreadPoolExecutor, one worker; never the event loop), `GET /api/jobs/{id}`, `GET /api/events` (SSE; objective values via `loop.call_soon_threadsafe` from the solution callback; verdict updates), `POST /api/extract` (ADK `Runner` + `InMemorySessionService`; the ADK API server is never mounted), `POST /api/set-events` (in-process event bus, which is also the `HOLD_FAKE_EXTERNALS=1` path; Confluent producer added in 4.1), `GET /api/rules`, `GET /api/bench`; verify `/api/status` answers during a solve | `api/routes/**`, `api/hold/bus.py`, `api/tests/test_routes.py` | Stephen | TODO | 2.9, 3.2 | Full loop over HTTP locally including an in-process set-event re-solve; status answers mid-solve | n/a |
| 3.6 | `GET /api/status`: computed once at startup, cached 10 minutes with `computed_at`; headline from `data/demo`; `benchmark_matched` from `bench/results.json` with its run SHA; `runtime {gemini_model, gemini_location, adk_version, ortools_version, confluent {connected:false ...}, mode}`; `scripts/facts.py` writes `docs/FACTS.json`; `api/tests/test_facts.py` checks the eight headline fields in README and docs (digits and spelled-out numerals) against FACTS, with an explicit allowlist for rules-sourced figures and citations | `api/routes/status.py`, `scripts/facts.py`, `docs/FACTS.json`, `api/tests/test_facts.py` | Stephen | TODO | 3.5 | Test green; FACTS has every headline field | n/a |
| 3.7 | Production deploy with the 1.10 flags, Secret Manager env, Application Default Credentials only; previous revision id recorded in Notes before each deploy; rollback command tested once; served bundle verified from a logged-out browser | `.github/workflows/deploy.yml` | Stephen | TODO | 3.5 | Live URL runs the loop end to end; rollback verified | n/a |
| 3.9 | iOS build uploaded, internal TestFlight confirmed, EXTERNAL TestFlight submitted with a reviewer note naming each native feature and how to reach it; API base points at the 3.7 URL, or the 1.10 shell URL if 3.7 slips | n/a | Stephen | TODO | 0.11, 3.8 | Build in Beta App Review by Fri night | n/a |
| 3.13 | Phase 3 boundary: export, screenshots both accounts, ATTRIBUTION; `/api/status.bob_usage` serves the committed aggregate | `docs/bob-evidence/**`, `api/routes/status.py` | both | TODO | 0.13, 3.6 | Endpoint matches the committed JSON | n/a |
| 3.11 | PWA: manifest, Workbox precache of the app shell, TanStack Query persisted to IndexedDB, "offline, cached as of HH:MM" indicator, no reliance on Background Sync | `web/vite.config.ts`, `web/src/offline/**` | Deem | TODO | 3.10 | Airplane mode: request fails visibly, cached verdict still renders | n/a |
| 3.12 | Camera scan UI: `Capacitor.isNativePlatform()` gate, document-scanner plugin, image to `/api/extract`; web fallback is file upload | `web/src/import/Scan.tsx` | Deem | TODO | 2.13, 3.8 | Works on a physical device | n/a |

**Gate, Fri 22:00:** the live URL runs the full loop from a logged-out browser and TestFlight is in review. Cut list item 2 fires if Apple has not responded by Sunday night.

### Phase 4: Streaming loop, native extras, APK, evidence (Sat Sep 6)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 4.1 | Confluent: topics `hold.set-events`, `hold.verdicts` (JSON, `rules/events.schema.json`); producer on `POST /api/set-events` (actor-late, scene-dropped, weather-cover); background consumer thread (auto-reconnect, `auto.offset.reset=latest`, log-and-skip on bad messages) re-solves and produces the verdict; SSE fan-out; `connected` true only after a real metadata call; in-process bus stays as fallback and `/api/status` reports which is live; `HOLD_FAKE_EXTERNALS=1` uses the bus and fixture extraction | `api/hold/streaming.py`, `api/routes/events.py`, `rules/events.schema.json`, `api/tests/test_streaming.py` | Stephen | TODO | 3.7, 0.3 | Publishing from the UI yields a new verdict on screen in under 5 s (measured); test green against the in-process bus | n/a |
| 4.2 | `scripts/simulate_set_day.py`: labeled simulation publishing a day's events at speed for the video | `scripts/simulate_set_day.py` | Stephen | TODO | 4.1 | Runs against the live cluster | n/a |
| 4.3 | Signed release APK (keystore at `~/.hold-release.jks`, gitignored, documented in Notes), `apksigner verify`, GitHub Release asset | `web/android/**` | Stephen | TODO | 3.8 | Release URL installs on a phone | n/a |
| 4.4 | Local notifications when a day flips to ILLEGAL or a minor is within 30 minutes of a cap; Android 13+ runtime permission; haptic on hard-out | `web/src/native/**` | Stephen | TODO | 3.8 | Fires on device | n/a |
| 2.6 | Coogan trust records, five states (CA Fam. Code 6752-6753, NY 12 NYCRR 186-3.5, IL 820 ILCS 206/90, LA R.S. 51:2131-2135 at $500+, NM 50-6-19 at $1,000+); Georgia none; display facts, not constraints | `rules/trust.yaml` | Stephen | DONE | 2.1 | Five records, GA explicitly absent | a6f8e0c, nine records across five states, GA absent by statement in api/hold/trust.py, 226 tests, 2026-09-02 23:10 |
| 2.11 | SAG-AFTRA penalties, second half: 12-hour rest, forced call lesser of daily rate or $900 (weekly $950), 56-hour weekend rest, meal within 6 hours, meal ladder $25 / $35 / $50 per half hour (flat $25 Ultra Low); integer cents | `rules/sag_rates.yaml`, `api/hold/penalties.py`, `api/tests/test_penalties.py` | Stephen | TODO | 2.5 | Hand calculation matches to the cent | n/a |
| 1.11 | Self-referential MCP server (`solve_schedule`, `check_legality`, `lookup_rule`, `run_residual` over stdio) registered in `.bob/mcp.json`; Bob calls `run_residual` from a Plan session | `api/hold/mcp_server.py`, `.bob/mcp.json` | Stephen | TODO | 1.4 | Bob task log shows the call; export re-run and committed | n/a |
| 4.5 | Optional: Cloud SQL Postgres for schedules and ADK `DatabaseSessionService`; only after 4.1 is closed | `api/hold/store.py` | Stephen | TODO | 4.1 | Survives a restart | n/a |
| 4.6 | Polish: empty, loading, error states on every screen; dark mode; keyboard flow; axe zero serious or critical on `/`, `/judge`, `/day/1`; report committed | `web/src/**` except `web/src/native/`, `docs/design/axe-report.md` | Deem | TODO | 3.11 | Report committed | n/a |
| 4.7 | Phase 4 boundary: export, screenshots both accounts, per-task metadata JSON from the Bob task store, Bob Shell log if used | `docs/bob-evidence/**` | both | TODO | 0.13 | Committed with dates | n/a |

**Gate, Sat 22:00:** Confluent loop closed and captured on video, or CUT with the reason recorded; the in-process bus remains and the README says so.

### Phase 5: Hardening and judge surfaces (Sun Sep 7)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 5.1 | Wired-or-cut audit: grep the shipped code for every tool, model and vendor named in README, `/judge`, `.env.example`, `AGENTS.md` and the submission draft; cut or reword until claimed equals invoked | `docs/claims-audit.md` | Stephen | TODO | 3.7 | Audit committed; zero unwired claims | n/a |
| 5.2 | Claims test: models and vendors named on judge-facing surfaces are a subset of those `/api/status.runtime` reports; non-vacuity assertion; mutation-tested once each way; streaming phrased as "connected at submission time" | `api/tests/test_claims.py` | Stephen | TODO | 5.1 | Green; both mutations go red | n/a |
| 5.3 | Independent adversarial review of the solver, legality and agent code (logic, not diff) by a second model (Gemini CLI) or a second reader; cap 3 rounds or 3 hours; every finding verified against source before a fix | n/a | Stephen | TODO | 3.7 | Rounds and outcomes recorded in Notes | n/a |
| 5.4 | Security: gitleaks over full history, dependency supply-chain check, license guard (everything permissive), `.gitleaksignore` only with hand-verified fingerprints | `.gitleaksignore`, `docs/THIRD_PARTY_NOTICES.md` | Stephen | TODO | 0.9 | Clean | n/a |
| 2.16 | Quote verification, fetching version: `scripts/verify_quotes.py` fetches each `source_url` into the gitignored cache (paced 8 to 10 s, content-checked, never trusting a 200), refreshes `rules/sources/` snapshots and `rules/verification.json` | `scripts/verify_quotes.py`, `rules/verification.json` | Stephen | TODO | 2.10 | Record complete; any UNVERIFIABLE named | n/a |
| 3.4 | adk eval: three or four text cases (extraction, NL constraint, refusal on ambiguity, tool trajectory), `tool_trajectory_avg_score` plus `final_response_match_v2`; an image case is added only if the local runner accepts an image part (try one); run once with credentials; score into FACTS via `scripts/facts.py` | `api/agents/hold_agent/evalset.json`, `api/agents/hold_agent/test_config.json` | Stephen | TODO | 3.6 | Score in FACTS | n/a |
| 3.14 | `THREAT_MODEL.md` table (asset, threat, control, residual risk), including the unmounted ADK server and the extraction timeout | `docs/THREAT_MODEL.md` | Stephen | TODO | 3.3 | Committed | n/a |
| 5.5 | README to the judged shape: problem, what it does, the three proofs, architecture (only what `/api/status` self-reports), how to run, honesty panel, whether a practitioner interview was obtained, How IBM Bob was used, streaming section, license; `JUDGE.md` 90-second walkthrough | `README.md`, `JUDGE.md` | Stephen | TODO | 3.6, 5.1, 5.12 | A fresh reader reproduces the residual from the README alone | n/a |
| 5.6 | Architecture diagram as a designed artifact naming every wired component | `docs/architecture.svg` | Deem | TODO | 5.1 | Matches the claims audit | n/a |
| 5.7 | Playwright golden path in CI under `HOLD_FAKE_EXTERNALS=1` (bus from 3.5, fixture extraction from 3.2): load, drag, solve, reorder, open the illegal day, read the citations, import the sample, confirm, publish an event, see the re-solve | `web/tests/e2e/**`, `.github/workflows/ci.yml` | Deem | TODO | 4.6, 3.5 | Green in CI without secrets | n/a |
| 5.8 | `uptime.yml`: content-check `/api/status` for `benchmark_matched`, offset minutes, fails if the URL variable is unset | `.github/workflows/uptime.yml` | Stephen | TODO | 3.7 | Newest run age matches cadence | n/a |
| 5.9 | Fresh-clone dry run on a clean machine following the README exactly; every printed command executed | n/a | Deem | TODO | 5.5 | Every step works | n/a |
| 5.10 | Video beats captured as features land (1080p60, zoomed, real device for mobile, one unbroken take for offline with a visibly failing request); `docs/video/raw/` gitignored | `docs/video/script.md` | Stephen | TODO | 3.7 | Every beat on disk | n/a |
| 5.11 | AI-tone and em-dash sweep on every judge-facing surface; PII sweep (`git ls-files` and eyeball) | n/a | Stephen | TODO | 5.5 | Clean | n/a |
| 5.12 | Bob `/review` on `api/hold/` and `api/agents/`, SARIF committed; `docs/bob-evidence/build-trace.md`; `api/tests/test_bob_usage.py`; lane-enforcement record with a real refusal SHA; exhaustion screenshots for any account at zero; honesty log for any row not captured; `/api/status.bob_usage` adds the build trace | `security/review-*.sarif`, `docs/bob-evidence/**`, `api/tests/test_bob_usage.py` | Stephen | TODO | 4.7 | Green in CI; every evidence row has a file or a dated absence statement | n/a |

### Phase 6: Video and submission (Mon Sep 8)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 6.1 | Cut the video to 3:00 or under; every spoken number from `docs/FACTS.json`; measure the shipped file (ebur128 integrated loudness -14 to -16 LUFS, duration, 1080p, fps) | `docs/video/script.md`, `docs/video/measurements.md` | Stephen | TODO | 5.10 | Measurements committed and inside targets | n/a |
| 6.2 | Upload to YouTube, public, English; confirm oEmbed 200 AND `playabilityStatus: OK` logged out | n/a | Stephen | TODO | 6.1 | Both checks recorded in Notes | n/a |
| 6.3 | Devpost: every field, track IBM, repo URL, hosted URL, video URL, Google Cloud products, other tools, team count 2; SUBMIT by 21:00 ET; reload and re-read every field | n/a | Stephen | TODO | 6.2, 5.5 | Project shows Submitted; every field re-read after reload | n/a |
| 6.4 | Gallery images captioned; thumbnail is the before/after frame | `docs/submission-assets/**` | Deem | TODO | 5.6 | Uploaded and visible on the project page | n/a |
| 6.5 | Click every link on every judge-facing surface from a logged-out browser and a phone; table of URL, status and expected title committed | `JUDGE.md` | both | TODO | 6.3 | Every link 200 with the expected title | n/a |
| 6.6 | Phase 6 boundary: export, screenshots both accounts | `docs/bob-evidence/**` | both | TODO | 0.13 | Committed with dates | n/a |

### Phase 7: Freeze and final (Tue Sep 9)

| # | Task | Files | Owner | Status | Deps | Done means | Notes |
|---|---|---|---|---|---|---|---|
| 7.1 | Freeze at wake. Only claim-correcting, guard-adding, test-adding and documentation changes; each deferral recorded with its reason | `PLAN.md` | both | TODO | 6.3 | Deferral list in Notes | n/a |
| 7.2 | Re-verify the served bundle of every surface (grep for a fix-unique string), `/api/status`, TestFlight state, APK link, CI green per job on the merged SHA via the check-runs API | n/a | Stephen | TODO | 7.1 | Each check recorded in Notes | n/a |
| 7.3 | Final Devpost re-save by 12:30 PM PT; confirm submitted state in the UI and by re-fetching the project | n/a | Stephen | TODO | 7.2 | Confirmed twice | n/a |
| 7.4 | Post-submission: calendar entries for Oct 1 (Confluent card before the trial ends) and daily uptime checks through Oct 8; links re-clicked weekly | n/a | Stephen | TODO | 7.3 | Calendar entries exist | n/a |

---

## Cut list, ranked, decided now

| Order | What goes | Decision point | What it costs |
|---|---|---|---|
| 1 | Camera document scan (3.12) | Sat Sep 6 noon | One native feature; upload path remains |
| 2 | External TestFlight (3.9) | Sun Sep 7 night | The public TestFlight link; internal TestFlight + APK + PWA remain |
| 3 | Confluent loop (4.1, 4.2) | Sat Sep 6 22:00 | The event-driven story; the in-process bus keeps `POST /api/set-events` working; README says Confluent was not used |
| 4 | Self-referential MCP (1.11) | Sat Sep 6 | One Bob-evidence item |
| 5 | Coogan records (2.6) and the meal-ladder half of penalties (2.11) | Sat Sep 6 | Display facts and two penalty types; hold-day rate remains |
| 6 | Local notifications and haptics (4.4) | Sat Sep 6 | One Apple 4.2 mitigation; offline and native nav remain |
| 7 | Cloud SQL persistence (4.5) | Sat Sep 6 | Sessions in memory; seeded demo loads from the repo |
| 8 | adk eval (3.4) | Sun Sep 7 | The `adk_eval` field in FACTS reads `not run` |
| gate | Pass 1 (2.7), only on a failed Thu 22:00 gate | Thu Sep 4 22:00 | The solver-proven verdict; the checker (2.9) still lists every violation with citations, labeled "checked, not proven", and 2.8 runs without the assumptions explanation path |

**Never cut:** the residual and checker with the CI badge, the verdict pass with citations, Gemini extraction through ADK, the hosted URL, `/api/status`, `docs/FACTS.json`, the video.

---

## Shared Contracts

| Contract | Owner | Consumers | Definition |
|---|---|---|---|
| `ScheduleInput` | Stephen | Deem, agent | `api/hold/schemas.py`: scenes (id, number, int_ext, day_night, set, pages_eighths, cast_ids, location_id), cast (id, letter, age, resident_state, day_rate_cents, rate_tier), days (date, call, wrap, school_day, `school_night: bool or null`: the following calendar day is a school day; null derives it from the next shoot day when that is the next calendar date, otherwise assumes true and labels the assumption), constraints (availability windows, precedence), jurisdiction (shoot_state), `constructed: bool`, `overnight_location: bool` (default false; under the SAG-AFTRA low-budget agreements consecutive employment, and so paid hold days, applies only on overnight locations); `days` in chronological order with unique dates, rejected otherwise (announced 2026-09-02 22:44, validator follows under a CONTRACT commit). Fixture: `data/fixtures/contracts/schedule-input.json` |
| `ExtractResult` | Stephen | Deem, agent | `{status: ok or needs_clarification, schedule: ScheduleInput or null, questions: list[str], notes: str}`; Gemini-friendly (Literal enums, no free-form dicts) |
| `Verdict` | Stephen | Deem | `{status: LEGAL or ILLEGAL or UNDETERMINED, day, violations: [{rule_id, citation, title, limit, computed, over_by, quote, source_url, jurisdiction}], core_rule_ids, witness, reason}`; the checker fills `violations`, the solver fills `core_rule_ids`; `reason` is one sentence for the card (why UNDETERMINED, or how the core reads); `witness` (LEGAL only) keys: `day, date, crew_call, crew_wrap, heuristic, scenes: [{id, start, end, cast_ids}], minors: {cast_id: {call, dismiss, work_minutes, location_minutes, meal: {start, end} or null}}`, times as `HH:MM` |
| `SolveResult` | Stephen | Deem | `{pass1: Verdict[], pass2: {order, status: OPTIMAL or FEASIBLE or UNDETERMINED, holding_cents, total_cents, bound, hold_days, penalties_cents, reasons}, checker: {agrees: bool}, benchmark: null or {instance, published, ours, residual}}` |
| SSE events | Stephen | Deem | `event: objective` `{job_id, value, bound, t_ms}`; `event: verdict` `{job_id, verdict}`; `event: set-event` `{kind, payload, source: ui or simulation}` |
| `/api/status` | Stephen | judges, README, video, tests | Unauthenticated; shape frozen after 4.1; cached 10 minutes with `computed_at`; `runtime` names what is invoked and `mode` (live or fake externals) |
| API base and CORS | Stephen | Deem, native shells | Web uses relative `/api`; native builds set `VITE_API_BASE` to the Cloud Run URL; server allows `capacitor://localhost`, `http://localhost`, `https://localhost`, the Cloud Run origin |
| Rules record | Stephen | Deem, checker, solver | `rules/schema.json`; `quote` verbatim or the record is UNVERIFIABLE and excluded from claims; every numeric param is stated by the quote, an `evidence: "..."` fragment in the note, a `derived:` expression or a counted `assumption:` (CI); `jurisdiction` enum gains NY, IL, LA, NM for the trust records (2.6); a record with `params.kind: trust` is a display fact that never enters the checker or the solver (announced 2026-09-02 22:44, lands under a CONTRACT commit) |
| `docs/FACTS.json` | Stephen | README, video, submission, tests | Written only by `scripts/facts.py`; hand edits fail CI |
| Kafka payloads | Stephen | Deem (SSE), simulation | `rules/events.schema.json`; every event carries `source` |

Contract changes are announced in this table BEFORE they are committed, with a `CONTRACT:` commit prefix.

---

## Lanes and Bob modes

Stephen: `api/**`, `rules/**`, `bench/**`, `scripts/**`, `data/**`, `docs/**` except `docs/design/**`, `security/**`, `specs/**`, `web/android/**`, `web/ios/**`, `web/src/native/**`, `web/capacitor.config.ts`, root files.
Deem: `web/**` except those four native paths; `docs/design/**`.

| slug | Owner | fileRegex (JavaScript) |
|---|---|---|
| `solver-engine` | Stephen | `^(api/(hold\|tests\|routes)/\|pyproject\.toml$\|uv\.lock$\|bench/\|rules/\|scripts/\|data/)` |
| `agent-runtime` | Stephen | `^(api/(agents/\|main\.py$)\|Dockerfile$\|api/hold/(streaming\|mcp_server)\.py$)` |
| `mobile-shell` | Stephen | `^web/(android\|ios\|src/native)/\|^web/capacitor\.config\.ts$` |
| `frontend` | Deem | `^web/(?!android/\|ios/\|src/native/\|capacitor\.config\.ts$)\|^docs/design/` |
| `evidence-writer` | any | `^docs/(?!design/)\|^README\.md$\|^specs/\|^security/` |

Overlap between Stephen's own modes is intentional. Root files (`.github/**`, `.gitignore`, `LICENSE`, `PLAN.md`, `AGENTS.md`, `.bob/**`, `.bobignore`, `.env.example`) are edited in Bob's built-in Agent mode or by hand. A file in the other person's lane is a question in Open Questions, not an edit.

---

## Decisions (locked)

- **D1 Proof before pixels.** Residual 8/8 in CI is the first deliverable; the identity test runs before the solver exists.
- **D2 Two passes, never one.** Legality with assumptions (single worker, no objective, times free) for the verdict; cost minimization with legality as hard constraints for the schedule. The solver structurally cannot emit an illegal schedule.
- **D3 Two panels, never blended.** Optimality is claimed only on the benchmark model. The extended model reports "best found" with the bound.
- **D4 Cite or refuse.** No legal statement without citation, verbatim quote, source URL and effective dates. Unverified values are refused.
- **D5 Cumulative jurisdiction.** "Comply with both, stricter controls each field."
- **D6 Gemini has one load-bearing job.** Document or plain English into typed constraints or clarifying questions, plus a cited explanation. A human confirms before anything solves.
- **D7 Headline numbers come from FACTS.json only.**
- **D8 Constructed demo data is labeled.** Cast letters, not names. The rule side is always real.
- **D9 Streaming is load-bearing or cut.** A closed re-solve-on-event loop, or the in-process bus and a plain statement.
- **D10 Mobile floor ships regardless.** PWA, internal TestFlight and APK are guaranteed; external TestFlight cannot gate the submission.
- **D11 One Cloud Run instance, instance-based billing.** The job store, SSE subscribers and consumer live in-process; `--max-instances=1 --no-cpu-throttling`.
- **D12 The ADK API server is never mounted.** google-adk runs through a `Runner` behind our own routes.
- **D13 The checker is the source of truth for violations.** The solver core explains; the checker enumerates.
- **D14 Manual coordination, no hooks.**
- **D15 No em-dashes anywhere.** Gate in CI.
- **D16 Page-per-hour is a labeled heuristic.**
- **D17 Five trust states.** CA, NY, IL, LA, NM. Georgia none.

---

## CI rules

1. Every gate runs bare. No pipe on the exit path.
2. A conditionally skipped test is a false green. Guards fail under CI, never skip.
3. Guards resolve their file set with `git ls-files --cached --others --exclude-standard`.
4. Never trust a `--watch` exit code. Read the per-SHA check-runs API and require every conclusion to be success.
5. Watch the post-merge run on `main` on the merged SHA.
6. Verify what a commit contains: `git show HEAD:<path> | grep -c '<unique string>'`.
7. Content-check, never status-check.
8. Never let an unverified figure become a test assertion.
9. A quote must be verbatim or it is labeled a paraphrase.
10. Pin every dev tool before the freeze.
11. `pytest api/tests` is hermetic: no test hits the live URL or fetches a source; network tests carry `@pytest.mark.network` and are deselected by default.

---

## Definition of done

- [ ] Public repo, Apache-2.0 detected in About, `.bob/` and `specs/` committed, no PDFs, no PII, no assistant config files
- [ ] Bob evidence complete: `Tool: IBM-Bob` trailers on Bob-authored commits, session-store export and screenshots for both accounts at every phase boundary and at exhaustion, ATTRIBUTION.md current, lane-enforcement and build-trace tests green, `/review` SARIF committed, `/api/status.bob_usage` matching the committed JSON, self-referential MCP wired unless cut
- [ ] CI green per job on `main`: identity, residual 8/8 (or the named 7/8), checker, brute force, symmetry, quote record, claims, lane, attribution, em-dash gate, gitleaks, license guard, web build, e2e under fake externals
- [ ] Live hosted URL runs the loop logged out: drag, solve, animated reorder, verdict card listing every violation with citation and quote, import, confirm, on-set event, re-solve over SSE (Confluent or bus, stated)
- [ ] `/api/status` serves the cached headline and names what is invoked
- [ ] `docs/FACTS.json` written by a real run; README, `/judge`, video and submission read from it
- [ ] Installable PWA with offline cached verdict; signed APK on a GitHub Release; internal TestFlight confirmed; external TestFlight link if approved
- [ ] Streaming loop closed and on video, or cut and stated
- [ ] README with the honesty panel, the interview line, and the How IBM Bob was used section
- [ ] Video 3:00 or under, loudness-measured, every number from FACTS, public and playable logged out
- [ ] Devpost submission in submitted state Sep 8, re-verified Sep 9
- [ ] Post-submission: Confluent card added by Oct 1, Cloud Run warm, uptime freshness checked daily through Oct 8

---

## Verification, by a stranger

Prerequisites: uv, Node 22, jq. The residual suite takes about a minute on a laptop.

```bash
git clone https://github.com/StephenSook/hold && cd hold
uv sync && uv run pytest api/tests -q
uv run python scripts/facts.py --check
cd web && npm ci && npm run build && npm run test
curl -s https://HOLD_URL/api/status | jq
```

Replace `HOLD_URL` with the hosted URL printed at the top of the README. Then, logged out: open `/#/judge`, follow the numbered itinerary. On a phone: install the PWA, turn on airplane mode, watch a request fail and the cached verdict still render.

---

## Open Questions

- [ ] **Q1 (Stephen, Wed):** does `Solve()` release the GIL on this build so `/api/status` answers mid-solve? If not, a `spawn`-context process with a `Manager().Queue()` replaces the thread in 3.5.
- [ ] **Q2 (Stephen, Thu 22:00):** if the pass-1 gate fails, 2.7 is cut and Layer B ships as the checker (2.9) labeled "checked, not proven"; record the reason here.

---

## Coordination Protocol

1. Before starting a task: set WIP, add a timestamp and your name in Notes, commit `PLAN.md` only, push. That is your lock.
2. After finishing: flip to DONE, commit, push.
3. Blocked: BLOCKED plus a one-line reason, ping the other.
4. Before starting any task: `git pull` and re-read this file.
5. Hotfixes skip the protocol. Commit the fix, update this file after.
6. Status commits are atomic: `status: 2.7 WIP pass-1 assumptions`.
7. Code commits: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), one logical change per commit, subject 100 characters or fewer, `--trailer "Tool: IBM-Bob"` when Bob authored the diff.
8. Contract changes: announce in Shared Contracts first, `CONTRACT:` prefix.
9. Handoffs: `-> Name` in Notes.
10. Stale locks: 4 hours without a commit is claimable; replace owner and timestamp, ping first.

_Last updated: 2026-09-02 by Stephen. Day zero._
