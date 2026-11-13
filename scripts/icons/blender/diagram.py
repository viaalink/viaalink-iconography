"""
2.5D flow diagrams: our Blender icons (and dolls) as nodes on a board, linked by pipes that
are routed by script, so a diagram always comes out tidy.

  blender -b --factory-startup -P scripts/icons/blender/diagram.py -- \
      --spec scripts/icons/blender/diagrams/relay-solo.json --out local/icons/diagrams/relay-solo \
      [--mode dark|light|both] [--samples 64]
  (or: just icons-diagram relay-solo)

Spec (JSON):
  {"nodes": [{"id": "dev", "doll": "developer", "at": [0, 0], "label": "You"},
             {"id": "cli", "icon": "cli", "at": [1, 0], "label": "via up"}],
   "edges": [["dev", "cli"], ["cli", "relay", {"label": "tunnel"}]]}
`at` is [column, row] on a screen-aligned grid: columns run left→right, rows top→bottom, so a
diagram reads like a flowchart. Edges are pipes: they leave a node on the side facing the
other node, run straight or as a Z with rounded bends, and carry two packets plus an arrow
cone toward the target. Same model + palette swap for light and dark, like the icons.
"""
import json
import math
import os
import runpy
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
B = runpy.run_path(os.path.join(HERE, "build.py"), init_globals={"VIA_IMPORT_ONLY": True}, run_name="via_build")

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def opt(k, d):
    if f"--{k}" in argv:
        i = argv.index(f"--{k}")
        return argv[i + 1]
    return d


SPEC = opt("spec", "")
OUT = opt("out", "local/icons/diagrams/tmp")
MODE = opt("mode", "both")
SAMPLES = int(opt("samples", "64"))
GRID = 3.7  # world units between grid cells
FOOT = 1.45  # max node footprint (icons are normalised to this)
PIPE_Z = 0.3  # pipe centre height above the board
PIPE_R = 0.09
AZ = math.radians(B["AZIMUTH"])
RIGHT = Vector((math.cos(AZ), math.sin(AZ), 0))  # screen right, on the ground
AWAY = Vector((-math.sin(AZ), math.cos(AZ), 0))  # screen up, on the ground
NODE_TURN = {"relay": 0}  # relay ports are now on ±X like icon_caddy
# Devices built with two cream side ports on ±X (owner 2026-11-12: "2 ports, plus sockets in the diagram").
# A pipe that meets such a device from a side WITHOUT a port gets a matching socket there, so a hub with
# four pipes shows four ports and an icon on its own keeps its clean two-port silhouette.
DEVICE_PORTS = {"relay", "caddy", "firewall", "vm", "api", "monitoring", "switch", "modem", "router",
                "server", "nas", "certstore", "dns"}


def socket_for(node, end, out):
    """A cream port where a pipe meets `node` from a side its own ports don't cover. `end` is the pipe's
    end point at the node, `out` the unit direction from the node along the pipe."""
    if node.get("icon") not in DEVICE_PORTS:
        return None
    turn = math.radians(node.get("turn", NODE_TURN.get(node.get("icon", ""), 0)))
    axis = Vector((math.cos(turn), math.sin(turn), 0))  # the model's own ports run along its local X
    flat = Vector((out.x, out.y, 0))
    if flat.length < 1e-6 or abs(flat.normalized().dot(axis)) > 0.5:
        return None  # the pipe runs along the device's own ports: those already take it
    k = node.get("scale", 1.0)
    c = B["cyl"](PIPE_R * 1.8 * k, 0.26 * k, tuple(end + out * 0.08 * k), "s", 0.04, verts=48)
    c.rotation_euler = out.to_track_quat("Z", "Y").to_euler()
    return c
# Layout frame: "iso" (default) runs columns along world +X (down-right on screen) and rows along
# world -Y (down-left), like the desk scenes; "screen" makes rows horizontal on screen.
U, V = Vector((1, 0, 0)), Vector((0, -1, 0))


def set_layout(kind):
    global U, V
    U, V = (RIGHT, -AWAY) if kind == "screen" else (Vector((1, 0, 0)), Vector((0, -1, 0)))

D2R = math.radians
DOLLS = None


def dolls():
    global DOLLS
    if DOLLS is None:
        DOLLS = runpy.run_path(os.path.join(HERE, "kit_dolls.py"), init_globals={"B": B}, run_name="via_kit")
    return DOLLS


def grid_point(col, row):
    return U * (col * GRID) + V * (row * GRID)


def renderable(objs):
    return [o for o in objs if o.type in ("MESH", "FONT", "CURVE") and not o.hide_render]


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in renderable(objs) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def screen_extent(objs):
    """Extent of a node in the screen-aligned ground frame (u = right, w = away)."""
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in renderable(objs) for c in o.bound_box]
    us = [p.dot(U) for p in pts]
    ws = [p.dot(V) for p in pts]
    return min(us), max(us), min(ws), max(ws)


