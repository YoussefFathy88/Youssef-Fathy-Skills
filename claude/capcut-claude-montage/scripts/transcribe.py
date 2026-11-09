"""Speech to timed words, from the audio audio.py made.

    python scripts/transcribe.py "<project>"                    uses "engine" from config (default: whisper)
    python scripts/transcribe.py "<project>" --engine elevenlabs
    python scripts/transcribe.py "<project>" --language ar

Engines:
  whisper     free, runs on this PC (faster-whisper). The model downloads once. Slower on long videos.
  elevenlabs  ElevenLabs Speech to Text (scribe_v2): seconds instead of minutes, more accurate. Needs ELEVENLABS_API_KEY
              in ~/.capcut-claude-montage/.env and uses the account's credits. If it fails, Whisper runs instead and the
              reason is printed.

Writes work/<project>/transcript.json: {"engine", "language", "words": [{"text", "startMs", "endMs"}]}.
Then keeps an Arabic prefix and its English word together ("الـ" + "AI" -> "الـAI") and applies "spellings" from config.
"""
import argparse, json, os, sys, time, urllib.error, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import load_config, read_env, work_dir

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--engine", choices=["whisper", "elevenlabs"])
ap.add_argument("--language")
ap.add_argument("--model")
args = ap.parse_args()
cfg = load_config()
engine = args.engine or cfg.get("engine", "whisper")
lang = args.language or cfg.get("language", "auto")
lang = None if lang in (None, "", "auto") else lang
wav = os.path.join(work_dir(args.project), "audio16k.wav")
if not os.path.exists(wav):
    raise SystemExit(f'No audio yet. Run first: python scripts/audio.py "{args.project}"')


def whisper():
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("Whisper isn't installed: python -m pip install faster-whisper")
    model_name = args.model or cfg.get("whisperModel", "medium")
    print(f"Whisper {model_name} on the CPU (first run downloads the model)...")
    import wave, numpy as np  # numpy comes with faster-whisper
    with wave.open(wav, "rb") as w:  # our own 16 kHz mono 16-bit file; read it here so PyAV version changes can't break it
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(samples, language=lang, word_timestamps=True, beam_size=1)
    words = [{"text": w.word.strip(), "startMs": round(w.start * 1000), "endMs": round(w.end * 1000)}
             for s in segments for w in (s.words or []) if w.word.strip()]
    return words, info.language, model_name


def elevenlabs():
    key = read_env("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("no ELEVENLABS_API_KEY in ~/.capcut-claude-montage/.env")
    boundary = uuid.uuid4().hex
    fields = {"model_id": "scribe_v2", "timestamps_granularity": "word", "tag_audio_events": "false", "diarize": "false"}
    if lang:  # ISO 639-3, as used in testing ("ara" for Arabic)
        fields["language_code"] = {"ar": "ara", "en": "eng", "fr": "fra", "es": "spa", "de": "deu", "tr": "tur"}.get(lang, lang)
    body = b""
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    with open(wav, "rb") as fh:
        audio = fh.read()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio16k.wav"\r\n'
             f"Content-Type: audio/wav\r\n\r\n").encode() + audio + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        try:
            text = json.loads(text).get("detail", {}).get("message", text)
        except (ValueError, AttributeError):
            pass
        # 401 also means a valid key WITHOUT the Speech to Text permission
        why = {401: "key rejected, or Speech to Text not allowed on this key", 402: "out of credits",
               403: "not allowed on this plan", 429: "busy / rate limit"}.get(e.code, "error")
        raise RuntimeError(f"ElevenLabs {e.code} ({why}): {text[:300]}")
    words = [{"text": w["text"].strip(), "startMs": round(w["start"] * 1000), "endMs": round(w["end"] * 1000)}
             for w in j.get("words", []) if w.get("type") == "word" and w.get("start") is not None and w["text"].strip()]
    return words, j.get("language_code"), "scribe_v2"


t0 = time.time()
used = engine
if engine == "elevenlabs":
    try:
        words, detected, model = elevenlabs()
    except Exception as e:  # network, key, credits: never leave the user stuck
        print(f"ElevenLabs didn't work: {e}\nFalling back to Whisper on this PC.")
        used = "whisper"
        words, detected, model = whisper()
else:
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
    json.dump({"engine": used, "model": model, "language": detected, "words": out}, fh, ensure_ascii=False, indent=1)
print(f"{used} ({model}), language {detected}: {len(out)} words in {time.time() - t0:.0f} s -> {path}")
print("Text:", " ".join(w["text"] for w in out)[:400])
