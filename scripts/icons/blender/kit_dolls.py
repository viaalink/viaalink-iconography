"""
Dolls kit: faceless toy people for the deterministic Blender icon pipeline (W-140).

Preview every outfit as its own icon, plus a lineup of all of them:

  blender -b --factory-startup -P scripts/icons/blender/kit_dolls.py -- \
      --out local/icons/rounds/25d-b8-dolls [--mode dark|light|both] [--samples 48] [outfit ...]
  bun scripts/icons/normalize.ts local/icons/rounds/25d-b8-dolls

Writes <out>/<mode>/doll-<outfit>.png and <out>/<mode>/doll-lineup.png.

Use from another script (shares ONE build.py globals dict, so one material set / paint()):

  K = runpy.run_path("kit_dolls.py", init_globals={"B": B}, run_name="via_kit")
  K["doll"]("doctor", at=(-1.1, 0.9, 0.3), turn=10)

doll() only adds objects to the current scene; it never calls reset() or build.py's turn().

A doll is a pill body (a lathed, slightly oval rounded cylinder ~0.62 x 0.52 x 1.0) with a
round faceless head (r 0.28) on top, ~1.56 tall. Outfit details that sit ON the body (shirt V,
tie) are inlays: a slightly grown copy of the body intersected with a prism, so they follow
the curved surface. Roles as in build.py: p primary, s secondary, r recess, c cream, g glyph.

Outfits:
  doctor     c coat, p stethoscope loop around the neck with a chest disc
  lawyer     p suit, c shirt V, s tie
  student    p hoodie with c hood rim, s backpack with c straps
  teacher    s body, book (p cover, c pages) held in front
  parent     p body, c scarf (neck roll + tail)
  child      scale 0.75, rounder body and bigger head; c body, p cap
  developer  s hoodie with p hood rim, small p laptop held at the waist, screen out
  client     c body, s folder under the arm (+X side) with a p band
"""

import math
import os
import runpy
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
B = globals().get("B") or runpy.run_path(
    os.path.join(HERE, "build.py"), init_globals={"VIA_IMPORT_ONLY": True}, run_name="via_build"
)
B = B["box"].__globals__  # runpy returns a COPY; the live dict is what build.py's functions read (CURRENT)
box, cyl, tube, plate, finish, rr_profile, smooth, torus = (
    B["box"],
    B["cyl"],
    B["tube"],
    B["plate"],
    B["finish"],
    B["rr_profile"],
    B["smooth"],
    B["torus"],
)
D2R = math.radians
FACE = (D2R(90), 0, 0)  # plate: profile XY -> XZ, extruded toward -Y


# ---------------------------------------------------------------- body geometry
class Body:
    """Lathed pill profile (r, z) from the bottom axis to the top axis; `sy` squashes depth."""

    def __init__(self, R=0.31, H=1.0, shoulder=0.27, top=0.05, foot=0.05, sy=0.52 / 0.62):
        self.R, self.H, self.sy = R, H, sy
        p = [(0.0, 0.0)]
        for k in range(5):  # small foot fillet
            a = D2R(-90 + 90 * k / 4)
            p.append((R - foot + foot * math.cos(a), foot + foot * math.sin(a)))
        cx, cz = R - shoulder, H - shoulder
        for k in range(17):  # big round shoulder
            a = D2R(90 * k / 16)
            p.append(
                (max(cx, top) + shoulder * math.cos(a) * (R - max(cx, top)) / shoulder, cz + shoulder * math.sin(a))
            )
        p.append((0.0, H))
        self.prof = p

    def offset(self, g):
        """Profile grown by g along its 2D normal (axis points stay on the axis)."""
        out = []
        n = len(self.prof)
        for i, (r, z) in enumerate(self.prof):
            if r == 0.0:
                out.append((0.0, z + (g if z > 0 else -g)))
                continue
            a, b = self.prof[max(i - 1, 0)], self.prof[min(i + 1, n - 1)]
            tx, tz = b[0] - a[0], b[1] - a[1]
            L = math.hypot(tx, tz) or 1.0
            out.append((r + g * tz / L, z - g * tx / L))
        return out

    def r_at(self, z, prof=None):
        """Outer radius at height z (0 above the top)."""
        best = 0.0
        prof = prof or self.prof
        for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
            if min(z0, z1) <= z <= max(z0, z1) and z1 != z0:
                t = (z - z0) / (z1 - z0)
                best = max(best, r0 + (r1 - r0) * t)
        return best

    def surf(self, th, z, off=0.0):
        """Point on the (grown) surface; th = degrees around Z from the front (-Y) toward +X."""
        r = self.r_at(z, self.offset(off) if off else None)
        a = D2R(th)
        return (r * math.sin(a), -r * self.sy * math.cos(a), z)


