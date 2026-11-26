/**
 * Minimal OpenRouter image client for the icon pipeline.
 *
 * OpenRouter serves image models through chat completions with
 * `modalities: ["image", "text"]`; the image comes back as a data URL on
 * `choices[0].message.images[].image_url.url`.
 *
 * The key is read from OPENROUTER_API_KEY (never stored in the repo).
 */
import { THEME } from "./theme"

export const DEFAULT_IMAGE_MODEL = process.env.ICON_MODEL ?? "google/gemini-3-pro-image"

export interface ImageRequest {
  prompt: string
  model?: string
  /** Optional reference images (data URLs or https URLs), e.g. the logo mark. */
  references?: string[]
}

interface ChatImage {
  image_url?: { url?: string }
}

export async function generateImage(req: ImageRequest): Promise<Buffer> {
  const key = process.env.OPENROUTER_API_KEY
  if (!key) throw new Error("OPENROUTER_API_KEY is not set")

  const content: unknown[] = [{ type: "text", text: req.prompt }]
  for (const url of req.references ?? []) content.push({ type: "image_url", image_url: { url } })

  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      "X-Title": `${THEME.brand.slug}-iconography`,
    },
    body: JSON.stringify({
      model: req.model ?? DEFAULT_IMAGE_MODEL,
      modalities: ["image", "text"],
      // Icons live on a square canvas; without this the model sometimes picks 16:9-ish.
      image_config: { aspect_ratio: "1:1" },
      messages: [{ role: "user", content }],
    }),
  })
  if (!res.ok) throw new Error(`OpenRouter ${res.status}: ${(await res.text()).slice(0, 500)}`)

  const json = (await res.json()) as {
    choices?: { message?: { images?: ChatImage[]; content?: string } }[]
  }
  const url = json.choices?.[0]?.message?.images?.[0]?.image_url?.url
  if (!url) {
    const text = json.choices?.[0]?.message?.content ?? JSON.stringify(json).slice(0, 300)
    throw new Error(`No image in response: ${text}`)
  }
  if (url.startsWith("data:")) return Buffer.from(url.slice(url.indexOf(",") + 1), "base64")
  const img = await fetch(url)
  return Buffer.from(await img.arrayBuffer())
}

/** Read a local file as a data URL, for passing reference images. */
export async function fileToDataUrl(path: string, mime = "image/png"): Promise<string> {
  const buf = Buffer.from(await Bun.file(path).arrayBuffer())
  return `data:${mime};base64,${buf.toString("base64")}`
}
