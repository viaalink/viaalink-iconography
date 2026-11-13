# 017: certstore livelier, cicd redo (owner 2026-11-13)

Executor: agy. Edit ONLY icon_certstore and icon_cicd in scripts/icons/blender/build.py and FLAT.certstore,
FLAT.cicd (+ STAMP_KNOCKOUT if needed) in scripts/icons/flat.ts. Do not change palette, lighting, camera,
gate or other icons. Do not commit. Read docs/skill/SKILL.md first.

1. certstore: the owner wants it "more lively", closer to the approved AI sketch
   local/icons/rounds/concept-caddy-1/dark/certstore.png. Today the left cream port sits over the open drawer
   and hides the certificate. Make the CERTIFICATE the hero: the top drawer pulled further out toward the
   viewer, a bigger cream certificate card standing up out of it (about 1.5x today) with a bigger red round
   seal and a red ribbon hanging from the seal. Keep the device-family ports (owner: ports for all) but move
   them to the BACK half of the cabinet sides (and a bit lower), so they never overlap the drawer or the
   certificate. Flat twin to match (certificate clearly sticking out of the drawer, ports at the sides).
2. cicd: the 2.5D infinity loop lies flat/tilted back and the flat twin is tiny (fills ~40% of its cell).
   2.5D: stand the infinity loop UPRIGHT facing the camera (like the approved sync icon stands), thick and
   rounded, with a clear cream arrow head on one lobe pointing along the loop, and a small second cream
   arrow head on the other lobe so it reads as a continuous cycle. Flat: fill the cell like the other flat
   icons (~80% width), same upright loop with the two cream arrow heads.

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 certstore cicd
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at light + dark, 2.5D and flat; compare with sync, relay, caddy. Iterate at most 3 times per icon.
Report done / NOT DONE + why, and the gate line.
