# 009: Ecosystem gaps (owner 2026-11-11: "keep looking, there are more things")

Executor: agy. Edit ONLY scripts/icons/blender/build.py (new icon_* functions + ICONS entries) and
scripts/icons/flat.ts (new FLAT entries; add a STAMP_KNOCKOUT entry when a cream/navy detail sits
straight on the red body, see the existing database/error/warning entries). Do not change existing
icons, lighting, palette, camera or gate. Do not commit. Read docs/skill/SKILL.md
first. For style, look at icon_nas, icon_server, icon_lock, icon_cli, icon_phone and viaalink_phone()
(2.5D), and at the FLAT entries nas, cli, lock and phone.

House style: chunky, rounded (bevels ≥ 0.08), at most ~5 parts, front faces -Y, body red (p), cream
panels (s/c), navy only in recesses/screens (r), glyphs via the glyph/emboss helpers (single smooth
outlines, no thin line-work). Any phone is the canonical viaalink_phone(...). No brand logos except
the ones already in scripts/icons/brands.

New icons (a 2.5D model and a flat twin each, same name in both):
- desktop: a monitor on a stand, the screen showing the Viaalink app (logo + text lines, as the
  diagram glyph "desktop" in scripts/icons/blender/diagram.py does).
- tablet: a landscape tablet (red body, navy screen with two cream text blocks).
- browser-ext: a puzzle piece (red) with a small cream Viaalink chevron/logo on it.
- vscode: a code editor window (red frame, navy pane) showing "</>" in cream. NOT Microsoft's logo.
- mail: an envelope (red) with a cream flap line.
- calendar: a desk calendar (red binding rings on top, cream page with a grid and one red day).
- qr-pair: a QR code tile (cream with navy squares; three finder squares) with a small red link
  chain badge in the corner.
- bluetooth: a rounded red disc with the cream Bluetooth rune (the two-triangle B, drawn as one
  smooth outline).
- wifi: three cream arcs plus a dot on a red rounded tile.
- license: a key (red bow with a cream hole, cream bit) lying over a small cream card.
- payment: a credit card (red) with a navy stripe and a cream chip.
- upload / download: a red rounded tray with a cream arrow up (upload) / down (download).
- sync: two curved red arrows forming a circle around a cream dot.
- backup: a database-like cylinder (red) with a cream circular arrow on the front.
- voice-profile: a person bust (cream head) with a red waveform badge (3–5 bars) at the shoulder.
- video: a red video camera body with a navy lens and a small cream record dot.

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 desktop tablet browser-ext vscode mail calendar qr-pair bluetooth wifi license payment upload download sync backup voice-profile video
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at each PNG (light + dark, 2.5D and flat) and iterate at most 3 times per icon. Report per icon
done / not done + why, and the gate line. A truthful "NOT DONE: <reason>" beats a false "done".
