"""Video or audio -> timed words, as accurate as possible.

    python scripts/transcribe.py "<video or audio file>"
    python scripts/transcribe.py "<file>" --engine whisper --language ar

Writes "<name> captions/words.json" next to the file. Then run build.py to make the caption files.

Engine: ElevenLabs FIRST, always (unless config "engine" is "whisper"):
  ElevenLabs (recommended): Speech to Text, model scribe_v2. Seconds, accurate, keeps English words in English inside
    Arabic. Needs ELEVENLABS_API_KEY in ~/.claude-captions/.env. If it can't be used, a box "ELEVENLABS NOT USED:
    <reason>" is printed with the fix (no key / no credits / bad key / no Speech to Text permission / busy / offline),
    then Whisper runs with a warning that it's less accurate and may need fixes.
  Whisper (free, this computer, faster-whisper). Tuned for accuracy:
    - clean audio: 16 kHz mono, low rumble removed, loudness evened out (quiet audio makes Whisper invent text)
    - the language is set, not guessed, when config has it
    - beam search 5, silence skipped (VAD), no carry-over between pieces (stops repeated or invented lines)
    - repetition penalty + no repeated 3-word runs (stops "اي اي اي اي" loops)
    - a STYLE EXAMPLE + vocabulary as the prompt: Whisper copies how that sentence is written, so English terms stay
      in English letters (tested: "البرومت" became "الـprompt", "الويبسايت" became "لـwebsite")
Every word gets a confidence; low ones are listed for the user to check.
"""
import argparse, json, math, os, subprocess, sys, time, urllib.error, urllib.request, uuid, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap_common import ENV_PATH, load_config, out_dir, read_env

ap = argparse.ArgumentParser()
ap.add_argument("media")
ap.add_argument("--engine", choices=["auto", "elevenlabs", "whisper"])
ap.add_argument("--language")
ap.add_argument("--model")
args = ap.parse_args()
cfg = load_config()
if not os.path.exists(args.media):
    raise SystemExit(f"File not found: {args.media}")
folder, base = out_dir(args.media)
lang = args.language or cfg["language"]
lang = None if lang in (None, "", "auto") else lang
engine = args.engine or cfg["engine"]
key = read_env("ELEVENLABS_API_KEY")

# ---- 1. clean audio
wav = os.path.join(folder, "audio16k.wav")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", args.media, "-vn",
                "-af", "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav], check=True)
with wave.open(wav, "rb") as w:
    seconds = w.getnframes() / w.getframerate()
print(f"Audio: {seconds:.1f} s")
vocab = [v for v in cfg.get("vocabulary", []) if v]


class ElevenLabsProblem(Exception):
    def __init__(self, kind, detail=""):
        super().__init__(kind)
        self.kind, self.detail = kind, detail


def classify(code, body):
    """ElevenLabs answers 401 both for a bad key and for no credits: the reason is in detail.status / detail.message."""
    status, message = "", body
    try:
        d = json.loads(body).get("detail", {})
        if isinstance(d, dict):
            status, message = d.get("status", ""), d.get("message", body)
        elif isinstance(d, str):
            message = d
    except (ValueError, AttributeError):
        pass
    low = f"{status} {message}".lower()
    if code == 402 or "quota" in low or "credit" in low or "insufficient" in low or "payment" in low:
        return "no_credits", message
    if "permission" in low or "speech_to_text" in low:
        return "no_permission", message
    if code == 401 or "invalid_api_key" in low or "api key" in low:
        return "bad_key", message
    if code == 429:
        return "busy", message
    return "other", f"{code}: {message}"


# What the user is told, per case. Claude repeats this to the user in plain words.
PROBLEMS = {
    "no_key": "There's no ElevenLabs API key yet. To get the fastest, most accurate captions, create one at elevenlabs.io "
              "(Developers > API keys, with Speech to Text allowed) and paste it yourself into " + ENV_PATH +
              " as ELEVENLABS_API_KEY=your-key (never in the chat).",
    "no_credits": "Your ElevenLabs account is out of credits. Add credits or upgrade at elevenlabs.io (Subscription), "
                  "or wait for your monthly credits to renew.",
    "bad_key": "ElevenLabs rejected the API key. Check it was pasted completely in " + ENV_PATH + ", or create a new key at "
               "elevenlabs.io (Developers > API keys).",
    "no_permission": "This ElevenLabs key isn't allowed to use Speech to Text. Edit the key at elevenlabs.io "
                     "(Developers > API keys) and turn Speech to Text on, or create a new key with it.",
    "busy": "ElevenLabs is busy right now (rate limit). Try again in a minute.",
    "offline": "Couldn't reach ElevenLabs (no internet, or the connection dropped). Check the connection and try again.",
    "other": "ElevenLabs returned an error.",
}
FALLBACK = ("So this time Whisper runs on this computer instead (free), with the most accurate settings. Whisper is less "
            "accurate than ElevenLabs, so expect some words to need fixing: check the transcript before using it.")


