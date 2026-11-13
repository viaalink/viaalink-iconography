/**
 * Live end-to-end test of a feedback round over the REAL shared link (HTTPS through the Relay, basic auth,
 * random slug), clicking through the page as a reviewer. Run while a round is open and shared:
 *   just review-test-live <round> <base-url>     e.g. just review-test-live live-test https://icons-<slug>.<relay domain>
 * Reads the credentials from tools/icon-gallery/.env, never prints them. Writes test votes/comments into the round.
 */
import { chromium, expect } from "@playwright/test"

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
const ROUND = process.argv[2] ?? "live-test"
const HOST = (process.argv[3] ?? "").replace(/\/$/, "")
let pass = 0,
  fail = 0
const step = async (name: string, fn: () => Promise<void>) => {
  try {
    await fn()
    pass++
    console.log("PASS ", name)
  } catch (e) {
    fail++
    console.log("FAIL ", name, String(e).split("\n")[0].slice(0, 160))
  }
}
const b = await chromium.launch()
const c = await b.newContext({
  httpCredentials: { username: env.REVIEW_USER, password: env.REVIEW_PASSWORD },
  viewport: { width: 1280, height: 900 },
})
const p = await c.newPage()
await step("open the shared link (real HTTPS, basic auth, random slug)", async () => {
  await p.goto(`${HOST}/r/${env.REVIEW_SLUG}/approve?round=${ROUND}`, { waitUntil: "networkidle" })
  await expect(p.locator("#nameform")).toBeVisible()
})
await step("enter a name in the form", async () => {
  await p.locator("#name").fill("UI reviewer")
  await p.locator("#nameform button.primary").click()
  await expect(p.getByText("You are")).toBeVisible()
})
const up = p.locator('button[data-vote="1"]').nth(2),
  down = p.locator('button[data-vote="-1"]').nth(2)
await step("click 👍: the button turns pressed", async () => {
  await up.click()
  await expect(p.locator('button[data-vote="1"]').nth(2)).toHaveAttribute("aria-pressed", "true")
})
await step("click 👎: a comment is required before it counts", async () => {
  await down.click()
  await expect(p.locator('[data-act="send-down"]').first()).toBeVisible()
  await p.screenshot({ path: `${S}/4-down-needs-comment.png` })
  const box = p.locator("textarea:visible").first()
  await box.fill("UI test: the tray edge disappears on dark")
  await p.locator('[data-act="send-down"]').first().click()
  await expect(p.locator('button[data-vote="-1"]').nth(2)).toHaveAttribute("aria-pressed", "true")
})
await step("the 👎 comment shows in the thread", async () => {
  await expect(p.getByText("UI test: the tray edge disappears on dark").first()).toBeVisible()
})
await step("owner controls are not shown to a reviewer", async () => {
  await expect(p.locator('[data-act="close-round"]')).toHaveCount(0)
})
await p.screenshot({ path: `${S}/5-ui-after.png`, fullPage: false })
await b.close()
console.log(`\n${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)
