# 019: caddy with the OFFICIAL Caddy mark on our device block (owner 2026-11-13)

Owner: "look, you need to redo https://caddyserver.com/resources/images/logo-dark.svg, it's different. Use that on
the default block we use."

Executor: agy. Edit ONLY icon_caddy in scripts/icons/blender/build.py and FLAT.caddy (+ STAMP_KNOCKOUT if needed)
in scripts/icons/flat.ts. You may add a cleaned icon-only SVG at scripts/icons/brands/caddy-mark.svg.
Do not change palette, lighting, camera, gate or other icons. Do not commit.
Read docs/skill/SKILL.md first.

Source: scripts/icons/brands/caddy-logo-official.svg (Caddy's official logo-dark.svg; reference render:
local/icons/loop/caddy-logo-reference.png). Only the ICON part on the left is used, never the "caddy" wordmark:
- an OPEN padlock: the shackle (path id "Shackle") and the lock body with its key-shaped cut-out (path id
  "Lock-body");
- an ORBIT ring around it with TWO nodes: a small ring at the top right connected by a short spoke, and a
  bigger ring at the bottom left with a spoke reaching into the lock.
Today's emblem (a closed padlock in an ellipse with one ball) is NOT this mark: replace it.

Build:
- Keep the default device block exactly as it is now (the red rounded box with the cream ports left and right,
  the navy front panel and the three g status dots under it).
- On the navy panel, the official mark as the emblem: create scripts/icons/brands/caddy-mark.svg with ONLY the
  icon paths (orbit, both nodes, shackle, lock body) in one viewBox, then put it on the panel with
  brand_mark(...) (role "c", small depth, a rounded bevel) like apple_mark_solid, sized to fill the panel. If
  thin parts of the orbit are too fine at 48 px, thicken them a little. The shape must stay recognisably
  Caddy's mark. Single colour, our palette (no green/blue gradient).
- Flat twin: same block, navy panel, the mark from caddy-mark.svg in cream, filling the panel.

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 caddy
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Compare with the reference PNG: open lock, key cut, orbit with two nodes. Iterate at most 3 times.
Report done / NOT DONE + why, and the gate line.