def lathe(prof, role, sy=1.0, n=72):
    """Closed surface of revolution from a profile (first/last point on the axis)."""
    verts, faces, rings = [], [], []
    for r, z in prof:
        if r == 0.0:
            verts.append((0.0, 0.0, z))
            rings.append([len(verts) - 1])
        else:
            start = len(verts)
            for k in range(n):
                a = 2 * math.pi * k / n
                verts.append((r * math.sin(a), -r * sy * math.cos(a), z))
            rings.append(list(range(start, start + n)))
    for A, Bv in zip(rings, rings[1:]):
        if len(A) == 1:
            faces += [[A[0], Bv[(k + 1) % n], Bv[k]] for k in range(n)]
        elif len(Bv) == 1:
            faces += [[A[k], A[(k + 1) % n], Bv[0]] for k in range(n)]
        else:
            faces += [[A[k], A[(k + 1) % n], Bv[(k + 1) % n], Bv[k]] for k in range(n)]
    me = bpy.data.meshes.new("lathe")
    me.from_pydata(verts, [], faces)
    me.update()
    me.validate()
    o = bpy.data.objects.new("lathe", me)
    bpy.context.collection.objects.link(o)
    finish(o, role)
    # consistent outward normals (pole fans are wound by hand)
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    return o


def sphere(r, loc, role, sz=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=64, ring_count=32)
    o = bpy.context.view_layer.objects.active
    if sz != 1.0:
        o.scale = (1, 1, sz)
        bpy.ops.object.transform_apply(scale=True)
    return finish(o, role)


def apply_bool(target, cutter, op):
    mod = target.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(cutter, do_unlink=True)
    smooth(target, 40)
    return target


def inlay(body, profile_xz, role, grow=0.014):
    """Surface-following patch on the front of the body: a grown body shell cut to a 2D outline
    (profile in XZ, seen from the front)."""
    shell = lathe(body.offset(grow), role, body.sy)
    if sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(profile_xz, profile_xz[1:] + profile_xz[:1])) < 0:
        profile_xz = profile_xz[::-1]  # plate() needs CCW for outward normals
    cutter = plate(profile_xz, 1.0, (0, 0, 0), role, rot=FACE)
    return apply_bool(shell, cutter, "INTERSECT")


def smooth_path(pts, k=6):
    """Catmull-Rom through pts (open) -> dense polyline for tube()."""
    P = [Vector(p) for p in pts]
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(k):
            t = j / k
            out.append(
                tuple(
                    0.5
                    * (
                        (2 * p1)
                        + (-p0 + p2) * t
                        + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                        + (-p0 + 3 * p1 - 3 * p2 + p3) * t**3
                    )
                )
            )
    out.append(tuple(P[-2]))
    return out


def neck_ring(body, z, r, role, off=None):
    """Closed roll lying on the shoulders around the neck (hood rim, scarf)."""
    off = r * 0.75 if off is None else off
    pts = [body.surf(th, z, off) for th in range(0, 361, 6)]
    o = tube(pts, r, role)
    o.data.splines[0].use_cyclic_u = True
    return o


# ---------------------------------------------------------------- outfits
ADULT = {"R": 0.31, "H": 1.0, "shoulder": 0.27}
HEAD_R = 0.28


def base(body_role, head_role="c", body=None, head_r=HEAD_R):
    body = body or Body(**ADULT)
    objs = [lathe(body.prof, body_role, body.sy)]
    objs.append(sphere(head_r, (0, 0, body.H + head_r - 0.035), head_role))
    return body, objs


def straps(body, xs, role, r=0.055, zlow=0.42):
    """Backpack straps: over the shoulder from the back to the front at |x| = xs."""
    objs = []
    for sx in (-1, 1):
        x = sx * xs
        g = body.offset(r * 0.8)
        ztop = max(z for (rr, z) in g if rr >= abs(x)) if any(rr >= abs(x) for rr, _ in g) else body.H
        pts = []
        zs = [zlow + (ztop - zlow) * k / 10 for k in range(11)]
        for z in zs:
            rr = body.r_at(z, g)
            pts.append((x, body.sy * math.sqrt(max(rr * rr - x * x, 0)), z))
        pts.append((x, 0.0, ztop + 0.02))
        for z in reversed(zs):
            rr = body.r_at(z, g)
            pts.append((x, -body.sy * math.sqrt(max(rr * rr - x * x, 0)), z))
        objs.append(tube(smooth_path(pts[::2] + [pts[-1]], 4), r, role))
    return objs


def hoodie(body, rim_role, string_role=None):
    objs = [neck_ring(body, body.H - 0.03, 0.062, rim_role, 0.04)]
    for x in (-0.07, 0.07) if string_role else ():  # drawstrings
        top = body.surf(math.degrees(math.asin(x / 0.3)), body.H - 0.14, 0.03)
        objs.append(
            tube(
                [top, (top[0], top[1] - 0.02, top[2] - 0.13), (top[0], top[1] - 0.025, top[2] - 0.22)],
                0.032,
                string_role,
            )
        )
    return objs