def place_node(n):
    """Build one icon/doll, normalise its size, and put it on its grid cell."""
    before = set(bpy.data.objects)
    B["FROZEN"].clear()
    B["FROZEN"].update(o.name for o in before)
    if n.get("hub"):  # a plain pipe junction (a tee in the pipe), not a device (agy diagrams r5)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=PIPE_R * 2.1, location=(0, 0, PIPE_Z), segments=32, ring_count=16)
        B["finish"](bpy.context.object, "p")
        B["cyl"](PIPE_R * 0.9, PIPE_Z, (0, 0, PIPE_Z / 2), "p", 0.01, verts=24)  # short stem to the board
    elif n.get("glyph") == "desktop":  # Viaalink desktop (Notetaker app): the cli laptop body with the
        # canonical app screen (logo on top, transcript lines) instead of the `> via` prompt
        box, plate, D2R_ = B["box"], B["plate"], math.radians
        box((2.6, 1.75, 0.34), (0, -0.6, 0.17), "p", 0.12)
        for y in (-0.42, -0.86):
            for i in range(4):
                box((0.48, 0.36, 0.14), (-0.84 + i * 0.56, y, 0.39), "c", 0.06)
        box((2.16, 0.3, 0.14), (0.0, -1.28, 0.39), "c", 0.06)
        tilt = D2R_(-6)
        hinge = Vector((0, 0.2, 0.22))
        Rm = __import__("mathutils").Euler((tilt, 0, 0)).to_matrix()
        on_lid = lambda x, y, z: hinge + Rm @ Vector((x, y, z))
        rot = (D2R_(90) + tilt, 0, 0)
        box((2.6, 0.3, 1.95), on_lid(0, 0, 0.98), "p", 0.12, rot=(tilt, 0, 0))
        plate(B["rr_profile"](2.2, 1.55, 0.14), 0.02, on_lid(0, -0.15, 1.0), "r", rot=rot)
        B["logo"](0.62, on_lid(0, -0.17, 1.42), "g", 0.03, rot=rot)
        for k, w in enumerate((1.5, 1.5, 1.05)):
            box((w, 0.03, 0.12), on_lid(-0.75 + w / 2, -0.17, 1.02 - k * 0.24), "g", 0.03, rot=(tilt, 0, 0))
    elif n.get("glyph") == "key":  # a key standing on a small base: "login", where a lock reads as encryption
        B["cyl"](0.5, 0.62, (0, 0, 0.31), "s", 0.08, verts=64)  # plinth: the pipe enters it, not the key
        B["torus"](0.3, 0.1, (0, 0, 1.75), "p", rot=(math.radians(90), 0, 0))
        B["box"]((0.16, 0.16, 0.9), (0, 0, 1.08), "p", 0.04)
        B["box"]((0.24, 0.14, 0.12), (0.17, 0, 0.82), "p", 0.03)
        B["box"]((0.18, 0.14, 0.12), (0.14, 0, 1.05), "p", 0.03)
    elif "doll" in n:
        dolls()["doll"](n["doll"])
    else:
        B["CURRENT"] = n["icon"]
        B["ICONS"][n["icon"]]()
    objs = [o for o in bpy.data.objects if o not in before]
    for o in objs:  # owner: animated later — every node stays its own named set of objects
        o.name = f"{n['id']}.{o.name}"
    lo, hi = bounds(objs)
    size = max(hi.x - lo.x, hi.y - lo.y, (hi.z - lo.z) * 0.8)  # tall icons count by height too
    k = n.get("scale", 1.0) * (FOOT / size if "icon" in n else 1.0)
    if n.get("hub"):
        k = 1.0
    if n.get("glyph"):
        k = n.get("scale", 1.0) * FOOT / size
    centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    target = grid_point(*n["at"])
    turn = n.get("turn", NODE_TURN.get(n.get("icon", ""), 0))
    M = Matrix.Translation(target) @ Matrix.Rotation(D2R(turn), 4, "Z") @ Matrix.Scale(k, 4) @ Matrix.Translation(-centre)
    for o in objs:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world
    return objs


def fillet(pts, rad=0.45, steps=8):
    """Round every interior corner of a polyline (pipes bend, they don't kink)."""
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        d1, d2 = (b - a), (c - b)
        if d1.length < 1e-6 or d2.length < 1e-6 or d1.normalized().dot(d2.normalized()) > 0.999:
            out.append(b)
            continue
        r = min(rad, d1.length / 2, d2.length / 2)
        p1, p2 = b - d1.normalized() * r, b + d2.normalized() * r
        for i in range(steps + 1):  # quadratic Bezier through the corner
            t = i / steps
            out.append(p1 * (1 - t) ** 2 + b * 2 * t * (1 - t) + p2 * t * t)
    out.append(pts[-1])
    return out


def along(pts, f):
    """Point and direction at fraction f of a polyline's length."""
    segs = [(a, b, (b - a).length) for a, b in zip(pts, pts[1:])]
    total = sum(s[2] for s in segs)
    d = f * total
    for a, b, L in segs:
        if d <= L:
            return a + (b - a) * (d / L), (b - a).normalized()
        d -= L
    a, b, _ = segs[-1]
    return b, (b - a).normalized()


CAM = Matrix.Rotation(AZ, 3, "Z") @ Matrix.Rotation(math.radians(60), 3, "X")  # same as build.py camera
CR, CU = CAM @ Vector((1, 0, 0)), CAM @ Vector((0, 1, 0))  # screen right / screen up in world space


def arc_pts(c, u, w, R):
    return [c + u * (R * math.cos(math.radians(-50 + 100 * k / 12))) + w * (R * math.sin(math.radians(-50 + 100 * k / 12))) for k in range(13)]


def waves(at, d, role="c", z=1.15, radii=(0.22, 0.38, 0.54), clear=None):
    """Three ')))' arcs at `at` in the SCREEN plane, aimed at the target as seen on screen
    (agy rounds 4–5: arcs in the ground plane read edge-on/backward, fixed ones pointed nowhere).
    clear = (mouth, body radius, height, aim): step the arcs further ALONG the mouth→recorder line
    (never sideways: scenes lane, the slide aimed them into empty air) while they lie over the
    speaker's upper body; after `reach` they may overlap the lower front of the body."""
    phi = math.atan2(d.dot(CU), d.dot(CR))
    u = CR * math.cos(phi) + CU * math.sin(phi)  # toward the target on screen
    w = -CR * math.sin(phi) + CU * math.cos(phi)
    c = at + Vector((0, 0, z))
    if clear:
        mouth, rb, h, aim = clear
        step = aim.normalized() * 0.04
        reach = min(aim.length * 0.55, 1.2)  # never further than about halfway to the recorder
        def on_upper_body(c):
            for R in radii:
                for p in arc_pts(c, u, w, R):
                    q = p - mouth
                    if abs(q.dot(CR)) < rb + 0.08 and -0.45 * h < q.dot(CU) < 0.3 * h:
                        return True
            return False
        moved = 0.0
        while on_upper_body(c) and moved < reach:
            c, moved = c + step, moved + 0.04
    for i, R in enumerate(radii):
        arc = [tuple(c + u * (R * math.cos(math.radians(-50 + 100 * k / 12))) + w * (R * math.sin(math.radians(-50 + 100 * k / 12)))) for k in range(13)]
        B["tube"](arc, 0.05 - i * 0.006, role)


