/**
 * W-140 publishing pack: one build of the icon library for use outside the website.
 *   bun scripts/icons/pack.ts [--out local/icons/pack]   (just icons-pack)
 *
 * Writes, from the canonical rounds (2.5D: 25d-b7, flat: flat-r9) and flat.ts:
 *   svg/{light,dark,themeable,mono}/<name>.svg  flat twins (themeable = CSS variables --via-*)
 *   png/{25d,flat}/{light,dark}/<name>.png       1024 px, transparent
 *   mermaid/viaalink.json                        Iconify icon set (prefix "viaalink"); `<name>` is the
 *                                                themeable flat icon, `<name>-mono` the one-colour stamp
 *   drawio/viaalink-{25d,flat}-{light,dark}.xml  draw.io / diagrams.net libraries (also Confluence;
 *                                                draw.io exports .vsdx for Visio)
 *   README.md, then viaalink-icons.zip of all of it.
 */
import { mkdir, readdir, rm } from "node:fs/promises"
import sharp from "sharp"
import { FLAT, stampSvg, svgFor, svgThemeable } from "./flat"

const arg = (k: string, d: string) => {
  const i = process.argv.indexOf(`--${k}`)
  return i > 0 ? process.argv[i + 1] : d
}
const OUT = arg("out", "local/icons/pack")
const R25 = "local/icons/rounds/25d-b7"
const RFLAT = "local/icons/rounds/flat-r9"
/** Aliases and experiments that are not part of the published set. */
const SKIP = new Set(["apple", "calib", "ai-b", "ai-c", "mcp-b", "mcp-c"])

/** Release split (0.1): `--only a,b` packs just these, `--skip a,b` leaves these out (e.g. third-party
 *  platform marks in their own folder); `--prefix` names the Iconify set. */
const list = (k: string) => new Set(arg(k, "").split(",").filter(Boolean))
const ONLY = list("only")
const EXTRA_SKIP = list("skip")
const PREFIX = arg("prefix", "viaalink")
const have25 = new Set((await readdir(`${R25}/light`)).filter((f) => f.endsWith(".png")).map((f) => f.slice(0, -4)))
const names = Object.keys(FLAT)
  .filter((n) => !SKIP.has(n) && !EXTRA_SKIP.has(n) && (ONLY.size === 0 || ONLY.has(n)) && have25.has(n))
  .sort()

await rm(OUT, { recursive: true, force: true })
for (const d of ["svg/light", "svg/dark", "svg/themeable", "svg/mono", "png/25d/light", "png/25d/dark", "png/flat/light", "png/flat/dark", "mermaid", "drawio"])
  await mkdir(`${OUT}/${d}`, { recursive: true })

const inner = (svg: string) => svg.replace(/^<svg[^>]*>/, "").replace(/<\/svg>\s*$/, "")
const iconify: { prefix: string; width: number; height: number; icons: Record<string, { body: string }> } = {
  prefix: PREFIX,
  width: 24,
  height: 24,
  icons: {},
}
const lib: Record<string, { data: string; w: number; h: number; title: string; aspect: string }[]> = {
  "25d-light": [],
  "25d-dark": [],
  "flat-light": [],
  "flat-dark": [],
}

for (const n of names) {
  const themeable = svgThemeable(n)
  await Bun.write(`${OUT}/svg/themeable/${n}.svg`, themeable)
  await Bun.write(`${OUT}/svg/mono/${n}.svg`, stampSvg(n))
  iconify.icons[n] = { body: inner(themeable) }
  iconify.icons[`${n}-mono`] = { body: inner(stampSvg(n)) }
  for (const mode of ["light", "dark"] as const) {
    const svg = svgFor(n, mode)
    await Bun.write(`${OUT}/svg/${mode}/${n}.svg`, svg)
    const png25 = Bun.file(`${R25}/${mode}/${n}.png`)
    await Bun.write(`${OUT}/png/25d/${mode}/${n}.png`, png25)
    const pngFlat = Bun.file(`${RFLAT}/${mode}/${n}.png`)
    if (await pngFlat.exists()) await Bun.write(`${OUT}/png/flat/${mode}/${n}.png`, pngFlat)
    const small = await sharp(Buffer.from(await png25.arrayBuffer())).resize(256, 256).png().toBuffer()
    lib[`25d-${mode}`].push({ data: `data:image/png;base64,${small.toString("base64")}`, w: 96, h: 96, title: n, aspect: "fixed" })
    lib[`flat-${mode}`].push({
      data: `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`,
      w: 64,
      h: 64,
      title: n,
      aspect: "fixed",
    })
  }
}
await Bun.write(`${OUT}/mermaid/${PREFIX}.json`, JSON.stringify(iconify))
for (const [k, entries] of Object.entries(lib))
  await Bun.write(`${OUT}/drawio/${PREFIX}-${k}.xml`, `<mxlibrary>${JSON.stringify(entries)}</mxlibrary>`)

await Bun.write(
  `${OUT}/README.md`,
  `# Viaalink icons

${names.length} icons, each as a 2.5D render (Blender) and a flat twin, in a light and a dark edition.

| Folder | What |
|---|---|
| \`png/25d/{light,dark}\` | 2.5D renders, 1024 px, transparent |
| \`png/flat/{light,dark}\`, \`svg/{light,dark}\` | flat twins |
| \`svg/themeable\` | flat twins that follow CSS variables \`--via-p --via-s --via-n --via-m --via-r --via-c\` (light colours as fallback) |
| \`svg/mono\` | one colour (\`currentColor\`), for stamps, favicons and print |
| \`mermaid/viaalink.json\` | Iconify set for Mermaid |
| \`drawio/*.xml\` | draw.io / diagrams.net libraries (File → Open Library); draw.io exports Visio (.vsdx) |

## Mermaid

\`\`\`js
mermaid.registerIconPacks([{ name: "viaalink", loader: () => fetch("/viaalink.json").then((r) => r.json()) }])
\`\`\`

\`\`\`mermaid
architecture-beta
  service phone(viaalink:record)[Notetaker phone]
  service relay(viaalink:relay)[Your Relay]
  service ai(viaalink:ai-a)[Your AI]
  phone:R --> L:relay
  relay:R --> L:ai
\`\`\`

Use \`viaalink:<name>-mono\` for the one-colour version.

## Icons

${names.map((n) => `\`${n}\``).join(" · ")}

Platform marks (GitHub, Apple, Windows, Linux, Android, Docker, Raspberry Pi) are trademarks of their owners; use them only to say where Viaalink runs.
`,
)
if (!process.argv.includes("--no-zip")) {
  await rm(`${OUT}.zip`, { force: true })
  const z = Bun.spawnSync(["zip", "-qr", `${process.cwd()}/${OUT}/../viaalink-icons.zip`, "."], { cwd: OUT })
  if (z.exitCode !== 0) throw new Error("zip failed")
}
console.log(`pack: ${names.length} icons → ${OUT} (+ viaalink-icons.zip)`)
