/**
 * The vocabulary of a stripboard, in the forms an assistant director expects to read.
 * Page counts are eighths. Money is cents. Times are 24 hour. Nothing here rounds silently.
 */
import type { DayNight, IntExt } from '@/types/contracts'

/**
 * Page counts, written the way every scheduling product writes them.
 *
 * Two conventions, both observed in Movie Magic, StudioBinder, Gorilla and Celtx output:
 * eighths are never reduced ("4/8", not "1/2"), and a whole number of pages carries an
 * explicit zero-eighths ("4 0/8", not "4"). A page is eight eighths because the standard
 * script page was measured with a ruler in inches.
 *
 * 20 becomes "2 4/8". 8 becomes "1 0/8". 3 becomes "3/8". 0 becomes "0".
 */
export function eighths(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '0'
  const whole = Math.floor(value / 8)
  const part = value % 8
  if (whole === 0) return `${part}/8`
  return `${whole} ${part}/8`
}

/** 406992 becomes "$4,069.92". Cents are never dropped: a hold day is paid to the cent. */
export function dollars(cents: number, withCents = true): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: withCents ? 2 : 0,
    maximumFractionDigits: withCents ? 2 : 0,
  }).format(cents / 100)
}

/** "07:00:00" becomes "07:00". An already short time is returned unchanged. */
export function hhmm(time: string): string {
  const match = /^(\d{2}):(\d{2})/.exec(time)
  return match ? `${match[1]}:${match[2]}` : time
}

/** "2026-10-01" becomes "Thu 1 Oct". Parsed as a local date, never shifted by a timezone. */
export function shootDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!match) return iso
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  return new Intl.DateTimeFormat('en-US', { weekday: 'short', day: 'numeric', month: 'short' }).format(date)
}

/** The industry strip colour code. White INT day, yellow EXT day, blue INT night, green EXT night. */
export type StripColour = 'white' | 'yellow' | 'blue' | 'green'

export function stripColour(intExt: IntExt, dayNight: DayNight): StripColour {
  if (intExt === 'INT') return dayNight === 'DAY' ? 'white' : 'blue'
  return dayNight === 'DAY' ? 'yellow' : 'green'
}

/** The slugline a scene would carry at the head of a script page. */
export function slugline(intExt: IntExt, set: string, dayNight: DayNight): string {
  return `${intExt}. ${set.toUpperCase()} - ${dayNight}`
}

/**
 * A minor's cast chip. The call sheet convention is the cast number with a "K" beside it for a
 * minor (John Wells Productions, "How to read a call sheet"). Our demo cast carry letters
 * rather than numbers because the data is constructed and nobody is named.
 */
export function castChip(letter: string, age: number | null): string {
  return age === null ? letter : `${letter}K`
}

/** True when child performer rules apply to this cast member. */
export function isMinor(age: number | null): boolean {
  return age !== null
}

/** Frames at 24 fps, for the running counter in the header. Film runs at 24, so this does too. */
export function timecode(elapsedMs: number, fps = 24): string {
  const totalFrames = Math.floor((elapsedMs / 1000) * fps)
  const frames = totalFrames % fps
  const totalSeconds = Math.floor(totalFrames / fps)
  const seconds = totalSeconds % 60
  const minutes = Math.floor(totalSeconds / 60) % 60
  const hours = Math.floor(totalSeconds / 3600) % 24
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}:${pad(frames)}`
}
