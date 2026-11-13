/**
 * One canvas for every icon: square, transparent, the object centred with the
 * same margin. The image model sometimes returns 1408×768 or 1504×704 instead
 * of a square; pages that show icons in square boxes then squash them. Trimming
 * to the object and re-placing it also makes every icon in the family the same
 * optical size.
 */
import sharp from "sharp"
import { THEME } from "./theme"

export const ICON_SIZE = THEME.canvas.size
/** Margin on each side, as a share of the canvas. */
export const ICON_MARGIN = THEME.canvas.margin
/**
 * Optical size: a square icon fitted edge to edge looks twice as heavy as a tall
 * phone fitted to the same box. Cap the scale so the object's area-equivalent side
 * (√(w·h)) is at most this share of the box; tall or wide objects still reach the
 * box edge on their long side. Scenes and other near-square art pass optical=false.
 */
export const ICON_OPTICAL = THEME.canvas.optical

/** Scale for a trimmed w×h object on the square canvas (shared with the gallery's label mapping). */
export function fitScale(w: number, h: number, size = ICON_SIZE, optical = true): number {
  const box = Math.round(size * (1 - 2 * ICON_MARGIN))
  const k = Math.min(box / w, box / h)
  return optical ? Math.min(k, (box * ICON_OPTICAL) / Math.sqrt(w * h)) : k
}

export async function squareIcon(png: Buffer, size = ICON_SIZE, optical = true): Promise<Buffer> {
  const trimmed = await sharp(png)
    .ensureAlpha()
    .trim({ background: { r: 0, g: 0, b: 0, alpha: 0 }, threshold: THEME.canvas.trimThreshold })
    .toBuffer({ resolveWithObject: true })
  const k = fitScale(trimmed.info.width, trimmed.info.height, size, optical)
  const fitted = await sharp(trimmed.data)
    .resize(Math.round(trimmed.info.width * k), Math.round(trimmed.info.height * k), {
      fit: "fill",
      kernel: "lanczos3",
    })
    .toBuffer({ resolveWithObject: true })
  const { width, height } = fitted.info
  return sharp({
    create: { width: size, height: size, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } },
  })
    .composite([
      {
        input: fitted.data,
        left: Math.round((size - width) / 2),
        top: Math.round((size - height) / 2),
      },
    ])
    .png()
    .toBuffer()
}
