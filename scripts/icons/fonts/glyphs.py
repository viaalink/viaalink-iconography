"""Turn a few capitals of a brand font into SVG path data (run with Blender), so flat SVGs carry the letters as
shapes instead of depending on the viewer's fonts.
  blender -b --factory-startup -P scripts/icons/fonts/glyphs.py -- SpaceGrotesk-Bold.ttf VIALNK out.json
Paths are in em units: x from 0, baseline at y=0, y grows DOWN (SVG), cap height ~0.7."""
import json, os, sys
import bpy
argv = sys.argv[sys.argv.index("--") + 1:]
font_file, letters, out = argv
here = os.path.dirname(os.path.abspath(__file__))
font = bpy.data.fonts.load(os.path.join(here, font_file))
res = {}
for ch in letters:
    bpy.ops.object.text_add()
    t = bpy.context.object
    t.data.body = ch
    t.data.font = font
    t.data.size = 1.0
    bpy.ops.object.convert(target="CURVE")
    c = bpy.context.object
    d, adv = [], 0.0
    for sp in c.data.splines:
        pts = sp.bezier_points
        if not len(pts):
            continue
        f = lambda v: f"{v.x:.4f} {-v.y:.4f}"
        d.append(f"M{f(pts[0].co)}")
        for a, b in zip(pts, list(pts[1:]) + [pts[0]]):
            d.append(f"C{f(a.handle_right)} {f(b.handle_left)} {f(b.co)}")
        d.append("Z")
    xs = [p.co.x for sp in c.data.splines for p in sp.bezier_points]
    res[ch] = {"d": "".join(d), "x0": round(min(xs), 4), "x1": round(max(xs), 4)}
    bpy.data.objects.remove(c)
json.dump({"font": font_file, "glyphs": res}, open(out, "w"), indent=1)
print("ok", len(res), "glyphs")
