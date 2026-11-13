"""Story animation of a saved diagram (W-140, owner 2026-11-12: "not impressed by how we animated it").

  blender -b local/icons/diagrams/<name>/<name>.blend -P scripts/icons/blender/story.py -- \
      --story scripts/icons/blender/stories/<name>.json --out <dir> [--samples 10] [--scale 60] [--fit 2.26]
  (just icons-story <name>)

Instead of a drifting camera over a finished board, the diagram is TOLD:
  - nodes pop in one by one (scale from 0 with a small overshoot), in the order of the story;
  - pipes draw themselves from source to target (curve bevel_factor_end 0 -> 1), their collars and
    arrow pop in when the pipe arrives;
  - from "flow" on, packets ride every live pipe from source to target;
  - "fail" makes a node sink and fade out of the story: its pipes retract and stop carrying packets,
    while the others keep flowing (zero downtime, shown);
  - the camera frames the beats (a list of focus node sets) and eases between them.
The board is there from the first frame. Frames -> <out>/<name>.webm (VP9, for the film's Chromium) +
.mp4, and labels-anim.json: per label its per-frame screen position plus the frames it is on screen
(a node's label appears with the node and leaves with a failed node; an edge label with its pipe).

Story spec (JSON, times in seconds):
  {"diagram": "relay-ha", "seconds": 12,
   "beats": [{"at": 0.2, "node": "web"}, {"at": 0.6, "edge": "web>modem"}, {"at": 5, "flow": true},
             {"at": 8, "fail": "r2"}],
   "camera": [{"at": 0, "focus": ["web", "modem"]}, {"at": 3.5, "focus": "all"}]}
"""

import json
import math
import os
import subprocess
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # scripts/icons
import theme  # noqa: E402  (the one theme loader, scripts/icons/theme.py)

THEME = theme.load()
argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def opt(k, d):
    return argv[argv.index(f"--{k}") + 1] if f"--{k}" in argv else d


def read_json(path):
    with open(path) as f:
        return json.load(f)


STORY = read_json(opt("story", ""))
OUT = opt("out", "local/icons/anim/story")
FPS = int(opt("fps", str(THEME["animation"]["fps"])))
SAMPLES = int(opt("samples", str(THEME["animation"]["storySamples"])))
SCALE = int(opt("scale", "60"))
FIT = float(opt("fit", "2.26"))
FRAMES = int(STORY.get("seconds", 10) * FPS)
NAME = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
_spec = f"scripts/icons/blender/diagrams/{STORY['diagram']}.json"
SPEC = read_json(_spec if os.path.exists(_spec) else f"scripts/icons/blender/scenes/{STORY['diagram']}.json")


def auto_story(spec, seconds):
    """No hand-written beats: nodes pop in spec order, each pipe draws once both ends are there,
    packets start when everything stands, the camera goes from the first nodes to the whole board."""
    beats, t, seen = [], 0.2, {}
    # the build is over by ~2.8 s: a film line can be as short as ~3.5 s (owner: show the point in time)
    gap = min(0.3, 2.4 / max(1, len(spec["nodes"])))
    edges = [e for e in spec.get("edges", []) if not (len(e) > 2 and e[2].get("style") in ("speech", "face"))]
    for n in spec["nodes"]:
        beats.append({"at": round(t, 2), "node": n["id"]})
        seen[n["id"]] = t
        for e in edges:
            a, b = e[0], e[1]
            if n["id"] in (a, b) and a in seen and b in seen:
                beats.append({"at": round(t + 0.3, 2), "edge": f"{a}>{b}"})
        t += gap
    beats.append({"at": round(t + 0.4, 2), "flow": True})
    first = [n["id"] for n in spec["nodes"][:3]]
    return beats, [{"at": 0, "focus": first}, {"at": 2.0, "focus": "all"}]


if "beats" not in STORY:
    STORY["beats"], cam_auto = auto_story(SPEC, STORY.get("seconds", 10))
    STORY.setdefault("camera", cam_auto)
STORY["beats"] = STORY["beats"] + STORY.get("extra", [])  # e.g. a grow or pulse on top of the auto beats

scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = FPS
F = lambda t: max(1, int(round(t * FPS)) + 1)  # seconds -> frame

node_ids = [n["id"] for n in SPEC["nodes"]]
groups = {i: [] for i in node_ids}
edges = {}
for o in list(bpy.data.objects):
    head = o.name.split(".", 1)[0]
    if head in groups:
        groups[head].append(o)
    elif o.name.startswith("edge."):
        key = o.name.split(".", 2)[1]
        edges.setdefault(key, []).append(o)


