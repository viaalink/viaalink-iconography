"""
Deterministic 2.5D icons in Blender: one model per icon, colours by ROLE.

  blender -b --factory-startup -P scripts/icons/blender/build.py -- --out <dir> [--mode dark|light|both] [--samples 96] [name ...]

Same camera, light, bevel and palette for every icon, so the set is a family by
construction and light/dark is only a palette swap on the same geometry.
Roles match the flat twins (scripts/icons/flat.ts):
  p  primary body      s  secondary parts (shackle, phone shell)
  r  recessed cavity   c  interior cream detail (keys, text, rings)
Writes <out>/<mode>/<name>.png (transparent, 1024 px). Normalise afterwards with
`just icons-normalize <out>` so the margin matches the AI rounds.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def opt(k, d):
    if f"--{k}" in argv:
        i = argv.index(f"--{k}")
        v = argv[i + 1]
        del argv[i : i + 2]
        return v
    return d


OUT = opt("out", "local/icons/rounds/25d-b1-blender")
MODE = opt("mode", "both")
SAMPLES = int(opt("samples", "96"))
AZIMUTH = float(opt("azimuth", "35"))
KEY = float(opt("key", "740"))  # key light energy (calibrated with the `calib` model)
WORLD = float(opt("world", "0.22"))
GLOW = float(opt("glow", "0.15"))
CREAM_ALBEDO = float(opt("cream", "0.88"))
NAVY_LIFT = float(opt("navy", "2.4"))  # owner 2026-11-11: light-mode navy looked black; recesses (r) stay dark  # calibrated with `calib` (bun local/icons/sample.ts)  # emission of screen glyphs (role g)
ICON_AZIMUTH = {}
ICON_KEY_TURN = {}
CURRENT = ""
FROZEN: set = set()  # object names turn() must not move (diagram.py fills this per node)
# Brand fonts (viaalink.com/brand), shipped with the pipeline (OFL, scripts/icons/fonts): IBM Plex Mono for
# the `> via` prompts and other mono text, Space Grotesk for letters (owner 2026-11-13: use the brand fonts)
FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
FONT = opt("font", os.environ.get("VIA_ICON_FONT", os.path.join(FONTS, "IBMPlexMono-Bold.ttf")))
SANS_FONT = os.path.join(FONTS, "SpaceGrotesk-Bold.ttf")
NAMES = [a for a in argv if not a.startswith("--")]

# ---------------------------------------------------------------- palette
HEX = {
    "red": "#F73F3F",
    "redDeep": "#D62828",
    "coral": "#FF6B6B",
    "warm": "#E04A46",  # owner 2026-11-11: the red of the approved hero desk scene (lit ≈ #D84848, sides ≈ #A81818); salmon read pink
    "navy": "#13223A",
    "slate": "#1C2B45",
    "cream": "#F6F3EE",
}
PALETTES = {
    # g = screen glyph: cream that glows a little, so it reads cream on a shaded face
    # owner 2026-11-11: "I like the old colours better" — the AI set used warm coral + cream on BOTH
    # page colours, so light and dark share one palette (navy only in recesses)
    "dark": {"p": HEX["warm"], "s": HEX["cream"], "r": HEX["slate"], "c": HEX["cream"], "g": HEX["cream"], "k": HEX["warm"]},
    "light": {"p": HEX["warm"], "s": HEX["cream"], "r": HEX["slate"], "c": HEX["cream"], "g": HEX["cream"], "k": HEX["warm"]},
}  # k = accent rim: contrasts with the secondary body in both modes (cream on navy, coral on cream)


def lin(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


MATS = {}


def material(role):
    if role in MATS:
        return MATS[role]
    m = bpy.data.materials.new(f"role-{role}")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    # agy 2026-11-11: matte, almost no white sheen (the sheen washed coral pink)
    b.inputs["Roughness"].default_value = {"p": 0.78, "s": 0.82, "c": 0.82, "g": 0.85, "r": 0.72}.get(role.partition(":")[0], 0.8)
    b.inputs["Coat Weight"].default_value = 0.0
    b.inputs["Specular IOR Level"].default_value = {"p": 0.06, "s": 0.04, "c": 0.04, "g": 0.0, "r": 0.12}.get(role.partition(":")[0], 0.05)
    if role == "g":  # screen glyphs: lit from inside, never grey
        b.inputs["Emission Strength"].default_value = GLOW
    if role == "g:flesh":  # the apple's bitten flesh sits on the shaded side: brighter self-light
        b.inputs["Emission Strength"].default_value = 0.55
    b.inputs["Coat Roughness"].default_value = 0.35
    MATS[role] = m
    return m


def paint(mode):
    for key, m in MATS.items():
        # "c:dim" = role c at a lower albedo, for large cream areas facing the key light (globe
        # land clipped to white at the shared cream albedo)
        role, _, variant = key.partition(":")
        b = m.node_tree.nodes["Principled BSDF"]
        col = lin(PALETTES[mode][role])
        if PALETTES[mode][role] == HEX["cream"]:  # lit cream top must land ON #F6F3EE, not above it
            col = tuple(c * CREAM_ALBEDO * (0.86 if variant == "dim" else 1.0) for c in col[:3]) + (1.0,)
        if role == "s" and PALETTES[mode][role] == HEX["navy"]:  # navy parts read navy on screen, not black
            col = tuple(min(1.0, c * NAVY_LIFT) for c in col[:3]) + (1.0,)
        b.inputs["Base Color"].default_value = col
        b.inputs["Emission Color"].default_value = lin(PALETTES[mode][role])


# ---------------------------------------------------------------- primitives
def finish(o, role, bevel=0.0, segs=8):
    if bevel > 0:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = max(segs, 12)  # agy: no faceting on pill ends
        mod.limit_method = "ANGLE"
        mod.harden_normals = False
    o.data.materials.append(material(role))
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def box(size, loc, role, bevel=0.08, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return finish(o, role, min(bevel, min(size) / 2 - 1e-3))


def cyl(r, depth, loc, role, bevel=0.03, rot=(0, 0, 0), verts=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    return finish(bpy.context.object, role, min(bevel, depth / 2 - 1e-3), 6)


def torus(R, r, loc, role, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot,
                                     major_segments=96, minor_segments=32)
    return finish(bpy.context.object, role)


def cut(target, cutter):
    """Boolean difference; the cutter is removed."""
    for m in cutter.data.materials:
        if m.name not in target.data.materials:
            target.data.materials.append(m)
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    if hasattr(mod, "material_mode"):
        mod.material_mode = "TRANSFER"
    mod.object = cutter
    # the bevel must run before the cut so the recess keeps a crisp rim
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=len(target.modifiers) - 1)
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    return target


def arc(R, z, n=24):
    """Upper half circle in XZ from (-R, z) over the top to (R, z)."""
    return [(-R * math.cos(math.pi * k / n), 0, z + R * math.sin(math.pi * k / n)) for k in range(1, n)]


def tube(points, r, role):
    """One seamless round tube along a polyline (shackles, cables)."""
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, (x, y, z) in zip(sp.points, points):
        p.co = (x, y, z, 1)
    cu.bevel_depth = r
    cu.bevel_resolution = 14
    cu.use_fill_caps = True
    o = bpy.data.objects.new("tube", cu)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(material(role))
    return o


def smooth(o, angle=40):
    """Smooth by angle: keeps the boolean rims crisp without shading smudges."""
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))


def text(s, size, loc, rot, role, depth=0.02):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    t = bpy.context.object
    t.data.body = s
    t.data.font = bpy.data.fonts.load(FONT, check_existing=True)
    t.data.size = size
    t.data.extrude = depth
    t.data.bevel_depth = 0.004
    t.data.align_x = "LEFT"
    t.data.align_y = "CENTER"
    t.data.materials.append(material(role))
    return t


def rr_profile(w, h, r, n=12):
    """Rounded rectangle outline in XY, centred."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def keyhole_profile(R, w_top, w_bot, h, n=40):
    """Circle (radius R, centre 0,0) over a trapezoid reaching down to y=-h; CCW."""
    t = math.acos(min(1.0, w_top / (2 * R)))
    a0, a1 = -t, math.pi + t
    pts = [(w_bot / 2, -h)]
    pts += [(R * math.cos(a0 + (a1 - a0) * k / n), R * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
    pts.append((-w_bot / 2, -h))
    return pts


def rim(outer, inner, depth, loc, role="c", rot=(0, 0, 0)):
    """A thin raised frame (outer minus inner profile): the cream accent around a sunk port."""
    o = plate(outer, depth, loc, role, rot=rot, edge=0.012)
    cut(o, plate(inner, depth * 4, loc, role, rot=rot) if rot == (0, 0, 0) else plate(inner, depth * 4, loc, role, rot=rot))
    return o


def round_corners(pts_r, n=16):
    """2D polygon [(x, y, r), ...] with exact tangent circular arcs at corners with r > 0."""
    m = len(pts_r)
    out = []
    for i in range(m):
        ax, ay, _ = pts_r[(i - 1) % m]
        bx, by, r = pts_r[i]
        cx, cy, _ = pts_r[(i + 1) % m]
        if r <= 0:
            out.append((bx, by))
            continue
        A, B, C = Vector((ax, ay)), Vector((bx, by)), Vector((cx, cy))
        u1, u2 = (A - B).normalized(), (C - B).normalized()
        half = math.acos(max(-1.0, min(1.0, u1.dot(u2)))) / 2
        if half < 1e-3 or abs(half - math.pi / 2) < 1e-4:
            out.append((bx, by))
            continue
        d = min(r / math.tan(half), (A - B).length * 0.45, (C - B).length * 0.45)
        r_eff = d * math.tan(half)
        T1, T2 = B + u1 * d, B + u2 * d
        O = B + (u1 + u2).normalized() * (r_eff / math.sin(half))
        a1, a2 = math.atan2((T1 - O).y, (T1 - O).x), math.atan2((T2 - O).y, (T2 - O).x)
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            a = a1 + da * k / n
            out.append((O.x + r_eff * math.cos(a), O.y + r_eff * math.sin(a)))
    return out


def bubble_profile(w, h, r, tx0, tx1, tip_x, tip_y):
    """Rounded rectangle speech bubble with a bottom tail as one seamless 2D outline."""
    return round_corners([
        (-w / 2, -h / 2, r),
        (tx0, -h / 2, 0.09),
        (tip_x, tip_y, 0.09),
        (tx1, -h / 2, 0.09),
        (w / 2, -h / 2, r),
        (w / 2, h / 2, r),
        (-w / 2, h / 2, r),
    ], 20)


def plate(profile, depth, loc, role, rot=(0, 0, 0), edge=0.0, clean=False):
    """Extrude a 2D profile (XY) by `depth` along +Z, then place it."""
    pts = []
    for p in profile:
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-4:
            pts.append(p)
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= 1e-4:
        pts.pop()
    area2 = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area2 < 0:
        pts.reverse()
    profile = pts
    me = bpy.data.meshes.new("plate")
    n = len(profile)
    verts = [(x, y, 0) for x, y in profile] + [(x, y, depth) for x, y in profile]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new("plate", me)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    finish(o, role, edge, 4)
    if clean:  # concave ngon caps (✦, check, bubbles) shade with creases: guard-inset and triangulate caps AFTER bevel
        if "bevel" in o.modifiers:
            import bmesh
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier="bevel")
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bm.normal_update()
            caps = [f for f in bm.faces if abs(f.normal.z) > 0.95 and len(f.verts) > 4]
            res = bmesh.ops.triangulate(bm, faces=caps)
            cap_tris = set(res["faces"])
            for f in bm.faces:
                f.smooth = f not in cap_tris
            bm.to_mesh(o.data)
            bm.free()
        else:
            for f in me.polygons:
                f.use_smooth = False
            tri = o.modifiers.new("tri", "TRIANGULATE")
            tri.min_vertices = 5
    else:
        for f in me.polygons:
            f.use_smooth = False
    return o


# ---------------------------------------------------------------- icons
D2R = math.radians


def icon_cli():
    box((2.6, 1.75, 0.34), (0, -0.6, 0.17), "p", 0.12)
    # keyboard bed: 4 + 4 aligned key columns and a wide space bar spanning the key area
    for y in (-0.42, -0.86):
        for i in range(4):
            box((0.48, 0.36, 0.14), (-0.84 + i * 0.56, y, 0.39), "c", 0.06)
    box((2.16, 0.3, 0.14), (0.0, -1.28, 0.39), "c", 0.06)  # space bar spanning the 4 columns
    tilt = D2R(-6)
    hinge = Vector((0, 0.2, 0.22))
    R = __import__("mathutils").Euler((tilt, 0, 0)).to_matrix()
    def on_lid(x, y, z):  # lid-local (x across, y out of screen toward -Y, z up from hinge)
        return hinge + R @ Vector((x, y, z))
    rot = (D2R(90) + tilt, 0, 0)
    box((2.6, 0.3, 1.95), on_lid(0, 0, 0.98), "p", 0.12, rot=(tilt, 0, 0))
    plate(rr_profile(2.2, 1.55, 0.14), 0.02, on_lid(0, -0.15, 1.0), "r", rot=rot)
    # terminal window title bar: three dots (red + two cream) and a divider line
    for k, role in enumerate(("p", "g", "g")):
        cyl(0.075, 0.03, on_lid(-0.84 + k * 0.24, -0.17, 1.54), role, 0.014, rot=rot)
    box((2.08, 0.02, 0.035), on_lid(0, -0.17, 1.34), "g", 0.008, rot=(tilt, 0, 0))
    text(">", 0.58, on_lid(-0.88, -0.165, 0.81), rot, "g", 0.02)
    t = text("via", 0.64, on_lid(-0.46, -0.165, 0.86), rot, "g", 0.02)
    bpy.context.view_layer.update()
    box((0.24, 0.03, 0.38), on_lid(-0.46 + t.dimensions.x + 0.30, -0.17, 0.90), "g", 0.014, rot=(tilt, 0, 0))


def icon_lock():
    """Matches the approved AI lock (25d-r1): near-square body, thick cream shackle,
    big keyhole sunk into the face with a thin raised cream rim."""
    W, D, H = 1.75, 0.95, 1.7
    body = box((W, D, H), (0, 0, H / 2), "p", 0.3)
    # shackle: thick half-torus + straight legs that disappear into the top
    tube([(-0.5, 0, H - 0.15), (-0.5, 0, H + 0.3)] + arc(0.5, H + 0.3) + [(0.5, 0, H - 0.15)], 0.17, "s")
    # keyhole, on the -Y face
    face = -D / 2
    rot = (D2R(90), 0, 0)
    cz = H * 0.56
    inner = keyhole_profile(0.21, 0.15, 0.3, 0.52)
    outer = keyhole_profile(0.29, 0.29, 0.45, 0.61)
    cut(body, plate(keyhole_profile(0.216, 0.156, 0.306, 0.524), 0.5, (0, face + 0.14, cz), "r", rot=rot))
    sleeve = plate(keyhole_profile(0.25, 0.2, 0.36, 0.56), 0.135, (0, face + 0.135, cz), "r", rot=rot)
    cut(sleeve, plate(inner, 0.4, (0, face + 0.2, cz), "r", rot=rot))
    plate(inner, 0.02, (0, face + 0.13, cz), "r", rot=rot)  # floor of the cavity
    rim = plate(outer, 0.05, (0, face + 0.025, cz), "c", rot=rot, edge=0.012)
    cut(rim, plate(inner, 0.3, (0, face + 0.1, cz), "c", rot=rot))
    smooth(body)


def phone_app(screen_fn):
    """The Viaalink app on a phone (record/keep share it). In scenes and diagrams it stands on a
    little stand on the desk; the icon has no stand, like call, transcribe and the flat twins."""
    if globals().get("VIA_IMPORT_ONLY"):
        box((1.2, 0.95, 0.24), (0, 0.15, 0.12), "s", 0.1)  # stand
    ph = Device(1.45, 2.5, 0.34, "p", screen=(0.13, 0.13, 0.26, 0.15), z0=0.18, y=-0.05, bevel=0.28)
    box((0.38, 0.1, 0.07), (0, ph.face + 0.03, 0.18 + 2.37), "p", 0.035)  # notch
    screen_fn(ph)
    return ph


def viaalink_phone(cue=None, x=0.0, y=0.0, z0=None, stand=None):
    """The canonical Viaalink phone (owner, W-140): one screen used everywhere — the real
    Viaalink logo (cream) at the top, a red record button below it, then text lines top to
    bottom. Variants only add a small role cue:
      cue=None        record (the plain app)
      cue="audio"     transcribe: an audio pod plugged into the left side
      cue="lock"      keep (minutes): a cream padlock badge at the front bottom-right
    `stand` (default: only in scenes/diagrams) puts it on the little desk stand.
    Returns the Device, so callers can place more on the screen with dev.at(u, v)."""
    if stand is None:
        stand = bool(globals().get("VIA_IMPORT_ONLY"))
    if z0 is None:
        z0 = 0.18 if stand else 0.0
    if stand:
        box((1.2, 0.95, 0.24), (x, y + 0.2, 0.12), "s", 0.1)
    ph = Device(1.55, 2.6, 0.36, "p", screen=(0.15, 0.15, 0.25, 0.16), x=x, y=y, z0=z0, bevel=0.28)
    box((0.42, 0.12, 0.08), (x, ph.face + 0.03, z0 + 2.47), "p", 0.04)  # earpiece
    # 1. the real logo, cream, printed flat on the screen
    lx, ly, lz = ph.at(0, 0.33)
    m = logo(ph.sw * 0.62, (lx, ph.floor - 0.035, lz), "g", 0.04, rot=FACE, soft=False)  # centred on its depth: sits proud of the screen plate
    # the SVG curve has duplicate points: as a raw curve it renders dark slits (agy). Mesh it clean.
    import bmesh
    bpy.ops.object.select_all(action="DESELECT")
    m.select_set(True)
    bpy.context.view_layer.objects.active = m
    bpy.ops.object.convert(target="MESH")
    bm = bmesh.new()
    bm.from_mesh(m.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(m.data)
    bm.free()
    for f in m.data.polygons:
        f.use_smooth = False
    # 2. the record button: cream ring, dark moat, red button
    bx, by, bz = ph.at(0, 0.03)
    torus(0.26, 0.05, (bx, ph.floor - 0.035, bz), "c", rot=FACE)
    cyl(0.17, 0.08, (bx, ph.floor - 0.045, bz), "p", 0.03, rot=FACE)
    # 3. text lines, top to bottom
    right = 0.06 if cue == "lock" else 0.3  # the padlock badge covers the lower right
    for v, u0, u1 in ((-0.22, -0.3, right), (-0.31, -0.3, right), (-0.4, -0.3, min(0.12, right - 0.08))):
        bar(ph, u0, u1, v, 0.036)
    if cue == "audio":
        px = x - 1.15
        box((0.9, 0.55, 1.05), (px, y + 0.08, z0 + 1.3), "s", 0.22)
        for k, hgt in ((-1, 0.34), (0, 0.6), (1, 0.34)):
            box((0.13, 0.08, hgt), (px + k * 0.19, y - 0.22, z0 + 1.3), "p", 0.06)
    elif cue == "lock":
        padlock(x + 0.62, ph.face - 0.22, z0 + 0.42, 1.0, "s", "r")
    return ph


def icon_record():
    """Record: the canonical Viaalink phone (logo, record button, text lines)."""
    viaalink_phone()


# ---------------------------------------------------------------- shared parts (icons + scene kit)
FACE = (D2R(90), 0, 0)  # plate rotation: profile XY -> XZ, extruded toward the viewer (-Y)


class Device:
    """Upright slab (phone, card, clipboard) standing on z=0, front face at -Y,
    with a sunk screen. `at(x, z, out)` gives a point on the screen floor."""

    def __init__(self, w, h, d, role="p", screen=(0.16, 0.16, 0.16, 0.16), bevel=None, x=0.0, y=0.0, z0=0.0, sink=0.06):
        self.w, self.h, self.d = w, h, d
        self.x, self.y, self.z0 = x, y, z0
        self.body = box((w, d, h), (x, y, z0 + h / 2), role, bevel if bevel is not None else min(w, h) * 0.13)
        l, r_, t, b = screen
        sw, sh = w - l - r_, h - t - b
        self.cx, self.cz = x + (l - r_) / 2, z0 + b + sh / 2
        self.sw, self.sh = sw, sh
        self.face = y - d / 2
        self.floor = self.face + sink
        prof = rr_profile(sw, sh, min(sw, sh) * 0.1)
        cut(self.body, plate(prof, 0.6, (self.cx, self.floor, self.cz), "r", rot=FACE))
        plate(prof, 0.02, (self.cx, self.floor + 0.002, self.cz), "r", rot=FACE)
        smooth(self.body)

    def at(self, u, v, out=0.0):
        """u, v in screen units (-0.5..0.5) -> world point just above the screen floor."""
        return (self.cx + u * self.sw, self.floor - out, self.cz + v * self.sh)


def stroke_outline(pts, w, n=16):
    """Outline of a thick polyline with round outer joins and round caps, as ONE closed 2D profile
    (agy: glyphs must be single smooth shapes, no overlapping capsules with seams)."""
    P = [Vector((x, y)) for x, y in pts]
    h = w / 2
    norm = lambda d: Vector((-d.y, d.x)).normalized()
    left, right = [], []
    for i, p in enumerate(P):
        if i == 0:
            nrm = norm(P[1] - P[0]); left.append(p + nrm * h); right.append(p - nrm * h); continue
        if i == len(P) - 1:
            nrm = norm(P[-1] - P[-2]); left.append(p + nrm * h); right.append(p - nrm * h); continue
        d1, d2 = (p - P[i - 1]).normalized(), (P[i + 1] - p).normalized()
        n1, n2 = norm(d1), norm(d2)
        m = (n1 + n2).normalized()
        k = h / max(m.dot(n1), 0.35)
        turn = d1.x * d2.y - d1.y * d2.x
        if turn > 1e-4:
            c_in = p + m * k
            left.extend(
                Vector(q)
                for q in round_corners(
                    [(P[i - 1].x + n1.x * h, P[i - 1].y + n1.y * h, 0), (c_in.x, c_in.y, h * 0.45), (P[i + 1].x + n2.x * h, P[i + 1].y + n2.y * h, 0)],
                    12,
                )[1:-1]
            )
            a1, a2 = math.atan2(-n1.y, -n1.x), math.atan2(-n2.y, -n2.x)
            da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
            right.extend(p + Vector((math.cos(a1 + da * t / n), math.sin(a1 + da * t / n))) * h for t in range(n + 1))
        elif turn < -1e-4:
            a1, a2 = math.atan2(n1.y, n1.x), math.atan2(n2.y, n2.x)
            da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
            left.extend(p + Vector((math.cos(a1 + da * t / n), math.sin(a1 + da * t / n))) * h for t in range(n + 1))
            c_in = p - m * k
            right.extend(
                Vector(q)
                for q in round_corners(
                    [(P[i - 1].x - n1.x * h, P[i - 1].y - n1.y * h, 0), (c_in.x, c_in.y, h * 0.45), (P[i + 1].x - n2.x * h, P[i + 1].y - n2.y * h, 0)],
                    12,
                )[1:-1]
            )
        else:
            left.append(p + m * k); right.append(p - m * k)
    def cap(c, d, sign):
        nrm = norm(d)
        a0 = math.atan2(nrm.y, nrm.x)
        return [c + Vector((math.cos(a0 + sign * math.pi * t / n), math.sin(a0 + sign * math.pi * t / n))) * h for t in range(1, n)]
    end = cap(P[-1], P[-1] - P[-2], -1)
    ring = left + end + right[::-1] + cap(P[0], P[0] - P[1], -1)
    return [(q.x, q.y) for q in ring]


def emboss(dev, pts_uv, w, role="g", depth=0.13):
    """Glyph (chevron, arrow, bar) as one pressed plate with a soft bevel, on a device screen."""
    sw, sh = dev.sw, dev.sh
    loc = Vector(dev.at(0, 0, depth / 2 - 0.01))
    prof = stroke_outline([(u * sw, v * sh) for u, v in pts_uv], w)
    return [plate(prof, depth, (loc.x, loc.y + depth / 2 - 0.01, loc.z), role, rot=FACE, edge=min(0.03, w * 0.25), clean=True)]


def bar(dev, u0, u1, v, r=0.055, role="g"):
    """Text line on a screen: an embossed pill."""
    return emboss(dev, [(u0, v), (u1, v)], r * 2.3, role)


def vbar(dev, u, v0, v1, w=0.11, role="c"):
    x, y, z0 = dev.at(u, v0)
    z1 = dev.at(u, v1)[2]
    return box((w, w, z1 - z0), (x, y - w / 2, (z0 + z1) / 2), role, w * 0.45)


def glyph(dev, pts_uv, r=0.06, role="g"):
    """Polyline glyph (chevron, arrow): embossed pill strokes, ~2.4x r wide."""
    return emboss(dev, pts_uv, r * 2.4, role)


def dot(dev, u, v, r=0.07, role="g"):
    x, y, z = dev.at(u, v)
    return cyl(r, 0.08, (x, y - 0.04, z), role, 0.03, rot=FACE)


def arrow_profile(x_tail, x_wing, y_wing, x_tip, w, n=16):
    """Single closed 2D outline of a right-pointing arrow (shaft + open chevron head), no internal seam."""
    h = w / 2
    P_up, P_tip, P_dn = Vector((x_wing, y_wing)), Vector((x_tip, 0.0)), Vector((x_wing, -y_wing))
    u = (P_up - P_tip).normalized()
    n_out = Vector((u.y, -u.x))  # outward normal on upper wing (up-right)
    n_in = -n_out
    t_join = h * (1 - n_in.y) / u.y
    x_join = P_tip.x + n_in.x * h + t_join * u.x
    # round cap at upper wing tip P_up (from inner edge to outer edge)
    a_up = math.atan2(n_out.y, n_out.x)
    cap_up = [(P_up.x + h * math.cos(a_up + math.pi * k / n), P_up.y + h * math.sin(a_up + math.pi * k / n)) for k in range(n, -1, -1)]
    # round nose at P_tip from +n_out to (n_out.x, -n_out.y)
    a_tip = math.atan2(n_out.y, n_out.x)
    nose = [(P_tip.x + h * math.cos(a_tip - 2 * a_tip * k / n), P_tip.y + h * math.sin(a_tip - 2 * a_tip * k / n)) for k in range(n + 1)]
    # round cap at lower wing tip P_dn (from outer edge to inner edge)
    cap_dn = [(P_dn.x + h * math.cos(-a_up - math.pi * k / n), P_dn.y + h * math.sin(-a_up - math.pi * k / n)) for k in range(n + 1)]
    # round cap at shaft left end (x_tail, 0)
    cap_tail = [(x_tail + h * math.cos(math.pi / 2 + math.pi * k / n), h * math.sin(math.pi / 2 + math.pi * k / n)) for k in range(n + 1)]
    j_up = round_corners([(x_tail, h, 0), (x_join, h, h * 0.35), (cap_up[0][0], cap_up[0][1], 0)], 8)[1:-1]
    j_dn = round_corners([(cap_dn[-1][0], cap_dn[-1][1], 0), (x_join, -h, h * 0.35), (x_tail, -h, 0)], 8)[1:-1]
    pts = [*j_up, *cap_up, *nose, *cap_dn, *j_dn, *cap_tail[::-1]]
    return pts[::-1]


def icon_transcribe():
    """Transcribe: speech-to-text conversion — a red waveform block on the left, a cream arrow,
    and a cream page with 3 text lines on the right."""
    cz = 1.04
    # 1. Left: red waveform block with 3 bold cream vertical bars
    wx, wd = -1.12, 0.42
    box((1.20, wd, 1.62), (wx, 0.0, cz), "p", 0.22)
    wf = -wd / 2
    for dx, hgt in ((-0.32, 0.50), (0.0, 1.02), (0.32, 0.62)):
        bar_prof = stroke_outline([(dx, -hgt / 2), (dx, hgt / 2)], 0.175)
        plate(bar_prof, 0.08, (wx, wf + 0.02, cz), "c", rot=FACE, edge=0.025, clean=True)
    # 2. Middle: chunky cream arrow pointing right
    arr = arrow_profile(-0.25, 0.02, 0.28, 0.29, 0.20)
    plate(arr, 0.38, (-0.02, 0.19, cz), "s", rot=FACE, edge=0.05, clean=True)
    # 3. Right: cream page with 3 staggered dark text lines
    px, pw, pd, ph = 1.14, 1.28, 0.42, 1.84
    box((pw, pd, ph), (px, 0.0, cz), "s", 0.20)
    pf = -pd / 2
    for dz, lw in ((0.39, 0.80), (0.0, 0.80), (-0.39, 0.52)):
        line_prof = stroke_outline([(-0.40, dz), (-0.40 + lw, dz)], 0.155)
        plate(line_prof, 0.07, (px, pf + 0.02, cz), "r", rot=FACE, edge=0.02, clean=True)


def icon_minutes():
    """Minutes: red clipboard/page with the small Viaalink mark at the top and 3 cream
    timestamp lines (a short dot + a line each)."""
    cb = Device(1.92, 2.38, 0.28, "p", screen=(0.17, 0.17, 0.32, 0.17))
    box((0.82, 0.42, 0.32), (0, -0.04, 2.37), "s", 0.10)
    box((0.36, 0.32, 0.22), (0, -0.03, 2.57), "s", 0.10)
    lx, _, lz = cb.at(0, 0.30)
    _clean_logo(0.74, (lx, cb.floor - 0.035, lz), "g", 0.04, rot=FACE)
    for v, u1 in ((0.03, 0.32), (-0.17, 0.32), (-0.37, 0.16)):
        dot(cb, -0.32, v, r=0.075, role="g")
        bar(cb, -0.14, u1, v, 0.052, role="g")


def icon_report():
    cb = Device(1.9, 2.35, 0.26, "p", screen=(0.17, 0.17, 0.32, 0.17))
    # clip: cream block with a tab, on the top edge
    box((0.82, 0.42, 0.32), (0, -0.04, 2.34), "s", 0.1)
    box((0.36, 0.32, 0.22), (0, -0.03, 2.54), "s", 0.1)
    # AI summary (agy: bars read as analytics): a ✦ heading and summary lines
    x, y, z = cb.at(-0.25, 0.29, 0.04)
    plate(spark_profile(0.18, 2.7), 0.09, (x, y + 0.04, z), "g", rot=FACE, edge=0.012, clean=True)
    bar(cb, -0.01, 0.3, 0.27, 0.06)
    for v, u1 in ((0.07, 0.3), (-0.1, 0.3), (-0.27, 0.12)):
        bar(cb, -0.3, u1, v, 0.055)


def icon_mcp_a():
    """Connect (MCP), after the owner's favourite r6 render: angular agent plug (front-left)
    with a big '>', dark rods into a Viaalink socket (back-right) with a dark sunk port and
    the real logo stamped into its top."""
    plug = Device(1.4, 1.4, 0.95, "p", screen=(0.17, 0.17, 0.17, 0.17), y=-0.68, bevel=0.15)  # agy: shorter prongs
    glyph(plug, [(-0.13, 0.22), (0.13, 0.0), (-0.13, -0.22)], 0.1)
    H = 1.4
    sock = box((1.35, 1.05, H), (0, 1.0, 0.75), "s", 0.15)
    port = rr_profile(0.92, 0.92, 0.14)
    cut(sock, plate(port, 0.5, (0, 0.475 + 0.09, 0.75), "r", rot=FACE))
    plate(port, 0.02, (0, 0.475 + 0.092, 0.75), "r", rot=FACE)
    rim(rr_profile(1.12, 1.12, 0.2), port, 0.035, (0, 0.475 + 0.005, 0.75), "k", rot=FACE)  # accent frame: the connect point
    m = logo(0.88, (0, 1.0, 0.75 + H / 2 - 0.035), "p", 0.3, soft=False)
    stamp(sock, m)
    logo(0.88, (0, 1.0, 0.75 + H / 2 - 0.03), "p", 0.026, soft=False)  # coral inlay: contrast on cream
    for x, z in ((-0.23, 0.88), (0.23, 0.88)):
        cyl(0.11, 0.85, (x, 0.22, z), "c", 0.025, rot=(D2R(90), 0, 0))  # two visible cream rods, thicker
        cyl(0.15, 0.06, (x, 0.55, z), "r", 0.02, rot=(D2R(90), 0, 0))  # dark ring where they enter


def icon_phone():
    """Secure page on a phone (like the flat twin): cream card on the screen with a padlock
    inside it and two red text lines under the lock."""
    if globals().get("VIA_IMPORT_ONLY"):  # stand in scenes/diagrams only (see phone_app)
        box((1.2, 0.95, 0.24), (0, 0.15, 0.12), "s", 0.1)
    ph = Device(1.55, 2.55, 0.36, "p", screen=(0.14, 0.14, 0.26, 0.15), z0=0.18, y=-0.05, bevel=0.28)
    box((0.38, 0.1, 0.07), (0, ph.face + 0.03, 0.18 + 2.41), "p", 0.035)  # earpiece
    x, y, z = ph.at(0, 0.0)
    box((0.96, 0.08, 1.54), (x, y - 0.04, z), "c", 0.12)  # secure page card
    yc = y - 0.08  # card front
    lx, lz = x, z + 0.24
    box((0.38, 0.1, 0.3), (lx, yc - 0.05, lz), "p", 0.07)  # padlock body inside the card
    q = 0.1
    tube([(lx - q, yc - 0.05, lz + 0.12), (lx - q, yc - 0.05, lz + 0.2)] + [
        (lx - q * math.cos(math.pi * k / 10), yc - 0.05, lz + 0.2 + q * math.sin(math.pi * k / 10)) for k in range(1, 10)
    ] + [(lx + q, yc - 0.05, lz + 0.2), (lx + q, yc - 0.05, lz + 0.12)], 0.035, "p")
    cyl(0.045, 0.04, (lx, yc - 0.085, lz + 0.03), "c", 0.012, rot=FACE)  # keyhole dot
    for dz, w in ((-0.32, 0.56), (-0.50, 0.38)):
        box((w, 0.06, 0.07), (x - (0.56 - w) / 2, yc - 0.03, z + dz), "p", 0.03)


LOGO_SVG = __import__("os").path.join(__import__("os").path.dirname(__file__), "logo-mark.svg")


def logo(width, loc, role="c", depth=0.07, rot=(0, 0, 0), soft=True):
    """The real Viaalink mark (scripts/icons/blender/logo-mark.svg), extruded as one solid.
    Lies in XY (reads upright toward +Y); `loc` is the centre of its underside."""
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=LOGO_SVG)
    parts = [o for o in bpy.data.objects if o not in before]
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active  # not context.object: that can still be the previous import
    k = width / o.dimensions.x
    o.data.extrude = depth / k / 2
    o.data.bevel_depth = depth / k / 6 if soft else 0.0  # a bevelled cutter self-intersects
    o.data.bevel_resolution = 4
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    o.scale = (k, k, k)
    o.rotation_euler = rot
    o.location = (loc[0], loc[1], loc[2] + depth / 2)
    o.data.materials.clear()
    o.data.materials.append(material(role))
    return o


def icon_relay():
    """Viaalink Relay: logo stamped INTO the top, a narrow screen band across the middle of the -Y
    front face with `<•••>`, and two cream pipe ports sticking out on ±X like icon_caddy."""
    W, D, H = 1.9, 1.45, 1.75
    band = 0.8
    dev = Device(W, H, D, "p", screen=(0.18, 0.18, (H - band) / 2, (H - band) / 2), bevel=0.18)
    # owner: `<•••>` — traffic goes both ways through the relay
    for u in (-0.12, 0.0, 0.12):
        x, y, z = dev.at(u, 0.0)
        box((0.14, 0.16, 0.14), (x, y - 0.06, z), "g", 0.04)
    glyph(dev, [(-0.24, 0.22), (-0.36, 0.0), (-0.24, -0.22)], 0.07, "g")
    glyph(dev, [(0.24, 0.22), (0.36, 0.0), (0.24, -0.22)], 0.07, "g")
    # two cream pipe ports on ±X, like icon_caddy
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, H / 2), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, H / 2), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    # logo stamped into the top
    m = logo(1.08, (0, 0.0, H - 0.035), "p", 0.3, soft=False)
    stamp(dev.body, m)
    logo(1.08, (0, 0.0, H - 0.03), "c", 0.026, soft=False)  # cream inlay on the floor of the stamp