def o_doctor():
    body, objs = base("c")
    # stethoscope: closed loop hanging from the neck, low at the front, with a chest disc
    pts = []
    for th in range(0, 361, 6):
        d = min(th, 360 - th)
        t = min(max((d - 8) / 62, 0), 1)
        t = t * t * (3 - 2 * t)
        z = 0.58 + (body.H + 0.0 - 0.58) * t
        pts.append(body.surf(th, z, 0.05))
    loop = tube(pts, 0.058, "p")
    loop.data.splines[0].use_cyclic_u = True
    x, y, z = body.surf(0, 0.58, 0.05)
    objs += [loop, tube([(x, y, z), (x, y - 0.02, z - 0.1)], 0.058, "p")]
    objs.append(cyl(0.11, 0.08, (x, y - 0.05, z - 0.17), "p", 0.03, rot=FACE))
    objs.append(cyl(0.055, 0.04, (x, y - 0.1, z - 0.17), "c", 0.015, rot=FACE))
    return objs


TIE_ROLE = "p"  # brief said s; s is cream in dark mode and vanished on the cream shirt


def o_lawyer():
    body, objs = base("p")
    H = body.H
    objs.append(
        inlay(body, [(-0.3, H + 0.1), (0.3, H + 0.1), (0.0, 0.4)], "c")
    )  # agy r11: wide shirt V so the red tie reads
    tie = [(0.0, H - 0.06), (0.07, H - 0.13), (0.045, 0.64), (0.0, 0.57), (-0.045, 0.64), (-0.07, H - 0.13)]
    objs.append(inlay(body, tie, TIE_ROLE, 0.03))
    return objs


def o_student():
    """Student: red hoodie + mortarboard (agy r10 blind: the backpack read as a white block)."""
    body, objs = base("p")
    hz = body.H + HEAD_R - 0.035
    objs.append(cyl(0.22, 0.14, (0, 0, hz + 0.22), "p", 0.03))  # cap band on the head
    objs.append(box((0.62, 0.62, 0.06), (0, 0, hz + 0.31), "p", 0.025, rot=(0, 0, D2R(45))))  # board
    objs.append(sphere(0.045, (0, 0, hz + 0.35), "c"))
    objs.append(
        tube(
            [(0, 0, hz + 0.345), (0.22, -0.22, hz + 0.345), (0.25, -0.25, hz + 0.3), (0.25, -0.25, hz + 0.14)],
            0.025,
            "c",
        )
    )  # tassel cord
    objs.append(cyl(0.05, 0.12, (0.25, -0.25, hz + 0.1), "c", 0.02))  # tassel
    return objs


def o_teacher():
    """Teacher: cream body holding a red book open toward the class, at the front (agy r14: a
    lanyard read as 'corporate'). Since ebccb6a the speech waves clear the speaker's silhouette, so
    the book no longer looks like it is talking (agy r10)."""
    body, objs = base("s")
    y = -body.R * body.sy - 0.1
    parts = [
        box((0.34, 0.12, 0.42), (0.03, y, 0.5), "c", 0.03),
        box((0.38, 0.04, 0.46), (0.02, y - 0.075, 0.5), "p", 0.02),
        box((0.38, 0.04, 0.46), (0.02, y + 0.075, 0.5), "p", 0.02),
        box((0.05, 0.19, 0.46), (-0.165, y, 0.5), "p", 0.02),
    ]
    bpy.context.view_layer.update()
    c = Vector((0, y, 0.5))
    M = (
        Matrix.Translation(c)
        @ Matrix.Rotation(D2R(8), 4, "Z")
        @ Matrix.Rotation(D2R(-10), 4, "X")
        @ Matrix.Translation(-c)
    )
    for o in parts:
        o.matrix_world = M @ o.matrix_world
    return objs + parts


def o_parent():
    """Parent: plain red adult. Scenes stand the parent next to a child; the scarf read as a neck
    brace (agy r10) and a crossbody bag as an unknown white object (agy r11)."""
    body, objs = base("p")
    return objs


CHILD_BODY = {"R": 0.31, "H": 0.6, "shoulder": 0.27}  # agy r14: shorter torso, full-size head = child
CHILD_HEAD = 0.34  # agy r10: kids read as workers; a bigger head reads younger


def o_child():
    """Child: round beanie with a big pompom (agy r10: the brimmed cap read as a worker's cap)."""
    body = Body(**CHILD_BODY)
    hr = CHILD_HEAD
    body, objs = base("c", body=body, head_r=hr)
    hz = body.H + hr - 0.035
    cap = [(0.0, hz + hr + 0.025)]
    for k in range(16, -1, -1):  # dome from the top down to just above the equator
        a = D2R(18 + 72 * k / 16)
        cap.append(((hr + 0.025) * math.cos(a), hz + (hr + 0.025) * math.sin(a)))
    cap.append((0.0, hz + (hr + 0.025) * math.sin(D2R(18))))
    objs.append(lathe(cap[::-1], "p"))
    objs.append(torus(hr * math.cos(D2R(18)) + 0.02, 0.05, (0, 0, hz + hr * math.sin(D2R(18))), "p"))
    objs.append(sphere(0.12, (0, 0, hz + hr + 0.1), "c"))
    return objs


