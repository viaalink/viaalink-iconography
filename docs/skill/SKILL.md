---
name: via-blender-icons
description: Build or change Viaalink 2.5D icons and desk scenes in Blender (deterministic, colour by role, light/dark = palette swap). Use when the user asks to add/fix a 2.5D icon or scene, make icons consistent, recolour the set, reuse dolls/props, or asks how the Blender icon pipeline works.
---

# Viaalink icons in Blender

The 2.5D set used to come from an image model (scripts/icons/render.ts). Each render
re-draws the object, so shapes drift between rounds and between light and dark. The
Blender pipeline fixes that: one model per icon, one camera, one light, colours by role.
AI stays for **concepts**; Blender makes the **final** icon.

## Commands

```bash
just icons-blender local/icons/rounds/25d-b1-blender                 # all models, light + dark
just icons-blender local/icons/rounds/25d-b1-blender --mode dark lock # one icon, one mode
just icons-blender <dir> --samples 32                                 # fast preview
```

The recipe runs `blender -b --factory-startup -P scripts/icons/blender/build.py`, then
`scripts/icons/normalize.ts`, which puts the icon on the square canvas with the same margin
as the AI rounds.
With an NVIDIA GPU, Cycles uses OptiX. The "HIPEW initialization failed" warning is harmless.

Name Blender rounds `25d-b<N>-…`. Rounds sort newest-first by label, and `b` sorts before `r`,
so a Blender round never silently replaces an AI main on the site. It shows up as history on
/approve, where the owner can make it main.

## Model rules (build.py)

- **Role `k` (accent rim):** cream in light, coral in dark. Use it for the frame around a sunk port or slot (Keep's cassette mouth, Connect's port), so the opening always contrasts with its body. The owner asked for these accents.
- **Navy lift:** light-mode navy `s` parts are rendered at ×2.4 albedo (`--navy`), otherwise navy reads as black on screen. `r` recesses stay dark.
- **Role `g` (screen glyph):** cream with emission 0.75. Use it for `•••>`, `>` and text on screens that face away from the key light; plain `c` turns grey there (owner flagged it on the relay).
- **Roles, not colours.** Every part gets a role: `p` (primary body), `s` (secondary:
  shackle, phone shell, stands), `r` (recessed cavity, screens), `c` (cream detail: keys,
  text, rims). The same roles are used in the flat twins (scripts/icons/flat.ts).
  `PALETTES["dark"|"light"]` maps role → brand hex. Never hard-code a hex in a model.
- **Camera:** orthographic, rotation (60°, 0, 45°). The front of the object faces **−Y**
  (it appears bottom-left), and the depth side faces +X (bottom-right, kept dark).
- **Light:** a warm area key from the top-left, a rim light behind-left, and a low warm
  world. The right side must stay deep red. A rim light on the right makes it look flat
  and pink.
