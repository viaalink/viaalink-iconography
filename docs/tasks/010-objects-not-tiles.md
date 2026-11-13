# 010: The icon IS the object (owner 2026-11-11)

Executor: agy. Edit ONLY the functions named below in scripts/icons/blender/build.py and their FLAT
(+ STAMP_KNOCKOUT) entries in scripts/icons/flat.ts. Do not touch any other icon, lighting, palette,
camera or gate. Do not commit. Read the section "The icon IS the object" in
docs/skill/SKILL.md first.

Owner: "by placing everything in squares … we can make the icon the actual object". Reference: the
owner-approved `sync` (icon_sync and FLAT.sync): the shape itself, red, thick, rounded, standing, with
at most one cream accent, no tile, no disc behind it.

Rebuild:
- wifi: the three arcs and the dot themselves as thick, rounded red solids standing upright (stacked
  concentric arcs, rounded ends, dot below), no tile. Flat twin: the same arcs and dot in red with the
  lip, no tile.
- bluetooth: the Bluetooth rune itself as a thick red solid with a rounded rim (one smooth closed
  outline, extruded), standing, no disc. Flat twin: the rune in red with the lip.
- upload: a thick red arrow pointing up, standing on a cream rounded bar (the "tray" as a low bar,
  not a box). Flat twin to match.
- download: the same, arrow pointing down onto the cream bar.
- voice-profile (flat twin only): the person is a solid cream bust with the lip (like the other flat
  people, e.g. FLAT.team or FLAT.page), not line art; keep the red waveform badge.

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 wifi bluetooth upload download
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at each PNG (light + dark, 2.5D and flat) and iterate at most 3 times. Report per icon
done / not done + why, and the gate line.
