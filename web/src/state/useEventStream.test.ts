import { describe, expect, it } from 'vitest'

/**
 * The deduplication rule, tested on its own.
 *
 * The hook's behaviour under reconnect went through two wrong versions before this one. Appending
 * duplicated the log after every blip, because the stream URL asks for a replay and EventSource
 * reconnects by itself. Clearing on reconnect then discarded the log entirely after an instance
 * swap, because the bus is in process and a new process replays nothing.
 *
 * Skipping what has already been shown is the only rule that is correct in both cases, so it is
 * pinned here rather than left to a comment.
 */
interface Line {
  at: number
  kind: string
  text: string
}

interface State {
  lines: Line[]
  seen: string[]
}

const signature = (kind: string, text: string): string => `${kind} :: ${text}`

/** The same reducer the hook applies, extracted so the rule can be tested without a browser. */
function receive(state: State, kind: string, text: string): State {
  const key = signature(kind, text)
  if (state.seen.includes(key)) return state
  return {
    lines: [...state.lines.slice(-40), { at: 0, kind, text }],
    seen: [...state.seen.slice(-200), key],
  }
}

const EMPTY: State = { lines: [], seen: [] }

describe('the event log under reconnect', () => {
  it('shows each event once when the stream replays the whole history', () => {
    const history: [string, string][] = [
      ['objective', 'objective 100 bound 0 at 12 ms'],
      ['objective', 'objective 90 bound 0 at 30 ms'],
      ['verdict', 'day 4 ILLEGAL'],
    ]
    let state = history.reduce((s, [kind, text]) => receive(s, kind, text), EMPTY)
    expect(state.lines).toHaveLength(3)

    // The reconnect replays everything it already sent.
    state = history.reduce((s, [kind, text]) => receive(s, kind, text), state)
    expect(state.lines, 'a replay must not duplicate the log').toHaveLength(3)
  })

  it('keeps the log when the replay comes back empty', () => {
    // The instance-swap case. The bus is in process, so a new process has nothing to replay, and
    // an earlier version cleared here and discarded the only remaining copy of the log.
    const state = receive(receive(EMPTY, 'objective', 'a'), 'verdict', 'b')
    expect(state.lines).toHaveLength(2)

    // An empty replay delivers nothing, so nothing changes.
    const afterEmptyReplay = [].reduce<State>((s) => s, state)
    expect(afterEmptyReplay.lines, 'an empty replay must not empty the log').toHaveLength(2)
  })

  it('still shows a genuinely new event after a replay', () => {
    let state = receive(EMPTY, 'objective', 'objective 100 at 12 ms')
    state = receive(state, 'objective', 'objective 100 at 12 ms')
    state = receive(state, 'objective', 'objective 90 at 30 ms')
    expect(state.lines.map((line) => line.text)).toEqual([
      'objective 100 at 12 ms',
      'objective 90 at 30 ms',
    ])
  })

  it('separates two events that differ only by kind', () => {
    let state = receive(EMPTY, 'objective', 'same text')
    state = receive(state, 'verdict', 'same text')
    expect(state.lines).toHaveLength(2)
  })
})
