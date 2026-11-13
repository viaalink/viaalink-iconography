/**
 * Re-place already keyed icons on the square canvas (see canvas.ts).
 *   bun scripts/icons/normalize.ts local/icons/rounds/25d-r3 [more dirs…]
 * Rewrites <dir>/{light,dark}/<name>.png in place; <name>.raw.png is untouched,
 * so the step is repeatable.
 */
import { readdir } from "node:fs/promises"
import { squareIcon } from "./canvas"

const dirs = process.argv.slice(2)
if (!dirs.length) throw new Error("usage: normalize.ts <round dir>…")
for (const dir of dirs) {
  for (const mode of ["light", "dark"]) {
    const files = await readdir(`${dir}/${mode}`).catch(() => [] as string[])
    for (const f of files) {
      if (!f.endsWith(".png") || f.endsWith(".raw.png")) continue
      const p = `${dir}/${mode}/${f}`
      await Bun.write(p, await squareIcon(Buffer.from(await Bun.file(p).arrayBuffer()), undefined, !f.startsWith("scene-")))
      console.log(`square ${p}`)
    }
  }
}