def collars(pts, inset, r, skip=(False, False)):
    """A cream socket ring where the pipe meets each node's surface (not at a device: its port is the ring)."""
    for (p, q), bare in zip(((pts[0], pts[1]), (pts[-1], pts[-2])), skip):
        if bare:
            continue
        d = (q - p).normalized()
        c = B["cyl"](r * 1.7, 0.12, tuple(p + d * (inset + 0.04)), "s", 0.03, verts=48)
        c.rotation_euler = d.to_track_quat("Z", "Y").to_euler()


def pipe(ext_a, ext_b, centre_a, centre_b, cable=False, speech=False, wireless=False, height=1.4,
         target_height=1.0, body=1.0, offset=1.0, packet=0.45, arrow=0.78, route=None, nwaves=2,
         hub_a=False, hub_b=False, wave_at=0.42, bare_a=False, bare_b=False, port_a=None, port_b=None):
    """Route a pipe between two nodes on the screen-aligned grid."""
    ua, wa = centre_a.dot(U), centre_a.dot(V)
    ub, wb = centre_b.dot(U), centre_b.dot(V)
    gap = -0.3 if cable else -0.05  # pipes plug INTO the node (agy: no floating cuffs / short cables)
    # edge meta "route": "rows" forces leaving/entering on the row sides (two pipes into one node
    # then arrive from both sides instead of sharing one muddy segment, agy diagrams r2)
    if route == "L":  # leave on the u side, turn once, enter the target from its row side (into a hub)
        sa = ext_a[1] + gap if ub > ua else ext_a[0] - gap
        sb = ext_b[2] - gap if wb > wa else ext_b[3] + gap
        uw = [(sa, wa), (ub, wa), (ub, sb)]
    elif route == "cols" or (route != "rows" and abs(ub - ua) >= abs(wb - wa)):  # leave/enter on the u sides
        sa = ext_a[1] + gap if ub > ua else ext_a[0] - gap
        sb = ext_b[0] - gap if ub > ua else ext_b[1] + gap
        mid = (sa + sb) / 2
        uw = [(sa, wa), (mid, wa), (mid, wb), (sb, wb)]
    else:  # mostly along rows: leave/enter on the v sides
        sa = ext_a[3] + gap if wb > wa else ext_a[2] - gap
        sb = ext_b[2] - gap if wb > wa else ext_b[3] + gap
        mid = (sa + sb) / 2
        uw = [(ua, sa), (ua, mid), (ub, mid), (ub, sb)]
    pts = [U * u + V * w + Vector((0, 0, PIPE_Z)) for u, w in uw]
    if speech or wireless:  # voice / Bluetooth: waves, not a pipe (agy round 2)
        a, b = centre_a, centre_b
        d = b - a
        if speech:  # owner (2026-11-11): "the angle should come from the face, not from some upper surface".
            # The arcs start just in front of the FACE at mouth height, centred on the face→recorder
            # direction and opening toward it — never anchored beside the head, body or shoulder.
            hr = 0.28 * body  # kit_dolls HEAD_R × doll scale
            mouth = a + Vector((0, 0, height - hr * 1.25))
            aim = (b + Vector((0, 0, target_height * 0.55))) - mouth
            flat = Vector((aim.x, aim.y, 0)).normalized()
            at = mouth + flat * hr * 0.55 * offset  # arc centre just inside the face: the first arc sits on it
            sx, sy = aim.dot(CR), aim.dot(CU)
            if abs(sy) > abs(sx) * 0.8:  # recorder mostly below on screen (back speaker): move the stack one
                # head radius sideways toward it, so the arcs leave the mouth instead of lying on the neck (w4)
                at = at + CR * (1 if sx >= 0 else -1) * hr * 1.1
            waves(Vector((at.x, at.y, 0)), aim, z=at.z, radii=(0.2, 0.32, 0.44))
        else:  # wireless: waves leaving the source and arriving at the target
            for f in ((wave_at,) if nwaves == 1 else (0.3, 0.62)):  # edge meta "waves": 1 = one set, at "waveAt"
                waves(a + d * f, d, role="p", z=PIPE_Z + 0.3, radii=(0.2, 0.34, 0.48))  # red: radio, not voice
        return [a + Vector((0, 0, PIPE_Z)), b + Vector((0, 0, PIPE_Z))]
    if cable:  # scene cable: on the desk, visible, collars at both ends (like the desk-scene cables)
        pts = [p - Vector((0, 0, PIPE_Z - 0.09)) for p in pts]
        pts = fillet(pts, rad=0.35)
        B["tube"]([tuple(p) for p in pts], 0.075, "p")
        collars(pts, 0.3, 0.075)
        p, d = along(pts, 0.6)  # direction (agy round 6)
        bpy.ops.mesh.primitive_cone_add(radius1=0.17, radius2=0, depth=0.3, location=p, vertices=32)
        cone = bpy.context.object
        cone.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        B["finish"](cone, "s")
        return pts
    # a pipe running along a device's own ports enters the port at the port's height: the last stretch
    # ramps from the pipe height to it (owner: "perfect the connection logic"); port_* = (axis, z)
    def ramp(pts, port):
        if port is None or len(pts) < 2:
            return pts
        axis, z = port
        d = pts[1] - pts[0]
        flat = Vector((d.x, d.y, 0))
        if flat.length < 1e-6 or abs(flat.normalized().dot(axis)) < 0.5 or abs(z - PIPE_Z) < 0.02:
            return pts
        run = min(0.55, flat.length * 0.45)
        p0 = pts[0].copy(); p0.z = z
        mid = pts[0] + flat.normalized() * run
        p1 = mid.copy(); p1.z = z
        p2 = pts[0] + flat.normalized() * (run * 1.8); p2.z = PIPE_Z
        return [p0, p1, p2] + pts[1:]
    pts = ramp(pts, port_a)
    pts = list(reversed(ramp(list(reversed(pts)), port_b)))
    pts = fillet(pts, rad=0.22)
    B["tube"]([tuple(p) for p in pts], PIPE_R, "p")
    # owner 2026-11-13 "perfect the connection logic": a pipe into a device ends IN its port (or the socket the
    # diagram adds), so no extra collar or cuff at that end; other ends keep their cream ring
    ends = [e for e, hub, bare in (((pts[0], pts[1] - pts[0]), hub_a, bare_a), ((pts[-1], pts[-2] - pts[-1]), hub_b, bare_b))
            if not hub and not bare]
    if not (hub_a or hub_b):
        collars(pts, 0.05, PIPE_R, skip=(bare_a, bare_b))
    for p, d in ends:  # collars at the ports (none into a junction: agy r6, they clipped the tee)
        c = B["cyl"](PIPE_R * 1.6, 0.1, tuple(p), "s", 0.03)
        c.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    for f in (packet,):  # a packet riding the pipe
        p, _ = along(pts, f)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=PIPE_R * 1.55, location=p, segments=24, ring_count=12)
        B["finish"](bpy.context.object, "g")
    p, d = along(pts, arrow)  # arrow toward the target (edge meta "arrow"/"packet": fractions)
    bpy.ops.mesh.primitive_cone_add(radius1=PIPE_R * 2.3, radius2=0, depth=0.34, location=p, vertices=32)
    cone = bpy.context.object
    cone.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    B["finish"](cone, "g")
    return pts


