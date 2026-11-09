"""Timed words -> caption files. Run after transcribe.py (and after fixing any wrong words in words.json).

    python scripts/build.py "<video or audio file>"
    python scripts/build.py "<file>" --preset video        up to 2 lines per caption (YouTube, landscape)

Writes next to the video, in "<name> captions/":
  <name>.srt         captions for any editor or platform (CapCut, Premiere, DaVinci, YouTube...)
  <name>.vtt         the same for web players
  <name>.words.json  every word with its own start and end, for word-by-word highlight styles
  <name>.txt         the plain transcript

Line rules (from real reels):
  - "reel": one short line, at most 5 words / 24 characters. "video": up to 2 lines of 42 characters.
  - break at punctuation and at pauses longer than 0.7 s; never one word alone on a line
  - Arabic: a line never STARTS with an English word (editors then lay the line out left to right and scramble the
    Arabic); each Arabic line starts with a right-to-left mark so players keep the order
  - a caption stays at least 0.7 s when there's room, and never overlaps the next one
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap_common import load_config, out_dir

ap = argparse.ArgumentParser()
ap.add_argument("media")
ap.add_argument("--preset", choices=["reel", "video"])
args = ap.parse_args()
cfg = load_config()
folder, base = out_dir(args.media)
src = os.path.join(folder, "words.json")
if not os.path.exists(src):
    raise SystemExit(f'No words yet. Run first: python scripts/transcribe.py "{args.media}"')
with open(src, encoding="utf-8") as fh:
    data = json.load(fh)
preset = args.preset or cfg.get("preset", "reel")
MAX_WORDS, MAX_CHARS, LINES = (5, 24, 1) if preset == "reel" else (14, 42, 2)
LATIN = re.compile(r"[A-Za-z]")
RLM = "‏"

def clean(t):
    t = re.sub(r"[،؛؟,.?!]+$", "", t.strip())
    return re.sub(r"^([وفب]?ال|لل)([A-Za-z])", r"\1ـ\2", t)  # "الAI" -> "الـAI"
words = [{"text": clean(w["text"]), "mark": bool(re.search(r"[،؛؟,.?!]$", w["text"].strip())), "start": w["start"], "end": w["end"]}
         for w in data["words"] if w["text"].strip()]
words = [w for w in words if w["text"]]
if not words:
    raise SystemExit("No words to caption.")
arabic = any(re.search(r"[؀-ۿ]", w["text"]) for w in words)
text_of = lambda ph: " ".join(x["text"] for x in ph)
limit = MAX_CHARS * LINES

# ---- phrases
phrases, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    nxt = words[i + 1] if i + 1 < len(words) else None
    size = len(text_of(cur + ([nxt] if nxt else [])))
    pause = nxt is not None and nxt["start"] - w["end"] > 0.7
    if not nxt or pause or ((w["mark"] or len(cur) >= MAX_WORDS or size > limit) and (len(cur) >= 2 or w["mark"] or size > limit)):
        phrases.append(cur)
        cur = []
tidy = []
for ph in phrases:  # never one word alone
    if len(ph) == 1 and tidy and len(text_of(tidy[-1] + ph)) <= limit + 4:
        tidy[-1] = tidy[-1] + ph
    elif len(ph) == 1 and tidy and len(tidy[-1]) >= 3:
        tidy.append([tidy[-1].pop()] + ph)
    else:
        tidy.append(ph)
phrases = tidy
if arabic:
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
    if len(text_of(ph)) <= limit + 4 or len(ph) < 4:
        return [ph]
    cuts = sorted(range(2, len(ph) - 1), key=lambda k: abs(len(text_of(ph[:k])) - len(text_of(ph[k:]))))
    k = next((k for k in cuts if not (arabic and LATIN.match(ph[k]["text"]))), None)
    return [ph] if k is None else split_long(ph[:k]) + split_long(ph[k:])
phrases = [p for ph in phrases for p in split_long(ph)]

def lines(ph):
    """Up to LINES lines, balanced, never starting a line with English in Arabic text."""
    t = text_of(ph)
    if LINES == 1 or len(t) <= MAX_CHARS or len(ph) < 2:
        out = [t]
    else:
        ks = sorted(range(1, len(ph)), key=lambda k: abs(len(text_of(ph[:k])) - len(text_of(ph[k:]))))
        k = next((k for k in ks if not (arabic and LATIN.match(ph[k]["text"]))), ks[0])
        out = [text_of(ph[:k]), text_of(ph[k:])]
    return [RLM + x if arabic and re.search(r"[؀-ۿ]", x) else x for x in out]

# ---- timing
cues = []
for i, ph in enumerate(phrases):
    start, end = ph[0]["start"], ph[-1]["end"] + 0.3
    nxt = phrases[i + 1][0]["start"] if i + 1 < len(phrases) else None
    end = max(end, start + 0.7)
    if nxt is not None:
        end = min(end, nxt)
    if data.get("seconds"):
        end = min(end, data["seconds"])  # never past the end of the video
    cues.append((start, max(end, start + 0.05), lines(ph)))

def ts(sec, sep):
    ms = int(round(sec * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"
with open(os.path.join(folder, f"{base}.srt"), "w", encoding="utf-8") as fh:
    for n, (a, b, ls) in enumerate(cues, 1):
        fh.write(f"{n}\n{ts(a, ',')} --> {ts(b, ',')}\n" + "\n".join(ls) + "\n\n")
with open(os.path.join(folder, f"{base}.vtt"), "w", encoding="utf-8") as fh:
    fh.write("WEBVTT\n\n")
    for a, b, ls in cues:
        fh.write(f"{ts(a, '.')} --> {ts(b, '.')}\n" + "\n".join(ls) + "\n\n")
with open(os.path.join(folder, f"{base}.words.json"), "w", encoding="utf-8") as fh:
    json.dump({"engine": data.get("engine"), "language": data.get("language"),
               "captions": [{"start": round(a, 3), "end": round(b, 3), "text": text_of(ph),
                             "words": [{"text": w["text"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in ph]}
                            for (a, b, _), ph in zip(cues, phrases)]}, fh, ensure_ascii=False, indent=1)
with open(os.path.join(folder, f"{base}.txt"), "w", encoding="utf-8") as fh:
    fh.write(" ".join(w["text"] for w in words) + "\n")
print(f"{len(cues)} captions ({preset}) -> {folder}")
for a, b, ls in cues[:6]:
    print(f"  {a:6.2f}-{b:6.2f}  " + " / ".join(x.replace(RLM, "") for x in ls))
