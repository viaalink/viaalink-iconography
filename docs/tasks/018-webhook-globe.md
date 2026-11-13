# 018: webhook with a globe (owner 2026-11-13: "render a globe in the webhook, that makes more sense, and use more navy")

Executor: agy. Edit ONLY icon_webhook in scripts/icons/blender/build.py and FLAT.webhook (+ STAMP_KNOCKOUT if
needed) in scripts/icons/flat.ts. Do not change palette, lighting, camera, gate or other icons. Do not commit.
Read docs/skill/SKILL.md first.

- 2.5D: keep the chunky red hook (with its eyelet). Replace the cream ball in its curve by a small GLOBE caught
  in the hook: a NAVY sphere (role r) with cream (c) continents/meridian lines, like a mini version of the
  globe idea (see icon_globe for how continents are made, but navy ocean instead of red). Make the globe clearly
  readable at 48 px (big enough, about the width of the hook's curve).
- Flat twin: same red hook, navy globe with cream land/meridian lines, and fill the cell like the other flat
  icons (~80% height; today it is tiny).

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 webhook
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at light + dark, 2.5D and flat. Iterate at most 3 times. Report done / NOT DONE + why, and the gate line.
