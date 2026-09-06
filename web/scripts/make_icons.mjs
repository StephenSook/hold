/**
 * The app mark, drawn once.
 *
 * Every icon this project ships comes from this file: the Android launcher icon, the iOS store
 * icon, and the three PWA icons the web manifest names. They diverged once already. The PWA set
 * was the camera gate while the installed app was the stripboard, so a phone with both showed two
 * different marks for one product, and nothing catches that because no test looks at a picture.
 *
 * The mark is four strips in the four industry colours on the board ground. At the size a launcher
 * icon is actually seen, roughly 60px, a thin monochrome outline disappears and four saturated
 * bars do not, and the bars say what the product is rather than what the industry is.
 *
 * Colours are the measured token values from src/styles/theme.css, written here as hex rather than
 * imported, because a CSS custom property in oklch has to go through a browser to become a pixel
 * and that is the variance this generator exists to remove.
 *
 * Geometry is integer and axis aligned, so the rasteriser has no edge to smooth and the output is
 * byte stable across runs and machines.
 *
 *   node scripts/make_icons.mjs            write the files
 *   node scripts/make_icons.mjs --check    fail if a committed file differs from what this draws
 *
 * The files under android/ and ios/ are derived from assets/ by @capacitor/assets, not by this
 * script, and --check does not see them. After changing the mark, run `npm run icons:native` or
 * the launcher icon keeps the old drawing while everything CI looks at agrees with the new one.
 */
import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const WEB = join(dirname(fileURLToPath(import.meta.url)), '..')

const BOARD = '#101010'
/** INT DAY, EXT DAY, INT NIGHT, EXT NIGHT, in the order a board carries them. */
const STRIPS = ['#ebe7e1', '#efd77c', '#8fbde5', '#a0dcac']
const BONE = '#f4f1ec'

/**
 * Four centred bars.
 *
 * `inset` is the margin on the left and right, `bar` the height of one strip, `gap` the space
 * between two. The block is centred vertically, so the top margin follows from the other three
 * and is not a fourth thing to keep in sync.
 */
function strips(size, { inset, bar, gap, ground }) {
  // Geometry is a fraction of the canvas, not a pixel count, because the same mark is drawn at
  // 192, 512, 1024 and 2732. Reusing the 1024 numbers at 192 put every bar off the canvas and
  // produced three solid squares, which no assertion here would have caught: the sizes are
  // measured, and only measuring found it.
  const px = (f) => Math.round(f * size)
  const [i, b, g] = [px(inset), px(bar), px(gap)]
  const total = STRIPS.length * b + (STRIPS.length - 1) * g
  const top = Math.round((size - total) * 0.5)
  const rects = STRIPS.map(
    (fill, n) =>
      `<rect x="${i}" y="${top + n * (b + g)}" width="${size - i * 2}" height="${b}" fill="${fill}"/>`,
  ).join('')
  const base = ground ? `<rect width="${size}" height="${size}" fill="${ground}"/>` : ''
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${base}${rects}</svg>`
}

/** One bone bar on the board. The splash is a held frame, not a second logo. */
function splash(size) {
  const w = Math.round(size * 0.0732)
  const h = Math.round(size * 0.0161)
  const x = Math.round((size - w) * 0.5)
  const y = Math.round((size - h) * 0.5)
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><rect width="${size}" height="${size}" fill="${BOARD}"/><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${BONE}"/></svg>`
}

/**
 * The full mark, as fractions of the canvas, used where the icon keeps its own corners: the iOS store icon, which Apple masks
 * itself, and the PWA `any` icons.
 */
const FULL = { inset: 150 / 1024, bar: 132 / 1024, gap: 62 / 1024, ground: BOARD }
/**
 * The same mark pulled in to survive a mask. Android's adaptive icon keeps only the middle, and a
 * maskable PWA icon promises the inner circle is enough, so the bars sit well inside both.
 */
const SAFE = { inset: 288 / 1024, bar: 92 / 1024, gap: 44 / 1024, ground: BOARD }

const OUTPUTS = [
  // What @capacitor/assets reads to fill android/ and ios/.
  { file: 'assets/icon-only.png', size: 1024, svg: (s) => strips(s, FULL), alpha: false },
  { file: 'assets/icon-background.png', size: 1024, alpha: false,
    svg: (s) => `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}"><rect width="${s}" height="${s}" fill="${BOARD}"/></svg>` },
  // The adaptive foreground layer is the one file that must keep its alpha: Android composites it
  // over the background layer and moves the two against each other.
  { file: 'assets/icon-foreground.png', size: 1024, svg: (s) => strips(s, { ...SAFE, ground: null }), alpha: true },
  { file: 'assets/splash.png', size: 2732, svg: splash, alpha: false },
  { file: 'assets/splash-dark.png', size: 2732, svg: splash, alpha: false },
  // What the web manifest names. vite-plugin-pwa owns the manifest; these are the files it points at.
  { file: 'public/icon-192.png', size: 192, svg: (s) => strips(s, FULL), alpha: false },
  { file: 'public/icon-512.png', size: 512, svg: (s) => strips(s, FULL), alpha: false },
  { file: 'public/icon-512-maskable.png', size: 512, svg: (s) => strips(s, SAFE), alpha: false },
]

/**
 * Draw at the target size rather than drawing once and downscaling. A resample would blur the
 * strip edges and, at 192px, mix two strip colours into a third that is not in the code.
 */
async function render({ size, svg, alpha }) {
  const pipeline = sharp(Buffer.from(svg(size)))
  // Apple rejects a store icon carrying an alpha channel, and it is the same source file as the
  // rest, so the flattening is per output rather than a property of the drawing.
  return (alpha ? pipeline : pipeline.flatten({ background: BOARD }).removeAlpha()).png({ compressionLevel: 9 }).toBuffer()
}

const digest = (buf) => createHash('sha256').update(buf).digest('hex').slice(0, 12)

const check = process.argv.includes('--check')
const drift = []

for (const out of OUTPUTS) {
  const drawn = await render(out)
  const path = join(WEB, out.file)
  const existing = await readFile(path).catch(() => null)
  const same = existing !== null && existing.equals(drawn)
  if (check) {
    if (!same) drift.push(`${out.file}  committed ${existing ? digest(existing) : 'missing'}  drawn ${digest(drawn)}`)
    continue
  }
  if (!same) await writeFile(path, drawn)
  console.log(`${same ? '  same' : ' wrote'}  ${out.file.padEnd(30)} ${out.size}px  ${digest(drawn)}`)
}

if (check && drift.length > 0) {
  console.error('icons differ from scripts/make_icons.mjs. Run it and commit the result.')
  for (const line of drift) console.error(`  ${line}`)
  process.exit(1)
}
if (check) console.log(`icons match scripts/make_icons.mjs (${OUTPUTS.length} files)`)
