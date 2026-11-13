# 012: caddy (redo), certstore, dns (owner 2026-11-12, from approved AI concepts)

Executor: agy. Edit ONLY scripts/icons/blender/build.py (replace the body of icon_caddy; add icon_certstore and
icon_dns + ICONS entries) and scripts/icons/flat.ts (replace FLAT.caddy; add FLAT.certstore, FLAT.dns;
STAMP_KNOCKOUT entries where cream/navy details sit straight on the red body). Do not change other icons,
lighting, palette, camera or gate. Do not commit. Read docs/skill/SKILL.md first.

Owner: the old caddy (the bare Caddy mark as a sculpture) "looked odd and not fitting when used as example in
our project". It must be a DEVICE in the family of icon_relay, icon_modem and icon_server, usable on pipes in
diagrams and animations. The owner picked these AI concept sketches (look at them; they are sketches, do not
copy their gradients or proportions blindly, build them in our house style):
- caddy:     local/icons/rounds/concept-caddy-2/dark/caddy-e.png  (also local/icons/rounds/concept-caddy-1/dark/caddy-e.png)
- certstore: local/icons/rounds/concept-caddy-1/dark/certstore.png (also local/icons/rounds/concept-caddy-2/dark/certstore.png)
- dns:       local/icons/rounds/concept-caddy-1/dark/dns.png       (also local/icons/rounds/concept-caddy-2/dark/dns.png)

Build:
- caddy: a compact red rounded box like icon_relay (same scale and bevel feel), with short thick cream round
  pipe ports sticking out of the left and right sides (same as the relay's ports, so pipes in diagrams plug
  into them). The front face (-Y) has a navy recess plate; on it an inlaid cream emblem: the Caddy mark
  (scripts/icons/brands/caddy.svg via brand_mark(..., role "c", small depth, bevel) like apple_mark_solid) OR,
  if that reads poorly at icon size, a chunky padlock inside an orbit ring with one small ball on the ring.
  Under the emblem three small g status dots. Flat twin: box with lip, side ports, navy panel, cream emblem.
- certstore: a small upright red cabinet on a short cream foot, two drawers (cream handles); the top drawer is
  pulled half open toward the viewer and a cream certificate card with a red round seal (and a short red
  ribbon) stands up out of it. One small g light. Flat twin to match.
- dns: a compact red box; on its top a cream signpost (a post with two arrow-shaped boards pointing in
  different directions); the front face has a navy recess with three short cream lines (an address list) and
  two or three small g dots. Flat twin to match.
House style: chunky, rounded (bevels >= 0.08), at most ~6 parts, no tile, front faces -Y, body red (p), cream
secondary (s/c), navy only in recesses (r), lights g. No text on the objects.

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 caddy certstore dns
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at each PNG (light + dark, 2.5D and flat) and iterate at most 3 times per icon. Report per icon
done / not done + why, and the gate line. A truthful "NOT DONE: <reason>" beats a false "done".
