/**
 * Feedback rounds: the data model. Plain JSON on disk (one file per round), no brand names in here,
 * so the same store works for any icon set (see README "Feedback rounds").
 *
 * An item is one image in a round, keyed like the gallery keys it: `round:<render round>/<mode>/<name>`,
 * for example `round:25d-b7/dark/relay`. Votes and verdicts are per item; comments hang off an icon
 * name (one thread per icon card) and may point at the item they are about.
 */

export const VERDICTS = ["approved", "needs-work", "rejected", "regenerate"] as const
export type Verdict = (typeof VERDICTS)[number]

export type ItemKey = string
export const ITEM_KEY = /^round:([\w.-]+)\/(light|dark)\/([\w-]+)$/
export const ROUND_NAME = /^[\w][\w.-]{0,59}$/

/** One reviewer's vote on one item. A down vote always points at the comment that explains it. */
export interface Vote {
  value: 1 | -1
  at: string
  commentId?: string
}

export interface Comment {
  id: string
  /** Icon name the thread belongs to. */
  icon: string
  /** The image the comment is about, when it is about one (a down vote's reason always is). */
  item?: ItemKey
  parentId?: string
  /** Random reviewer id (never shown to other reviewers). */
  reviewer: string
  name: string
  owner: boolean
  text: string
  at: string
  /** Set by a down vote: this comment is the reason for it. */
  down?: boolean
}

export interface IconRequest {
  id: string
  /** Proposed icon name (free text, e.g. "invoice"). */
  name: string
  /** What it should show. */
  shows: string
  reviewer: string
  by: string
  at: string
}

/** The human verdict on one item; only the owner sets it. */
export interface VerdictEntry {
  verdict: Verdict
  note: string
  at: string
}

/** One icon in a round with the images that were snapshotted for it. */
export interface RoundIcon {
  name: string
  /** Style id ("25d", "flat") → mode → item key. */
  images: Record<string, Partial<Record<"light" | "dark", ItemKey>>>
}

export interface Round {
  version: 1
  name: string
  status: "open" | "closed"
  /** Feed this round's feedback into the next generation run when it closes (opt-in). */
  feed: boolean
  createdAt: string
  closedAt?: string
  icons: RoundIcon[]
  /** item → reviewer id → vote */
  votes: Record<ItemKey, Record<string, Vote>>
  comments: Comment[]
  requests: IconRequest[]
  verdicts: Record<ItemKey, VerdictEntry>
}

export interface VoteSummary {
  up: number
  down: number
  score: number
  voters: number
}

/** The legacy single-file reviews (local/icons/reviews.json): key → verdict, still read and kept in sync. */
export type LegacyReviews = Record<ItemKey, { status: Verdict; note: string; at: string }>

/** What `review-feedback` writes to local/icons/feedback/<round>.json and the next AI round reads. */
export interface FeedbackItem {
  icon: string
  style: string
  mode: "light" | "dark"
  key: ItemKey
  verdict: Verdict | null
  note: string
  votes: VoteSummary
  comments: string[]
  /** Note plus comments as one brief for the generator. */
  feedback: string
}

export interface FeedbackFile {
  round: string
  feed: boolean
  generatedAt: string
  closedAt?: string
  /** verdict regenerate or needs-work: the notes and comments become the next prompt's feedback. */
  regenerate: FeedbackItem[]
  /** verdict approved: the target for a Blender model. */
  buildInBlender: FeedbackItem[]
  rejected: FeedbackItem[]
  /** Down votes or comments without a verdict yet: listed, never fed. */
  unjudged: FeedbackItem[]
  newIcons: { name: string; shows: string; by: string; at: string }[]
}
