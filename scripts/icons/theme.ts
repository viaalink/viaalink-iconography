/**
 * The icon theme: one JSON file with everything brand- or look-specific (colours, fonts, logo,
 * camera, light rig, materials, canvas, gate, diagram look). TypeScript side of the one loader
 * per language (Python: scripts/icons/theme.py).
 *
 *   import { THEME, themePath } from "./theme"
 *   THEME.flat.roles.light.p
 *   themePath(THEME.logo.markFlat)        // paths in the theme are relative to the file
 *
 * The file is $VIA_ICON_THEME, else theme/brand.json. It is validated against
 * theme/brand.schema.json (a small JSON-schema subset, no dependencies), so a missing key or a
 * wrong type stops the run with the path of the problem.
 */
import { readFileSync } from "node:fs"
import { dirname, isAbsolute, join, resolve } from "node:path"

type Hex = string
type Vec3 = [number, number, number]
type PerRole = { p: number; s: number; c: number; g: number; r: number; default: number }
type Light = { energy: number; color: Vec3; size: number; location: Vec3 }
export type Role25 = "p" | "s" | "r" | "c" | "g" | "k"
export type FlatRole = "p" | "s" | "n" | "m" | "r" | "c"
export type Mode = "light" | "dark"

export interface Theme {
  brand: { name: string; slug: string; cssPrefix: string; cliWord: string; url: string }
  fonts: { mono: string; sans: string; sansCaps: string }
  logo: { mark3d: string; markFlat: string }
  pages: { light: Hex; dark: Hex; video: Hex }
  colors25d: { hex: Record<string, Hex>; roles: Record<Mode, Record<Role25, string>>; calibrated: string; lifted: string }
  materials: {
    roughness: PerRole
    specular: PerRole
    coatWeight: number
    coatRoughness: number
    glow: number
    glowFlesh: number
    creamAlbedo: number
    creamDim: number
    navyLift: number
  }
  render: {
    samples: number
    seed: number
    resolution: number
    denoise: boolean
    viewTransform: string
    look: string
    exposure: number
    world: { color: Vec3; strength: number }
  }
  camera: { azimuth: number; pitch: number; orthoMargin: number; distance: number }
  lights: { target: Vec3; key: Light; rim: Light }
  shape: {
    bevel: { box: number; cyl: number; minSegments: number; text: number }
    smoothAngle: number
    tubeResolution: number
    port: { radius: number; length: number; offset: number; bevel: number; bore: number; boreLength: number; boreOffset: number }
  }
  flat: { roles: Record<Mode, Record<FlatRole, Hex>>; lip: number; art: number }
  canvas: { size: number; margin: number; optical: number; trimThreshold: number }
  gate: { whiteLevel: number; whiteMaxPct: number; opaqueAlpha: number; edgePx: number; minAspect: number }
  diagram: {
    samples: number
    grid: number
    foot: number
    pipeZ: number
    pipeR: number
    tileFont: number
    fullFont: number
    board: { thickness: number; thicknessScene: number; topRole: string; underRole: string; groupRole: string }
  }
  animation: { samples: number; storySamples: number; fps: number }
  gallery: { background: Hex; ink: Hex; link: Hex }
  prompt: { chroma: Hex; palette: Record<"red" | "redDeep" | "coral" | "navy" | "navyDeep" | "slate" | "cream" | "white", Hex> }
}

type Schema = {
  type?: "object" | "array" | "string" | "boolean" | "integer" | "number"
  required?: string[]
  properties?: Record<string, Schema>
  additionalProperties?: Schema | boolean
  items?: Schema
  minItems?: number
  maxItems?: number
  pattern?: string
}

const REPO = resolve(import.meta.dir, "../..")
export const DEFAULT_THEME = join(REPO, "theme/brand.json")
export const THEME_SCHEMA = join(REPO, "theme/brand.schema.json")
export const THEME_ENV = "VIA_ICON_THEME"

const isType: Record<NonNullable<Schema["type"]>, (v: unknown) => boolean> = {
  object: (v) => typeof v === "object" && v !== null && !Array.isArray(v),
  array: Array.isArray,
  string: (v) => typeof v === "string",
  boolean: (v) => typeof v === "boolean",
  integer: Number.isInteger,
  number: (v) => typeof v === "number" && Number.isFinite(v),
}

function check(value: unknown, schema: Schema, where: string, errors: string[]) {
  if (schema.type && !isType[schema.type](value)) {
    errors.push(`${where}: expected ${schema.type}, got ${Array.isArray(value) ? "array" : typeof value}`)
    return
  }
  if (schema.pattern && typeof value === "string" && !new RegExp(schema.pattern).test(value))
    errors.push(`${where}: "${value}" does not match ${schema.pattern}`)
  if (isType.object(value)) {
    const obj = value as Record<string, unknown>
    for (const k of schema.required ?? []) if (!(k in obj)) errors.push(`${where}.${k}: missing`)
    for (const [k, v] of Object.entries(obj)) {
      const sub = schema.properties?.[k] ?? (typeof schema.additionalProperties === "object" ? schema.additionalProperties : undefined)
      if (sub) check(v, sub, `${where}.${k}`, errors)
    }
  }
  if (Array.isArray(value)) {
    if (value.length < (schema.minItems ?? 0) || value.length > (schema.maxItems ?? value.length))
      errors.push(`${where}: ${value.length} items`)
    if (schema.items) for (const [i, v] of value.entries()) check(v, schema.items, `${where}[${i}]`, errors)
  }
}

/** Throws with every problem listed; returns the theme typed. */
export function validateTheme(theme: unknown, schema?: Schema): Theme {
  const errors: string[] = []
  check(theme, schema ?? (JSON.parse(readFileSync(THEME_SCHEMA, "utf8")) as Schema), "theme", errors)
  if (!errors.length) {
    const t = theme as Theme
    for (const [mode, roles] of Object.entries(t.colors25d.roles))
      for (const [role, name] of Object.entries(roles))
        if (!(name in t.colors25d.hex)) errors.push(`theme.colors25d.roles.${mode}.${role}: "${name}" is not in colors25d.hex`)
  }
  if (errors.length) throw new Error(`invalid icon theme:\n  ${errors.join("\n  ")}`)
  return theme as Theme
}

export function loadTheme(path = process.env[THEME_ENV] || DEFAULT_THEME): Theme & { file: string; dir: string } {
  const file = resolve(path)
  const theme = validateTheme(JSON.parse(readFileSync(file, "utf8")))
  return { ...theme, file, dir: dirname(file) }
}

/** The theme in use ($VIA_ICON_THEME or theme/brand.json). */
export const THEME = loadTheme()

/** A path from the theme (fonts, logo), relative to the theme file. */
export const themePath = (rel: string) => (isAbsolute(rel) ? rel : resolve(THEME.dir, rel))

/** CSS variable for a flat role: --<cssPrefix>-<role>. */
export const cssVar = (role: string) => `--${THEME.brand.cssPrefix}-${role}`

if (import.meta.main) console.log(`theme ok: ${THEME.file} (${THEME.brand.name})`)
