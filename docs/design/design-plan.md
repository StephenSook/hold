# HOLD design plan

First pass, written before any component. Reviewed against the brief in the section at the end.

## Subject, audience, job

The artifact at the centre of this product is the **production strip board**: cardboard strips,
one per scene, slotted into a board, reordered by hand by a first assistant director. The stakes
are money (a performer paid to wait between their scenes) and law (a minor's hour caps).

Audience: an AD who has used Movie Magic for fifteen years, and a judge who has five minutes.

The job of the interface: make a stranger believe, in one screen, that the board reorders itself
to a proven cheapest order, and that a red day names the law it breaks with the sentence on
screen.

## Principle: colour is data

Every saturated colour in this interface means something in the domain. Nothing is coloured for
decoration.

The four strip colours are industry standard: white INT/DAY, yellow EXT/DAY, blue INT/NIGHT,
green EXT/NIGHT. Those four, plus three verdict states, consume the useful hue circle. So the
chrome gets **no brand accent hue at all**. The interface is graphite and bone. The only red on
a page is a broken law. The only other colour is a strip.

That also settles the accessibility requirement in the same stroke: strips carry black text, as
the physical strips do, and every status is colour plus word plus icon.

## Tokens

Base, dark (the board):

| Token | OKLCH | Role |
|---|---|---|
| `board` | `oklch(0.18 0.004 120)` | page, the aluminium board |
| `board-2` | `oklch(0.23 0.004 120)` | raised surface, the channel rails |
| `rail` | `oklch(0.31 0.004 120)` | hairlines and dividers |
| `bone` | `oklch(0.96 0.008 85)` | primary text, call-sheet stock |
| `bone-dim` | `oklch(0.72 0.006 85)` | secondary text |

Light mode is the other physical artifact: the call sheet. Bone paper, graphite ink, the same
strips, the same red.

Strips are printed cardstock, not screen neon:

| Token | OKLCH | Means |
|---|---|---|
| `strip-white` | `oklch(0.93 0.010 85)` | INT DAY |
| `strip-yellow` | `oklch(0.88 0.115 95)` | EXT DAY |
| `strip-blue` | `oklch(0.78 0.075 245)` | INT NIGHT |
| `strip-green` | `oklch(0.84 0.090 150)` | EXT NIGHT |

Verdict:

- **LEGAL** carries no colour. A hairline rule and a checked box. Legality is the default state;
  only failure is news, which is how a call sheet reads. Green is already EXT NIGHT and cannot
  mean legal.
- **ILLEGAL** `oklch(0.62 0.20 25)`, a 4 px left bar plus a filled slug, the word ILLEGAL and a
  slashed-circle icon.
- **UNDETERMINED** carries no colour either: a diagonal hatch in `rail`, the word, a diamond
  icon. Undetermined is the absence of proof, so it looks like an unfilled form, not a warning.

## Type

Two families, sharply distinct, both open licence, both self-hosted.

1. Display and UI: a **wide grotesque**, set at a signage width no default reaches for.
2. Data and statute: a **mono**. Screenplays, call sheets and timecode are monospaced; page
   eighths, scene numbers, cast letters, times and cents are all tabular.

Rejected: Fira Code with Fira Sans (the recommender's answer, and the generic dashboard
default), Inter, Geist Sans, Space Grotesk.

Scale runs on a 1 px spacing scale so pixel values are typed directly: `text-11` through
`text-140`.

## Layout

The board is horizontal strips, so the page's rhythm is **horizontal bands, not cards**. No
rounded SaaS cards anywhere. Radius 2 px at most and usually 0, because cardstock and paper have
square corners. Elevation is a 1 px hard offset, never a soft grey blur.

Everything is left aligned and hard against a rail. Centred text appears only on day-break slugs,
because physical day-break strips are centred.

## The one orchestrated moment

**The reorder.** On first paint the board holds the hand-built order: four hold days, one red
day. Once, unprompted, the solved order arrives and the strips fly to their positions in about a
second while the two dollar totals count down and the red day goes quiet. That is the product.

Everything else moves only in answer to a click, a drag or a hover.

The second beat is the load-in: four panels forming a **camera gate**, held closed while the
fonts and the demo fixture load, then opening as an aperture while the mark assembles from four
quarter marks. The centre holds the figure the site is about to prove, counting to `8/8`.

## Structural devices

- Numbered markers appear only on the `/judge` itinerary, which genuinely is a sequence.
- No tracked-out all-caps eyebrow above every heading. Section headers are set as **sluglines**
  (`EXT. PEACH ORCHARD - DAY`), which is the domain's own device and carries meaning.

## Review against the brief

Checked for the defaults that appear regardless of subject:

- Cream ground with a terracotta accent: rejected. It is the reference site's palette and it is
  the commonest generated-page tell. Ours is graphite and bone with no brand hue at all.
- Rounded cards with a soft grey shadow: rejected, on the physical grounds above.
- Gradient washes: none.
- All-caps tracked eyebrows: replaced by sluglines.
- An arrow appended to button text: no.
- A monospace face for small data labels is on the tell list, and is kept here, because the
  domain's own documents are monospaced and the numbers are tabular. It is a choice, not a
  default.
