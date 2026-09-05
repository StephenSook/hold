import { describe, expect, it } from 'vitest'
import { castChip, dollars, eighths, hhmm, isMinor, shootDate, slugline, stripColour, timecode } from './format'

describe('eighths', () => {
  it('never reduces the fraction', () => {
    expect(eighths(4)).toBe('4/8')
    expect(eighths(2)).toBe('2/8')
    expect(eighths(6)).toBe('6/8')
  })

  it('writes a whole page with an explicit zero-eighths', () => {
    expect(eighths(8)).toBe('1 0/8')
    expect(eighths(32)).toBe('4 0/8')
  })

  it('writes a mixed number with a space', () => {
    expect(eighths(20)).toBe('2 4/8')
    expect(eighths(14)).toBe('1 6/8')
  })

  it('answers zero for nothing and for nonsense', () => {
    expect(eighths(0)).toBe('0')
    expect(eighths(-3)).toBe('0')
    expect(eighths(Number.NaN)).toBe('0')
  })
})

describe('dollars', () => {
  it('keeps the cents, because a hold day is paid to the cent', () => {
    expect(dollars(406992)).toBe('$4,069.92')
    expect(dollars(83400)).toBe('$834.00')
  })

  it('drops them only when asked', () => {
    expect(dollars(406992, false)).toBe('$4,070')
  })
})

describe('stripColour', () => {
  it('follows the industry code', () => {
    expect(stripColour('INT', 'DAY')).toBe('white')
    expect(stripColour('EXT', 'DAY')).toBe('yellow')
    expect(stripColour('INT', 'NIGHT')).toBe('blue')
    expect(stripColour('EXT', 'NIGHT')).toBe('green')
  })
})

describe('cast chips', () => {
  it('marks a minor with K and leaves an adult alone', () => {
    expect(castChip('M', 14)).toBe('MK')
    expect(castChip('A', null)).toBe('A')
    expect(isMinor(14)).toBe(true)
    expect(isMinor(null)).toBe(false)
  })
})

describe('times and dates', () => {
  it('shortens a wall time and leaves a short one alone', () => {
    expect(hhmm('07:00:00')).toBe('07:00')
    expect(hhmm('19:30')).toBe('19:30')
  })

  it('reads a shoot date as a local date, never shifted by a timezone', () => {
    expect(shootDate('2026-10-01')).toBe('Thu, Oct 1')
  })

  it('counts frames at 24', () => {
    expect(timecode(0)).toBe('00:00:00:00')
    expect(timecode(1000)).toBe('00:00:01:00')
    expect(timecode(1000 / 24)).toBe('00:00:00:01')
    expect(timecode(3_661_000)).toBe('01:01:01:00')
  })
})

describe('slugline', () => {
  it('reads as a script slugline', () => {
    expect(slugline('EXT', 'Peach Orchard', 'DAY')).toBe('EXT. PEACH ORCHARD - DAY')
  })
})
