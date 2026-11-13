/**
 * Live end-to-end test of a feedback round over the REAL shared link (HTTPS through the Relay, basic auth,
 * random slug), as a reviewer, plus the owner on this machine. Run while a round is open and shared:
 *   just review-test-live <round> <base-url>     e.g. just review-test-live live-test https://icons-<slug>.<relay domain>
 * Reads the credentials from tools/icon-gallery/.env, never prints them. Writes test votes/comments into the round.
 */
import { chromium } from "@playwright/test"

const G = new URL("../tools/icon-gallery/.env", import.meta.url).pathname
const S = new URL("../local/icons/review/shots", import.meta.url).pathname
const env = Object.fromEntries(
  (await Bun.file(G).text())
    .split("\n")
    .filter((l) => /^REVIEW_/.test(l))
    .map((l) => {
      const i = l.indexOf("=")
      return [l.slice(0, i), l.slice(i + 1).replace(/^["']|["']$/g, "")]
    }),
)
const slug = env.REVIEW_SLUG,
  user = env.REVIEW_USER,
  pass = env.REVIEW_PASSWORD
const ROUND = process.argv[2] ?? "live-test"
const HOST = (process.argv[3] ?? "").replace(/\/$/, "")
if (!HOST.startsWith("https://")) throw new Error("usage: live-review.ts <round> <https base url of the share>")
const res: [string, boolean, string][] = []
const ok = (name: string, cond: boolean, info = "") => {
  res.push([name, cond, info])
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}  ${info}`)
}
const b = await chromium.launch()
// 1. no login -> 401
{
  const c = await b.newContext()
  const p = await c.newPage()
  const r = await p.goto(`${HOST}/r/${slug}/approve?round=${ROUND}`)
  ok("no login is refused", r?.status() === 401, String(r?.status()))
  await c.close()
}
// 2. wrong password -> 401
{
  const c = await b.newContext({ httpCredentials: { username: user, password: "wrong" } })
  const p = await c.newPage()
  const r = await p.goto(`${HOST}/r/${slug}/approve?round=${ROUND}`)
  ok("wrong password is refused", r?.status() === 401, String(r?.status()))
  await c.close()
}
// 3. login but wrong slug -> 404
{
  const c = await b.newContext({ httpCredentials: { username: user, password: pass } })
  const p = await c.newPage()
  const r = await p.goto(`${HOST}/r/000000000000/approve?round=${ROUND}`)
  ok("wrong slug gives 404", r?.status() === 404, String(r?.status()))
  await c.close()
}
// 4. reviewer full cycle over real HTTPS
const c = await b.newContext({
  httpCredentials: { username: user, password: pass },
  viewport: { width: 1280, height: 900 },
})
const p = await c.newPage()
const r = await p.goto(`${HOST}/r/${slug}/approve?round=${ROUND}`, { waitUntil: "networkidle" })
ok(
  "reviewer opens the shared link over HTTPS",
  (r?.status() ?? 0) < 400,
  `${r?.status()} ${p.url().replace(slug, "<slug>")}`,
)
await p.screenshot({ path: `${S}/1-open.png` })
const api = async (path: string, body: unknown) =>
  p.evaluate(
    async ([path, body]) => {
      const r = await fetch(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      })
      return { s: r.status, t: (await r.text()).slice(0, 160) }
    },
    [path, body] as const,
  )
const view = await p.evaluate(async (round) => (await fetch(`/api/review/round?round=${round}`)).json(), ROUND)
const key = view?.icons?.[0]?.images?.[0]?.key,
  icon = view?.icons?.[0]?.name
ok("round view loads over HTTPS", !!key, `${view?.icons?.length} icons`)
let x = await api("/api/review/me", { name: "Playwright reviewer" })
ok("reviewer sets a name", x.s < 300, String(x.s))
x = await api("/api/review/vote", { round: ROUND, key, value: 1 })
ok("reviewer votes up", x.s < 300, String(x.s))
x = await api("/api/review/vote", { round: ROUND, key, value: -1 })
ok("down vote without comment is refused", x.s === 422, String(x.s))
x = await api("/api/review/vote", {
  round: ROUND,
  key,
  value: -1,
  comment: "Edge is too thin at 48 px (Playwright test)",
})
ok("down vote with comment", x.s < 300, String(x.s))
x = await api("/api/review/comment", { round: ROUND, icon, text: "Live HTTPS test comment" })
ok("reviewer comments", x.s < 300, String(x.s))
x = await api("/api/review/request", {
  round: ROUND,
  name: "test-icon",
  shows: "A test request from the live Playwright run",
})
ok("reviewer requests an icon", x.s < 300, String(x.s))
x = await api("/api/review/verdict", { round: ROUND, key, verdict: "approved" })
ok("reviewer cannot set a verdict (owner only)", x.s === 403, String(x.s))
x = await api("/api/review/round-state", { round: ROUND, action: "close" })
ok("reviewer cannot close the round", x.s === 403, String(x.s))
await p.reload({ waitUntil: "networkidle" })
await p.screenshot({ path: `${S}/2-after-review.png` })
const m = await b.newContext({
  httpCredentials: { username: user, password: pass },
  viewport: { width: 390, height: 844 },
})
const mp = await m.newPage()
await mp.goto(`${HOST}/r/${slug}/approve?round=${ROUND}`, { waitUntil: "networkidle" })
await mp.screenshot({ path: `${S}/3-mobile.png` })
ok(
  "mobile has no horizontal overflow",
  await mp.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
)
await m.close()
await c.close()
// 5. owner locally sets the verdict, then the reviewer sees it over HTTPS
{
  const oc = await b.newContext()
  const op = await oc.newPage()
  await op.goto(`http://127.0.0.1:5330/approve?round=${ROUND}`)
  const o = await op.evaluate(
    async ([round, key]) => {
      const r = await fetch("/api/review/verdict", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ round, key, verdict: "needs-work", note: "Live test: thicken the edge" }),
      })
      return r.status
    },
    [ROUND, key] as const,
  )
  ok("owner sets a verdict locally", o < 300, String(o))
  await oc.close()
}
{
  const c2 = await b.newContext({ httpCredentials: { username: user, password: pass } })
  const p2 = await c2.newPage()
  await p2.goto(`${HOST}/r/${slug}/approve?round=${ROUND}`, { waitUntil: "networkidle" })
  const v = await p2.evaluate(async (round) => (await fetch(`/api/review/round?round=${round}`)).json(), ROUND)
  const img = (v.icons as { images: { key: string }[] }[]).flatMap((i) => i.images).find((i) => i.key === key)
  ok("reviewer sees the owner's verdict over HTTPS", JSON.stringify(img ?? {}).includes("needs-work"), "")
  await c2.close()
}
await b.close()
const failed = res.filter((r) => !r[1]).length
console.log(`\n${res.length - failed} passed, ${failed} failed`)
process.exit(failed ? 1 : 0)
