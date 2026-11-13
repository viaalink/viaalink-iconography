/**
 * The flat set: each 2.5D icon's twin, drawn as SVG on a 24-unit grid.
 *
 * A twin is the same object seen straight on: same parts, same colour roles,
 * and a darker "lip" under every solid part so it keeps the chunky feel of
 * the 2.5D version. Geometry is hand-authored (not traced) so it stays crisp
 * in fonts, Iconify and diagram tools (ADR 0001, D6).
 *
 * Colour roles (same as style.ts):
 *   P  primary body        #F73F3F in both modes (W-140: the 2.5D set uses one red too;
 *                          the old dark #FF6B6B read pink next to it)
 *   S  primary lip/shade   #D62828 in both modes
 *   N  secondary part      light #33496E  dark #F6F3EE  (lighter than R: visible over screens)
 *   M  secondary lip       light #1E2F4C  dark #D8D1C6
 *   R  recess (screens)    light #13223A  dark #17243A
 *   C  detail (cream)      light #F6F3EE  dark #F6F3EE
 *
 * The shipped SVG uses CSS variables with the light values as fallback
 * (`fill="var(--via-p, #F73F3F)"`), so one file follows a page theme when
 * inlined and still renders as the light edition inside <img>.
 *
 *   bun scripts/icons/flat.ts --out local/icons/rounds/flat-r1
 * writes <out>/<mode>/<name>.svg + <name>.png (1024) and <out>/pairs.png
 * (2.5D best icon next to its flat twin, both modes).
 */
import sharp from "sharp"
import { mkdir } from "node:fs/promises"
import { parseArgs } from "node:util"

/** The Viaalink mark, recoloured to one role, placed in a box (x, y, width). */
const LOGO = await Bun.file(new URL("../../static/assets/logo-mark.svg", import.meta.url)).text()
const LOGO_VIEWBOX = LOGO.match(/viewBox="([^"]+)"/)![1]
const LOGO_BODY = LOGO.replace(/^[\s\S]*?<title>[^<]*<\/title>/, "")
  .replace(/<\/svg>\s*$/, "")
  .replace(/style="[^"]*"/g, "")
  .replace(/<path /g, '<path fill="{LOGO}" ')
const mark = (x: number, y: number, w: number, f: Role) => {
  const [, , vw, vh] = LOGO_VIEWBOX.split(" ").map(Number)
  return `<svg x="${x}" y="${y}" width="${w}" height="${(w * vh) / vw}" viewBox="${LOGO_VIEWBOX}">${LOGO_BODY.replaceAll("{LOGO}", `{${f}}`)}</svg>`
}

export const ROLES = {
  // light n/m: sand (cream with a darker sand lip), the flat twin of the 2.5D cream secondary parts
  // (owner 2026-11-12, after the expert review found navy used as a body colour on light; navy and
  // red stay for accents). Sand also stays visible over the navy screen recess r.
  light: { p: "#F73F3F", s: "#D62828", n: "#E2D5C4", m: "#BFAE98", r: "#13223A", c: "#F6F3EE" },
  dark: { p: "#F73F3F", s: "#D62828", n: "#F6F3EE", m: "#D8D1C6", r: "#17243A", c: "#F6F3EE" },
} as const
type Role = keyof (typeof ROLES)["light"]

/** `{p}` etc. in the shape strings become fill/stroke values. */
const LIP = 1.1 // depth of the lip, in grid units

/** A solid part with its lip: the same path, shifted down in the shade colour. */
const part = (d: string, body: Role, lip: Role) =>
  `<path d="${d}" fill="{${lip}}" transform="translate(0 ${LIP})"/><path d="${d}" fill="{${body}}"/>`
const rrect = (x: number, y: number, w: number, h: number, r: number) =>
  `M${x + r} ${y}h${w - 2 * r}a${r} ${r} 0 0 1 ${r} ${r}v${h - 2 * r}a${r} ${r} 0 0 1 -${r} ${r}h-${w - 2 * r}a${r} ${r} 0 0 1 -${r} -${r}v-${h - 2 * r}a${r} ${r} 0 0 1 ${r} -${r}z`
const ellipse = (cx: number, cy: number, rx: number, ry: number) =>
  `M${cx - rx} ${cy}a${rx} ${ry} 0 1 0 ${2 * rx} 0a${rx} ${ry} 0 1 0 -${2 * rx} 0z`
const rect = (x: number, y: number, w: number, h: number, r: number, f: Role) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="{${f}}"/>`
const line = (d: string, f: Role, w: number) =>
  `<path d="${d}" fill="none" stroke="{${f}}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`

/**
 * The canonical Viaalink phone (owner, W-140), twin of viaalink_phone() in build.py: the real
 * logo (cream) at the top of the screen, a red record button, then text lines. `dx` shifts it
 * right (room for a cue); the cue (audio pod, padlock badge) is added by the icon.
 */
const viaPhone = (dx = 0, badge = false) =>
  [
    part(rrect(4.8 + dx, 1.3, 14.4, 20.8, 3), "p", "s"),
    rect(6.5 + dx, 3.8, 11, 16.5, 1.5, "r"),
    rect(10.4 + dx, 2.3, 3.2, 0.8, 0.4, "s"),
    mark(8.6 + dx, 5.2, 6.8, "c"),
    `<circle cx="${12 + dx}" cy="12" r="2.75" fill="{c}"/><circle cx="${12 + dx}" cy="12" r="2.05" fill="{r}"/>`,
    `<circle cx="${12 + dx}" cy="12.25" r="1.45" fill="{s}"/><circle cx="${12 + dx}" cy="11.85" r="1.45" fill="{p}"/>`,
    rect(8.4 + dx, 15.3, badge ? 4.6 : 7.2, 0.95, 0.48, "c"),
    rect(8.4 + dx, 16.85, badge ? 4.6 : 7.2, 0.95, 0.48, "c"),
    rect(8.4 + dx, 18.4, badge ? 3 : 4.4, 0.95, 0.48, "c"),
  ].join("")

/**
 * The globe's world map (owner, W-140): scripts/icons/world-land.json projected orthographically
 * onto the flat globe, Europe in the centre, north up — the same view as the 2.5D globe.
 * Points on the far side are pulled onto the rim, so a coast that runs round the back follows it.
 */
const WORLD = JSON.parse(await Bun.file(new URL("./world-land.json", import.meta.url)).text())
const GLOBE = { cx: 11.5, cy: 10.6, r: 7.4, lon0: 8, lat0: 47 }
const project = (lon: number, lat: number): [number, number] | null => {
  const d = Math.PI / 180
  const [l, p, l0, p0] = [lon * d, lat * d, GLOBE.lon0 * d, GLOBE.lat0 * d]
  let x = Math.cos(p) * Math.sin(l - l0)
  let y = Math.cos(p0) * Math.sin(p) - Math.sin(p0) * Math.cos(p) * Math.cos(l - l0)
  const front = Math.sin(p0) * Math.sin(p) + Math.cos(p0) * Math.cos(p) * Math.cos(l - l0)
  if (front < 0) {
    const n = Math.hypot(x, y) || 1
    ;[x, y] = [x / n, y / n]
  }
  return [GLOBE.cx + GLOBE.r * x, GLOBE.cy - GLOBE.r * y]
}
const mapPath = (polys: number[][][]) =>
  polys
    .filter((poly) => poly.length)
    .map((poly) => {
      const pts: [number, number][] = []
      for (let k = 0; k < poly.length; k++) {
        const [a, b] = [poly[k], poly[(k + 1) % poly.length]]
        const m = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1])))
        for (let t = 0; t < m; t++) pts.push(project(a[0] + ((b[0] - a[0]) * t) / m, a[1] + ((b[1] - a[1]) * t) / m)!)
      }
      return "M" + pts.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join("L") + "Z"
    })
    .join("")
const LAND_D = mapPath(Object.values(WORLD.land) as number[][][])
const SEA_D = mapPath(Object.values(WORLD.seas) as number[][][])
const NL = project(WORLD.nl[0], WORLD.nl[1])!

/** The Apple mark (brands/apple.svg) and the inner Octocat silhouette of brands/github.svg (no outer disc). */
const GITHUB_MARK = (await Bun.file(new URL("./brands/github.svg", import.meta.url)).text()).match(/ d="([^"]+)"/)![1]
const GITHUB_OCTOCAT =
  "M9.025 22.4c" +
  GITHUB_MARK.slice(GITHUB_MARK.indexOf("0-.285"), GITHUB_MARK.indexOf(" 0 .315")) +
  "a1 1 0 0 1-1 1h-3.914a1 1 0 0 1-1-1z"
const APPLE_MARK = (await Bun.file(new URL("./brands/apple.svg", import.meta.url)).text()).match(/ d="([^"]+)"/)![1]
const ANDROID_MARK = (await Bun.file(new URL("./brands/android.svg", import.meta.url)).text()).match(/ d="([^"]+)"/)![1]
const LINUX_MARK = (await Bun.file(new URL("./brands/linux.svg", import.meta.url)).text()).match(/ d="([^"]+)"/)![1]
const WINDOWS_MARK = (await Bun.file(new URL("./brands/windows.svg", import.meta.url)).text()).match(/ d="([^"]+)"/)![1]

