/**
 * The rule that unrolls.
 *
 * The clip enters from the left while the rule inside it enters from the right, at the same
 * rate. Because they counter-move, the rule appears to unroll in place rather than slide across,
 * which is a different and much better read than a left-to-right wipe. Put it inside a
 * `group/swap` alongside SwapText.
 */
export function Underline() {
  return (
    <span
      aria-hidden="true"
      className="absolute bottom-0 left-0 block h-px w-full overflow-hidden"
    >
      <span className="block h-px w-full -translate-x-[105%] bg-bone transition-transform duration-400 ease-in-out group-hover/swap:translate-x-0 group-focus-visible/swap:translate-x-0" />
    </span>
  )
}
