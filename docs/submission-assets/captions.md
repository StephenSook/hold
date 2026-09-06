# Gallery captions

Task 6.4. Every image is a real screen capture of the running product at the deployed URL, taken
by `web/scripts/capture_gallery.mjs`. Nothing here is a mockup, a render, or generated art.

Every number in a caption comes from `docs/FACTS.json`, which a real run writes and continuous
integration recomputes. This file lives under `docs/` for a reason: the numeral guard in
`api/tests/test_facts.py` scans `docs/**/*.md`, so a caption that drifts from the engine turns
the build red. Captions pasted into the submission are pasted from here, never typed there.

The thumbnail is `01-before-after.png`.

---

## 01-before-after.png

**Four performers were paid to wait. Now none are.** The hand-built order holds four hold days
and one day that cannot legally be shot. The solver returns the provably cheapest order: zero
hold days, zero illegal days, and $4,069.92 of payroll removed at the published SAG-AFTRA low
budget day rate.

## 02-stripboard.png

**A real stripboard, with the industry colour code.** White interior day, yellow exterior day,
blue interior night, green exterior night, and a black slug at every day break carrying the
date, the page count in eighths, and the day's verdict. Drag a strip past a day break and it
belongs to that day, exactly as on a physical board. The strip is one continuous slat with no
internal cell borders, which is the thing every scheduling product on the market draws as a
spreadsheet row.

## 03-illegal-day.png

**An illegal day names every rule it breaks.** Seven rules across three jurisdictions, each with
its citation, the limit it sets, the value we computed, and how far over it is. CORE marks the
rules the solver proved make the day impossible on their own.

## 04-statute.png

**The sentence from the statute, not our summary of it.** Open any rule and the verbatim quote
is there with a link to the source. Every quote in the registry is verified in continuous
integration as a byte-for-byte substring of a committed snapshot of its source. A record whose
quote cannot be verified is excluded rather than paraphrased.

## 05-day-view.png

**The day, on the phone that is actually on set.** The verdict comes first, because on set the
only question is whether the day is legal. Primary targets in the thumb zone are 64 px and up,
every status carries a word and an icon as well as a colour, and the text is AAA at 7:1 or
better against its own background.

## 06-judge.png

**Six things a stranger can check, and the contrast measured rather than claimed.** Every figure
on the page is read from the live service. The verdict is a legal claim, so it is held to AAA
rather than AA, and the ratios are read from the painted pixels rather than computed by hand.
axe-core reports zero violations of any impact across all five routes.

## 07-architecture.png

**Every component here is one the service reports about itself.** The solver, the independent
checker, the rules registry and the job store run in the same process on one Cloud Run instance
that also serves the app. Vertex AI and Confluent Cloud are the only two things outside it.
Nothing on the diagram is planned or partial.