def o_child_b():
    """Second child: red hair with two buns, red body (two different kids; agy r12: two cream
    bodies vanished on the cream desk)."""
    body = Body(**CHILD_BODY)
    hr = CHILD_HEAD
    body, objs = base("p", body=body, head_r=hr)
    hz = body.H + hr - 0.035
    cap = [(0.0, hz + hr + 0.02)]
    for k in range(16, -1, -1):  # hair: dome over the back and top
        a = D2R(-5 + 95 * k / 16)
        cap.append(((hr + 0.02) * math.cos(a), hz + (hr + 0.02) * math.sin(a)))
    cap.append((0.0, hz + (hr + 0.02) * math.sin(D2R(-5))))
    hair = lathe(cap[::-1], "p")
    cutter = box((1.0, 0.5, 0.44), (0, -0.36, hz - 0.1), "p", 0.0)  # open the face
    B["cut"](hair, cutter)
    objs.append(hair)
    for sx in (-1, 1):
        objs.append(sphere(0.14, (sx * (hr - 0.02), 0.05, hz + hr * 0.62), "p"))
    return objs


def o_developer():
    body, objs = base("s")
    objs += hoodie(body, "p")
    y0 = -body.R * body.sy - 0.14
    z0 = 0.46
    parts = [
        box((0.56, 0.32, 0.06), (0, y0 + 0.06, z0), "p", 0.025),
        box((0.56, 0.06, 0.4), (0, y0 - 0.1, z0 + 0.19), "p", 0.03),
    ]
    parts.append(plate(rr_profile(0.46, 0.3, 0.04), 0.02, (0, y0 - 0.13, z0 + 0.21), "r", rot=FACE))
    for a, b in (((-0.16, 0.29), (-0.08, 0.23)), ((-0.08, 0.23), (-0.16, 0.17))):
        pa, pb = Vector((a[0], 0, z0 + a[1])), Vector((b[0], 0, z0 + b[1]))
        d = pb - pa
        parts.append(
            box(
                (d.length + 0.05, 0.03, 0.05),
                ((pa.x + pb.x) / 2, y0 - 0.15, (pa.z + pb.z) / 2),
                "g",
                0.02,
                rot=(0, -math.atan2(d.z, d.x), 0),
            )
        )
    parts.append(box((0.16, 0.03, 0.05), (0.04, y0 - 0.15, z0 + 0.17), "g", 0.02))
    return objs + parts


def o_client():
    """Client holding a tablet in front (agy r7: the folder read as an unknown slab)."""
    body, objs = base("c")
    y = -body.R * body.sy - 0.12
    parts = [box((0.46, 0.07, 0.6), (0.08, y, 0.62), "p", 0.05)]
    scr = box((0.36, 0.02, 0.48), (0.08, y - 0.04, 0.64), "r", 0.03)
    parts.append(scr)
    parts.append(box((0.22, 0.02, 0.05), (0.08, y - 0.055, 0.74), "c", 0.02))
    parts.append(box((0.16, 0.02, 0.05), (0.05, y - 0.055, 0.64), "c", 0.02))
    bpy.context.view_layer.update()
    c = Vector((0.08, y, 0.62))
    M = Matrix.Translation(c) @ Matrix.Rotation(D2R(-18), 4, "X") @ Matrix.Translation(-c)
    for o in parts:
        o.matrix_world = M @ o.matrix_world
    return objs + parts


def o_patient():
    """Patient: red body leaning on a cream crutch (agy r19: a red cross plaster made the patient
    read as medical staff, and the sling read as an unknown white shape)."""
    body, objs = base("p")
    x0, x1 = (
        -(body.R + 0.02),
        -(body.R + 0.3),
    )  # on -X (faces the camera once the patient turns to the phone); pad in the armpit, foot splayed out
    zt, zj = body.H - 0.1, 0.34
    lerp = lambda z: x0 + (x1 - x0) * (zt - z) / (zt - 0.04)
    for dy in (-0.09, 0.09):  # two rails, like a real crutch
        objs.append(tube([(x0, dy, zt), (lerp(zj), dy * 0.15, zj)], 0.042, "s"))
    objs.append(box((0.1, 0.3, 0.08), (x0, 0.0, zt + 0.03), "s", 0.035))  # underarm pad
    objs.append(box((0.07, 0.2, 0.06), (lerp(0.6), 0.0, 0.6), "s", 0.025))  # hand grip
    objs.append(tube([(lerp(zj), 0.0, zj), (x1, 0.0, 0.06)], 0.048, "s"))  # leg
    objs.append(cyl(0.075, 0.07, (x1, 0.0, 0.035), "p", 0.02))  # rubber foot
    return objs