def label(text, at_ground, size=0.3):
    """Text lying on the board, horizontal on screen."""
    bpy.ops.object.text_add(location=(at_ground.x, at_ground.y, 0.005), rotation=(0, 0, AZ))
    t = bpy.context.object
    t.data.body = text
    t.data.font = bpy.data.fonts.load("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", check_existing=True)
    t.data.size = size
    t.data.extrude = 0.012
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.data.materials.append(B["material"]("r"))
    return t


LABELS = []  # exported as labels.json: crisp HTML labels over the render (agy: no 3D floor text)
PLACED = []  # label rects already on the board, in (right, away) coordinates
PIPE_PTS = []  # sampled pipe points: labels never lie under a pipe
PIPE_SEGS = []  # pipe polylines (fitted board)


def free_spot(anchor, text, size, node_objs, prefer):
    """First candidate label position that is not on a node's footprint, not hidden behind a
    node (its screen 'shadow'), and not on another label. `prefer` = list of (right, away) offsets."""
    lines = text.split("\n")
    w, h = max(len(l) for l in lines) * size * 0.62, size * 1.15 * len(lines)
    blocks = []
    for objs in node_objs:
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in renderable(objs) for c in o.bound_box]
        u0, u1 = min(p.dot(RIGHT) for p in pts) - 0.15, max(p.dot(RIGHT) for p in pts) + 0.15
        w0, w1 = min(p.dot(AWAY) for p in pts) - 0.15, max(p.dot(AWAY) for p in pts)
        hgt = max(p.z for p in pts)
        blocks.append((u0, u1, w0, w1 + hgt * 0.75 + 0.15))  # footprint + the area it hides
    au, aw = anchor.dot(RIGHT), anchor.dot(AWAY)
    for du, dw in prefer:
        u, wv = au + du, aw + dw
        r = (u - w / 2, u + w / 2, wv - h / 2, wv + h / 2)
        hit = any(not (r[1] < b[0] or r[0] > b[1] or r[3] < b[2] or r[2] > b[3]) for b in blocks + PLACED) or any(
            r[0] - 0.15 < q.dot(RIGHT) < r[1] + 0.15 and r[2] - 0.15 < q.dot(AWAY) < r[3] + 0.15 for q in PIPE_PTS)
        if not hit:
            PLACED.append(r)
            return RIGHT * u + AWAY * wv
    PLACED.append((au - w / 2, au + w / 2, aw - h / 2, aw + h / 2))
    return anchor


def wrap(text, limit=11):
    """Long labels go on two lines (centred), so they fit between nodes and pipes."""
    if len(text) <= limit or " " not in text:
        return text
    mid = len(text) // 2
    cut = min((i for i, ch in enumerate(text) if ch == " "), key=lambda i: abs(i - mid))
    return text[:cut] + "\n" + text[cut + 1 :]


def fit_board(rects, t=0.34, step=0.05, rad=0.55):
    """A board shaped to the diagram (agy r5: a rectangle leaves empty corners round an L or a
    branch): the union of rounded strips round the nodes and pipes, in the (u, w) grid frame,
    traced to one outline, corners filleted, extruded like the rectangular board."""
    u0 = min(r[0] for r in rects); u1 = max(r[1] for r in rects)
    w0 = min(r[2] for r in rects); w1 = max(r[3] for r in rects)
    nu, nw = int((u1 - u0) / step) + 3, int((w1 - w0) / step) + 3
    def filled(i, j):
        if i < 0 or j < 0 or i >= nu or j >= nw:
            return False
        u, w = u0 + (i - 1 + 0.5) * step, w0 + (j - 1 + 0.5) * step
        return any(r[0] <= u <= r[1] and r[2] <= w <= r[3] for r in rects)
    grid = [[filled(i, j) for j in range(nw)] for i in range(nu)]
    nxt = {}
    for i in range(nu):  # boundary edges, counter-clockwise round filled cells
        for j in range(nw):
            if not grid[i][j]:
                continue
            for (di, dj), a, b in (((0, -1), (i, j), (i + 1, j)), ((1, 0), (i + 1, j), (i + 1, j + 1)),
                                   ((0, 1), (i + 1, j + 1), (i, j + 1)), ((-1, 0), (i, j + 1), (i, j))):
                ii, jj = i + di, j + dj
                if not (0 <= ii < nu and 0 <= jj < nw and grid[ii][jj]):
                    nxt[a] = b
    start = min(nxt)
    loop, p = [start], nxt[start]
    while p != start and len(loop) < 100000:
        loop.append(p)
        p = nxt[p]
    pts = [(u0 + (i - 1) * step, w0 + (j - 1) * step) for i, j in loop]
    keep = [q for k, q in enumerate(pts)  # corners only
            if (pts[k - 1][0] - q[0]) * (pts[(k + 1) % len(pts)][1] - q[1]) - (pts[k - 1][1] - q[1]) * (pts[(k + 1) % len(pts)][0] - q[0]) != 0]
    def jogs(q, short=0.4):  # drop the tiny steps left where strips are offset by a cell or two
        while len(q) > 4:
            L = [math.dist(q[k], q[(k + 1) % len(q)]) for k in range(len(q))]
            k = min(range(len(q)), key=L.__getitem__)
            if L[k] >= short:
                break
            q = [x for idx, x in enumerate(q) if idx not in (k, (k + 1) % len(q))]
        return q
    keep = jogs(keep)
    ring = [Vector((u, w, 0)) for u, w in keep]
    ring = ring + ring[:2]
    sm = fillet(ring, rad=rad, steps=10)[1:-1]
    prof = [tuple((U * q.x + V * q.y).to_2d()) for q in sm]
    top = B["plate"](prof, t, (0, 0, -t), "c", edge=0.12, clean=True)  # concave caps: no shading creases
    under = B["plate"](prof, t * 0.6, (0, 0, -t - t * 0.85), "p", edge=0.08, clean=True)
    return [top, under]


