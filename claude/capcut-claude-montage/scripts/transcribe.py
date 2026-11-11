"""Speech to timed words, from the audio audio.py made.

    python scripts/transcribe.py "<project>"
    python scripts/transcribe.py "<project>" --language ar

Engine: ElevenLabs FIRST, always (unless config "engine" is "whisper"):
  ElevenLabs (recommended): Speech to Text, scribe_v2. Seconds, accurate, keeps English words in English inside Arabic.
    Needs ELEVENLABS_API_KEY in ~/.capcut-claude-montage/.env. If it can't be used, a box "ELEVENLABS NOT USED: <reason>"
    is printed with the fix (no key / no credits / bad key / no Speech to Text permission / busy / offline), then
    Whisper runs with a warning that it's less accurate and may need fixes.
  Whisper (free, this PC, faster-whisper) with the most accurate settings found in testing: beam search 5, silence
    skipped, no carry-over, anti-repetition, and a style example + vocabulary prompt (config "styleExample",
    "vocabulary") so English terms stay in English letters.

Writes work/<project>/transcript.json: {"engine", "language", "words": [{"text", "startMs", "endMs"}]}.
Then keeps an Arabic prefix and its English word together ("الـ" + "AI" -> "الـAI") and applies "spellings" from config.
"""
import argparse, json, os, sys, time, urllib.error, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import ENV_PATH, load_config, read_env, work_dir

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--engine", choices=["auto", "whisper", "elevenlabs"])
ap.add_argument("--language")
ap.add_argument("--model")
args = ap.parse_args()
cfg = load_config()
engine = args.engine or cfg.get("engine", "auto")
lang = args.language or cfg.get("language", "auto")
lang = None if lang in (None, "", "auto") else lang
wav = os.path.join(work_dir(args.project), "audio16k.wav")
if not os.path.exists(wav):
    raise SystemExit(f'No audio yet. Run first: python scripts/audio.py "{args.project}"')
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


PROBLEMS = {
    "no_key": "There's no ElevenLabs API key yet. For the fastest, most accurate captions, create one at elevenlabs.io "
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
FALLBACK = ("So this time Whisper runs on this PC instead (free), with the most accurate settings. Whisper is less "
            "accurate than ElevenLabs, so expect some words to need fixing: check the transcript before the captions.")


def whisper():
    try:
        from faster_whisper import WhisperModel
        import wave, numpy as np  # numpy comes with faster-whisper
    except ImportError:
        raise SystemExit("Whisper isn't installed: python -m pip install faster-whisper")
    model_name = args.model or cfg.get("whisperModel", "large-v3-turbo")
    print(f"Whisper {model_name} on the CPU (the first run downloads the model, once)...")
    with wave.open(wav, "rb") as w:  # our own 16 kHz mono file; read here so audio library version changes can't break it
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    prompt = " ".join(x for x in [cfg.get("styleExample", ""), ", ".join(vocab)] if x) or None
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(samples, language=lang, word_timestamps=True, beam_size=5, vad_filter=True,
                                      condition_on_previous_text=False, initial_prompt=prompt,
                                      repetition_penalty=1.2, no_repeat_ngram_size=3)
    words = [{"text": w.word.strip(), "startMs": round(w.start * 1000), "endMs": round(w.end * 1000)}
             for s in segments for w in (s.words or []) if w.word.strip()]
    return words, info.language, model_name


def elevenlabs(key):
    boundary = uuid.uuid4().hex
    fields = [("model_id", "scribe_v2"), ("timestamps_granularity", "word"), ("tag_audio_events", "false"), ("diarize", "false")]
    if lang:  # ISO 639-3, as used in testing ("ara" for Arabic)
        fields.append(("language_code", {"ar": "ara", "en": "eng", "fr": "fra", "es": "spa", "de": "deu", "tr": "tur"}.get(lang, lang)))
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
    words = [{"text": w["text"].strip(), "startMs": round(w["start"] * 1000), "endMs": round(w["end"] * 1000)}
             for w in j.get("words", []) if w.get("type") == "word" and w.get("start") is not None and w["text"].strip()]
    return words, j.get("language_code"), "scribe_v2"


t0 = time.time()
used, problem, detail, note = "elevenlabs", None, "", ""
if engine == "whisper":  # the user chose Whisper on purpose
    used = "whisper"
    words, detected, model = whisper()
else:  # ElevenLabs first, always
    try:
        key = read_env("ELEVENLABS_API_KEY")
        if not key:
            raise ElevenLabsProblem("no_key")
        words, detected, model = elevenlabs(key)
    except ElevenLabsProblem as e:
        problem, detail = e.kind, e.detail
    except Exception as e:  # anything unexpected: never leave the user stuck
        problem, detail = "other", str(e)
    if problem:
        note = PROBLEMS[problem] + (f" ({detail[:200]})" if detail else "") + " " + FALLBACK
        print("\n" + "=" * 70 + "\nELEVENLABS NOT USED: " + problem.upper().replace("_", " ") + "\n" + note + "\n" + "=" * 70 + "\n")
        used = "whisper"
        words, detected, model = whisper()

# Keep an Arabic prefix with the next word, and apply the user's spellings
PREFIX = {"الـ", "للـ", "بـ", "لـ", "فالـ", "والـ"}
spell = {k.lower(): v for k, v in cfg.get("spellings", {}).items()}
out = []
for w in words:
    core = w["text"].rstrip("،؛؟,.?!")
    mark = w["text"][len(core):]
    w["text"] = spell.get(core.lower(), core) + mark
    if out and out[-1]["text"] in PREFIX:
        out[-1]["text"] += w["text"]
        out[-1]["endMs"] = w["endMs"]
        continue
    out.append(w)

path = os.path.join(work_dir(args.project), "transcript.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump({"engine": used, "model": model, "language": detected, "elevenlabsProblem": problem, "note": note,
               "words": out}, fh, ensure_ascii=False, indent=1)
print(f"{used} ({model}), language {detected}: {len(out)} words in {time.time() - t0:.0f} s -> {path}")
print("Text:", " ".join(w["text"] for w in out))