def o_visitor():
    """Client at a lawyer's: cream body with a red open polo collar, casual next to the suit (agy
    r15: plain client; r19: a briefcase read as a toolbox and sat under the waves)."""
    body, objs = base("c")
    H = body.H
    for sx in (-1, 1):  # collar points
        objs.append(inlay(body, [(sx * 0.02, H - 0.02), (sx * 0.24, H - 0.02), (sx * 0.1, H - 0.2)], "p", 0.02))
    return objs


def o_adult_cap():
    """An ordinary person (cream) in a red flat cap: one of two equal parties to an agreement."""
    body, objs = base("c")
    hz = body.H + HEAD_R - 0.035
    objs.append(sphere(HEAD_R + 0.025, (0, 0.02, hz + 0.1), "p", 0.42))  # flat crown
    objs.append(cyl(0.17, 0.04, (0, -0.24, hz + 0.08), "p", 0.015, rot=(D2R(-12), 0, 0)))  # peak
    return objs


def o_adult_bun():
    """The other party: red body, red hair with a bun at the back (a different person at a glance)."""
    body, objs = base("p")
    hr = HEAD_R
    hz = body.H + hr - 0.035
    cap = [(0.0, hz + hr + 0.02)]
    for k in range(16, -1, -1):
        a = D2R(-15 + 105 * k / 16)
        cap.append(((hr + 0.02) * math.cos(a), hz + (hr + 0.02) * math.sin(a)))
    cap.append((0.0, hz + (hr + 0.02) * math.sin(D2R(-15))))
    hair = lathe(cap[::-1], "p")
    B["cut"](hair, box((1.0, 0.5, 0.42), (0, -0.33, hz - 0.1), "p", 0.0))  # open the face
    objs += [hair, sphere(0.15, (0, hr * 0.8, hz + hr * 0.55), "p")]  # bun
    return objs


def o_person(role="c"):
    """Plain person (no outfit): for scenes where the role is 'anyone' (two people agreeing)."""
    return base(role)[1]


# ---------------------------------------------------------------- scene props
# Desk-scene props that have no icon in build.py (that file belongs to the icons lane). They live
# here because diagram.py places any name doll() knows; a scene node uses {"doll": "contract",
# "turn": 0}: `turn` keeps the scene's face-the-recorder rule from turning the prop away.
# Built at icon size (about 1.9 x 2.4), the same as report, so scale ~0.85 matches the icons.


def _sheet(w, h, d, z0, paper="c"):
    """Upright document on a cream stand: red frame, sunk face filled with a paper plate."""
    box((w * 0.62, 0.9, 0.2), (0, 0.18, 0.1), "s", 0.08)  # stand
    dev = B["Device"](w, h, d, "p", screen=(0.16, 0.16, 0.16, 0.16), z0=z0, y=-0.02)
    prof = rr_profile(dev.sw, dev.sh, min(dev.sw, dev.sh) * 0.1)
    plate(prof, 0.03, (dev.cx, dev.floor + 0.004, dev.cz), paper, rot=FACE)
    dev.floor -= 0.026  # glyphs sit on the paper, not under it
    return dev


