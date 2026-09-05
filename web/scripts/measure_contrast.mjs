import { chromium } from 'playwright'
const b = await chromium.launch({ headless: true, channel: 'chromium' })
const p = await (await b.newContext()).newPage()
await p.goto(process.env.BASE || 'http://127.0.0.1:4173/#/', { waitUntil: 'networkidle' })
await new Promise(r => setTimeout(r, 2500))

const out = await p.evaluate(() => {
  // getComputedStyle returns oklch() in this engine, so paint each token and read the pixel.
  const probe = document.createElement('div')
  probe.style.cssText = 'position:fixed;left:-9999px;width:8px;height:8px'
  document.body.appendChild(probe)
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 8
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  const rgbOf = (name) => {
    probe.style.background = `var(${name})`
    const painted = getComputedStyle(probe).backgroundColor
    ctx.clearRect(0, 0, 8, 8); ctx.fillStyle = painted; ctx.fillRect(0, 0, 8, 8)
    const d = ctx.getImageData(4, 4, 1, 1).data
    return [d[0], d[1], d[2]]
  }
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4) }
  const lum = ([r, g, bb]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(bb)
  const ratio = (a, c) => { const [x, y] = [lum(a), lum(c)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05) }
  const hex = ([r, g, bb]) => '#' + [r, g, bb].map(v => v.toString(16).padStart(2, '0')).join('')

  const pairs = [
    ['bone on board', '--color-bone', '--color-board', 'text'],
    ['bone-dim on board', '--color-bone-dim', '--color-board', 'text'],
    ['bone-faint on board', '--color-bone-faint', '--color-board', 'text'],
    ['bone-dim on board-3', '--color-bone-dim', '--color-board-3', 'text'],
    ['bone-faint on board-3', '--color-bone-faint', '--color-board-3', 'text'],
    ['ink on strip-white', '--color-ink', '--color-strip-white', 'text'],
    ['ink on strip-yellow', '--color-ink', '--color-strip-yellow', 'text'],
    ['ink on strip-blue', '--color-ink', '--color-strip-blue', 'text'],
    ['ink on strip-green', '--color-ink', '--color-strip-green', 'text'],
    ['bone on flag-deep', '--color-bone', '--color-flag-deep', 'text'],
    ['flag-deep on bone', '--color-flag-deep', '--color-bone', 'text'],
    ['flag on board', '--color-flag', '--color-board', 'graphic'],
    ['rail on board', '--color-rail', '--color-board', 'graphic'],
    ['bone ring on board', '--color-bone', '--color-board', 'graphic'],
  ]
  const rows = pairs.map(([label, f, g, kind]) => {
    const fg = rgbOf(f), bg = rgbOf(g)
    return { label, kind, fg: hex(fg), bg: hex(bg), ratio: Number(ratio(fg, bg).toFixed(2)) }
  })
  probe.remove()
  return rows
})
let bad = 0
for (const r of out) {
  const bar = r.kind === 'graphic'
    ? (r.ratio >= 3 ? 'ok (3:1 floor)' : 'FAILS 3:1')
    : r.ratio >= 7 ? 'AAA' : r.ratio >= 4.5 ? 'AA only' : 'FAILS AA'
  if (bar.startsWith('FAILS') || bar === 'AA only') bad++
  console.log(`${String(r.ratio).padStart(7)}:1  ${bar.padEnd(15)} ${r.label.padEnd(24)} ${r.fg} on ${r.bg}`)
}
console.log(`\npairs below AAA (text) or below 3:1 (graphic): ${bad}`)
await b.close()