def renderable(objs):
    return [o for o in objs if o.type in ("MESH", "CURVE", "FONT") and not o.hide_render]


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in renderable(objs) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def rig(objs, name):
    """An empty at the base centre of a set of objects, parenting its roots: scale/sink it as one."""
    lo, hi = bounds(objs)
    bpy.ops.object.empty_add(location=((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    e = bpy.context.object
    e.name = f"rig.{name}"
    bpy.context.view_layer.update()
    for o in objs:
        if o.parent is None:
            mw = o.matrix_world.copy()
            o.parent = e
            o.matrix_parent_inverse = e.matrix_world.inverted()
            o.matrix_world = mw
    return e


def key_scale(e, frames_values):
    for f, v in frames_values:
        e.scale = (v, v, v)
        e.keyframe_insert("scale", frame=f)


def key_scale3(e, frames_xyz):
    for f, xyz in frames_xyz:
        e.scale = xyz
        e.keyframe_insert("scale", frame=f)


def pop(e, t, dur=0.5):
    """Drop in with squash and stretch: tall and thin while growing, a soft squash on landing, settle."""
    f0, n = F(t), int(dur * FPS)
    key_scale3(
        e,
        [
            (1, (0.001,) * 3),
            (f0, (0.001,) * 3),
            (f0 + int(n * 0.45), (0.92, 0.92, 1.22)),
            (f0 + int(n * 0.7), (1.1, 1.1, 0.88)),
            (f0 + n, (1.0, 1.0, 1.0)),
        ],
    )


# ---- beats ----------------------------------------------------------------------------------
beats = sorted(STORY["beats"], key=lambda b: b["at"])
appear = {}  # node id -> time
drawn = {}  # edge key -> time
flow_at = next((b["at"] for b in beats if b.get("flow")), None)
failed = {b["fail"]: b["at"] for b in beats if b.get("fail")}
for b in beats:
    if "node" in b:
        appear[b["node"]] = b["at"]
    if "edge" in b:
        drawn[b["edge"]] = b["at"]

top0 = {}  # full-size bounds of nodes that fail (they are gone at the end)
for nid in failed:
    if groups.get(nid):
        lo, hi = bounds(groups[nid])
        top0[nid] = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z))
rigs = {}
for nid, objs in groups.items():
    if not objs:
        continue
    rigs[nid] = rig(objs, nid)
    pop(rigs[nid], appear.get(nid, 0.0))

# "grow": a node swells to show it gets stronger (Heyvia on stronger chips); "pulse": it beats
# every second from then on (a recurring cost)
for b in beats:
    if b.get("grow") in rigs:
        e, f0 = rigs[b["grow"]], F(b["at"])
        key_scale(
            e, [(f0, 1.0), (f0 + int(1.2 * FPS), b.get("to", 1.35)), (f0 + int(1.5 * FPS), b.get("to", 1.35) * 0.96)]
        )
    if b.get("pulse") in rigs:
        e, f = rigs[b["pulse"]], F(b["at"])
        while f + FPS <= FRAMES:
            key_scale(e, [(f, 1.0), (f + 5, 1.18), (f + 12, 1.0)])
            f += FPS

for nid, t in failed.items():  # sink, tilt and shrink out of the story
    e = rigs[nid]
    f0, f1 = F(t), F(t + 0.9)
    e.keyframe_insert("location", frame=f0)
    e.keyframe_insert("rotation_euler", frame=f0)
    loc = e.location.copy()
    e.location = loc - Vector((0, 0, 0.55))
    e.rotation_euler = (0.0, math.radians(14), 0.0)
    e.keyframe_insert("location", frame=f1)
    e.keyframe_insert("rotation_euler", frame=f1)
    e.location = loc
    e.rotation_euler = (0, 0, 0)
    key_scale(e, [(f0, 1.0), (f0 + 4, 1.1), (f1, 0.001)])


def polyline(o):
    pts = []
    for sp in o.data.splines:
        src = sp.points if len(sp.points) else sp.bezier_points
        for p in src:
            pts.append(o.matrix_world @ Vector((p.co[0], p.co[1], p.co[2])))
    return pts


def point_at(pts, s):
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        if s <= L:
            return a.lerp(b, 0 if L == 0 else s / L)
        s -= L
    return pts[-1]


edge_alive = {}  # edge key -> (from frame, to frame) during which packets ride
for key, objs in edges.items():
    a, b = key.split(">")
    t = drawn.get(key, max(appear.get(a, 0), appear.get(b, 0)) + 0.2)
    t_end = min([failed[x] for x in (a, b) if x in failed], default=None)
    tubes = [o for o in objs if o.type == "CURVE"]
    for tb in tubes:  # the pipe draws itself from its source; a pipe into a failed node retracts
        tb.data.bevel_factor_mapping_end = "SPLINE"
        for f, v in [(1, 0.0), (F(t), 0.0), (F(t + 0.6), 1.0)] + (
            [(F(t_end), 1.0), (F(t_end + 0.6), 0.0)] if t_end else []
        ):
            tb.data.bevel_factor_end = v
            tb.data.keyframe_insert("bevel_factor_end", frame=f)
    for o in objs:  # collars, arrow, the static packet: pop in when the pipe arrives
        if o.type != "MESH":
            continue
        if o.name.split(".")[2].startswith("Sphere"):  # the diagram's static packet: riders replace it
            o.hide_render = True
            continue
        s0 = o.scale.copy()
        for f, v in [(1, 0.001), (F(t + 0.45), 0.001), (F(t + 0.65), 1.0)] + (
            [(F(t_end), 1.0), (F(t_end + 0.4), 0.001)] if t_end else []
        ):
            o.scale = s0 * v
            o.keyframe_insert("scale", frame=f)
    if tubes and flow_at is not None:
        edge_alive[key] = (tubes[0], F(max(flow_at, t + 0.6)), F(t_end) if t_end else FRAMES + 1)

# packets: two per live pipe, source -> target, one trip per PERIOD frames
PERIOD = int(STORY.get("period", 2.0) * FPS)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, segments=24, ring_count=12)
proto = bpy.context.object
proto.name = "packet"
src_mat = next(
    (
        o.active_material
        for objs in edges.values()
        for o in objs
        if o.name.split(".")[2].startswith("Sphere") and o.active_material
    ),
    None,
)
if src_mat:
    proto.data.materials.append(src_mat)