def p_contract(seal="check", mark=False):
    """Signed contract: paper with text lines, a big red signature and a round seal: a check
    (agreed) or a padlock (kept private). agy r9: the check-on-a-disc did not read as a contract;
    no pen: a thin prop that met the cable."""
    dev = _sheet(1.9, 2.4, 0.24, 0.16)
    emboss = B["emboss"]
    if mark:  # legal: a red section mark heads the page (agy r14: lawyer = contract scene)
        x, y, z = dev.at(-0.2, 0.3, 0.0)
        cyl(0.3, 0.07, (x, y - 0.035, z), "p", 0.025, rot=FACE)
        yy = y - 0.085  # cream scales of justice on the disc (a § read as an 8 at 400 px)
        box((0.045, 0.03, 0.3), (x, yy, z - 0.01), "c", 0.012)  # post
        box((0.36, 0.03, 0.04), (x, yy, z + 0.12), "c", 0.012)  # beam
        box((0.18, 0.03, 0.04), (x, yy, z - 0.15), "c", 0.012)  # foot
        half = [(0.09 * math.cos(math.pi * k / 12), -0.09 * math.sin(math.pi * k / 12)) for k in range(13)]
        for sx in (-1, 1):
            px = x + sx * 0.16
            tube([(px, yy, z + 0.12), (px, yy, z + 0.0)], 0.01, "c")  # hanger
            plate(half, 0.03, (px, yy + 0.015, z - 0.005), "c", rot=FACE, edge=0.008)  # pan
        emboss(dev, [(0.1, 0.36), (0.32, 0.36)], 0.13, "r", 0.06)
        emboss(dev, [(0.1, 0.24), (0.26, 0.24)], 0.1, "r", 0.05)
    else:
        emboss(dev, [(-0.3, 0.36), (0.12, 0.36)], 0.15, "r", 0.06)  # heading
    for v, u1 in ((0.2, 0.3), (0.07, 0.3), (-0.06, 0.18)):
        emboss(dev, [(-0.3, v), (u1, v)], 0.1, "r", 0.05)
    # signature: one smooth loopy stroke (tube) over a signing line
    emboss(dev, [(-0.32, -0.36), (-0.02, -0.36)], 0.05, "r", 0.04)
    sig = []
    for k in range(41):
        t = k / 40
        u = -0.3 + 0.26 * t  # ends well left of the seal (agy r15: contact)
        v = -0.27 + 0.07 * math.sin(t * math.pi * 3.2) * (1 - 0.4 * t) + 0.03 * math.sin(t * math.pi)
        sig.append(dev.at(u, v, 0.05))
    tube(sig, 0.04, "p")
    # seal, lower right: red disc with a cream check, or a red padlock
    x, y, z = dev.at(0.27, -0.29, 0.0)
    if seal == "lock":
        cyl(0.31, 0.08, (x, y - 0.04, z), "p", 0.03, rot=FACE)
        B["padlock"](x, y - 0.13, z - 0.04, 0.74, "c", "r")  # agy r11: a red lock vanished on the red frame
        return
    cyl(0.25, 0.08, (x, y - 0.04, z), "p", 0.03, rot=FACE)
    chk = B["stroke_outline"]([(-0.11, 0.0), (-0.03, -0.08), (0.12, 0.08)], 0.07)
    plate(chk, 0.04, (x, y - 0.075, z), "c", rot=FACE, edge=0.015, clean=True)


def p_checklist():
    """What was promised: paper with three big ticked boxes (kids scene; agy r11: the legal
    contract duplicated the lawyer scene)."""
    dev = _sheet(1.9, 2.4, 0.24, 0.16)
    for v in (0.3, 0.0, -0.3):
        x, y, z = dev.at(-0.24, v, 0.0)
        box((0.4, 0.06, 0.4), (x, y - 0.03, z), "p", 0.07)  # red box (agy r13: red ticks on slate too dark)
        chk = B["stroke_outline"]([(-0.11, 0.0), (-0.02, -0.09), (0.14, 0.11)], 0.085)
        plate(chk, 0.05, (x + 0.01, y - 0.06, z), "c", rot=FACE, edge=0.015, clean=True)
        B["emboss"](dev, [(-0.04, v), (0.3, v)], 0.11, "r", 0.05)


def p_chart():
    """Medical notes: the report clipboard with a red cross header instead of the AI spark
    (agy r10: the doctor's output should read as clinical notes)."""
    dev = B["Device"](1.9, 2.35, 0.26, "p", screen=(0.17, 0.17, 0.32, 0.17))
    box((0.75, 0.34, 0.26), (0, 0, 2.38), "s", 0.1)  # clip
    box((0.36, 0.3, 0.22), (0, 0, 2.55), "s", 0.1)
    x, y, z = dev.at(-0.22, 0.27, 0.0)
    cross = [
        (-0.06, -0.17),
        (0.06, -0.17),
        (0.06, -0.06),
        (0.17, -0.06),
        (0.17, 0.06),
        (0.06, 0.06),
        (0.06, 0.17),
        (-0.06, 0.17),
        (-0.06, 0.06),
        (-0.17, 0.06),
        (-0.17, -0.06),
        (-0.06, -0.06),
    ]
    box((0.5, 0.06, 0.5), (x, y - 0.02, z), "c", 0.08)  # cream badge: red on slate was too dark at 400 px (agy r13)
    plate([(px * 1.15, py * 1.15) for px, py in cross], 0.06, (x, y - 0.04, z), "k", rot=FACE, edge=0.02, clean=True)
    B["bar"](dev, 0.06, 0.3, 0.27, 0.06)
    for v, u1 in ((0.07, 0.3), (-0.1, -0.04), (-0.27, -0.1)):  # short lower lines leave room for the seal
        B["bar"](dev, -0.3, u1, v, 0.055)
    x, y, z = dev.at(0.27, -0.29, 0.0)  # private: the same red seal + cream padlock as the contract
    cyl(0.31, 0.08, (x, y - 0.04, z), "p", 0.03, rot=FACE)
    B["padlock"](x, y - 0.13, z - 0.04, 0.74, "c", "r")