def elevenlabs():
    boundary = uuid.uuid4().hex
    fields = [("model_id", "scribe_v2"), ("timestamps_granularity", "word"), ("tag_audio_events", "false"), ("diarize", "false")]
    if lang:  # ISO 639-3 ("ara" worked in testing)
        fields.append(("language_code", {"ar": "ara", "en": "eng", "fr": "fra", "es": "spa", "de": "deu", "tr": "tur"}.get(lang, lang)))
    if cfg.get("elevenlabsKeyterms") and vocab:  # optional, costs extra per ElevenLabs
        fields += [("keyterms", v[:50]) for v in vocab[:1000]]
    body = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields)
    with open(wav, "rb") as fh:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio16k.wav"\r\n'
                 "Content-Type: audio/wav\r\n\r\n").encode() + fh.read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        raise ElevenLabsProblem(*classify(e.code, e.read().decode("utf-8", "replace")))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ElevenLabsProblem("offline", str(getattr(e, "reason", e)))
    words = [{"text": w["text"].strip(), "start": w["start"], "end": w["end"], "confidence": round(math.exp(w.get("logprob") or 0), 3)}
             for w in j.get("words", []) if w.get("type") == "word" and w.get("start") is not None and w["text"].strip()]
    return words, j.get("language_code"), "elevenlabs scribe_v2"


def whisper():
    try:
        from faster_whisper import WhisperModel
        import numpy as np
    except ImportError:
        raise SystemExit("Whisper isn't installed: python -m pip install faster-whisper")
    name = args.model or cfg["whisperModel"]
    print(f"Whisper {name} on the CPU (the first run downloads the model, once)...")
    with wave.open(wav, "rb") as w:  # read our own file here, so audio library version changes can't break it
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    prompt = " ".join(x for x in [cfg.get("styleExample", ""), ", ".join(vocab)] if x) or None
    model = WhisperModel(name, device="cpu", compute_type="int8")
    # repetition_penalty + no_repeat_ngram_size: stop Whisper looping on one word ("اي اي اي اي") and drifting into
    # formal Arabic at the end of a clip (tested on a 37 s Egyptian Arabic reel)
    segments, info = model.transcribe(samples, language=lang, word_timestamps=True, beam_size=5, vad_filter=True,
                                      condition_on_previous_text=False, initial_prompt=prompt,
                                      repetition_penalty=1.2, no_repeat_ngram_size=3)
    words = [{"text": w.word.strip(), "start": w.start, "end": w.end, "confidence": round(w.probability, 3)}
             for s in segments for w in (s.words or []) if w.word.strip()]
    return words, info.language, f"whisper {name}"


t0 = time.time()
note, problem, detail = "", None, ""
if engine == "whisper":  # the user chose Whisper on purpose
    words, detected, used = whisper()
else:  # ElevenLabs first, always
    try:
        if not key:
            raise ElevenLabsProblem("no_key")
        words, detected, used = elevenlabs()
    except ElevenLabsProblem as e:
        problem, detail = e.kind, e.detail
    except Exception as e:  # anything unexpected: never leave the user stuck
        problem, detail = "other", str(e)
    if problem:
        note = PROBLEMS[problem] + (f" ({detail[:200]})" if detail else "") + " " + FALLBACK
        print("\n" + "=" * 70 + "\nELEVENLABS NOT USED: " + problem.upper().replace("_", " ") + "\n" + note + "\n" + "=" * 70 + "\n")
        words, detected, used = whisper()

# ---- 2. clean up: user spellings, Arabic prefix + English word kept together ("الـ" + "AI" -> "الـAI")
spell = {k.lower(): v for k, v in cfg.get("spellings", {}).items()}
PREFIX = {"الـ", "للـ", "بـ", "لـ", "فالـ", "والـ"}
out = []
for w in words:
    core = w["text"].rstrip("،؛؟,.?!")
    w["text"] = spell.get(core.lower(), core) + w["text"][len(core):]
    if out and out[-1]["text"] in PREFIX:
        out[-1]["text"] += w["text"]
        out[-1]["end"] = w["end"]
        out[-1]["confidence"] = min(out[-1]["confidence"], w["confidence"])
        continue
    out.append(w)

low = [f'{w["text"]} ({w["start"]:.1f}s)' for w in out if w["confidence"] < 0.5]
result = {"file": os.path.abspath(args.media), "engine": used, "language": detected, "seconds": round(seconds, 2),
          "elevenlabsProblem": problem, "note": note, "words": out}
path = os.path.join(folder, "words.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1)
print(f"{used}, language {detected}: {len(out)} words in {time.time() - t0:.0f} s -> {path}")
print("Text:", " ".join(w["text"] for w in out))
print("Check these (low confidence):", ", ".join(low) if low else "none")