def stamp(body, cutter_curve):
    """Press a curve shape (logo) into a body. Curves from SVG are not watertight, so
    clean the mesh first; a failed boolean would otherwise erase the whole body."""
    import bmesh
    bpy.ops.object.select_all(action="DESELECT")
    cutter_curve.select_set(True)
    bpy.context.view_layer.objects.active = cutter_curve
    bpy.ops.object.convert(target="MESH")
    me = cutter_curve.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    for mod in list(body.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bm_b = bmesh.new()
    bm_b.from_mesh(body.data)
    bm_b.normal_update()
    top_faces = [f for f in bm_b.faces if f.normal.z > 0.999 and f.calc_area() > 0.1]
    if top_faces:
        bmesh.ops.inset_individual(bm_b, faces=top_faces, thickness=0.02, depth=0.0)
    bm_b.to_mesh(body.data)
    bm_b.free()
    before = len(body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
    cut(body, cutter_curve)
    after = len(body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
    if after < before * 0.5:  # boolean ate the body: fall back to a raised logo
        body.modifiers.remove(body.modifiers[-1])
        cutter_curve.hide_render = False
        print("stamp failed; logo raised instead")
        smooth(body)
        return
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    for mod in list(body.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bm_b = bmesh.new()
    bm_b.from_mesh(body.data)
    bm_b.normal_update()
    caps = [f for f in bm_b.faces if f.normal.z > 0.999 and len(f.verts) > 4]
    if caps:
        res = bmesh.ops.triangulate(bm_b, faces=caps)
        for f in res["faces"]:
            f.smooth = False
    bm_b.to_mesh(body.data)
    bm_b.free()
    smooth(body)


def turn(deg):
    """Rotate the whole model about Z (keeps the shared camera; used to match an approved pose)."""
    from mathutils import Matrix
    R = Matrix.Rotation(D2R(deg), 4, "Z")
    bpy.context.view_layer.update()  # matrix_world is stale for objects placed since the last update
    for o in bpy.context.scene.objects:
        if o.parent is None and o.name not in FROZEN:  # diagrams freeze nodes placed earlier
            o.matrix_world = R @ o.matrix_world


def icon_notetaker():
    """Viaalink Notetaker — owner pick (2026-11-11): the original r2 capsule microphone.
    Coral capsule whose upper half is a big sunk grille with three cream slots, a chunky
    U-yoke + stem + pedestal in the secondary role, minutes pad leaning front-right."""
    from mathutils import Matrix
    cyl(0.95, 0.3, (0, 0.1, 0.15), "s", 0.1)
    cyl(0.17, 0.5, (0, 0.1, 0.5), "s", 0.05)
    W = 1.08
    cap = box((W, 0.92, 1.8), (0, 0.1, 1.62), "p", 0.42)
    gp = rr_profile(0.78, 0.68, 0.22)
    face = 0.1 - 0.46
    cut(cap, plate(gp, 0.5, (0, face + 0.08, 1.8), "r", rot=FACE))
    plate(gp, 0.02, (0, face + 0.082, 1.8), "r", rot=FACE)
    smooth(cap)
    for x in (-0.14, 0.14):  # grille: two columns of three short slots (owner example)
        for z in (1.96, 1.8, 1.64):
            box((0.21, 0.12, 0.105), (x, face + 0.02, z), "c", 0.048)  # lit front: c, not g (gate)
    # chunky U-yoke around the lower capsule, legs ending at the pin centre with round caps
    R, z_pin = 0.74, 1.54
    pts = [(-R, 0.1, z_pin), (-R, 0.1, 1.05)] + [(-R * math.cos(math.pi * k / 14), 0.1, 1.05 - 0.36 * math.sin(math.pi * k / 14)) for k in range(1, 14)] + [(R, 0.1, 1.05), (R, 0.1, z_pin)]
    tube(pts, 0.14, "s")
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(sx * R, 0.1, z_pin), segments=32, ring_count=16)
        finish(bpy.context.object, "s")
        cyl(0.11, 0.24, (sx * (R - 0.11), 0.1, z_pin), "s", 0.03, rot=(0, D2R(90), 0))
    if not globals().get("VIA_IMPORT_ONLY"):
        # minutes pad leaning on the pedestal, front-right, facing the viewer
        objs = notepad((0.82, -0.8, 0.0), 0.82, 0.82, lean=16, thick=0.22)
        bpy.context.view_layer.update()
        M = Matrix.Translation((0.85, -0.78, 0)) @ Matrix.Rotation(D2R(14), 4, "Z") @ Matrix.Translation((-0.85, 0.78, 0))
        for o in objs:
            o.matrix_world = M @ o.matrix_world


def notepad(at, w, h, lean=0.0, lines=2, thick=0.16):
    """Coral pad with a cream page and coral lines, standing (leaning back by `lean` degrees)."""
    x0, y0, z0 = at
    objs = [box((w, thick, h), (x0, y0, z0 + h / 2), "p", 0.1)]
    objs.append(box((w - 0.2, 0.05, h - 0.2), (x0, y0 - thick / 2, z0 + h / 2), "c", 0.06))
    for dx in (-w * 0.22, 0.0, w * 0.22):  # spiral rings on top (agy r7: '=' tile was unidentifiable)
        objs.append(cyl(0.035, 0.04, (x0 + dx, y0 - thick / 2 - 0.015, z0 + h - 0.075), "r", 0.008, rot=FACE))
        objs.append(torus(0.07, 0.025, (x0 + dx, y0 - thick / 2 + 0.02, z0 + h - 0.02), "s", rot=(0, D2R(90), 0)))
    for k in range(lines):
        z = z0 + h * (0.62 - 0.22 * k)
        objs.append(box((w * 0.5, 0.05, 0.09), (x0 - w * 0.02, y0 - thick / 2 - 0.04, z), "p", 0.04))
    from mathutils import Matrix
    bpy.context.view_layer.update()
    R = Matrix.Translation((x0, y0, z0)) @ Matrix.Rotation(D2R(-lean), 4, "X") @ Matrix.Translation((-x0, -y0, -z0))
    for o in objs:
        o.matrix_world = R @ o.matrix_world
    return objs


def dotted_dome(c, R, face=-1, reach=0.82, dot=0.036, pitch=0.105):
    """Dark convex grille (r0 studio mic): a slate dome bulging out of a sphere toward -Y,
    with cream dots on a hex grid following its surface, ringed by a cream collar."""
    cx, cy, cz = c
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, location=(cx, cy, cz), segments=64, ring_count=32)
    finish(bpy.context.object, "r")
    lim = R * reach
    row = 0
    z = -lim
    while z <= lim:
        x = -lim + (pitch / 2 if row % 2 else 0)
        while x <= lim:
            if x * x + z * z <= lim * lim:
                y = cy - math.sqrt(max(R * R - x * x - z * z, 0)) - dot * 0.3
                bpy.ops.mesh.primitive_uv_sphere_add(radius=dot, location=(cx + x, y, cz + z), segments=12, ring_count=8)
                finish(bpy.context.object, "c")
            x += pitch
        z += pitch * 0.866
        row += 1


def mic_head(at, R=0.72):
    """Round coral microphone head with the dotted dome on its front."""
    x, y, z = at
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, location=at, segments=64, ring_count=32)
    finish(bpy.context.object, "p")
    dotted_dome((x, y - R * 0.42, z), R * 0.72)
    torus(R * 0.72 * 0.93, 0.05, (x, y - R * 0.42 - R * 0.72 * 0.36, z), "c", rot=FACE)


def icon_notetaker_b():
    """Notetaker: the round r0 microphone holding its minutes pad up in both hands (no pen),
    chunky parts (tubes >= 0.09, slabs >= 0.16)."""
    cyl(0.75, 0.24, (0, 0.35, 0.12), "p", 0.1)
    tube([(0, 0.35, 0.2), (0, 0.4, 0.75), (0, 0.42, 1.0)], 0.14, "p")
    mic_head((0, 0.42, 1.62))
    # pad held upright in front of the stand, page facing the viewer
    px, py, pz, pw, ph = 0.0, -0.72, 0.62, 1.0, 0.92
    box((pw, 0.18, ph), (px, py, pz), "p", 0.08)
    box((pw - 0.2, 0.05, ph - 0.2), (px, py - 0.1, pz - 0.02), "c", 0.04)
    box((0.42, 0.16, 0.14), (px, py - 0.02, pz + ph / 2 + 0.02), "s", 0.05)  # clip
    for k, w in ((0, 0.52), (1, 0.52), (2, 0.34)):
        z = pz + 0.2 - k * 0.2
        tube([(px - 0.26, py - 0.14, z), (px - 0.26 + w, py - 0.14, z)], 0.045, "p")
    # arms from the sides of the head to hands gripping the pad edges
    for sx in (-1, 1):
        hand = (sx * (pw / 2 + 0.02), py - 0.04, pz + 0.12)
        tube([(sx * 0.7, 0.42, 1.6), (sx * 1.0, 0.0, 1.2), (sx * 0.85, -0.5, 0.75), hand], 0.095, "s")
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=hand, segments=32, ring_count=16)
        finish(bpy.context.object, "s")


def icon_notetaker_c():
    """agy's pick: the r0 round dotted-grille head on a coral U-yoke and stand, minutes pad
    front-right. Hardware object, no mascot arms."""
    cyl(0.68, 0.2, (0, 0.2, 0.1), "p", 0.08)
    cyl(0.12, 0.6, (0, 0.2, 0.45), "p", 0.04)
    mic_head((0, 0.2, 1.55))
    R = 0.86
    tube([(-R, 0.2, 1.55)] + [(-R * math.cos(math.pi * k / 16), 0.2, 1.55 - R * math.sin(math.pi * k / 16) * 0.85) for k in range(1, 16)] + [(R, 0.2, 1.55)], 0.11, "p")
    for x in (-R, R):
        cyl(0.17, 0.14, (x, 0.2, 1.55), "p", 0.05, rot=(0, D2R(90), 0))
    # minutes pad grounded front-right, cream sheet, secondary clip
    box((0.72, 0.18, 0.88), (0.85, -0.7, 0.44), "s", 0.07)
    box((0.56, 0.05, 0.66), (0.85, -0.8, 0.42), "c", 0.04)
    box((0.4, 0.16, 0.14), (0.85, -0.74, 0.88), "p", 0.05)  # clip
    for v in (0.55, 0.36):
        tube([(0.68, -0.84, v), (1.02, -0.84, v)], 0.045, "p")