def p_camera():
    """Another recording device: a chunky camera with a big lens (import scene)."""
    box((1.9, 0.95, 1.25), (0, 0, 0.66), "p", 0.22)
    box((0.62, 0.7, 0.3), (-0.45, 0.0, 1.32), "p", 0.1)  # viewfinder hump
    cyl(0.13, 0.12, (0.55, 0.0, 1.32), "s", 0.04)  # shutter button
    y0 = -0.475
    cyl(0.52, 0.16, (0.08, y0 - 0.06, 0.66), "s", 0.05, rot=FACE)  # lens rim
    cyl(0.42, 0.2, (0.08, y0 - 0.12, 0.66), "r", 0.04, rot=FACE)  # glass
    cyl(0.2, 0.06, (0.08, y0 - 0.23, 0.66), "k", 0.02, rot=FACE)  # inner ring
    tube(
        [(0.08 + 0.3 * math.cos(D2R(a)), y0 - 0.24, 0.66 + 0.3 * math.sin(D2R(a))) for a in range(110, 161, 5)],
        0.03,
        "c",
    )  # glint
    cyl(0.08, 0.05, (-0.68, y0 - 0.02, 1.05), "c", 0.02, rot=FACE)  # record lamp


def p_audiofolder():
    """Audio files: the folder shape with a waveform on the front instead of the share glyph
    (agy r10: share read as 'file sharing', not 'recordings')."""
    W, T = 2.5, 0.24
    box((W, T, 1.85), (0, 0.14, 0.925), "p", 0.11)
    box((0.9, T, 0.38), (-W / 2 + 0.52, 0.14, 1.85), "p", 0.11)
    box((1.75, 0.1, 1.4), (0.1, 0.0, 1.25), "c", 0.05)  # paper
    for zz in (1.72, 1.51):
        box((1.05, 0.06, 0.085), (0.1, -0.04, zz), "r", 0.04)
    box((W, T, 1.3), (0, -0.14, 0.65), "p", 0.11)
    box((W - 0.12, 0.28, 0.22), (0, 0.0, 0.11), "p", 0.06)
    yf = -0.14 - T / 2
    for i, hgt in enumerate((0.3, 0.6, 0.85, 0.5, 0.7, 0.35)):  # waveform
        x = -0.62 + i * 0.25
        prof = B["stroke_outline"]([(0, -hgt / 2), (0, hgt / 2)], 0.13)
        plate(prof, 0.06, (x, yf + 0.01, 0.65), "c", rot=FACE, edge=0.025, clean=True)


def p_sessions():
    """All recorded sessions, kept: three session cards standing one behind the other in a cream
    tray (agy r12: one phone list read as 'private notes', not 'every session kept')."""
    box((2.3, 1.55, 0.3), (0.2, 0.17, 0.15), "s", 0.1)  # tray
    for i, (dx, dy, dz) in enumerate(((0.5, 0.55, 0.42), (0.25, 0.18, 0.21), (0.0, -0.2, 0.0))):
        dev = B["Device"](1.6, 1.9, 0.16, "p", screen=(0.14, 0.14, 0.14, 0.14), x=dx, y=dy, z0=0.2 + dz, bevel=0.1)
        if i == 2:  # the front card shows a session: waveform + two lines
            for k, hgt in enumerate((0.25, 0.5, 0.75, 0.45, 0.6, 0.3)):
                u = -0.3 + k * 0.12
                B["emboss"](dev, [(u, 0.18 - hgt * 0.12), (u, 0.18 + hgt * 0.12)], 0.1, "g", 0.06)
            B["bar"](dev, -0.3, 0.3, -0.18, 0.06)
            B["bar"](dev, -0.3, 0.1, -0.33, 0.06)


def p_magnifier():
    """Search: a big magnifying glass standing on a cream foot; the lens shows two text lines."""
    c = Vector((-0.12, 0.0, 1.55))
    R = 0.62
    cyl(R, 0.08, tuple(c), "r", 0.02, rot=FACE)  # glass
    torus(R, 0.14, tuple(c), "p", rot=FACE)  # rim
    for dz, w in ((0.13, 0.62), (-0.13, 0.42)):  # magnified text on the glass
        x0 = c.x - 0.31
        prof = B["stroke_outline"]([(0, 0), (w, 0)], 0.13)
        plate(
            prof, 0.05, (x0, c.y - 0.04, c.z + dz), "k" if dz > 0 else "g", rot=FACE, edge=0.02, clean=True
        )  # the match, highlighted
    d = Vector((math.cos(D2R(-52)), 0, math.sin(D2R(-52))))
    s = c + d * (R + 0.1)
    e = Vector((0.55, 0.0, 0.3))
    cyl(0.2, 0.22, tuple(c + d * (R + 0.14)), "p", 0.05, rot=(-d).to_track_quat("Z", "Y").to_euler())  # collar
    tube([tuple(s + d * 0.15), tuple(e)], 0.13, "s")  # handle
    # base plate under the whole footprint (agy r11: a scene cable ends at the node's bounding box,
    # which began under the lens, so the pipe stopped in mid-air)
    # (agy r12: a flat plate read as a stray slab) -> one round pedestal the handle stands in
    cyl(0.86, 0.16, (-0.05, 0.0, 0.08), "s", 0.07)
    cyl(0.26, 0.14, (0.55, 0.0, 0.22), "p", 0.05)  # handle socket


