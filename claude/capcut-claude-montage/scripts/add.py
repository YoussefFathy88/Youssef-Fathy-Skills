"""Adds the user's own images and videos INTO the Edit copy, as normal CapCut clips they can still move or trim.

    python scripts/add.py "<project> Edit" --plan plan.json
    python scripts/add.py "<project> Edit" --plan plan.json --replace     first removes what add.py placed before

plan.json (times in seconds, positions in pixels on the canvas, 1080 x 1920 for a reel):
  {"items": [
     {"file": "C:/Users/me/Pictures/logo.png", "start": 3.2, "end": 5.0, "y": 1200, "height": 300},
     {"file": "C:/Users/me/Videos/demo.mp4",   "start": 10,  "end": 14,  "y": 960,  "height": 1920, "sound": false}
  ]}
  Optional per item: "x" (centre, default the middle), "allow": true (place it even over one of the user's B-rolls).

Refuses an item that would cover one of the user's own overlay clips (B-rolls) unless "allow" is set, and anything
inside an "avoid" box from config ([[x0, y0, x1, y1], ...], e.g. where the face usually is). The project must be
closed. A backup is saved first: restore.py undoes it.
"""
import argparse, copy, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import (Canvas, backup, clone_refs, load_config, load_draft, new_id, new_track, our_track,
                        require_closed, save_draft)

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--plan", required=True)
ap.add_argument("--replace", action="store_true")
args = ap.parse_args()
cfg = load_config()
require_closed(args.project, cfg)
with open(args.plan, encoding="utf-8") as fh:
    plan = json.load(fh)
here = os.path.dirname(os.path.abspath(args.plan))
items = plan.get("items", [])
if not items:
    raise SystemExit("The plan has no items.")
for x in items:
    x["file"] = os.path.abspath(os.path.join(here, x["file"])).replace("\\", "/")
    if not os.path.exists(x["file"]):
        raise SystemExit(f"File not found: {x['file']}")
    if not x["end"] > x["start"] >= 0:
        raise SystemExit(f"Bad times for {x['file']}: start {x['start']}, end {x['end']}")

