/**
 * Blender icon gate — deterministic checks that encode past failures.
 *   bun scripts/icons/blender/gate.ts            (checks every local/icons/rounds/25d-b*)
 * 1. No clipped white: cream must never render as #FFFFFF (owner, 2026-11-11: CLI was 16.5% white).
 * 2. Both editions exist for every Blender icon (light/dark = palette swap of one model).
 * 3. Nothing touches the canvas edge (framing/cropping regressions).
 * 4. An icon (not a scene or doll line-up) is no thin strip: the short side of its opaque
 *    bounding box is >= 45% of the long side (W-140: the horizontal link was 859×299 next to a
 *    set of near-square icons; orient long objects diagonally instead). Checked on the box
 *    shape, not on coverage, because normalize.ts scales square icons down optically (56a17c1).
 * Thresholds come from the theme (theme/brand.json "gate").
 * Prints a table and exits 1 on any failure.
 */
import { readdir } from "node:fs/promises"
import sharp from "sharp"
import { THEME } from "../theme"

const { whiteLevel, whiteMaxPct, opaqueAlpha, edgePx, minAspect } = THEME.gate

const ROOT = "local/icons/rounds"
const rounds = (await readdir(ROOT)).filter((r) => r.startsWith("25d-b"))
let fail = 0
for (const r of rounds) {
  const names = new Set<string>()
  for (const m of ["light", "dark"])
    for (const f of await readdir(`${ROOT}/${r}/${m}`).catch(() => []))
      if (f.endsWith(".png") && !f.endsWith(".raw.png")) names.add(f)
  for (const f of names) {
    for (const m of ["light", "dark"]) {
      const p = `${ROOT}/${r}/${m}/${f}`
      if (!(await Bun.file(p).exists())) {
        console.log(`FAIL ${p}: missing edition`)
        fail++
        continue
      }
      const { data, info } = await sharp(p).raw().toBuffer({ resolveWithObject: true })
      let op = 0,
        white = 0,
        edge = 0,
        x0 = info.width,
        x1 = 0,
        y0 = info.height,
        y1 = 0
      for (let y = 0; y < info.height; y++)
        for (let x = 0; x < info.width; x++) {
          const i = (y * info.width + x) * info.channels
          if (data[i + 3] < opaqueAlpha) continue
          op++
          if (x < x0) x0 = x
          if (x > x1) x1 = x
          if (y < y0) y0 = y
          if (y > y1) y1 = y
          if (data[i] > whiteLevel && data[i + 1] > whiteLevel && data[i + 2] > whiteLevel) white++
          if (x < edgePx || y < edgePx || x > info.width - 1 - edgePx || y > info.height - 1 - edgePx) edge++
        }
      const w = (100 * white) / Math.max(op, 1)
      const fill = (100 * op) / (info.width * info.height)
      const aspect = Math.min(x1 - x0, y1 - y0) / Math.max(x1 - x0, y1 - y0, 1)
      const icon = !/^(scene-|doll)/.test(f) // scenes and doll line-ups are wide by design
      const bad = w > whiteMaxPct || edge > 0 || (icon && aspect < minAspect)
      if (bad) fail++
      console.log(
        `${bad ? "FAIL" : "ok  "} ${r}/${m}/${f} white=${w.toFixed(2)}% edge=${edge} fill=${fill.toFixed(0)}% aspect=${aspect.toFixed(2)}`,
      )
    }
  }
}
console.log(fail ? `GATE: ${fail} failure(s)` : "GATE: pass")
process.exit(fail ? 1 : 0)
