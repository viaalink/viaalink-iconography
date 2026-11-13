/**
 * Viaalink icon gallery — local review tool for the generated icon set.
 * Started by tools/icon-gallery/via.yaml (`via up` there), or:
 *   bun tools/icon-gallery/server.ts        (from the repo root)
 *
 * Reads local/icons/rounds/<round>/{light,dark}/*.png, prompts.json and critique.md,
 * and the shipped set in static/assets/icons/<style>/<mode>/ once it exists.
 * Feedback rounds (votes, comments, icon requests, the owner's verdicts) live in
 * local/icons/review/rounds/<round>.json (scripts/review/store.ts); verdicts are mirrored into
 * local/icons/reviews.json, which picks the main version of each icon.
 *
 * Roles, checked here on every write:
 *   reviewer  anyone who reached us: through the Relay that means past via's basic auth and the
 *             random /r/<slug>/ path; a display name in a cookie with a random reviewer id
 *   owner     the owner key cookie (/owner?key=...), or a direct request from this machine that did
 *             not come through a proxy (no X-Forwarded-*, Forwarded, X-Real-IP or Via header)
 */

import { randomBytes, timingSafeEqual } from "node:crypto"
import { chmod, readdir, readFile, stat } from "node:fs/promises"
import { join, resolve, sep } from "node:path"
import sharp from "sharp"
import { fitScale, ICON_SIZE } from "../../scripts/icons/canvas"
import { ICONS } from "../../scripts/icons/catalog"
import { FLAT, stampSvg, svgThemeable } from "../../scripts/icons/flat"
import { THEME, themePath } from "../../scripts/icons/theme"
import { CANON, DOLLS_ROUND, NOT_SHOWN, STYLE_EXT, snapshot, styleOf } from "../../scripts/review/snapshot"
import { isVerdict, ReviewError, repoStore, summarize, topByScore } from "../../scripts/review/store"
import { ITEM_KEY, ROUND_NAME } from "../../scripts/review/types"

const ROOT = resolve(import.meta.dir, "../..")
const ROUNDS = join(ROOT, "local/icons/rounds")
const SHIPPED = join(ROOT, "static/assets/icons")
const PORT = Number(process.env.ICON_GALLERY_PORT ?? 5330)
const MODES = ["light", "dark"] as const

const STORE = repoStore(ROOT).store
/** The gallery's .env (written by via from tpl.env): REVIEW_SLUG is the random path a proxied request needs. */
const GALLERY_ENV = join(resolve(process.env.REVIEW_GALLERY_DIR ?? import.meta.dir), ".env")

/**
 * The owner's key (local/icons/owner.key, gitignored, made on first start).
 * Opening /owner?key=<key> once sets an HttpOnly cookie, so the owner can
 * accept icons on the public site too; everyone else stays read-only.
 */
const OWNER_KEY_FILE = join(ROOT, "local/icons/owner.key")
const OWNER_COOKIE = "via_icon_owner"
async function ownerKey() {
  const f = Bun.file(OWNER_KEY_FILE)
  if (await f.exists()) return (await f.text()).trim()
  const key = randomBytes(24).toString("base64url")
  await Bun.write(OWNER_KEY_FILE, `${key}\n`)
  await chmod(OWNER_KEY_FILE, 0o600)
  return key
}
const OWNER_KEY = await ownerKey()
const sameKey = (k: string | null | undefined) =>
  !!k && k.length === OWNER_KEY.length && timingSafeEqual(Buffer.from(k), Buffer.from(OWNER_KEY))
const cookie = (req: Request, name: string) =>
  (req.headers.get("cookie") ?? "")
    .split(/;\s*/)
    .find((c) => c.startsWith(`${name}=`))
    ?.slice(name.length + 1)
const sameSecret = (a: string | null | undefined, b: string) =>
  !!a && a.length === b.length && timingSafeEqual(Buffer.from(a), Buffer.from(b))

