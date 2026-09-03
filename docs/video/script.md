# HOLD demo video, script

Target: under three minutes, 1080p60, English narration. Every spoken number below is read from
`docs/FACTS.json` at recording time and re-read before the cut (`uv run python scripts/facts.py --check`
must be clean). No fictional person appears; the two of us and a constructed, labeled schedule are
the only subjects. Beats marked **[web]** need the web app and are recorded when it lands; beats
marked **[api]** can be captured now against the live URL.

| Step | Time | Beat | Capture |
|---|---|---|---|
| 01 Hook | 0:00 to 0:20 | A shooting schedule is a math problem nobody on a low-budget set gets to solve. Show the hand-built plan for the constructed demo: its hold days and its one illegal day, from FACTS. | **[web]** the before board; fallback **[api]** the before file in a terminal |
| 02 Problem | 0:20 to 0:45 | Every day a performer sits between scenes is paid. Every day a child is on set has an hour cap, a curfew, a turnaround and a meal rule from a different authority. The assistant director finds out after the day is paid for. | **[web]** the verdict card with the statute sentence |
| 03 Solution | 0:45 to 1:00 | HOLD solves the order and checks every day, and proves the order is the cheapest one. One sentence, no stack. | **[web]** the solved board |
| 04 Demo | 1:00 to 2:10 | Live on the deployed instance: the solve runs, hold days go from the before figure to the after figure (FACTS), the illegal day clears, the verdict names the rule and quotes the statute. Then a set event: an actor late, the plan re-solves in front of the viewer, the verdict updates. Pause on the quote. | **[web]** solve and set event; **[api]** `/api/status`, Swagger, `scripts/simulate_set_day.py` against the live URL in a terminal |
| 05 Impact | 2:10 to 2:35 | The payroll removed on the demo (FACTS), stated as constructed and labeled. The residual: the published benchmark optima matched on every instance, re-run on every push with no key. | **[api]** the CI residual job and the README badge |
| 06 Team and tech | 2:35 to 2:50 | Two of us. Gemini on Vertex AI through the Google Agent Development Kit for extraction, OR-Tools CP-SAT, Cloud Run, Confluent Cloud for the set events, IBM Bob for Phases 0 to 2 with the evidence committed. | **[api]** `/api/status` runtime block, `docs/bob-evidence/` |
| 07 Close | 2:50 to 3:00 | The line: the law is checked before the day is shot, not after it is paid for. Repo and live URL on screen. | title card |

## Rules for the cut

- Narrate outcomes, not clicks. "The illegal day clears" beats "click here".
- One visceral moment: the verdict quoting the statute sentence, held for two seconds.
- Nothing in the video may claim a practitioner used HOLD unless one has and said so.
- Measure the shipped file before it is final: integrated loudness between -16 and -14 LUFS,
  duration under 3:00, 1080p, the frame rate the capture used. Record the measurements in
  `docs/video/measurements.md` (task 6.1).
- Raw captures live under `docs/video/raw/` and never enter the repository.
