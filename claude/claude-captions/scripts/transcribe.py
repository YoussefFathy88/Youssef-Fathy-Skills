"""Video or audio -> timed words, as accurate as possible.

    python scripts/transcribe.py "<video or audio file>"
    python scripts/transcribe.py "<file>" --engine whisper --language ar

Writes "<name> captions/words.json" next to the file. Then run build.py to make the caption files.

Engine (config "engine", default "auto"):
  ElevenLabs (recommended): Speech to Text, model scribe_v2. Seconds, accurate, keeps English words in English inside
    Arabic. Used when ELEVENLABS_API_KEY is in ~/.claude-captions/.env. If it fails (key, credits, network), the reason
    is printed and Whisper runs instead.
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
        text = e.read().decode("utf-8", "replace")
        try:
            text = json.loads(text).get("detail", {}).get("message", text)
        except (ValueError, AttributeError):
            pass
        why = {401: "key rejected, or Speech to Text not allowed on this key", 402: "out of credits",
               403: "not allowed on this plan", 429: "busy / rate limit"}.get(e.code, "error")
        raise RuntimeError(f"ElevenLabs {e.code} ({why}): {text[:300]}")
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
note = ""
if engine in ("auto", "elevenlabs") and key:
    try:
        words, detected, used = elevenlabs()
    except Exception as e:  # never leave the user stuck
        note = f"ElevenLabs didn't work: {e}. Used Whisper instead."
        print(note)
        words, detected, used = whisper()
else:
    if engine == "elevenlabs":
        note = f"ElevenLabs was chosen but there's no ELEVENLABS_API_KEY in {ENV_PATH}. Used Whisper instead."
    elif engine == "auto":
        note = "No ElevenLabs key found, so Whisper was used (free). ElevenLabs is recommended for faster, more accurate captions."
    print(note)
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
          "note": note, "words": out}
path = os.path.join(folder, "words.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1)
print(f"{used}, language {detected}: {len(out)} words in {time.time() - t0:.0f} s -> {path}")
print("Text:", " ".join(w["text"] for w in out))
print("Check these (low confidence):", ", ".join(low) if low else "none")