type Server = { requestIP(req: Request): { address: string } | null }
const LOOPBACK = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"])
const PROXY_HEADERS = ["x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-real-ip", "forwarded", "via"]
/**
 * A request is local only when it comes straight from this machine: loopback peer, loopback Host,
 * and no proxy header at all. Caddy and the Relay always add X-Forwarded-* (via's routing rule), so
 * anything that came through them is never local, whatever IP the headers claim.
 */
function isDirectLocal(req: Request, server: Server): boolean {
  if (PROXY_HEADERS.some((h) => req.headers.has(h))) return false
  const host = (req.headers.get("host") ?? "").replace(/:\d+$/, "")
  if (host !== "127.0.0.1" && host !== "localhost" && host !== "[::1]") return false
  return LOOPBACK.has(server.requestIP(req)?.address ?? "")
}
const isOwner = (req: Request, server: Server) => sameKey(cookie(req, OWNER_COOKIE)) || isDirectLocal(req, server)

/** REVIEW_SLUG from the gallery's .env, re-read when the file changes (a rotation needs no restart). */
let slugCache = { mtime: -1, slug: "" }
async function currentSlug(): Promise<string> {
  const st = await stat(GALLERY_ENV).catch(() => null)
  if (!st) return process.env.REVIEW_SLUG ?? ""
  if (st.mtimeMs !== slugCache.mtime) {
    const m = (await readFile(GALLERY_ENV, "utf8")).match(/^\s*REVIEW_SLUG\s*=\s*["']?([\w-]+)/m)
    slugCache = { mtime: st.mtimeMs, slug: m?.[1] ?? "" }
  }
  return slugCache.slug
}
const SLUG_COOKIE = "via_icon_round"
const REVIEWER_COOKIE = "via_icon_reviewer"

async function exists(p: string) {
  return stat(p).then(
    () => true,
    () => false,
  )
}
async function dirs(p: string) {
  if (!(await exists(p))) return []
  return (await readdir(p, { withFileTypes: true })).filter((d) => d.isDirectory()).map((d) => d.name)
}

/** A "set" is a round directory or a shipped style directory; both hold <mode>/<name>.png. */
async function listSets() {
  const rounds = (await dirs(ROUNDS)).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
  const sets = []
  for (const id of rounds) {
    const base = join(ROUNDS, id)
    const meta = (await exists(join(base, "prompts.json")))
      ? JSON.parse(await readFile(join(base, "prompts.json"), "utf8"))
      : {}
    const critique = (await exists(join(base, "critique.md"))) ? await readFile(join(base, "critique.md"), "utf8") : ""
    sets.push({
      id: `round:${id}`,
      label: id,
      kind: "round",
      icons: await icons(base),
      meta,
      critique,
    })
  }
  for (const style of await dirs(SHIPPED)) {
    const base = join(SHIPPED, style)
    sets.push({
      id: `shipped:${style}`,
      label: `shipped ${style}`,
      kind: "shipped",
      icons: await icons(base),
      meta: {},
      critique: "",
    })
  }
  return sets
}

async function icons(base: string) {
  const out: Record<string, { modes: string[]; raw: boolean }> = {}
  for (const mode of MODES) {
    const d = join(base, mode)
    if (!(await exists(d))) continue
    for (const f of await readdir(d)) {
      if (!f.endsWith(".png") || f.endsWith(".raw.png")) continue
      const name = f.slice(0, -4)
      out[name] ??= { modes: [], raw: false }
      out[name].modes.push(mode)
      if (await exists(join(d, `${name}.raw.png`))) out[name].raw = true
    }
  }
  return out
}

const loadReviews = () => STORE.legacyReviews()

/** Resolve /img/<round|shipped>/<id>/<mode>/<file> inside its root, refusing traversal. */
function imagePath(parts: string[]): string | null {
  const [kind, id, mode, file] = parts
  if (!id || !mode || !file || !/^[\w.-]+\.(png|svg)$/.test(file)) return null
  const root = kind === "round" ? ROUNDS : kind === "shipped" ? SHIPPED : null
  if (!root) return null
  const p = resolve(root, id, mode, file)
  return p.startsWith(root + sep) ? p : null
}

/** Round directory a resolved icon path came from (null for the shipped set). */
const roundOf = (p: string | null) => (p?.startsWith(ROUNDS + sep) ? p.slice(ROUNDS.length + 1).split(sep)[0] : null)

/** Every icon: the version each style shows now (main, per mode) and every other version, light and dark. */
async function approval() {
  const reviews = await loadReviews()
  const names = [...new Set([...ICONS.map((i) => i.name), ...Object.keys(FLAT)])]
  const rounds = (await dirs(ROUNDS)).sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))
  const out = []
  for (const name of names) {
    const row: Record<string, unknown> = { name }
    for (const [style, ext] of [
      ["25d", "png"],
      ["flat", "svg"],
    ] as const) {
      const main = {
        dark: roundOf(await bestIcon("dark", name, style, ext)),
        light: roundOf(await bestIcon("light", name, style, ext)),
      }
      const history = []
      for (const round of rounds.filter((r) => r.startsWith(`${style}-`)))
        for (const mode of ["dark", "light"] as const) {
          if (!(await exists(join(ROUNDS, round, mode, `${name}.${ext}`)))) continue
          const key = `round:${round}/${mode}/${name}`
          history.push({ round, mode, key, ext, main: round === main[mode], review: reviews[key] ?? null })
        }
      row[style] = history.length ? { main, history } : null
    }
    out.push(row)
  }
  return out
}