export const FLAT: Record<string, string> = {
  // laptop: screen with `>` and block cursor on a trapezoid base, one hinge
  cli: [
    rect(9.0, 14.7, 6.0, 1.3, 0.35, "s"), // one central hinge joining screen lid and trapezoid base
    part(
      "M3.3 15.8h17.4a1 1 0 0 1 .9.56l1.5 3.35a1.1 1.1 0 0 1-1 1.55H1.9a1.1 1.1 0 0 1-1-1.55l1.5-3.35a1 1 0 0 1 .9-.56z",
      "p",
      "s",
    ),
    `<path d="M5.2 16.7h13.6l.9 2.0H4.3z" fill="{r}"/>`,
    rect(10.0, 19.4, 4.0, 0.85, 0.4, "r"),
    part(rrect(3.2, 2.0, 17.6, 11.8, 2.2), "p", "s"),
    rect(4.9, 3.6, 14.2, 8.6, 1.2, "r"),
    line("M7.4 5.9l2.8 2.2-2.8 2.2", "c", 1.8),
    rect(12.0, 5.9, 2.2, 4.4, 0.45, "c"),
  ].join(""),

  // relay: a box with a tube running through it; window shows packets and ">"
  relay: [
    part(rrect(0.7, 9.5, 22.6, 5.8, 2.9), "n", "m"),
    part(rrect(4.5, 2.8, 15, 16.8, 3), "p", "s"),
    rect(5.7, 9.2, 12.6, 6.8, 1.4, "r"),
    // owner: `<•••>` — traffic goes both ways through the relay
    ...[10.15, 11.9, 13.65].map((x) => rect(x - 0.7, 11.9, 1.4, 1.4, 0.4, "c")),
    line("M8.6 10.85l-1.9 1.75 1.9 1.75M15.4 10.85l1.9 1.75-1.9 1.75", "c", 1.4),
    mark(7.4, 4.1, 9.2, "c"),
  ].join(""),

  // a real chain: red link face-on, navy link upright and threaded through its hole
  // (navy passes in front of the red back bar and behind the red front bar)
  link: (() => {
    // two links of a taut chain on one axis rising left to right, like the 2.5D link (W-140):
    // the top link passes over the red link's upper rail and under its lower rail
    const ring = (cx: number, cy: number, f: Role, dy = 0) =>
      `<rect x="-6.3" y="-3.2" width="12.6" height="6.4" rx="3.2" fill="none" stroke="{${f}}" stroke-width="2.6" transform="translate(${cx} ${cy + dy}) rotate(-35)"/>`
    const A = [8.3, 14.6] as const // red, bottom-left
    const B = [15.7, 9.4] as const // secondary, top-right
    const top = ring(...B, "m", LIP) + ring(...B, "n")
    const red = ring(...A, "s", LIP) + ring(...A, "p")
    return [
      top,
      red,
      // the half above the chain axis, around the crossing: there the top link lies in front
      `<clipPath id="via-lk"><path d="M7 0H17V12H7Z" transform="rotate(-35 12 12)"/></clipPath>`,
      `<g clip-path="url(#via-lk)">${top}</g>`,
    ].join("")
  })(),

  // asymmetric tick standing on a coin
  check: [
    part(ellipse(12, 19.2, 8.2, 2.6), "n", "m"),
    line("M6.6 11.4l3.9 4.4 8.3-11", "s", 4).replace(
      "<path",
      `<path transform="translate(0 ${LIP})"`,
    ),
    line("M6.6 11.4l3.9 4.4 8.3-11", "p", 4),
  ].join(""),

  // studio mic in a yoke on a base, notepad leaning at the front-right
  notetaker: [
    part(rrect(5, 19.4, 10.4, 2.4, 1.2), "n", "m"),
    rect(9.3, 15.8, 1.8, 4.6, 0.5, "n"),
    line("M4.6 8.8v1.2a5.6 5.6 0 0 0 11.2 0V8.8", "m", 2).replace(
      "<path",
      `<path transform="translate(0 .7)"`,
    ),
    line("M4.6 8.8v1.2a5.6 5.6 0 0 0 11.2 0V8.8", "n", 2),
    rect(4.9, 8.1, 10.6, 1.5, 0.75, "n"), // axle pins: the yoke holds the capsule
    part(rrect(6.5, 1.4, 7.4, 11, 3.7), "p", "s"),
    rect(7.9, 2.7, 4.6, 6.2, 2, "r"),
    ...[4.3, 5.8, 7.3].map((y) => line(`M8.9 ${y}h.8M11.0 ${y}h.8`, "c", 1.15)),
    part(rrect(14.2, 13.6, 8, 8.2, 1.6), "p", "s"),
    rect(15.5, 14.9, 5.4, 5.6, 0.8, "c"),
    ...[16.2, 18.2, 20.2].map((x) => rect(x - 0.4, 12.9, 0.8, 2, 0.4, "n")), // spiral rings, like the 2.5D pad
    line("M16.7 17.2h3M16.7 19h3", "p", 1.15),
  ].join(""),

  // padlock: navy shackle, red body, cream collar round the keyhole
  lock: [
    line("M7.8 11V7.4a4.2 4.2 0 0 1 8.4 0V11", "m", 2.8).replace(
      "<path",
      `<path transform="translate(0 .6)"`,
    ),
    line("M7.8 11V7.4a4.2 4.2 0 0 1 8.4 0V11", "n", 2.8),
    part(rrect(4.6, 9.6, 14.8, 12, 2.8), "p", "s"),
    `<circle cx="12" cy="14.3" r="2.75" fill="{c}"/><path d="M9.9 15.4h4.2l.8 3.5a.7.7 0 0 1-.7.8H9.8a.7.7 0 0 1-.7-.8z" fill="{c}"/>`,
    `<circle cx="12" cy="14.3" r="1.55" fill="{r}"/>`,
    `<path d="M11.1 15h1.8l.55 3.15h-2.9z" fill="{r}"/>`,
  ].join(""),

  // via.yaml: sheet with folded corner, tall dark panel with indented bars, a second sheet
  // behind it peeking out on the left (like the 2.5D model)
  config: [
    part(rrect(2.4, 3.4, 5, 16.4, 1.4), "n", "m"),
    part("M6.6 1.5h9.8l4.6 4.6v14.1a2 2 0 0 1-2 2H6.6a2 2 0 0 1-2-2V3.5a2 2 0 0 1 2-2z", "p", "s"),
    rect(6.5, 5.8, 12.6, 14.4, 1.3, "r"),
    `<path d="M16.4 1.5v3.6a1.5 1.5 0 0 0 1.5 1.5H21v-.5z" fill="{s}"/>`,
    `<path d="M16.4 1.5v3.1a1.5 1.5 0 0 0 1.5 1.5H21z" fill="{c}"/>`,
    ...(
      [
        [8.2, 13.6],
        [10.2, 16.8],
        [10.2, 14.6],
        [8.2, 12.4],
        [10.2, 11.6],
      ] as const
    ).map(([x, x2], i) => line(`M${x} ${8.2 + i * 2.35}H${x2}`, "c", 1.3)),
    // gear badge (blind review: the lines alone read as a log or a Gantt chart)
    `<path d="M19.81 16.88L20.86 17.04L20.86 18.16L19.81 18.32L19.47 19.15L20.10 20.00L19.30 20.80L18.45 20.17L17.62 20.51L17.46 21.56L16.34 21.56L16.18 20.51L15.35 20.17L14.50 20.80L13.70 20.00L14.33 19.15L13.99 18.32L12.94 18.16L12.94 17.04L13.99 16.88L14.33 16.05L13.70 15.20L14.50 14.40L15.35 15.03L16.18 14.69L16.34 13.64L17.46 13.64L17.62 14.69L18.45 15.03L19.30 14.40L20.10 15.20L19.47 16.05Z" fill="{m}" transform="translate(0 .6)"/><path d="M19.81 16.88L20.86 17.04L20.86 18.16L19.81 18.32L19.47 19.15L20.10 20.00L19.30 20.80L18.45 20.17L17.62 20.51L17.46 21.56L16.34 21.56L16.18 20.51L15.35 20.17L14.50 20.80L13.70 20.00L14.33 19.15L13.99 18.32L12.94 18.16L12.94 17.04L13.99 16.88L14.33 16.05L13.70 15.20L14.50 14.40L15.35 15.03L16.18 14.69L16.34 13.64L17.46 13.64L17.62 14.69L18.45 15.03L19.30 14.40L20.10 15.20L19.47 16.05Z" fill="{c}"/>`,
    `<circle cx="16.9" cy="17.6" r="1.25" fill="{p}"/>`,
  ].join(""),

  // globe (owner, W-140): a real world map, Europe facing you, a red pin on the Netherlands;
  // the grid is subtle (thin darker-red equator and meridian under the land)
  globe: [
    part(rrect(6.9, 20.1, 9.2, 2.2, 1.1), "n", "m"),
    rect(10.6, 17.6, 1.8, 3.6, 0.5, "n"),
    line("M18.1 3.7a8.9 8.9 0 0 1-12.4 12.8", "n", 1.7),
    `<circle cx="11.5" cy="10.6" r="7.4" fill="{s}" transform="translate(0 ${LIP * 0.6})"/>`,
    `<circle cx="11.5" cy="10.6" r="7.4" fill="{p}"/>`,
    `<clipPath id="via-gl"><circle cx="11.5" cy="10.6" r="7.4"/></clipPath>`,
    `<g clip-path="url(#via-gl)">`,
    `<path d="M4.1 11.9a7.4 2.2 0 0 0 14.8 0M11.5 3.2a2.6 7.4 0 0 0 0 14.8" fill="none" stroke="{s}" stroke-width=".55"/>`,
    `<path d="${LAND_D}" fill="{c}" fill-rule="nonzero" data-land="1"/>`,
    `<path d="${SEA_D}" fill="{p}"/>`,
    `</g>`,
    `<circle cx="${NL[0].toFixed(2)}" cy="${NL[1].toFixed(2)}" r="1.05" fill="{c}"/><circle cx="${NL[0].toFixed(2)}" cy="${NL[1].toFixed(2)}" r=".7" fill="{p}"/>`,
  ].join(""),

  // phone: dark screen with a cream card and a padlock badge, like a secure page
  // social: canonical Viaalink phone with ONE big chat bubble beside it
  social: [
    viaPhone(-2.8),
    part(
      "M15.0 4.2h5.4a2.4 2.4 0 0 1 2.4 2.4v3.0a2.4 2.4 0 0 1-2.4 2.4h-4.6l-3.2 2.2V6.6a2.4 2.4 0 0 1 2.4-2.4z",
      "n",
      "m",
    ),
    ...[15.2, 17.7, 20.2].map((x) => `<circle cx="${x}" cy="8.1" r="1" fill="{p}"/>`),
  ].join(""),

  phone: [
    part(rrect(5.5, 1.3, 13, 20.8, 3), "p", "s"),
    rect(7.1, 3.9, 9.8, 16.2, 1.5, "r"),
    rect(10.4, 2.3, 3.2, 0.8, 0.4, "s"),
    rect(8.4, 5.6, 7.2, 12.8, 1.4, "c"),
    line("M10.6 9.8V8.4a1.4 1.4 0 0 1 2.8 0v1.4", "p", 1.15),
    rect(9.7, 9.5, 4.6, 3.6, 0.8, "p"),
    `<circle cx="12" cy="11.3" r=".55" fill="{c}"/>`,
    line("M9.9 14.9h4.2M9.9 16.6h2.8", "p", 1.1),
  ].join(""),

  // browser: a real page (header, image, text, button) and a pointer
  browser: [
    part(rrect(1.2, 2.6, 21.6, 17.6, 2.6), "p", "s"),
    ...[3.9, 5.8, 7.7].map((x) => `<circle cx="${x}" cy="5" r=".75" fill="{c}"/>`),
    rect(9.5, 4, 11.4, 2, 1, "c"),
    line("M10.75 5v-.2a.55.55 0 0 1 1.1 0v.2", "p", 0.6),
    rect(10.35, 4.95, 1.9, 0.85, 0.25, "p"),
    rect(2.9, 7.3, 18.2, 11.2, 1.1, "r"),
    rect(4, 8.3, 16, 1.3, 0.6, "c"),
    rect(4, 10.5, 7, 6.9, 0.9, "c"),
    `<path d="M4.8 16.6l2.1-2.9 1.4 1.7.9-1 1.7 2.2z" fill="{r}"/><circle cx="9.3" cy="12" r=".75" fill="{r}"/>`,
    rect(12.3, 10.7, 7.2, 1.1, 0.55, "c"),
    rect(12.3, 12.5, 5.6, 1.1, 0.55, "c"),
    rect(12.3, 14.3, 4.2, 1.1, 0.55, "c"),
    rect(12.3, 15.9, 3.4, 1.7, 0.85, "p"),
    `<path transform="translate(.6 .7)" d="M15.6 15.5v5.8l1.4-1.3 1.1 2.1 1.3-.6-1.1-2.1 2-.1z" fill="{c}" stroke="{r}" stroke-width=".75" stroke-linejoin="round"/>`,
  ].join(""),

  // meet: video-meeting screen with top camera barrel and two-up participant grid
  meet: [
    part(rrect(1.2, 5, 21.6, 16, 2.6), "p", "s"),
    rect(2.8, 6.8, 18.4, 12.4, 1.3, "r"),
    line("M12 9v8.6", "c", 1),
    `<circle cx="7.4" cy="11.1" r="2" fill="{c}"/><path d="M4.2 17.7c0-2.1 1.4-3.5 3.2-3.5s3.2 1.4 3.2 3.5z" fill="{c}"/>`,
    `<circle cx="16.6" cy="11.1" r="2" fill="{c}"/><path d="M13.4 17.7c0-2.1 1.4-3.5 3.2-3.5s3.2 1.4 3.2 3.5z" fill="{c}"/>`,
    // webcam sits on the top edge, like the 2.5D model
    part(rrect(8.8, 1, 6.4, 4.4, 2.2), "n", "m"),
    `<circle cx="12" cy="3.2" r="1.6" fill="{p}"/><circle cx="12" cy="3.2" r="1" fill="{r}"/>`,
  ].join(""),

  // chat: overlapping speech bubbles with message bars and a padlock badge
  chat: [
    part(
      "M12.9 .9h7.2a2.4 2.4 0 0 1 2.4 2.4v4.2a2.4 2.4 0 0 1-2.4 2.4h-7.2a2.4 2.4 0 0 1-2.4-2.4V3.3a2.4 2.4 0 0 1 2.4-2.4z",
      "n",
      "m",
    ),
    part(
      "M3.8 5.2h11.8a2.6 2.6 0 0 1 2.6 2.6v8.8a2.6 2.6 0 0 1-2.6 2.6H8.4l-3.2 2.8v-2.8H3.8a2.6 2.6 0 0 1-2.6-2.6V7.8a2.6 2.6 0 0 1 2.6-2.6z",
      "p",
      "s",
    ),
    rect(3, 7, 13.4, 10.4, 1.4, "r"),
    rect(4.6, 9.2, 9.2, 1.7, 0.85, "c"),
    rect(4.6, 12.4, 6.2, 1.7, 0.85, "c"),
    line("M16.3 15.6v-1.8a1.7 1.7 0 0 1 3.4 0v1.8", "m", 1.7).replace(
      "<path",
      `<path transform="translate(0 .5)"`,
    ),
    line("M16.3 15.6v-1.8a1.7 1.7 0 0 1 3.4 0v1.8", "n", 1.7),
    part(rrect(14.6, 15.2, 6.8, 6.2, 1.5), "n", "m"),
    rect(15.6, 16.1, 4.8, 4.4, 0.9, "c"),
    `<circle cx="18" cy="17.6" r=".85" fill="{r}"/><path d="M17.5 18h1l.25 1.8h-1.5z" fill="{r}"/>`,
  ].join(""),

  // call: red smartphone (like the 2.5D model), cream handset and two voice bars on the screen
  call: [
    part(rrect(4.8, 1.3, 14.4, 20.8, 3), "p", "s"),
    rect(6.5, 3.8, 11, 16.5, 1.5, "r"),
    rect(10.4, 2.3, 3.2, 0.8, 0.4, "s"),
    // two sound-wave arcs off the handset's open side (two bars read as "pause")
    line("M11.89 7.73A4.5 4.5 0 0 1 15.03 10.56M12.35 5.89A6.4 6.4 0 0 1 16.81 9.91", "c", 1.1),
    `<path transform="translate(2.6 2) scale(.82)" d="M7.8 7.8a1.4 1.4 0 0 1 2 0l1.5 1.5a1 1 0 0 1 0 1.4l-1 1a5.5 5.5 0 0 0 2.6 2.6l1-1a1 1 0 0 1 1.4 0l1.5 1.5a1.4 1.4 0 0 1 0 2l-1.2 1.2c-1.6 1.6-4.6.6-7.1-1.9s-3.5-5.5-1.9-7.1z" fill="{c}"/>`,
  ].join(""),

  // files (share): folder with ONE depth like the 2.5D model — back flap with a tab, cream
  // paper sticking out, front panel with the share glyph (3 dots + 2 lines) on it
  files: [
    part(
      "M4.2 3h5.2a2 2 0 0 1 1.6.8l1.1 1.4H20a2.2 2.2 0 0 1 2.2 2.2v11.6a2.2 2.2 0 0 1-2.2 2.2H4.2A2.2 2.2 0 0 1 2 19V5.2A2.2 2.2 0 0 1 4.2 3z",
      "p",
      "s",
    ),
    rect(5.2, 6.2, 13.6, 9.4, 1.2, "c"),
    line("M8 8.2h8M8 10.1h6", "r", 1.2),
    rect(2, 10.3, 20.2, 4.4, 2.2, "s"), // shade: the front pocket stands in front of the back flap
    part(rrect(2, 11.2, 20.2, 10.6, 2.2), "p", "s"),
    line("M9.2 16.5L14.4 14.1M9.2 16.5L14.4 18.9", "c", 1.1),
    `<circle cx="9.2" cy="16.5" r="1.55" fill="{c}"/><circle cx="14.4" cy="14.1" r="1.55" fill="{c}"/><circle cx="14.4" cy="18.9" r="1.55" fill="{c}"/>`,
  ].join(""),

  // record: the canonical Viaalink phone (logo, record button, text lines)
  record: [viaPhone()].join(""),

  // transcribe: red waveform block on the left, arrow in the middle, cream page with 3 text lines on the right
  transcribe: [
    part(rrect(0.8, 5.0, 7.6, 12.4, 2.0), "p", "s"),
    line("M2.6 9.3v3.8M4.6 7.2v8.0M6.6 8.7v5.0", "c", 1.45),
    line("M9.6 11.2h3.3M11.3 9.0l2.2 2.2-2.2 2.2", "m", 1.9).replace("<path", `<path transform="translate(0 .7)"`),
    line("M9.6 11.2h3.3M11.3 9.0l2.2 2.2-2.2 2.2", "n", 1.9),
    part(rrect(14.4, 3.8, 8.8, 14.8, 1.8), "n", "m"),
    rect(15.05, 4.45, 7.5, 13.5, 1.25, "c"),
    line("M16.6 8.1h4.2M16.6 11.2h4.2M16.6 14.3h2.6", "r", 1.4),
  ].join(""),

  // minutes: red clipboard/page with the small Viaalink mark at the top and 3 cream timestamp lines (dot + line each)
  minutes: [
    part(rrect(3.4, 3.2, 17.2, 18.8, 2.8), "p", "s"),
    rect(5.4, 6.6, 13.2, 13.6, 1.5, "r"),
    part(
      "M10.8 1.2h2.4a1.2 1.2 0 0 1 1.2 1.2v.4h1.2a1.4 1.4 0 0 1 1.4 1.4v1.2a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4.2a1.4 1.4 0 0 1 1.4-1.4h1.2v-.4a1.2 1.2 0 0 1 1.2-1.2z",
      "n",
      "m",
    ),
    mark(8.9, 8.5, 6.2, "c"),
    ...[
      [13.6, 7.4],
      [16.0, 7.4],
      [18.4, 4.8],
    ].flatMap(([y, w]) => [`<circle cx="7.6" cy="${y}" r=".8" fill="{c}"/>`, rect(9.4, y - 0.65, w, 1.3, 0.65, "c")]),
  ].join(""),

  // report: AI summary on a clipboard, like the 2.5D model: ✦ heading, then summary lines
  report: [
    part(rrect(3.4, 3.2, 17.2, 18.8, 2.8), "p", "s"),
    rect(5.4, 6.6, 13.2, 13.6, 1.5, "r"),
    part(
      "M10.8 1.2h2.4a1.2 1.2 0 0 1 1.2 1.2v.4h1.2a1.4 1.4 0 0 1 1.4 1.4v1.2a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4.2a1.4 1.4 0 0 1 1.4-1.4h1.2v-.4a1.2 1.2 0 0 1 1.2-1.2z",
      "n",
      "m",
    ),
    `<path d="M8.9 7.9c.35 1.55.85 2.05 2.4 2.4-1.55.35-2.05.85-2.4 2.4-.35-1.55-.85-2.05-2.4-2.4 1.55-.35 2.05-.85 2.4-2.4z" fill="{c}"/>`,
    rect(12.4, 9.55, 4.6, 1.5, 0.75, "c"),
    rect(7.2, 13.4, 9.8, 1.35, 0.68, "c"),
    rect(7.2, 15.6, 9.8, 1.35, 0.68, "c"),
    rect(7.2, 17.8, 5.6, 1.35, 0.68, "c"),
  ].join(""),

  // page: personal web page with only a thin top bar, header strip, round avatar, and two content blocks
  page: [
    part(rrect(1.8, 2.2, 20.4, 18.6, 2.6), "p", "s"),
    rect(3.8, 3.35, 7.6, 0.85, 0.42, "c"),
    rect(3.4, 5.0, 17.2, 14.2, 1.3, "r"),
    rect(4.6, 6.0, 14.8, 2.1, 0.8, "c"),
    `<circle cx="12" cy="11.3" r="2.55" fill="{c}"/>`,
    `<circle cx="12" cy="10.55" r=".78" fill="{r}"/><path d="M10.35 13.1c0-1.05.74-1.65 1.65-1.65s1.65.6 1.65 1.65z" fill="{r}"/>`,
    rect(4.6, 14.8, 6.9, 3.2, 0.85, "c"),
    rect(12.5, 14.8, 6.9, 3.2, 0.85, "c"),
  ].join(""),

  // ai-a: the robot head of the 2.5D model seen straight on — screen face with a flat "> ✦",
  // ear bolts and an antenna (no base: flat, a base read as a play button)
  "ai-a": [
    line("M12 5V2.6", "n", 1.2),
    `<circle cx="12" cy="2.1" r="1.35" fill="{p}"/>`,
    part(rrect(0.8, 9.3, 2.6, 5.6, 1.1), "n", "m"),
    part(rrect(20.6, 9.3, 2.6, 5.6, 1.1), "n", "m"),
    part(rrect(2.8, 4.8, 18.4, 15.4, 3.4), "p", "s"),
    rect(4.6, 6.6, 14.8, 11.8, 1.6, "r"),
    line("M6.9 9.7l2.9 2.8-2.9 2.8", "c", 1.8),
    `<path d="M15.2 9.3c.45 2 1.2 2.75 3.2 3.2-2 .45-2.75 1.2-3.2 3.2-.45-2-1.2-2.75-3.2-3.2 2-.45 2.75-1.2 3.2-3.2z" fill="{c}"/>`,
  ].join(""),

  // mcp-a (connect): the 2.5D pair seen from the front — the agent plug (red, ">" screen) on the
  // left, its two cream prongs going into the Viaalink socket (secondary, red port rim, logo)
  "mcp-a": [
    part(rrect(13.4, 4.6, 9.4, 13.4, 2.4), "n", "m"),
    rect(13.4, 6, 2.8, 10.6, 1.1, "p"), // red port rim (the 2.5D accent frame) with the dark port in it
    rect(13.4, 7, 1.7, 8.6, 0.7, "r"),
    mark(16.4, 9.9, 5.4, "p"),
    part(rrect(10.6, 7.6, 4.2, 1.9, 0.5), "c", "m"),
    part(rrect(10.6, 12.3, 4.2, 1.9, 0.5), "c", "m"),
    part(rrect(1.2, 4.6, 10.4, 13.4, 2.4), "p", "s"),
    rect(2.9, 6.3, 7, 10, 1.3, "r"),
    line("M5 9l2.6 2.3L5 13.6", "c", 1.8),
  ].join(""),

  // warning: chunky rounded triangle slab (p/s) with a cream "!" — no base disc, like the 2.5D slab
  warning: [
    `<g transform="translate(0 1.6)">`, // centred on the grid now the disc is gone
    part(
      "M10.1 2.7a2.2 2.2 0 0 1 3.8 0l7.4 12.8a2.2 2.2 0 0 1-1.9 3.3H4.6a2.2 2.2 0 0 1-1.9-3.3z",
      "p",
      "s",
    ),
    rect(10.8, 6.9, 2.4, 5.8, 1.2, "c"),
    `<circle cx="12" cy="15.3" r="1.35" fill="{c}"/>`,
    `</g>`,
  ].join(""),

  // error: chunky rounded octagon (p/s) with a cream "×" (two flat pill strokes)
  error: [
    part(
      "M8.6 2.2h6.8a2.2 2.2 0 0 1 1.56.64l4.2 4.2a2.2 2.2 0 0 1 .64 1.56v5.8a2.2 2.2 0 0 1-.64 1.56l-4.2 4.2a2.2 2.2 0 0 1-1.56.64H8.6a2.2 2.2 0 0 1-1.56-.64l-4.2-4.2A2.2 2.2 0 0 1 2.2 14.4V8.6a2.2 2.2 0 0 1 .64-1.56l4.2-4.2A2.2 2.2 0 0 1 8.6 2.2z",
      "p",
      "s",
    ),
    line("M8.6 8.1l6.8 6.8M15.4 8.1l-6.8 6.8", "c", 2.6),
  ].join(""),

  // info: chunky rounded disc (n/m) with a red accent ring, dark recess (r) and a cream "i"
  info: [
    part(ellipse(12, 11.5, 9.6, 9.6), "n", "m"),
    `<circle cx="12" cy="11.5" r="7.5" fill="{p}"/>`,
    `<circle cx="12" cy="11.5" r="6.4" fill="{r}"/>`,
    `<circle cx="12" cy="8.1" r="1.35" fill="{c}"/>`,
    rect(10.8, 10.6, 2.4, 5.2, 1.2, "c"),
  ].join(""),

  // pending: clock disc (p/s) with a dark face (r), two cream hands and 4 cream ticks at 12/3/6/9
  pending: [
    part(ellipse(12, 11.5, 9.6, 9.6), "p", "s"),
    `<circle cx="12" cy="11.5" r="7.2" fill="{r}"/>`,
    `<circle cx="12" cy="5.5" r=".75" fill="{c}"/><circle cx="18" cy="11.5" r=".75" fill="{c}"/><circle cx="12" cy="17.5" r=".75" fill="{c}"/><circle cx="6" cy="11.5" r=".75" fill="{c}"/>`,
    line("M12 8.2v3.3l2.7 1.6", "c", 2.0),
  ].join(""),

  // server: stacked rack of 3 rounded units (p/s body, n front panels) with side pipe ports, cream LEDs and dark vent slot
  server: [
    part(rrect(0.5, 8.7, 23.0, 5.6, 2.8), "n", "m"),
    ...[1.6, 8.7, 15.8].map((y) =>
      [
        part(rrect(3.6, y, 16.8, 5.6, 1.9), "p", "s"),
        rect(4.9, y + 1.1, 14.2, 3.4, 1.0, "n"),
        rect(5.8, y + 1.8, 4.4, 2.0, 1.0, "r"),
        `<circle cx="7.0" cy="${y + 2.8}" r=".65" fill="{c}"/><circle cx="9.0" cy="${y + 2.8}" r=".65" fill="{c}"/>`,
        rect(11.7, y + 1.7, 6.5, 2.2, 1.0, "p"),
        rect(12.3, y + 2.1, 5.3, 1.4, 0.7, "r"),
      ].join(""),
    ),
  ].join(""),

  // database: 3 stacked rounded discs (cylinder stack) in p/s with n/m rings between, cream highlight dots
  // database: a stacked cylinder, like the 2.5D disc stack — elliptical top, two band seams,
  // two cream dots per tier (validation: the stacked pills read as a server rack)
  database: [
    part("M3.5 5v14a8.5 2.8 0 0 0 17 0V5z", "p", "s"),
    `<ellipse cx="12" cy="5" rx="8.5" ry="2.8" fill="{s}"/><ellipse cx="12" cy="4.75" rx="7.6" ry="2.2" fill="{p}"/>`,
    line("M3.5 10.6a8.5 2.8 0 0 0 17 0M3.5 15.6a8.5 2.8 0 0 0 17 0", "n", 1.1),
    ...[9.3, 14.3, 19.2].map((y) => `<circle cx="6.6" cy="${y - 0.4}" r=".75" fill="{c}"/><circle cx="8.9" cy="${y + 0.3}" r=".75" fill="{c}"/>`),
  ].join(""),

  // team: three toy-figure heads/shoulders together on a base (middle one larger)
  team: [
    part(rrect(1.4, 18.2, 21.2, 3.6, 1.8), "n", "m"),
    // left & right figures
    part(ellipse(5.2, 9.6, 2.1, 2.1), "p", "s"),
    part("M2.1 17.6c0-2.6 1.4-4.2 3.1-4.2s3.1 1.6 3.1 4.2z", "p", "s"),
    part(ellipse(18.8, 9.6, 2.1, 2.1), "p", "s"),
    part("M15.7 17.6c0-2.6 1.4-4.2 3.1-4.2s3.1 1.6 3.1 4.2z", "p", "s"),
    // middle figure (larger, in front)
    part(ellipse(12, 6.8, 2.7, 2.7), "p", "s"),
    part("M8.0 18.0c0-3.5 1.8-5.6 4.0-5.6s4.0 2.1 4.0 5.6z", "p", "s"),
  ].join(""),

  // OS devices (owner, 016): desktop monitor on a stand (os-linux, os-macos, os-windows) and
  // plain phone body (os-ios, os-android), each with ONLY that OS mark in cream on its navy screen
  "os-linux": [
    part(rrect(7, 19.6, 10, 2.2, 1.1), "n", "m"),
    rect(10.4, 16.2, 3.2, 4.2, 0.6, "n"),
    part(rrect(1.4, 2, 21.2, 14.8, 2.4), "p", "s"),
    rect(3.2, 3.8, 17.6, 11.2, 1.3, "r"),
    `<path data-mark="1" fill="{c}" transform="translate(8.1 5.5) scale(${7.8 / 24})" d="${LINUX_MARK}"/>`,
  ].join(""),
  // owner: the Apple mark itself, solid red with the lip (twin of apple_mark_solid())
  apple: `<g transform="translate(1.8 1.2) scale(0.85)">${part(APPLE_MARK, "p", "s")}</g>`,
  "os-macos": [
    part(rrect(7, 19.6, 10, 2.2, 1.1), "n", "m"),
    rect(10.4, 16.2, 3.2, 4.2, 0.6, "n"),
    part(rrect(1.4, 2, 21.2, 14.8, 2.4), "p", "s"),
    rect(3.2, 3.8, 17.6, 11.2, 1.3, "r"),
    `<path data-mark="1" fill="{c}" transform="translate(8.3 5.6) scale(${7.4 / 24})" d="${APPLE_MARK}"/>`,
  ].join(""),
  // iOS: the phone is the object — our plain phone body with the Apple mark (brands/apple.svg,
  // unaltered) in cream on its navy screen
  "os-ios": [
    part(rrect(4.8, 1.3, 14.4, 20.8, 3), "p", "s"),
    rect(6.5, 3.8, 11, 16.5, 1.5, "r"),
    rect(10.4, 2.3, 3.2, 0.8, 0.4, "s"),
    `<path data-mark="1" fill="{c}" transform="translate(8.4 8.2) scale(${7.2 / 24})" d="${APPLE_MARK}"/>`,
  ].join(""),
  // Android: plain phone body with the Android mark (brands/android.svg) in cream on its navy screen
  "os-android": [
    part(rrect(4.8, 1.3, 14.4, 20.8, 3), "p", "s"),
    rect(6.5, 3.8, 11, 16.5, 1.5, "r"),
    rect(10.4, 2.3, 3.2, 0.8, 0.4, "s"),
    `<path data-mark="1" fill="{c}" transform="translate(7.9 7.95) scale(${8.2 / 24})" d="${ANDROID_MARK}"/>`,
  ].join(""),
  // Windows: desktop monitor on a stand with the Windows mark (brands/windows.svg) in cream on its navy screen
  "os-windows": [
    part(rrect(7, 19.6, 10, 2.2, 1.1), "n", "m"),
    rect(10.4, 16.2, 3.2, 4.2, 0.6, "n"),
    part(rrect(1.4, 2, 21.2, 14.8, 2.4), "p", "s"),
    rect(3.2, 3.8, 17.6, 11.2, 1.3, "r"),
    `<path data-mark="1" fill="{c}" transform="translate(8.5 5.9) scale(${7.0 / 24})" d="${WINDOWS_MARK}"/>`,
  ].join(""),
  // GitHub: the Octocat mark itself (brands/github.svg inner contour), solid red with the lip, no disc behind it
  github: `<g transform="translate(-0.2 -3.3) scale(1.06)">${part(GITHUB_OCTOCAT, "p", "s").replace(`translate(0 ${LIP})`, "translate(0 .85)")}</g>`,
  // NAS: red rounded body with side pipe ports, four cream drive trays with grip slots and status LEDs
  nas: [
    part(rrect(0.5, 9.4, 23.0, 5.6, 2.8), "n", "m"),
    part(rrect(3.6, 1.8, 16.8, 19.4, 2.6), "p", "s"),
    rect(5, 3.6, 14, 15.6, 1.2, "r"),
    ...[0, 1, 2, 3].map((i) => rect(5.8 + i * 3.25, 4.4, 2.75, 14, 0.8, "c")),
    ...[0, 1, 2, 3].map((i) => rect(6.9 + i * 3.25, 6, 0.55, 6, 0.27, "r")),
    ...[0, 1, 2, 3].map((i) => `<circle cx="${7.17 + i * 3.25}" cy="15.6" r=".6" fill="{p}"/>`),
  ].join(""),
  // Raspberry Pi, sculpted twin: solid red drupelets with darker-red lip/gap, cream leaves on top
  raspberrypi: [
    `<path d="M11.6 6.4C9.4 3.5 6.1 3.1 4.3 4.3c1.3 2.6 4.2 3.7 7.3 2.8zM12.4 6.4c2.2-2.9 5.5-3.3 7.3-2.1-1.3 2.6-4.2 3.7-7.3 2.8z" fill="{r}" stroke="{r}" stroke-width=".6" stroke-linejoin="round"/>`,
    `<ellipse cx="12" cy="14.5" rx="5.8" ry="6.2" fill="{s}"/>`,
    ...[
      [8.5, 9.6, 2.35],
      [15.5, 9.6, 2.35],
      [12.0, 9.3, 2.45],
      [6.7, 13.1, 2.45],
      [17.3, 13.1, 2.45],
      [10.25, 13.0, 2.5],
      [13.75, 13.0, 2.5],
      [8.4, 16.6, 2.45],
      [15.6, 16.6, 2.45],
      [12.0, 16.7, 2.5],
      [10.3, 19.7, 2.3],
      [13.7, 19.7, 2.3],
    ].map(
      ([x, y, r]) =>
        `<circle cx="${x}" cy="${y + 0.65}" r="${r}" fill="{s}"/><circle cx="${x}" cy="${y}" r="${r}" fill="{p}" stroke="{s}" stroke-width=".75"/>`,
    ),
  ].join(""),
  // Docker, our way (owner): the whale's containers spell VIA on top and LINK below, one letter each
  docker: [
    ...[..."VIA"].map((ch, i) => [4.6 + i * 4.1, 3.4, ch] as const)
      .concat([..."LINK"].map((ch, i) => [2.55 + i * 4.1, 7.5, ch] as const))
      .map(
        ([x, y, ch]) =>
          part(rrect(x, y, 3.7, 3.7, 0.5), "n", "m") +
          `<text x="${x + 1.85}" y="${y + 2.85}" text-anchor="middle" font-family="DejaVu Sans Mono" font-weight="bold" font-size="2.9" fill="{p}" stroke="{c}" stroke-width=".35" paint-order="stroke">${ch}</text>`,
      ),
    part("M1.6 12h17.6c.8-1.6 2.2-2.4 3.6-2.2-.2 1.4-.9 2.4-2 2.9C19.6 18 15 21.4 9.6 21.4 4.6 21.4 1.6 17.4 1.6 12z", "p", "s"),
    `<circle cx="5.6" cy="14.6" r=".8" fill="{c}"/>`,
  ].join(""),

  // desktop: monitor on a stand, the screen showing the Viaalink app (logo + text lines)
  desktop: [
    part(rrect(7, 19.6, 10, 2.2, 1.1), "n", "m"),
    rect(10.4, 16.2, 3.2, 4.2, 0.6, "n"),
    part(rrect(1.4, 2, 21.2, 14.8, 2.4), "p", "s"),
    rect(3.2, 3.8, 17.6, 11.2, 1.3, "r"),
    mark(8.6, 4.8, 6.8, "c"),
    rect(6, 9.8, 12, 1.1, 0.55, "c"),
    rect(6, 11.5, 12, 1.1, 0.55, "c"),
    rect(6, 13.2, 7.6, 1.1, 0.55, "c"),
  ].join(""),

  // tablet: landscape tablet (red body, navy screen with two cream text blocks)
  tablet: [
    part(rrect(1.2, 3.2, 21.6, 16.4, 2.8), "p", "s"),
    rect(3.2, 5.2, 17.2, 12.4, 1.4, "r"),
    `<circle cx="21.6" cy="11.4" r=".6" fill="{c}"/>`,
    rect(4.8, 7.0, 6.4, 2.6, 0.7, "c"),
    rect(4.8, 10.8, 6.4, 1.1, 0.55, "c"),
    rect(4.8, 12.6, 4.6, 1.1, 0.55, "c"),
    rect(12.4, 7.0, 6.4, 2.6, 0.7, "c"),
    rect(12.4, 10.8, 6.4, 1.1, 0.55, "c"),
    rect(12.4, 12.6, 4.0, 1.1, 0.55, "c"),
  ].join(""),

  // browser-ext: puzzle piece (red) with a small cream Viaalink logo on it
  "browser-ext": [
    part(
      "M5 6.2h3.8a2.3 2.3 0 1 1 4.4 0H17a2 2 0 0 1 2 2v3.2a2.3 2.3 0 1 1 0 4.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3.2a2.2 2.2 0 1 0 0-4.4V8.2a2 2 0 0 1 2-2z",
      "p",
      "s",
    ),
    mark(7.6, 11.2, 7.2, "c"),
  ].join(""),

  // vscode: code editor window (red frame, navy pane) showing "</>" in cream
  vscode: [
    part(rrect(1.4, 2.6, 21.2, 17.6, 2.6), "p", "s"),
    ...[4.1, 6.0, 7.9].map((x) => `<circle cx="${x}" cy="5" r=".75" fill="{c}"/>`),
    rect(3.1, 7.2, 17.8, 11.3, 1.2, "r"),
    line("M8.8 10.6L6.2 12.85l2.6 2.25M15.2 10.6l2.6 2.25-2.6 2.25M13.1 9.8l-2.2 6.1", "c", 1.5),
  ].join(""),

  // mail: envelope (red) with a cream flap line
  mail: [
    part(rrect(1.6, 4.2, 20.8, 14.6, 2.6), "p", "s"),
    line("M4.2 7.2L12 13.0l7.8-5.8", "c", 2.0),
  ].join(""),

  // calendar: desk calendar (red binding rings on top, cream page with a grid and one red day)
  calendar: [
    part(rrect(2.4, 3.6, 19.2, 17.4, 2.6), "p", "s"),
    rect(5.8, 3.2, 3.6, 1.8, 0.9, "c"),
    rect(14.6, 3.2, 3.6, 1.8, 0.9, "c"),
    part(rrect(6.4, 1.4, 2.4, 3.2, 1.1), "p", "s"),
    part(rrect(15.2, 1.4, 2.4, 3.2, 1.1), "p", "s"),
    rect(4.2, 8.0, 15.6, 11.2, 1.4, "c"),
    rect(5.8, 9.6, 3.4, 3.2, 0.7, "r"),
    rect(10.3, 9.6, 3.4, 3.2, 0.7, "p"),
    rect(14.8, 9.6, 3.4, 3.2, 0.7, "r"),
    rect(5.8, 14.2, 3.4, 3.2, 0.7, "r"),
    rect(10.3, 14.2, 3.4, 3.2, 0.7, "r"),
    rect(14.8, 14.2, 3.4, 3.2, 0.7, "r"),
  ].join(""),

  // qr-pair: QR code tile (cream with navy squares; three finder squares) with a small red link chain badge
  "qr-pair": [
    part(rrect(1.8, 1.8, 18.4, 18.4, 2.6), "n", "m"),
    rect(3.2, 3.2, 15.6, 15.6, 1.6, "c"),
    // three finder squares (top-left, top-right, bottom-left)
    ...[
      [4.2, 4.2],
      [12.2, 4.2],
      [4.2, 12.2],
    ].flatMap(([x, y]) => [
      `<rect x="${x}" y="${y}" width="5.6" height="5.6" rx="1" fill="none" stroke="{r}" stroke-width="1.2"/>`,
      rect(x + 1.8, y + 1.8, 2.0, 2.0, 0.4, "r"),
    ]),
    rect(10.3, 10.3, 1.8, 1.8, 0.4, "r"),
    // red link chain badge in bottom-right corner
    part(ellipse(17.6, 17.2, 4.8, 4.8), "p", "s"),
    `<g transform="translate(17.6 17.2) rotate(-35)"><rect x="-3.1" y="-1.3" width="3.8" height="2.6" rx="1.3" fill="none" stroke="{c}" stroke-width="1.15"/><rect x="-0.7" y="-1.3" width="3.8" height="2.6" rx="1.3" fill="none" stroke="{c}" stroke-width="1.15"/></g>`,
  ].join(""),

  // bluetooth: the Bluetooth rune itself in red with the lip, no disc
  bluetooth: [
    line("M7.0 7.0l10.0 9.5-5.0 4.5V3.0l5.0 4.5-10.0 9.5", "s", 2.5).replace(
      "<path",
      `<path transform="translate(0 ${LIP})"`,
    ),
    line("M7.0 7.0l10.0 9.5-5.0 4.5V3.0l5.0 4.5-10.0 9.5", "p", 2.5),
  ].join(""),

  // wifi: three concentric red arcs and a dot below with the lip, no tile
  wifi: [
    line("M2.04 9.23a13.4 13.4 0 0 1 19.92 0M5.01 11.91a9.4 9.4 0 0 1 13.98 0M7.99 14.59a5.4 5.4 0 0 1 8.02 0", "s", 2.4).replace(
      "<path",
      `<path transform="translate(0 ${LIP})"`,
    ),
    line("M2.04 9.23a13.4 13.4 0 0 1 19.92 0M5.01 11.91a9.4 9.4 0 0 1 13.98 0M7.99 14.59a5.4 5.4 0 0 1 8.02 0", "p", 2.4),
    part(ellipse(12, 18.2, 2.0, 2.0), "p", "s"),
  ].join(""),

  // license: a key (red bow with a cream hole, cream bit) lying over a small cream card
  license: [
    part(rrect(4.6, 2.8, 17.6, 13.0, 2.4), "n", "m"),
    rect(6.2, 4.4, 14.4, 9.8, 1.4, "c"),
    line("M8.4 7.2h8.2M8.4 9.8h5.4", "r", 1.4),
    `<g transform="rotate(-24 11 15)">`,
    `<path d="M9.2 13.8h9.4a1.1 1.1 0 0 1 1.1 1.1v2.6a.8.8 0 0 1-.8.8h-.5a.8.8 0 0 1-.8-.8v-.9h-1.0v1.3a.8.8 0 0 1-.8.8h-.5a.8.8 0 0 1-.8-.8v-1.3H9.2z" fill="{r}" transform="translate(0 ${LIP * 0.8})"/>`,
    `<path d="M9.2 13.8h9.4a1.1 1.1 0 0 1 1.1 1.1v2.6a.8.8 0 0 1-.8.8h-.5a.8.8 0 0 1-.8-.8v-.9h-1.0v1.3a.8.8 0 0 1-.8.8h-.5a.8.8 0 0 1-.8-.8v-1.3H9.2z" fill="{c}" stroke="{r}" stroke-width=".45"/>`,
    part(ellipse(6.8, 15.0, 4.4, 4.4), "p", "s"),
    `<circle cx="6.8" cy="15.0" r="1.7" fill="{c}"/>`,
    `</g>`,
  ].join(""),

  // payment: credit card (red) with a navy stripe and a cream chip
  payment: [
    part(rrect(1.6, 4.0, 20.8, 14.8, 2.6), "p", "s"),
    rect(1.6, 7.0, 20.8, 3.4, 0, "r"),
    rect(4.2, 12.6, 4.8, 3.6, 0.9, "c"),
    line("M12.2 15.2h3.2M17.0 15.2h2.8", "c", 1.5),
  ].join(""),

  // upload: thick red arrow pointing up, standing on a cream rounded bar
  upload: [
    part(rrect(3.5, 18.2, 17, 3.4, 1.7), "n", "m"),
    line("M12 14.8V3.8M6.8 8.8L12 3.6l5.2 5.2", "s", 3.2).replace(
      "<path",
      `<path transform="translate(0 ${LIP})"`,
    ),
    line("M12 14.8V3.8M6.8 8.8L12 3.6l5.2 5.2", "p", 3.2),
  ].join(""),

  // download: thick red arrow pointing down onto a cream rounded bar
  download: [
    part(rrect(3.5, 18.2, 17, 3.4, 1.7), "n", "m"),
    line("M12 3.6v11.0M6.8 9.8L12 15.0l5.2-5.2", "s", 3.2).replace(
      "<path",
      `<path transform="translate(0 ${LIP})"`,
    ),
    line("M12 3.6v11.0M6.8 9.8L12 15.0l5.2-5.2", "p", 3.2),
  ].join(""),

  // sync: two curved red arrows forming a circle around a cream dot
  sync: [
    `<circle cx="12" cy="11.5" r="3.4" fill="{r}" transform="translate(0 ${LIP * 0.7})"/>`,
    `<circle cx="12" cy="11.5" r="3.2" fill="{c}" stroke="{r}" stroke-width=".6"/>`,
    line("M4.8 10.2A7.4 7.4 0 0 1 16.8 6.2", "s", 2.8).replace("<path", `<path transform="translate(0 ${LIP})"`),
    line("M4.8 10.2A7.4 7.4 0 0 1 16.8 6.2", "p", 2.8),
    part("M19.0 3.6v5.2h-5.2z", "p", "s"),
    line("M19.2 12.8A7.4 7.4 0 0 1 7.2 16.8", "s", 2.8).replace("<path", `<path transform="translate(0 ${LIP})"`),
    line("M19.2 12.8A7.4 7.4 0 0 1 7.2 16.8", "p", 2.8),
    part("M5.0 19.4v-5.2h5.2z", "p", "s"),
  ].join(""),

  // backup: database-like cylinder (red) with a cream circular arrow on the front
  backup: [
    part("M3.5 5v14a8.5 2.8 0 0 0 17 0V5z", "p", "s"),
    `<ellipse cx="12" cy="5" rx="8.5" ry="2.8" fill="{s}"/><ellipse cx="12" cy="4.75" rx="7.6" ry="2.2" fill="{p}"/>`,
    line("M3.5 8.8a8.5 2.8 0 0 0 17 0", "n", 1.1),
    line("M14.8 12.2a3.6 3.6 0 1 0 .6 3.6", "c", 1.7),
    `<path d="M16.2 10.2v3.6h-3.6z" fill="{c}"/>`,
  ].join(""),

  // voice-profile: solid cream bust with the lip, plus a red waveform badge at the shoulder
  "voice-profile": [
    part(ellipse(10.0, 6.8, 3.8, 3.8), "n", "m"),
    part("M3.2 19.6c0-4.6 3.0-7.2 6.8-7.2s6.8 2.6 6.8 7.2z", "n", "m"),
    part(ellipse(17.2, 15.8, 5.0, 5.0), "p", "s"),
    line("M14.8 14.3v3.0M17.2 12.8v6.0M19.6 14.3v3.0", "c", 1.6),
  ].join(""),

  // video: red video camera body with a navy lens and a small cream record dot
  video: [
    part("M15.6 9.6l5.6-3.0a1.2 1.2 0 0 1 1.8 1.05v7.7a1.2 1.2 0 0 1-1.8 1.05l-5.6-3.0z", "p", "s"),
    rect(19.6, 8.2, 2.0, 6.6, 0.7, "r"),
    part(rrect(1.4, 5.0, 15.2, 13.0, 2.6), "p", "s"),
    rect(3.4, 7.6, 7.8, 7.8, 1.6, "r"),
    `<circle cx="13.8" cy="8.2" r="1.25" fill="{c}"/>`,
  ].join(""),

  // router: low wide rounded red box with side pipe ports, two thick rounded antennas standing up at the back, 4 status LEDs on front
  router: [
    part(rrect(0.5, 13.3, 23.0, 5.6, 2.8), "n", "m"),
    `<g transform="rotate(-8 7.3 12.0)">${part(rrect(6.0, 2.8, 2.6, 10.2, 1.3), "n", "m")}</g>`,
    `<g transform="rotate(8 16.7 12.0)">${part(rrect(15.4, 2.8, 2.6, 10.2, 1.3), "n", "m")}</g>`,
    rect(5.5, 10.7, 3.6, 2.0, 0.8, "n"),
    rect(14.9, 10.7, 3.6, 2.0, 0.8, "n"),
    part(rrect(3.5, 12.0, 17.0, 8.2, 2.6), "p", "s"),
    rect(5.5, 14.5, 13.0, 3.2, 1.6, "r"),
    ...[7.5, 10.5, 13.5, 16.5].map((x) => `<circle cx="${x}" cy="16.1" r=".95" fill="{c}"/>`),
  ].join(""),

  // modem: slim upright red box on a small foot with side pipe ports, cream round globe/line emblem at top and 4 vertical LEDs; no antennas
  modem: [
    part(rrect(3.5, 10.2, 17.0, 5.6, 2.8), "n", "m"),
    part(rrect(4.8, 18.7, 14.4, 2.8, 0.85), "n", "m"),
    part(rrect(6.8, 1.8, 10.4, 17.4, 2.4), "p", "s"),
    `<circle cx="12" cy="6.2" r="2.5" fill="none" stroke="{c}" stroke-width=".88"/>`,
    `<ellipse cx="12" cy="6.2" rx="1.1" ry="2.5" fill="none" stroke="{c}" stroke-width=".8"/>`,
    line("M9.5 6.2h5", "c", 0.8),
    ...[10.7, 12.9, 15.1, 17.3].map((y) => `<circle cx="12" cy="${y}" r=".9" fill="{c}"/>`),
  ].join(""),

  // caddy: compact red box with side pipe ports, navy front panel, official Caddy mark in cream, 3 status dots
  caddy: [
    part(rrect(0.5, 9.0, 23.0, 5.6, 2.8), "n", "m"),
    part(rrect(3.8, 3.2, 16.4, 16.6, 3), "p", "s"),
    rect(5.3, 4.7, 13.4, 10.8, 1.5, "r"),
    `<path data-mark="1" fill="{c}" transform="translate(6.9 5) scale(${10.2 / 24})" d="${(await Bun.file(new URL("./brands/caddy-mark.svg", import.meta.url)).text()).match(/ d="([^"]+)"/)![1]}"/>`,
    ...[9.6, 12, 14.4].map((x) => `<circle cx="${x}" cy="17.7" r=".75" fill="{c}"/>`),
  ].join(""),

  // certstore: upright red cabinet on cream foot with lower side ports, two drawers (top pulled well open with hero certificate card sticking out + big red seal & ribbon)
  certstore: [
    part(rrect(0.5, 12.6, 23.0, 5.2, 2.6), "n", "m"),
    part(rrect(4.4, 19.6, 15.2, 2.2, 1.0), "n", "m"),
    part(rrect(3.6, 1.4, 16.8, 18.6, 2.8), "p", "s"),
    `<circle cx="12" cy="2.65" r=".66" fill="{c}"/>`,
    rect(5.0, 6.8, 14.0, 4.5, 1.2, "r"),
    rect(5.8, 4.05, 12.4, 7.35, 1.05, "c"),
    `<path d="M8.1 7.45l-.82 2.4 1.12-.48.55.58.25-.72.25.72.55-.58 1.12.48-.82-2.4z" fill="{p}"/>`,
    `<circle cx="9.2" cy="6.65" r="1.75" fill="{p}"/>`,
    line("M12.2 5.75h4.4M12.2 7.4h4.4M12.2 9.05h3.0", "r", 1.05),
    rect(4.0, 10.55, 16.0, 4.15, 1.35, "s"),
    part(rrect(4.4, 10.9, 15.2, 3.2, 1.05), "p", "s").replace(`translate(0 ${LIP})`, "translate(0 .75)"),
    rect(9.1, 11.95, 5.8, 1.15, 0.57, "c"),
    rect(5.4, 15.1, 13.2, 3.8, 1.1, "r"),
    rect(6.0, 15.6, 12.0, 2.8, 0.75, "p"),
    rect(9.4, 16.45, 5.2, 1.1, 0.55, "c"),
  ].join(""),

  // dns: compact red box with side pipe ports, cream signpost on top (two arrow boards), navy recess with 3 address lines + 3 dots
  dns: [
    part(rrect(0.5, 13.5, 23.0, 5.6, 2.8), "n", "m"),
    rect(10.9, 0.7, 2.2, 10.9, 1.1, "n"),
    rect(9.9, 10.4, 4.2, 1.2, 0.6, "n"),
    part(
      "M11.5 1.7h6.5a.8.8 0 0 1 .56.23l1.5 0.97a.55.55 0 0 1 0 .8l-1.5 0.97a.8.8 0 0 1-.56.23h-6.5a.6.6 0 0 1-.6-.6V2.3a.6.6 0 0 1 .6-.6z",
      "n",
      "m",
    ).replace(`translate(0 ${LIP})`, "translate(0 .6)"),
    part(
      "M12.5 5.8H6.0a.8.8 0 0 0-.56.23l-1.5 0.97a.55.55 0 0 0 0 .8l1.5 0.97a.8.8 0 0 0 .56.23h6.5a.6.6 0 0 0 .6-.6V6.4a.6.6 0 0 0-.6-.6z",
      "n",
      "m",
    ).replace(`translate(0 ${LIP})`, "translate(0 .6)"),
    part(rrect(3.6, 11.2, 16.8, 10.2, 2.5), "p", "s"),
    rect(5.2, 12.5, 13.6, 5.7, 1.3, "r"),
    rect(6.6, 13.45, 9.6, 0.98, 0.49, "c"),
    rect(6.6, 14.86, 6.6, 0.98, 0.49, "c"),
    rect(6.6, 16.27, 8.2, 0.98, 0.49, "c"),
    ...[9.6, 12, 14.4].map((x) => `<circle cx="${x}" cy="19.8" r=".72" fill="{c}"/>`),
  ].join(""),

  // user: one person bust (cream/sand round head, red shoulders), alone
  user: [
    part(ellipse(12, 6.4, 4.3, 4.3), "n", "m"),
    part("M4.2 19.6c0-4.4 3.4-7.0 7.8-7.0s7.8 2.6 7.8 7.0a1.6 1.6 0 0 1-1.6 1.6H5.8a1.6 1.6 0 0 1-1.6-1.6z", "p", "s"),
  ].join(""),

  // key: chunky red key, round bow with a cream hole, a small cream/sand tag hanging from the bow
  key: (() => {
    const keyD =
      "M-4.72 -1.6h-8.28a1.1 1.1 0 0 0-1.1 1.1v3.7a.9.9 0 0 0 .9.9h1.4a.9.9 0 0 0 .9-.9V1.6h1.3v1.3a.9.9 0 0 0 .9.9h1.4a.9.9 0 0 0 .9-.9V1.6h1.68A5.0 5.0 0 1 0 -4.72 -1.6z"
    return [
      `<g transform="translate(0 ${LIP})"><g transform="translate(15.6 7.6) rotate(-36)"><path d="${keyD}" fill="{s}"/></g></g>`,
      `<g transform="translate(15.6 7.6) rotate(-36)"><path d="${keyD}" fill="{p}"/></g>`,
      `<circle cx="15.6" cy="7.6" r="2.2" fill="{c}"/>`,
      part(rrect(13.8, 13.4, 5.4, 7.2, 1.5), "n", "m"),
      rect(15.0, 16.5, 3.0, 2.8, 0.65, "r"),
      `<circle cx="16.5" cy="15.0" r=".7" fill="{r}"/>`,
      line("M15.8 8.9l.7 5.6", "m", 1.9).replace("<path", `<path transform="translate(0 .45)"`),
      line("M15.8 8.9l.7 5.6", "n", 1.7),
    ].join("")
  })(),

  // shield: upright red shield, cream rim, big cream check mark
  shield: [
    part(
      "M12 1.6c3.5 0 6.5.7 8.0 1.4a1.8 1.8 0 0 1 1.1 1.7c0 6.8-2.9 12.6-8.2 16.3a1.6 1.6 0 0 1-1.8 0C5.8 17.3 2.9 11.5 2.9 4.7A1.8 1.8 0 0 1 4.0 3.0c1.5-.7 4.5-1.4 8.0-1.4z",
      "p",
      "s",
    ),
    `<path d="M12 3.55c2.8 0 5.2.55 6.4 1.1a.9.9 0 0 1 .55.85c0 5.55-2.4 10.35-6.95 13.65C7.45 15.85 5.05 11.05 5.05 5.5a.9.9 0 0 1 .55-.85c1.2-.55 3.6-1.1 6.4-1.1z" fill="none" stroke="{c}" stroke-width="1.65" stroke-linejoin="round"/>`,
    line("M8.6 11.5l2.3 2.4 4.7-5.0", "c", 2.4),
  ].join(""),

  // firewall: device family box with side ports; front = brick wall (cream mortar lines on red), one light
  firewall: [
    part(rrect(0.5, 9.0, 23.0, 5.6, 2.8), "n", "m"),
    part(rrect(3.8, 3.2, 16.4, 16.6, 3), "p", "s"),
    rect(5.4, 4.8, 13.2, 13.4, 1.4, "c"),
    rect(6.15, 5.55, 5.45, 2.45, 0.55, "p"),
    rect(12.4, 5.55, 5.45, 2.45, 0.55, "p"),
    rect(6.15, 8.8, 2.5, 2.45, 0.55, "p"),
    rect(9.45, 8.8, 5.1, 2.45, 0.55, "p"),
    rect(15.35, 8.8, 2.5, 2.45, 0.55, "p"),
    rect(6.15, 12.05, 5.45, 2.45, 0.55, "p"),
    rect(12.4, 12.05, 5.45, 2.45, 0.55, "p"),
    rect(6.15, 15.3, 2.5, 2.45, 0.55, "p"),
    rect(9.45, 15.3, 5.1, 2.45, 0.55, "p"),
    rect(15.35, 15.3, 2.5, 2.45, 0.55, "r"),
    `<circle cx="16.6" cy="16.52" r=".78" fill="{c}"/>`,
  ].join(""),

  // cloud: clean chunky puffy red cloud (4 round lobes) with a flat cream/sand underside
  cloud: (() => {
    const lobes = [
      [5.4, 13.5, 3.6],
      [10.1, 9.6, 4.6],
      [15.5, 10.8, 3.7],
      [18.9, 13.7, 3.2],
    ] as const
    const meet = (
      [x1, y1, r1]: readonly [number, number, number],
      [x2, y2, r2]: readonly [number, number, number],
    ) => {
      const dx = x2 - x1
      const dy = y2 - y1
      const d = Math.hypot(dx, dy)
      const a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
      const h = Math.sqrt(Math.max(0, r1 * r1 - a * a))
      const mx = x1 + (a * dx) / d
      const my = y1 + (a * dy) / d
      // upper intersection (smaller y in SVG)
      const p1: [number, number] = [mx + (h * dy) / d, my - (h * dx) / d]
      const p2: [number, number] = [mx - (h * dy) / d, my + (h * dx) / d]
      return p1[1] < p2[1] ? p1 : p2
    }
    const yFlat = 15.8
    const x0 = lobes[0][0] - Math.sqrt(lobes[0][2] ** 2 - (yFlat - lobes[0][1]) ** 2)
    const xEnd = lobes[3][0] + Math.sqrt(lobes[3][2] ** 2 - (yFlat - lobes[3][1]) ** 2)
    const j01 = meet(lobes[0], lobes[1])
    const j12 = meet(lobes[1], lobes[2])
    const j23 = meet(lobes[2], lobes[3])
    const f = (n: number) => n.toFixed(2)
    const d = [
      `M${f(x0)} ${yFlat}`,
      `A${lobes[0][2]} ${lobes[0][2]} 0 0 1 ${f(j01[0])} ${f(j01[1])}`,
      `A${lobes[1][2]} ${lobes[1][2]} 0 0 1 ${f(j12[0])} ${f(j12[1])}`,
      `A${lobes[2][2]} ${lobes[2][2]} 0 0 1 ${f(j23[0])} ${f(j23[1])}`,
      `A${lobes[3][2]} ${lobes[3][2]} 0 0 1 ${f(xEnd)} ${yFlat}`,
      "Z",
    ].join("")
    return [part(rrect(2.55, 15.0, 18.85, 3.4, 1.7), "n", "m"), part(d, "p", "s").replace(`translate(0 ${LIP})`, "translate(0 .75)")].join("")
  })(),

  // container: generic shipping container, ribbed red box, cream/sand corner posts, two cream doors on the end
  container: [
    part(rrect(2.2, 5.0, 19.6, 13.4, 1.8), "p", "s"),
    part(rrect(1.3, 4.4, 2.4, 14.6, 1.0), "n", "m"),
    part(rrect(10.6, 4.6, 2.0, 14.2, 0.8), "n", "m"),
    part(rrect(20.3, 4.4, 2.4, 14.6, 1.0), "n", "m"),
    rect(4.1, 6.0, 6.1, 11.4, 0.85, "r"),
    rect(4.6, 6.5, 2.35, 10.4, 0.55, "c"),
    rect(7.35, 6.5, 2.35, 10.4, 0.55, "c"),
    line("M6.35 7.4v8.6M7.95 7.4v8.6M5.75 12.1h.6M7.95 12.1h.6", "m", 0.75),
    ...[13.6, 15.35, 17.1, 18.85].map((x) => rect(x, 6.6, 0.95, 10.2, 0.48, "s")),
  ].join(""),

  // cluster: three small identical red rounded cubes on one shared cream/sand base plate, joined by short pipes
  cluster: [
    part(rrect(1.6, 17.6, 20.8, 3.6, 1.8), "n", "m"),
    line("M12 6.2L6.4 14.2L17.6 14.2Z", "m", 2.4).replace("<path", `<path transform="translate(0 .7)"`),
    line("M12 6.2L6.4 14.2L17.6 14.2Z", "n", 2.4),
    ...(
      [
        [8.9, 3.3],
        [3.3, 11.3],
        [14.5, 11.3],
      ] as const
    ).map(([x, y]) => part(rrect(x, y, 6.2, 5.8, 1.6), "p", "s") + `<circle cx="${x + 1.8}" cy="${y + 1.8}" r=".65" fill="{c}"/>`),
  ].join(""),

  // vm: device family box with side ports; front = navy screen showing a small cream box (machine in a machine)
  vm: [
    part(rrect(0.5, 9.0, 23.0, 5.6, 2.8), "n", "m"),
    part(rrect(3.8, 3.2, 16.4, 16.6, 3), "p", "s"),
    rect(5.4, 4.8, 13.2, 13.4, 1.6, "r"),
    part(rrect(7.6, 7.1, 8.8, 8.2, 1.8), "c", "m").replace(`translate(0 ${LIP})`, "translate(0 .8)"),
    rect(8.9, 8.4, 6.2, 2.3, 0.8, "p"),
    `<circle cx="10.2" cy="9.55" r=".55" fill="{c}"/><circle cx="11.7" cy="9.55" r=".55" fill="{c}"/>`,
    rect(8.9, 12.2, 4.0, 1.2, 0.6, "r"),
  ].join(""),

  // cache: short 2-disk database cylinder with a big cream lightning bolt on its front
  cache: [
    part("M3.2 6.0v11.6a8.8 3.0 0 0 0 17.6 0V6.0z", "p", "s"),
    `<ellipse cx="12" cy="6.0" rx="8.8" ry="3.0" fill="{s}"/><ellipse cx="12" cy="5.75" rx="7.9" ry="2.35" fill="{p}"/>`,
    line("M3.2 11.8a8.8 3.0 0 0 0 17.6 0", "n", 1.2),
    `<path d="M13.2 7.8L8.4 13.4h3.2l-1.1 5.1 4.9-5.7h-3.2z" fill="{s}" transform="translate(0 .6)"/>`,
    `<path d="M13.2 7.8L8.4 13.4h3.2l-1.1 5.1 4.9-5.7h-3.2z" fill="{c}" stroke="{c}" stroke-width=".55" stroke-linejoin="round"/>`,
  ].join(""),

  // queue: low red base with a cream/sand channel/pipe on top holding three red rounded packets in a row
  queue: [
    part(rrect(4.0, 16.4, 16.0, 4.2, 1.7), "p", "s"),
    `<circle cx="10.7" cy="18.5" r=".72" fill="{c}"/><circle cx="13.3" cy="18.5" r=".72" fill="{c}"/>`,
    rect(6.2, 14.5, 11.6, 2.3, 0.6, "r"),
    part(rrect(1.0, 5.0, 22.0, 9.6, 4.8), "n", "m"),
    rect(3.4, 6.8, 17.2, 6.0, 2.6, "r"),
    ...[4.9, 9.9, 14.9].map((x) => part(rrect(x, 7.8, 4.2, 3.8, 1.1), "p", "s").replace(`translate(0 ${LIP})`, "translate(0 .65)")),
  ].join(""),

  // bucket: red pail with cream/sand rim and handle, two cream sheets sticking up out of it
  bucket: [
    line("M4.8 10.0V7.8a7.2 5.8 0 0 1 14.4 0v2.2", "m", 2.1).replace("<path", `<path transform="translate(0 .55)"`),
    line("M4.8 10.0V7.8a7.2 5.8 0 0 1 14.4 0v2.2", "n", 2.1),
    rect(5.2, 8.8, 13.6, 2.6, 0.8, "r"),
    `<rect x="10.5" y="5.4" width="5.8" height="5.8" rx="1.0" fill="{c}" stroke="{r}" stroke-width=".65"/>`,
    `<rect x="6.9" y="6.1" width="6.2" height="5.3" rx="1.0" fill="{c}" stroke="{r}" stroke-width=".65"/>`,
    line("M8.3 7.9h3.2M8.3 9.4h2.2", "r", 1.0),
    part("M4.7 11.6h14.6l-1.5 8.4a2.0 2.0 0 0 1-2.0 1.6H8.2a2.0 2.0 0 0 1-2.0-1.6z", "p", "s"),
    part(rrect(3.3, 9.6, 17.4, 2.6, 1.3), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .75)"),
  ].join(""),

  // api: device family box with side ports; navy screen with cream curly braces { }
  api: [
    part(rrect(0.5, 9.0, 23.0, 5.6, 2.8), "n", "m"),
    part(rrect(3.8, 3.2, 16.4, 16.6, 3), "p", "s"),
    rect(5.4, 4.8, 13.2, 13.4, 1.6, "r"),
    line(
      "M10.2 7.6h-.7a1.2 1.2 0 0 0-1.2 1.2v1.3c0 .65-.45 1.15-1.15 1.4.7.25 1.15.75 1.15 1.4v1.3a1.2 1.2 0 0 0 1.2 1.2h.7M13.8 7.6h.7a1.2 1.2 0 0 1 1.2 1.2v1.3c0 .65.45 1.15 1.15 1.4-.7.25-1.15.75-1.15 1.4v1.3a1.2 1.2 0 0 1-1.2 1.2h-.7",
      "c",
      1.85,
    ),
  ].join(""),

  // webhook: chunky upright red J-hook (with its eyelet) catching a navy globe with cream continents and meridians
  webhook: (() => {
    const f = (n: number) => n.toFixed(2)
    const [xSh, yEye, rEye, hw, rF] = [6.35, 4.65, 3.55, 1.85, 1.0]
    const dyF = Math.sqrt((rEye + rF) ** 2 - (hw + rF) ** 2)
    const [ux, uy] = [(hw + rF) / (rEye + rF), dyF / (rEye + rF)]
    const [rB, cyB] = [6.85, 13.15]
    const [cxB, ro, ri] = [xSh + rB, rB + hw, rB - hw]
    const tipA = (-20 * Math.PI) / 180
    const hookD = [
      `M${f(xSh + hw)} ${f(yEye + dyF)}`,
      `A${rF} ${rF} 0 0 1 ${f(xSh + rEye * ux)} ${f(yEye + rEye * uy)}`,
      `A${rEye} ${rEye} 0 1 0 ${f(xSh - rEye * ux)} ${f(yEye + rEye * uy)}`,
      `A${rF} ${rF} 0 0 1 ${f(xSh - hw)} ${f(yEye + dyF)}`,
      `L${f(xSh - hw)} ${f(cyB)}`,
      `A${ro} ${ro} 0 1 0 ${f(cxB + ro * Math.cos(tipA))} ${f(cyB + ro * Math.sin(tipA))}`,
      `A${hw} ${hw} 0 0 0 ${f(cxB + ri * Math.cos(tipA))} ${f(cyB + ri * Math.sin(tipA))}`,
      `A${ri} ${ri} 0 1 1 ${f(xSh + hw)} ${f(cyB)}Z`,
    ].join("")
    const [gx, gy, gr, lon0, lat0] = [cxB, cyB, 5.05, -8, 28]
    const d = Math.PI / 180
    const [l0, p0] = [lon0 * d, lat0 * d]
    const proj = (lon: number, lat: number) => {
      const [l, p] = [lon * d, lat * d]
      let x = Math.cos(p) * Math.sin(l - l0)
      let y = Math.cos(p0) * Math.sin(p) - Math.sin(p0) * Math.cos(p) * Math.cos(l - l0)
      const front = Math.sin(p0) * Math.sin(p) + Math.cos(p0) * Math.cos(p) * Math.cos(l - l0)
      if (front < 0) {
        const n = Math.hypot(x, y) || 1
        ;[x, y] = [x / n, y / n]
      }
      return [gx + gr * x, gy - gr * y] as const
    }
    const whMap = (polys: number[][][]) =>
      polys
        .filter((poly) => poly.length)
        .map((poly) => {
          const pts: (readonly [number, number])[] = []
          for (let k = 0; k < poly.length; k++) {
            const [a, b] = [poly[k], poly[(k + 1) % poly.length]]
            const m = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 2))
            for (let t = 0; t < m; t++) pts.push(proj(a[0] + ((b[0] - a[0]) * t) / m, a[1] + ((b[1] - a[1]) * t) / m))
          }
          return "M" + pts.map(([x, y]) => `${f(x)} ${f(y)}`).join("L") + "Z"
        })
        .join("")
    const greatCircle = (kind: "eq" | "mer", lonDeg = 0) => {
      let out = ""
      let pen = false
      for (let k = 0; k <= 120; k++) {
        const th = (k * 3 * Math.PI) / 180
        const [vx, vy, vz] =
          kind === "eq"
            ? [Math.cos(th), Math.sin(th), 0]
            : [Math.cos(th) * Math.cos(lonDeg * d), Math.cos(th) * Math.sin(lonDeg * d), Math.sin(th)]
        const x = -vx * Math.sin(l0) + vy * Math.cos(l0)
        const y = Math.cos(p0) * vz - Math.sin(p0) * (vx * Math.cos(l0) + vy * Math.sin(l0))
        const front = Math.sin(p0) * vz + Math.cos(p0) * (vx * Math.cos(l0) + vy * Math.sin(l0))
        if (front >= -0.02) {
          out += `${pen ? "L" : "M"}${f(gx + gr * x)} ${f(gy - gr * y)}`
          pen = true
        } else {
          pen = false
        }
      }
      return out
    }
    const gridD = greatCircle("eq") + greatCircle("mer", -30) + greatCircle("mer", 30)
    const whLand = whMap(Object.values(WORLD.land) as number[][][])
    const whSea = whMap(Object.values(WORLD.seas) as number[][][])
    return [
      `<path d="${hookD}" fill="{s}" transform="translate(0 ${LIP})"/>`,
      `<circle data-wh-ocean="1" cx="${f(gx)}" cy="${f(gy)}" r="${f(gr)}" fill="{r}"/>`,
      `<clipPath id="via-wh"><circle cx="${f(gx)}" cy="${f(gy)}" r="${f(gr)}"/></clipPath>`,
      `<g data-wh-globe="1" clip-path="url(#via-wh)">`,
      `<path d="${gridD}" fill="none" stroke="{c}" stroke-width=".78" stroke-linecap="round"/>`,
      `<path d="${whLand}" fill="{c}" fill-rule="nonzero"/>`,
      `<path d="${whSea}" fill="{r}"/>`,
      `</g>`,
      `<path d="${hookD}" fill="{p}"/>`,
      `<circle cx="${f(xSh)}" cy="${f(yEye)}" r="1.45" fill="{c}"/>`,
    ].join("")
  })(),

  // loadbalancer: device box with ONE cream port on the left and THREE cream ports fanning out on the right
  loadbalancer: [
    part(rrect(0.5, 8.9, 6.6, 5.4, 2.7), "n", "m"),
    `<g transform="rotate(-28 17.6 8.8)">${part(rrect(16.8, 7.25, 6.6, 3.1, 1.55), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .7)")}</g>`,
    part(rrect(17.4, 10.05, 6.1, 3.1, 1.55), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .7)"),
    `<g transform="rotate(28 17.6 14.4)">${part(rrect(16.8, 12.85, 6.6, 3.1, 1.55), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .7)")}</g>`,
    part(rrect(4.0, 3.2, 15.2, 16.6, 3), "p", "s"),
    rect(5.6, 4.8, 12.0, 13.4, 1.5, "r"),
    line("M7.9 11.5h3.1M11.0 11.5l3.6-3.4M11.0 11.5h3.8M11.0 11.5l3.6 3.4", "c", 1.55),
    `<circle cx="7.7" cy="11.5" r="1.0" fill="{c}"/><circle cx="14.9" cy="7.9" r="1.0" fill="{c}"/><circle cx="15.1" cy="11.5" r="1.0" fill="{c}"/><circle cx="14.9" cy="15.1" r="1.0" fill="{c}"/>`,
  ].join(""),

  // switch: low wide box, front = row of 8 small navy square ports with tiny cream lights; side ports
  switch: [
    part(rrect(0.4, 10.2, 23.2, 4.8, 2.4), "n", "m"),
    part(rrect(2.4, 7.6, 19.2, 9.6, 2.4), "p", "s"),
    ...[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
      const xc = +(4.825 + i * 2.05).toFixed(3)
      return [
        `<circle cx="${xc}" cy="10.05" r=".52" fill="{c}"/>`,
        rect(+(xc - 0.34).toFixed(3), 11.75, 0.68, 0.55, 0.15, "r"),
        rect(+(xc - 0.72).toFixed(3), 12.15, 1.44, 1.65, 0.28, "r"),
      ].join("")
    }),
  ].join(""),

  // cicd: full-width upright red infinity loop with a clear cream arrow head on the left lobe and a smaller second on the right lobe
  cicd: (() => {
    const yc = 11.75
    const phi = (53 * Math.PI) / 180
    const R = 4.25
    const sw = 3.25
    const cx = R / Math.sin(phi)
    const xt = (R * Math.cos(phi) ** 2) / Math.sin(phi)
    const yt = R * Math.cos(phi)
    const f = (n: number) => n.toFixed(2)
    const infD = `M${f(12 - xt)} ${f(yc + yt)}L${f(12 + xt)} ${f(yc - yt)}A${R} ${R} 0 1 1 ${f(12 + xt)} ${f(yc + yt)}L${f(12 - xt)} ${f(yc - yt)}A${R} ${R} 0 1 0 ${f(12 - xt)} ${f(yc + yt)}Z`
    const overSpanD = `M${f(12 - xt)} ${f(yc - yt)}L${f(12 + xt)} ${f(yc + yt)}`
    const overHaloD = `M${f(12 - xt - 0.8)} ${f(yc - yt - 1.06)}L${f(12 + xt + 0.8)} ${f(yc + yt + 1.06)}`
    const lobeArrow = (cxL: number, aDeg: number, sgn: number, sc: number, wh: number) => {
      const a = (aDeg * Math.PI) / 180
      const px = cxL + R * Math.cos(a)
      const py = yc + R * Math.sin(a)
      const rx = Math.cos(a)
      const ry = Math.sin(a)
      // SVG +y is down: sgn = 1 is CW on screen, sgn = -1 is CCW on screen
      const tx = -sgn * Math.sin(a)
      const ty = sgn * Math.cos(a)
      const pts: [number, number, number][] = [
        [px + 2.95 * sc * tx, py + 2.95 * sc * ty, 0.48 * sc],
        [px - 1.48 * sc * tx + wh * rx, py - 1.48 * sc * ty + wh * ry, 0.44 * sc],
        [px - 0.58 * sc * tx, py - 0.58 * sc * ty, 0.28 * sc],
        [px - 1.48 * sc * tx - wh * rx, py - 1.48 * sc * ty - wh * ry, 0.44 * sc],
      ]
      return (
        pts
          .map(([bx, by, rad], i) => {
            const [ax, ay] = pts[(i + pts.length - 1) % pts.length]
            const [cxp, cyp] = pts[(i + 1) % pts.length]
            const l1 = Math.hypot(ax - bx, ay - by)
            const l2 = Math.hypot(cxp - bx, cyp - by)
            const u1x = (ax - bx) / l1
            const u1y = (ay - by) / l1
            const u2x = (cxp - bx) / l2
            const u2y = (cyp - by) / l2
            const half = Math.acos(Math.max(-1, Math.min(1, u1x * u2x + u1y * u2y))) / 2
            const d = Math.min(rad / Math.tan(half), l1 * 0.44, l2 * 0.44)
            const t1x = bx + u1x * d
            const t1y = by + u1y * d
            const t2x = bx + u2x * d
            const t2y = by + u2y * d
            return `${i === 0 ? "M" : "L"}${f(t1x)} ${f(t1y)}Q${f(bx)} ${f(by)} ${f(t2x)} ${f(t2y)}`
          })
          .join("") + "Z"
      )
    }
    const arrow1D = lobeArrow(12 - cx, -82, 1, 1.0, 2.15)
    const arrow2D = lobeArrow(12 + cx, 48, -1, 0.72, 1.76)
    return [
      line(infD, "s", sw).replace("<path", `<path transform="translate(0 ${LIP})"`),
      line(infD, "p", sw),
      `<clipPath id="via-ci"><rect x="8.8" y="${f(yc - sw / 2)}" width="6.4" height="${f(sw + LIP * Math.cos(phi))}" transform="rotate(-53 12 ${yc})"/></clipPath>`,
      `<g clip-path="url(#via-ci)"><path d="${overHaloD}" fill="none" stroke="{s}" stroke-width="4.85"/><path d="${overHaloD}" transform="translate(0 ${LIP})" fill="none" stroke="{s}" stroke-width="${sw}"/></g>`,
      line(overSpanD, "p", sw),
      part(arrow1D, "c", "m").replace(`translate(0 ${LIP})`, "translate(0 .65)"),
      part(arrow2D, "c", "m").replace(`translate(0 ${LIP})`, "translate(0 .55)"),
    ].join("")
  })(),

  // monitoring: device family box with side ports; navy screen with a cream rising zig-zag pulse line
  monitoring: [
    part(rrect(0.5, 9.0, 23.0, 5.6, 2.8), "n", "m"),
    part(rrect(3.8, 3.2, 16.4, 16.6, 3), "p", "s"),
    rect(5.4, 4.8, 13.2, 13.4, 1.6, "r"),
    line("M7.2 14.6l2.9-3.9 2.2 2.4 4.3-5.2", "c", 2.1),
  ].join(""),

  // logs: upright paper scroll, red roll ends, cream sheet with short navy lines
  logs: [
    part(rrect(1.7, 2.9, 3.4, 3.8, 1.5), "p", "s"),
    part(rrect(18.9, 2.9, 3.4, 3.8, 1.5), "p", "s"),
    part(rrect(4.2, 2.3, 15.6, 17.8, 2.2), "n", "m"),
    rect(5.2, 6.2, 13.6, 12.2, 1.1, "c"),
    rect(4.2, 5.75, 15.6, 0.85, 0.42, "m"),
    line("M7.0 8.5h2.0M10.7 8.5h6.1M7.0 11.1h2.0M10.7 11.1h4.2M7.0 13.7h2.0M10.7 13.7h5.4M7.0 16.3h2.0M10.7 16.3h3.0", "r", 1.45),
    part(rrect(3.5, 18.0, 17.0, 2.9, 1.45), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .75)"),
  ].join(""),

  // bell: classic chunky red bell (dome + flared rim) with a cream clapper ball and a small cream dot badge
  bell: [
    part(ellipse(12, 19.3, 2.5, 2.2), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .8)"),
    line("M10.7 4.4V3.0a1.3 1.3 0 0 1 2.6 0v1.4", "p", 1.75),
    part(
      "M12 3.8c-3.8 0-6.4 2.6-6.4 6.5v2.3c0 1.5-.8 2.7-2.1 3.5a1.2 1.2 0 0 0 .62 2.22h15.76a1.2 1.2 0 0 0 .62-2.22c-1.3-.8-2.1-2.0-2.1-3.5v-2.3c0-3.9-2.6-6.5-6.4-6.5z",
      "p",
      "s",
    ),
    `<circle cx="17.3" cy="6.2" r="2.2" fill="{s}" transform="translate(0 .5)"/>`,
    `<circle cx="17.3" cy="6.2" r="2.2" fill="{c}"/>`,
  ].join(""),

  // search: chunky magnifying glass, red ring and handle, cream glass
  search: [
    line("M14.2 14.2l6.1 6.1", "s", 3.6).replace("<path", `<path transform="translate(0 ${LIP})"`),
    line("M14.2 14.2l6.1 6.1", "p", 3.6),
    part(ellipse(10.2, 9.8, 7.2, 7.2), "p", "s"),
    `<circle cx="10.2" cy="9.8" r="4.6" fill="{s}"/>`,
    `<circle cx="10.2" cy="10.1" r="4.45" fill="{c}"/>`,
  ].join(""),

  // trash: red rounded bin, cream lid, three vertical cream grooves
  trash: [
    part("M4.9 6.2h14.2l-1.2 13.2a2.2 2.2 0 0 1-2.2 2.0H8.3a2.2 2.2 0 0 1-2.2-2.0z", "p", "s"),
    rect(4.9, 6.5, 14.2, 1.3, 0.4, "r"),
    line("M9.6 4.8V3.2a1.2 1.2 0 0 1 1.2-1.2h2.4a1.2 1.2 0 0 1 1.2 1.2v1.6", "n", 1.8),
    part(rrect(3.4, 4.4, 17.2, 2.6, 1.3), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .75)"),
    rect(8.0, 9.8, 1.6, 9.0, 0.8, "c"),
    rect(11.2, 9.8, 1.6, 9.0, 0.8, "c"),
    rect(14.4, 9.8, 1.6, 9.0, 0.8, "c"),
  ].join(""),
}

