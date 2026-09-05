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

| Token | OKLCH | Role | Measured on the board |
|---|---|---|---|
| `board` | `oklch(0.175 0 0)` | page, the aluminium board | ground |
| `board-2` | `oklch(0.222 0 0)` | raised surface | |
| `board-3` | `oklch(0.262 0 0)` | day breaks and table headers | |
| `rail` | `oklch(0.315 0 0)` | decorative hairlines only | 1.46:1, never a control boundary |
| `edge` | `oklch(0.53 0 0)` | the boundary of a control | 3.15:1, over the non-text floor |
| `bone` | `oklch(0.96 0.008 85)` | primary text | **16.89:1** |
| `bone-dim` | `oklch(0.75 0.006 85)` | secondary text | **8.59:1** |
| `bone-faint` | `oklch(0.702 0.005 85)` | labels and sources | **7.19:1** |

The greys carry no chroma at all. A tinted chrome shifts the INT NIGHT strip, and that strip has
to read as itself.

Light mode is the other physical artifact: the call sheet. Bone paper, graphite ink, the same
strips, the same red.

Strips are printed cardstock, not screen neon:

| Token | OKLCH | Means | Ink on it, measured |
|---|---|---|---|
| `strip-white` | `oklch(0.93 0.010 85)` | INT DAY | 15.88:1 |
| `strip-yellow` | `oklch(0.88 0.115 95)` | EXT DAY | 13.68:1 |
| `strip-blue` | `oklch(0.78 0.075 245)` | INT NIGHT | 9.85:1 |
| `strip-green` | `oklch(0.84 0.090 150)` | EXT NIGHT | 12.41:1 |

Every figure above is read from the painted pixels by `web/scripts/measure_contrast.mjs`. An
earlier version of this document computed them by hand and every one was wrong, in the flattering
direction. See `axe-report.md`.

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
fonts load, then opening as an aperture while the mark assembles from four quarter marks. The
centre holds the figure the site is about to prove, counting to `8/8`. It is capped at about 1.6
seconds and skipped on a repeat view and under reduced motion, because a hero held at zero
opacity behind an overlay is excluded from the largest-contentful-paint candidates and the
overlay's duration is then added to the metric.

**Text hierarchy never comes from opacity.** Opacity multiplies the effective contrast down, so a
dimmed label is a colour no token table describes and no audit of tokens will catch. It is used
only on things that are not text.

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
- **Film grain was planned and then cut.** This document originally called it "the only
  decorative layer in the interface". A noise overlay hurts exactly the small type that carries a
  data table, and no professional post or camera tool ships grain in its own chrome. The board's
  milled vertical channel is the texture instead, which is a reference to the physical artifact
  rather than to films about films.
