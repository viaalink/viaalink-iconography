"""Animate a saved diagram or scene (W-140, owner: "animations, GIFs, small videos for the product videos").

  blender -b local/icons/diagrams/<name>/<name>.blend -P scripts/icons/blender/animate.py -- --out <dir> [--frames 96] [--fps 24] [--samples 24] [--scale 50]
        [--camera none|push|orbit] [--webm]
  (just icons-animate <name>)

Film clips (owner 2026-11-12: "use Blender to animate the 3D objects and use that in the video
package"): --camera push (slow dolly in) or orbit (a slow quarter-ish turn of the camera round the
board), one way over the clip, so the clip plays once and holds; packets still loop. --webm also
writes <name>.webm (VP9, for the film's Chromium, which has no H.264) and labels-anim.json: every
label of labels.json re-projected per frame (needs the "w" world point the diagram render writes),
so the film draws the labels as crisp HTML that follows the camera.

Every diagram/scene render saves a .blend with named objects. Here the packets (the cream spheres on
the pipes) travel along their pipe in the direction of the pipe's arrow, two per pipe, looping
seamlessly; a pipe's arrow cone stays where it is. Frames go to <out>/frames/, then ffmpeg makes
<out>/<name>.mp4 (H.264) and <out>/<name>.gif (palette, loops). Light edition (the .blend is saved
after the light pass).
"""
import math
import os
import subprocess
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def opt(k, d):
    return argv[argv.index(f"--{k}") + 1] if f"--{k}" in argv else d


OUT = opt("out", "local/icons/anim")
FRAMES = int(opt("frames", "96"))
FPS = int(opt("fps", "24"))
SAMPLES = int(opt("samples", "24"))
SCALE = int(opt("scale", "50"))
CAMERA = opt("camera", "none")
PERIOD = int(opt("period", str(FRAMES)))  # frames per packet trip; FRAMES (default) = seamless loop
WEBM = "--webm" in argv
NAME = os.path.splitext(os.path.basename(bpy.data.filepath))[0]

scene = bpy.context.scene
objs = bpy.data.objects
tubes = [o for o in objs if o.type == "CURVE" and o.name.startswith("tube")]
packets = [o for o in objs if o.type == "MESH" and o.name.startswith("Sphere")]
cones = [o for o in objs if o.type == "MESH" and o.name.startswith("Cone")]


def polyline(o):
    pts = []
    for sp in o.data.splines:
        src = sp.points if len(sp.points) else sp.bezier_points
        for p in src:
            co = p.co
            pts.append(o.matrix_world @ Vector((co[0], co[1], co[2])))
    return pts


def project(pts, q):
    """Arc-length position of the point on the polyline nearest to q, and the total length."""
    best, acc, at = 1e9, 0.0, 0.0
    for a, b in zip(pts, pts[1:]):
        ab = b - a
        L = ab.length
        t = 0.0 if L == 0 else max(0.0, min(1.0, (q - a).dot(ab) / (L * L)))
        d = (a + ab * t - q).length
        if d < best:
            best, at = d, acc + L * t
        acc += L
    return best, at, acc


def point_at(pts, s):
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        if s <= L:
            return a.lerp(b, 0 if L == 0 else s / L)
        s -= L
    return pts[-1]


scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = FPS
moved = 0
for k, tb in enumerate(tubes):
    pts = polyline(tb)
    if len(pts) < 2:
        continue
    # this pipe's packet and arrow: the nearest of each to the polyline
    pk = min(packets, key=lambda o: project(pts, o.matrix_world.translation)[0], default=None)
    if pk is None or project(pts, pk.matrix_world.translation)[0] > 0.3:
        continue
    cn = min(cones, key=lambda o: project(pts, o.matrix_world.translation)[0], default=None)
    _, s_pk, total = project(pts, pk.matrix_world.translation)
    if cn is not None and project(pts, cn.matrix_world.translation)[1] < s_pk:
        pts = pts[::-1]  # flow runs toward the arrow
    _, _, total = project(pts, pts[0])
    riders = [pk, pk.copy()]
    riders[1].data = pk.data
    scene.collection.objects.link(riders[1])
    for j, r in enumerate(riders):
        r.animation_data_clear()
        for f in range(1, FRAMES + 1):
            u = ((f - 1) / PERIOD + j / len(riders) + k * 0.13) % 1.0
            r.location = point_at(pts, u * total)
            r.keyframe_insert("location", frame=f)
        for fc in r.animation_data.action.fcurves if r.animation_data.action and hasattr(r.animation_data.action, "fcurves") else []:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    moved += 1

cam = scene.camera
FIT = float(opt("fit", "0"))  # >0: re-frame tightly for this aspect (film clip box, e.g. 2.26)
lab_file = os.path.join(os.path.dirname(bpy.data.filepath), "labels.json")
pre = {}  # label anchors projected with the still's camera, before any re-framing
if os.path.exists(lab_file):
    import json
    from bpy_extras.object_utils import world_to_camera_view
    for l in json.load(open(lab_file))["labels"]:
        if "w" in l:
            v = world_to_camera_view(scene, cam, Vector(l["w"]))
            pre[l["text"]] = (v.x, 1 - v.y)