/**
 * The best version of one icon: newest approved review for that mode, else the
 * newest round (by round number) that has it, else the shipped set.
 */
async function bestIcon(
  mode: string,
  name: string,
  style: "25d" | "flat" = "25d",
  ext: "png" | "svg" = "png",
): Promise<string | null> {
  if (!/^(light|dark)$/.test(mode) || !/^[\w-]+$/.test(name)) return null
  // W-140: the Blender build (25d) and the newest flat round are the source of truth now;
  // older approved AI renders only fill in for names those rounds don't have yet.
  const canon = style === "25d" ? BLENDER_ROUND : FLAT_ROUND
  const cp = imagePath(["round", canon, mode, `${name}.${ext}`])
  if (cp && (await exists(cp))) return cp
  // rounds are named <style>-r<n>[-topic]; each style resolves only its own rounds
  const ofStyle = (round: string) => round.startsWith(`${style}-`)
  const approved = Object.entries(await loadReviews())
    .filter(
      ([k, r]) =>
        r.status === "approved" && k.startsWith("round:") && ofStyle(k.slice(6)) && k.endsWith(`/${mode}/${name}`),
    )
    .sort((a, b) => b[1].at.localeCompare(a[1].at))
  for (const [k] of approved) {
    const p = imagePath(["round", k.slice(6).split("/")[0], mode, `${name}.${ext}`])
    if (p && (await exists(p))) return p
  }
  const rounds = (await dirs(ROUNDS)).filter(ofStyle).sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))
  for (const r of rounds) {
    const p = imagePath(["round", r, mode, `${name}.${ext}`])
    if (p && (await exists(p))) return p
  }
  const p = imagePath(["shipped", style, mode, `${name}.${ext}`])
  if (p && (await exists(p))) return p
  return null
}

/** The brand colours the gallery pages share (--red, --navy, ...), from the theme; injected after each
 *  page's own :root block, so a theme change recolours the gallery without editing the HTML. */
const P = THEME.prompt.palette
const THEME_CSS = `<style id="theme">:root{--red:${P.red};--red-deep:${P.redDeep};--coral:${P.coral};--navy:${P.navy};--deep:${P.navyDeep};--slate:${P.slate};--cream:${P.cream}}</style>`
const page = async (f: string) =>
  new Response((await Bun.file(join(import.meta.dir, f)).text()).replace("</head>", `${THEME_CSS}</head>`), {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-cache" },
  })

