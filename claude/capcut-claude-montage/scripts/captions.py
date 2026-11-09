"""Word-by-word captions INTO the Edit copy, as normal CapCut text clips: the whole phrase shows, the spoken word in the
highlight colour. Style comes from config ("captions"). Running it again replaces only the skill's caption track.

    python scripts/captions.py "<project> Edit"
    python scripts/captions.py "<project> Edit" --y 1300        one-off position (pixels from the top)

Needs work/<project> Edit/transcript.json (audio.py + transcribe.py on the same project). The project must be closed.
A backup is saved first: python scripts/restore.py "<project> Edit" undoes it.
"""
import argparse, copy, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import (SKILL_DIR, Canvas, backup, clone_refs, hex_rgb, load_config, load_draft, new_id, new_track,
                        our_track, require_closed, save_draft, work_dir)

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--y", type=float)
args = ap.parse_args()
cfg = load_config()
st = cfg["captions"]
require_closed(args.project, cfg)
tpath = os.path.join(work_dir(args.project), "transcript.json")
if not os.path.exists(tpath):
    raise SystemExit(f'No transcript yet. Run audio.py and transcribe.py on "{args.project}" first.')
with open(tpath, encoding="utf-8") as fh:
    transcript = json.load(fh)
with open(os.path.join(SKILL_DIR, "templates", "text-template.json"), encoding="utf-8") as fh:
    tpl = json.load(fh)

d = load_draft(args.project, cfg)
cv = Canvas(d)
m = d["materials"]
COLOR, HIGHLIGHT, INK = hex_rgb(st["color"]), hex_rgb(st["highlight"]), hex_rgb(st["outline"])
SIZE, Y, FONT = st["size"], args.y if args.y is not None else st["y"], st["font"]
MAX_WORDS, MAX_CHARS = st["maxWords"], st["maxChars"]
LATIN = re.compile(r"[A-Za-z]")

def clean(w):
    w = re.sub(r"[،؛؟,.?!]+$", "", w.strip())
    return re.sub(r"^([وفب]?ال|لل)([A-Za-z])", r"\1ـ\2", w)  # "الAI" -> "الـAI"
words = [{"text": clean(w["text"]), "end_mark": bool(re.search(r"[،؛؟,.?!]$", w["text"].strip())),
          "start": w["startMs"] / 1000, "end": w["endMs"] / 1000} for w in transcript["words"] if w["text"].strip()]
words = [w for w in words if w["text"]]
if not words:
    raise SystemExit("The transcript has no words.")
arabic = any(re.search(r"[؀-ۿ]", w["text"]) for w in words)

# ---- phrases: short lines that end at punctuation or a size limit
text_of = lambda ph: " ".join(x["text"] for x in ph)
phrases, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    nxt = words[i + 1] if i + 1 < len(words) else None
    size = len(text_of(cur + ([nxt] if nxt else [])))
    pause = nxt and nxt["start"] - w["end"] > 0.7
    if not nxt or pause or ((w["end_mark"] or len(cur) >= MAX_WORDS or size > MAX_CHARS) and (len(cur) >= 2 or w["end_mark"] or size > MAX_CHARS)):
        phrases.append(cur)
        cur = []
# No word alone on a line
tidy = []
for ph in phrases:
    if len(ph) == 1 and tidy and len(text_of(tidy[-1] + ph)) <= MAX_CHARS + 4:
        tidy[-1] = tidy[-1] + ph
    elif len(ph) == 1 and tidy and len(tidy[-1]) >= 3:
        tidy.append([tidy[-1].pop()] + ph)
    else:
        tidy.append(ph)
phrases = tidy
if arabic:
    # A line that STARTS with an English word makes CapCut lay the whole line out left to right and scrambles the
    # Arabic, so it starts with the Arabic word before it instead.
    for prev, ph in zip(phrases, phrases[1:]):
        while ph and LATIN.match(ph[0]["text"]) and len(prev) >= 2:
            ph.insert(0, prev.pop())
    joined = []
    for ph in phrases:
        if joined and ph and LATIN.match(ph[0]["text"]) and len(joined[-1]) == 1:
            joined[-1] = joined[-1] + ph
        else:
            joined.append(ph)
    phrases = joined
