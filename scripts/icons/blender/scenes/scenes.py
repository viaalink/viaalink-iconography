"""Generator for the desk-scene specs: python3 scripts/icons/blender/scenes/scenes.py [scene-name ...]
Writes scripts/icons/blender/scenes/*.json (W-140 scenes lane). Base template: a square desk read
left -> right on screen: speakers on the left and back corners, the recorder at the front, the result
at the right corner (iso grid: col runs down-right on screen, row down-left)."""

import json
import os
import sys

D = os.path.dirname(os.path.abspath(__file__)) + "/"


def doll(i, o, c, r, s=1.55):
    return {"id": i, "doll": o, "at": [c, r], "scale": s}


def icon(i, o, c, r, s):
    return {"id": i, "icon": o, "at": [c, r], "scale": s}


def prop(i, o, c, r, s):
    return {"id": i, "doll": o, "at": [c, r], "scale": s, "turn": 0}


SP = {"style": "speech"}
# spacing (screen units): a speaker's waves reach ~1.1 to its right, so back - left >= 1.7 and the
# phone sits in front of the back doll, low enough not to cover it
# owner (2026-11-11): the phone stands to the RIGHT of the speakers on screen (screen x ~ col - row), so
# the face-anchored waves open sideways from the mouth instead of down from the chin; the result goes
# further right. Import/search have no speakers and keep the old recorder spot (F0/RT0).
L, BK, F, RT = (0, 1.3), (0.05, -0.1), (1.2, 0.55), (2.4, -0.35)
F0, RT0 = (1.2, 1.2), (1.4, -0.15)
REC = icon("rec", "record", *F, 1.05)


def pair(a, b, result, talk_b=True):
    nodes = [doll("a", a, *L), doll("b", b, *BK), REC, result]
    return nodes, [["a", "rec", SP]] + ([["b", "rec", SP]] if talk_b else []) + [["rec", result["id"]]]


S = {}
S["scene-doctor"] = pair("doctor", "patient", prop("note", "chart", *RT, 0.9))
S["scene-lawyer"] = pair("lawyer", "visitor", prop("con", "contract-law", *RT, 0.98))
S["scene-kids"] = pair("child", "child-b", prop("con", "checklist", *RT, 0.92))
for n in S["scene-kids"][0][:2]:
    n["scale"] = 1.75  # agy r12: kids a bit bigger (still child proportions)
S["scene-contract"] = pair("adult-cap", "adult-bun", prop("con", "contract-lock", *RT, 0.98))
# r16 (owner): a parent-teacher talk about a child: teacher and parent face each other across the
# phone, the child small beside the parent; the minutes at the front right
S["scene-school"] = (
    [
        doll("t", "teacher", 0.0, 1.3),
        REC | {"at": [1.2, 0.55]},
        doll("p", "parent", 0.0, -0.1),
        doll("c", "child", -0.6, -0.45),
        icon("note", "report", 2.4, -0.35, 1.0),
    ],
    [["t", "rec", SP], ["p", "rec", SP], ["rec", "note"]],
)
# w4: the teacher stands beside the chalkboard on the student's side (not behind it);
# r16 (owner): the teacher speaks at the chalkboard; the student (mortarboard) sits nearest the
# phone with its back to us, facing the board: listener and recorder
S["scene-student"] = (
    [
        prop("board", "chalkboard", -0.55, -0.45, 1.0),
        doll("tea", "teacher", 0.2, -0.2),
        dict(doll("stu", "student", 0.0, 1.3), turn=203),
        REC | {"at": [1.2, 0.55]},
        icon("note", "report", 2.4, -0.4, 1.05),
    ],
    [["tea", "rec", SP], ["rec", "note"]],
)
S["scene-import"] = (
    [
        prop("cam", "camera", 0, 1.25, 0.95),
        prop("f", "audiofolder", -0.25, 0.15, 0.8),
        icon("tr", "transcribe", *F0, 1.05),
        icon("note", "report", *RT0, 1.05),
    ],
    [["cam", "tr"], ["f", "tr"], ["tr", "note"]],
)
# r16: the magnifier hovers over the sessions tray (it searches the kept sessions); the find goes right
S["scene-search"] = (
    [prop("a", "sessions", 0, 0.95, 1.0), prop("m", "magnifier", 1.45, 1.05, 1.0), icon("p", "report", *RT0, 1.1)],
    [["a", "p"]],
)
# Numbered step labels (owner): 1 who talks -> 2 what records -> 3 what it becomes. diagram.py writes
# them to local/icons/scenes/<name>/labels.json; the gallery lays them over the picture as HTML.
STEPS = {
    "scene-doctor": {"a": "1 They talk", "rec": "2 Phone records", "note": "3 Private notes"},
    "scene-lawyer": {"a": "1 They talk", "rec": "2 Phone records", "con": "3 Contract"},
    "scene-contract": {"a": "1 They agree", "rec": "2 Phone records", "con": "3 Private contract"},
    "scene-kids": {"a": "1 They promise", "rec": "2 Phone records", "con": "3 Promises kept"},
    "scene-school": {"t": "1 They talk", "rec": "2 Phone records", "note": "3 Same minutes"},
    "scene-student": {"tea": "1 Teacher talks", "rec": "2 Phone records", "note": "3 Student's notes"},
    "scene-import": {"cam": "1 Recordings", "tr": "2 Phone transcribes", "note": "3 Text"},
    "scene-search": {"a": "1 All sessions", "m": "2 Search", "p": "3 The answer"},
}
for name, labels in STEPS.items():
    for n in S[name][0]:
        if n["id"] in labels:
            n["label"] = labels[n["id"]]
            n["short"] = labels[n["id"]].split(" ")[0]  # tiles show just the step number

only = sys.argv[1:]
for name, (nodes, edges) in S.items():
    if only and name not in only:
        continue
    with open(D + name + ".json", "w") as f:
        json.dump(
            {"kind": "scene", "grid": 1.75, "foot": 1.7, "boardPad": 0.35, "nodes": nodes, "edges": edges},
            f,
            indent=1,
        )
