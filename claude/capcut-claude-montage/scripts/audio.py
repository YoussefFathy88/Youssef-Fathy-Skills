"""The sound of a CapCut project's timeline, rebuilt from the original files, so the user never exports audio by hand.
FOR CAPTION TIMING ONLY: the real video always comes from the user's own export in CapCut.

    python scripts/audio.py "<project>"          writes ~/.capcut-claude-montage/work/<project>/audio16k.wav

Reads the project, never writes to it. Uses what was last SAVED in CapCut. Every clip with volume above 0 is placed at
its timeline time, speed changes included; compound clips are followed inside. Fades and effects are ignored.
"""
import argparse, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import load_config, load_draft, project_path, work_dir

CLEANUP = "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11"  # without it Whisper can return "??????" on quiet recordings

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--out")
args = ap.parse_args()
cfg = load_config()
root = load_draft(args.project, cfg)
folder = project_path(args.project, cfg)
out = args.out or os.path.join(work_dir(args.project), "audio16k.wav")
drafts = {m["id"]: m for m in root["materials"].get("drafts", [])}

known = {}
def has_audio(src):
    if src not in known:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", src],
                           capture_output=True, text=True)
        known[src] = bool(r.stdout.strip())
    return known[src]

def collect(draft, at, keep_from, keep_to, gain, speed):
    """Heard pieces: (file, source start s, source length s, tempo, volume, timeline start s)."""
    mats, pieces = draft["materials"], []
    by_id = {m["id"]: m for kind in ("videos", "audios") for m in mats.get(kind, [])}
    for track in draft["tracks"]:
        if track["type"] not in ("video", "audio"):
            continue
        for s in track["segments"]:
            volume = s.get("volume", 1) * gain
            if volume <= 0:
                continue
            start, length = s["target_timerange"]["start"], s["target_timerange"]["duration"]
            a, b = max(start, keep_from), min(start + length, keep_to)
            if a >= b:
                continue
            tempo = s.get("speed") or 1
            src_start = (s.get("source_timerange") or {}).get("start", 0) + (a - start) * tempo
            when = at + (a - keep_from) / speed
            mat = dict(by_id.get(s["material_id"], {}))
            path = mat.get("path") or ""
            if path.startswith("##_draftpath_placeholder_"):  # a file inside the project folder (e.g. a voiceover)
                path = os.path.join(folder, path.split("_##/", 1)[1])
            inner = next((drafts[r]["draft"] for r in s.get("extra_material_refs", []) if r in drafts and drafts[r].get("draft")), None)
            if inner:  # compound clip: follow its own timeline (its cached render is silent)
                pieces += collect(inner, when, src_start, src_start + (b - a) * tempo, volume, tempo * speed)
            elif path:
                if not os.path.exists(path):
                    raise SystemExit(f"Source file missing (moved or renamed?): {path}")
                if has_audio(path):
                    pieces.append((path, src_start / 1e6, (b - a) * tempo / 1e6, tempo * speed, volume, when / 1e6))
            elif mat:
                raise SystemExit(f"Can't find the file of a clip at {start / 1e6:.2f} s")
    return pieces

pieces = collect(root, 0, 0, root["duration"], 1, 1)
if not pieces:
    raise SystemExit("Nothing audible on this timeline.")
inputs, parts = [], []
for i, (src, start, length, tempo, volume, when) in enumerate(pieces):
    inputs += ["-ss", f"{start:.6f}", "-t", f"{length:.6f}", "-i", src]
    speedup = f"atempo={tempo:.6f}," if abs(tempo - 1) > 1e-6 else ""
    parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,{speedup}volume={volume:.4f},adelay={round(when * 1000)}:all=1[a{i}]")
total = root["duration"] / 1e6
mix = ("".join(f"[a{i}]" for i in range(len(pieces))) +
       f"amix=inputs={len(pieces)}:normalize=0:duration=longest,apad,atrim=0:{total:.6f},{CLEANUP},aresample=16000[out]")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(parts + [mix]),
                "-map", "[out]", "-ac", "1", "-c:a", "pcm_s16le", out], check=True)
print(f"{len(pieces)} clips, {total:.1f} s -> {out}")