old_scale, old_aspect = cam.data.ortho_scale, scene.render.resolution_x / scene.render.resolution_y
if FIT > 0:
    scene.render.resolution_y = int(round(scene.render.resolution_x / FIT / 4)) * 4  # even after scaling
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type in ("MESH", "CURVE", "FONT") and not o.hide_render for c in o.bound_box]
    R = cam.matrix_world.to_3x3()
    right, up, back = R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1))
    rs, us_ = [p.dot(right) for p in pts], [p.dot(up) for p in pts]
    mid = right * ((min(rs) + max(rs)) / 2) + up * ((min(us_) + max(us_)) / 2)
    cam.location = mid + back * (cam.location.dot(back))
    # room above for the labels over the tallest nodes
    cam.data.ortho_scale = max(max(rs) - min(rs), (max(us_) - min(us_) + 0.6) * FIT) * 1.04
    cam.location = cam.location + up * 0.3
if CAMERA in ("push", "orbit") and cam is not None:
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type in ("MESH", "CURVE", "FONT") and not o.hide_render for c in o.bound_box]
    centre = sum(pts, Vector()) / max(1, len(pts))
    loc0, rot0, scale0 = cam.location.copy(), cam.rotation_euler.copy(), cam.data.ortho_scale
    R = cam.matrix_world.to_3x3()
    back = R @ Vector((0, 0, 1))
    # the point the camera looks at: its axis through the board's height
    t = (centre - loc0).dot(-back)
    aim = loc0 - back * t
    for f in range(1, FRAMES + 1):
        e = (f - 1) / max(1, FRAMES - 1)
        e = e * e * (3 - 2 * e)  # ease in-out
        if CAMERA == "push":
            cam.data.ortho_scale = scale0 * (1.0 - 0.14 * e)
            cam.location = loc0 + (centre - aim) * 0.25 * e  # drift a little toward the middle
            cam.data.keyframe_insert("ortho_scale", frame=f)
            cam.keyframe_insert("location", frame=f)
        else:
            a = math.radians(-9 + 18 * e)
            Rz = Matrix.Rotation(a, 4, "Z")
            cam.location = aim + (Rz @ (loc0 - aim).to_4d()).to_3d()
            cam.rotation_euler = (Rz.to_3x3() @ rot0.to_matrix()).to_euler()
            cam.data.ortho_scale = scale0 * (1.0 - 0.06 * e)
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
            cam.data.keyframe_insert("ortho_scale", frame=f)

if WEBM and os.path.exists(lab_file):
    labs = [l for l in json.load(open(lab_file))["labels"] if "w" in l]
    # dx/dy: the still's screen offset of the label from its anchor (its layout pass moved it),
    # converted to this framing (ortho scale and aspect), so labels sit where the still has them
    sx = old_scale / cam.data.ortho_scale if FIT > 0 else 1.0
    new_aspect = scene.render.resolution_x / scene.render.resolution_y
    sy = sx * new_aspect / old_aspect
    track = [{"text": l["text"], "kind": l["kind"],
              "dx": round((l["x"] - pre[l["text"]][0]) * sx, 4), "dy": round((l["y"] - pre[l["text"]][1]) * sy, 4), "xy": []}
             for l in labs]
    for f in range(1, FRAMES + 1):
        scene.frame_set(f)
        for l, t_ in zip(labs, track):
            v = world_to_camera_view(scene, cam, Vector(l["w"]))
            t_["xy"].append([round(v.x, 4), round(1 - v.y, 4)])
    scene.frame_set(1)
    os.makedirs(OUT, exist_ok=True)
    json.dump({"fps": FPS, "frames": FRAMES, "aspect": scene.render.resolution_x / scene.render.resolution_y, "labels": track},
              open(f"{OUT}/labels-anim.json", "w"))

scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_percentage = SCALE
scene.render.film_transparent = True  # composited on the page cream below
W = scene.render.resolution_x * SCALE // 100 // 2 * 2  # even: H.264/VP9 need it
H = scene.render.resolution_y * SCALE // 100 // 2 * 2
os.makedirs(f"{OUT}/frames", exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = f"{OUT}/frames/f"
print(f"animate {NAME}: {moved} pipes, {FRAMES} frames")
bpy.ops.render.render(animation=True)

mp4, gif = f"{OUT}/{NAME}.mp4", f"{OUT}/{NAME}.gif"
pattern = f"{OUT}/frames/f%04d.png"
BG = opt("bg", "f4efe8")  # page cream (light edition)
on_bg = f"color=c=0x{BG}:s={W}x{H}:r={FPS}[bg];[bg][0:v]overlay=shortest=1:format=auto"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern, "-filter_complex",
                on_bg + ",format=yuv420p", "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart", mp4], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern, "-filter_complex",
                on_bg + ",fps=20,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
                "-loop", "0", gif], check=True)
if WEBM:
    webm = f"{OUT}/{NAME}.webm"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern, "-filter_complex",
                    on_bg + ",format=yuv420p", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30", "-row-mt", "1", "-deadline", "good", webm], check=True)
    print(f"ok   {webm}")
print(f"ok   {mp4} {gif}")
