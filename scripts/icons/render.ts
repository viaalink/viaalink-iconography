/**
 * Render icons into a round directory, key out the chroma background and
 * build a contact sheet showing each icon on its real page colour.
 *
 *   bun scripts/icons/render.ts --out local/icons/rounds/25d-r1 --style 25d [--mode light|dark|both] [--probe | name ...]
 *
 * Output:
 *   <out>/<mode>/<name>.raw.png   model output (chroma background)
 *   <out>/<mode>/<name>.png       transparent, keyed
 *   <out>/sheet.png               all icons on paper (light) and navy (dark), with 256 px and 48 px samples
 *   <out>/prompts.json            exact prompts used (for reproducibility)
 */
import sharp from "sharp"
import { squareIcon } from "./canvas"
import { CONCEPTS, ICONS, type IconSubject, PROBE } from "./catalog"
import { DEFAULT_IMAGE_MODEL, fileToDataUrl, generateImage } from "./openrouter"
import { buildPrompt, type Mode, STYLE_VERSION, type Style } from "./style"
import { THEME } from "./theme"

const args = process.argv.slice(2)
const opt = (k: string, d: string) => {
  const i = args.indexOf(`--${k}`)
  return i >= 0 ? args.splice(i, 2)[1] : d
}
const out = opt("out", `local/icons/rounds/tmp-${Date.now()}`)
const style = opt("style", "25d") as Style
const modeArg = opt("mode", "both")
const anchorArg = opt("anchors", "")
/** Extra subject references (any PNG path), e.g. the flat link drawn by hand: `--refs a.png,b.png`. */
const refArg = opt("refs", "")
/** Owner feedback for this run (regeneration): appended to every subject. */
const feedback = opt("feedback", "")
const probe = args.includes("--probe")
const names = args.filter((a) => !a.startsWith("--"))

const modes: Mode[] = modeArg === "both" ? ["light", "dark"] : [modeArg as Mode]
const icons: IconSubject[] = probe
  ? PROBE
  : names.length
    ? [...ICONS, ...CONCEPTS].filter((i) => names.includes(i.name))
    : ICONS
if (!icons.length) throw new Error(`no icons matched: ${names.join(", ")}`)

const logo = await fileToDataUrl("static/assets/logo-mark.png")

/**
 * Style anchors: the best icons so far, attached as extra reference images so
 * new icons match their camera, material and palette. `--anchors 25d-r2:light/cli,25d-r1:dark/lock`
 * (raw renders, chroma background included). Only anchors of the mode being rendered are sent.
 */
const refs = await Promise.all(
  refArg
    .split(",")
    .filter(Boolean)
    .map((p) => fileToDataUrl(p)),
)
const anchors: Record<Mode, string[]> = { light: [], dark: [] }
for (const spec of anchorArg.split(",").filter(Boolean)) {
  const m = spec.match(/^([\w.-]+):(light|dark)\/([\w-]+)$/)
  if (!m) throw new Error(`bad anchor: ${spec}`)
  anchors[m[2] as Mode].push(await fileToDataUrl(`local/icons/rounds/${m[1]}/${m[2]}/${m[3]}.raw.png`))
}

/** Chroma-key #00FF00 to alpha with a soft edge and green despill. */
export async function keyChroma(input: Buffer): Promise<Buffer> {
  const { data, info } = await sharp(input).ensureAlpha().raw().toBuffer({ resolveWithObject: true })
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i],
      g = data[i + 1],
      b = data[i + 2]
    const spill = g - Math.max(r, b)
    if (spill > 20) {
      // 20..120 green excess fades from opaque to fully transparent
      const a = Math.max(0, Math.min(1, 1 - (spill - 20) / 100))
      data[i + 3] = Math.round(255 * a)
      data[i + 1] = Math.max(r, b) // despill the edge pixel
    }
  }
  return sharp(data, { raw: info }).png().toBuffer()
}

/**
 * Share of the outer 2% border that is chroma green, and share of the outermost
 * pixel ring that is not (= object cropped by the canvas edge).
 */
