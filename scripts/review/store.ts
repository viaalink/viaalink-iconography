/**
 * Feedback rounds: the file store. One JSON file per round under <dir>/rounds/<name>.json, a reviewer
 * name book in <dir>/reviewers.json, and the legacy verdict file (local/icons/reviews.json) kept in sync
 * so the gallery's "main version" logic sees the owner's verdicts.
 *
 *   const store = new ReviewStore({ dir: "local/icons/review", legacy: "local/icons/reviews.json" })
 *
 * Every method validates its input and throws a ReviewError with an HTTP status, so a server can
 * pass the error straight on. Roles are NOT checked here: the caller decides who may call what.
 */
import { randomBytes } from "node:crypto"
import { mkdir, readdir, readFile, rename, stat } from "node:fs/promises"
import { join } from "node:path"
import {
  type Comment,
  type IconRequest,
  ITEM_KEY,
  type ItemKey,
  type LegacyReviews,
  ROUND_NAME,
  type Round,
  type RoundIcon,
  VERDICTS,
  type Verdict,
  type VoteSummary,
} from "./types"

export class ReviewError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

const LIMITS = { name: 40, text: 2000, note: 2000, iconName: 60 }
export const newId = () => randomBytes(9).toString("base64url")
const now = () => new Date().toISOString()

/** Drop control characters except tab and newline. */
const stripControl = (v: string) =>
  [...v]
    .filter((ch) => {
      const c = ch.charCodeAt(0)
      return c === 9 || c === 10 || (c >= 32 && c !== 127)
    })
    .join("")

function clean(v: unknown, max: number, what: string, required = true): string {
  const s = typeof v === "string" ? stripControl(v).trim() : ""
  if (required && !s) throw new ReviewError(400, `${what} is required`)
  if (s.length > max) throw new ReviewError(400, `${what} is longer than ${max} characters`)
  return s
}

async function exists(p: string) {
  return stat(p).then(
    () => true,
    () => false,
  )
}

/** Write JSON atomically (temp file + rename), so a crash never leaves half a round. */
async function writeJson(file: string, data: unknown) {
  const tmp = `${file}.${process.pid}.tmp`
  await Bun.write(tmp, `${JSON.stringify(data, null, 2)}\n`)
  await rename(tmp, file)
}

export function summarize(votes: Record<string, { value: 1 | -1 }> | undefined): VoteSummary {
  const all = Object.values(votes ?? {})
  const up = all.filter((v) => v.value === 1).length
  const down = all.filter((v) => v.value === -1).length
  return { up, down, score: up - down, voters: all.length }
}

export class ReviewStore {
  readonly dir: string
  readonly roundsDir: string
  readonly legacy?: string
  /** Writes run one after another (single server process), so read-modify-write never interleaves. */
  private queue: Promise<unknown> = Promise.resolve()

  constructor(opts: { dir: string; legacy?: string }) {
    this.dir = opts.dir
    this.roundsDir = join(opts.dir, "rounds")
    this.legacy = opts.legacy
  }

  private serial<T>(fn: () => Promise<T>): Promise<T> {
    const run = this.queue.then(fn, fn)
    this.queue = run.catch(() => {})
    return run
  }

  private file(name: string) {
    if (!ROUND_NAME.test(name)) throw new ReviewError(400, "bad round name")
    return join(this.roundsDir, `${name}.json`)
  }

  async list(): Promise<Round[]> {
    if (!(await exists(this.roundsDir))) return []
    const out: Round[] = []
    for (const f of (await readdir(this.roundsDir)).filter((f) => f.endsWith(".json")))
      out.push(JSON.parse(await readFile(join(this.roundsDir, f), "utf8")))
    return out.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  }

  async get(name: string): Promise<Round> {
    const f = this.file(name)
    if (!(await exists(f))) throw new ReviewError(404, `no round ${name}`)
    return JSON.parse(await readFile(f, "utf8"))
  }

  /** Newest open round, else newest round, else null. */
  async current(): Promise<Round | null> {
    const all = await this.list()
    return all.find((r) => r.status === "open") ?? all[0] ?? null
  }

  private async mutate(name: string, fn: (r: Round) => void | Promise<void>, allowClosed = false) {
    return this.serial(async () => {
      const r = await this.get(name)
      if (r.status !== "open" && !allowClosed) throw new ReviewError(409, `round ${name} is closed`)
      await fn(r)
      await writeJson(this.file(name), r)
      return r
    })
  }

