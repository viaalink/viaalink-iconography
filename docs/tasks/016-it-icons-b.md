# 016: IT-diagram icons, part B + OS icons as devices + relay orientation (owner 2026-11-12)

Executor: agy. Edit ONLY scripts/icons/blender/build.py, scripts/icons/flat.ts, and for item 4 also
NODE_TURN in scripts/icons/blender/diagram.py and the "turn" of node rc in
scripts/icons/blender/diagrams/ecosystem-future.json. Do not change the palette (ROLES), lighting, camera,
gate or other icons. Do not commit. Read docs/skill/SKILL.md first.

1. New IT icons (2.5D + flat twin, same name), from the owner-approved sketches in local/icons/rounds/concept-it-1/dark/<name>.png, built in
   OUR house style. Devices use icon_caddy's cream side ports (left and right, same construction/height).
   - api: device box with side ports; navy screen with cream curly braces { }.
   - webhook: a thick red HOOK (like a coat/fishing hook) with a cream packet ball caught in its curve.
     It must NOT look like an infinity sign (the sketch did; cicd is the infinity loop).
   - loadbalancer: box with ONE cream port on the left and THREE cream ports fanning out on the right.
   - switch: low wide box, front = row of 8 small navy square ports with tiny g lights; side ports.
   - cicd: a thick upright red infinity loop with a cream arrow head on it.
   - monitoring: device box with side ports; navy screen with a cream rising zig-zag pulse line.
   - logs: upright paper scroll, red roll ends, cream sheet with short navy lines.
   - bell: a CLASSIC chunky red bell (dome + flared rim) with a cream clapper ball and a small cream dot badge.
   - search: chunky magnifying glass, red ring and handle, cream glass.
   - trash: red rounded bin, cream lid, three vertical cream grooves.
2. OS icons as devices (owner: "if os-ios is a phone with the logo, do the same for the rest"):
   - os-android: the canonical viaalink_phone(...) with the Android mark (scripts/icons/brands/android.svg)
     in cream on its screen, exactly like os-ios does with the Apple mark.
   - os-linux, os-windows, os-macos: the desktop monitor (the diagram glyph "desktop" / icon_desktop body,
     monitor on a stand) with ONLY that OS mark in cream on the navy screen (brands/linux.svg,
     brands/windows.svg, brands/apple.svg). No other screen content.
   Flat twins to match (phone / monitor with the mark).
3. Keep the standalone marks: icon "apple" (alias) and "github" stay as they are.
4. relay orientation: the 2.5D relay faces bottom-RIGHT; every other icon faces bottom-LEFT (front -Y).
   Rotate the relay model so its screen (<•••>) is on the -Y front face and its two cream ports stick out
   on ±X, like icon_caddy. Keep the logo on top. Then set NODE_TURN relay to 0 in diagram.py (it was -90
   to line the old ±Y ports up with pipes) and change node rc's "turn" in ecosystem-future.json from 0 to
   90, so it still lines up with its vertical pipe.

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 api webhook loadbalancer switch cicd monitoring logs bell search trash os-android os-linux os-windows os-macos relay
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
  just icons-diagram relay-solo   (the relay must sit on its pipe with ports along the pipe)
Look at each PNG (light + dark, 2.5D and flat), iterate at most 3 times per icon. Report per item
done / NOT DONE + why, and the gate line.