/**
 * One row per icon/scene/doll, no duplicates: is the 2.5D done in Blender (canonical round
 * 25d-b7, dolls in 25d-b8-dolls) or still an AI render to convert, and does a flat twin exist?
 * Rejected AI variants and superseded experiments are left out.
 */
const BLENDER_ROUND = CANON["25d"]
const FLAT_ROUND = CANON.flat
async function overview() {
  const pngs = async (round: string) =>
    new Set(
      (await readdir(join(ROUNDS, round, "dark")).catch(() => [] as string[]))
        .filter((f) => f.endsWith(".png") && !f.endsWith(".raw.png"))
        .map((f) => f.slice(0, -4)),
    )
  const blender = await pngs(BLENDER_ROUND)
  const dolls = await pngs(DOLLS_ROUND)
  const names = [...new Set([...ICONS.map((i) => i.name), ...Object.keys(FLAT), ...blender])].filter(
    (n) => !NOT_SHOWN.has(n),
  )
  const rows = names.sort().map((name) => ({
    name,
    kind: name.startsWith("scene-") ? "scene" : "icon",
    blender: blender.has(name),
    flat: name in FLAT,
  }))
  for (const d of [...dolls].sort()) rows.push({ name: d, kind: "doll", blender: true, flat: false })
  const diagrams = (await readdir(join(ROOT, "local/icons/diagrams")).catch(() => [] as string[])).sort()
  return { blenderRound: BLENDER_ROUND, dollsRound: DOLLS_ROUND, rows, diagrams }
}

/**
 * Scene step labels (W-140): diagram.py writes labels.json in the coordinates of the raw render
 * (local/icons/scenes/<name>/light.png); the gallery shows the normalised square from the round.
 * Map every point through the same steps as canvas.ts squareIcon: trim the transparent border,
 * fit inside the margin box, centre on the square.
 */
async function sceneLabels(name: string) {
  const dir = join(ROOT, "local/icons/scenes", name)
  const lj = join(dir, "labels.json")
  if (!(await exists(lj))) return { labels: [] }
  const j = JSON.parse(await readFile(lj, "utf8"))
  const raw = join(dir, "light.png")
  if (!(await exists(raw))) return { labels: [] }
  const meta = await sharp(raw).metadata()
  const { info } = await sharp(raw)
    .ensureAlpha()
    .trim({ background: { r: 0, g: 0, b: 0, alpha: 0 }, threshold: THEME.canvas.trimThreshold })
    .toBuffer({ resolveWithObject: true })
  const W = meta.width ?? 0,
    H = meta.height ?? 0
  const left = -(info.trimOffsetLeft ?? 0),
    top = -(info.trimOffsetTop ?? 0)
  const k = fitScale(info.width, info.height, ICON_SIZE, false)
  const ox = (ICON_SIZE - Math.round(info.width * k)) / 2,
    oy = (ICON_SIZE - Math.round(info.height * k)) / 2
  const px = (x: number) => (ox + (x * W - left) * k) / ICON_SIZE
  const py = (y: number) => (oy + (y * H - top) * k) / ICON_SIZE
  const pt = (p: number[]) => [px(p[0]), py(p[1])]
  const r4 = (v: number) => Math.round(v * 1e4) / 1e4
  type Lab = { x: number; y: number; tx?: number; ty?: number; lead?: number[]; flead?: number[] }
  const labels = j.labels.map((l: Lab) => ({
    ...l,
    x: r4(px(l.x)),
    y: r4(py(l.y)),
    ...(l.tx !== undefined ? { tx: r4(px(l.tx)), ty: r4(py(l.ty ?? 0)) } : {}),
    ...(l.lead ? { lead: pt(l.lead).map(r4) } : {}),
    ...(l.flead ? { flead: pt(l.flead).map(r4) } : {}),
  }))
  return { ...j, aspect: 1, labels }
}