def hull_board(footprints, margin=0.6, thick=False, rad=1.3):
    """A rounded convex-hull slab round the content footprint (scenes round w4: a grid-aligned
    rectangle left the front corner empty and shrank the props). Same top/underside build as board()."""
    pts = []
    for u0, u1, w0, w1 in footprints:  # footprint corners pushed out by the margin; corners rounded below
        pts += [(u0 - margin, w0 - margin), (u1 + margin, w0 - margin), (u1 + margin, w1 + margin), (u0 - margin, w1 + margin)]
    pts = sorted(set((round(u, 4), round(w, 4)) for u, w in pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p_ in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p_) <= 0:
            lo.pop()
        lo.append(p_)
    for p_ in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p_) <= 0:
            hi.pop()
        hi.append(p_)
    hull = lo[:-1] + hi[:-1]
    # merge hull vertices closer than ~1 unit (clusters of near corners made the "melted" lumps):
    # an intentional island = a few clean straight sides with big round corners
    while len(hull) > 3:
        L = [math.dist(hull[k], hull[(k + 1) % len(hull)]) for k in range(len(hull))]
        k = min(range(len(hull)), key=L.__getitem__)
        if L[k] >= 1.0:
            break
        a_, b_ = hull[k], hull[(k + 1) % len(hull)]
        hull[k] = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
        del hull[(k + 1) % len(hull)]
    ring = [Vector((u, w, 0)) for u, w in hull]
    ring = fillet(ring + ring[:2], rad=rad, steps=14)[1:-1]  # big round corners
    prof = [tuple((U * q.x + V * q.y).to_2d()) for q in ring]
    t = 0.62 if thick else 0.34
    top = B["plate"](prof, t, (0, 0, -t), "c", edge=0.3 if thick else 0.12, clean=True)
    under = B["plate"](prof, t * 0.6, (0, 0, -t - t * 0.85), "p", edge=0.2 if thick else 0.08, clean=True)
    return [top, under]


def board(objs, margin=0.9, thick=False):
    """The rounded desk slab under the whole diagram (cream top, primary underside)."""
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in renderable(objs) for c in o.bound_box]
    us = [p.dot(U) for p in pts]
    ws = [p.dot(V) for p in pts]
    u0, u1, w0, w1 = min(us) - margin, max(us) + margin, min(ws) - margin, max(ws) + margin
    c = U * ((u0 + u1) / 2) + V * ((w0 + w1) / 2)
    W, D = u1 - u0, w1 - w0
    ang = math.atan2(U.y, U.x)
    t = 0.62 if thick else 0.34  # scenes: a chunky desk tile like the approved desk scenes
    W = D = max(W, D) if thick else None or W
    W, D = u1 - u0, w1 - w0
    top = B["box"]((W, D, t), (c.x, c.y, -t / 2), "c", 0.3 if thick else 0.18, rot=(0, 0, ang))
    under = B["box"]((W - 0.08, D - 0.08, t * 0.6), (c.x, c.y, -t - t * 0.25), "p", 0.2 if thick else 0.12, rot=(0, 0, ang))
    return [top, under]


def frame(width=1600, height=1000, tight=False):
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = width, height
    cam = s.camera
    objs = renderable(list(s.objects))
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    centre = sum(pts, Vector()) / len(pts)
    R = cam.matrix_world.to_3x3()
    right, up, back = R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1))
    if tight:  # diagrams: centre on the bounding box, not the vertex mean (which wastes a side)
        rs, us_ = [p.dot(right) for p in pts], [p.dot(up) for p in pts]
        centre = centre + right * ((min(rs) + max(rs)) / 2 - centre.dot(right)) + up * ((min(us_) + max(us_)) / 2 - centre.dot(up))
    er = max(abs((p - centre).dot(right)) for p in pts)
    eu = max(abs((p - centre).dot(up)) for p in pts)
    cam.location = centre + back * 40
    cam.data.clip_end = 200
    cam.data.ortho_scale = max(2 * er, 2 * eu * width / height) * 1.06
    s.render.film_transparent = True
    # scale the light rig to the diagram so the far nodes get the same light as the near ones
    ext = max(er, eu)
    k = max(1.0, ext / 2.2)
    for o in s.objects:
        if o.type == "LIGHT":
            o.location = centre + (o.location - Vector((0, 0, 0.8))) * k
            o.data.energy *= k * k
            o.data.size *= k


