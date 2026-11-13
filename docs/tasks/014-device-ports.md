# 014: pipe ports for every network device (owner 2026-11-12: "ports for all")

Executor: agy. Edit ONLY icon_modem, icon_router, icon_server, icon_nas, icon_certstore, icon_dns in
scripts/icons/blender/build.py and their FLAT entries in scripts/icons/flat.ts. Do not change the palette,
lighting, camera, gate, or any other icon. Do not commit. Read docs/skill/SKILL.md.

Owner: each device KEEPS its own recognisable shape (tower modem, router with antennas, stacked server,
NAS with drive bays, cabinet certstore, dns box with signpost), but all of them get the same cream pipe
ports as icon_caddy: one short, thick, round cream port sticking out of the LEFT side and one out of the
RIGHT side (world ±X, like icon_caddy, open round end visible), at the same height as caddy's ports
relative to the device's base (low-middle of the body, where diagram pipes run). Copy caddy's port
construction (radius, length, bevel, role) so they are identical across the family. Make sure the ports
do not hide the device's front details (LEDs, globe, trays, signpost) and the device still reads at 48 px.
Flat twins: the same two side port stubs as FLAT.caddy (sand secondary with lip).

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 modem router server nas certstore dns
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at each PNG (light + dark, 2.5D and flat) next to caddy and relay; iterate at most 3 times per icon.
Report per icon done / not done + why, and the gate line.
