# 013: weakest icons from the expert vision review (owner 2026-11-12: "b")

Executor: agy. Edit ONLY the functions/entries named below in scripts/icons/blender/build.py and
scripts/icons/flat.ts (+ STAMP_KNOCKOUT where needed). Do NOT change the ROLES palette, lighting, camera,
gate, or any other icon. Do not commit. Read docs/skill/SKILL.md first, especially
"The icon IS the object". References the owner loves: sync, phone, mcp-a (plug with the Viaalink mark).
Rule of thumb from the review: at most TWO ideas per icon, readable at 48 px; the flat twin must be the
same object as the 2.5D one.

Fix:
1. backup (2.5D): reads as a cooking pot. Keep the database-like cylinder but add two clear disk seams
   (like icon_database) and make the cream circular restore arrow LARGE and central on the front face,
   as the flat twin already has it.
2. transcribe (2.5D + flat): now a near clone of record. Make the subject the conversion itself: a red
   waveform block on the left, a cream arrow, and a cream page with 3 text lines on the right. NO phone.
3. minutes (2.5D + flat): now a near clone of record. Make it a red clipboard/page object with 3–4 cream
   timestamp lines (a short dot + a line each) and the small Viaalink mark at the top. NO phone.
   (record stays the phone with the record dot: do not change record.)
4. page (2.5D + flat): reads as an ID card. Make it a personal web page: a page with a header strip, a round
   avatar, and two content blocks (like a tiny profile page), no browser chrome beyond a thin top bar.
5. social (2.5D + flat): too busy. Reduce to two ideas: a phone (canonical viaalink_phone) with ONE big
   chat bubble beside it (no second person).
6. github (flat only): the flat sits on a disc and the owner said it "looks like a monster". Make the flat
   the same object as the 2.5D github: the mark itself, solid red with the lip, no disc behind it.
7. cli (flat only): the flat reads as a typewriter. Draw it as the same laptop as the 2.5D: screen with
   `>` and the cursor on a trapezoid base, one hinge.
8. raspberrypi (flat only): the outline circles read as bubbles. Fill the drupelets solid red with a
   darker-red lip/gap, keep the cream leaves.
9. os-windows (2.5D + flat): make the 2.5D four panes sit in the same 3/4 camera as the other icons (no
   own skew); remove the small centre dot in all variants (it shows on dark but not on light).

Verify:
  just icons-blender local/icons/rounds/25d-b7 --samples 48 backup transcribe minutes page social os-windows
  just icons-flat local/icons/rounds/flat-r9
  just icons-blender-gate   (must print GATE: pass)
Look at each PNG (light + dark, 2.5D and flat) and iterate at most 3 times per icon. Report per icon
done / not done + why, and the gate line. A truthful "NOT DONE: <reason>" beats a false "done".
