/**
 * The colour code, printed.
 *
 * Three of the four shipping scheduling products render white, yellow, blue, green for INT day,
 * EXT day, INT night, EXT night. One vendor has published the night pair reversed in its own
 * teaching material, so the legend is on screen rather than assumed: an assistant director who
 * trained on the other mapping can read ours in a second.
 */
const ENTRIES = [
  { swatch: 'bg-strip-white', label: 'INT DAY' },
  { swatch: 'bg-strip-yellow', label: 'EXT DAY' },
  { swatch: 'bg-strip-blue', label: 'INT NIGHT' },
  { swatch: 'bg-strip-green', label: 'EXT NIGHT' },
]

export function StripLegend() {
  return (
    <ul className="script flex flex-wrap items-center gap-x-5 gap-y-2 text-10 text-bone-dim">
      {ENTRIES.map((entry) => (
        <li key={entry.label} className="flex items-center gap-2">
          <span aria-hidden="true" className={`h-3 w-5 ${entry.swatch}`} />
          {entry.label}
        </li>
      ))}
    </ul>
  )
}