proto.hide_render = True
arrivals = {}  # node id -> frames a packet arrives
for k, (key, (tb, f_on, f_off)) in enumerate(edge_alive.items()):
    pts = polyline(tb)
    if len(pts) < 2:
        continue
    total = sum((b - a).length for a, b in zip(pts, pts[1:]))
    target = key.split(">")[1]
    for j in range(2):
        # the rider and two trailing sparks (smaller, a few frames behind): a packet with a light trail
        for lag, size in ((0, 1.0), (2, 0.62), (4, 0.36)):
            r = proto.copy()
            r.name = f"rider.{key}.{j}.{lag}"
            scene.collection.objects.link(r)
            r.hide_render = False
            prev_u = None
            for f in range(1, FRAMES + 1):
                on = f_on + lag <= f < f_off
                u = (((f - lag - f_on) / PERIOD) + j * 0.5 + k * 0.17) % 1.0 if on else 0.0
                r.location = point_at(pts, u * total)
                v = size if on else 0.001
                r.scale = (v, v, v)
                r.keyframe_insert("location", frame=f)
                r.keyframe_insert("scale", frame=f)
                if lag == 0 and on and prev_u is not None and u < prev_u:  # wrapped: arrived at the target
                    arrivals.setdefault(target, []).append(f)
                prev_u = u if on else None

# arrival pulse: the receiving device gives a small bump when a packet lands (not while it pops in or fails)
for nid, fs in arrivals.items():
    if nid not in rigs:
        continue
    settle = F(appear.get(nid, 0) + 0.6)
    end = F(failed[nid]) - 2 if nid in failed else FRAMES - 4
    last = -99
    for f in sorted(fs):
        if f < settle or f + 6 > end or f - last < 10:
            continue
        key_scale3(rigs[nid], [(f, (1.0, 1.0, 1.0)), (f + 3, (1.06, 1.06, 0.95)), (f + 7, (1.0, 1.0, 1.0))])
        last = f

# ---- camera ---------------------------------------------------------------------------------
cam = scene.camera
scene.render.resolution_y = int(round(scene.render.resolution_x / FIT / 4)) * 4
R = cam.matrix_world.to_3x3()
right, up, back = R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1))
depth = cam.location.dot(back)


def frame_on(ids):
    objs = [o for i in ids for o in groups.get(i, [])]
    if not objs:
        return
    # the board under them too when framing all, so the whole island is in view
    if len(ids) == len(node_ids):
        objs = objs + [o for o in bpy.data.objects if o.name.startswith("plate")]
    pts = [o.matrix_world @ Vector(c) for o in renderable(objs) for c in o.bound_box]
    rs, us = [p.dot(right) for p in pts], [p.dot(up) for p in pts]
    w, h = max(rs) - min(rs), max(us) - min(us) + 0.6
    cam.location = right * ((min(rs) + max(rs)) / 2) + up * ((min(us) + max(us)) / 2 + 0.25) + back * depth
    # a close-up keeps room round its nodes (owner: the board was cut at the clip's edge)
    cam.data.ortho_scale = max(w, h * FIT) * (1.12 if len(ids) == len(node_ids) else 1.4)


# frame with every node at full size (rigs are at scale ~0 at frame 1)
scene.frame_set(FRAMES)
shots = []
for c in STORY.get("camera", [{"at": 0, "focus": "all"}]):
    ids = node_ids if c["focus"] == "all" else c["focus"]
    frame_on(ids)
    shots.append((F(c["at"]), cam.location.copy(), cam.data.ortho_scale))
