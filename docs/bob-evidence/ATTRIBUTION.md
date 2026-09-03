# Bob Attribution

Generated: 2026-09-03 16:14 UTC

## Summary

| Metric | Value |
|---|---|
| Total commits | 148 |
| Bob-authored commits (Tool: IBM-Bob trailer) | 25 |
| feat commits | 24 |
| fix commits | 37 |
| chore commits | 10 |
| docs commits | 22 |
| ci commits | 4 |
| test commits | 4 |
| CONTRACT commits | 5 |
| status commits | 39 |

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
21:13 ce06c0313597480f4e6773aadeb6600c70fe4f07 docs(evidence): regenerate ATTRIBUTION.md build trace
21:13 cc8defb2072c103a7eaceeb7cfd290c2f7606081 chore(hygiene): generic local-config ignore patterns
21:13 50181227558130043898da9c2999010cb2181c84 status: 2.7 WIP 2026-09-02 21:13 Stephen
21:17 d40c556e19b58b412df872c0b16433f02254dd47 feat(checker): timeline path, meal rule, night-typed earliest call, consecutive-date turnaround, 24 tests
21:27 0535519ee794727bcc62ccc81f3e514290f4e040 refactor(checker): public applicability predicates shared with pass 1, 24 tests
21:27 23c699bc0977acc88abf9b540afc359a85a41b6a feat(solver): pass-1 legality model with named rule assumptions, 7 fixture days, 24 tests
21:27 781f999f6745f26f465015b4c5f077d75cc13706 docs(demo): correct the illegal-day reason in before-order.json
21:27 37e5fa439c21585751a986e861111f9d7bd85cc3 docs(contracts): document Verdict.witness keys in Shared Contracts
21:27 a4f27e48d81397f8caee5b14ec87d7a754b0c30c status: 2.7 DONE 23c699b 2026-09-02 21:27 Stephen
21:35 9ce460c8253c46ca237324f6a4a1e13e58daf57c status: 2.10 WIP 2026-09-02 21:35 Stephen
21:40 0cbcfeedfb79dac134d5f14c65dd7d07b27553eb fix(solver): scope errors and invalid models never read as scheduling verdicts, 28 tests
21:41 8f9d0ee1253a84cb5365f25b0f0ca5bd4223bfe1 fix(solver): a missing or empty day scene list is never LEGAL, 30 tests
21:42 61d17ae3bee4d3829099996bc88a81d7fdde7298 fix(checker): a minor is under 18, and proxy violations only for minors on set, 61 tests
21:43 0319cb243c3d4ad8ed3f89f2f6c8a065f4b2407e fix(checker): prev_dismissal override reaches the checker, one work-cap selection, 64 tests
21:44 d5b0d829a4ed9e1a5a129eb2b89b05bd9d37df13 fix(solver): meal rule also bounds the stretch after the meal, 66 tests
21:47 3b22f71757bdbac492403a824134697d2391e469 test(solver): joint-only case rebuilt around the post-meal bound, 66 tests
21:49 f493bc86261a4f52afb273aae1c0cd4b49c98e4b fix(solver): dangling or duplicate cast and scene ids are UNDETERMINED, 69 tests
21:52 ca4890e04cf2378b06a6de4ad1156cc3659eeda1 fix(solver): consecutive days count the minor own worked dates, 73 tests
21:53 1112f165f114d1a353d8a6578df5aa279254cd1f fix(types): annotate the per-day scene list and the empty day map, mypy strict clean
21:55 31158b0789a100cdb97013352e89db683a7a3567 docs(contracts): announce Verdict.reason, ShootDay.school_night, ScheduleInput.overnight_location
21:56 dec45d889b2835609ed69951466a326d03aa771c CONTRACT: Verdict.reason, ShootDay.school_night, ScheduleInput.overnight_location, 80 tests
22:16 0feb48958949008827da0a217c358ad2ddcffa85 feat(rules): every quote verbatim from a committed source snapshot, 54 records, quote check in CI, 197 tests
22:18 47342738454969df559cc31fdf28f412bd109798 docs(demo): July 2026 Low Budget day rate, overnight location declared, hold-day condition on the honesty panel
22:18 ad9c9b896c3ab7cf937ff366d49120e7b78f352e status: 2.10 DONE 0feb489 2026-09-02 22:18 Stephen; 2.5 rates re-sourced
22:23 1c5d82a8a913fade9a2413fa9026e0d3c92db009 fix(solver): crew meal on a minor line only inside that span, tidy fallback noted, 9 more tests
22:26 1266006dc4180644ea51bf4d1cf224a77d587b89 status: 2.8 WIP 2026-09-02 22:26 Stephen
22:33 d611fceebb62600fa0bb9f280e2d836b8ac2bc78 status: 2.8 DONE 1266006 2026-09-02 22:33 Stephen
22:34 eb9a261103089fbf325a18a42d86d00f5a25da32 status: 2.8 DONE note corrected to d611fce (the feature landed after the status commit)
22:44 6b75832e872bdcaee22e19d18d67d16bad5c9b4e status: 2.6 WIP 2026-09-02 22:44 Stephen; two contract changes announced
22:48 8dd9ebe3f48646c943a9870cd2f33454aee594b2 fix(checker): non-school work caps reach the checker, 212 tests
22:49 cdea6ab4d0faadfc3fab960fedd29ef0f175ff9b fix(checker): apply the record age bracket before every check, 213 tests
22:57 f7394778b79b5f4f4b7190526d5f3b84909c7547 CONTRACT: ScheduleInput.days chronological with unique dates, 217 tests
22:57 4089ae22d9d86f1493c0c0ac2fa083ac44e2a5c2 fix(solver): blame the assumed school night only for night-dependent cores, 217 tests
22:57 2f1bbc0e1960c32d9d5155aec6ae0449dfcba10e fix(quotes): hyphens touching a digit are never optional in quote verification, 217 tests
23:02 2bda6c8ca4719160b0d793007309a5dfe519b5bd feat(quotes): every numeric param is evidenced or labeled, 220 tests
23:02 55b425305f470a41057b604aaaa550acb28a83a1 docs: honesty panel and the rules-record contract name the parameter evidence check
23:05 c8b17d3d72e7f4d4a097670e63fec1709c4d89db CONTRACT: rules record jurisdictions NY, IL, LA, NM and params.kind trust, 222 tests
23:10 a6f8e0c73959b0ca3fc3a705e1864b8fc7e4f2ec feat(rules): Coogan trust records for five states, verbatim, display only, 226 tests
23:10 5fb1dadfa733ba105713ced856e0d5c0fce9f786 status: 2.6 DONE a6f8e0c 2026-09-02 23:10 Stephen
23:18 f95e0d272a82de36045ddd54e8786dd8df264623 fix(api): the SPA fallback annotation made the app unimportable, 227 tests
23:21 242bed82bca8b75eb560466e66723d2ef6337bcc feat(status): /api/status from FACTS.json, scripts/facts.py writes the headline, 235 tests
23:21 13c2a4cb114b05f6f26db5718c6af545f58ff757 status: 3.6 DONE 242bed8 2026-09-02 23:21 Stephen
23:23 6b787f6261b0f99758a0188c6d667272360fe4fb ci(deploy): pass with a notice when the GCP secrets are absent
23:43 1182cb3dbb7477b275f7a4fbcbebdaedc81a56d6 feat(api): solve jobs, SSE events, set-event re-solve, extract, rules and bench routes, 240 tests
23:43 40804fb7b4bef1d209fbbab51b77858abe1863cd status: 3.5 DONE 1182cb3 2026-09-02 23:43 Stephen
23:46 919ba94dd5e5cca90f034864dda266b0032ab3dd fix(penalties): refuse a shoot date no rate record covers, 243 tests
23:46 90f4d3584a2439b02afa775408102d07b84baabb test(quotes): pin the records that use derived, evidence and assumption markers
23:46 f1749cbd3f62b28e90ddf64f5266129c9d4e72ea docs(env): template names the model the code pins and the two variables the API reads
23:48 2ca72c9be647013fe166b364cc87008b7316071b docs: threat model with a status column, task 3.14
23:48 d0dd9749409bfebc22bdfdf95f6be56dc57e940b status: 3.14 DONE 2ca72c9 2026-09-02 23:48 Stephen
23:54 18584fcbdd21b302ad1cf5f5371405f911f9ec91 feat(agent): HOLD extraction agent on google-adk 2.6.3 with tool guardrails, 248 tests
23:54 a2139e37d07146e4fc091d769ad1eac299730c8d status: 3.1 WIP, 3.3 DONE 18584fc 2026-09-02 23:54 Stephen
23:57 37a0f9898b8693dea307d08bb6b5b29618604cec docs(demo): the sample call sheet carries no legality claim
23:57 794163c038bbbf5219bbc33c4f816b3be59b1aa3 chore(gcp): idempotent setup script for task 0.1
00:00 09731975bb751a3a61c750fd45c3b4dc0ce37d96 feat(agent): adk eval set with four text cases, 249 tests
00:00 62c3e28734854dc27fb8cf5f3fd31a25b968a2e3 status: 3.4 WIP 0973197 2026-09-03 00:00 Stephen
00:02 1cf41841d3658a384a07a96243e0355b9a728278 docs(readme): the dollars panel claims hold days only; penalties are not modeled yet
00:05 b588cbea03d1bde11b508d5853971ded40214a0d test(claims): judge-facing surfaces claim only what /api/status reports, 254 tests
00:05 860342adf67d57f33eb88fb6a6d206c9dfd8ba60 status: 5.2 DONE b588cbe 2026-09-03 00:05 Stephen
00:08 09b991a7d5d9058968fe34595ccef4434471764f feat(sim): labeled set-day simulation against the HTTP loop, 255 tests
00:08 b616b4788b3785b0ac35d3781967b3f9c8280b82 status: 4.2 WIP 09b991a 2026-09-03 00:08 Stephen
00:11 a361f0d22f931be6a8a560bde003d8425108a06e build(docker): the image builds before the web app exists, 256 tests
00:14 373ce73a0ffa06530f028f56da8163ff6a55cfc9 docs(plan): status symbols in the task table
00:24 d18ab882c9d86313d354a6dfc20149d7cb5a06b5 fix(status): a secret seeded with the placeholder "unset" reads as absent, 257 tests
00:24 d58e615487d2de588666eb19645f33b1954d85d2 build(docker): run uvicorn from the built venv
00:25 f2c1d528b9ce62b0fb519e0079d2b4aa2a8b69f3 chore(gcp): setup script fixes from the first real run
00:25 1ebf11f7ae859d5c65cd98132246e67abad1cb7b status: 0.1 DONE 2026-09-03 00:25 Stephen
00:31 adadf31981d138d5f7cf8f30135e0960d32155f6 fix(quotes): a line-end hyphen is optional only between letters, 257 tests
00:31 e7a88523ea35f17909a3b95acfbb61566d95f06c docs: live Cloud Run URL in the README
00:31 de50f0c2292fc21f753d0ff7b5cf95dcec089c99 status: 1.10 DONE 2026-09-03 00:30 Stephen, live at https://hold-fwmdq7fc3q-uc.a.run.app
00:33 903e1b7f1b3523de30ad7097613ff183a0127c02 ci(deploy): CORS origin from the service URL, not the project-number form
00:33 ab86216717d3a4298b5b7755a4ccc3c51fefaa34 ci(uptime): scheduled content check of the live /api/status
00:33 2c6db84f2c06d111ffb41491090b2395a68bc42a status: 5.8 DONE 2026-09-03 00:33 Stephen
00:37 5ce248740d9b83fb1b59c833c23f72444519a5f5 fix(pass2): re-judge turnaround on each minor's own dismissal, 259 tests
00:42 9480ecd1cd5548129baad72069f9a8f6d6caa88f fix(quotes): every param is evidenced with its unit, 263 tests
00:45 bf3aea32845a884e3ecf777257665c6a42713396 fix(pass2): hold days count the calendar days between work days, listed or not, 265 tests
00:45 05a16a10126d25e06ac107be20befe6743f8b6ff status: 5.3 WIP 2026-09-03 00:45 Stephen, three review rounds folded
00:48 29698205d507fbe398e227185cd03f12ee1838ff fix(extract): an unexpected failure answers 502 with its cause, 266 tests
00:51 ae5f776b1d4590cbd2fae09240f28f780038b44e fix(config): Gemini runs on the global Vertex location, 266 tests
00:53 fd57f2b3e6379ca78d1967d863b3342bf6325ebf fix(extract): the 502 names the failure class, the message stays in the log, 266 tests
00:56 a098ef1e8cca7c95a1b846b566cfbdef9cf5afbd fix(agent): at most three model calls per request, 266 tests
01:01 529f8cc3ec26eff6e13928a2b2296609b57f6177 fix(agent): extraction runs a tool-less twin of the agent, 267 tests
01:05 359c9cd1e7bcd6a07bd71f1efb89180a80d12277 feat(extract): first live golden, the constructed call sheet extracts to status ok, 268 tests
01:05 74fb88bee24ec8c0467ea43217823ddca6b1775e status: 3.1 DONE, 3.2 WIP 359c9cd 2026-09-03 01:05 Stephen
01:08 ea2f5ae8f20143b8bf2d4d147c6367bc2272e4e5 feat(extract): goldens for the constraints note and the ambiguous note, 268 tests
01:08 60bfc612273208f463f537d2797d344c71576caa status: 3.2 DONE ea2f5ae 2026-09-03 01:08 Stephen
01:11 26e6974cc0793574ce2243fbf79c62241df1a7c8 status: 3.7 DONE 2026-09-03 01:11 Stephen, live loop and rollback verified
01:16 c99762b5713980018a36037ba5c4af6fe17c640c docs(readme): quick start matches what exists
10:31 d905e0cbc9190b9302f7172b3701cf409c53490b status: 0.3 WIP 2026-09-03 10:31 Stephen, Confluent account created, cluster waits on a payment method
10:40 0d596b3396429c665efcec3be67d7e599cd2fa8a feat(streaming): Confluent leg behind the in-process bus, 275 tests
10:40 d4224bea6ff8c86fd8782b6c18da9d9b39a43f95 status: 4.1 WIP 0d596b3 2026-09-03 10:40 Stephen
10:47 fd9de905f7e026b9fa4354301d7d266b8d66abd0 chore(deps): google-adk eval extra as a dev dependency
10:49 b0527cf832af30b0f618b46c100dc4390b98c6be fix(status): the streaming transport and its counters are live, the headline stays cached, 276 tests
10:49 48e23ab151bf5ae2a6d73a2870e001442c2f7920 status: 0.3 DONE, 4.1 DONE 2026-09-03 10:49 Stephen, Confluent live with a 0.7 s round trip
10:56 60337ebda9aaaec52e4b7b4b3958d1cba93aa985 fix(agent): a per-request tool budget ends refusal loops; malformed base64 answers 422; parse errors name fields only, 285 tests
10:56 ed3e869ff91e42ee5ca763828e41794ad9c64393 fix(quotes): a number ends where it ends, 285 tests
10:56 3c74b6b88d0cef18f6bafebb719ec11f388f2435 fix(status): live means extraction can run; claims need a configured extraction, 285 tests
10:56 782145c6e3c73c2c036d0e998e21927c0139f682 CONTRACT: ExtractResult status matches its payload, 285 tests
10:56 cc0dffc3c1b73f14705e41a2595c53f0c146c950 fix(facts): FACTS keeps the matched count, not the residual run SHA
10:56 0d0ccf35712d92e5ed90e6595d699a2f6e5f83f3 fix(sim): the simulation fails on a failed, undetermined or illegal solve
10:56 f361140a86f70090fdb10c4390971f22114fe67e docs(threat-model): the extraction row reflects the shipped controls
10:56 a8b0c2e7dcd7fc3ad6c00ef66e5af8fe3ddad90f status: 5.3 round four folded 2026-09-03 10:56 Stephen
10:57 ea5d0e260826ee553d4ca0f3ec46c4253a9c4b2b chore: ignore the .adk directory the eval writes beside the agent
11:07 91d2bf9ce9e2326e10c6ac29b89422e2b9c10c27 feat(eval): record the adk eval summary into docs/adk_eval.json and FACTS, 288 tests
11:11 6d16339eeb04513b79491be08cbc0b7a1da785c3 fix(status): the runtime note no longer says the extract and set-event routes are pending
11:11 0a7d244ec23126b95cd5c203acb023dbed76cbe1 docs(screenshots): live Swagger page captured from the deployed URL, 2026-09-03
11:13 f101736ece9e62270e402574878666679e14b5f6 fix(config): .env.example matches what the code reads, held by a parity test, 292 tests
11:14 e659c5845da22447ec9853cbecb777b4930e9e78 docs(screenshots): live /api/status captured after the note fix deployed, 2026-09-03
11:17 914bd630681845eb1b0d382103dc9ca6f228e894 feat(simulation): --transport confluent produces set events on the topic and reads verdicts back, 293 tests
11:20 f560ec47a20c4643011484013e61f130e68481f7 status: 4.2 DONE 914bd63, 5.1 WIP, 3.7 screenshot note 2026-09-03 11:26 Stephen
12:03 5732e5c0b448d7a1047e1330a7e2f81455d1e96e fix(agent): the tool-bearing agent answers free-form; the schema stays on the extraction twin
12:10 b1de22ee78f7bf157623793d65130b35f3c89e7c feat(eval): 3.4 recorded from a real run, 4 of 4 cases passed, score in FACTS, 295 tests
12:10 d535aae8ae1f8a73b433ce61a6cabfb8a5c0c74c status: 3.4 DONE b1de22e 2026-09-03 12:12 Stephen
```