# ---- tile-size labels -------------------------------------------------------------------------
# At gallery-tile size (~210–330 px wide) the labels are large compared to the picture, so the
# full-size spots pile up (owner, 2026-11-10). For tiles we lay the labels out again in SCREEN
# space, with the label font as a fixed share of the image width (TILE_F; the HTML sets
# font-size: TILE_F * 100cqw), so what is computed here is exactly what a tile shows at any width.
# Each label goes to the free spot nearest its node: not on a node, not on another label, inside
# the frame; far spots get a leader line. Edge labels are optional (dropped at tile size when no
# spot is close to their pipe) unless the edge says "tile": "need"; a node label can say
# "short" (tile text), "tile": false (hidden on tiles) or "side": "in"/"out" (callout side).
TILE_F = 0.036  # label font, as a share of the image width
FULL_F = 0.0125  # enlarged view: 15 px on a 1200 px diagram (overlay.ts draws width/70)
TILE_SRC = []  # per node label: node id, short text, tile flag (same order as the node LABELS)


def tile_box(text, aspect, font=None):
    font = font or TILE_F
    w = (0.6 * len(text) + 1.1) * font  # Space Grotesk 600 ≈ 0.6 em per glyph, + padding
    h = 1.6 * font * aspect  # line height + border, in image-height units
    return w, h


def rect_gap(a, b):
    """Distance between two rects (x0, x1, y0, y1); 0 when they touch or overlap."""
    dx = max(0, a[0] - b[1], b[0] - a[1])
    dy = max(0, a[2] - b[3], b[2] - a[3])
    return math.hypot(dx, dy)


def overlaps(a, b, pad=0.0):
    return not (a[1] + pad <= b[0] or b[1] + pad <= a[0] or a[3] + pad <= b[2] or b[3] + pad <= a[2])