/** Animation proofs (just icons-animate <name>): local/icons/anim/<name>/<name>.{mp4,gif}. */
const ANIM = join(ROOT, "local/icons/anim")
async function animationsPage() {
  const dirs = (await exists(ANIM)) ? (await readdir(ANIM)).sort() : []
  const cards: string[] = []
  for (const d of dirs) {
    if (!/^[\w-]+$/.test(d)) continue
    const files = await readdir(join(ANIM, d)).catch(() => [] as string[])
    const mp4 = files.find((f) => f.endsWith(".mp4"))
    const gif = files.find((f) => f.endsWith(".gif"))
    const shown = mp4 ?? gif
    if (!shown) continue
    const when = new Date((await stat(join(ANIM, d, shown))).mtimeMs).toISOString().slice(0, 16).replace("T", " ")
    cards.push(
      `<figure>${
        mp4
          ? `<video src="/anim/${d}/${mp4}" autoplay loop muted playsinline></video>`
          : `<img src="/anim/${d}/${gif}" alt="${d}">`
      }<figcaption><b>${d}</b> · ${when}${mp4 ? ` · <a href="/anim/${d}/${mp4}" download>mp4</a>` : ""}${
        gif ? ` · <a href="/anim/${d}/${gif}" download>gif</a>` : ""
      }</figcaption></figure>`,
    )
  }
  return new Response(
    `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Animations</title>
<style>body{margin:0;background:${THEME.gallery.background};color:${THEME.gallery.ink};font:15px/1.5 system-ui,sans-serif}.wrap{max-width:1200px;margin:0 auto;padding:16px}
nav{display:flex;gap:16px;align-items:center;margin-bottom:16px}nav a{color:inherit}figure{margin:0 0 32px}
video,img{width:100%;height:auto;border-radius:12px;background:${THEME.gallery.background};display:block}figcaption{margin-top:6px}a{color:${THEME.gallery.link}}</style></head>
<body><div class="wrap"><nav><a href="/"><b>&gt;${THEME.brand.cliWord}</b> icons</a><a href="/overview">Overview</a><a href="/animations">Animations</a><a href="/gallery">All rounds</a></nav>
<h1>Animations</h1><p>Proofs rendered from the Blender scenes with <code>just icons-animate &lt;name&gt;</code>. Each loops seamlessly.</p>
${cards.join("\n") || "<p>No animations yet.</p>"}</div></body></html>`,
    { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-cache" } },
  )
}

// ---------------------------------------------------------------- feedback rounds

const json = (data: unknown, status = 200) => Response.json(data, { status, headers: { "cache-control": "no-store" } })
const fail = (status: number, message: string) => json({ error: message }, status)

/**
 * Writes must be same-origin JSON: a cross-site form cannot send application/json, and a browser
 * that says where the request came from must say it came from this page.
 */
function writeGuard(req: Request): Response | null {
  if (!req.headers.get("content-type")?.startsWith("application/json")) return fail(415, "json only")
  if (Number(req.headers.get("content-length") ?? 0) > 32_000) return fail(413, "too large")
  if (req.headers.get("sec-fetch-site") === "cross-site") return fail(403, "cross-site")
  const origin = req.headers.get("origin")
  if (origin) {
    const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host")
    let ok = false
    try {
      ok = new URL(origin).host === host
    } catch {}
    if (!ok) return fail(403, "cross-origin")
  }
  return null
}

type Who = { id: string; name: string; owner: boolean }
async function whoIs(req: Request, server: Server): Promise<{ owner: boolean; who: Who | null }> {
  const owner = isOwner(req, server)
  const rid = cookie(req, REVIEWER_COOKIE)
  const name = await STORE.reviewerName(rid)
  if (rid && name) return { owner, who: { id: rid, name, owner } }
  return { owner, who: owner ? { id: "owner", name: "Owner", owner: true } : null }
}

/** One round as the page needs it; reviewer ids never leave the server (only "mine" flags). */
async function roundView(name: string | null, me: { owner: boolean; who: Who | null }) {
  const all = await STORE.list()
  const r = name ? await STORE.get(name) : await STORE.current()
  const rounds = all.map((x) => ({ name: x.name, status: x.status, feed: x.feed, createdAt: x.createdAt }))
  const meOut = { name: me.who && me.who.id !== "owner" ? me.who.name : null, owner: me.owner }
  if (!r) return { round: null, rounds, me: meOut }
  const legacy = await STORE.legacyReviews()
  const mine = me.who?.id
  const icons = r.icons.map((i) => ({
    name: i.name,
    images: Object.entries(i.images).flatMap(([style, modes]) =>
      Object.entries(modes).map(([mode, key]) => {
        const [, round, , n] = (key ?? "").match(ITEM_KEY) ?? []
        return {
          style,
          mode,
          key,
          url: `/img/round/${round}/${mode}/${n}.${STYLE_EXT[styleOf(round)]}`,
          votes: summarize(r.votes[key ?? ""]),
          mine: mine ? (r.votes[key ?? ""]?.[mine]?.value ?? 0) : 0,
          verdict: r.verdicts[key ?? ""] ?? null,
          earlier: legacy[key ?? ""] ? { verdict: legacy[key ?? ""].status, note: legacy[key ?? ""].note } : null,
        }
      }),
    ),
  }))
  return {
    round: { name: r.name, status: r.status, feed: r.feed, createdAt: r.createdAt, closedAt: r.closedAt ?? null },
    rounds,
    me: meOut,
    icons,
    comments: r.comments.map(({ reviewer, ...c }) => ({ ...c, mine: !!mine && reviewer === mine })),
    requests: r.requests.map(({ reviewer, ...q }) => ({ ...q, mine: !!mine && reviewer === mine })),
    top: topByScore(r, 10),
  }
}

async function reviewApi(req: Request, url: URL, server: Server): Promise<Response | null> {
  if (!url.pathname.startsWith("/api/review/")) return null
  const me = await whoIs(req, server)
  const route = url.pathname.slice("/api/review/".length)
  try {
    if (req.method === "GET" && route === "round") return json(await roundView(url.searchParams.get("round"), me))
    if (req.method !== "POST") return fail(405, "method not allowed")
    const guard = writeGuard(req)
    if (guard) return guard
    const body = (await req.json().catch(() => null)) as Record<string, unknown> | null
    if (!body || typeof body !== "object") return fail(400, "bad json")
    const str = (k: string) => (typeof body[k] === "string" ? (body[k] as string) : "")
    if (route === "me") {
      const r = await STORE.setReviewer(cookie(req, REVIEWER_COOKIE), str("name"))
      const secure = PROXY_HEADERS.some((h) => req.headers.has(h)) ? "; Secure" : ""
      return new Response(JSON.stringify({ name: r.name }), {
        headers: {
          "content-type": "application/json",
          "set-cookie": `${REVIEWER_COOKIE}=${r.id}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000${secure}`,
        },
      })
    }
    // ---- owner only
    if (route === "verdict" || route === "round-state") {
      if (!me.owner) return fail(403, "only the owner can do this")
      if (route === "verdict") {
        const v = body.verdict === null ? null : body.verdict
        if (v !== null && !isVerdict(v)) return fail(400, "bad verdict")
        await STORE.setVerdict(str("round"), str("key"), v, str("note"))
        return json({ ok: true })
      }
      const name = str("round")
      if (!ROUND_NAME.test(name)) return fail(400, "bad round name")
      if (body.action === "close") await STORE.close(name, typeof body.feed === "boolean" ? body.feed : undefined)
      else if (body.action === "open") await STORE.open(name, await snapshot(ROUNDS), body.feed === true)
      else return fail(400, "action is open or close")
      return json({ ok: true })
    }
    // ---- reviewers (anyone past basic auth) with a display name
    if (!me.who) return fail(401, "enter your name first")
    if (route === "vote") {
      await STORE.vote(str("round"), str("key"), me.who, Number(body.value), str("comment"))
      return json({ ok: true })
    }
    if (route === "comment") {
      await STORE.comment(str("round"), me.who, {
        icon: str("icon"),
        text: str("text"),
        parentId: str("parentId") || undefined,
        item: str("item") || undefined,
      })
      return json({ ok: true })
    }
    if (route === "comment-delete") {
      await STORE.deleteComment(str("round"), str("id"), me.who)
      return json({ ok: true })
    }
    if (route === "request") {
      await STORE.request(str("round"), me.who, { name: str("name"), shows: str("shows") })
      return json({ ok: true })
    }
    return fail(404, "unknown")
  } catch (e) {
    if (e instanceof ReviewError) return fail(e.status, e.message)
    console.error(e)
    return fail(500, "server error")
  }
}

const notFound = () => new Response("not found", { status: 404 })

/**
 * The share link is random on purpose: through the Relay (any proxied request) the first hit must be
 * /r/<REVIEW_SLUG>/..., which sets a cookie and redirects to the page; later requests need that
 * cookie. Without it the gallery answers 404, so a guessed host alone shows nothing. Direct local
 * requests skip this. A rotated slug invalidates old links and cookies.
 */
async function slugGate(req: Request, url: URL, server: Server): Promise<Response | null> {
  if (isDirectLocal(req, server)) return null
  const slug = await currentSlug()
  if (!slug) return notFound()
  const m = url.pathname.match(/^\/r\/([\w-]+)(\/.*)?$/)
  if (m) {
    if (!sameSecret(m[1], slug)) return notFound()
    return new Response(null, {
      status: 303,
      headers: {
        location: `${m[2] ?? "/approve"}${url.search}`,
        "set-cookie": `${SLUG_COOKIE}=${slug}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`,
      },
    })
  }
  return sameSecret(cookie(req, SLUG_COOKIE), slug) ? null : notFound()
}

Bun.serve({
  port: PORT,
  hostname: "127.0.0.1",
  async fetch(req, server) {
    const url = new URL(req.url)
    const gate = await slugGate(req, url, server)
    if (gate) return gate
    const review = await reviewApi(req, url, server)
    if (review) return review
    if (url.pathname === "/") return page("showcase.html")
    if (url.pathname === "/gallery") return page("index.html")
    if (url.pathname === "/approve") return page("approve.html")
    if (url.pathname === "/versions") return page("versions.html")
    if (url.pathname === "/overview") return page("overview.html")
    if (url.pathname === "/animations") return animationsPage()
    const an = url.pathname.match(/^\/anim\/([\w-]+)\/([\w-]+\.(?:mp4|gif))$/)
    if (an && (await exists(join(ANIM, an[1], an[2]))))
      return new Response(Bun.file(join(ANIM, an[1], an[2])), { headers: { "cache-control": "no-cache" } })
    // the brand fonts the pages ask for, served from the theme's own font files (no website needed)
    if (url.pathname === "/fonts/fonts.css")
      return new Response(
        `@font-face{font-family:"IBM Plex Mono";font-weight:100 900;src:url(/fonts/mono.ttf) format("truetype")}\n` +
          `@font-face{font-family:"Space Grotesk";font-weight:100 900;src:url(/fonts/sans.ttf) format("truetype")}\n`,
        { headers: { "content-type": "text/css", "cache-control": "max-age=3600" } },
      )
    if (url.pathname === "/fonts/mono.ttf" || url.pathname === "/fonts/sans.ttf")
      return new Response(
        Bun.file(themePath(url.pathname.endsWith("mono.ttf") ? THEME.fonts.mono : THEME.fonts.sans)),
        {
          headers: { "content-type": "font/ttf", "cache-control": "max-age=86400" },
        },
      )
    if (url.pathname === "/zoom.js")
      return new Response(Bun.file(join(import.meta.dir, "zoom.js")), {
        headers: { "content-type": "text/javascript", "cache-control": "no-cache" },
      })
    if (url.pathname === "/api/overview") return Response.json(await overview())
    const dg = url.pathname.match(/^\/diagram\/([\w-]+)\/(light\.png|dark\.png|labels\.json)$/)
    if (dg) {
      const p = join(ROOT, "local/icons/diagrams", dg[1], dg[2])
      if (await exists(p)) return new Response(Bun.file(p), { headers: { "cache-control": "no-cache" } })
    }
    const sc = url.pathname.match(/^\/scene\/(scene-[\w-]+)\/labels\.json$/)
    if (sc) return Response.json(await sceneLabels(sc[1]))
    if (url.pathname === "/owner") {
      if (!sameKey(url.searchParams.get("key"))) return new Response("wrong key", { status: 403 })
      return new Response(null, {
        status: 303,
        headers: {
          location: "/approve",
          "cache-control": "no-store",
          "set-cookie": `${OWNER_COOKIE}=${OWNER_KEY}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=31536000`,
        },
      })
    }
    if (url.pathname === "/api/approval") return Response.json(await approval())
    const font = url.pathname.match(/^\/fonts\/([\w.-]+\.(?:css|woff2))$/)
    if (font) {
      const p = join(ROOT, "static/fonts", font[1])
      if (await exists(p)) return new Response(Bun.file(p))
    }
    if (url.pathname === "/api/config") return Response.json({ readonly: !isOwner(req, server) })
    if (url.pathname === "/api/sets") return Response.json(await listSets())
    // Iconify JSON of the flat set (prefix "via"): Mermaid architecture-beta,
    // Excalidraw/tldraw importers and @iconify/* all read this format.
    if (url.pathname === "/iconify/via.json") {
      const icons = Object.fromEntries(
        Object.keys(FLAT).map((n) => [n, { body: svgThemeable(n).replace(/^<svg[^>]*>|<\/svg>$/g, "") }]),
      )
      return Response.json(
        { prefix: "via", width: 24, height: 24, icons },
        { headers: { "access-control-allow-origin": "*", "cache-control": "no-cache" } },
      )
    }
    if (url.pathname === "/api/reviews" && req.method === "GET") return Response.json(await loadReviews())
    if (url.pathname === "/api/reviews" && req.method === "POST") {
      if (!isOwner(req, server)) return new Response("only the owner can do this", { status: 403 })
      const guard = writeGuard(req)
      if (guard) return guard
      const body = (await req.json()) as { key: string; status?: string | null; note?: string }
      if (!body.key || !ITEM_KEY.test(body.key)) return new Response("bad key", { status: 400 })
      if (body.status && !isVerdict(body.status)) return new Response("bad status", { status: 400 })
      return Response.json(await STORE.writeLegacy(body.key, isVerdict(body.status) ? body.status : null, body.note))
    }
    // /icon/<mode>/<name>.png → 2.5D · /flat/<mode>/<name>.(png|svg) → flat twin
    // /stamp/<name>.svg (one colour, currentColor) · /stamp/<name>-badge.svg (sub-logo badge)
    const st = url.pathname.match(/^\/stamp\/([\w-]+?)(-badge)?\.svg$/)
    if (st && FLAT[st[1]])
      return new Response(stampSvg(st[1], !!st[2]), {
        headers: { "content-type": "image/svg+xml", "cache-control": "no-cache" },
      })
    const best = url.pathname.match(/^\/(icon|flat)\/(light|dark)\/([\w-]+)\.(png|svg)$/)
    if (best && !(best[1] === "icon" && best[4] === "svg")) {
      const style = best[1] === "flat" ? "flat" : "25d"
      // design phase renders dark only (owner: dark reads well on light too),
      // so a light request falls back to the dark edition
      const p =
        (await bestIcon(best[2], best[3], style, best[4] as "png" | "svg")) ??
        (await bestIcon("dark", best[3], style, best[4] as "png" | "svg"))
      if (p) return new Response(Bun.file(p), { headers: { "cache-control": "no-cache" } })
    }
    if (url.pathname.startsWith("/img/")) {
      const p = imagePath(url.pathname.slice(5).split("/").map(decodeURIComponent))
      if (p && (await exists(p))) return new Response(Bun.file(p), { headers: { "cache-control": "no-cache" } })
    }
    return new Response("not found", { status: 404 })
  },
})
console.log(`icon gallery on http://127.0.0.1:${PORT}`)
