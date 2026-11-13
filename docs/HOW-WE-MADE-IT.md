# How we made the Viaalink icons

The set was built in November 2026 by one person (the owner) working with AI agents. The owner set the
direction and approved every icon. An agent acted as product owner and QA, a second agent built in
Blender, and independent reviewers judged the results by looking at them.

## 1. From AI pictures to Blender

The first rounds were AI image generations (OpenRouter, `scripts/icons/render.ts`). They looked good one by
one, but never matched each other: every icon had its own light, camera and red. So the 2.5D set moved to
**Blender**, where every icon shares one camera, one light rig and one palette:

- `scripts/icons/blender/build.py` models each icon from simple parts (rounded boxes, curves, extruded SVG
  paths) with a role per part: body red, cream secondary, navy only in recesses, glowing details.
- Light and dark are the same model with a palette swap, so they never drift apart.
- `scripts/icons/flat.ts` draws the flat twin of each icon as SVG on a 24-unit grid, part by part, with a
  "lip" (the same shape shifted down in a darker shade) as its only depth cue.

AI is still used, but only for **concepts**. When a new icon is needed, we write three to five ideas in
text, render rough AI sketches with the existing Blender icons attached as style references, the owner
picks one, and it is then built in Blender. The Caddy, Let's Encrypt and DNS icons were made this way.

## 2. Agents with a gate, not a promise

The Blender work was done by an executor agent (Google's Antigravity CLI, `agy`) from short task files. Six
real ones are in [docs/tasks](tasks). Every task ends the same way:

```
just icons-blender ... ; just icons-flat ... ; just icons-blender-gate   # must print GATE: pass
```

The agent iterates at most three times per icon and reports "done" or "NOT DONE: why" per icon. The
reviewing agent never trusts the report. It renders a contact sheet (2.5D and flat, light and dark, side by
side), **looks at it**, and only then commits. The working rules the agents follow are in
[docs/skill/SKILL.md](skill/SKILL.md).

## 3. Rules that came from the owner's eye

Most of the house style came from looking at renders and saying what was wrong:

- **The icon is the object.** No tile or disc behind an icon. A Wi-Fi icon is the arcs themselves, and a
  sync icon is the two arrows (the owner's reference icon).
- **One family for infrastructure.** Relay, modem, router, server, NAS, Caddy, certificate store and DNS
  keep their own shapes, but share the same cream pipe ports, so pipes plug into them in diagrams.
- **2D matches 2.5D.** The flat twins use sand where the 2.5D uses cream. Navy and red are accents.
- **Colour is checked on screen.** The red is measured, not guessed, because a monitor's night mode once
  made it look orange.

## 4. Independent review

Before the release, a reviewer agent that had not seen the work scored every icon from contact sheets
alone: 2.5D 7.2/10, flat 7.2/10. It named the weakest icons (a backup that read as a cooking pot, three
near-identical phone icons, a navy penguin that vanished on dark), and those were redone. Its list of
missing icons is the plan for 0.2.

## 5. From icons to diagrams and films

`diagram.py` places icons on a board shaped to the diagram and routes pipes between them. Labels are
projected from 3D, so they can be drawn as crisp HTML over a video. `story.py` turns a diagram into a short
story: nodes pop in, pipes draw themselves, packets flow, and a node can fail while the rest keeps serving.
Viaalink's promotional films are built from these clips.