def tile_layout(out, sc, nodes, edge_mids, spec, font=None, full=False):
    """full=True: the same placement for the enlarged view (FULL_F, full texts) → x/y, flead."""
    font = font or TILE_F
    from bpy_extras.object_utils import world_to_camera_view as w2c
    aspect = sc.render.resolution_x / sc.render.resolution_y
    bpy.context.view_layer.update()

    def sbox(objs):
        pts = [w2c(sc, sc.camera, o.matrix_world @ Vector(c)) for o in renderable(objs) for c in o.bound_box]
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
        y0, y1 = min(1 - p.y for p in pts), max(1 - p.y for p in pts)
        ix, iy = (x1 - x0) * 0.03, (y1 - y0) * 0.03  # bound boxes are a little loose
        return (x0 + ix, x1 - ix, y0 + iy, y1 - iy)

    boxes = {k: sbox(v) for k, v in nodes.items()}
    pipe = [w2c(sc, sc.camera, p) for p in PIPE_PTS]
    pipe = [(p.x, 1 - p.y) for p in pipe]
    items = []
    node_labels = [l for l in out if l["kind"] == "node"]
    # Callout sides: the chain runs along the grid columns, so labels alternate between the two
    # sides of it (into the free corners of the frame), column by column; `side` in the spec wins.
    o = w2c(sc, sc.camera, grid_point(0, 0))
    c1 = w2c(sc, sc.camera, grid_point(1, 0))
    run = Vector((c1.x - o.x, (1 - c1.y) - (1 - o.y))).normalized()
    perp = Vector((run.y, -run.x))  # +: the upper-right side of a down-right chain
    if perp.y > 0:
        perp = -perp
    spec_nodes = {n["id"]: n for n in spec["nodes"]}
    for l, src in zip(node_labels, TILE_SRC):
        n = spec_nodes[src["node"]]
        side = n.get("side", "out" if round(n["at"][0] + n["at"][1]) % 2 == 0 else "in")
        items.append({"l": l, "text": l["text"] if full else (src["short"] or l["text"]), "anchor": boxes[src["node"]],
                      "need": True, "skip": src["tile"] is False and not full, "side": perp if side == "out" else -perp,
                      "sidecost": 0.25 if "side" in n else 0.06})
    for l, (p, meta) in zip([l for l in out if l["kind"] == "edge"], edge_mids):
        v = w2c(sc, sc.camera, p)
        a = (v.x - 0.004, v.x + 0.004, 1 - v.y - 0.006, 1 - v.y + 0.006)
        es = meta.get("side")  # edge meta "side": "out"/"in" pins the label to one side of the chain
        items.append({"l": l, "text": l["text"] if full else (meta.get("short") or l["text"]), "anchor": a, "edge": not es,
                      **({"side": perp if es == "out" else -perp, "sidecost": 0.25, "free": True} if es else {}),
                      "need": full or meta.get("tile") == "need", "skip": meta.get("tile") is False and not full})
    steps = 140 if full else 90
    cands = [((i + 0.5) / steps, (j + 0.5) / steps) for i in range(steps) for j in range(steps)]

    def place(order):
        placed, total, res = [], 0.0, {}
        for it in order:
            if it["skip"]:
                res[id(it)] = None
                continue
            w, h = tile_box(it["text"], aspect, font)
            a = it["anchor"]
            acx, acy = (a[0] + a[1]) / 2, (a[2] + a[3]) / 2
            best, bc = None, 1e9
            pad = font * 0.25
            for relaxed in (False, True):  # a node label that finds no clear spot is placed anyway (agy r6: "Your AI" vanished)
                for cx, cy in cands:
                    r = (cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
                    if r[0] < 0.015 or r[1] > 0.985 or r[2] < 0.02 or r[3] > 0.98:
                        continue
                    if any(overlaps(r, q, font * 0.22) for q in placed):
                        continue
                    if any(overlaps(r, b, font * 0.15) for b in boxes.values()):
                        continue
                    d = rect_gap(r, a)
                    if not relaxed and "side" in it and not it.get("free") and any(rect_gap(r, b) < d + font * 0.42 for b in boxes.values() if b is not a):
                        continue  # it would sit nearer another node and read as that node's label
                    cost = d * 4 + (0.02 if cy < acy else 0)  # near the node; below it reads best
                    cost += 0.08 * sum(1 for px, py in pipe if r[0] - pad < px < r[1] + pad and r[2] - pad < py < r[3] + pad)  # off the pipes
                    if it.get("edge") and Vector((cx - acx, cy - acy)).dot(perp) < 0:
                        cost += 0.04  # edge labels above their pipe, node labels mostly below: no [Relay] [MCP] pairs
                    cost += 0.01 * abs(cx - acx)  # centred under/over its node
                    if "side" in it and not it.get("free") and (r[1] < a[0] or r[0] > a[1]):
                        cost += 0.2  # a callout reads best straight above/below its node, not beside it
                    if "side" in it and Vector((cx - acx, cy - acy)).dot(it["side"]) < 0:
                        cost += it["sidecost"]  # the other side of the chain
                    if cost < bc:
                        best, bc = r, cost
                if best is not None or not it["need"]:
                    break
            if best is None or (not it["need"] and rect_gap(best, a) > font * 1.4):
                res[id(it)] = None
                total += 5 if it["need"] else 0.05
                continue
            placed.append(best)
            res[id(it)] = best
            total += bc
        return total, res

    orders = [items, list(reversed(items)), sorted(items, key=lambda i: -len(i["text"])),
              sorted(items, key=lambda i: not i["need"]), sorted(items, key=lambda i: bool(i.get("edge") or i.get("free")))]
    total, res = min((place(o) for o in orders), key=lambda t: t[0])
    for it in items:
        r = res[id(it)]
        l = it["l"]
        if r is None:
            if not full:
                l["tile"] = False
            continue  # full size keeps the board-plane spot from free_spot
        cx, cy = (r[0] + r[1]) / 2, (r[2] + r[3]) / 2
        l.update({"x": round(cx, 4), "y": round(cy, 4)} if full else {"tx": round(cx, 4), "ty": round(cy, 4)})
        if not full and it["text"] != l["text"]:
            l["short"] = it["text"]
        a = it["anchor"]
        if rect_gap(r, a) > font * 0.3:  # far from its node: a leader line from the node's edge
            ax, ay = min(max(cx, a[0]), a[1]), min(max(cy, a[2]), a[3])
            l["flead" if full else "lead"] = [round(ax, 4), round(ay, 4)]


def main():
    spec = json.load(open(SPEC))
    name = os.path.splitext(os.path.basename(SPEC))[0]
    modes = ["dark", "light"] if MODE == "both" else [MODE]
    B["SAMPLES"] = SAMPLES
    B["reset"]()
    set_layout(spec.get("layout", "iso"))
    global GRID, FOOT
    GRID = spec.get("grid", GRID)
    FOOT = spec.get("foot", FOOT)
    scene = spec.get("kind") == "scene"
    nodes, ext, centres = {}, {}, {}
    for n in spec["nodes"]:
        objs = place_node(n)
        nodes[n["id"]] = objs
        ext[n["id"]] = screen_extent(objs)
        lo, hi = bounds(objs)
        centres[n["id"]] = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0))
    everything = [o for objs in nodes.values() for o in objs]
    heights = {k: bounds(v)[1].z for k, v in nodes.items()}
    ports = {}  # device id -> (port axis, port centre z): the outermost parts along the model's own X
    for n in spec["nodes"]:
        if n.get("icon") not in DEVICE_PORTS:
            continue
        turn = math.radians(n.get("turn", NODE_TURN.get(n.get("icon", ""), 0)))
        axis = Vector((math.cos(turn), math.sin(turn), 0))
        meshes = [o for o in renderable(nodes[n["id"]]) if o.type == "MESH"]
        if not meshes:
            continue
        def reach(o):
            return max(abs((o.matrix_world @ Vector(c) - centres[n["id"]]).dot(axis)) for c in o.bound_box)
        far = max(meshes, key=reach)
        lo, hi = bounds([far])
        ports[n["id"]] = (axis, (lo.z + hi.z) / 2)
    if scene:  # every person in a scene faces the recorder (agy r8), speakers or not
        rec = next((n["id"] for n in spec["nodes"] if n.get("icon") == "record"), None)
        talk = {e[0] for e in spec.get("edges", []) if len(e) > 2 and e[2].get("style") == "speech"}
        if rec:
            for n in spec["nodes"]:
                if "doll" in n and n["id"] not in talk and "turn" not in n:
                    spec.setdefault("edges", []).append([n["id"], rec, {"style": "face"}])
    for e in spec.get("edges", []):
        if len(e) > 2 and e[2].get("style") in ("speech", "face"):
            a, b = e[0], e[1]
            d = centres[b] - centres[a]
            ang = math.atan2(d.y, d.x) - math.atan2(-1, 0)  # -Y is the doll's front
            R = Matrix.Translation(centres[a]) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Translation(-centres[a])
            bpy.context.view_layer.update()
            for o in nodes[a]:
                if o.parent is None:
                    o.matrix_world = R @ o.matrix_world
    edge_labels, edge_mids = [], []
    spec_by_id = {n["id"]: n for n in spec["nodes"]}
    for e in spec.get("edges", []):
        a, b = e[0], e[1]
        meta = e[2] if len(e) > 2 else {}
        if meta.get("style") == "face":
            continue
        before_edge = set(bpy.data.objects)
        pts = pipe(ext[a], ext[b], centres[a], centres[b], cable=scene, speech=meta.get("style") == "speech",
                   wireless=meta.get("style") == "wireless", height=heights[a], target_height=heights[b],
                   body=spec_by_id[a].get("scale", 1.0), offset=meta.get("offset", 1.0),
                   packet=meta.get("packet", 0.45), arrow=meta.get("arrow", 0.78), route=meta.get("route"),
                   nwaves=meta.get("waves", 2), hub_a=bool(spec_by_id[a].get("hub")), hub_b=bool(spec_by_id[b].get("hub")),
                   wave_at=meta.get("waveAt", 0.42),
                   bare_a=not scene and spec_by_id[a].get("icon") in DEVICE_PORTS,
                   bare_b=not scene and spec_by_id[b].get("icon") in DEVICE_PORTS,
                   port_a=None if scene else ports.get(a), port_b=None if scene else ports.get(b))
        if not scene and len(pts) > 1:  # sockets where a pipe meets a device from a portless side
            socket_for(spec_by_id[a], pts[0], (pts[1] - pts[0]).normalized())
            socket_for(spec_by_id[b], pts[-1], (pts[-2] - pts[-1]).normalized())
        for o in [o for o in bpy.data.objects if o not in before_edge]:  # story animation (animate.py
            o.name = f"edge.{a}>{b}.{o.name}"  # --story): each pipe is its own named set
        for k in range(41):
            PIPE_PTS.append(along(pts, k / 40)[0])
        PIPE_SEGS.append(pts)
        if meta.get("label"):
            edge_labels.append((along(pts, 0.5)[0], meta["label"]))
            edge_mids.append((along(pts, 0.5)[0], meta))
    for n in spec["nodes"]:  # node labels first: they get the best spots
        if n.get("label"):
            c = centres[n["id"]]
            front = min((o.matrix_world @ Vector(k)).dot(AWAY) for o in renderable(nodes[n["id"]]) for k in o.bound_box)
            base = c - AWAY * (c.dot(AWAY) - front)
            n["label"] = wrap(n["label"])
            spot = free_spot(base, n["label"], 0.38, list(nodes.values()),
                             [(0, -0.45), (0, -0.85), (1.0, -0.45), (-1.0, -0.45), (1.0, -0.85), (-1.0, -0.85), (0, -1.25), (1.4, 0), (-1.4, 0)])
            LABELS.append({"text": n["label"].replace("\n", " "), "kind": "node", "at": tuple(spot)})
            TILE_SRC.append({"node": n["id"], "short": n.get("short"), "tile": n.get("tile", True)})
    for p, text in edge_labels:
        text = wrap(text)
        spot = free_spot(Vector((p.x, p.y, 0)), text, 0.28, list(nodes.values()),
                         [(0, -0.62), (0, -0.95), (0.8, -0.62), (-0.8, -0.62), (0, 0.62)])
        LABELS.append({"text": text.replace("\n", " "), "kind": "edge", "at": tuple(spot)})
    # spec "groups": [{"nodes": [...], "label": "...", "pad": 0.35}] — things that run in ONE box (owner
    # 2026-11-12: "Caddy also inside the Relay" on the NAS). A navy recess in the board under those
    # nodes, with its own label, so "these live together" reads without a second board.
    group_rects = []
    for g in spec.get("groups", []):
        es = [ext[i] for i in g["nodes"]]
        pad = g.get("pad", 0.35)
        u0, u1 = min(e[0] for e in es) - pad, max(e[1] for e in es) + pad
        w0, w1 = min(e[2] for e in es) - pad, max(e[3] for e in es) + pad
        group_rects.append((u0, u1, w0, w1))
        ring = [Vector((u0, w0, 0)), Vector((u1, w0, 0)), Vector((u1, w1, 0)), Vector((u0, w1, 0))]
        ring = fillet(ring + ring[:2], rad=g.get("round", 0.45), steps=10)[1:-1]
        prof = [tuple((U * q.x + V * q.y).to_2d()) for q in ring]
        B["plate"](prof, 0.03, (0, 0, -0.025), g.get("role", "r"), edge=0.012, clean=True)
        if g.get("label"):
            base = U * ((u0 + u1) / 2) + V * w1  # the front edge (w grows toward the viewer)
            text = wrap(g["label"])
            spot = free_spot(Vector((base.x, base.y, 0)), text, 0.28, list(nodes.values()),
                             [(0, -0.3), (0, -0.65), (0.8, -0.3), (-0.8, -0.3), (0, -1.0)])
            LABELS.append({"text": text.replace("\n", " "), "kind": "edge", "at": tuple(spot)})
    if spec.get("board") == "fit":
        # an even-width ribbon: one half-width round every node centre and along every pipe
        exts = [screen_extent(v) for v in nodes.values()]
        h = max(max(e[1] - e[0], e[3] - e[2]) for e in exts) / 2 + spec.get("boardPad", 0.4)
        rects = []
        for e in exts:
            cu, cw = (e[0] + e[1]) / 2, (e[2] + e[3]) / 2
            rects.append((cu - h, cu + h, cw - h, cw + h))
        for pts in PIPE_SEGS:
            for a, b in zip(pts, pts[1:]):
                us, ws = (a.dot(U), b.dot(U)), (a.dot(V), b.dot(V))
                rects.append((min(us) - h, max(us) + h, min(ws) - h, max(ws) + h))
        rects += [(r[0] - 0.25, r[1] + 0.25, r[2] - 0.25, r[3] + 0.25) for r in group_rects]
        fit_board(rects, rad=spec.get("boardRound", 0.9))
    elif spec.get("board", "hull" if scene else "rect") == "hull":
        hull_board([screen_extent(v) for v in nodes.values()], margin=spec.get("boardPad", 0.6), thick=scene)
    else:
        board([o for o in bpy.context.scene.objects], margin=spec.get("boardPad", 0.45 if scene else 0.65), thick=scene)
    B["CURRENT"] = ""
    B["light_and_camera"]()
    frame(1024, 1024, tight=True) if scene else frame(tight=True)
    for mode in modes:
        B["paint"](mode)
        bpy.context.scene.render.filepath = f"{OUT}/{mode}.png"
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print(f"gpu failed ({e}); rendering on CPU")
            bpy.context.scene.cycles.device = "CPU"
            bpy.ops.render.render(write_still=True)
        print(f"ok   {name}/{mode}")
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    out = []
    for l in LABELS:
        v = world_to_camera_view(sc, sc.camera, Vector(l["at"]))
        # "w": the label's world point, so animate.py can re-project it per frame (moving camera)
        out.append({"text": l["text"], "kind": l["kind"], "x": round(v.x, 4), "y": round(1 - v.y, 4),
                    "w": [round(c, 4) for c in l["at"]]})
    if LABELS:
        tile_layout(out, sc, nodes, edge_mids, spec, FULL_F, full=True)
        tile_layout(out, sc, nodes, edge_mids, spec)
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(f"{OUT}/{name}.blend"), compress=True)  # for the animation pass
    res = sc.render
    json.dump({"title": spec.get("title", ""), "aspect": round(res.resolution_x / res.resolution_y, 4), "tileFont": TILE_F, "fullFont": FULL_F,
               "labels": out}, open(f"{OUT}/labels.json", "w"), indent=1)


main()
