/**
 * Burn the HTML-style labels (labels.json from diagram.py) into a diagram PNG, for reviews,
 * docs and places without HTML:
 *   bun scripts/icons/blender/overlay.ts <diagram dir> <mode> <out.png> [--tile [px]]
 * --tile draws the gallery-tile layout (tx/ty, short texts, leader lines, label font = tileFont
 * × width), which is what a ~210–330 px tile shows, here at full resolution; with a width in px
 * the result is also scaled down to that size.
 */
import sharp from "sharp"
const args = process.argv.slice(2)
const [dir, mode, out] = args
const ti = args.indexOf("--tile")
const tile = ti >= 0
const tilePx = tile ? Number(args[ti + 1]) || 0 : 0
const img = sharp(`${dir}/${mode}.png`)
const { width = 0, height = 0 } = await img.metadata()
type Label = {
  text: string
  kind: string
  x: number
  y: number
  tx?: number
  ty?: number
  short?: string
  tile?: boolean
  lead?: [number, number]
  flead?: [number, number]
}
const spec = JSON.parse(await Bun.file(`${dir}/labels.json`).text())
const labels: Label[] = spec.labels
const fs = Math.round(width * (tile ? (spec.tileFont ?? 0.04) : (spec.fullFont ?? 1 / 70)))
const esc = (t: string) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;")
const dark = mode === "dark"
const shown = labels.filter((l) => !tile || (l.tile !== false && l.tx !== undefined))
const pos = (l: Label) => (tile ? [l.tx! * width, l.ty! * height] : [l.x * width, l.y * height])
const from = (l: Label) => (tile ? l.lead : l.flead)
const ink2 = dark ? "#f6f0e6" : "#13223a"
const leads = shown
  .filter((l) => from(l))
  .map((l) => {
    const [x, y] = pos(l)
    const f = from(l)!
    return `<line x1="${f[0] * width}" y1="${f[1] * height}" x2="${x}" y2="${y}" stroke="${ink2}" stroke-opacity=".55" stroke-width="${Math.max(2, fs / 9)}" stroke-linecap="round"/><circle cx="${f[0] * width}" cy="${f[1] * height}" r="${Math.max(3, fs / 6)}" fill="${ink2}" fill-opacity=".7"/>`
  })
  .join("")
const pills = shown
  .map((l) => {
    const text = tile && l.short ? l.short : l.text
    const w = text.length * fs * 0.6 + fs * 1.2
    const [x, y] = pos(l)
    const ink = l.kind === "edge" ? "#c0392b" : "#13223a"
    return `<rect x="${x - w / 2}" y="${y - fs * 0.8}" width="${w}" height="${fs * 1.6}" rx="${fs * 0.8}" fill="#ffffff" fill-opacity=".92" stroke="#e6e0d6"/><text x="${x}" y="${y + fs * 0.35}" font-family="DejaVu Sans" font-weight="bold" font-size="${fs}" fill="${ink}" text-anchor="middle">${esc(text)}</text>`
  })
  .join("")
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">${leads}${pills}</svg>`
let pipe = img.composite([{ input: Buffer.from(svg) }])
if (tilePx) pipe = sharp(await pipe.png().toBuffer()).resize(tilePx)
await pipe.png().toFile(out)
