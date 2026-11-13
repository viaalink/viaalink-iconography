/**
 * What a feedback round shows: a snapshot of the current renders, per icon the 2.5D and the flat
 * edition in light and dark. This is the one file that knows this repo's round layout
 * (local/icons/rounds/<style>-<round>/<mode>/<name>.png|svg); another set swaps it for its own.
 */
import { readdir, stat } from "node:fs/promises"
import { join } from "node:path"
import { ICONS } from "../icons/catalog"
import { FLAT } from "../icons/flat"
import type { RoundIcon } from "./types"

/** The canonical rounds: the Blender build (2.5D) and the newest flat round are the source of truth. */
export const CANON = { "25d": "25d-b7", flat: "flat-r9" } as const
export const DOLLS_ROUND = "25d-b8-dolls"
/** Rejected AI variants, the calibration render and aliases (apple = os-macos) are never shown. */
export const NOT_SHOWN = new Set(["ai-b", "ai-c", "mcp-b", "mcp-c", "calib", "apple"])
export const STYLE_EXT = { "25d": "png", flat: "svg" } as const
export type StyleId = keyof typeof STYLE_EXT
const MODES = ["dark", "light"] as const

const has = (p: string) =>
  stat(p).then(
    () => true,
    () => false,
  )

async function roundDirs(roundsDir: string, style: StyleId) {
  const all = await readdir(roundsDir).catch(() => [] as string[])
  const rest = all
    .filter((r) => r.startsWith(`${style}-`) && r !== CANON[style] && r !== DOLLS_ROUND)
    .sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))
  return [CANON[style], ...rest]
}

/** Style of an item key's render round ("25d-b7" → "25d"). */
export const styleOf = (round: string): StyleId => (round.startsWith("flat-") ? "flat" : "25d")

/** Per icon, the newest render of each style and mode (canonical round first). `only` limits the names. */
export async function snapshot(roundsDir: string, only: string[] = []): Promise<RoundIcon[]> {
  const blender = (await readdir(join(roundsDir, CANON["25d"], "dark")).catch(() => [] as string[]))
    .filter((f) => f.endsWith(".png") && !f.endsWith(".raw.png"))
    .map((f) => f.slice(0, -4))
  let names = [...new Set([...ICONS.map((i) => i.name), ...Object.keys(FLAT), ...blender])]
    .filter((n) => !NOT_SHOWN.has(n))
    .sort()
  if (only.length) names = names.filter((n) => only.includes(n))
  const order = { "25d": await roundDirs(roundsDir, "25d"), flat: await roundDirs(roundsDir, "flat") }
  const out: RoundIcon[] = []
  for (const name of names) {
    const icon: RoundIcon = { name, images: {} }
    for (const style of ["25d", "flat"] as const)
      for (const mode of MODES)
        for (const round of order[style])
          if (await has(join(roundsDir, round, mode, `${name}.${STYLE_EXT[style]}`))) {
            icon.images[style] ??= {}
            ;(icon.images[style] as Record<string, string>)[mode] = `round:${round}/${mode}/${name}`
            break
          }
    if (Object.keys(icon.images).length) out.push(icon)
  }
  return out
}