const VAR = { p: "--via-p", s: "--via-s", n: "--via-n", m: "--via-m", r: "--via-r", c: "--via-c" }

/** Resolved SVG for one mode (used for PNG renders and the dark file). */
export function svgFor(name: string, mode: "light" | "dark") {
  const body = FLAT[name].replace(/\{(\w)\}/g, (_, k: Role) => ROLES[mode][k])
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">${body}</svg>`
}
/** Themeable SVG: CSS variables with the light edition as fallback. */
export function svgThemeable(name: string) {
  const body = FLAT[name].replace(/\{(\w)\}/g, (_, k: Role) => `var(${VAR[k]}, ${ROLES.light[k]})`)
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">${body}</svg>`
}

/**
 * Stamp: the flat twin in ONE colour (currentColor), recesses knocked out. Painting order
 * is kept, so a cream detail drawn on a dark recess comes back as ink. `badge` puts the
 * knocked-out icon inside a filled rounded square: the product sub-logo for app icons,
 * favicons, watermarks and documents.
 */
/** Details drawn in the same ink as the shape under them; a stamp knocks them out instead. */
const STAMP_KNOCKOUT: Record<string, (svg: string) => string> = {
  social: (svg) =>
    svg
      .replace(
        '<path d="M15.0 4.2h5.4a2.4 2.4 0 0 1 2.4 2.4v3.0a2.4 2.4 0 0 1-2.4 2.4h-4.6l-3.2 2.2V6.6a2.4 2.4 0 0 1 2.4-2.4z" fill="{m}"',
        '<path d="M15.0 4.2h5.4a2.4 2.4 0 0 1 2.4 2.4v3.0a2.4 2.4 0 0 1-2.4 2.4h-4.6l-3.2 2.2V6.6a2.4 2.4 0 0 1 2.4-2.4z" fill="{r}" stroke="{r}" stroke-width="1.6" stroke-linejoin="round"/><path d="M15.0 4.2h5.4a2.4 2.4 0 0 1 2.4 2.4v3.0a2.4 2.4 0 0 1-2.4 2.4h-4.6l-3.2 2.2V6.6a2.4 2.4 0 0 1 2.4-2.4z" fill="{m}"',
      )
      .replace(/(<circle cx="(?:15\.2|17\.7|20\.2)" cy="8\.1" r="1" fill=")\{p\}/g, "$1{r}"),
  transcribe: (svg) => svg.replace('stroke="{c}" stroke-width="1.45"', 'stroke="{r}" stroke-width="1.45"'),
  page: (svg) => svg.replace(rect(3.8, 3.35, 7.6, 0.85, 0.42, "c"), rect(3.8, 3.35, 7.6, 0.85, 0.42, "r")),
  notetaker: (svg) => svg.replace('stroke="{p}" stroke-width="1.15"', 'stroke="{r}" stroke-width="1.15"'),
  // one ink: cut a thin gap round each link where it passes in front, or the chain is one blob
  link: (svg) => {
    const halo = (role: string) => (m: string) =>
      m.replace(`stroke="{${role}}" stroke-width="2.6"`, `stroke="{r}" stroke-width="4"`) + m
    return svg
      .replace(/<rect [^>]*stroke="\{p\}" stroke-width="2\.6"[^>]*\/>/, halo("p"))
      .replace(/(<g clip-path="url\(#via-lk\)">)([\s\S]*?)(<\/g>)/, (_, a, b, c) =>
        a + b.replace(/<rect [^>]*stroke="\{n\}" stroke-width="2\.6"[^>]*\/>/, halo("n")) + c,
      )
  },
  // cream details drawn straight on the red body (W-140 twins) would vanish in one ink
  files: (svg) =>
    svg
      .replace('stroke="{c}" stroke-width="1.1"', 'stroke="{r}" stroke-width="1.1"')
      .replaceAll(/(<circle cx="(?:9\.2|14\.4)" cy="(?:16\.5|14\.1|18\.9)" r="1\.55" fill=")\{c\}/g, "$1{r}"),
  globe: (svg) => svg.replace('fill="{c}" fill-rule="nonzero" data-land="1"', 'fill="{r}" fill-rule="nonzero" data-land="1"'),
  config: (svg) =>
    svg
      .replace(/<path d="M[0-9. L]+Z" fill="\{m\}" transform="translate\(0 \.6\)"\/>/, "")
      .replace(/<path d="(M[0-9. L]+Z)" fill="\{c\}"\/>/, '<path d="$1" fill="{r}"/>')
      .replace('<circle cx="16.9" cy="17.6" r="1.25" fill="{p}"/>', '<circle cx="16.9" cy="17.6" r="1.25" fill="{c}"/>'),
  phone: (svg) =>
    svg
      .replaceAll('stroke="{p}"', 'stroke="{r}"')
      .replace(rect(9.7, 9.5, 4.6, 3.6, 0.8, "p"), rect(9.7, 9.5, 4.6, 3.6, 0.8, "r")),
  // W-140 publishing pack: one ink would merge these details into their body
  docker: (svg) => svg.replaceAll('fill="{p}" stroke="{c}" stroke-width=".35" paint-order="stroke"', 'fill="{r}"'),
  raspberrypi: (svg) =>
    svg
      .replace('<ellipse cx="12" cy="14.5" rx="5.8" ry="6.2" fill="{s}"/>', "")
      .replaceAll(/<circle cx="[^"]+" cy="[^"]+" r="[^"]+" fill="\{s\}"\/>/g, "")
      .replace('stroke="{s}" stroke-width=".6"', 'stroke="{r}" stroke-width=".6"')
      .replaceAll('stroke="{s}" stroke-width=".75"', 'stroke="{r}" stroke-width=".75"'),
  database: (svg) => svg.replaceAll('stroke="{n}"', 'stroke="{r}"').replaceAll('fill="{c}"', 'fill="{r}"'),
  error: (svg) => svg.replaceAll('stroke="{c}"', 'stroke="{r}"'),
  warning: (svg) => svg.replaceAll('fill="{c}"', 'fill="{r}"'),
  // socket rim + logo are red on the secondary socket: one ink, so cut them out
  "mcp-a": (svg) =>
    svg
      .replace(rect(13.4, 6, 2.8, 10.6, 1.1, "p"), rect(13.4, 6, 2.8, 10.6, 1.1, "r"))
      .replace(mark(16.4, 9.9, 5.4, "p"), mark(16.7, 10, 5.5, "r")),
  // 009 ecosystem gaps: cream details drawn straight on the red body
  tablet: (svg) => svg.replace('<circle cx="21.6" cy="11.4" r=".6" fill="{c}"/>', '<circle cx="21.6" cy="11.4" r=".6" fill="{r}"/>'),
  "browser-ext": (svg) => svg.replaceAll('fill="{c}"', 'fill="{r}"'),
  vscode: (svg) => svg.replaceAll('r=".75" fill="{c}"', 'r=".75" fill="{r}"'),
  mail: (svg) => svg.replaceAll('stroke="{c}"', 'stroke="{r}"'),
  calendar: (svg) =>
    svg
      .replace(rect(5.8, 3.2, 3.6, 1.8, 0.9, "c"), rect(5.8, 3.2, 3.6, 1.8, 0.9, "r"))
      .replace(rect(14.6, 3.2, 3.6, 1.8, 0.9, "c"), rect(14.6, 3.2, 3.6, 1.8, 0.9, "r"))
      .replace(rect(10.3, 9.6, 3.4, 3.2, 0.7, "p"), `<rect x="10.3" y="9.6" width="3.4" height="3.2" rx="0.7" fill="none" stroke="{r}" stroke-width=".9"/>`),
  "qr-pair": (svg) => svg.replaceAll('stroke="{c}"', 'stroke="{r}"'),
  license: (svg) => svg.replace('<circle cx="6.8" cy="15.0" r="1.7" fill="{c}"/>', '<circle cx="6.8" cy="15.0" r="1.7" fill="{r}"/>'),
  payment: (svg) => svg.replaceAll('fill="{c}"', 'fill="{r}"').replaceAll('stroke="{c}"', 'stroke="{r}"'),
  backup: (svg) => svg.replaceAll('stroke="{n}"', 'stroke="{r}"').replaceAll('stroke="{c}"', 'stroke="{r}"').replaceAll('fill="{c}"', 'fill="{r}"'),
  "voice-profile": (svg) =>
    svg
      .replace('<path d="M12.2 15.8', '<circle cx="17.2" cy="15.8" r="5.9" fill="{r}"/><path d="M12.2 15.8')
      .replaceAll('stroke="{c}"', 'stroke="{r}"'),
  video: (svg) => svg.replace('<circle cx="13.8" cy="8.2" r="1.25" fill="{c}"/>', '<circle cx="13.8" cy="8.2" r="1.25" fill="{r}"/>'),
  // 011 network icons: cream emblem + LEDs drawn straight on the red modem body
  modem: (svg) => svg.replaceAll('fill="{c}"', 'fill="{r}"').replaceAll('stroke="{c}"', 'stroke="{r}"'),
  // 012 caddy, certstore, dns: status dots, handles and seal drawn on same-ink surfaces
  caddy: (svg) => svg.replaceAll('cy="17.7" r=".75" fill="{c}"', 'cy="17.7" r=".75" fill="{r}"'),
  certstore: (svg) =>
    svg
      .replace('<circle cx="12" cy="2.65" r=".66" fill="{c}"/>', '<circle cx="12" cy="2.65" r=".66" fill="{r}"/>')
      .replace(rect(5.8, 4.05, 12.4, 7.35, 1.05, "c"), rect(5.2, 3.55, 13.6, 4.2, 1.35, "r") + rect(5.8, 4.05, 12.4, 7.35, 1.05, "c"))
      .replace('<circle cx="9.2" cy="6.65" r="1.75" fill="{p}"/>', '<circle cx="9.2" cy="6.65" r="1.75" fill="{r}"/>')
      .replace('2.4z" fill="{p}"', '2.4z" fill="{r}"')
      .replace(rect(4.0, 10.55, 16.0, 4.15, 1.35, "s"), rect(3.85, 10.4, 16.3, 4.55, 1.5, "r"))
      .replace(rect(9.1, 11.95, 5.8, 1.15, 0.57, "c"), rect(9.1, 11.95, 5.8, 1.15, 0.57, "r"))
      .replace(rect(9.4, 16.45, 5.2, 1.1, 0.55, "c"), rect(9.4, 16.45, 5.2, 1.1, 0.55, "r")),
  dns: (svg) => svg.replaceAll('cy="19.8" r=".72" fill="{c}"', 'cy="19.8" r=".72" fill="{r}"'),
  // 015 IT diagram icons, part A: knock out cream/lip details sitting straight on same-ink bodies
  key: (svg) =>
    svg
      .replace('<circle cx="15.6" cy="7.6" r="2.2" fill="{c}"/>', '<circle cx="15.6" cy="7.6" r="2.2" fill="{r}"/>')
      .replace(
        line("M15.8 8.9l.7 5.6", "m", 1.9).replace("<path", `<path transform="translate(0 .45)"`),
        line("M15.8 8.9l.7 5.6", "r", 3.1),
      ),
  shield: (svg) => svg.replaceAll('stroke="{c}"', 'stroke="{r}"'),
  firewall: (svg) => svg.replace(rect(5.4, 4.8, 13.2, 13.4, 1.4, "c"), rect(5.4, 4.8, 13.2, 13.4, 1.4, "r")),
  cloud: (svg) => svg.replace('transform="translate(0 .75)"', 'transform="translate(0 .75)" stroke="{r}" stroke-width="1.1"'),
  container: (svg) =>
    svg
      .replaceAll('stroke="{m}"', 'stroke="{r}"')
      .replaceAll('height="10.2" rx="0.48" fill="{s}"', 'height="10.2" rx="0.48" fill="{r}"'),
  cluster: (svg) =>
    svg
      .replaceAll('r=".65" fill="{c}"', 'r=".65" fill="{r}"')
      .replace(part(rrect(1.6, 17.6, 20.8, 3.6, 1.8), "n", "m"), rect(1.6, 17.1, 20.8, 1.0, 0.5, "r") + part(rrect(1.6, 17.9, 20.8, 3.4, 1.7), "n", "m")),
  vm: (svg) => svg.replace(rect(8.9, 8.4, 6.2, 2.3, 0.8, "p"), rect(8.9, 8.4, 6.2, 2.3, 0.8, "r")),
  cache: (svg) =>
    svg
      .replaceAll('stroke="{n}"', 'stroke="{r}"')
      .replace('<path d="M13.2 7.8L8.4 13.4h3.2l-1.1 5.1 4.9-5.7h-3.2z" fill="{s}" transform="translate(0 .6)"/>', "")
      .replace('fill="{c}" stroke="{c}"', 'fill="{r}" stroke="{r}"'),
  queue: (svg) =>
    svg
      .replaceAll('cy="18.5" r=".72" fill="{c}"', 'cy="18.5" r=".72" fill="{r}"')
      .replace(rect(6.2, 14.5, 11.6, 2.3, 0.6, "r"), rect(3.8, 14.6, 16.4, 2.1, 0.6, "r")),
  bucket: (svg) =>
    svg.replace(
      part(rrect(3.3, 9.6, 17.4, 2.6, 1.3), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .75)"),
      rect(3.3, 12.1, 17.4, 0.95, 0.45, "r") + part(rrect(3.3, 9.6, 17.4, 2.5, 1.25), "n", "m"),
    ),
  // 016 IT diagram icons, part B: knock out cream/lip details sitting straight on same-ink bodies
  webhook: (svg) =>
    svg
      .replace('<circle cx="6.35" cy="4.65" r="1.45" fill="{c}"/>', '<circle cx="6.35" cy="4.65" r="1.45" fill="{r}"/>')
      .replace(
        '<g data-wh-globe="1" clip-path="url(#via-wh)">',
        '<circle cx="13.20" cy="13.15" r="4.05" fill="none" stroke="{c}" stroke-width=".9"/><g transform="translate(13.20 13.15) scale(.82) translate(-13.20 -13.15)"><g data-wh-globe="1" clip-path="url(#via-wh)">',
      )
      .replace('</g><path d="M8.20', '</g></g><path d="M8.20'),
  switch: (svg) => svg.replaceAll('cy="10.05" r=".52" fill="{c}"', 'cy="10.05" r=".52" fill="{r}"'),
  cicd: (svg) =>
    svg
      .replace('stroke="{s}" stroke-width="4.85"', 'stroke="{r}" stroke-width="5.1"')
      .replaceAll(
        /<path d="(M[^"]+Z)" fill="\{m\}" transform="translate\(0 \.(?:65|55)\)"\/><path d="\1" fill="\{c\}"\/>/g,
        (_, d: string) =>
          `<path d="${d}" fill="{r}" stroke="{r}" stroke-width="1.35" stroke-linejoin="round"/>` +
          part(d, "c", "m").replace(`translate(0 ${LIP})`, "translate(0 .5)"),
      ),
  logs: (svg) =>
    svg
      .replace(rect(4.2, 5.75, 15.6, 0.85, 0.42, "m"), rect(4.2, 5.75, 15.6, 0.85, 0.42, "r"))
      .replace(
        part(rrect(3.5, 18.0, 17.0, 2.9, 1.45), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .75)"),
        rect(3.5, 17.25, 17.0, 0.85, 0.42, "r") + part(rrect(3.5, 18.0, 17.0, 2.9, 1.45), "n", "m").replace(`translate(0 ${LIP})`, "translate(0 .75)"),
      ),
  bell: (svg) =>
    svg
      .replace('<circle cx="17.3" cy="6.2" r="2.2" fill="{s}" transform="translate(0 .5)"/>', '<circle cx="17.3" cy="6.2" r="3.0" fill="{r}"/>')
      .replace('<path d="M12 3.8', '<rect x="8.6" y="18.6" width="6.8" height="1.2" rx=".6" fill="{r}"/><path d="M12 3.8'),
  search: (svg) =>
    svg
      .replace('<circle cx="10.2" cy="9.8" r="4.6" fill="{s}"/>', "")
      .replace('<circle cx="10.2" cy="10.1" r="4.45" fill="{c}"/>', '<circle cx="10.2" cy="9.8" r="4.5" fill="{r}"/>'),
  trash: (svg) => svg.replaceAll('height="9" rx="0.8" fill="{c}"', 'height="9" rx="0.8" fill="{r}"'),
}

export function stampSvg(name: string, badge = false) {
  const id = `st-${name}${badge ? "-b" : ""}`
  const ink = { p: "#fff", s: "#fff", n: "#fff", m: "#fff", c: "#fff", r: "#000" } as const
  const src = (STAMP_KNOCKOUT[name] ?? ((x: string) => x))(FLAT[name])
  const body = src.replace(/\{(\w)\}/g, (_, k: keyof typeof ink) => ink[k])
  if (!badge)
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><mask id="${id}" maskUnits="userSpaceOnUse" x="0" y="0" width="24" height="24"><rect width="24" height="24" fill="#000"/>${body}</mask><rect width="24" height="24" fill="currentColor" mask="url(#${id})"/></svg>`
  // badge: square in ink, icon (scaled to 70%) cut out of it, recess details back in ink
  const inv = body.replaceAll("#fff", "#tmp").replaceAll("#000", "#fff").replaceAll("#tmp", "#000")
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><mask id="${id}" maskUnits="userSpaceOnUse" x="0" y="0" width="24" height="24"><rect width="24" height="24" fill="#fff"/><g transform="translate(2.4 2.4) scale(.8)">${inv}</g></mask><rect width="24" height="24" rx="5.5" fill="currentColor" mask="url(#${id})"/></svg>`
}

if (import.meta.main) {
  const { values, positionals } = parseArgs({
    args: Bun.argv.slice(2),
    options: { out: { type: "string" }, pairs: { type: "string" } },
    allowPositionals: true,
  })
  const out = values.out ?? "local/icons/rounds/flat-r1"
  const names = positionals.length ? positionals : Object.keys(FLAT)
  for (const mode of ["light", "dark"] as const) {
    await mkdir(`${out}/${mode}`, { recursive: true })
    for (const name of names) {
      const svg = svgFor(name, mode)
      await Bun.write(`${out}/${mode}/${name}.svg`, svg)
      // 24-unit art on a 1024 canvas with the same 8% margin as the 2.5D set
      const art = await sharp(Buffer.from(svg), { density: (860 / 24) * 72 })
        .resize(860, 860)
        .png()
        .toBuffer()
      await sharp({
        create: {
          width: 1024,
          height: 1024,
          channels: 4,
          background: { r: 0, g: 0, b: 0, alpha: 0 },
        },
      })
        .composite([{ input: art, left: 82, top: 82 }])
        .png()
        .toFile(`${out}/${mode}/${name}.png`)
    }
  }
  await Bun.write(
    `${out}/themeable.json`,
    JSON.stringify(Object.fromEntries(names.map((n) => [n, svgThemeable(n)])), null, 2),
  )

  // pairs sheet: for every icon, 2.5D (best render) | flat at 200 px and at 24 px, both modes
  if (values.pairs) {
    const rounds = values.pairs.split(",")
    const cell = 220
    const tiles: sharp.OverlayOptions[] = []
    let row = 0
    for (const mode of ["light", "dark"] as const) {
      for (const [i, name] of names.entries()) {
        const x = i * cell
        const y = row * (cell * 2 + 20)
        let raster: string | null = null
        for (const r of rounds) {
          const p = `local/icons/rounds/${r}/${mode}/${name}.png`
          if (await Bun.file(p).exists()) {
            raster = p
            break
          }
        }
        if (raster)
          tiles.push({
            input: await sharp(raster).resize(190, 190).png().toBuffer(),
            left: x + 15,
            top: y + 10,
          })
        tiles.push({
          input: await sharp(`${out}/${mode}/${name}.png`).resize(150, 150).png().toBuffer(),
          left: x + 35,
          top: y + cell + 10,
        })
        tiles.push({
          input: await sharp(Buffer.from(svgFor(name, mode)), { density: 72 })
            .resize(24, 24)
            .png()
            .toBuffer(),
          left: x + 185,
          top: y + cell + 170,
        })
      }
      row++
    }
    const bg = (m: "light" | "dark") => (m === "light" ? "#F6F3EE" : "#0E1626")
    const W = names.length * cell
    const H = 2 * (cell * 2 + 20)
    const bands = [
      {
        input: {
          create: {
            width: W,
            height: cell * 2 + 20,
            channels: 4 as const,
            background: bg("light"),
          },
        },
        left: 0,
        top: 0,
      },
      {
        input: {
          create: { width: W, height: cell * 2 + 20, channels: 4 as const, background: bg("dark") },
        },
        left: 0,
        top: cell * 2 + 20,
      },
    ]
    await sharp({ create: { width: W, height: H, channels: 4, background: "#ffffff" } })
      .composite([...bands, ...tiles])
      .png()
      .toFile(`${out}/pairs.png`)
    console.log(`pairs ${out}/pairs.png`)
  }
  console.log(`flat ${names.length} icons → ${out}`)
}