- **View transform: Standard**, look None. AgX and Filmic shift the brand hex.
- **Fixed seed (7) and fixed samples**, so the same input gives the same pixels.
- Helpers:
  - `box` (rounded box via a bevel modifier);
  - `cyl`, `torus`;
  - `plate(profile, depth)`, which extrudes a 2D outline (`rr_profile`, `keyhole_profile`);
  - `tube(points, r)`, a seamless round tube for shackles and cables (better than
    torus + cylinders, which leaves shading seams);
  - `text` (the theme's mono font, IBM Plex Mono Bold);
  - `cut(target, cutter)`, an exact boolean after the bevel;
  - `smooth(o)`, smooth-by-angle after a cut, which avoids the shading smudge.
- **Recesses:** cut the body with the outline, put an `r` floor plate inside, and add a thin
  raised `c` rim around it. This is the keyhole and screen look of the approved set.
- A cavity inside an `s` part needs a `c` bezel. In light mode `s` and `r` are both navy,
  the same trap as the flat twins.
- The framing reads the bounding boxes of MESH, FONT and CURVE objects. Any new object
  type has to be added there, or parts get cropped.
- Work from the approved AI render as the target. Make a side-by-side strip
  (the target and your renders next to each other in one image) and compare after every change.
  Stop after 3 passes and show the owner rather than polishing endlessly.

## The icon IS the object (owner, 2026-11-11)

Never put a glyph on a square tile or disc. Build the thing itself as a standing sculpture: wifi = the
arcs and dot, bluetooth = the rune, upload/download = the arrow, Apple = the mark extruded with a
rounded rim (`brand_mark(..., bevel=)`). Reference: `sync` (two red arrows around a cream core,
owner-approved). Real objects stay objects: a card, an envelope, a key, a NAS, a whale. Brand marks
with a ® or hairline outlines (Raspberry Pi) get sculpted instead of imported. Smooth shapes beat
boolean cuts: flatten with a smooth clamp on vertices + subsurf (see `icon_docker`), not a hard cut.

## Colour decision (owner, 2026-11-11)

- The primary colour is the **red of the approved hero desk scene** (`HEX["warm"]` = #E04A46; the lit
  top renders at about #D54640, the sides deep red). Salmon (#FF7E66) and the brand hex #FF6B6B both
  read **pink** in this light, and the owner rejected them.
- Light and dark use **one palette**: red body, cream secondary, slate recesses. Navy appears only in recesses.
- The world fill is near-neutral (0.9, 0.88, 0.85). A warm or pink fill tints cream pink.
- Renders are made at 2048 px and normalised to 1024 px (sharp edges). Cream albedo 0.88 is gate-safe.

## Light calibration (do not eyeball)

- Clipping is the classic failure. Cream (#F6F3EE) clips to pure white once top-face light goes
  above 1.0, and then coral turns pink as well. On 2026-11-11 the CLI was 16.5% pure white.
- Check with `calib`: a cream block and a coral block. Run
  `blender -b … -P build.py -- --out local/icons/calib --samples 32 calib`, then
  `bun local/icons/sample.ts local/icons/calib/light/calib.png`, which prints the top/front/side
  hex and the clipped share.
- Targets:
  - coral top ≈ the brand hex (dark #FF6B6B → about #F66561, light #F73F3F → about #EE3D3B);
  - cream top about #F6F0E6;
  - cream front about #E9DFD2;
  - clipped share under 4%.
- `bun local/icons/measure.ts <png>`: the share of white pixels, which should be 0 on finished icons.
- Settings: key energy 740 at (-2.5,-5.5,6), size 4.5; rim 65; world (0.92,0.8,0.7) × 0.22;
  exposure -0.15; roughness about 0.8; specular 0.04–0.12; no emission on `c`; `g` emission 0.22.
  All of these can be overridden with `--key/--world/--glow`.

## Gotchas learned the hard way

- Call `bpy.context.view_layer.update()` before reading or setting `matrix_world`. Without it,
  objects placed since the last update keep a stale identity matrix, and `turn()` reset the
  logo to its import size.
- After an operator import, take the new object from `view_layer.objects.active` or from a
  before/after diff of `bpy.data.objects`. Never use `bpy.context.object`, which can still be
  the previous object.
- To stamp the logo: import the SVG with **no bevel** (a bevelled curve self-intersects). Convert
  it to a mesh, remove doubles and recalc normals, then cut. `stamp()` checks the vertex count
  and falls back to a raised logo, so a failed boolean can't erase the body. Put a thin `c`
  inlay at the floor of the stamp.
- The real logo is `scripts/icons/blender/logo-mark.svg`, cleaned from static/assets/avatar-mark.svg.
- Other jobs (TTS) can fill the GPU. The render then falls back to CPU automatically, with the
  same image.
- Camera azimuth is 30° by default, so the front face leads. `ICON_AZIMUTH` overrides it per
  icon to match an approved pose (relay: 58).
- Stamps (one colour, `currentColor`) come from the flat twins: `stampSvg(name, badge)` in
  flat.ts, served at `/stamp/<name>[-badge].svg`.

## Scenes: kit + description (next step)

The scenes (doctor, lawyer, student, school board, kids, contract, import, search) share
almost everything, so they are built from a **kit** instead of one-off models:

- **Doll:** a pill body, a round faceless head, `scale` (0.8 = child), and an `outfit` that
  sets role and accessory: stethoscope, suit collar, hoodie + backpack, teacher.
- **Slab:** the rounded desk tile (`s`, with a `p` underside in dark mode).
- **Props:** phone (flat, or upright with record/transcribe screen), laptop (`> via` or text
  lines), books, folder, contract + pen, round table, voice recorder, camera, magnifier,
  session cards, padlock.
- **Cable:** `tube()` through a few points from one prop to another.

A scene is data, e.g. `scripts/icons/blender/scenes/doctor.yaml`:

```yaml
slab: {size: [4, 4]}
place:
  - {part: doll, outfit: doctor, at: [-1.1, 0.9]}
  - {part: phone, screen: record, lying: true, at: [0, -0.6]}
  - {part: laptop, screen: via, at: [1.2, 0.6]}
  - {part: lock, scale: 0.35, on: phone}
cable: [phone, laptop]
```

Build parts as Python functions (deterministic, diffable, reviewable). A `kit.blend` with
assets is only worth it for shapes that are easier to sculpt by hand. If so, load it with
`bpy.data.libraries.load(path, link=False)` (append; linked overrides are fragile).

## Owner decisions (2026-11-10)

- Convert the Notetaker icons first (transcribe, minutes, report, mcp-a, phone), then the rest.
- Rebuild the scenes in Blender as a kit + YAML.
- The brand hex is leading (#FF6B6B coral in dark mode), not the more orange tint of the AI renders.
- AI is for concepts. Image→3D is allowed only when it actually saves time.

## Where AI fits

| Use | Tool | Final? |
|---|---|---|
| Explore a new icon or scene idea | render.ts via OpenRouter (`just icons-render`) | no: concept |
| Write or extend a bpy part function | Claude, reviewed and committed | yes, after review |
| Rough mesh for an odd organic prop | TRELLIS.2 (MIT, local) or Tripo API | no: rebuild clean |
| Final icon / scene pixels | Blender only | yes |

Avoid Hunyuan3D: its licence excludes the EU. Blender MCP servers are fine for interactive
modelling, but never inside the render pipeline.

## Costs

- An image render via OpenRouter costs money each time.
- Blender renders are free and repeatable: about 5–15 s per icon at 64 samples.
- Modelling a new icon takes about 20–40 min, once.
- A new scene from the kit means writing a YAML file plus any missing prop.
- Re-render only when the owner names a defect.

## Roadmap (owner, 2026-11-11)

1. **Everything in Blender.** Every icon (also globe, browser, config, check, meet, chat, call,
   files, page) and every desk scene (doctor, lawyer, student, school board, kids, contract,
   import, search) is rebuilt from the kit. AI renders are concepts only.
2. **Dolls kit** (`scripts/icons/blender/kit_dolls.py`): one doll, many outfits (doctor, lawyer,
   student, teacher, parent, child, developer, client). Scenes reuse it.
3. **Flow diagrams in 2.5D** (`scripts/icons/blender/diagram.py`): a diagram is data
   (nodes = icons or dolls on a grid, edges = pipes). Pipes are routed by script (orthogonal,
   rounded bends, collars at the ports), so every diagram always looks right, like the cables
   in the desk scenes and like the Mermaid flowcharts, but in our 2.5D style.
4. **Animated, scene by scene (later).** The same diagram data drives a short film: nodes
   appear one by one, packets flow through the pipes, and a caption names each actor's role.
   This is for explainers and the product films. Blender scenes
   are animation-ready, so it's a keyframe pass on the same objects, not a new pipeline.

## Working loop (how this got to 8/10)

- I am PO + QA. agy is the independent art director: give it a folder of renders plus
  references, ask for a numbered punch list with exact values and a score /10, and run it in
  `--mode plan` (read-only).
- Subagents build file-disjoint modules (a kit file each). build.py is the hotspot that only
  the orchestrator edits.
- Every new failure becomes a check in `scripts/icons/blender/gate.ts` (`just icons-blender-gate`):
  clipped white, a missing edition, cropping.
- Scores and the task index live in `local/icons/loop/` (README, backlog, scores).

## Comprehension review (owner, 2026-11-11): does the picture explain itself?

Looking good is not enough. A picture must tell the intended story **without our words**.

- **Blind read.** Hand an independent reviewer (agy in `--mode plan`, or a fresh subagent) ONLY
  the image(s): no labels, file names, captions or prior context. Ask: "What is happening here?
  Who does what, what flows where, what does the product do? What is unclear?"
- **Intent sheet.** For every icon, scene and diagram, `local/icons/loop/intent.md` holds 1–2
  sentences saying what it must communicate (for example scene-doctor: "a doctor's consultation is
  recorded on the phone and the minutes go privately to the doctor's own laptop").
- **Score.** Compare the blind answer with the intent: 0 = wrong story, 1 = partly, 2 = matches.
  Anything under 2 goes on the punch list, with the misread quoted as the defect (for example
  "reviewer saw a pager, not a phone").
- **Then with labels.** Run the same question again with labels and captions. If only the labelled
  version is understood, the picture leans on text and needs a clearer object or flow.
- **When.** After every iteration, next to the art-direction score. The loop is done when both
  the art score is ≥ 8/10 AND every item scores 2 blind.
- Use the misreads to improve the designs, the flow diagrams, and the explanations and copy on the
  site.