  /** A new round from a snapshot of icons; an existing round with that name is reopened, not replaced. */
  async open(name: string, icons: RoundIcon[], feed = false): Promise<Round> {
    return this.serial(async () => {
      const f = this.file(name)
      await mkdir(this.roundsDir, { recursive: true })
      if (await exists(f)) {
        const r: Round = JSON.parse(await readFile(f, "utf8"))
        r.status = "open"
        delete r.closedAt
        await writeJson(f, r)
        return r
      }
      for (const i of icons)
        for (const modes of Object.values(i.images))
          for (const k of Object.values(modes)) if (!k || !ITEM_KEY.test(k)) throw new ReviewError(400, `bad item ${k}`)
      const r: Round = {
        version: 1,
        name,
        status: "open",
        feed,
        createdAt: now(),
        icons,
        votes: {},
        comments: [],
        requests: [],
        verdicts: {},
      }
      await writeJson(f, r)
      return r
    })
  }

  /** Freeze a round: no more votes, comments, requests or verdicts until it is reopened. */
  close(name: string, feed?: boolean) {
    return this.mutate(
      name,
      (r) => {
        r.status = "closed"
        r.closedAt = now()
        if (feed !== undefined) r.feed = feed
      },
      true,
    )
  }

  private requireItem(r: Round, key: string): { icon: string } {
    if (!ITEM_KEY.test(key)) throw new ReviewError(400, "bad item key")
    for (const i of r.icons)
      for (const modes of Object.values(i.images)) if (Object.values(modes).includes(key)) return { icon: i.name }
    throw new ReviewError(404, "item is not in this round")
  }

  /** +1, -1 (needs a comment: it becomes the reason) or 0 (take the vote back). */
  vote(
    round: string,
    key: ItemKey,
    who: { id: string; name: string; owner: boolean },
    value: number,
    comment?: string,
  ) {
    return this.mutate(round, (r) => {
      const { icon } = this.requireItem(r, key)
      if (![1, -1, 0].includes(value)) throw new ReviewError(400, "vote is 1, -1 or 0")
      r.votes[key] ??= {}
      if (value === 0) {
        delete r.votes[key][who.id]
        return
      }
      if (value === -1) {
        const text = clean(comment, LIMITS.text, "a comment with a thumbs down", false)
        if (text.length < 3) throw new ReviewError(422, "a thumbs down needs a comment: what should change?")
        const c: Comment = {
          id: newId(),
          icon,
          item: key,
          reviewer: who.id,
          name: who.name,
          owner: who.owner,
          text,
          at: now(),
          down: true,
        }
        r.comments.push(c)
        r.votes[key][who.id] = { value: -1, at: c.at, commentId: c.id }
        return
      }
      r.votes[key][who.id] = { value: 1, at: now() }
    })
  }

  comment(
    round: string,
    who: { id: string; name: string; owner: boolean },
    input: { icon: string; text: string; parentId?: string; item?: string },
  ) {
    return this.mutate(round, (r) => {
      const icon = clean(input.icon, LIMITS.iconName, "icon")
      if (!r.icons.some((i) => i.name === icon)) throw new ReviewError(404, "icon is not in this round")
      if (input.item) this.requireItem(r, input.item)
      if (input.parentId && !r.comments.some((c) => c.id === input.parentId && c.icon === icon))
        throw new ReviewError(400, "unknown parent comment")
      r.comments.push({
        id: newId(),
        icon,
        ...(input.item ? { item: input.item } : {}),
        ...(input.parentId ? { parentId: input.parentId } : {}),
        reviewer: who.id,
        name: who.name,
        owner: who.owner,
        text: clean(input.text, LIMITS.text, "comment"),
        at: now(),
      })
    })
  }

  /** Reviewers delete their own comments; the owner may delete anyone's. A down vote loses its reason, so it goes too. */
  deleteComment(round: string, id: string, who: { id: string; owner: boolean }) {
    return this.mutate(round, (r) => {
      const c = r.comments.find((x) => x.id === id)
      if (!c) throw new ReviewError(404, "no such comment")
      if (c.reviewer !== who.id && !who.owner) throw new ReviewError(403, "not your comment")
      const gone = new Set([id])
      // replies go with their parent
      for (let grew = true; grew; ) {
        grew = false
        for (const x of r.comments)
          if (x.parentId && gone.has(x.parentId) && !gone.has(x.id)) {
            gone.add(x.id)
            grew = true
          }
      }
      r.comments = r.comments.filter((x) => !gone.has(x.id))
      for (const votes of Object.values(r.votes))
        for (const [rid, v] of Object.entries(votes)) if (v.commentId && gone.has(v.commentId)) delete votes[rid]
    })
  }