def p_chalkboard():
    """Class: a chalkboard on an easel with 'a+b' (agy r10 blind: teacher/student roles unclear)."""
    for x in (-0.75, 0.75):  # legs
        box((0.1, 0.1, 1.9), (x, 0.12, 0.95), "s", 0.04, rot=(D2R(-6), 0, 0))
    dev = B["Device"](1.9, 1.35, 0.12, "p", screen=(0.12, 0.12, 0.12, 0.12), z0=0.75, bevel=0.06)
    x, y, z = dev.at(-0.36, 0.12, 0.0)
    B["text"]("a+b", 0.46, (x, y - 0.005, z), FACE, "g", 0.03)
    B["emboss"](dev, [(-0.36, -0.22), (0.2, -0.22)], 0.07, "g", 0.04)
    box((0.5, 0.12, 0.06), (0.35, dev.face - 0.04, 0.72), "c", 0.02)  # chalk ledge


PROPS = {
    "contract": p_contract,
    "contract-lock": lambda: p_contract("lock"),
    "contract-law": lambda: p_contract("check", True),
    "chart": p_chart,
    "checklist": p_checklist,
    "camera": p_camera,
    "audiofolder": p_audiofolder,
    "magnifier": p_magnifier,
    "sessions": p_sessions,
    "chalkboard": p_chalkboard,
}


OUTFITS = {
    "person": o_person,
    "person-red": lambda: o_person("p"),
    "patient": o_patient,
    "visitor": o_visitor,
    "adult-cap": o_adult_cap,
    "adult-bun": o_adult_bun,
    "doctor": o_doctor,
    "lawyer": o_lawyer,
    "student": o_student,
    "teacher": o_teacher,
    "parent": o_parent,
    "child": o_child,
    "child-b": o_child_b,
    "developer": o_developer,
    "client": o_client,
}
OUTFIT_SCALE = {"child": 0.75, "child-b": 0.75}


def doll(outfit, at=(0, 0, 0), turn=0.0, scale=1.0):
    """Build one doll standing on z=at[2] at (at[0], at[1]), turned `turn` degrees about Z.
    Returns its objects. Adds to the current scene; never resets it."""
    before = set(bpy.data.objects)
    (OUTFITS.get(outfit) or PROPS[outfit])()
    objs = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()  # matrix_world is stale for objects placed since the last update
    k = scale * OUTFIT_SCALE.get(outfit, 1.0)
    M = Matrix.Translation(Vector(at)) @ Matrix.Rotation(D2R(turn), 4, "Z") @ Matrix.Scale(k, 4)
    for o in objs:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    return objs


def lineup(names=None, gap=0.82, turn=18.0, scale=0.5):
    """All outfits in a row along the camera's right axis, each turned a little toward the camera.
    Built at half size: a full-size row reaches ~3 units toward the key light and the dolls there
    clip to white (area-light falloff). The framing/normalize step scales it back up anyway."""
    names = names or [n for n in OUTFITS if not n.startswith("person")]
    az = D2R(B["AZIMUTH"])
    right = Vector((math.cos(az), math.sin(az), 0))
    objs = []
    for i, n in enumerate(names):
        p = right * gap * scale * (i - (len(names) - 1) / 2)
        objs += doll(n, (p.x, p.y, 0), turn, scale)
    return objs


# ---------------------------------------------------------------- CLI preview
def _render(name, build, modes, out):
    B["CURRENT"] = name
    B["reset"]()
    build()
    B["light_and_camera"]()
    for mode in modes:
        B["paint"](mode)
        bpy.context.scene.render.filepath = f"{out}/{mode}/{name}.png"
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:  # GPU busy (other jobs hold VRAM): same image on CPU, just slower
            print(f"gpu failed ({e}); rendering on CPU")
            bpy.context.scene.cycles.device = "CPU"
            bpy.ops.render.render(write_still=True)
        print(f"ok   {mode}/{name}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    opts, names, i = {}, [], 0
    while i < len(argv):
        if argv[i].startswith("--"):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            names.append(argv[i])
            i += 1
    out = opts.get("out", "local/icons/rounds/25d-b8-dolls")
    mode = opts.get("mode", "both")
    modes = ["dark", "light"] if mode == "both" else [mode]
    names = names or [n for n in OUTFITS if n != "person-red"] + ["lineup"]
    for n in names:
        if n == "lineup":
            _render("doll-lineup", lineup, modes, out)
        else:
            _render(f"doll-{n}", lambda n=n: doll(n), modes, out)


if __name__ == "__main__":
    main()