async function borderReport(input: Buffer): Promise<{ chroma: number; touching: number }> {
  const { data, info } = await sharp(input).removeAlpha().raw().toBuffer({ resolveWithObject: true })
  const { width: w, height: h } = info
  const band = Math.max(2, Math.round(w * 0.02))
  const green = (x: number, y: number) => {
    const i = (y * w + x) * 3
    return data[i + 1] - Math.max(data[i], data[i + 2]) > 80
  }
  let total = 0,
    hits = 0,
    ring = 0,
    ringMiss = 0
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const d = Math.min(x, y, w - 1 - x, h - 1 - y)
      if (d >= band) continue
      total++
      const g = green(x, y)
      if (g) hits++
      if (d === 0) {
        ring++
        if (!g) ringMiss++
      }
    }
  return { chroma: +(hits / total).toFixed(3), touching: +(ringMiss / ring).toFixed(3) }
}

async function renderOne(icon: IconSubject, mode: Mode) {
  const subject = feedback
    ? `${icon.subject} OWNER FEEDBACK on the previous version (attached as the last reference image): ${feedback}`
    : icon.subject
  const prompt = buildPrompt(subject, style, mode)
  const dir = `${out}/${mode}`
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const raw = await generateImage({ prompt, references: [logo, ...anchors[mode], ...refs] })
      await Bun.write(`${dir}/${icon.name}.raw.png`, raw)
      const border = await borderReport(raw)
      if (border.chroma < 0.97) throw new Error(`background not chroma (${border.chroma})`)
      if (border.touching > 0.01) throw new Error(`object touches the edge (${border.touching})`)
      await Bun.write(`${dir}/${icon.name}.png`, await squareIcon(await keyChroma(raw)))
      console.log(`ok   ${mode}/${icon.name}`)
      return { name: icon.name, mode, prompt }
    } catch (e) {
      console.log(`try ${attempt} ${mode}/${icon.name}: ${(e as Error).message.slice(0, 160)}`)
    }
  }
  console.log(`FAIL ${mode}/${icon.name}`)
  return { name: icon.name, mode, prompt, failed: true }
}

const jobs = modes.flatMap((m) => icons.map((i) => () => renderOne(i, m)))
const results: Awaited<ReturnType<typeof renderOne>>[] = []
const CONCURRENCY = 4
await Promise.all(
  Array.from({ length: CONCURRENCY }, async () => {
    for (let job = jobs.shift(); job; job = jobs.shift()) results.push(await job())
  }),
)
await Bun.write(
  `${out}/prompts.json`,
  JSON.stringify(
    {
      styleVersion: STYLE_VERSION,
      style,
      model: DEFAULT_IMAGE_MODEL,
      anchors: anchorArg,
      refs: refArg,
      feedback,
      results,
    },
    null,
    2,
  ),
)

// Contact sheet: one row per mode; each cell = 256 px icon + a 48 px sample, on the real page colour.
const CELL = 300
const rows: sharp.OverlayOptions[] = []
for (const [r, mode] of modes.entries()) {
  const bg = THEME.pages[mode]
  rows.push({
    input: await sharp({
      create: { width: CELL * icons.length, height: CELL, channels: 4, background: bg },
    })
      .png()
      .toBuffer(),
    left: 0,
    top: r * CELL,
  })
  for (const [c, icon] of icons.entries()) {
    const file = `${out}/${mode}/${icon.name}.png`
    if (!(await Bun.file(file).exists())) continue
    const big = await sharp(file).resize(240, 240).png().toBuffer()
    const small = await sharp(file).resize(48, 48).png().toBuffer()
    rows.push({ input: big, left: c * CELL + 4, top: r * CELL + 4 })
    rows.push({ input: small, left: c * CELL + CELL - 52, top: r * CELL + CELL - 52 })
  }
}
await sharp({
  create: {
    width: CELL * icons.length,
    height: CELL * modes.length,
    channels: 4,
    background: "#ffffff",
  },
})
  .composite(rows)
  .png()
  .toFile(`${out}/sheet.png`)
console.log(`sheet ${out}/sheet.png`)
