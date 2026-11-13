/**
 * Icon style spec — the single source the generator builds prompts from (brand words and
 * colours from the theme, theme/brand.json).
 *
 * Two styles share one palette and one subject catalog:
 *  - "25d"  : soft-matte 2.5D isometric objects (website, marketing, app hero/empty states)
 *  - "flat" : flat front-view glyphs for small UI sizes where 2.5D does not read
 *
 * Two modes per style: "light" (sits on paper #F6F3EE / white) and "dark" (sits on navy #0E1626).
 *
 * Prompt technique (keep when editing):
 *  - Labelled sections in a fixed order; the model weights early sections most, so SUBJECT comes first.
 *  - Every colour is a hex with a ROLE and an approximate SHARE, never a bare colour word.
 *  - One fixed camera and light for every icon, so the set reads as a family.
 *  - Positive instructions first, a short hard NEVER list last.
 *  - Background is a flat chroma key (#00FF00) that never appears in the palette, so the
 *    optimizer can cut it out and ship transparent PNGs for any app surface.
 *  - The logo mark is attached as a reference image; designs may quote its curve language.
 *
 * This file is edited by the design iterations (local/icons/rounds/*); bump STYLE_VERSION each round.
 */

import { THEME } from "./theme"

export const STYLE_VERSION = 4

export type Style = "25d" | "flat"
export type Mode = "light" | "dark"

/** Prompt colours and the chroma key come from the theme (theme/brand.json "prompt"). */
export const PALETTE = THEME.prompt.palette
export const CHROMA = THEME.prompt.chroma
const BRAND = THEME.brand.name
const CLI = THEME.brand.cliWord

const BACKGROUND = `BACKGROUND (MANDATORY): perfectly flat, uniform pure chroma green ${CHROMA} filling 100% of the canvas edge to edge (never white, grey, cream, teal, or dark navy). The object floats in space with a razor-sharp outer silhouette: zero floor, zero cast shadow, zero contact shadow or ambient occlusion smudge beneath the object, no vignette, no background gradient or texture, and zero green colour spill on the object.`

const COMPOSITION = `COMPOSITION & SCALE: exactly one compact object centred in the square 1:1 canvas. Normalise visual weight so the entire object is completely contained within a central isometric bounding cube occupying 64%–68% of canvas width AND 64%–68% of canvas height, leaving a mandatory 16%–18% empty ${CHROMA} chroma-green margin on all four sides (no part of the object may ever approach or touch the canvas border). Tall objects must be wide/chunky and flat objects must be tall/thick to share identical visual mass.`

const TEXT_RULE = `TEXT: zero letters, numbers, symbols, or keyboard legends anywhere on the object, EXCEPT when the subject explicitly asks for the terminal prompt "> ${CLI}", which is rendered in bold lowercase monospaced font with a solid block cursor.`