phrases = [ph for ph in phrases if ph]
def split_long(ph):
    if len(text_of(ph)) <= MAX_CHARS + 4 or len(ph) < 4:
        return [ph]
    cuts = sorted(range(2, len(ph) - 1), key=lambda k: abs(len(text_of(ph[:k])) - len(text_of(ph[k:]))))
    k = next((k for k in cuts if not (arabic and LATIN.match(ph[k]["text"]))), None)
    return [ph] if k is None else split_long(ph[:k]) + split_long(ph[k:])
phrases = [part for ph in phrases for part in split_long(ph)]

# ---- one text clip per spoken word
def style(rgb, rng):
    return {"fill": {"content": {"render_type": "solid", "solid": {"color": rgb}}}, "font": {"path": FONT, "id": ""},
            "strokes": [{"content": {"render_type": "solid", "solid": {"color": INK}}, "width": st["outlineWidth"], "mode": 0}],
            "size": SIZE, "useLetterColor": True, "range": rng}
caps = []
for pi, ph in enumerate(phrases):
    text = text_of(ph)
    next_start = phrases[pi + 1][0]["start"] if pi + 1 < len(phrases) else ph[-1]["end"] + 0.3
    pos = 0
    for wi, w in enumerate(ph):
        a, b = pos, pos + len(w["text"])
        pos = b + 1
        until = ph[wi + 1]["start"] if wi + 1 < len(ph) else min(next_start, w["end"] + 0.6)
        s_t = cv.snap(w["start"])
        e_t = max(cv.snap(until), s_t + int(round(cv.frame)))
        styles = ([style(COLOR, [0, a])] if a else []) + [style(HIGHLIGHT, [a, b])] + ([style(COLOR, [b, len(text)])] if b < len(text) else [])
        mat = copy.deepcopy(tpl["material"])
        mat.update(id=new_id(), type="text", text_color=st["color"].lower(), font_size=float(SIZE), font_path=FONT,
                   content=json.dumps({"text": text, "styles": styles}, ensure_ascii=False))
        mat["words"] = {"start_time": [], "end_time": [], "text": []}
        mat["current_words"] = {"start_time": [], "end_time": [], "text": []}
        m.setdefault("texts", []).append(mat)
        seg = copy.deepcopy(tpl["segment"])
        seg.update(id=new_id(), material_id=mat["id"], raw_segment_id="",
                   source_timerange={"start": 0, "duration": e_t - s_t}, target_timerange={"start": s_t, "duration": e_t - s_t})
        clone_refs(seg, tpl["materials"], m)
        seg["clip"]["transform"] = {"x": 0.0, "y": cv.to_y(Y)}
        caps.append(seg)
for a, b in zip(caps, caps[1:]):  # never overlap on one track
    end_a = a["target_timerange"]["start"] + a["target_timerange"]["duration"]
    if end_a > b["target_timerange"]["start"]:
        a["target_timerange"]["duration"] = a["source_timerange"]["duration"] = b["target_timerange"]["start"] - a["target_timerange"]["start"]
dropped = {c["material_id"] for c in caps if not (c["target_timerange"]["duration"] > 0 and c["target_timerange"]["start"] < d["duration"])}
caps = [c for c in caps if c["material_id"] not in dropped]
m["texts"] = [t for t in m["texts"] if t["id"] not in dropped]  # no leftover text entries
last = caps[-1]  # captions must not make the video longer
if last["target_timerange"]["start"] + last["target_timerange"]["duration"] > d["duration"]:
    last["target_timerange"]["duration"] = last["source_timerange"]["duration"] = d["duration"] - last["target_timerange"]["start"]

# ---- replace the skill's previous caption track (if any), keep everything else the user did
backup(args.project, cfg, "captions")
old = our_track(d, "ccm-captions", "text")
if old:
    gone = {s["material_id"] for s in old["segments"]}
    m["texts"] = [t for t in m.get("texts", []) if t["id"] not in gone]
    d["tracks"].remove(old)
d["tracks"].append(new_track("text", "ccm-captions", caps))
save_draft(args.project, d, cfg)
print(f'"{args.project}": {len(phrases)} caption lines, {len(caps)} clips' + (" (replaced the previous captions)" if old else "") + ".")
for ph in phrases[:8]:
    print("  ", text_of(ph))