def icon_notetaker_d():
    """agy spec (2026-11-11): upright capsule mic (original Notetaker style) on a U-yoke and
    pedestal; two stubby pill arms from the yoke shoulders, mitten hands holding the minutes
    pad low and front-right so the grille stays clear."""
    from mathutils import Matrix
    cyl(0.72, 0.24, (0, 0, 0.12), "s", 0.06)
    cyl(0.16, 0.26, (0, 0, 0.35), "s", 0.03)
    # squared U-yoke in XZ
    pts = [(-0.64, 0, 1.28), (-0.64, 0, 0.7)] + [(-0.64 * math.cos(math.pi * k / 10), 0, 0.7 - 0.22 * math.sin(math.pi * k / 10)) for k in range(1, 10)] + [(0.64, 0, 0.7), (0.64, 0, 1.28)]
    tube(pts, 0.105, "s")
    for x in (-0.56, 0.56):
        cyl(0.11, 0.1, (x, 0, 1.2), "s", 0.03, rot=(0, D2R(90), 0))
    head = box((0.96, 0.78, 1.42), (0, 0, 1.38), "p", 0.38)
    gp = rr_profile(0.68, 0.74, 0.3)
    cut(head, plate(gp, 0.5, (0, -0.39 + 0.07, 1.54), "r", rot=FACE))
    plate(gp, 0.02, (0, -0.39 + 0.072, 1.54), "r", rot=FACE)
    smooth(head)
    for z in (1.72, 1.54, 1.36):
        box((0.48, 0.08, 0.11), (0, -0.37, z), "g", 0.05)
    # stubby arms + mitten hands
    tube([(-0.68, -0.05, 1.12), (-0.52, -0.3, 0.95), (-0.36, -0.5, 0.78)], 0.13, "p")
    tube([(0.68, -0.05, 1.1), (0.66, -0.3, 0.92), (0.58, -0.52, 0.74)], 0.13, "p")
    for hpos in ((-0.3, -0.56, 0.74), (0.54, -0.58, 0.7)):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=hpos, segments=32, ring_count=16)
        finish(bpy.context.object, "s")
    # notepad, tilted up toward the camera
    c = Vector((0.12, -0.6, 0.68))
    parts = [box((0.78, 0.14, 0.86), tuple(c), "p", 0.09),
             box((0.62, 0.05, 0.64), tuple(c + Vector((0, -0.08, -0.03))), "c", 0.05),
             box((0.34, 0.1, 0.12), tuple(c + Vector((0, -0.02, 0.45))), "s", 0.04),
             box((0.42, 0.05, 0.07), tuple(c + Vector((-0.04, -0.11, 0.1))), "p", 0.03),
             box((0.28, 0.05, 0.07), tuple(c + Vector((-0.11, -0.11, -0.1))), "p", 0.03)]
    bpy.context.view_layer.update()
    M = Matrix.Translation(c) @ Matrix.Rotation(D2R(12), 4, "Z") @ Matrix.Rotation(D2R(-18), 4, "X") @ Matrix.Translation(-c)
    for o in parts:
        o.matrix_world = M @ o.matrix_world


def stadium(L, W, n=16):
    """Closed stadium (chain-link) path in local XZ, long axis X, centred."""
    r, h = W / 2, (L - W) / 2
    pts = []
    for k in range(n + 1):
        a = -math.pi / 2 + math.pi * k / n
        pts.append((h + r * math.cos(a), 0, r * math.sin(a)))
    for k in range(n + 1):
        a = math.pi / 2 + math.pi * k / n
        pts.append((-h + r * math.cos(a), 0, r * math.sin(a)))
    return pts


def ring(points, r, role):
    o = tube(points + [points[0]], r, role)
    o.data.splines[0].use_cyclic_u = True
    return o


def icon_link():
    """Two links of a chain under tension, left to right like the chain in the logo:
    long axis horizontal on screen, links pulled apart until their bends bite."""
    from mathutils import Matrix
    L, W, r = 2.2, 1.15, 0.2
    gap = L - 4 * r  # taut: B's bend presses into A's bend
    a = ring(stadium(L, W, 40), r, "p")  # 40 per bend: no facets on the silhouette
    b = ring(stadium(L, W, 40), r, "s")
    bpy.context.view_layer.update()
    a.matrix_world = Matrix.Translation((-gap / 2, 0, 0))  # upright, hole to the viewer
    b.matrix_world = Matrix.Translation((gap / 2, 0, 0)) @ Matrix.Rotation(D2R(90), 4, "X")  # lying, through A
    bpy.context.view_layer.update()
    M = Matrix.Rotation(D2R(AZIMUTH), 4, "Z")  # long axis = camera's right: horizontal on screen
    # then tilt it up 35° in the picture plane: rising left to right like the flat twin, and it
    # fills the square canvas instead of a thin strip (horizontal it covered 16%, the set ~40%)
    view = Matrix.Rotation(D2R(AZIMUTH), 3, "Z") @ Matrix.Rotation(D2R(60), 3, "X") @ Vector((0, 0, 1))
    M = Matrix.Rotation(D2R(35), 4, view) @ M
    for o in (a, b):
        o.matrix_world = M @ o.matrix_world


def spark_profile(R, p=4.0, n=160):
    """Four-point AI spark (✦): an astroid-like curve with concave sides."""
    w = R * 0.25
    return round_corners([
        (R, 0, R * 0.09), (w, w, R * 0.5),
        (0, R, R * 0.09), (-w, w, R * 0.5),
        (-R, 0, R * 0.09), (-w, -w, R * 0.5),
        (0, -R, R * 0.09), (w, -w, R * 0.5),
    ], 24)


def icon_ai_a():
    """Agent (owner): an AI robot head — rounded head whose face is a screen with '>' and ✦,
    ear bolts on the sides and an antenna with a ball on top."""
    head = Device(1.9, 1.6, 1.25, "p", screen=(0.24, 0.24, 0.24, 0.24), z0=0.0, bevel=0.26)
    chev = stroke_outline([(-0.32 * head.sw, 0.16 * head.sh), (-0.16 * head.sw, 0.0), (-0.32 * head.sw, -0.16 * head.sh)], 0.15)
    plate(chev, 0.04, (head.cx, head.floor + 0.01, head.cz), "g", rot=FACE, edge=0.008, clean=True)
    x, _, z = head.at(0.18, 0.0)
    plate(spark_profile(0.26, 2.7), 0.04, (x, head.floor + 0.01, z), "g", rot=FACE, edge=0.008, clean=True)
    for sx in (-1, 1):  # ear bolts
        cyl(0.3, 0.2, (sx * 1.02, 0, 0.8), "s", 0.06, rot=(0, D2R(90), 0))
        cyl(0.14, 0.26, (sx * 1.06, 0, 0.8), "p", 0.04, rot=(0, D2R(90), 0))
    cyl(0.06, 0.42, (0, 0, 1.78), "s", 0.02)  # antenna
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(0, 0, 2.04), segments=32, ring_count=16)
    finish(bpy.context.object, "p")


def bust(dev, u, v, scale=1.0, role="g"):
    """Person on a screen: round head over smooth rounded shoulders, embossed with a clear neck gap."""
    x, y, z = dev.at(u, v)
    cyl(0.115 * scale, 0.12, (x, y - 0.05, z + 0.21 * scale), role, 0.04, rot=FACE)
    rc = 0.05 * scale
    shoulders = round_corners(
        [(0.32 * scale, 0.0, rc)]
        + [(0.32 * scale * math.cos(t), 0.2 * scale * math.sin(t), 0.0) for t in [math.pi * k / 72 for k in range(14, 59)]]
        + [(-0.32 * scale, 0.0, rc)],
        12,
    )
    plate(shoulders, 0.12, (x, y + 0.01, z - 0.15 * scale), role, rot=FACE, edge=0.025, clean=True)


def icon_social():
    """Viaalink Social: canonical Viaalink phone with ONE big chat bubble beside it."""
    viaalink_phone(x=-0.42)
    bx, by, bz = 0.94, -0.28, 1.72
    plate(bubble_profile(1.30, 0.94, 0.26, -0.42, -0.08, -0.52, -0.76), 0.36, (bx, by + 0.18, bz), "s", rot=FACE, edge=0.08, clean=True)
    for k in (-0.31, 0.0, 0.31):
        cyl(0.095, 0.08, (bx + k, by - 0.20, bz), "p", 0.03, rot=FACE)


def icon_calib():
    """Calibration: a cream (c) and a coral (p) block; sample top / front / side colours."""
    box((1.2, 1.2, 1.2), (-0.8, 0, 0.6), "c", 0.12)
    box((1.2, 1.2, 1.2), (0.8, 0, 0.6), "p", 0.12)


def padlock(x, y, z, s=1.0, role="c", hole="r", rim_role=None, shackle=None):
    """Small padlock badge facing -Y: body, shackle, recessed keyhole. (x, y, z) = body centre."""
    w, d, h = 0.56 * s, 0.3 * s, 0.46 * s
    body = box((w, d, h), (x, y, z), role, 0.1 * s)
    q = 0.16 * s
    tube([(x - q, y, z + h * 0.3), (x - q, y, z + h * 0.5)] + [(x + px, y, z + h * 0.5 + pz) for px, _, pz in arc(q, 0)] + [(x + q, y, z + h * 0.5), (x + q, y, z + h * 0.3)], 0.055 * s, shackle or role)
    if hole and s >= 0.4:
        import bmesh
        bpy.ops.object.select_all(action="DESELECT")
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        for mod in list(body.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bm.normal_update()
        front = [f for f in bm.faces if f.normal.y < -0.999 and f.calc_area() > 0.01 * s * s]
        if front:
            bmesh.ops.inset_individual(bm, faces=front, thickness=0.015 * s, depth=0.0)
        bm.to_mesh(body.data)
        bm.free()
        face = y - d / 2
        sink = 0.04 * s
        cz = z + 0.045 * s
        kh = keyhole_profile(0.068 * s, 0.05 * s, 0.075 * s, 0.16 * s)
        cut(body, plate(kh, 0.2 * s, (x, face + sink, cz), hole, rot=FACE))
        plate(kh, 0.01 * s, (x, face + sink + 0.001, cz), hole, rot=FACE)
        if rim_role:
            kh_out = keyhole_profile(0.095 * s, 0.09 * s, 0.125 * s, 0.19 * s)
            r_plate = plate(kh_out, 0.022 * s, (x, face + 0.008 * s, cz), rim_role, rot=FACE, edge=0.006 * s)
            cut(r_plate, plate(kh, 0.12 * s, (x, face + 0.05 * s, cz), rim_role, rot=FACE))
        bpy.ops.object.select_all(action="DESELECT")
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        for mod in list(body.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bm.normal_update()
        caps = [f for f in bm.faces if f.normal.y < -0.999 and len(f.verts) > 4]
        if caps:
            res = bmesh.ops.triangulate(bm, faces=caps)
            for f in res["faces"]:
                f.smooth = False
        bm.to_mesh(body.data)
        bm.free()
        smooth(body)


WORLD_JSON = __import__("os").path.join(__import__("os").path.dirname(__file__), "..", "world-land.json")


def _in_poly(lon, lat, poly):
    inside = False
    n = len(poly)
    for k in range(n):
        x1, y1 = poly[k]
        x2, y2 = poly[(k + 1) % n]
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def geo(lon, lat):
    """Unit vector for a longitude/latitude (degrees): x toward lon 0, z north."""
    lo, la = D2R(lon), D2R(lat)
    return Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))


def land_shell(c, R, role="c:dim", lift=0.004, thick=0.022, segs=480, rings=240):
    """The continents (scripts/icons/world-land.json) as a thin raised shell on a sphere of
    radius R at c, in the geo frame (x = lon 0, z = north). Faces of a fine UV sphere are kept
    where their centre is land (minus inland seas); the coastline is then relaxed so it reads
    as a smooth outline instead of a pixel staircase, and the land gets a little thickness."""
    import json
    import bmesh
    W = json.load(open(WORLD_JSON))
    polys = [p for p in W["land"].values() if p]
    seas = list(W["seas"].values())
    box_of = lambda p: (min(x for x, _ in p), max(x for x, _ in p), min(y for _, y in p), max(y for _, y in p))
    pb = [(p, box_of(p)) for p in polys]
    sb = [(p, box_of(p)) for p in seas]
    hit = lambda lon, lat, lst: any(b[0] <= lon <= b[1] and b[2] <= lat <= b[3] and _in_poly(lon, lat, p) for p, b in lst)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R + lift, location=(0, 0, 0), segments=segs, ring_count=rings)
    o = bpy.context.object
    bm = bmesh.new()
    bm.from_mesh(o.data)
    drop = []
    for f in bm.faces:
        v = f.calc_center_median().normalized()
        lat = math.degrees(math.asin(max(-1.0, min(1.0, v.z))))
        lon = math.degrees(math.atan2(v.y, v.x))
        if not (hit(lon, lat, pb) and not hit(lon, lat, sb)):
            drop.append(f)
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    edge = [v for v in bm.verts if v.is_boundary]
    for _ in range(8):  # relax the staircase coast, then put it back on the sphere
        bmesh.ops.smooth_vert(bm, verts=edge, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        for v in edge:
            v.co = v.co.normalized() * (R + lift)
    bm.to_mesh(o.data)
    bm.free()
    mod = o.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thick
    mod.offset = 1.0
    o.location = c
    finish(o, role)
    return [o], W


def icon_globe():
    """Globe on a stand (owner, W-140): a real world map — cream continents on the red sphere,
    Europe facing the viewer with a small red marker on the Netherlands, a subtle red grid
    (thin raised equator + meridian), the cream half-ring holder on the +X side, stem, foot."""
    from mathutils import Matrix
    c = Vector((0, 0, 1.6))
    R = 0.98
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, location=tuple(c), segments=96, ring_count=48)
    sphere = finish(bpy.context.object, "p")
    lands, W = land_shell(c, R)
    # subtle grid: thin ridges in the sphere's own red, under the land
    grid = [torus(R - 0.008, 0.022, tuple(c), "p"), torus(R - 0.008, 0.022, tuple(c), "p", rot=(D2R(90), 0, D2R(100)))]
    nl = Vector(W["nl"] and geo(*W["nl"]))
    # Netherlands: a red pin head in a cream collar, so it reads on the coast (land and sea)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=tuple(c + nl * (R + 0.045)), segments=32, ring_count=16)
    marker = finish(bpy.context.object, "p")
    collar = torus(0.075, 0.022, tuple(c + nl * (R + 0.03)), "c")
    collar.rotation_euler = nl.to_track_quat("Z", "Y").to_euler()
    # axial tilt toward the holder, then spin about the tilted pole so Europe faces the camera
    # the map faces the viewer: Europe in the centre of the view, north up on screen. (The
    # holder keeps the classic 20° lean; at icon size the pins read as the stand, not as poles.)
    az = D2R(ICON_AZIMUTH.get(CURRENT or "globe", AZIMUTH))
    cam = Matrix.Rotation(az, 3, "Z") @ Matrix.Rotation(D2R(60), 3, "X")
    to_cam = -(cam @ Vector((0, 0, -1)))
    up = cam @ Vector((0, 1, 0))
    europe = geo(8, 47)
    north = Vector((0, 0, 1))
    n_src = (north - europe * north.dot(europe)).normalized()
    src = Matrix((europe, n_src, europe.cross(n_src))).transposed()
    n_dst = (up - to_cam * up.dot(to_cam)).normalized()
    dst = Matrix((to_cam, n_dst, to_cam.cross(n_dst))).transposed()
    Rm = (dst @ src.transposed()).to_4x4()
    M = Matrix.Translation(c) @ Rm @ Matrix.Translation(-c)
    bpy.context.view_layer.update()
    for o in [sphere, marker, collar] + lands + grid:
        o.matrix_world = M @ o.matrix_world
    # holder: half ring round the +X side along a 20° leaning axis, with round caps and pins
    tilt = D2R(20)
    axis = Vector((math.sin(D2R(25)), -math.cos(D2R(25)), 0))
    T = Matrix.Rotation(tilt, 3, axis)
    pole = T @ Vector((0, 0, 1))
    H = R + 0.2
    eq = T @ Vector((math.cos(D2R(25)), math.sin(D2R(25)), 0))
    pts = [tuple(c + eq * (H * math.sin(math.pi * k / 32)) - pole * (H * math.cos(math.pi * k / 32))) for k in range(33)]
    tube(pts, 0.1, "s")
    for sgn, end in ((-1, pts[0]), (1, pts[-1])):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=end, segments=32, ring_count=16)
        finish(bpy.context.object, "s")
        tube([end, tuple(c + pole * (sgn * (R - 0.12)))], 0.082, "s")
    cyl(0.12, 0.38, (0, 0, 0.29), "s", 0.04)
    cyl(0.72, 0.2, (0, 0, 0.1), "s", 0.08)


def icon_browser():
    """Browser window: coral frame, top bar with three dots and an address pill with a
    padlock, sunk dark page (header, picture, text, button) and a pointer."""
    W, H = 2.7, 2.1
    dev = Device(W, H, 0.42, "p", screen=(0.17, 0.17, 0.52, 0.17))
    zt = H - 0.27
    f = dev.face
    for k in range(3):
        cyl(0.075, 0.08, (-W / 2 + 0.32 + k * 0.24, f - 0.02, zt), "c", 0.03, rot=FACE)
    box((1.45, 0.1, 0.26), (0.38, f - 0.03, zt), "c", 0.12)
    padlock(-0.12, f - 0.07, zt - 0.03, 0.30, "p", None)
    # a real page, like the flat twin: header bar, picture tile (mountain + sun), text lines,
    # a red button, and a pointer over it
    x, y, z = dev.at(0, 0.36)
    box((dev.sw * 0.86, 0.1, 0.13), (x, y - 0.04, z), "g", 0.06)
    x, y, z = dev.at(-0.24, -0.12)
    tile = box((0.86, 0.12, 0.74), (x, y - 0.05, z), "c", 0.08)
    tile_front = y - 0.11
    plate([(-0.32, -0.22), (-0.08, 0.06), (0.06, -0.08), (0.14, 0.0), (0.32, -0.22)], 0.022, (x, tile_front + 0.02, z), "r", rot=FACE)
    sun_prof = [(0.075 * math.cos(2 * math.pi * k / 32), 0.075 * math.sin(2 * math.pi * k / 32)) for k in range(32)]
    plate(sun_prof, 0.022, (x + 0.2, tile_front + 0.02, z + 0.17), "r", rot=FACE)
    for v, u1 in ((0.12, 0.42), (-0.04, 0.34), (-0.2, 0.26)):
        bar(dev, 0.06, u1, v, 0.042)
    x, y, z = dev.at(0.17, -0.36)
    box((0.42, 0.12, 0.16), (x, y - 0.05, z), "p", 0.07)
    arrow = round_corners([(px * 0.75, py * 0.75, 0.025) for px, py in [(0, 0), (0, -0.62), (0.15, -0.48), (0.26, -0.7), (0.37, -0.65), (0.26, -0.43), (0.46, -0.42)]], 12)
    x, y, z = dev.at(0.25, -0.25)  # the tip on the red button, clear of the text lines and inside the frame
    plate(arrow, 0.08, (x, y - 0.2, z), "c", rot=FACE, edge=0.015, clean=True)


