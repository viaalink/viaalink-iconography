# 011: router, modem, caddy (owner 2026-11-12)

Executor: agy. Edit ONLY scripts/icons/blender/build.py (new icon_router, icon_modem, icon_caddy + ICONS
entries) and scripts/icons/flat.ts (new FLAT entries; STAMP_KNOCKOUT entries where a cream/navy detail
sits straight on the red body). Do not change existing icons, lighting, palette, camera or gate. Do not
commit. Read docs/skill/SKILL.md first, especially "The icon IS the object".

Why: the owner wants to explain "internet → modem → router → three NATS-linked Relays (zero downtime)"
and "the via CLI as a web publisher, Caddy doing HTTPS in front of the Relay". These icons stand on pipes
in 2.5D flow diagrams, so they must read at small size and have a clear front (-Y).

House style: chunky, rounded (bevels >= 0.08), at most ~5 parts, the object itself (no tile, no disc),
body red (p), cream secondary (s/c), navy only in recesses (r), lit details as g. Reference objects:
icon_nas (box with LEDs), icon_server, icon_sync (approved), icon_docker (brand mark + smooth body).

New icons (2.5D model + flat twin, same name):
- router: a low wide rounded red box (like a home wifi router) with two or three thick rounded cream
  antennas standing up at the back, a row of 3-4 small g status LEDs on the front edge. Distinct from
  nas (which is tall with trays) and server (stacked).
- modem: a slim upright red box standing on a small cream foot, front face with a vertical row of 4 g
  LEDs and a small cream round "globe/line" emblem at the top; NO antennas (so it never reads as a
  router).
- caddy: the Caddy webserver mark from scripts/icons/brands/caddy.svg as a standing sculpture via
  brand_mark(..., bevel=...) like apple_mark_solid (body p, rounded rim, smooth()). If the mark's
  inner details melt together at extrusion, sculpt the main silhouette and keep the inner padlock as a
  cream (s) inset. Flat twin: the mark in red with the lip (see FLAT.github / FLAT.apple using
  part(...)). Read the mark with: grep -o 'd="[^"]*"' scripts/icons/brands/caddy.svg

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 router modem caddy
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at each PNG (light + dark, 2.5D and flat) and iterate at most 3 times per icon. Report per icon
done / not done + why, and the gate line. A truthful "NOT DONE: <reason>" beats a false "done".
