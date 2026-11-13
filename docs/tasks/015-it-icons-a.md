# 015: IT-diagram icons, part A (owner 2026-11-12: "make complete IT diagrams possible with our set")

Executor: agy. Edit ONLY scripts/icons/blender/build.py (new icon_* functions + ICONS entries) and
scripts/icons/flat.ts (new FLAT entries + STAMP_KNOCKOUT where a cream/navy detail sits straight on the red
body). Do not change existing icons, the palette (ROLES), lighting, camera or gate. Do not commit.
Read docs first: docs/skill/SKILL.md ("The icon IS the object", house style).

The owner approved these AI concept sketches (look at them; they are sketches, build them in OUR house style:
same camera, bevels >= 0.08, red body p, cream secondary s/c, navy only in recesses r, glowing g details,
no tile, no text): local/icons/rounds/concept-it-1/dark/<name>.png. Network/compute devices use the device family: icon_caddy's cream side
ports (same construction, same height) on the LEFT and RIGHT. Flat twins: same object, flat light secondary
is sand (n/m), see existing FLAT entries such as relay, caddy, server, database.

Icons (2.5D + flat twin each, same name):
- user: one person bust (cream round head, red shoulders), alone. Like a single member of icon_team.
- key: a chunky red key, round bow with a cream hole, a small cream tag hanging from the bow.
- shield: upright red shield, cream rim, big cream check mark.
- firewall: device family box with side ports; front = brick wall (cream mortar lines on red), one g light.
- cloud: a CLEAN chunky puffy red cloud (3–4 round lobes) with a flat cream underside. No band through it
  (the sketch had a strange band: do not copy that).
- container: generic shipping container, ribbed red box, cream corner posts, two cream doors on the end.
- cluster: three small identical red rounded cubes on one shared cream base plate, joined by short cream pipes.
- vm: device family box with side ports; front = navy screen showing a small cream box (machine in a machine).
- cache: a short database cylinder (like icon_database, 2 disks) with a big cream lightning bolt on its front.
  It must read as fast STORAGE, not as a coin.
- queue: a low red base with a cream channel/pipe on top holding three red rounded packets in a row.
- bucket: a red pail with cream rim and handle, two cream sheets sticking up out of it.

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 user key shield firewall cloud container cluster vm cache queue bucket
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at each PNG (light + dark, 2.5D and flat) next to relay/server/database; iterate at most 3 times per icon.
Report per icon done / NOT DONE + why, and the gate line.