const STYLE_25D: Record<Mode, string> = {
  light: `CAMERA & ANGLE: strict orthographic isometric projection viewed from 30 degrees above horizontal along the front-right axis (standard 30°/30° isometric grid, zero perspective convergence), identical for every icon in the set. Every object's primary front face is angled toward the bottom-left, its extruded depth side is angled toward the bottom-right, and its top plane is clearly visible from above.
STYLE & FORM: premium 2.5D isometric hardware/desk-toy icon. Chunky, compact, simplified geometry with thick extruded depth (at least 25% of object width) and generously rounded edges (corner radius about 10% of object size); soft pillowy bevels echoing the smooth curves of the attached ${BRAND} logo mark. Maximum 3–4 bold parts with zero tiny pinholes or fine textures so it reads clearly at 48 px and 32 px.
MATERIAL & LIGHT: uniform soft-matte powder-coated finish, slightly satin like ceramic or anodized metal. No gloss, no glass, no chrome, no flat painted 2D stripes. Soft studio key light from top-left: top faces lightest, front-left faces mid-tone, bottom-right depth faces darkest, with smooth shading across rounded bevels and no shadow on the background.
PALETTE & COLOUR ROLES (light-mode variant — outer silhouette edges must be bold red and dark navy, never cream; canvas background is always pure ${CHROMA} green):
- Primary colour (about 65%): ${PALETTE.red} brand red on main top and front-left hero surfaces, shaded with ${PALETTE.redDeep} deep red on bottom-right extrusions and lower bevels
- Secondary contrasting colour (about 25%): solid ${PALETTE.navy} dark navy ink for secondary structural parts (pedestal bases, stands, shackles, side plugs, frames, or secondary rings)
- Interior detail cream (about 10%): ${PALETTE.cream} warm cream strictly for enclosed interior details (embossed front emblems, blank keycaps, "> ${CLI}" text, grille bars, page lines, or keyhole collars) framed inside primary red or dark navy — never on an outer silhouette edge
- Recessed interior dark: ${PALETTE.navy} dark navy ink for enclosed recessed cavities (screen panels, grille recesses, keyhole openings).
Use only these colours plus their natural matte shading.`,
  dark: `CAMERA & ANGLE: strict orthographic isometric projection viewed from 30 degrees above horizontal along the front-right axis (standard 30°/30° isometric grid, zero perspective convergence), identical for every icon in the set. Every object's primary front face is angled toward the bottom-left, its extruded depth side is angled toward the bottom-right, and its top plane is clearly visible from above.
STYLE & FORM: premium 2.5D isometric hardware/desk-toy icon. Chunky, compact, simplified geometry with thick extruded depth (at least 25% of object width) and generously rounded edges (corner radius about 10% of object size); soft pillowy bevels echoing the smooth curves of the attached ${BRAND} logo mark. Maximum 3–4 bold parts with zero tiny pinholes or fine textures so it reads clearly at 48 px and 32 px.
MATERIAL & LIGHT: uniform soft-matte powder-coated finish, slightly satin like ceramic or anodized metal. No gloss, no glass, no chrome, no flat 2D sticker outlines, no painted stripes. Soft studio key light from top-left: top faces brightest, front-left faces warm mid-tone, bottom-right depth faces deeper red, with smooth 3D bevel highlights and no shadow on the background.
PALETTE & COLOUR ROLES (dark-mode variant — every outer silhouette edge MUST be high-contrast coral, red, or warm cream; NEVER use dark navy on any outer edge, base, shackle, plug, or ring; canvas background is always pure ${CHROMA} green):
- Primary colour (about 70%): ${PALETTE.coral} bright coral on lit top and front-left hero surfaces, shaded with ${PALETTE.red} brand red and ${PALETTE.redDeep} deep red on bottom-right depth extrusions
- Secondary contrasting colour (about 15%): solid ${PALETTE.cream} warm cream for all secondary structural parts (pedestal bases, stands, shackles, side plugs, frames, or secondary rings) so they contrast brightly in dark mode
- Interior detail cream (about 5%): ${PALETTE.cream} warm cream for enclosed interior details (embossed front emblems, blank keycaps, "> ${CLI}" text, grille bars, page lines, or keyhole collars)
- Recessed interior dark (about 10%): ${PALETTE.slate} slate navy strictly for recessed interior cavities completely enclosed inside a primary or cream frame (screen panels, grille recesses, keyhole openings).
Use only these colours plus their natural matte shading.`,
}

const STYLE_FLAT: Record<Mode, string> = {
  light: `STYLE: flat vector glyph icon, front view, no perspective, no 3D, no gradients.
FORM: bold geometric shapes with rounded corners and rounded stroke ends, consistent 8% stroke weight, echoing the smooth curves of the attached ${BRAND} logo mark. Max three parts; must read at 16 px.
PALETTE & COLOUR ROLES: ${PALETTE.navy} navy for the secondary contrasting colour and main shape, ${PALETTE.red} brand red for the primary colour accent, ${PALETTE.cream} cream for interior detail counters. Solid fills only.`,
  dark: `STYLE: flat vector glyph icon, front view, no perspective, no 3D, no gradients.
FORM: bold geometric shapes with rounded corners and rounded stroke ends, consistent 8% stroke weight, echoing the smooth curves of the attached ${BRAND} logo mark. Max three parts; must read at 16 px.
PALETTE & COLOUR ROLES: ${PALETTE.cream} cream for the secondary contrasting colour and main shape, ${PALETTE.coral} coral for the primary colour accent, ${PALETTE.slate} slate navy for recessed interior dark counters. Solid fills only.`,
}

const NEVER = `NEVER: green (${CHROMA}) on the object, white/teal/navy or any non-${CHROMA} background, cropping or touching the canvas border, text or keyboard letters other than "> ${CLI}", front-facing flat views, lying-down padlock or microphone, symmetric V-shaped checkmark, sync arrows, cut or broken open chain-link loops, dark navy outer parts in dark mode, 2D sticker outlines, painted two-tone stripes, fine mesh or pinhole dots, drop or contact shadows on the background, multiple disconnected objects, watermark, frame or border.`

export function buildPrompt(subject: string, style: Style, mode: Mode): string {
  const look = style === "25d" ? STYLE_25D[mode] : STYLE_FLAT[mode]
  return [
    `SUBJECT: ${subject}`,
    BACKGROUND,
    look,
    COMPOSITION,
    TEXT_RULE,
    NEVER,
    `The attached anchor icons define the exact camera, material, bevel radius, lighting and palette to match, while the SUBJECT defines what to draw; the attached ${BRAND} logo mark is for smooth curve language and brand colour reference only (do not paste or copy the full mark onto the object).`,
  ].join("\n\n")
}