def gear_profile(R, r, n=8, steps=6):
    """Gear outline (n trapezoid teeth between radius r and R), CCW, centred."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        w = math.pi / n
        for t, rad in ((-0.62 * w, r), (-0.36 * w, R), (0.36 * w, R), (0.62 * w, r)):
            pts.append((rad * math.cos(a + t), rad * math.sin(a + t), 0.022))
        pts.append((r * math.cos(a + w), r * math.sin(a + w), 0.0))
    return round_corners(pts, 8)


def icon_config():
    """via.yaml: coral sheet with a folded corner, sunk dark page with config lines,
    a cream sheet behind it."""
    import bmesh
    W, Hh, D, cf = 1.8, 2.3, 0.36, 0.55
    z = Hh / 2 + 0.02
    def dogear(w, h, c):
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2 - c), (w / 2 - c, h / 2), (-w / 2, h / 2)]
    box((1.55, 0.2, 2.0), (-0.3, 0.45, z + 0.12), "s", 0.12)  # sheet behind
    body = plate(dogear(W, Hh, cf), D, (0, D / 2, z), "p", rot=FACE, edge=0.1)
    face = -D / 2
    inner = dogear(W - 0.36, Hh - 0.36, cf - 0.22)
    cut(body, plate(inner, 0.6, (0, face + 0.06, z), "r", rot=FACE))
    plate(inner, 0.02, (0, face + 0.062, z), "r", rot=FACE)
    corner_cut = [(W / 2 - cf + 0.06, Hh / 2 + 0.05), (W / 2 - cf + 0.06, Hh / 2 - cf + 0.06), (W / 2 + 0.05, Hh / 2 - cf + 0.06), (W / 2 + 0.05, Hh / 2 + 0.05)]
    cut(body, plate(corner_cut, D * 0.5, (0, face + 0.08, z), "p", rot=FACE))
    smooth(body)
    fold = round_corners([(W / 2 - cf, Hh / 2, 0), (W / 2 - cf, Hh / 2 - cf, 0.08), (W / 2, Hh / 2 - cf, 0)], 12)
    plate(fold, 0.10, (0, face + 0.09, z), "c", rot=FACE, edge=0.03, clean=True)
    for zz, x0, L in ((0.42, -0.5, 0.55), (0.18, -0.32, 0.75), (-0.06, -0.32, 0.55), (-0.3, -0.5, 0.42), (-0.54, -0.32, 0.42)):
        box((L, 0.12, 0.12), (x0 + L / 2, face + 0.0, z + zz), "g", 0.055)
    # blind review: the lines alone read as a log or a Gantt chart; a gear badge says "settings"
    gc = (0.62, face + 0.04, z - 0.74)
    gprof = gear_profile(0.44, 0.33, 8)
    gn = len(gprof)
    gin = [(0.20 * gx / math.hypot(gx, gy), 0.20 * gy / math.hypot(gx, gy)) for gx, gy in gprof]
    gverts = (
        [(gx, gy, 0.0) for gx, gy in gprof]
        + [(gx, gy, 0.16) for gx, gy in gprof]
        + [(gx, gy, 0.0) for gx, gy in gin]
        + [(gx, gy, 0.16) for gx, gy in gin]
    )
    gfaces = (
        [[i, (i + 1) % gn, gn + (i + 1) % gn, gn + i] for i in range(gn)]
        + [[2 * gn + i, 2 * gn + (i + 1) % gn, (i + 1) % gn, i] for i in range(gn)]
        + [[gn + i, gn + (i + 1) % gn, 3 * gn + (i + 1) % gn, 3 * gn + i] for i in range(gn)]
        + [list(range(2 * gn, 3 * gn))[::-1], list(range(3 * gn, 4 * gn))]
    )
    gme = bpy.data.meshes.new("gear")
    gme.from_pydata(gverts, [], gfaces)
    gme.update()
    go = bpy.data.objects.new("gear", gme)
    bpy.context.collection.objects.link(go)
    go.location = gc
    go.rotation_euler = FACE
    finish(go, "c", 0.02, 4)
    bpy.ops.object.select_all(action="DESELECT")
    go.select_set(True)
    bpy.context.view_layer.objects.active = go
    bpy.ops.object.modifier_apply(modifier="bevel")
    for gf in go.data.polygons:
        gf.use_smooth = abs(gf.normal.z) < 0.999
    cyl(0.14, 0.08, (gc[0], gc[1] - 0.14, gc[2]), "p", 0.02, rot=FACE)  # red hub: reads as a gear, not a hole


def icon_check():
    """Chunky asymmetric checkmark standing on a cream disc."""
    cyl(0.95, 0.36, (0, 0, 0.18), "s", 0.10)
    prof = stroke_outline([(-0.6, 0.08), (-0.2, -0.34), (0.86, 0.9)], 0.46, n=28)  # short leg, long leg: a tick, not a V
    plate(prof, 0.5, (0.0, 0.25, 0.92), "p", rot=FACE, edge=0.065, clean=True)


def icon_meet():
    """Video meeting: landscape coral screen, two people split by a line, webcam on top."""
    W, H = 2.7, 1.85
    dev = Device(W, H, 0.6, "p", screen=(0.18, 0.18, 0.18, 0.18))
    for u in (-0.25, 0.25):
        bust(dev, u, -0.05, 1.45)
    x, y, z = dev.at(0, 0)
    box((0.06, 0.06, dev.sh * 0.86), (x, y - 0.03, z), "g", 0.025)
    # webcam on the top edge
    box((0.78, 0.44, 0.4), (0.0, -0.02, H + 0.17), "s", 0.17)  # centred, like the flat twin
    cyl(0.13, 0.06, (0.0, -0.24, H + 0.17), "r", 0.02, rot=FACE)
    torus(0.15, 0.035, (0.0, -0.25, H + 0.17), "k", rot=FACE)


def icon_chat():
    """Private chat: coral bubble with text lines, cream bubble behind, padlock front-right."""
    bx, bz = 0.5, 1.75
    plate(rr_profile(1.35, 0.95, 0.24), 0.32, (bx, 0.45 + 0.16, bz), "s", rot=FACE, edge=0.075, clean=True)
    dev = Device(2.0, 1.45, 0.42, "p", screen=(0.2, 0.2, 0.2, 0.2), x=-0.2, z0=0.45)
    bpy.data.objects.remove(dev.body, do_unlink=True)
    dev.body = plate(bubble_profile(2.0, 1.45, 0.26, -0.72, -0.3, -0.76, -1.1), 0.42, (-0.2, 0.21, 0.45 + 1.45 / 2), "p", rot=FACE, edge=0.08, clean=True)
    prof = rr_profile(dev.sw, dev.sh, min(dev.sw, dev.sh) * 0.1)
    cut(dev.body, plate(rr_profile(dev.sw + 0.01, dev.sh + 0.01, min(dev.sw, dev.sh) * 0.1), 0.6, (dev.cx, dev.floor, dev.cz), "r", rot=FACE))
    smooth(dev.body)
    sleeve = plate(rr_profile(dev.sw + 0.08, dev.sh + 0.08, min(dev.sw, dev.sh) * 0.12), 0.055, (dev.cx, dev.floor, dev.cz), "r", rot=FACE)
    cut(sleeve, plate(prof, 0.3, (dev.cx, dev.floor + 0.05, dev.cz), "r", rot=FACE))
    bar(dev, -0.3, 0.28, 0.16, 0.06)
    bar(dev, -0.3, 0.06, -0.12, 0.06)
    padlock(0.72, dev.face - 0.2, 0.55, 1.05, "s", "r")  # cream on the red bubble: contrast (a red lock merged into it)


def handset_profile(scale=1.0, tilt_deg=32):
    """Smooth 2D closed profile of a telephone handset (thick ear/mouth cups + curved handle), CCW."""
    inner = [(0.08 + 0.25 * math.cos(D2R(a)), 0.25 * math.sin(D2R(a))) for a in range(140, 221, 10)]
    outer = [(0.08 + 0.46 * math.cos(D2R(a)), 0.46 * math.sin(D2R(a))) for a in range(232, 127, -8)]
    raw = [
        (0.0, 0.44),
        (0.2, 0.33),
        (0.09, 0.14),
        *inner,
        (0.09, -0.14),
        (0.2, -0.33),
        (0.0, -0.44),
        *outer,
    ][::-1]
    # round the corners of the ear and mouth cups
    P = [Vector(p) * scale for p in raw]
    n = len(P)
    pts = []
    for i in range(n):
        a, b, c = P[(i - 1) % n], P[i], P[(i + 1) % n]
        d1, d2 = (b - a), (c - b)
        if d1.normalized().dot(d2.normalized()) > 0.85:
            pts.append(b)
            continue
        r = min(0.06 * scale, d1.length * 0.38, d2.length * 0.38)
        p1, p2 = b - d1.normalized() * r, b + d1.normalized() * 0 + d2.normalized() * r
        for k in range(7):
            t = k / 6
            pts.append(p1 * (1 - t) ** 2 + b * 2 * t * (1 - t) + p2 * t * t)
    ca, sa = math.cos(D2R(tilt_deg)), math.sin(D2R(tilt_deg))
    return [(p.x * ca - p.y * sa, p.x * sa + p.y * ca) for p in pts]


def icon_call():
    """Voice call: smartphone slab with rounded corners, top earpiece/notch, embossed handset
    and two sound-wave arcs inside the dark screen."""
    ph = Device(1.55, 2.6, 0.36, "p", screen=(0.15, 0.15, 0.25, 0.16), bevel=0.28)
    box((0.42, 0.12, 0.08), (0, ph.face + 0.03, 2.47), "p", 0.04)  # earpiece
    x, _, z = ph.at(-0.08, -0.04)  # bigger handset: it carries the icon (the flat twin fills the screen)
    plate(handset_profile(1.12, 32), 0.12, (x, ph.floor, z), "g", rot=FACE, edge=0.025, clean=True)
    # blind review (twice): two bars read as "pause" or signal strength; two sound-wave arcs
    # off the handset's open side are the universal "call in progress" sign (flat twin too)
    cu, cv = -0.08 + 0.1 / ph.sw, -0.04 + 0.1 / ph.sh
    for r in (0.38, 0.55):  # the outer arc stays inside the screen
        arc_uv = [(cu + r * math.cos(D2R(a)) / ph.sw, cv + r * math.sin(D2R(a)) / ph.sh) for a in range(20, 81, 4)]
        emboss(ph, arc_uv, 0.1, "g", depth=0.1)


def icon_files():
    """Shared files: coral folder with ONE clear depth (back flap + front panel of equal
    thickness, paper sticking out between them, share glyph embossed on the front panel)."""
    W, T = 2.5, 0.24
    # back flap + top-left folder tab as ONE profile, flush on the left edge
    flap = round_corners([
        (-W / 2, 0.0, 0.14),
        (W / 2, 0.0, 0.14),
        (W / 2, 1.85, 0.14),
        (-W / 2 + 1.0, 1.85, 0.1),
        (-W / 2 + 0.88, 2.15, 0.12),
        (-W / 2, 2.15, 0.12),
    ], 16)
    plate(flap, T, (0, 0.14 + T / 2, 0), "p", rot=FACE, edge=0.08, clean=True)
    # cream paper sheet sitting between back flap and front panel, sticking out above front
    box((1.75, 0.1, 1.4), (0.1, 0.0, 1.25), "c", 0.05)
    for zz in (1.72, 1.51):
        box((1.05, 0.06, 0.085), (0.1, -0.04, zz), "r", 0.04)
    # front panel of equal thickness + inner bottom bridge
    box((W, T, 1.3), (0, -0.14, 0.65), "p", 0.11)
    box((W, 0.28, 0.22), (0, 0.0, 0.11), "p", 0.11)
    # share glyph: 3 bevelled cylinders and 2 connecting box struts
    yf = -0.14 - T / 2
    ax, bx, by = -0.34, 0.3, 0.27
    th = math.atan2(by, bx - ax)
    L = math.hypot(bx - ax, by)
    for sgn in (-1, 1):
        box((L, 0.075, 0.10), ((ax + bx) / 2, yf - 0.02, 0.65 + sgn * by / 2), "c", 0.02, rot=(0, -sgn * th, 0))
    for px, pz in ((ax, 0.65), (bx, 0.65 + by), (bx, 0.65 - by)):
        cyl(0.15, 0.08, (px, yf - 0.02, pz), "c", 0.025, rot=FACE)


def icon_page():
    """Personal web page: red page frame with only a thin top bar, header strip, round avatar,
    and two side-by-side content blocks."""
    W, H, D = 2.28, 2.16, 0.38
    page = Device(W, H, D, "p", screen=(0.17, 0.17, 0.30, 0.17), bevel=0.22)
    # thin top bar accent (minimal web chrome, no dots or URL box)
    box((0.96, 0.06, 0.065), (-W / 2 + 0.68, page.face - 0.005, H - 0.155), "c", 0.03)
    # 1. header strip across the top of the page
    hx, _, hz = page.at(0, 0.36)
    plate(rr_profile(1.68, 0.24, 0.09), 0.08, (hx, page.floor + 0.01, hz), "g", rot=FACE, edge=0.025, clean=True)
    # 2. round avatar in the middle (cream circle with a small dark person silhouette inside)
    ax, _, az = page.at(0, 0.02)
    cyl(0.32, 0.08, (ax, page.floor - 0.03, az), "g", 0.028, rot=FACE)
    af = page.floor - 0.07
    cyl(0.085, 0.04, (ax, af, az + 0.085), "r", 0.015, rot=FACE)
    sh = round_corners(
        [(0.19, 0.0, 0.035)]
        + [(0.19 * math.cos(t), 0.12 * math.sin(t), 0.0) for t in [math.pi * k / 36 for k in range(8, 29)]]
        + [(-0.19, 0.0, 0.035)],
        8,
    )
    plate(sh, 0.04, (ax, af + 0.02, az - 0.155), "r", rot=FACE, edge=0.01, clean=True)
    # 3. two side-by-side content blocks below
    for u in (-0.23, 0.23):
        bx, _, bz = page.at(u, -0.32)
        plate(rr_profile(0.76, 0.36, 0.10), 0.08, (bx, page.floor + 0.01, bz), "g", rot=FACE, edge=0.025, clean=True)


def cross_profile(arm, w, n=12):
    """Single closed 2D outline of a 45° '×' (two crossed pill strokes), CCW, no internal seam."""
    h = w / 2
    d_in = h / math.sin(D2R(45))
    pts = []
    for k in range(4):
        # inner corner between arm k-1 and arm k (at angle 90*k)
        ca = D2R(90 * k)
        pts.append((d_in * math.cos(ca), d_in * math.sin(ca), h * 0.3))
        # outer semicircular cap of arm k (at angle 45 + 90*k), wound CCW from a - pi/2 to a + pi/2
        a = D2R(45 + 90 * k)
        cx, cy = arm * math.cos(a), arm * math.sin(a)
        for j in range(n + 1):
            th = a - math.pi / 2 + math.pi * j / n
            pts.append((cx + h * math.cos(th), cy + h * math.sin(th), 0.0))
    return round_corners(pts, 8)


def icon_warning():
    """Warning: a thick flat-faced triangle slab (p) with a cream '!' on its front face — the same
    slab treatment as error's octagon (validation: the bevelled triangle on a disc read as a cone
    or a shark fin)."""
    tri = round_corners([(-1.3, 0.0, 0.26), (1.3, 0.0, 0.26), (0.0, 2.25, 0.26)], 24)
    D = 0.56
    plate(tri, D, (0, D / 2, 0.0), "p", rot=FACE, edge=0.07, clean=True)
    face = -D / 2
    stem = stroke_outline([(0.0, 0.92), (0.0, 1.5)], 0.27)
    plate(stem, 0.10, (0, face + 0.02, 0.0), "c", rot=FACE, edge=0.035, clean=True)
    cyl(0.145, 0.10, (0, face - 0.03, 0.5), "c", 0.035, rot=FACE)


def icon_error():
    """Error: chunky rounded octagon/disc (p) with a cream '×' (single smooth cross outline)."""
    R, D = 1.22, 0.56
    oct_pts = [(R * math.cos(D2R(22.5 + 45 * k)), R * math.sin(D2R(22.5 + 45 * k)), 0.28) for k in range(8)]
    plate(round_corners(oct_pts, 16), D, (0, D / 2, 1.22), "p", rot=FACE, edge=0.12, clean=True)
    face = -D / 2
    plate(cross_profile(0.48, 0.28), 0.11, (0, face + 0.02, 1.22), "c", rot=FACE, edge=0.035, clean=True)


def icon_info():
    """Info: chunky rounded disc (s) with a sunk dark recess (r), accent rim (k), and cream 'i' (c)."""
    R, D, cz = 1.18, 0.56, 1.20
    body = cyl(R, D, (0, 0, cz), "s", 0.14, rot=FACE)
    face = -D / 2
    r_in = 0.82
    rec = [(r_in * math.cos(2 * math.pi * k / 64), r_in * math.sin(2 * math.pi * k / 64)) for k in range(64)]
    cut(body, plate(rec, 0.5, (0, face + 0.08, cz), "r", rot=FACE))
    plate(rec, 0.02, (0, face + 0.082, cz), "r", rot=FACE)
    smooth(body)
    r_out = 0.95
    outer = [(r_out * math.cos(2 * math.pi * k / 64), r_out * math.sin(2 * math.pi * k / 64)) for k in range(64)]
    rim(outer, rec, 0.04, (0, face + 0.01, cz), "k", rot=FACE)
    floor = face + 0.08
    stem = stroke_outline([(0.0, -0.44), (0.0, 0.08)], 0.25)
    plate(stem, 0.11, (0, floor + 0.01, cz), "c", rot=FACE, edge=0.035, clean=True)
    cyl(0.14, 0.10, (0, floor - 0.04, cz + 0.42), "c", 0.035, rot=FACE)


def icon_pending():
    """Pending (clock): chunky disc (p) with a sunk dark face (r), two cream hands and 4 ticks."""
    R, D, cz = 1.20, 0.56, 1.20
    body = cyl(R, D, (0, 0, cz), "p", 0.14, rot=FACE)
    face = -D / 2
    r_in = 0.88
    rec = [(r_in * math.cos(2 * math.pi * k / 64), r_in * math.sin(2 * math.pi * k / 64)) for k in range(64)]
    cut(body, plate(rec, 0.5, (0, face + 0.08, cz), "r", rot=FACE))
    plate(rec, 0.02, (0, face + 0.082, cz), "r", rot=FACE)
    smooth(body)
    floor = face + 0.08
    hands = stroke_outline([(0.0, 0.36), (0.0, 0.0), (0.34, -0.20)], 0.19)
    plate(hands, 0.11, (0, floor + 0.01, cz), "c", rot=FACE, edge=0.03, clean=True)
    for dx, dz in ((0, 0.73), (0.73, 0), (0, -0.73), (-0.73, 0)):
        cyl(0.075, 0.09, (dx, floor - 0.03, cz + dz), "c", 0.025, rot=FACE)


def icon_server():
    """Server/NAS: 3 stacked rounded rack units (p body, s front panels) with cream LEDs, dark vent
    slot, and left/right cream pipe ports like icon_caddy."""
    W, D, H = 2.16, 1.42, 0.66
    face = -D / 2
    box((W - 0.28, D - 0.28, 1.60), (0, 0, 1.10), "r", 0.06)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, 1.10), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, 1.10), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    for i in range(3):
        cz = 0.36 + i * 0.74
        box((W, D, H), (0, 0, cz), "p", 0.14)
        # s front panel on the -Y face
        plate(rr_profile(1.84, 0.44, 0.12), 0.08, (0, face + 0.02, cz), "s", rot=FACE, edge=0.025, clean=True)
        pf = face - 0.06
        # dark recessed status pill on the left holding two cream status LEDs
        plate(rr_profile(0.56, 0.24, 0.11), 0.03, (-0.51, pf + 0.015, cz), "r", rot=FACE, edge=0.01)
        for lx in (-0.64, -0.38):
            cyl(0.078, 0.05, (lx, pf - 0.01, cz), "c", 0.02, rot=FACE)
        # dark vent slot on the right with a k accent rim
        vent_in = rr_profile(0.72, 0.16, 0.07)
        vent_out = rr_profile(0.84, 0.26, 0.11)
        plate(vent_in, 0.03, (0.34, pf + 0.015, cz), "r", rot=FACE)
        rim(vent_out, vent_in, 0.035, (0.34, pf + 0.01, cz), "k", rot=FACE)


def icon_database():
    """Database: 3 stacked rounded discs (cylinder stack) in p with s rings between, cream highlight dots."""
    R = 1.12
    for i in range(3):
        cz = 0.36 + i * 0.74
        cyl(R, 0.56, (0, 0, cz), "p", 0.13)
        if i < 2:
            cyl(0.98, 0.22, (0, 0, cz + 0.37), "s", 0.04)
        # cream highlight dots on the front (-Y) face of each cylinder
        for a in (-22, -6):
            rad = D2R(a - 90)
            px, py = (R - 0.02) * math.cos(rad), (R - 0.02) * math.sin(rad)
            cyl(0.095, 0.09, (px, py, cz), "c", 0.03, rot=(D2R(90), 0, D2R(a)))


def toy_bust(x, y, z, scale=1.0, role="p"):
    """Chunky 3D toy-figure head + rounded shoulders standing at (x, y, z), facing -Y."""
    D = 0.38 * scale
    rc = 0.09 * scale
    w, h = 0.44 * scale, 0.42 * scale
    sh = round_corners(
        [(w, 0.0, rc)]
        + [(w * math.cos(t), h * math.sin(t), 0.0) for t in [math.pi * k / 48 for k in range(10, 39)]]
        + [(-w, 0.0, rc)],
        12,
    )
    plate(sh, D, (x, y + D / 2, z), role, rot=FACE, edge=0.07 * scale, clean=True)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25 * scale, location=(x, y, z + 0.67 * scale), segments=48, ring_count=24)
    finish(bpy.context.object, role)


def icon_team():
    """Team: three toy figures on a slim plinth, the middle one larger and centred behind
    (validation: the big plinth dominated and the figures got lost at small sizes)."""
    plate(rr_profile(2.7, 0.95, 0.42), 0.16, (0, 0, 0.0), "s", edge=0.06, clean=True)
    toy_bust(0.0, 0.1, 0.16, 1.3, "p")
    toy_bust(-0.92, 0.0, 0.16, 1.0, "p")
    toy_bust(0.92, 0.0, 0.16, 1.0, "p")

# ---------------------------------------------------------------- platform marks (W-140)
BRANDS = __import__("os").path.join(__import__("os").path.dirname(__file__), "..", "brands")


def brand_mark(name, width, center, depth, role, rot=FACE, bevel=0.0):
    """A platform mark (scripts/icons/brands/<name>.svg) as a clean solid, `width` wide, centred
    on `center` (its depth centred there too). The mark's shape is used unaltered: imported,
    extruded, meshed (duplicate SVG points removed so it renders without slits), one colour."""
    import bmesh
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=__import__("os").path.join(BRANDS, f"{name}.svg"))
    parts = [o for o in bpy.data.objects if o not in before]
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    k = width / o.dimensions.x
    o.data.extrude = max(0.0, depth / 2 - bevel) / k
    o.data.bevel_depth = bevel / k  # a rounded rim (sculpted marks); 0 = crisp
    o.data.bevel_resolution = 4
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    o.scale = (k, k, k)
    o.rotation_euler = rot
    o.location = center
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.view_layer.objects.active
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    o.data.materials.clear()
    o.data.materials.append(material(role))
    for f in o.data.polygons:
        f.use_smooth = False
    return o


def ellipsoid(center, radii, role, rot=(0, 0, 0), segs=64):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=center, rotation=rot, segments=segs, ring_count=segs // 2)
    o = bpy.context.object
    o.scale = radii
    bpy.ops.object.transform_apply(scale=True)
    return finish(o, role)


def capsule(a, b, r, role):
    """A rounded rod from a to b (round caps)."""
    o = tube([a, b], r, role)
    for p in (a, b):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=p, segments=32, ring_count=16)
        finish(bpy.context.object, role)
    return o


def lathe(profile, role, segs=72, loc=(0, 0, 0)):
    """Revolve a (radius, z) profile about Z (first and last points on the axis)."""
    verts, faces = [], []
    n = len(profile)
    for k in range(segs):
        a = 2 * math.pi * k / segs
        verts += [(r * math.cos(a), r * math.sin(a), z) for r, z in profile]
    for k in range(segs):
        k2 = (k + 1) % segs
        for i in range(n - 1):
            faces.append([k * n + i, k2 * n + i, k2 * n + i + 1, k * n + i + 1])
    me = bpy.data.meshes.new("lathe")
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new("lathe", me)
    bpy.context.collection.objects.link(o)
    o.location = loc
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.remove_doubles(threshold=1e-4)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return finish(o, role)


def apple_model(x=0.0, y=0.0, z=0.0, s=1.0):
    """A 3D apple (owner, W-140): a taller lathe body with a dip at the top (not a tomato), a
    real concave bite (sphere cutter) with cream flesh inside, a slate stem and a curved,
    pointed slate leaf."""
    H = 1.16  # taller than wide
    prof = [(0, 0.12), (0.18, 0.03), (0.4, 0.0), (0.62, 0.1), (0.8, 0.34), (0.9, 0.66), (0.9, 1.0),
            (0.84, 1.26), (0.68, 1.44), (0.48, 1.5), (0.3, 1.42), (0.14, 1.28), (0, 1.2)]
    def catmull(pts, n=8):  # smooth the profile so the silhouette has no corners
        out = []
        P = [pts[0]] + pts + [pts[-1]]
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            for k in range(n):
                t = k / n
                out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
        return out + [pts[-1]]
    prof = catmull(prof)
    prof[0] = (0, prof[0][1])
    body = lathe([(max(0.0, r) * s, zz * H * s) for r, zz in prof], "p", segs=160, loc=(x, y, z))
    # the bite: a sphere scooped out of the front-right, between camera-right (0.82, 0.57) and
    # toward-camera (0.57, -0.82), so its hollow faces the viewer and the key light
    # owner: one clean, deep, round bite like the mark (~30% of the width), on the right edge of
    # the silhouette as the camera sees it (camera-right is azimuth 35°), turned a little toward
    # the viewer so the cream flesh inside reads. Flesh in self-lit glyph cream.
    d = Vector((math.cos(D2R(30)), math.sin(D2R(30)), 0))
    body.data.materials.append(material("g:flesh"))  # the cut faces take the cutter's cream: the flesh
    # a round notch, not a sliced side: radius ~0.23 of the width, ~0.52 deep, centre inside the rim
    bc = Vector((x, y, z + 0.92 * H * s)) + d * (0.8 * s)
    bite = ellipsoid(tuple(bc), (0.42 * s, 0.42 * s, 0.42 * s), "g:flesh", segs=96)
    cut(body, bite)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    for mod in list(body.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)  # the scoop's faces came out inverted (flat grey)
    bpy.ops.object.mode_set(mode="OBJECT")
    smooth(body, 70)
    top = z + 1.2 * H * s
    tube([(x, y, top - 0.04 * s), (x + 0.02 * s, y, top + 0.24 * s), (x + 0.1 * s, y, top + 0.42 * s)], 0.055 * s, "r")
    # leaf: pointed at both ends, bent along its length and across its width
    L, W, T, n = 0.66 * s, 0.2 * s, 0.035 * s, 24
    verts, faces = [], []
    for i in range(n + 1):
        u = i / n
        hw = W * math.sin(math.pi * u) ** 0.8
        for v in (-1, 0, 1):
            for side in (0, 1):
                px = u * L
                pz = v * hw + 0.3 * L * u * u  # blade in the vertical plane, sweeping up
                py = side * T - 0.35 * v * v * hw  # cupped across its width
                verts.append((px, py, pz))
    def vid(i, v, sd):
        return (i * 3 + (v + 1)) * 2 + sd
    for i in range(n):
        for v in (-1, 0):
            for sd in (0, 1):
                q = [vid(i, v, sd), vid(i + 1, v, sd), vid(i + 1, v + 1, sd), vid(i, v + 1, sd)]
                faces.append(q if sd else q[::-1])
        for v in (-1, 1):  # edges
            a, b = (vid(i, v, 0), vid(i + 1, v, 0)), (vid(i, v, 1), vid(i + 1, v, 1))
            faces.append([a[0], a[1], b[1], b[0]] if v < 0 else [a[1], a[0], b[0], b[1]])
    me = bpy.data.meshes.new("leaf")
    me.from_pydata(verts, [], faces)
    me.update()
    leaf = bpy.data.objects.new("leaf", me)
    bpy.context.collection.objects.link(leaf)
    leaf.location = (x + 0.08 * s, y, top + 0.32 * s)
    leaf.rotation_euler = (0, D2R(-18), D2R(35))  # blade faces the camera (azimuth 35), tip up-right
    finish(leaf, "r")
    bpy.context.view_layer.objects.active = leaf
    bpy.ops.object.select_all(action="DESELECT")
    leaf.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    for f in me.polygons:
        f.use_smooth = True
    return body


def apple_mark_solid():
    """The Apple mark as a thick, soft-bevelled red sculpture (owner: the realistic fruit read
    wrong; ASD Manager's mark-as-statue was the look): brands/apple.svg extruded deep, the leaf a
    separate piece, bevelled edges so the key light draws the rim."""
    o = brand_mark("apple", 1.8, (0, 0, 1.05), 0.5, "p", bevel=0.07)
    smooth(o, 50)
    return o


def icon_apple():
    """The apple alone: the Apple mark as a sculpture (same as macOS)."""
    apple_mark_solid()


def _os_monitor(mark_name, mark_width, dv=0.0):
    """Desktop monitor on a stand (icon_desktop body) with ONLY an OS mark in cream on its navy screen."""
    box((1.35, 0.9, 0.2), (0, 0.08, 0.1), "s", 0.09)
    box((0.46, 0.36, 0.48), (0, 0.08, 0.34), "s", 0.09)
    dev = Device(2.65, 1.85, 0.38, "p", screen=(0.18, 0.18, 0.18, 0.18), z0=0.52, bevel=0.2)
    x, _, z = dev.at(0, dv)
    brand_mark(mark_name, mark_width, (x, dev.floor - 0.035, z), 0.04, "g")


def icon_os_macos():
    """macOS: desktop monitor on a stand with the Apple mark in cream on its navy screen."""
    _os_monitor("apple", 0.84, dv=0.02)


def icon_os_ios():
    """iOS: the phone is the object — our plain phone body with the Apple mark in cream on
    its navy screen, embossed the way the logo sits on the Viaalink phone."""
    ph = Device(1.55, 2.6, 0.36, "p", screen=(0.15, 0.15, 0.25, 0.16), bevel=0.28)
    box((0.42, 0.12, 0.08), (0, ph.face + 0.03, 2.47), "p", 0.04)  # earpiece
    x, _, z = ph.at(0, 0.04)
    brand_mark("apple", ph.sw * 0.56, (x, ph.floor - 0.035, z), 0.04, "g")


def icon_os_linux():
    """Linux: desktop monitor on a stand with the Tux mark in cream on its navy screen."""
    _os_monitor("linux", 0.88)


def icon_os_android():
    """Android: canonical phone body with the Android mark in cream on its navy screen, like os-ios."""
    stand = bool(globals().get("VIA_IMPORT_ONLY"))
    z0 = 0.18 if stand else 0.0
    if stand:
        box((1.2, 0.95, 0.24), (0, 0.2, 0.12), "s", 0.1)
    ph = Device(1.55, 2.6, 0.36, "p", screen=(0.15, 0.15, 0.25, 0.16), z0=z0, bevel=0.28)
    box((0.42, 0.12, 0.08), (0, ph.face + 0.03, z0 + 2.47), "p", 0.04)  # earpiece
    x, _, z = ph.at(0, 0.02)
    brand_mark("android", ph.sw * 0.70, (x, ph.floor - 0.035, z), 0.04, "g")


def icon_os_windows():
    """Windows: desktop monitor on a stand with the Windows mark in cream on its navy screen."""
    _os_monitor("windows", 0.92)


def icon_github():
    """GitHub: an octocat-style figure — head with cat ears, a cream face plate with navy eyes,
    curling tentacles with glyph tips, in red."""
    ellipsoid((0, 0, 1.95), (0.88, 0.72, 0.72), "p")  # head
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cone_add(radius1=0.34, radius2=0.08, depth=0.42, location=(sx * 0.5, 0.05, 2.5), rotation=(0, D2R(sx * 14), 0), vertices=48)
        finish(bpy.context.object, "p", 0.03)
    # cream face plate with navy eyes (validation: the navy band read as a ninja mask)
    ellipsoid((0, -0.46, 1.86), (0.62, 0.3, 0.46), "c:dim")
    for sx in (-1, 1):
        ellipsoid((sx * 0.24, -0.74, 1.9), (0.1, 0.05, 0.15), "r")
    ellipsoid((0, 0, 1.3), (0.42, 0.38, 0.32), "p")  # neck
    for k, a in enumerate((-70, -35, 0, 35, 70)):
        ar = D2R(a)
        d = Vector((math.sin(ar), -math.cos(ar) * 0.6, 0))
        pts = []
        for t in [i / 14 for i in range(15)]:
            r = 0.25 + 0.85 * t
            pts.append(tuple(Vector((0, 0, 1.2 - 1.15 * t + 0.6 * t ** 3)) + d * r))  # down, then curling up
        tube(pts, 0.12, "p")
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=pts[-1], segments=24, ring_count=12)
        finish(bpy.context.object, "g")


def icon_docker():
    """Docker, our way (owner): Docker's whale, sleek and rounded, with a flat deck carrying
    rounded shipping containers that spell VIA over LINK, one letter each, rows exactly aligned."""
    # hull: a bulbous blunt head tapering to the tail (a smoothed lathe along x). The deck is flattened
    # with a smooth clamp on the vertices (no boolean: the cut left hard, angular rims), then subdivided
    prof = [(0.0, 0.0), (0.36, 0.03), (0.6, 0.14), (0.76, 0.38), (0.84, 0.78), (0.83, 1.3), (0.75, 1.9),
            (0.6, 2.5), (0.42, 3.0), (0.27, 3.32), (0.12, 3.47), (0.0, 3.5)]
    def catmull(pts, n=6):
        P = [pts[0]] + pts + [pts[-1]]
        out = []
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            for k in range(n):
                t = k / n
                out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
        return [(max(0.0, r), z) for r, z in out] + [pts[-1]]
    prof = catmull(prof)
    prof[0] = (0.0, prof[0][1])
    hull = lathe(prof, "p", segs=128)
    hull.rotation_euler = (0, D2R(90), 0)
    hull.location = (-1.85, 0, 0.84)
    hull.scale = (1.0, 0.82, 1.0)
    bpy.context.view_layer.objects.active = hull
    bpy.ops.object.select_all(action="DESELECT")
    hull.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    DECK, SOFT = 1.3, 0.07
    for v in hull.data.vertices:  # smooth min(z, DECK): a flat deck that rolls into the sides
        z = v.co.z
        v.co.z = DECK - SOFT * math.log1p(math.exp((DECK - z) / SOFT)) if z > DECK - 6 * SOFT else z
    sub = hull.modifiers.new("smooth", "SUBSURF")
    sub.levels, sub.render_levels = 1, 2
    smooth(hull, 180)
    # tail: one tapered curl rising from the back, ending in a single wide fluke
    cu = bpy.data.curves.new("tail", "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("NURBS")
    pts = [(1.3, 0, 0.9, 0.2), (1.72, 0, 1.02, 0.17), (1.98, 0, 1.3, 0.14), (2.02, 0, 1.62, 0.12), (1.9, 0, 1.86, 0.1)]
    sp.points.add(len(pts) - 1)
    for p, (x, y, z, r) in zip(sp.points, pts):
        p.co = (x, y, z, 1)
        p.radius = r / 0.2
    sp.order_u = 3
    sp.use_endpoint_u = True
    cu.bevel_depth = 0.2
    cu.bevel_resolution = 14
    cu.use_fill_caps = True
    tail = bpy.data.objects.new("tail", cu)
    bpy.context.collection.objects.link(tail)
    tail.data.materials.append(material("p"))
    # fluke: two slim lobes in a shallow V that meet at the tail tip
    for side in (-1, 1):
        ellipsoid((1.9 + side * 0.27, 0, 1.98 + 0.07), (0.34, 0.15, 0.085), "p", rot=(0, D2R(-side * 22), 0))
    ellipsoid((-1.3, -0.6, 1.0), (0.09, 0.05, 0.1), "g")  # eye, near the blunt nose
    # containers: shipping proportions, generous rounding, tight even gaps, top row centred over
    # the joints of the bottom row
    W, H, D, gap = 0.6, 0.5, 0.52, 0.035
    sans = bpy.data.fonts.load(SANS_FONT, check_existing=True)
    def container(cx, cz, ch):
        box((W, D, H), (cx, 0, cz), "s", 0.09)
        for dx in (-0.2, 0.2):  # two soft corrugation ribs, either side of the letter
            box((0.03, 0.02, H * 0.62), (cx + dx, -D / 2 - 0.004, cz), "c:dim", 0.01)
        t = text(ch, 0.36, (cx, -D / 2 - 0.006, cz), (D2R(90), 0, 0), "p", 0.025)
        t.data.font = sans
        t.data.align_x = "CENTER"
        t.data.align_y = "CENTER"
    z1 = DECK + H / 2 + 0.005
    X0 = -0.3  # owner: the stack sat too far right; over the middle of the back, toward the head
    for i, ch in enumerate("LINK"):
        container(X0 + (i - 1.5) * (W + gap), z1, ch)
    for i, ch in enumerate("VIA"):
        container(X0 + (i - 1) * (W + gap), z1 + H + gap, ch)



def icon_nas():
    """NAS (owner: our Relay runs on one): a compact desktop NAS, red rounded body, four cream
    drive trays on the front, each with a dark grip slot and a glowing status LED, a power LED on
    top, and left/right cream pipe ports like icon_caddy."""
    W, D, H = 1.9, 1.7, 2.0
    face = -D / 2
    box((W, D, H), (0, 0, H / 2), "p", 0.18)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, 0.91), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, 0.91), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    plate(rr_profile(1.6, 1.62, 0.12), 0.05, (0, face + 0.02, H / 2 + 0.06), "r", rot=FACE, edge=0.015)
    bw = 0.34
    for i in range(4):
        x = (i - 1.5) * (bw + 0.05)
        plate(rr_profile(bw, 1.44, 0.07), 0.07, (x, face - 0.02, H / 2 + 0.06), "s", rot=FACE, edge=0.02, clean=True)
        plate(rr_profile(0.08, 0.7, 0.04), 0.02, (x, face - 0.075, H / 2 + 0.14), "r", rot=FACE, edge=0.006)
        cyl(0.05, 0.04, (x, face - 0.08, H / 2 - 0.5), "g", 0.015, rot=FACE)
    cyl(0.09, 0.04, (0.62, 0.3, H + 0.005), "g", 0.015)


def icon_raspberrypi():
    """Raspberry Pi, sculpted (the mark has a ® and hairline outlines that mesh badly): a red berry
    of round drupelets on a red core, two slate leaves on top."""
    cx, cz = 0.0, 1.0
    ellipsoid((cx, 0.08, cz), (0.78, 0.66, 0.9), "p")  # core
    rows = [(0.62, 3), (0.28, 4), (-0.08, 5), (-0.44, 4), (-0.76, 3)]  # (height, count) top to bottom
    for hz, n in rows:
        half = math.sqrt(max(0.0, 1 - (hz / 0.98) ** 2))
        for k in range(n):
            u = (k - (n - 1) / 2) / max(1, n - 1) * 1.7 * half if n > 1 else 0.0
            # sit on the core's front, facing the camera (-y), spread on the visible half
            ang = u
            r = 0.27 if n >= 4 else 0.25
            x = cx + 0.74 * half * math.sin(ang)
            y = 0.08 - 0.6 * half * math.cos(ang)
            ellipsoid((x, y, cz + hz), (r, r, r), "p", segs=48)
    for side in (-1, 1):  # leaves, splayed up and out like the logo
        ellipsoid((cx + side * 0.36, 0.0, cz + 1.0), (0.42, 0.13, 0.2), "r", rot=(0, D2R(side * -28), 0))


# ---------------------------------------------------------------- ecosystem gaps (009)
def _clean_logo(width, loc, role="g", depth=0.04, rot=FACE):
    import bmesh
    m = logo(width, loc, role, depth, rot=rot, soft=False)
    bpy.ops.object.select_all(action="DESELECT")
    m.select_set(True)
    bpy.context.view_layer.objects.active = m
    bpy.ops.object.convert(target="MESH")
    bm = bmesh.new()
    bm.from_mesh(m.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(m.data)
    bm.free()
    for f in m.data.polygons:
        f.use_smooth = False
    return m


def icon_desktop():
    """Desktop monitor on a stand, the screen showing the Viaalink app (logo + text lines)."""
    box((1.35, 0.9, 0.2), (0, 0.08, 0.1), "s", 0.09)
    box((0.46, 0.36, 0.48), (0, 0.08, 0.34), "s", 0.09)
    dev = Device(2.65, 1.85, 0.38, "p", screen=(0.18, 0.18, 0.18, 0.18), z0=0.52, bevel=0.2)
    lx, _, lz = dev.at(0, 0.24)
    _clean_logo(0.86, (lx, dev.floor - 0.035, lz), "g", 0.04, rot=FACE)
    for v, u1 in ((-0.04, 0.32), (-0.19, 0.32), (-0.34, 0.12)):
        bar(dev, -0.32, u1, v, 0.045)


def icon_tablet():
    """Landscape tablet: red body, navy screen with two cream text blocks."""
    dev = Device(2.55, 1.85, 0.36, "p", screen=(0.22, 0.22, 0.2, 0.2), bevel=0.24)
    # home indicator dot on right bezel
    cyl(0.065, 0.06, (2.55 / 2 - 0.11, dev.face - 0.01, 1.85 / 2), "c", 0.02, rot=FACE)
    for sx, u0 in ((-1, -0.38), (1, 0.05)):
        x, y, z = dev.at((u0 + (u0 + 0.33)) / 2, 0.22)
        box((dev.sw * 0.33, 0.09, 0.26), (x, y - 0.03, z), "g", 0.07)
        bar(dev, u0, u0 + 0.33, -0.04, 0.045)
        bar(dev, u0, u0 + (0.24 if sx < 0 else 0.2), -0.22, 0.045)


def icon_browser_ext():
    """Puzzle piece (red) with a small cream Viaalink logo on it."""
    W = 1.65
    h = W / 2
    # square body with top knob and right knob, left socket cut
    pts = [
        (-h, -h, 0.22),
        (h, -h, 0.22),
        (h, -0.22, 0.08),
        (h + 0.42, -0.26, 0.18),
        (h + 0.42, 0.26, 0.18),
        (h, 0.22, 0.08),
        (h, h, 0.22),
        (0.22, h, 0.08),
        (0.26, h + 0.42, 0.18),
        (-0.26, h + 0.42, 0.18),
        (-0.22, h, 0.08),
        (-h, h, 0.22),
    ]
    D = 0.52
    cz = h + 0.1
    body = plate(round_corners(pts, 14), D, (0, D / 2, cz), "p", rot=FACE, edge=0.09, clean=True)
    # cut left socket
    cyl_cut = cyl(0.27, D * 2.5, (-h + 0.04, 0, cz), "p", 0, rot=FACE)
    cut(body, cyl_cut)
    smooth(body)
    face = -D / 2
    _clean_logo(0.88, (0.06, face - 0.05, cz - 0.02), "c", 0.08, rot=FACE)


def icon_vscode():
    """Code editor window (red frame, navy pane) showing '</>' in cream."""
    W, H = 2.65, 2.05
    dev = Device(W, H, 0.42, "p", screen=(0.17, 0.17, 0.48, 0.17), bevel=0.2)
    zt = H - 0.25
    f = dev.face
    for k in range(3):
        cyl(0.075, 0.08, (-W / 2 + 0.34 + k * 0.24, f - 0.02, zt), "c", 0.03, rot=FACE)
    # '<' '/' '>' on the screen
    glyph(dev, [(-0.20, 0.20), (-0.36, 0.0), (-0.20, -0.20)], 0.058, "g")
    glyph(dev, [(-0.06, -0.26), (0.06, 0.26)], 0.055, "g")
    glyph(dev, [(0.20, 0.20), (0.36, 0.0), (0.20, -0.20)], 0.058, "g")


def icon_mail():
    """Envelope (red) with a cream flap line."""
    W, H, D = 2.45, 1.72, 0.48
    cz = H / 2 + 0.1
    box((W, D, H), (0, 0, cz), "p", 0.2)
    face = -D / 2
    flap = stroke_outline([(-0.92, 0.44), (0.0, -0.18), (0.92, 0.44)], 0.20)
    plate(flap, 0.10, (0, face + 0.02, cz), "c", rot=FACE, edge=0.035, clean=True)


def icon_calendar():
    """Desk calendar: red binding rings on top, cream page with a grid and one red day."""
    W, H, D = 2.15, 2.15, 0.44
    cz = H / 2
    box((W, D, H), (0, 0, cz), "p", 0.22)
    face = -D / 2
    # cream page on lower part of the front
    pw, ph, pz = 1.75, 1.38, cz - 0.16
    plate(rr_profile(pw, ph, 0.16), 0.08, (0, face + 0.01, pz), "c", rot=FACE, edge=0.025, clean=True)
    pf = face - 0.07
    # 3x2 grid of days: 5 navy (r) cells and 1 red (p) day cell
    for r_idx, dz in enumerate((0.26, -0.24)):
        for c_idx, dx in enumerate((-0.48, 0.0, 0.48)):
            is_red = (r_idx == 0 and c_idx == 1)
            role = "p" if is_red else "r"
            plate(rr_profile(0.34, 0.30, 0.07), 0.05, (dx, pf + 0.01, pz + dz), role, rot=FACE, edge=0.015, clean=True)
    # two chunky red binding rings on top with a cream collar where they enter
    for rx in (-0.56, 0.56):
        cyl(0.20, 0.08, (rx, 0, H + 0.01), "c", 0.03)
        box((0.24, 0.28, 0.48), (rx, 0, H + 0.12), "p", 0.09)


def icon_qr_pair():
    """QR code tile (cream with navy squares; three finder squares) with a small red link chain badge in the corner."""
    W, D = 2.1, 0.42
    cz = W / 2 + 0.08
    box((W, D, W), (0, 0, cz), "s", 0.22)
    face = -D / 2
    # 3 finder squares at top-left, top-right, bottom-left
    for fx, fz in ((-0.52, 0.52), (0.52, 0.52), (-0.52, -0.52)):
        outer = rr_profile(0.62, 0.62, 0.1)
        inner = rr_profile(0.38, 0.38, 0.05)
        rim(outer, inner, 0.05, (fx, face + 0.01, cz + fz), "r", rot=FACE)
        plate(rr_profile(0.20, 0.20, 0.04), 0.05, (fx, face + 0.01, cz + fz), "r", rot=FACE, edge=0.01)
    # data modules
    for mx, mz in ((0.0, 0.52), (0.0, 0.0), (-0.52, 0.0), (0.0, -0.52)):
        plate(rr_profile(0.22, 0.22, 0.05), 0.05, (mx, face + 0.01, cz + mz), "r", rot=FACE, edge=0.01)
    # red link chain badge at bottom-right corner
    bx, by, bz = 0.62, face - 0.12, cz - 0.58
    cyl(0.58, 0.24, (bx, by, bz), "p", 0.08, rot=FACE)
    bf = by - 0.12
    # two clearly separated interlocked chain links (left-lower, right-upper) rotated 35°
    ca, sa = math.cos(D2R(35)), math.sin(D2R(35))
    rot_pts = lambda pts, ox, oz: [((x + ox) * ca - (y + oz) * sa, (x + ox) * sa + (y + oz) * ca) for x, y in pts]
    for ox, oz in ((-0.16, -0.04), (0.16, 0.04)):
        p_out = rot_pts(rr_profile(0.42, 0.25, 0.12), ox, oz)
        p_in = rot_pts(rr_profile(0.22, 0.09, 0.04), ox, oz)
        rim(p_out, p_in, 0.05, (bx, bf + 0.01, bz), "c", rot=FACE)


def icon_bluetooth():
    """The Bluetooth rune itself as a thick red solid with a rounded rim, standing, no disc."""
    import bmesh
    D, cz = 0.38, 1.22
    outer_pts = round_corners([
        (-0.58, -0.66, 0.09),
        (-0.15, -0.26, 0.05),
        (-0.15, -1.06, 0.09),
        (0.06, -1.14, 0.10),
        (0.84, -0.51, 0.11),
        (0.18, 0.0, 0.06),
        (0.84, 0.51, 0.11),
        (0.06, 1.14, 0.10),
        (-0.15, 1.06, 0.09),
        (-0.15, 0.26, 0.05),
        (-0.58, 0.66, 0.09),
        (-0.76, 0.46, 0.09),
        (-0.22, 0.0, 0.06),
        (-0.76, -0.46, 0.09),
    ], 16)
    cu = bpy.data.curves.new("bt", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    for loop in [
        outer_pts,
        round_corners([(0.11, 0.17, 0.04), (0.53, 0.51, 0.04), (0.11, 0.85, 0.04)], 12),
        round_corners([(0.11, -0.85, 0.04), (0.53, -0.51, 0.04), (0.11, -0.17, 0.04)], 12),
    ]:
        sp = cu.splines.new("POLY")
        sp.use_cyclic_u = True
        sp.points.add(len(loop) - 1)
        for p, (x, y) in zip(sp.points, loop):
            p.co = (x, y, 0, 1)
    o = bpy.data.objects.new("bt", cu)
    bpy.context.collection.objects.link(o)
    o.location = (0, D / 2, cz)
    o.rotation_euler = FACE
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.view_layer.objects.active
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_limit(bm, angle_limit=D2R(1), verts=bm.verts, edges=bm.edges)
    ext = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=(0, 0, D))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    finish(o, "p", 0.065, 12)
    bpy.ops.object.modifier_apply(modifier="bevel")
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()
    caps = [f for f in bm.faces if abs(f.normal.z) > 0.95 and len(f.verts) > 4]
    res = bmesh.ops.triangulate(bm, faces=caps)
    cap_tris = set(res["faces"])
    for f in bm.faces:
        f.smooth = f not in cap_tris
    bm.to_mesh(o.data)
    bm.free()


def icon_wifi():
    """The three arcs and the dot themselves as thick, rounded red solids standing upright, no tile."""
    D, bz = 0.48, 0.34
    cyl(0.24, D, (0, 0, bz), "p", 0.07, rot=FACE)
    a0, a1, h = D2R(42), D2R(138), 0.14
    n_arc, n_cap = 32, 16
    for r in (0.66, 1.16, 1.66):
        outer = [((r + h) * math.cos(a0 + (a1 - a0) * k / n_arc), (r + h) * math.sin(a0 + (a1 - a0) * k / n_arc)) for k in range(n_arc + 1)]
        cap1 = [(r * math.cos(a1) + h * math.cos(a1 + math.pi * k / n_cap), r * math.sin(a1) + h * math.sin(a1 + math.pi * k / n_cap)) for k in range(1, n_cap)]
        inner = [((r - h) * math.cos(a1 - (a1 - a0) * k / n_arc), (r - h) * math.sin(a1 - (a1 - a0) * k / n_arc)) for k in range(n_arc + 1)]
        cap0 = [(r * math.cos(a0) + h * math.cos(a0 - math.pi + math.pi * k / n_cap), r * math.sin(a0) + h * math.sin(a0 - math.pi + math.pi * k / n_cap)) for k in range(1, n_cap)]
        plate(outer + cap1 + inner + cap0, D, (0, D / 2, bz), "p", rot=FACE, edge=0.065, clean=True)


def icon_license():
    """A key (red bow with a cream hole, cream bit) lying over a small cream card."""
    # cream card behind-right
    box((1.95, 0.34, 1.45), (0.22, 0.18, 1.05), "s", 0.18)
    for dz, w in ((0.26, 1.05), (-0.04, 0.75)):
        box((w, 0.08, 0.13), (0.22 - (1.05 - w) / 2, -0.01, 1.05 + dz), "r", 0.05)
    # key lying diagonally in front of the card as a single smooth profile for shaft + bit
    from mathutils import Matrix
    kc = Vector((-0.15, -0.22, 0.88))
    bit_pts = [
        (-0.20, 0.11, 0.04),
        (0.92, 0.11, 0.09),
        (0.92, -0.32, 0.07),
        (0.72, -0.32, 0.07),
        (0.72, -0.11, 0.03),
        (0.60, -0.11, 0.03),
        (0.60, -0.36, 0.07),
        (0.40, -0.36, 0.07),
        (0.40, -0.11, 0.03),
        (-0.20, -0.11, 0.04),
    ]
    shaft = plate(round_corners(bit_pts, 10), 0.24, (-0.15, -0.22 + 0.12, 0.88), "c", rot=FACE, edge=0.04, clean=True)
    # red bow with recessed cream hole
    bow = cyl(0.52, 0.28, (-0.52, -0.22, 0.88), "p", 0.09, rot=FACE)
    hole = cyl(0.20, 0.32, (-0.52, -0.22, 0.88), "c", 0.04, rot=FACE)
    bpy.context.view_layer.update()
    M = Matrix.Translation(kc) @ Matrix.Rotation(D2R(-24), 4, "Y") @ Matrix.Translation(-kc)
    for o in (shaft, bow, hole):
        o.matrix_world = M @ o.matrix_world


def icon_payment():
    """Credit card (red) with a navy stripe and a cream chip."""
    W, H, D = 2.45, 1.68, 0.42
    cz = H / 2 + 0.12
    box((W, D, H), (0, 0, cz), "p", 0.22)
    face = -D / 2
    # navy magnetic stripe near top
    plate(rr_profile(W - 0.24, 0.36, 0.08), 0.06, (0, face + 0.01, cz + 0.34), "r", rot=FACE, edge=0.015)
    # cream chip on lower-left and two short number pills on lower-right
    plate(rr_profile(0.52, 0.40, 0.09), 0.08, (-0.62, face + 0.01, cz - 0.28), "c", rot=FACE, edge=0.025, clean=True)
    for dx in (0.12, 0.64):
        plate(rr_profile(0.36, 0.14, 0.06), 0.07, (dx, face + 0.01, cz - 0.34), "c", rot=FACE, edge=0.02, clean=True)


def _tray_arrow_icon(up=True):
    D = 0.50
    # low cream rounded bar at the bottom
    plate(rr_profile(2.05, 0.40, 0.195), D, (0, D / 2, 0.20), "s", rot=FACE, edge=0.07, clean=True)
    # thick red arrow pointing up (upload) or down (download) above the cream bar
    arr = arrow_profile(-0.78, 0.06, 0.66, 0.78, 0.38)
    ang = 90 if up else -90
    ca, sa = math.cos(D2R(ang)), math.sin(D2R(ang))
    arr_rot = [(x * ca - y * sa, x * sa + y * ca) for x, y in arr]
    plate(arr_rot, D, (0, D / 2, 1.52), "p", rot=FACE, edge=0.07, clean=True)


def icon_upload():
    """Red rounded tray with a cream arrow up."""
    _tray_arrow_icon(up=True)


def icon_download():
    """Red rounded tray with a cream arrow down."""
    _tray_arrow_icon(up=False)


def _curved_arrow_profile(R, a0_deg, a1_deg, w, head_len=0.36, head_hw=0.28, n=28):
    """Single closed 2D profile of a circular arc arrow from a0_deg to a1_deg (CCW if a1 > a0)."""
    sgn = 1 if a1_deg > a0_deg else -1
    ro, ri = R + w / 2, R - w / 2
    # arc shaft stops slightly before a1_deg so the triangular head sits at a1_deg
    da_head = sgn * math.degrees(head_len / R) * 0.45
    a_shaft_end = a1_deg - da_head
    outer = [(ro * math.cos(D2R(a0_deg + (a_shaft_end - a0_deg) * k / n)),
              ro * math.sin(D2R(a0_deg + (a_shaft_end - a0_deg) * k / n)), 0.0) for k in range(n + 1)]
    inner = [(ri * math.cos(D2R(a0_deg + (a_shaft_end - a0_deg) * k / n)),
              ri * math.sin(D2R(a0_deg + (a_shaft_end - a0_deg) * k / n)), 0.0) for k in range(n, -1, -1)]
    ar = D2R(a_shaft_end)
    er = Vector((math.cos(ar), math.sin(ar)))
    et = Vector((-sgn * math.sin(ar), sgn * math.cos(ar)))
    base = er * R
    w_out = base + er * head_hw
    w_in = base - er * head_hw
    tip = base + et * head_len
    pts = [
        (outer[0][0], outer[0][1], w * 0.4),
        *outer[1:-1],
        (outer[-1][0], outer[-1][1], 0.03),
        (w_out.x, w_out.y, 0.06),
        (tip.x, tip.y, 0.06),
        (w_in.x, w_in.y, 0.06),
        (inner[0][0], inner[0][1], 0.03),
        *inner[1:-1],
        (inner[-1][0], inner[-1][1], w * 0.4),
    ]
    return round_corners(pts, 8)


def icon_sync():
    """Two curved red arrows forming a circle around a cream dot."""
    cz = 1.22
    D = 0.48
    # central cream dot
    cyl(0.32, D * 0.9, (0, 0, cz), "s", 0.10, rot=FACE)
    # two curved red arrows around it
    for a0, a1 in ((25, 165), (205, 345)):
        prof = _curved_arrow_profile(0.86, a0, a1, 0.28, head_len=0.42, head_hw=0.30)
        plate(prof, D, (0, D / 2, cz), "p", rot=FACE, edge=0.07, clean=True)


def icon_backup():
    """Database-like 3-tier cylinder with two clear disk seams (like icon_database) and a large
    central cream circular restore arrow wrapped onto the front face."""
    import bmesh
    R = 1.12
    for i in range(3):
        cz = 0.36 + i * 0.74
        cyl(R, 0.56, (0, 0, cz), "p", 0.13)
        if i < 2:
            cyl(0.90, 0.22, (0, 0, cz + 0.37), "s", 0.04)
    # large central cream circular arrow wrapped smoothly onto the front of the cylinder
    prof = _curved_arrow_profile(0.58, -35, -315, 0.21, head_len=0.38, head_hw=0.30, n=64)
    arr = plate(prof, 0.28, (0, 0, 0), "c", edge=0.035, clean=True)
    bm = bmesh.new()
    bm.from_mesh(arr.data)
    long_edges = [e for e in bm.edges if e.calc_length() > 0.16]
    if long_edges:
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=2)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    phi0 = D2R(35 - 90)
    cz_mid = 1.10
    for v in bm.verts:
        x2d, y2d, zloc = v.co.x, v.co.y, v.co.z
        phi = phi0 + x2d / (R + 0.04)
        rad = (R - 0.15) + zloc
        v.co = Vector((rad * math.cos(phi), rad * math.sin(phi), cz_mid + y2d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(arr.data)
    bm.free()
    smooth(arr, 60)


def icon_voice_profile():
    """Person bust (cream head) with a red waveform badge (3-5 bars) at the shoulder."""
    # cream person bust (head + shoulders)
    toy_bust(-0.18, 0.05, 0.12, 1.55, "s")
    # red waveform badge at the front-right shoulder
    bx, by, bz = 0.62, -0.26, 0.62
    cyl(0.58, 0.28, (bx, by, bz), "p", 0.09, rot=FACE)
    bf = by - 0.14
    for k, hgt in ((-1, 0.36), (0, 0.62), (1, 0.36)):
        bar_prof = stroke_outline([(k * 0.22, -hgt / 2), (k * 0.22, hgt / 2)], 0.13)
        plate(bar_prof, 0.07, (bx, bf + 0.02, bz), "c", rot=FACE, edge=0.02, clean=True)


def icon_video():
    """Red video camera body with a navy lens and a small cream record dot."""
    W, H, D = 1.75, 1.45, 0.95
    cz = H / 2 + 0.15
    # main camera body on the left
    box((W, D, H), (-0.28, 0, cz), "p", 0.22)
    face = -D / 2
    # recessed navy viewport/lens on the front face + cream record dot
    plate(rr_profile(0.78, 0.68, 0.16), 0.05, (-0.42, face + 0.02, cz - 0.06), "r", rot=FACE, edge=0.015)
    cyl(0.12, 0.08, (0.24, face - 0.02, cz + 0.36), "c", 0.03, rot=FACE)
    # side lens hood on the right (+X) with navy lens interior
    hood = round_corners([
        (0.52, cz - 0.32, 0.08),
        (1.22, cz - 0.56, 0.12),
        (1.22, cz + 0.56, 0.12),
        (0.52, cz + 0.32, 0.08),
    ], 12)
    plate(hood, 0.68, (0, 0.34, 0), "p", rot=FACE, edge=0.09, clean=True)
    plate(rr_profile(0.18, 0.68, 0.06), 0.06, (1.06, -0.34 + 0.02, cz), "r", rot=FACE, edge=0.015)


# ---------------------------------------------------------------- network (011)
def icon_router():
    """Home Wi-Fi router: low wide rounded red box, two thick rounded cream antennas standing up
    at the back (slightly splayed so it never reads as a plug), 4 glowing front status LEDs, and
    left/right cream pipe ports like icon_caddy."""
    W, D, H = 2.28, 1.45, 1.02
    y_body = -0.06
    cz = H / 2
    box((W, D, H), (0, y_body, cz), "p", 0.18)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), y_body, cz), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), y_body, cz), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    face = y_body - D / 2
    # dark recessed LED window along the front edge with 4 glowing status LEDs
    plate(rr_profile(1.72, 0.32, 0.15), 0.04, (0, face + 0.015, cz), "r", rot=FACE, edge=0.012)
    for lx in (-0.57, -0.19, 0.19, 0.57):
        cyl(0.082, 0.055, (lx, face - 0.01, cz), "g", 0.022, rot=FACE)
    # two thick rounded cream antennas standing up at the back, subtly splayed outward
    y_ant = y_body + D / 2 - 0.28
    tilt = D2R(8)
    for sx in (-1, 1):
        bx = sx * 0.72
        cyl(0.19, 0.14, (bx, y_ant, H + 0.03), "s", 0.04)
        L = 1.34
        box((0.25, 0.22, L), (bx + sx * (L / 2) * math.sin(tilt), y_ant, H + (L / 2) * math.cos(tilt)), "s", 0.105, rot=(0, sx * tilt, 0))


def _globe_emblem(R, loc, depth=0.055, role="c"):
    """Seamless 3D globe wireframe emblem (outer circle + curved meridian ellipse + equator)."""
    import bmesh
    r_in = R * 0.77
    b = R * 0.095  # half equator thickness
    a_in, z_in = R * 0.31, R * 0.74
    a_out, z_out = R * 0.50, R * 0.88
    loops = [[(R * math.cos(2 * math.pi * k / 72), R * math.sin(2 * math.pi * k / 72)) for k in range(72)]]
    # 2 inner meridian-equator D-loops (top-center, bottom-center)
    for sy in (-1, 1):
        ys = [b + (z_in - b) * k / 24 for k in range(25)]
        right = [(a_in * math.sqrt(max(0.0, 1 - (y / z_in) ** 2)), sy * y) for y in ys]
        left = [(-x, y) for x, y in reversed(right[:-1])]
        loops.append(right + left)
    # 4 outer crescent loops between meridian ellipse and outer ring
    y_top = math.sqrt(max(b * b + 1e-5, (r_in * r_in - a_out * a_out) / max(1e-4, 1 - (a_out / z_out) ** 2))) * 0.96
    for sx in (-1, 1):
        for sy in (-1, 1):
            ys = [b + (y_top - b) * k / 20 for k in range(21)]
            inner_e = [(sx * a_out * math.sqrt(max(0.0, 1 - (y / z_out) ** 2)), sy * y) for y in ys]
            outer_c = [(sx * math.sqrt(max(0.0, r_in * r_in - y * y)), sy * y) for y in reversed(ys)]
            loops.append(inner_e + outer_c)
    cu = bpy.data.curves.new("globe_emblem", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    for loop in loops:
        sp = cu.splines.new("POLY")
        sp.use_cyclic_u = True
        sp.points.add(len(loop) - 1)
        for p, (x, y) in zip(sp.points, loop):
            p.co = (x, y, 0, 1)
    o = bpy.data.objects.new("globe_emblem", cu)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = FACE
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.view_layer.objects.active
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    ext = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    bmesh.ops.translate(bm, verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)], vec=(0, 0, depth))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    finish(o, role, 0.012, 6)
    bpy.ops.object.modifier_apply(modifier="bevel")
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()
    caps = [f for f in bm.faces if abs(f.normal.z) > 0.95 and len(f.verts) > 4]
    res = bmesh.ops.triangulate(bm, faces=caps)
    cap_tris = set(res["faces"])
    for f in bm.faces:
        f.smooth = f not in cap_tris
    bm.to_mesh(o.data)
    bm.free()
    return o


def icon_modem():
    """ISP modem: slim upright red box standing on a small cream foot, front face with a small
    cream round globe/line emblem at the top, a vertical row of 4 glowing LEDs, and left/right
    cream pipe ports like icon_caddy; no antennas."""
    box((1.38, 1.48, 0.24), (0, 0, 0.12), "s", 0.10)  # cream foot
    W, D, H = 1.14, 1.34, 2.20
    z0 = 0.18
    cz = z0 + H / 2
    box((W, D, H), (0, 0, cz), "p", 0.18)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, 0.91), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, 0.91), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    face = -D / 2
    # small cream round globe/line emblem near the top of the front face
    gz = z0 + H - 0.47
    _globe_emblem(0.29, (0, face + 0.015, gz), depth=0.055, role="c")
    # vertical row of 4 glowing LEDs down the front face
    for lz in (1.34, 1.07, 0.80, 0.53):
        cyl(0.082, 0.06, (0, face - 0.005, lz), "g", 0.025, rot=FACE)


def icon_caddy():
    """Caddy reverse proxy: compact red rounded box like icon_relay with short thick cream round
    pipe ports on left and right, a navy recess plate on -Y with Caddy's official mark in cream,
    and three small glowing status dots below."""
    W, D, H = 1.92, 1.45, 1.82
    dev = Device(W, H, D, "p", screen=(0.20, 0.20, 0.16, 0.40), bevel=0.18)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, H / 2), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, H / 2), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    o = brand_mark("caddy-mark", 1.18, (dev.cx, dev.floor - 0.025, dev.cz), 0.056, "c", bevel=0.0055)
    for f in o.data.polygons:
        f.use_smooth = abs(f.normal.z) < 0.99
    for lx in (-0.30, 0.0, 0.30):
        cyl(0.078, 0.06, (lx, dev.face - 0.01, 0.21), "g", 0.025, rot=FACE)


def icon_certstore():
    """Certificate store: upright red cabinet on a stepped cream foot, device-family ports on the back-lower
    half of the sides, two drawers; top drawer pulled well out toward -Y with a big cream certificate card
    (big red scalloped seal, hanging red V-ribbons, embossed lines) as the hero, plus a top status light."""
    box((1.84, 1.72, 0.22), (0, -0.02, 0.11), "c:dim", 0.095)
    box((1.40, 1.32, 0.16), (0, 0.0, 0.24), "c:dim", 0.05)
    W, D, H = 1.66, 1.66, 2.42
    z0 = 0.28
    cab = box((W, D, H), (0, 0, z0 + H / 2), "p", 0.23)
    y_port, z_port = 0.44, 0.74
    for sx in (-1, 1):
        p_cyl = cyl(0.38, 0.84, (sx * (W / 2 + 0.10), y_port, z_port), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.205, 0.80, (sx * (W / 2 + 0.38), y_port, z_port), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    face = -D / 2
    cyl(0.084, 0.06, (0, face - 0.01, z0 + H - 0.23), "g", 0.028, rot=FACE)
    z_bot = z0 + 0.46
    cut(cab, plate(rr_profile(1.28, 0.58, 0.11), 0.30, (0, face + 0.07, z_bot), "r", rot=FACE))
    plate(rr_profile(1.28, 0.58, 0.11), 0.02, (0, face + 0.072, z_bot), "r", rot=FACE)
    z_top = z0 + 1.18
    cut(cab, plate(rr_profile(1.28, 0.66, 0.12), 0.92, (0, face + 0.64, z_top), "r", rot=FACE))
    plate(rr_profile(1.28, 0.66, 0.12), 0.02, (0, face + 0.642, z_top), "r", rot=FACE)
    smooth(cab)

    def _drawer_handle(y_front, z_c):
        hx, hd, rc = 0.27, 0.14, 0.06
        pts = [(-hx, y_front + 0.05, z_c)]
        for k in range(9):
            a = math.pi + (math.pi / 2) * k / 8
            pts.append((-hx + rc + rc * math.cos(a), y_front - hd + rc + rc * math.sin(a), z_c))
        for k in range(9):
            a = -math.pi / 2 + (math.pi / 2) * k / 8
            pts.append((hx - rc + rc * math.cos(a), y_front - hd + rc + rc * math.sin(a), z_c))
        pts.append((hx, y_front + 0.05, z_c))
        tube(pts, 0.058, "c:dim")

    box((1.18, 0.16, 0.48), (0, face + 0.02, z_bot), "p", 0.08)
    _drawer_handle(face - 0.06, z_bot)

    pull = 0.90
    tray = box((1.18, 1.00, 0.48), (0, face - pull + 0.51, z_top - 0.05), "r", 0.08)
    cut(tray, box((1.00, 0.86, 0.48), (0, face - pull + 0.51, z_top + 0.08), "r", 0.04))
    smooth(tray)
    box((1.22, 0.19, 0.52), (0, face - pull, z_top - 0.03), "p", 0.09)
    _drawer_handle(face - pull - 0.095, z_top - 0.03)

    yc = face - pull * 0.55
    card_z = 1.88
    box((1.16, 0.16, 1.12), (0, yc, card_z), "c:dim", 0.09)
    cf = yc - 0.08
    sx_s, sz_s = -0.20, 2.05
    rib = round_corners([
        (-0.13, 0.02, 0.02),
        (-0.25, -0.37, 0.022),
        (-0.14, -0.30, 0.0),
        (-0.07, -0.39, 0.022),
        (0.0, -0.18, 0.0),
        (0.07, -0.39, 0.022),
        (0.14, -0.30, 0.0),
        (0.25, -0.37, 0.022),
        (0.13, 0.02, 0.02),
    ], 8)
    plate(rib, 0.065, (sx_s, cf + 0.015, sz_s), "p", rot=FACE, edge=0.016, clean=True)
    n_lobes = 12
    seal_pts = []
    for k in range(n_lobes * 8):
        a = 2 * math.pi * k / (n_lobes * 8)
        r = 0.245 + 0.024 * math.cos(n_lobes * a)
        seal_pts.append((r * math.cos(a), r * math.sin(a)))
    plate(seal_pts, 0.08, (sx_s, cf + 0.01, sz_s), "p", rot=FACE, edge=0.02, clean=True)
    torus(0.148, 0.026, (sx_s, cf - 0.068, sz_s), "p", rot=FACE)
    cyl(0.085, 0.07, (sx_s, cf - 0.048, sz_s), "p", 0.03, rot=FACE)
    for lz, x1 in ((2.16, 0.45), (1.98, 0.45), (1.80, 0.35)):
        plate(stroke_outline([(0.14, lz), (x1, lz)], 0.09), 0.055, (0, cf + 0.02, 0), "c:dim", rot=FACE, edge=0.02, clean=True)


def icon_dns():
    """DNS: compact red box with left/right cream pipe ports like icon_caddy and a cream signpost on
    top (post + two arrow-shaped boards pointing in different directions); front face (-Y) has a
    navy recess with three short cream lines (an address list) and three small glowing dots."""
    from mathutils import Matrix
    W, D, H = 2.12, 1.58, 1.38
    dev = Device(W, H, D, "p", screen=(0.22, 0.22, 0.18, 0.36), bevel=0.20)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, H / 2), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, H / 2), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    for v, u1 in ((0.27, 0.34), (0.0, 0.12), (-0.27, 0.25)):
        bar(dev, -0.35, u1, v, 0.046, role="c")
    for lx in (-0.28, 0.0, 0.28):
        cyl(0.075, 0.06, (lx, dev.face - 0.01, 0.19), "g", 0.025, rot=FACE)
    px, py = 0.0, 0.04
    cyl(0.28, 0.12, (px, py, H + 0.03), "s", 0.05)
    post_h = 1.38
    capsule((px, py, H + 0.02), (px, py, H + post_h), 0.135, "s")
    bt = 0.16
    for sgn, bz, ang in ((1, H + 0.98, 22), (-1, H + 0.50, -12)):
        pts = round_corners([
            (-0.03 * sgn, -0.175, 0.04),
            (0.70 * sgn, -0.175, 0.05),
            (1.00 * sgn, 0.0, 0.05),
            (0.70 * sgn, 0.175, 0.05),
            (-0.03 * sgn, 0.175, 0.04),
        ], 12)
        b_obj = plate(pts, bt, (px, py + bt / 2, bz), "s", rot=FACE, edge=0.05, clean=True)
        bpy.context.view_layer.update()
        M = Matrix.Translation((px, py, bz)) @ Matrix.Rotation(D2R(ang), 4, "Z") @ Matrix.Translation((-px, -py, -bz))
        b_obj.matrix_world = M @ b_obj.matrix_world


# ---------------------------------------------------------------- IT diagram icons, part A (015)
def _quad_ring_solid(outer_pts, inner_pts, loc, depth, role, bev=0.03, rot=FACE):
    """Extrude a clean 1-to-1 quad-ring annulus between two matching CCW 2D loops."""
    import bmesh
    n = len(outer_pts)
    verts = (
        [(x, y, 0.0) for x, y in outer_pts]
        + [(x, y, 0.0) for x, y in inner_pts]
        + [(x, y, depth) for x, y in outer_pts]
        + [(x, y, depth) for x, y in inner_pts]
    )
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, n + i, n + j, j])
        faces.append([2 * n + i, 2 * n + j, 3 * n + j, 3 * n + i])
        faces.append([i, j, 2 * n + j, 2 * n + i])
        faces.append([n + i, 3 * n + i, 3 * n + j, n + j])
    me = bpy.data.meshes.new("quad_ring")
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("quad_ring", me)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    finish(o, role, bev, 4)
    smooth(o, 35)
    return o


def icon_user():
    """One person bust (cream round head, red shoulders), alone. Like a single member of icon_team."""
    w, h, D = 0.98, 0.94, 0.88
    rc = 0.22
    n_arc, n_dome = 12, 48
    right_arc = [
        (w - rc + rc * math.cos(-math.pi / 2 + math.pi / 2 * k / n_arc), rc + rc * math.sin(-math.pi / 2 + math.pi / 2 * k / n_arc))
        for k in range(n_arc)
    ]
    dome = [(w * math.cos(math.pi * k / n_dome), rc + (h - rc) * math.sin(math.pi * k / n_dome)) for k in range(n_dome + 1)]
    left_arc = [
        (-w + rc + rc * math.cos(math.pi + math.pi / 2 * k / n_arc), rc + rc * math.sin(math.pi + math.pi / 2 * k / n_arc))
        for k in range(1, n_arc + 1)
    ]
    plate(right_arc + dome + left_arc, D, (0, D / 2, 0.0), "p", rot=FACE, edge=0.16, clean=True)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.57, location=(0, 0, 1.50), segments=64, ring_count=32)
    finish(bpy.context.object, "s")


def icon_key():
    """Chunky red key, round bow with a cream hole, a small cream tag hanging from the bow."""
    R_bow, v_sh = 0.70, 0.21
    u_join = -math.sqrt(R_bow * R_bow - v_sh * v_sh)
    a_top = math.pi - math.asin(v_sh / R_bow)
    a_bot = -a_top
    n_bow = 56
    bow_pts = [(R_bow * math.cos(a_bot + (a_top - a_bot) * k / n_bow),
                R_bow * math.sin(a_bot + (a_top - a_bot) * k / n_bow), 0.0) for k in range(n_bow + 1)]
    shaft_pts = [
        (-1.86, v_sh, 0.11),
        (-1.86, -0.56, 0.09),
        (-1.53, -0.56, 0.09),
        (-1.53, -v_sh, 0.05),
        (-1.31, -v_sh, 0.05),
        (-1.31, -0.49, 0.09),
        (-0.99, -0.49, 0.09),
        (-0.99, -v_sh, 0.05),
    ]
    raw = [(u_join, -v_sh, 0.05), *bow_pts[1:-1], (u_join, v_sh, 0.05), *shaft_pts]
    prof_local = round_corners(raw, 10)
    ca, sa = math.cos(D2R(36)), math.sin(D2R(36))
    bx, bz = 0.52, 1.56
    prof = [(bx + u * ca - v * sa, bz + u * sa + v * ca) for u, v in prof_local]
    D = 0.42
    body = plate(prof, D, (0, D / 2, 0), "p", rot=FACE, edge=0.095, clean=True)
    cut(body, cyl(0.32, D * 3.0, (bx, 0, bz), "p", 0, rot=FACE))
    smooth(body)
    # cream hole lining inside the bow
    liner = cyl(0.39, D + 0.03, (bx, 0, bz), "s", 0.05, rot=FACE)
    cut(liner, cyl(0.22, D * 3.0, (bx, 0, bz), "s", 0, rot=FACE))
    smooth(liner)
    # small cream tag hanging from the bow on a cream ring
    tx, ty, tz = 0.56, -0.06, 0.52
    tag = box((0.68, 0.26, 0.86), (tx, ty, tz), "s", 0.12)
    cut(tag, cyl(0.085, 0.6, (tx, ty, tz + 0.27), "r", 0, rot=FACE))
    smooth(tag)
    plate(rr_profile(0.42, 0.34, 0.07), 0.04, (tx, ty - 0.13 + 0.015, tz - 0.10), "r", rot=FACE, edge=0.01)
    # cream jump-ring threading through the bow hole and tag hole
    ring_pts = [(bx + 0.02, -0.03 + 0.18 * math.cos(2 * math.pi * k / 40), 1.07 + 0.28 * math.sin(2 * math.pi * k / 40)) for k in range(40)]
    ring(ring_pts, 0.072, "s")


def _shield_outline(w, zt, zsh, zb, rs=0.22, rt=0.16):
    """Smooth G1-continuous convex symmetric shield contour centred around (0, 0), CCW."""
    def bez3(p0, p1, p2, p3, m, include_end=False):
        rng = range(m + 1) if include_end else range(m)
        return [
            (
                (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0],
                (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1],
            )
            for t in [k / m for k in rng]
        ]

    xs = w - rs
    p_top = (xs, zsh)
    p2_crown = (xs * 0.78, zsh + (zt - zsh) * 0.55)
    t_in = (Vector(p_top) - Vector(p2_crown)).normalized()
    p_side = (w, zsh - rs)

    tx = rt
    ty = -zb + 0.38 * tx
    p_tip_r = (tx, ty)
    span = (w - tx) * 0.95
    p2_flank = (tx + span * 0.45, ty + span * 0.38)

    crown = bez3((0.0, zt), (xs * 0.42, zt), p2_crown, p_top, 16)
    shoulder = bez3(p_top, (p_top[0] + t_in.x * rs * 0.52, p_top[1] + t_in.y * rs * 0.52), (w, zsh - rs * 0.45), p_side, 12)
    flank = bez3(p_side, (w, zsh - rs - 0.42 * (zsh - rs + zb)), p2_flank, p_tip_r, 28)
    half_tip = bez3(p_tip_r, (tx * 0.55, -zb), (tx * 0.25, -zb), (0.0, -zb), 8, include_end=True)

    right_pts = crown + shoulder + flank + half_tip
    left_pts = [(-x, y) for x, y in reversed(right_pts[1:-1])]
    return (right_pts + left_pts)[::-1]


def icon_shield():
    """Upright red shield, cream rim, big cream check mark."""
    cz = 1.24
    D = 0.50
    outer = _shield_outline(1.08, 1.18, 0.96, 1.18, rs=0.22, rt=0.16)
    plate(outer, D, (0, D / 2, cz), "p", rot=FACE, edge=0.10, clean=True)
    face = -D / 2
    rim_out = _shield_outline(0.93, 1.02, 0.83, 1.00, rs=0.17, rt=0.12)
    rim_in = _shield_outline(0.74, 0.83, 0.67, 0.79, rs=0.11, rt=0.08)
    _quad_ring_solid(rim_out, rim_in, (0, face + 0.02, cz), 0.11, "s", bev=0.028, rot=FACE)
    chk = stroke_outline([(-0.40, -0.02), (-0.09, -0.33), (0.45, 0.34)], 0.25, n=20)
    plate(chk, 0.13, (0, face + 0.02, cz + 0.02), "c", rot=FACE, edge=0.038, clean=True)


def icon_firewall():
    """Device family box with side ports; front = brick wall (cream mortar lines on red), one g light."""
    W, D, H = 1.94, 1.45, 1.86
    box((W, D, H), (0, 0, H / 2), "p", 0.18)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, 0.91), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, 0.91), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    face = -D / 2
    cz = H / 2
    # cream mortar plate on -Y with staggered courses of rounded red bricks standing proud
    plate(rr_profile(1.52, 1.44, 0.14), 0.05, (0, face + 0.02, cz), "s", rot=FACE, edge=0.018, clean=True)
    bh, gap = 0.265, 0.075
    rows_z = [cz + (1.5 - r_idx) * (bh + gap) for r_idx in range(4)]
    for r_idx, rz in enumerate(rows_z):
        if r_idx % 2 == 0:
            bricks = [(-0.34, 0.605, "p"), (0.34, 0.605, "p")]
        elif r_idx == 1:
            bricks = [(-0.51, 0.265, "p"), (0.0, 0.605, "p"), (0.51, 0.265, "p")]
        else:
            bricks = [(-0.51, 0.265, "p"), (0.0, 0.605, "p"), (0.51, 0.265, "r")]
        for bx, bw, brole in bricks:
            b_depth = 0.055 if brole == "r" else 0.085
            b_edge = 0.015 if brole == "r" else 0.025
            plate(rr_profile(bw, bh, 0.05), b_depth, (bx, face - 0.01, rz), brole, rot=FACE, edge=b_edge, clean=True)
    # one glowing g status light in the bottom-right cell
    cyl(0.085, 0.07, (0.51, face - 0.075, rows_z[3]), "g", 0.025, rot=FACE)


def icon_cloud():
    """Clean chunky puffy red cloud (4 round lobes) with a flat cream underside; no band through it."""
    # flat cream underside flush with the cloud's lower perimeter (no protruding tray shelf)
    L_base, W_base, H_base = 2.52, 0.96, 0.34
    r_end = W_base / 2
    hx = (L_base - W_base) / 2
    base_prof = (
        [(hx + r_end * math.cos(-math.pi / 2 + math.pi * k / 24), r_end * math.sin(-math.pi / 2 + math.pi * k / 24)) for k in range(25)]
        + [(-hx + r_end * math.cos(math.pi / 2 + math.pi * k / 24), r_end * math.sin(math.pi / 2 + math.pi * k / 24)) for k in range(25)]
    )
    plate(base_prof, H_base, (0.02, 0.0, 0.0), "s", edge=0.12, clean=True)
    # 4 puffy round red lobes + plump belly core meeting the cream underside flush at z_cut
    lobes = [
        ((-0.84, 0.0, 0.64), (0.58, 0.56, 0.56)),
        ((-0.22, 0.0, 1.08), (0.74, 0.66, 0.76)),
        ((0.46, 0.0, 0.90), (0.62, 0.60, 0.64)),
        ((0.94, 0.0, 0.60), (0.50, 0.52, 0.50)),
        ((0.03, 0.0, 0.62), (1.16, 0.64, 0.52)),
    ]
    parts = []
    for loc, rad in lobes:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=loc, segments=64, ring_count=32)
        o = bpy.context.object
        o.scale = rad
        bpy.ops.object.transform_apply(location=True, scale=True)
        parts.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    cloud = bpy.context.view_layer.objects.active
    rem = cloud.modifiers.new("remesh", "REMESH")
    rem.mode = "VOXEL"
    rem.voxel_size = 0.025
    bpy.ops.object.modifier_apply(modifier=rem.name)
    sm = cloud.modifiers.new("sm", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = 6
    bpy.ops.object.modifier_apply(modifier=sm.name)
    Z_CUT, SOFT = 0.28, 0.04
    for v in cloud.data.vertices:
        z = v.co.z
        if z < Z_CUT + 6 * SOFT:
            v.co.z = Z_CUT + SOFT * math.log1p(math.exp((z - Z_CUT) / SOFT))
    finish(cloud, "p")
    smooth(cloud, 180)


def icon_container():
    """Generic shipping container: ribbed red box, cream corner posts, two cream doors on the end."""
    W, D, H = 1.56, 2.28, 1.56
    cz = H / 2 + 0.04
    # main red box + top/bottom side rails
    box((W - 0.08, D - 0.08, H), (0, 0, cz), "p", 0.10)
    for sz in (-1, 1):
        box((W, D, 0.20), (0, 0, cz + sz * (H / 2 - 0.08)), "p", 0.08)
    for sx in (-1, 1):
        box((0.20, D, 0.20), (sx * (W / 2 - 0.08), 0, cz + H / 2 - 0.08), "p", 0.08)
    # chunky vertical corrugation ribs along left & right walls, and transverse ribs on roof
    for k in range(5):
        ry = -0.72 + k * 0.36
        for sx in (-1, 1):
            box((0.10, 0.20, H - 0.34), (sx * (W / 2 - 0.02), ry, cz), "p", 0.045)
        box((W - 0.34, 0.20, 0.10), (0, ry, cz + H / 2 - 0.02), "p", 0.045)
    # four chunky cream vertical corner posts
    for sx in (-1, 1):
        for sy in (-1, 1):
            box((0.30, 0.30, H + 0.08), (sx * (W / 2 - 0.03), sy * (D / 2 - 0.03), cz), "s", 0.10)
    # end (-Y): dark door-frame recess + two cream double-doors with vertical locking bars
    face = -D / 2
    plate(rr_profile(1.06, 1.20, 0.08), 0.05, (0, face + 0.02, cz), "r", rot=FACE, edge=0.015)
    for sx in (-1, 1):
        dx = sx * 0.255
        plate(rr_profile(0.45, 1.08, 0.08), 0.09, (dx, face - 0.01, cz), "s", rot=FACE, edge=0.03, clean=True)
        bx = dx - sx * 0.09
        capsule((bx, face - 0.10, cz - 0.48), (bx, face - 0.10, cz + 0.48), 0.035, "c")
        box((0.14, 0.07, 0.07), (bx + sx * 0.05, face - 0.11, cz - 0.06), "c", 0.03)


def icon_cluster():
    """Three small identical red rounded cubes on one shared cream base plate, joined by short cream pipes."""
    pts_xy = [(-0.50, 0.72), (-0.48, -0.66), (0.80, -0.06)]
    # shared cream base plate hugging the 3 nodes with generous rounded corners
    cx_avg = sum(x for x, _ in pts_xy) / 3
    cy_avg = sum(y for _, y in pts_xy) / 3
    pad_pts = []
    for px, py in pts_xy:
        vx, vy = px - cx_avg, py - cy_avg
        d = math.hypot(vx, vy)
        pad_pts.append((px + vx / d * 1.08, py + vy / d * 1.08, 0.80))
    plate(round_corners(pad_pts, 24), 0.26, (0, 0, 0.0), "s", edge=0.10, clean=True)
    # three short cream pipes joining the 3 cubes in a triangle
    cz = 0.26 + 0.43
    for i in range(3):
        x1, y1 = pts_xy[i]
        x2, y2 = pts_xy[(i + 1) % 3]
        tube([(x1, y1, cz), (x2, y2, cz)], 0.135, "s")
    # three small identical red rounded cubes, each with a glowing status dot on top
    for px, py in pts_xy:
        box((0.86, 0.86, 0.86), (px, py, cz), "p", 0.16)
        cyl(0.085, 0.05, (px - 0.18, py - 0.18, cz + 0.43), "g", 0.02)


def icon_vm():
    """Device family box with side ports; front = navy screen showing a small cream box (machine in a machine)."""
    W, D, H = 1.92, 1.45, 1.82
    dev = Device(W, H, D, "p", screen=(0.20, 0.20, 0.20, 0.20), bevel=0.18)
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, H / 2), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, H / 2), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    # small cream box inside the navy screen (machine in a machine)
    mx, my, mz = dev.cx, dev.floor - 0.08, dev.cz - 0.02
    box((0.92, 0.28, 0.84), (mx, my, mz), "s", 0.13)
    mf = my - 0.14
    plate(rr_profile(0.66, 0.24, 0.08), 0.04, (mx, mf + 0.015, mz + 0.16), "p", rot=FACE, edge=0.015, clean=True)
    for lx in (-0.19, -0.04):
        cyl(0.058, 0.05, (mx + lx, mf - 0.015, mz + 0.16), "g", 0.018, rot=FACE)
    plate(rr_profile(0.46, 0.12, 0.05), 0.03, (mx - 0.10, mf + 0.015, mz - 0.18), "r", rot=FACE, edge=0.01)


def icon_cache():
    """Short database cylinder (like icon_database, 2 disks) with a big cream lightning bolt on its front."""
    import bmesh
    R = 1.12
    for i, cz in enumerate((0.40, 1.24)):
        cyl(R, 0.64, (0, 0, cz), "p", 0.13)
        if i == 0:
            cyl(0.96, 0.24, (0, 0, 0.82), "s", 0.04)
    # big cream lightning bolt sliced along vertical cylinder rulings before wrapping (creases eliminated)
    bolt_pts = round_corners([
        (0.21, 0.66, 0.042),
        (-0.50, -0.05, 0.048),
        (-0.04, -0.05, 0.028),
        (-0.22, -0.66, 0.042),
        (0.50, 0.05, 0.048),
        (0.04, 0.05, 0.028),
    ], 12)
    bolt = plate(bolt_pts, 0.28, (0, 0, 0), "c", edge=0.042, clean=True)
    bm = bmesh.new()
    bm.from_mesh(bolt.data)
    for k in range(-18, 19):
        bmesh.ops.bisect_plane(
            bm,
            geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            plane_co=(k * 0.03, 0.0, 0.0),
            plane_no=(1.0, 0.0, 0.0),
        )
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    phi0 = D2R(35 - 90)
    cz_mid = 0.82
    for v in bm.verts:
        x2d, y2d, zloc = v.co.x, v.co.y, v.co.z
        phi = phi0 + x2d / (R + 0.04)
        rad = (R - 0.14) + zloc
        v.co = Vector((rad * math.cos(phi), rad * math.sin(phi), cz_mid + y2d))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(bolt.data)
    bm.free()
    smooth(bolt, 45)


def icon_queue():
    """Low red base with a cream channel/pipe on top holding three red rounded packets in a row."""
    # low red base + dark neck
    box((2.16, 1.32, 0.44), (0, 0, 0.22), "p", 0.14)
    for lx in (-0.18, 0.18):
        cyl(0.075, 0.06, (lx, -0.66 - 0.01, 0.22), "g", 0.022, rot=FACE)
    box((1.66, 0.84, 0.28), (0, 0, 0.50), "r", 0.06)
    # cream channel/pipe along X with bored ends and open front-top trough
    pz = 1.14
    pipe_cyl = cyl(0.62, 2.66, (0, 0, pz), "s", 0.09, rot=(0, D2R(90), 0))
    for sx in (-1, 1):
        cut(pipe_cyl, cyl(0.35, 0.65, (sx * 1.15, 0, pz), "s", 0, rot=(0, D2R(90), 0)))
    tilt = D2R(38)
    ny, nz = -math.sin(tilt), math.cos(tilt)
    cut(pipe_cyl, plate(rr_profile(1.98, 0.86, 0.24), 0.75, (0, ny * 0.20, pz + nz * 0.20), "r", rot=(tilt, 0, 0)))
    smooth(pipe_cyl)
    plate(rr_profile(2.00, 0.88, 0.24), 0.06, (0, ny * 0.18, pz + nz * 0.18), "r", rot=(tilt, 0, 0))
    # three red rounded packets in a row inside the channel
    for px in (-0.62, 0.0, 0.62):
        box((0.50, 0.56, 0.36), (px, ny * 0.39, pz + nz * 0.39), "p", 0.10, rot=(tilt, 0, 0))


def icon_bucket():
    """Red pail with cream rim and handle, two cream sheets sticking up out of it."""
    from mathutils import Matrix
    # tapered round red pail body (lathe) with dark interior floor
    prof = [
        (0.0, 0.0), (0.58, 0.0), (0.72, 0.02), (0.78, 0.12),
        (0.98, 1.40), (0.88, 1.40), (0.70, 0.90), (0.0, 0.90),
    ]
    pail = lathe(prof, "p", segs=96)
    smooth(pail, 65)
    cyl(0.81, 0.08, (0, 0, 1.24), "r", 0.02)
    # chunky cream rim around the mouth + side handle lugs
    rim_cyl = cyl(1.10, 0.28, (0, 0, 1.40), "s", 0.10)
    cut(rim_cyl, cyl(0.78, 0.70, (0, 0, 1.40), "r", 0))
    smooth(rim_cyl)
    for sx in (-1, 1):
        cyl(0.20, 0.16, (sx * 1.10, 0, 1.40), "s", 0.05, rot=(0, D2R(90), 0))
    # arched cream bail handle tilted slightly back so the sheets stand clear
    R_h = 1.10
    lean = D2R(22)
    h_pts = [
        (
            -R_h * math.cos(math.pi * k / 32),
            R_h * math.sin(math.pi * k / 32) * math.sin(lean),
            1.40 + R_h * math.sin(math.pi * k / 32) * math.cos(lean),
        )
        for k in range(33)
    ]
    tube(h_pts, 0.105, "s")
    # two cream sheets sticking up out of the pail
    s_back = box((0.82, 0.13, 0.98), (0.17, 0.12, 1.62), "s", 0.08)
    bpy.context.view_layer.update()
    s_back.matrix_world = (
        Matrix.Translation((0.17, 0.12, 1.62))
        @ Matrix.Rotation(D2R(-8), 4, "Y")
        @ Matrix.Translation((-0.17, -0.12, -1.62))
        @ s_back.matrix_world
    )
    fx, fy, fz = -0.16, -0.10, 1.56
    f_parts = [
        box((0.82, 0.13, 0.98), (fx, fy, fz), "c:dim", 0.08),
        box((0.48, 0.05, 0.085), (fx, fy - 0.06, fz + 0.24), "r", 0.035),
        box((0.36, 0.05, 0.085), (fx - 0.06, fy - 0.06, fz + 0.04), "r", 0.035),
    ]
    bpy.context.view_layer.update()
    M_f = Matrix.Translation((fx, fy, fz)) @ Matrix.Rotation(D2R(7), 4, "Y") @ Matrix.Translation((-fx, -fy, -fz))
    for o in f_parts:
        o.matrix_world = M_f @ o.matrix_world


# ---------------------------------------------------------------- IT diagram icons, part B (016)
def _caddy_ports(W, z_port):
    """Left and right cream bored pipe ports (±X), identical to icon_caddy."""
    for sx in (-1, 1):
        p_cyl = cyl(0.39, 0.88, (sx * (W / 2 + 0.20), 0.0, z_port), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.21, 0.80, (sx * (W / 2 + 0.46), 0.0, z_port), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)


def icon_api():
    """API: device box with side ports; navy screen with cream curly braces { }."""
    W, D, H = 1.92, 1.45, 1.82
    dev = Device(W, H, D, "p", screen=(0.20, 0.20, 0.20, 0.20), bevel=0.18)
    _caddy_ports(W, H / 2)
    x0 = 0.27
    top_arc = [(x0 - 0.05 + 0.10 * math.cos(D2R(a)), 0.33 + 0.10 * math.sin(D2R(a))) for a in range(90, -1, -15)]
    bot_arc = [(x0 - 0.05 + 0.10 * math.cos(D2R(a)), -0.33 + 0.10 * math.sin(D2R(a))) for a in range(0, -91, -15)]
    right_brace = [
        (x0 - 0.13, 0.43),
        *top_arc,
        (x0 + 0.05, 0.12),
        (x0 + 0.18, 0.0),
        (x0 + 0.05, -0.12),
        *bot_arc,
        (x0 - 0.13, -0.43),
    ]
    for sgn in (-1, 1):
        pts = [(sgn * x, z) for x, z in right_brace]
        plate(stroke_outline(pts, 0.145), 0.10, (dev.cx, dev.floor + 0.02, dev.cz), "g", rot=FACE, edge=0.032, clean=True)


def icon_webhook():
    """Webhook: chunky upright red J-hook (with its eyelet) catching a navy globe with cream continents and meridians."""
    from mathutils import Matrix
    R_eye, hw, r_f = 0.42, 0.19, 0.12
    x_sh, z_eye = -0.52, 1.94
    R_b = 0.74
    cx_b, cz_b = x_sh + R_b, 0.93  # straight shank meets bend tangentially at x_sh
    dz_f = math.sqrt((R_eye + r_f) ** 2 - (hw + r_f) ** 2)
    alpha = math.asin((hw + r_f) / (R_eye + r_f))
    # G1-smooth CCW contour: right neck fillet -> top eye arc -> left neck fillet -> outer J-bend -> tip -> inner J-bend
    r_neck = [
        (x_sh + (hw + r_f) + r_f * math.cos(math.pi - (math.pi / 2 - alpha) * k / 10),
         z_eye - dz_f + r_f * math.sin(math.pi - (math.pi / 2 - alpha) * k / 10))
        for k in range(11)
    ]
    a0, a1 = -math.pi / 2 + alpha, 1.5 * math.pi - alpha
    eye_arc = [
        (x_sh + R_eye * math.cos(a0 + (a1 - a0) * k / 44),
         z_eye + R_eye * math.sin(a0 + (a1 - a0) * k / 44))
        for k in range(1, 44)
    ]
    l_neck = [
        (x_sh - (hw + r_f) + r_f * math.cos((math.pi / 2 - alpha) * (1 - k / 10)),
         z_eye - dz_f + r_f * math.sin((math.pi / 2 - alpha) * (1 - k / 10)))
        for k in range(11)
    ]
    n_b, n_cap = 48, 16
    b0, b1 = D2R(180), D2R(378)
    ro, ri = R_b + hw, R_b - hw
    outer_bend = [(cx_b + ro * math.cos(b0 + (b1 - b0) * k / n_b), cz_b + ro * math.sin(b0 + (b1 - b0) * k / n_b)) for k in range(n_b + 1)]
    tip_c = (cx_b + R_b * math.cos(b1), cz_b + R_b * math.sin(b1))
    tip_cap = [(tip_c[0] + hw * math.cos(b1 + math.pi * k / n_cap), tip_c[1] + hw * math.sin(b1 + math.pi * k / n_cap)) for k in range(1, n_cap)]
    inner_bend = [(cx_b + ri * math.cos(b1 - (b1 - b0) * k / n_b), cz_b + ri * math.sin(b1 - (b1 - b0) * k / n_b)) for k in range(n_b + 1)]
    prof = r_neck + eye_arc + l_neck + outer_bend + tip_cap + inner_bend
    D = 0.46
    hook = plate(prof, D, (0, D / 2, 0), "p", rot=FACE, edge=0.08, clean=True)
    cut(hook, cyl(0.16, D * 3.0, (x_sh, 0, z_eye), "p", 0, rot=FACE))
    smooth(hook)
    # Mini globe caught snugly in the hook's curve: navy ocean (r) + cream continents & meridian/equator lines (c:dim)
    c = Vector((cx_b - 0.01, -0.04, cz_b + 0.05))
    R = 0.515
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, location=tuple(c), segments=96, ring_count=48)
    sphere = finish(bpy.context.object, "r")
    lands, _ = land_shell(c, R, role="c:dim", lift=0.002, thick=0.022, segs=360, rings=180)
    grid = [
        torus(R - 0.007, 0.026, tuple(c), "c:dim"),
        torus(R - 0.007, 0.026, tuple(c), "c:dim", rot=(D2R(90), 0, D2R(-30))),
        torus(R - 0.007, 0.026, tuple(c), "c:dim", rot=(D2R(90), 0, D2R(30))),
    ]
    az = D2R(ICON_AZIMUTH.get(CURRENT or "webhook", AZIMUTH))
    cam = Matrix.Rotation(az, 3, "Z") @ Matrix.Rotation(D2R(60), 3, "X")
    to_cam = -(cam @ Vector((0, 0, -1)))
    up = cam @ Vector((0, 1, 0))
    aim = geo(-8, 28)
    north = Vector((0, 0, 1))
    n_src = (north - aim * north.dot(aim)).normalized()
    src = Matrix((aim, n_src, aim.cross(n_src))).transposed()
    n_dst = (up - to_cam * up.dot(to_cam)).normalized()
    dst = Matrix((to_cam, n_dst, to_cam.cross(n_dst))).transposed()
    Rm = (dst @ src.transposed()).to_4x4()
    M = Matrix.Translation(c) @ Rm @ Matrix.Translation(-c)
    bpy.context.view_layer.update()
    for o in [sphere] + lands + grid:
        o.matrix_world = M @ o.matrix_world


def icon_loadbalancer():
    """Load balancer: device box with ONE cream port on the left and THREE cream ports fanning out on the right."""
    W, D, H = 1.88, 1.48, 1.96
    cz = H / 2
    dev = Device(W, H, D, "p", screen=(0.20, 0.20, 0.20, 0.20), bevel=0.18)
    # ONE cream port on the left (-X), same construction as icon_caddy
    p_left = cyl(0.39, 0.88, (-W / 2 - 0.20, 0.0, cz), "s", 0.08, rot=(0, D2R(90), 0))
    cut(p_left, cyl(0.21, 0.80, (-W / 2 - 0.46, 0.0, cz), "s", 0, rot=(0, D2R(90), 0)))
    smooth(p_left)
    # THREE cream ports fanning out on the right (+X)
    for dz0, tilt_deg in ((0.33, -31), (0.0, 0), (-0.33, 31)):
        ang = D2R(90 + tilt_deg)
        dx_u, dz_u = math.sin(ang), math.cos(ang)
        ax, az = W / 2 - 0.06, cz + dz0
        p_r = cyl(0.24, 0.88, (ax + 0.34 * dx_u, 0.0, az + 0.34 * dz_u), "s", 0.055, rot=(0, ang, 0))
        cut(p_r, cyl(0.13, 0.80, (ax + 0.60 * dx_u, 0.0, az + 0.60 * dz_u), "s", 0, rot=(0, ang, 0)))
        smooth(p_r)
    # 1-to-3 split glyph on the navy screen
    emboss(dev, [(-0.34, 0.0), (-0.06, 0.0)], 0.12, "g", depth=0.10)
    for vz in (0.29, 0.0, -0.29):
        emboss(dev, [(-0.06, 0.0), (0.26, vz)], 0.11, "g", depth=0.10)
        dot(dev, 0.31, vz, r=0.09, role="g")
    dot(dev, -0.35, 0.0, r=0.09, role="g")


def icon_switch():
    """Network switch: low wide box, front = row of 8 small navy square ports with tiny g lights; side ports."""
    W, D, H = 2.54, 1.48, 1.02
    cz = H / 2
    body = box((W, D, H), (0, 0, cz), "p", 0.17)
    for sx in (-1, 1):
        p_cyl = cyl(0.37, 0.88, (sx * (W / 2 + 0.20), 0.0, cz), "s", 0.08, rot=(0, D2R(90), 0))
        cut(p_cyl, cyl(0.20, 0.80, (sx * (W / 2 + 0.46), 0.0, cz), "s", 0, rot=(0, D2R(90), 0)))
        smooth(p_cyl)
    face = -D / 2
    # shallow recessed front tray holding the 8-port bank
    tray = rr_profile(2.22, 0.66, 0.11)
    cut(body, plate(tray, 0.24, (0, face + 0.055, cz), "p", rot=FACE))
    smooth(body)
    pf = face + 0.055
    for i in range(8):
        px = (i - 3.5) * 0.258
        plate(rr_profile(0.195, 0.22, 0.03), 0.045, (px, pf + 0.01, cz - 0.09), "r", rot=FACE, edge=0.008)
        plate(rr_profile(0.09, 0.065, 0.015), 0.045, (px, pf + 0.01, cz + 0.02), "r", rot=FACE, edge=0.005)
        cyl(0.044, 0.045, (px, pf - 0.015, cz + 0.165), "g", 0.015, rot=FACE)


def icon_cicd():
    """CI/CD: thick upright red infinity loop standing facing -Y (like icon_sync) with a clear cream
    arrow head on the left lobe and a smaller second cream arrow head on the right lobe."""
    cz = 1.12
    phi = D2R(50)
    R = 0.68
    cx = R / math.sin(phi)
    xt = R * (math.cos(phi) ** 2) / math.sin(phi)
    zt = R * math.cos(phi)
    y_step = 0.085
    n_lobe, n_br = 72, 36
    pts = []
    # Left lobe CW: 320° -> 270° -> 180° -> 90° -> 40°
    for k in range(n_lobe):
        a = D2R(320.0 - 280.0 * k / n_lobe)
        pts.append((-cx + R * math.cos(a), 0.0, cz + R * math.sin(a)))
    # Front over-bridge (\): (-xt, cz + zt) -> (+xt, cz - zt), stepping forward toward -Y
    for k in range(n_br):
        u = k / n_br
        s = 2.0 * u - 1.0
        pts.append((-xt + 2.0 * xt * u, -y_step * 0.5 * (1.0 + math.cos(math.pi * s)), cz + zt - 2.0 * zt * u))
    # Right lobe CCW: -140° -> -90° -> 0° -> +90° -> +140°
    for k in range(n_lobe):
        a = D2R(-140.0 + 280.0 * k / n_lobe)
        pts.append((cx + R * math.cos(a), 0.0, cz + R * math.sin(a)))
    # Back under-bridge (/): (+xt, cz + zt) -> (-xt, cz - zt), stepping back toward +Y
    for k in range(n_br):
        u = k / n_br
        s = 2.0 * u - 1.0
        pts.append((xt - 2.0 * xt * u, y_step * 0.5 * (1.0 + math.cos(math.pi * s)), cz + zt - 2.0 * zt * u))

    # Upright flat-faced rounded-rectangle cross-section (width w in XZ, depth D along Y, bevel rb)
    w, D, rb, nc, g = 0.36, 0.46, 0.08, 8, 0.008
    hw, hd = w / 2, D / 2
    sec = [(-hw + rb + g, -hd), (hw - rb - g, -hd)]
    for k in range(nc + 1):
        a = D2R(-90.0 + 90.0 * k / nc)
        sec.append((hw - rb + rb * math.cos(a), -hd + rb + rb * math.sin(a)))
    sec += [(hw, -hd + rb + g), (hw, hd - rb - g)]
    for k in range(nc + 1):
        a = D2R(0.0 + 90.0 * k / nc)
        sec.append((hw - rb + rb * math.cos(a), hd - rb + rb * math.sin(a)))
    sec += [(hw - rb - g, hd), (-hw + rb + g, hd)]
    for k in range(nc + 1):
        a = D2R(90.0 + 90.0 * k / nc)
        sec.append((-hw + rb + rb * math.cos(a), hd - rb + rb * math.sin(a)))
    sec += [(-hw, hd - rb - g), (-hw, -hd + rb + g)]
    for k in range(nc + 1):
        a = D2R(180.0 + 90.0 * k / nc)
        sec.append((-hw + rb + rb * math.cos(a), -hd + rb + rb * math.sin(a)))

    N, M = len(pts), len(sec)
    verts, faces = [], []
    for i in range(N):
        p0, p, p1 = pts[(i - 1) % N], pts[i], pts[(i + 1) % N]
        dx, dz = p1[0] - p0[0], p1[2] - p0[2]
        L = math.hypot(dx, dz)
        ux, uz = -dz / L, dx / L
        for su, sv in sec:
            verts.append((p[0] + su * ux, p[1] + sv, p[2] + su * uz))
    for i in range(N):
        i1 = (i + 1) % N
        for j in range(M):
            j1 = (j + 1) % M
            faces.append([i * M + j, i1 * M + j, i1 * M + j1, i * M + j1])
    me = bpy.data.meshes.new("cicd_loop")
    me.from_pydata(verts, [], faces)
    me.update()
    loop_obj = bpy.data.objects.new("cicd_loop", me)
    bpy.context.collection.objects.link(loop_obj)
    finish(loop_obj, "p")

    def _qpoly(pts_r, n=12):
        out, m = [], len(pts_r)
        for i in range(m):
            ax, ay, _ = pts_r[(i - 1) % m]
            bx, by, r = pts_r[i]
            cx_p, cy_p, _ = pts_r[(i + 1) % m]
            A, B, C = Vector((ax, ay)), Vector((bx, by)), Vector((cx_p, cy_p))
            u1, u2 = (A - B).normalized(), (C - B).normalized()
            half = math.acos(max(-1.0, min(1.0, u1.dot(u2)))) / 2
            d = min(r / math.tan(half), (A - B).length * 0.44, (C - B).length * 0.44)
            T1, T2 = B + u1 * d, B + u2 * d
            for k in range(n + 1):
                t = k / n
                p = T1 * ((1 - t) ** 2) + B * (2 * (1 - t) * t) + T2 * (t ** 2)
                out.append((p.x, p.y))
        return out

    def _lobe_arrow(cx_l, a_deg, sgn, scale, hw_arr, y_front, depth, edge):
        ar = D2R(a_deg)
        px, pz = cx_l + R * math.cos(ar), cz + R * math.sin(ar)
        rx, rz = math.cos(ar), math.sin(ar)
        tx, tz = -sgn * math.sin(ar), sgn * math.cos(ar)
        raw = [
            (0.49 * scale, 0.0, 0.075 * scale),
            (-0.24 * scale, hw_arr, 0.068 * scale),
            (-0.09 * scale, 0.0, 0.045 * scale),
            (-0.24 * scale, -hw_arr, 0.068 * scale),
        ]
        prof = _qpoly([(px + t * tx + r * rx, pz + t * tz + r * rz, rad) for t, r, rad in raw], 12)
        plate(prof, depth, (0, y_front + depth, 0), "c:dim", rot=FACE, edge=edge, clean=True)

    # Clear primary cream arrow head on left lobe (CW -> into front bridge) + smaller second on right lobe (CCW)
    _lobe_arrow(-cx, 82.0, -1, 1.00, 0.305, -0.32, 0.24, 0.048)
    _lobe_arrow(cx, -48.0, 1, 0.72, 0.240, -0.31, 0.23, 0.040)


def icon_monitoring():
    """Monitoring: device box with side ports; navy screen with a cream rising zig-zag pulse line."""
    W, D, H = 1.92, 1.45, 1.82
    dev = Device(W, H, D, "p", screen=(0.20, 0.20, 0.20, 0.20), bevel=0.18)
    _caddy_ports(W, H / 2)
    emboss(dev, [(-0.37, -0.26), (-0.13, 0.06), (0.05, -0.15), (0.36, 0.27)], 0.145, "g", depth=0.11)


def icon_logs():
    """Logs: upright paper scroll, red roll ends, cream sheet with short navy lines."""
    W_s = 1.46
    yc, zc, R_roll = 0.12, 1.84, 0.34
    # top rolled paper cylinder + hanging upright sheet with forward bottom curl
    cyl(R_roll, W_s + 0.06, (0, yc, zc), "c:dim", 0.04, rot=(0, D2R(90), 0))
    curl = [(-0.42 + 0.30 * math.cos(D2R(a)), 0.58 + 0.30 * math.sin(D2R(a))) for a in range(0, -116, -8)]
    sheet_yz = [(0.04, 1.90), (-0.12, zc), (-0.12, 0.58), *curl[1:]]
    plate(stroke_outline(sheet_yz, 0.20, n=16), W_s, (-W_s / 2, 0.0, 0.0), "c:dim",
          rot=(D2R(90), 0, D2R(90)), edge=0.055, clean=True)
    # chunky red roll ends on left and right of top scroll
    for sx in (-1, 1):
        rcap = cyl(0.47, 0.34, (sx * (W_s / 2 + 0.13), yc, zc), "p", 0.09, rot=(0, D2R(90), 0))
        cut(rcap, cyl(0.22, 0.30, (sx * (W_s / 2 + 0.24), yc, zc), "p", 0, rot=(0, D2R(90), 0)))
        smooth(rcap)
    # short navy log lines on the upright front face (y = -0.22)
    y_face = -0.22
    for rz, x_end in ((1.40, 0.50), (1.14, 0.32), (0.88, 0.46), (0.62, 0.18)):
        plate(stroke_outline([(-0.50, rz), (-0.28, rz)], 0.115), 0.055, (0, y_face + 0.02, 0), "r", rot=FACE, edge=0.018, clean=True)
        plate(stroke_outline([(-0.12, rz), (x_end, rz)], 0.115), 0.055, (0, y_face + 0.02, 0), "r", rot=FACE, edge=0.018, clean=True)


def icon_bell():
    """Bell: classic chunky red bell (dome + flared rim) with a cream clapper ball and a small cream dot badge."""
    ctrl = [
        (0.0, 2.36),
        (0.28, 2.33),
        (0.55, 2.17),
        (0.70, 1.88),
        (0.76, 1.50),
        (0.83, 1.16),
        (0.99, 0.92),
        (1.10, 0.78),
        (1.08, 0.69),
        (0.95, 0.67),
        (0.82, 0.74),
        (0.70, 0.86),
        (0.0, 0.86),
    ]
    P = [ctrl[0]] + ctrl + [ctrl[-1]]
    prof = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(8):
            t = k / 8
            r = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t * t + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t ** 3)
            z = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t * t + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t ** 3)
            prof.append((max(0.0, r), z))
    prof.append((0.0, ctrl[-1][1]))
    prof[0] = (0.0, prof[0][1])
    bell = lathe(prof, "p", segs=128)
    smooth(bell, 70)
    # classic top hanging loop in red
    torus(0.16, 0.08, (0, 0, 2.44), "p", rot=FACE)
    # dark hollow interior + plump cream clapper ball (role g so under-rim shade reads warm cream, not grey)
    cyl(0.80, 0.06, (0, 0, 0.76), "r", 0.01)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0.17, -0.25, 0.35), segments=48, ring_count=24)
    finish(bpy.context.object, "g")
    # small cream notification dot badge breaking the upper-right silhouette contour
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(0.59, 0.24, 2.04), segments=48, ring_count=24)
    finish(bpy.context.object, "s")


def icon_search():
    """Search: chunky magnifying glass, red ring and handle, cream glass."""
    cx, cz, D = -0.34, 1.48, 0.46
    ro, ri = 0.94, 0.60
    n = 72
    outer = [(ro * math.cos(2 * math.pi * k / n), ro * math.sin(2 * math.pi * k / n)) for k in range(n)]
    inner = [(ri * math.cos(2 * math.pi * k / n), ri * math.sin(2 * math.pi * k / n)) for k in range(n)]
    _quad_ring_solid(outer, inner, (cx, D / 2, cz), D, "p", bev=0.095, rot=FACE)
    # convex cream glass lens
    ellipsoid((cx, 0.0, cz), (0.63, 0.16, 0.63), "c:dim", segs=64)
    # chunky red neck + handle along -45° in XZ
    ux, uz = math.cos(D2R(-45)), math.sin(D2R(-45))
    cyl(0.165, 0.34, (cx + 0.98 * ux, 0.0, cz + 0.98 * uz), "p", 0.04, rot=(0, D2R(135), 0))
    cyl(0.26, 0.88, (cx + 1.48 * ux, 0.0, cz + 1.48 * uz), "p", 0.11, rot=(0, D2R(135), 0))


def icon_trash():
    """Trash: red rounded bin, cream lid, three vertical cream grooves."""
    from mathutils import Matrix
    prof = [
        (0.0, 0.0), (0.60, 0.0), (0.74, 0.03), (0.79, 0.16),
        (0.89, 1.54), (0.80, 1.58), (0.0, 1.58),
    ]
    bin_body = lathe(prof, "p", segs=96)
    smooth(bin_body, 65)
    cyl(0.84, 0.10, (0, 0, 1.58), "r", 0.02)
    # overhanging chunky cream lid + top handle loop
    cyl(1.03, 0.28, (0, 0, 1.74), "c:dim", 0.11)
    h_pts = [(-0.27, 0, 1.82), (-0.27, 0, 1.97)] + [(-0.27 * math.cos(math.pi * k / 16), 0, 1.97 + 0.12 * math.sin(math.pi * k / 16)) for k in range(1, 16)] + [(0.27, 0, 1.97), (0.27, 0, 1.82)]
    tube(h_pts, 0.085, "s")
    # three vertical cream grooves along the -Y front of the tapered bin
    taper = math.atan2(0.89 - 0.79, 1.54 - 0.16)
    r_mid, cz_g = 0.84, 0.84
    for a_deg in (-26, 0, 26):
        g = box((0.185, 0.11, 0.92), (0, 0, 0), "c", 0.08)
        bpy.context.view_layer.update()
        g.matrix_world = Matrix.Rotation(D2R(a_deg), 4, "Z") @ Matrix.Translation((0, -(r_mid + 0.01), cz_g)) @ Matrix.Rotation(taper, 4, "X")


ICONS = {
    "calib": icon_calib,
    "notetaker": icon_notetaker,
    "notetaker-b": icon_notetaker_b,
    "notetaker-c": icon_notetaker_c,
    "notetaker-d": icon_notetaker_d,
    "link": icon_link,
    "social": icon_social,
    "ai-a": icon_ai_a,
    "relay": icon_relay,
    "cli": icon_cli,
    "lock": icon_lock,
    "record": icon_record,
    "transcribe": icon_transcribe,
    "minutes": icon_minutes,
    "report": icon_report,
    "mcp-a": icon_mcp_a,
    "phone": icon_phone,
    "globe": icon_globe,
    "browser": icon_browser,
    "config": icon_config,
    "check": icon_check,
    "meet": icon_meet,
    "chat": icon_chat,
    "call": icon_call,
    "files": icon_files,
    "page": icon_page,
    "warning": icon_warning,
    "error": icon_error,
    "info": icon_info,
    "pending": icon_pending,
    "server": icon_server,
    "database": icon_database,
    "team": icon_team,
    "github": icon_github,
    "os-windows": icon_os_windows,
    "os-macos": icon_os_macos,
    "os-linux": icon_os_linux,
    "os-android": icon_os_android,
    "os-ios": icon_os_ios,
    "apple": icon_apple,
    "docker": icon_docker,
    "nas": icon_nas,
    "raspberrypi": icon_raspberrypi,
    "desktop": icon_desktop,
    "tablet": icon_tablet,
    "browser-ext": icon_browser_ext,
    "vscode": icon_vscode,
    "mail": icon_mail,
    "calendar": icon_calendar,
    "qr-pair": icon_qr_pair,
    "bluetooth": icon_bluetooth,
    "wifi": icon_wifi,
    "license": icon_license,
    "payment": icon_payment,
    "upload": icon_upload,
    "download": icon_download,
    "sync": icon_sync,
    "backup": icon_backup,
    "voice-profile": icon_voice_profile,
    "video": icon_video,
    "router": icon_router,
    "modem": icon_modem,
    "caddy": icon_caddy,
    "certstore": icon_certstore,
    "dns": icon_dns,
    "user": icon_user,
    "key": icon_key,
    "shield": icon_shield,
    "firewall": icon_firewall,
    "cloud": icon_cloud,
    "container": icon_container,
    "cluster": icon_cluster,
    "vm": icon_vm,
    "cache": icon_cache,
    "queue": icon_queue,
    "bucket": icon_bucket,
    "api": icon_api,
    "webhook": icon_webhook,
    "loadbalancer": icon_loadbalancer,
    "switch": icon_switch,
    "cicd": icon_cicd,
    "monitoring": icon_monitoring,
    "logs": icon_logs,
    "bell": icon_bell,
    "search": icon_search,
    "trash": icon_trash,
}


# ---------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == kind
                s.cycles.device = "GPU"
                break
        except TypeError:
            continue
    s.cycles.samples = SAMPLES
    s.cycles.use_denoising = True
    s.cycles.seed = 7
    s.render.film_transparent = True
    s.render.resolution_x = s.render.resolution_y = 2048  # supersampled; normalize scales to 1024 (sharp edges)
    s.view_settings.view_transform = "Standard"  # brand hex in, brand hex out
    s.view_settings.look = "None"
    s.view_settings.exposure = -0.15  # headroom; cream gets its own albedo calibration (CREAM_ALBEDO)
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.88, 0.85, 1)  # near-neutral fill: cream stays cream, no pink cast
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = WORLD
    s.world = w


def light_and_camera():
    s = bpy.context.scene
    from mathutils import Matrix
    cam_az = ICON_AZIMUTH.get(CURRENT, AZIMUTH)
    # the light rig turns with the camera (same look for every icon), plus a per-icon turn
    # when the approved pose puts the hero face on the usual shadow side (relay: screen right)
    rig = Matrix.Rotation(D2R(cam_az - 35 + ICON_KEY_TURN.get(CURRENT, 0)), 3, "Z")
    # key: big soft area from the top-left of the frame
    # lower and more frontal than before: top ≈ brand hex, front ≈ 85%, right side ≈ 55%
    bpy.ops.object.light_add(type="AREA", location=rig @ Vector((-2.5, -5.5, 6.0)))
    key = bpy.context.object
    key.data.energy = KEY
    key.data.color = (1.0, 0.95, 0.88)
    key.data.size = 4.5
    key.rotation_euler = (Vector((0, 0, 0.8)) - key.location).to_track_quat("-Z", "Y").to_euler()
    # rim from the back right so cream edges separate from navy
    bpy.ops.object.light_add(type="AREA", location=rig @ Vector((-3, 5, 4)))  # behind-left: lifts top edges
    rim = bpy.context.object
    rim.data.energy = 65
    rim.data.size = 3.5
    rim.data.color = (1.0, 0.88, 0.78)
    rim.rotation_euler = (Vector((0, 0, 0.8)) - rim.location).to_track_quat("-Z", "Y").to_euler()
    # strict orthographic isometric: 30° above horizontal, front face to the bottom-left
    # 30° above horizontal; turned 30° (not 45°) so the front face leads, like the approved AI set
    bpy.ops.object.camera_add(rotation=(D2R(60), 0, D2R(ICON_AZIMUTH.get(CURRENT, AZIMUTH))))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    s.camera = cam
    objs = [o for o in s.objects if o.type in ("MESH", "FONT", "CURVE") and not o.hide_render]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.view3d.camera_to_view_selected() if False else None
    # frame: bounding box centre, generous margin (normalize recentres anyway)
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    centre = sum(pts, Vector()) / len(pts)
    d = cam.matrix_world.to_3x3() @ Vector((0, 0, 1))
    cam.location = centre + d * 20
    right = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
    up = cam.matrix_world.to_3x3() @ Vector((0, 1, 0))
    ext = max(max(abs((p - centre).dot(right)), abs((p - centre).dot(up))) for p in pts)
    cam.data.ortho_scale = ext * 2 * 1.25


def main():
    names = NAMES or list(ICONS)
    modes = ["dark", "light"] if MODE == "both" else [MODE]
    global CURRENT
    for name in names:
        CURRENT = name
        reset()
        ICONS[name]()
        light_and_camera()
        for mode in modes:
            paint(mode)
            bpy.context.scene.render.filepath = f"{OUT}/{mode}/{name}.png"
            try:
                bpy.ops.render.render(write_still=True)
            except RuntimeError as e:  # GPU busy (other jobs hold VRAM): same image on CPU, just slower
                print(f"gpu failed ({e}); rendering on CPU")
                # scene.cycles.device alone still opens the CUDA context (and fails again):
                # switch the compute backend off too
                bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "NONE"
                bpy.context.scene.cycles.device = "CPU"
                bpy.ops.render.render(write_still=True)
            print(f"ok   {mode}/{name}")


# `blender -P build.py` runs main(); other scripts (diagram.py, kit modules) import the helpers.
if __name__ == "__main__" and not globals().get("VIA_IMPORT_ONLY"):
    main()