for i, (f, loc, sc) in enumerate(shots):
    for ff in [f] if i == 0 else [f]:
        cam.location, cam.data.ortho_scale = loc, sc
        cam.keyframe_insert("location", frame=ff)
        cam.data.keyframe_insert("ortho_scale", frame=ff)
    if i + 1 < len(shots):  # hold, then ease to the next shot over 1.2 s
        nf = shots[i + 1][0]
        hold = max(f, nf - int(1.0 * FPS))
        cam.keyframe_insert("location", frame=hold)
        cam.data.keyframe_insert("ortho_scale", frame=hold)

# after the last shot the camera never stops: a slow push-in to the end of the clip
lf, lloc, lsc = shots[-1]
if FRAMES - lf > FPS:
    cam.location, cam.data.ortho_scale = lloc, lsc * 0.94
    cam.keyframe_insert("location", frame=FRAMES)
    cam.data.keyframe_insert("ortho_scale", frame=FRAMES)

# ---- labels ---------------------------------------------------------------------------------
lab_file = os.path.join(os.path.dirname(bpy.data.filepath), "labels.json")
labs = [l for l in read_json(lab_file)["labels"] if "w" in l] if os.path.exists(lab_file) else []
by_text = {}
for n in SPEC["nodes"]:
    if n.get("label"):
        by_text[n["label"].replace("\n", " ")] = ("node", n["id"])
for e in SPEC.get("edges", []):
    if len(e) > 2 and e[2].get("label"):
        by_text[e[2]["label"]] = ("edge", f"{e[0]}>{e[1]}")
track = []
for l in labs:
    kind, ref = by_text.get(l["text"], ("node", None))
    if kind == "node":
        on, off = F(appear.get(ref, 0) + 0.3), F(failed[ref]) if ref in failed else FRAMES + 1
    else:
        a, b = ref.split(">")
        on = F(drawn.get(ref, 0) + 0.6)
        off = min([F(failed[x]) for x in (a, b) if x in failed], default=FRAMES + 1)
    w = l["w"]
    if kind == "node" and ref in groups and groups[ref]:  # a node's label floats just above the node
        scene.frame_set(FRAMES)  # nodes at full size (unless failed: then it is gone by then anyway)
        if ref in failed:
            w = [top0[ref].x, top0[ref].y, top0[ref].z + 0.35]
        else:
            lo, hi = bounds(groups[ref])
            w = [(lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z + 0.35]
    track.append({"text": l["text"], "kind": l["kind"], "on": on, "off": off, "w": w, "xy": []})

for f in range(1, FRAMES + 1):
    scene.frame_set(f)
    for t in track:
        v = world_to_camera_view(scene, cam, Vector(t["w"]))
        t["xy"].append([round(v.x, 4), round(1 - v.y, 4)])
scene.frame_set(1)
os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/labels-anim.json", "w") as f:
    json.dump(
        {
            "fps": FPS,
            "frames": FRAMES,
            "aspect": scene.render.resolution_x / scene.render.resolution_y,
            "labels": [
                {
                    "text": t["text"],
                    "kind": t["kind"],
                    "on": t["on"],
                    "off": t["off"],
                    "dx": 0,
                    "dy": -0.02,
                    "xy": t["xy"],
                }
                for t in track
            ],
        },
        f,
    )

# ---- render ---------------------------------------------------------------------------------
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_percentage = SCALE
scene.render.film_transparent = True
W = scene.render.resolution_x * SCALE // 100 // 2 * 2
H = scene.render.resolution_y * SCALE // 100 // 2 * 2
os.makedirs(f"{OUT}/frames", exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = f"{OUT}/frames/f"
print(f"story {NAME}: {len(rigs)} nodes, {len(edges)} pipes, {len(edge_alive)} live, {FRAMES} frames")
bpy.ops.render.render(animation=True)

pattern = f"{OUT}/frames/f%04d.png"
BG = opt("bg", THEME["pages"]["video"].lstrip("#"))  # page cream (light edition)
on_bg = f"color=c=0x{BG}:s={W}x{H}:r={FPS}[bg];[bg][0:v]overlay=shortest=1:format=auto"
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(FPS),
        "-i",
        pattern,
        "-filter_complex",
        on_bg + ",format=yuv420p",
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "30",
        "-row-mt",
        "1",
        f"{OUT}/{NAME}.webm",
    ],
    check=True,
)
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(FPS),
        "-i",
        pattern,
        "-filter_complex",
        on_bg + ",format=yuv420p",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-movflags",
        "+faststart",
        f"{OUT}/{NAME}.mp4",
    ],
    check=True,
)
print(f"ok   {OUT}/{NAME}.webm {OUT}/{NAME}.mp4")
