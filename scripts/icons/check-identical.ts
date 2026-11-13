/**
 * Refactor guard: prove a change did not change the icons.
 *
 *   bun scripts/icons/check-identical.ts dump <dir>
 *     writes every flat SVG string (svgFor light/dark, svgThemeable, stampSvg) to <dir>/<kind>/<name>.svg
 *   bun scripts/icons/check-identical.ts svg <before dir> <after dir>
 *     every dumped SVG must be byte-identical (exit 1 otherwise)
 *   bun scripts/icons/check-identical.ts png <before dir> <after dir> [--max-mean 1.0]
 *     per-icon mean absolute difference (0–255, over RGBA), the largest channel difference and the
 *     number of differing pixels of the PNGs under <dir>/{light,dark}; prints the worst first, exits 1
 *     when a mean is above --max-mean (Cycles noise between two renders stays well below 1.0; a real
 *     shift does not).
 *
 * (just icons-check-dump / icons-check-svg / icons-check-png)
 */
import { mkdir, readdir } from "node:fs/promises"
import sharp from "sharp"
import { FLAT, stampSvg, svgFor, svgThemeable } from "./flat"

const [cmd, a, b] = process.argv.slice(2)
const flag = (k: string, d: number) => {
  const i = process.argv.indexOf(`--${k}`)
  return i > 0 ? Number(process.argv[i + 1]) : d
}

const KINDS: Record<string, (n: string) => string> = {
  light: (n) => svgFor(n, "light"),
  dark: (n) => svgFor(n, "dark"),
  themeable: svgThemeable,
  mono: (n) => stampSvg(n),
  badge: (n) => stampSvg(n, true),
}

async function dump(dir: string) {
  for (const [kind, fn] of Object.entries(KINDS)) {
    await mkdir(`${dir}/${kind}`, { recursive: true })
    for (const n of Object.keys(FLAT)) await Bun.write(`${dir}/${kind}/${n}.svg`, fn(n))
  }
  console.log(`dump ${Object.keys(FLAT).length} icons × ${Object.keys(KINDS).length} kinds → ${dir}`)
}

async function files(dir: string, ext: string) {
  const out: string[] = []
  for (const sub of await readdir(dir).catch(() => [] as string[]))
    for (const f of await readdir(`${dir}/${sub}`).catch(() => [] as string[]))
      if (f.endsWith(ext) && !f.endsWith(`.raw${ext}`)) out.push(`${sub}/${f}`)
  return out.sort()
}

async function svg(before: string, after: string) {
  const want = await files(before, ".svg")
  const have = new Set(await files(after, ".svg"))
  let bad = 0
  for (const f of want) {
    if (!have.has(f)) {
      console.log(`MISSING ${f}`)
      bad++
      continue
    }
    const [x, y] = await Promise.all([Bun.file(`${before}/${f}`).text(), Bun.file(`${after}/${f}`).text()])
    if (x !== y) {
      console.log(`DIFFERS ${f}`)
      bad++
    }
  }
  for (const f of have) if (!want.includes(f)) console.log(`NEW     ${f}`)
  console.log(bad ? `SVG: ${bad} of ${want.length} differ` : `SVG: ${want.length} byte-identical`)
  return bad
}

async function png(before: string, after: string) {
  const maxMean = flag("max-mean", 1.0)
  const rows: { f: string; mean: number; max: number; px: number }[] = []
  let bad = 0
  for (const f of await files(before, ".png")) {
    const p = `${after}/${f}`
    if (!(await Bun.file(p).exists())) {
      console.log(`MISSING ${f}`)
      bad++
      continue
    }
    const [x, y] = await Promise.all(
      [`${before}/${f}`, p].map((q) => sharp(q).ensureAlpha().raw().toBuffer({ resolveWithObject: true })),
    )
    if (x.info.width !== y.info.width || x.info.height !== y.info.height) {
      console.log(`SIZE    ${f}: ${x.info.width}x${x.info.height} vs ${y.info.width}x${y.info.height}`)
      bad++
      continue
    }
    let sum = 0
    let max = 0
    let px = 0 // pixels with any channel different
    for (let i = 0; i < x.data.length; i += 4) {
      let pixel = 0
      for (let c = 0; c < 4; c++) {
        const d = Math.abs(x.data[i + c] - y.data[i + c])
        sum += d
        if (d > pixel) pixel = d
      }
      if (pixel) px++
      if (pixel > max) max = pixel
    }
    rows.push({ f, mean: sum / x.data.length, max, px })
  }
  rows.sort((p, q) => q.mean - p.mean)
  for (const r of rows) {
    const over = r.mean > maxMean
    if (over) bad++
    console.log(`${over ? "FAIL" : "ok  "} ${r.f.padEnd(34)} mean=${r.mean.toFixed(4)} max=${r.max} pixels=${r.px}`)
  }
  console.log(
    bad ? `PNG: ${bad} of ${rows.length} beyond noise (mean > ${maxMean})` : `PNG: ${rows.length} within noise`,
  )
  return bad
}

if (cmd === "dump" && a) await dump(a)
else if (cmd === "svg" && a && b) process.exit((await svg(a, b)) ? 1 : 0)
else if (cmd === "png" && a && b) process.exit((await png(a, b)) ? 1 : 0)
else {
  console.error("usage: check-identical.ts dump <dir> | svg <before> <after> | png <before> <after> [--max-mean 1.0]")
  process.exit(2)
}
