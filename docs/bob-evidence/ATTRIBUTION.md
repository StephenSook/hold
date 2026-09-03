# Bob Attribution

Generated: 2026-09-03 01:13 UTC

## Summary

| Metric | Value |
|---|---|
| Total commits | 35 |
| Bob-authored commits (Tool: IBM-Bob trailer) | 25 |
| feat commits | 8 |
| fix commits | 3 |
| chore commits | 5 |
| docs commits | 6 |
| ci commits | 1 |
| test commits | 1 |
| CONTRACT commits | 1 |
| status commits | 10 |

## Modes used

Five write-scoped custom modes configured in `.bob/custom_modes.yaml`:
- `solver-engine`: api/hold/, api/tests/, api/routes/, bench/, rules/, scripts/, data/
- `agent-runtime`: api/agents/, api/main.py, Dockerfile, streaming/mcp modules
- `mobile-shell`: web/android/, web/ios/, web/src/native/, capacitor.config.ts
- `frontend`: web/ (non-native paths), docs/design/
- `evidence-writer`: docs/ (non-design), README.md, specs/, security/

## Build trace

```
15:57 bce0bd7824fd5c5ca21c879489bc335727623471 chore: init repo, Apache-2.0, README stub, .gitignore, PLAN.md
15:58 f20a78635fef0dbbdad1a7e09e26b0f3a46eb7d7 status: 0.5 DONE 0.6 WIP 2026-09-03 Stephen
16:05 db5250b03975883b19aa6a08cc26853994b5da6f chore: Bob init, five write-scoped modes, AGENTS.md, .bobignore
16:06 813d7982467704500ec1aa6b9c29c91bd252a41f status: 0.6 DONE 0.8 WIP 2026-09-03 Stephen
16:16 171a1dcd2736786b00e1c8a4479bae0234b24a9c chore: root pyproject.toml, uv.lock, .env.example, api/__init__
16:17 04fdf8bf4287fa68c439ea102b17ec5c98501206 status: 0.8 DONE 0.9 WIP 2026-09-03 Stephen
16:20 24142d17102baa366f78e2d4a356a9ab8b5ad99a ci: skeleton - ruff, mypy, pytest, residual job, gitleaks, em-dash gate, license guard
16:23 93b651146dbaece3bb6478654e3c92a20b6dca44 docs(specs): 001-phase0-and-solver spec kit, plan, tasks
16:23 afaae938b8c28d7a485d5114b2540b845f4a7ac0 status: 0.9 DONE 0.7 DONE 0.13 WIP 2026-09-03 Stephen
16:30 a8a883dcfbde6ac57134989dcd02b5e457eef928 chore(evidence): export_bob_evidence.py, bob_attribution.sh, first run output
16:41 cfe1ac2f68cc622b60c8997dcf802060cb2107e4 test(evidence): lane-enforcement and attribution tests, 24 tests
16:45 573a5b3b1bd7303ea089c6b456ded9412b5c9660 chore: pin GEMINI_MODEL gemini-3.1-flash-lite config.py, 5 tests
16:45 90fffbaf9b6816bbd946e2ffabb170f667f3863a status: 0.13 DONE 0.14 DONE 0.15 DONE 1.9 WIP 2026-09-03 Stephen
16:58 4239213b767536b5722c76b7362c0351f294d0b8 CONTRACT: schemas.py ScheduleInput ExtractResult Verdict SolveResult, 4 fixtures, 10 tests
17:18 f9d8bcc1230f3a67af033a158d989726aa437698 feat(solver): bench instances, optima.json, dzn parser Instance, identity 8/8, 19 tests
17:25 a64970638ef34a2c5d7000b37b8f173b59d398a7 feat(solver): CP-SAT benchmark model pos/scene_at onset objective, 2 tests
18:15 32508a213fc0cc02dd72a07fb10d69110c9c3f64 feat(solver): checker + residual 8/8 + brute-force + props + symmetry, 28 tests
18:16 aad91ccaff1a7203447d1194d5ac0190df209d41 status: 0.14 DONE 1.1-1.6 DONE 1.9 DONE 1.7 WIP 1.10 WIP gate green 2026-09-03 Stephen
18:23 12a7424e595d190088807a56549f5397a437bab7 fix(ci): ruff lint errors, web cache guard when scaffold absent, 88 tests
18:40 d117b5ba6e0b66bf02ef2aa9c3d16fd39a44dca0 fix(lint): mypy clean - type args, LinearExpr.sum, dict access, 88 tests
18:42 4512170402ca5386ccb089f5d85b28d1f5e4b5da status: 1.7 DONE, 1.10 WIP 2026-09-04 Stephen
19:02 e73aca4bf13cbe963d9f9aa8ad7648525992e521 docs(evidence): Bobcoin usage screenshot stephen 2026-09-04 p1 (50/50 exhausted)
19:07 8f5deee3043e952547d92ab58851061aa6a4f940 feat(deploy): stub api/main.py, Dockerfile, deploy.yml, /api/status, CORS, SPA fallback
19:07 ef5131bbd7a32de31e370135bf62cb7655e3eb00 status: 1.10 WIP files committed 8f5deee, blocked on 0.1 GCP project for live URL
19:22 474b5c9c6b43ecf7f84295e74eedaf3d5deb3ff1 docs(evidence): Bobcoin usage screenshot stephen account3 2026-09-04 p1 (50/50 exhausted)
19:23 13f09333ac833d4dd1ff39d16c20abbcd3f622e4 feat(demo): constructed schedule 10 scenes 4 cast GA minor, callsheet day3, 7 hold days
19:23 109c74c7981ab7917e7ed0c62a8a49f4f938719e status: 1.12 DONE 13f0933, account3 bobcoin evidence committed 474b5c9
19:28 83a83754671449bacaaa919ccdf3e4e683d9bb03 docs(evidence): rename account3 screenshot to account2 (yahoo=acct2, stevefunds=acct3)
19:33 3b856a36995708987bc42d5b3f9f25bb1104f850 feat(rules): registry schema.json + loader registry.py, 12 tests
19:43 650b30f29bd0a2da3c75427a2b2fa83d8f99e6d0 feat(rules): registry parser, 34 rules (CA/GA/SAG), penalties calc, 19 tests
19:49 ef148ae0af7cd330312809a64e4de25d75fc8a32 fix(lint): ruff I001/SIM102/F401 in penalties.py and test_penalties.py
20:15 e7ec7db0434363d92afaa280d376c816d84f0839 feat(checker): legality violation enumerator, 18 tests
20:19 f00aa114d60ebd987a007a5722ae0e52c4514d0b status: 2.1/2.2/2.3/2.4/2.5/2.9 DONE
21:13 82af9fe0add41dfc8bd67684d4b7abb4c71f78a8 docs(evidence): Bobcoin exhaustion screenshot stephen account3 2026-09-02 p2 (50/50)
21:13 ddc1d9eb7deda18c3bb74e71012e542aaa6f73b6 docs(evidence): redact account emails and correct capture dates on p1 screenshots
```
