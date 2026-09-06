# Fresh-clone dry run

Task 5.9. The README followed exactly on a clean machine, by someone with no access to the
working copy the project was built in. That last part is the point: a working copy that has built
the project passes checks a stranger's will not, and the whole task is to find out whether a
stranger can run this.

**Run on 2026-09-06 against commit `5863855`**, cloned fresh from GitHub into a temp directory.
Total wall clock for the walkthrough: about 13 minutes, of which roughly 4.5 is machine time.

## Result

**Every printed command works.** 24 commands across the README, JUDGE.md and PLAN.md's
"Verification, by a stranger". All exit 0. The one non-zero is
`simulate_set_day.py --transport confluent`, which exits 2 with a message naming the three
environment variables it needs, which is exactly what the README says will happen without them.

Reproduced on the clean clone:

| Claim | What the clone got |
|---|---|
| Benchmark residual | 9 passed, 8/8 matched |
| `facts.py --check` | `FACTS check: clean` |
| Hermetic suite | 381 passed, 11 skipped, 6 deselected |
| Quote verification | 16 passed |
| Web suite and build | 31 tests passed, build clean |
| A live solve | OPTIMAL, zero hold days, zero illegal days |
| `/api/rules` | 70 records, 70 verified, 1 assumed parameter |
| Residual suite duration | 58.9 seconds, against the stated "about a minute" |

All 12 relative links resolve to tracked files, all 11 backticked paths exist, and all 6 external
URLs answer 200 with the right content type.

## What it found, and what was done

Four findings. Three are fixed in the same batch as this file; the fourth is recorded.

1. **The quick start could not be pasted as a block.** `uvicorn` runs in the foreground and does
   not return, so every line after it never ran. Proven rather than reasoned: the two lines were
   run as a script and the marker after the simulation line never appeared. It is two blocks and
   two terminals now, and the README says so.

2. **The residual badge did not measure the residual.** The README pointed at
   `ci.yml/badge.svg?job=residual`. GitHub's badge endpoint has no `job` parameter: the response
   is byte-identical to the plain workflow badge and its title reads `CI - passing`, so a red
   residual under a green CI would still have shown green. Verified by fetching both and
   comparing bytes. The badge is labelled CI now, because that is what it measures.

3. **Eleven tests skipped with no explanation.** They check what the server serves out of the web
   build, Node was not in the prerequisites, and the README never said to build the web app. Both
   are stated now.

4. **The first proof command rewrites `bench/results.json`**, with the run's own SHA and eight
   timings. Every substantive field is byte-identical, so the optima do not move. Recorded in the
   README with the one command that puts it back.

Also noted and now true: the README promised an architecture diagram that did not exist, and
task 5.6 has since shipped it.

## One thing a judge should know

Every unmatched path on the live host answers **HTTP 200 with the web app**, because that is how
a single-page app is served. A status code alone therefore proves nothing about whether a route
exists. JUDGE.md says so now, since it invites route poking.

## How to repeat this

```bash
git clone https://github.com/StephenSook/hold /tmp/hold-check && cd /tmp/hold-check
```

then follow README.md exactly, executing every printed command in order and recording the exit
code of each. The value is in following it exactly: a step you improve while running it is a step
the next stranger will still trip over.