d = load_draft(args.project, cfg)
cv = Canvas(d)
m = d["materials"]
videos = {v["id"]: v for v in m["videos"]}
FULL_CROP = {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0,
             "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0}
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def probe(path):
    if path.lower().endswith(IMAGE_EXT):
        from PIL import Image
        w, h = Image.open(path).size
        return "photo", w, h, 10_800_000_000, False
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    audio = any(s["codec_type"] == "audio" for s in j["streams"])
    return "video", v["width"], v["height"], int(float(j["format"]["duration"]) * 1e6), audio


def on_screen(seg):
    """Where one of the user's clips sits on the canvas (crop, fit, scale, position)."""
    mat = videos[seg["material_id"]]
    c = mat.get("crop") or {}
    pw = mat["width"] * (c.get("lower_right_x", 1) - c.get("upper_left_x", 0))
    ph = mat["height"] * (c.get("lower_right_y", 1) - c.get("upper_left_y", 0))
    f = min(cv.w / pw, cv.h / ph) * seg["clip"]["scale"]["x"]
    cx = cv.w / 2 + seg["clip"]["transform"]["x"] * cv.w / 2
    cy = cv.h / 2 - seg["clip"]["transform"]["y"] * cv.h / 2
    return cx - pw * f / 2, cy - ph * f / 2, cx + pw * f / 2, cy + ph * f / 2
overlap = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

video_tracks = [t for t in d["tracks"] if t["type"] == "video"]
if not video_tracks or not any(t["segments"] for t in video_tracks):
    raise SystemExit("This project has no video clips to work with.")
overlays = [s for t in video_tracks[1:] if t.get("name") != "ccm-media" for s in t["segments"]
            if s["material_id"] in videos and videos[s["material_id"]].get("path")]
avoid = cfg.get("avoid", [])

problems, placed = [], []
for x in items:
    kind, iw, ih, length, audio = probe(x["file"])
    height = x.get("height", min(ih, cv.h))
    width = iw * height / ih
    cx, cy = x.get("x", cv.w / 2), x["y"]
    box = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
    a, b = cv.snap(x["start"]), cv.snap(x["end"])
    if not x.get("allow"):
        if any(s["target_timerange"]["start"] < b and a < s["target_timerange"]["start"] + s["target_timerange"]["duration"]
               and overlap(box, on_screen(s)) for s in overlays):
            problems.append(f"{os.path.basename(x['file'])} at {x['start']:.2f} s covers one of your B-rolls")
            continue
        if any(overlap(box, z) for z in avoid):
            problems.append(f"{os.path.basename(x['file'])} at {x['start']:.2f} s is inside an \"avoid\" area")
            continue
    if kind == "video" and b - a > length:
        problems.append(f"{os.path.basename(x['file'])} is {length / 1e6:.1f} s long, shorter than its slot")
        continue
    placed.append((x, kind, iw, ih, length, audio, height, cx, cy, a, b))
if problems:
    raise SystemExit("Nothing written. Fix these (other spot or time), or add \"allow\": true after the user agrees:\n  " + "\n  ".join(problems))

# Clone a real clip from the user's own project: CapCut trusts clips shaped like its own. Prefer a plain overlay clip.
drafts = {x["id"] for x in m.get("drafts", [])}
plain = lambda s: s["material_id"] in videos and videos[s["material_id"]].get("path") and not any(r in drafts for r in s.get("extra_material_refs", []))
pool = [s for t in video_tracks[1:] for s in t["segments"] if plain(s)] or [s for t in video_tracks for s in t["segments"] if plain(s)]
if not pool:
    raise SystemExit("Couldn't find a plain video clip in this project to use as a model.")
tmpl_seg, tmpl_mat = pool[0], videos[pool[0]["material_id"]]


def clip(x, kind, iw, ih, length, audio, height, cx, cy, a, b):
    mat = copy.deepcopy(tmpl_mat)
    mat.update(id=new_id(), type=kind, path=x["file"], width=iw, height=ih, duration=length, material_name=os.path.basename(x["file"]),
               has_audio=audio, local_material_id="", crop_ratio="free", crop_scale=1.0, crop=copy.deepcopy(FULL_CROP))
    m["videos"].append(mat)
    seg = copy.deepcopy(tmpl_seg)
    sound = kind == "video" and audio and x.get("sound", False)
    seg.update(id=new_id(), material_id=mat["id"], volume=1.0 if sound else 0.0, last_nonzero_volume=1.0, speed=1.0,
               source_timerange={"start": 0, "duration": b - a}, target_timerange={"start": a, "duration": b - a})
    seg["render_timerange"] = {"start": 0, "duration": 0}
    for k in ("common_keyframes", "keyframe_refs"):
        if k in seg:
            seg[k] = []
    clone_refs(seg, m, m)
    s = height / (ih * min(cv.w / iw, cv.h / ih))
    seg["clip"].update(scale={"x": s, "y": s}, transform={"x": cv.to_x(cx), "y": cv.to_y(cy)}, rotation=0.0, alpha=1.0)
    return seg


backup(args.project, cfg, "add")
track = our_track(d, "ccm-media", "video")
if args.replace:
    gone = {s["material_id"] for t in d["tracks"] if t.get("name") == "ccm-media" for s in t["segments"]}
    m["videos"] = [v for v in m["videos"] if v["id"] not in gone]  # no leftover media entries
    d["tracks"] = [t for t in d["tracks"] if t.get("name") != "ccm-media"]
    track = None
new = sorted((clip(*p) for p in placed), key=lambda s: s["target_timerange"]["start"])
if track:
    segs = track["segments"] + new
else:
    segs = new
# Clips on one track must not overlap in time: put overlapping ones on extra tracks
lanes = []
for s in sorted(segs, key=lambda s: s["target_timerange"]["start"]):
    for lane in lanes:
        e = lane[-1]["target_timerange"]["start"] + lane[-1]["target_timerange"]["duration"]
        if e <= s["target_timerange"]["start"]:
            lane.append(s)
            break
    else:
        lanes.append([s])
d["tracks"] = [t for t in d["tracks"] if t.get("name") != "ccm-media"]
at = next((i for i, t in enumerate(d["tracks"]) if t["type"] == "text"), len(d["tracks"]))  # under the captions
for i, lane in enumerate(lanes):
    d["tracks"].insert(at + i, new_track("video", "ccm-media", lane))
save_draft(args.project, d, cfg)
print(f'"{args.project}": added {len(new)} item(s) on {len(lanes)} track(s). Your own clips are untouched.')
