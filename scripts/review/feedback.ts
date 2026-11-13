/**
 * Close the loop: turn a round's verdicts, notes, down-vote reasons and requests into a feedback file
 * (JSON, read by the next AI round) and a readable summary (Markdown).
 *
 *   regenerate / needs-work → their note and comments become the feedback text for the generator
 *   approved                → the "build in Blender" list
 *   requests                → the new-icons list
 *
 * A round closed without feeding (`feed: false`) still gets both files; the generator refuses it.
 */
import { mkdir } from "node:fs/promises"
import { join } from "node:path"
import { summarize } from "./store"
import { type FeedbackFile, type FeedbackItem, ITEM_KEY, type Round } from "./types"

const styleOf = (round: string) => round.split("-")[0]

export function compileFeedback(r: Round): FeedbackFile {
  const items: FeedbackItem[] = []
  for (const icon of r.icons)
    for (const modes of Object.values(icon.images))
      for (const key of Object.values(modes)) {
        if (!key) continue
        const [, round, mode] = key.match(ITEM_KEY) ?? []
        const v = r.verdicts[key]
        // top-level comments about this image, then the rest of the icon's thread (general remarks)
        const thread = r.comments.filter((c) => c.item === key || (c.icon === icon.name && !c.item))
        const comments = thread.map(
          (c) => `${c.down ? "thumbs down: " : ""}${c.text} (${c.name}${c.owner ? ", owner" : ""})`,
        )
        const note = v?.note ?? ""
        const feedback = [note, ...thread.map((c) => c.text)].filter(Boolean).join(" | ")
        items.push({
          icon: icon.name,
          style: styleOf(round),
          mode: mode as "light" | "dark",
          key,
          verdict: v?.verdict ?? null,
          note,
          votes: summarize(r.votes[key]),
          comments,
          feedback,
        })
      }
  const by = (f: (i: FeedbackItem) => boolean) => items.filter(f)
  return {
    round: r.name,
    feed: r.feed,
    generatedAt: new Date().toISOString(),
    ...(r.closedAt ? { closedAt: r.closedAt } : {}),
    regenerate: by((i) => i.verdict === "regenerate" || i.verdict === "needs-work"),
    buildInBlender: by((i) => i.verdict === "approved"),
    rejected: by((i) => i.verdict === "rejected"),
    unjudged: by((i) => i.verdict === null && (i.votes.down > 0 || i.comments.length > 0)),
    newIcons: r.requests.map((q) => ({ name: q.name, shows: q.shows, by: q.by, at: q.at })),
  }
}

const line = (i: FeedbackItem) =>
  `- **${i.icon}** (${i.style}, ${i.mode}) ${i.votes.up} up, ${i.votes.down} down${i.note ? `. Note: ${i.note}` : ""}${
    i.comments.length ? `\n${i.comments.map((c) => `  - ${c}`).join("\n")}` : ""
  }`

export function feedbackMarkdown(f: FeedbackFile): string {
  const sec = (title: string, rows: string[], empty = "None.") =>
    `## ${title}\n\n${rows.length ? rows.join("\n") : empty}\n`
  return [
    `# Feedback round ${f.round}\n`,
    `Generated ${f.generatedAt}${f.closedAt ? `, round closed ${f.closedAt}` : ", round still open"}.`,
    f.feed
      ? "This round feeds the next generation run: `just icons-regen <out> " +
        `local/icons/feedback/${f.round}.json\`.\n`
      : "Closed circle: this round is NOT fed into generation. The feedback stays here and in the gallery.\n",
    sec("Regenerate or needs work", f.regenerate.map(line)),
    sec("Build in Blender (approved)", f.buildInBlender.map(line)),
    sec("Rejected", f.rejected.map(line)),
    sec("Comments without a verdict yet (not fed)", f.unjudged.map(line)),
    sec(
      "New icons requested",
      f.newIcons.map((q) => `- **${q.name}**: ${q.shows} (${q.by})`),
    ),
  ].join("\n")
}

/** Write <dir>/<round>.json and <dir>/<round>.md; returns both paths. */
export async function writeFeedback(r: Round, dir: string) {
  await mkdir(dir, { recursive: true })
  const f = compileFeedback(r)
  const json = join(dir, `${r.name}.json`)
  const md = join(dir, `${r.name}.md`)
  await Bun.write(json, `${JSON.stringify(f, null, 2)}\n`)
  await Bun.write(md, feedbackMarkdown(f))
  return { json, md, file: f }
}

/**
 * For the generator: per icon name (and style), one feedback text. Throws when the round was closed
 * without feeding, so a closed-circle round never ends up in a prompt by accident.
 */
export async function readFeedbackForGeneration(path: string, style: string): Promise<Map<string, string>> {
  const f = (await Bun.file(path).json()) as FeedbackFile
  if (!f.feed)
    throw new Error(
      `${path}: round ${f.round} was closed without feeding (closed circle). Close it again with --feed to use it.`,
    )
  const out = new Map<string, string>()
  for (const i of f.regenerate.filter((x) => x.style === style && x.feedback)) {
    const prev = out.get(i.icon)
    const text = `${i.mode} edition: ${i.feedback}`
    out.set(i.icon, prev ? `${prev} / ${text}` : text)
  }
  return out
}