  request(round: string, who: { id: string; name: string }, input: { name: string; shows: string }) {
    return this.mutate(round, (r) => {
      const req: IconRequest = {
        id: newId(),
        name: clean(input.name, LIMITS.iconName, "icon name"),
        shows: clean(input.shows, LIMITS.text, "what it should show"),
        reviewer: who.id,
        by: who.name,
        at: now(),
      }
      r.requests.push(req)
    })
  }

  /** The owner's verdict on one item (null clears it). Mirrored into the legacy reviews file. */
  async setVerdict(round: string, key: ItemKey, verdict: Verdict | null, note = "") {
    const r = await this.mutate(round, (r) => {
      this.requireItem(r, key)
      if (verdict !== null && !VERDICTS.includes(verdict)) throw new ReviewError(400, "bad verdict")
      if (verdict === null) delete r.verdicts[key]
      else r.verdicts[key] = { verdict, note: clean(note, LIMITS.note, "note", false), at: now() }
    })
    await this.writeLegacy(key, verdict, note)
    return r
  }

  async legacyReviews(): Promise<LegacyReviews> {
    if (!this.legacy || !(await exists(this.legacy))) return {}
    return JSON.parse(await readFile(this.legacy, "utf8"))
  }

  /**
   * The legacy file the gallery already reads: approving one version of an icon makes it the main one,
   * so any other approved version of the same style, mode and name loses that status.
   */
  writeLegacy(key: ItemKey, status: Verdict | null, note = "") {
    return this.serial(async () => {
      if (!this.legacy) return {}
      const all = await this.legacyReviews()
      if (status === "approved") {
        const [, round, mode, name] = key.match(ITEM_KEY) ?? []
        const style = round?.split("-")[0]
        for (const [k, rv] of Object.entries(all))
          if (
            rv.status === "approved" &&
            k !== key &&
            k.startsWith(`round:${style}-`) &&
            k.endsWith(`/${mode}/${name}`)
          )
            delete all[k]
      }
      if (!status) delete all[key]
      else all[key] = { status, note: note.slice(0, LIMITS.note), at: now() }
      await writeJson(this.legacy, all)
      return all
    })
  }

  // ---- reviewer names: random id → display name ----

  private get reviewersFile() {
    return join(this.dir, "reviewers.json")
  }

  async reviewerName(id: string | undefined): Promise<string | null> {
    if (!id || !(await exists(this.reviewersFile))) return null
    const all = JSON.parse(await readFile(this.reviewersFile, "utf8")) as Record<string, { name: string }>
    return all[id]?.name ?? null
  }

  /** Store a display name; returns the (possibly new) reviewer id. */
  setReviewer(id: string | undefined, name: string) {
    return this.serial(async () => {
      const clean_ = clean(name, LIMITS.name, "name")
      await mkdir(this.dir, { recursive: true })
      const all = (await exists(this.reviewersFile))
        ? (JSON.parse(await readFile(this.reviewersFile, "utf8")) as Record<string, { name: string; at: string }>)
        : {}
      const rid = id && /^[\w-]{12,64}$/.test(id) ? id : randomBytes(18).toString("base64url")
      all[rid] = { name: clean_, at: now() }
      await writeJson(this.reviewersFile, all)
      return { id: rid, name: clean_ }
    })
  }
}

/** Top items by score (ties: more voters first), for the "top by score" strip. */
export function topByScore(r: Round, n = 10) {
  const rows: { key: ItemKey; icon: string; style: string; mode: string; votes: VoteSummary }[] = []
  for (const i of r.icons)
    for (const [style, modes] of Object.entries(i.images))
      for (const [mode, key] of Object.entries(modes))
        if (key) rows.push({ key, icon: i.name, style, mode, votes: summarize(r.votes[key]) })
  return rows
    .filter((x) => x.votes.voters > 0)
    .sort((a, b) => b.votes.score - a.votes.score || b.votes.voters - a.votes.voters)
    .slice(0, n)
}

export function isVerdict(v: unknown): v is Verdict {
  return typeof v === "string" && (VERDICTS as readonly string[]).includes(v)
}

/**
 * This repo's store: local/icons/review, the legacy local/icons/reviews.json and feedback in
 * local/icons/feedback. REVIEW_DATA_DIR moves all three into one directory (tests, other brands).
 */
export function repoStore(root: string) {
  const d = process.env.REVIEW_DATA_DIR
  return {
    store: d
      ? new ReviewStore({ dir: d, legacy: join(d, "reviews.json") })
      : new ReviewStore({ dir: join(root, "local/icons/review"), legacy: join(root, "local/icons/reviews.json") }),
    feedbackDir: d ? join(d, "feedback") : join(root, "local/icons/feedback"),
  }
}
