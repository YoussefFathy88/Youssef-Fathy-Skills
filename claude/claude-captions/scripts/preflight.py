"""Checks what the skill needs before any transcription. Read-only: it changes nothing.

    python scripts/preflight.py

Lines are OK, FIX (must be fixed first), ASK (Claude asks the user) or INFO. Exit code 1 if any FIX.
"""
import importlib.util, os, platform, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap_common import ENV_PATH, load_config, read_env, user_set

cfg = load_config()
fixes = 0
def say(status, check, detail, fix=""):
    global fixes
    fixes += status == "FIX"
    print(f"{status:<5} {check}: {detail}")
    for line in fix.splitlines():
        print(f"      -> {line}")

py = sys.version_info
say("OK" if py >= (3, 9) else "FIX", "Python", platform.python_version(), "" if py >= (3, 9) else "Install Python 3.9 or newer: https://www.python.org/downloads/")
for tool in ("ffmpeg", "ffprobe"):
    if shutil.which(tool):
        say("OK", tool, "installed")
    else:
        say("FIX", tool, "missing", "Windows: winget install Gyan.FFmpeg | Mac: brew install ffmpeg | Linux: sudo apt install ffmpeg\n"
            "Then open a NEW terminal.")

key = read_env("ELEVENLABS_API_KEY")
engine = cfg["engine"]
whisper_ok = importlib.util.find_spec("faster_whisper") is not None
if key:
    say("OK", "ElevenLabs", "key found (recommended engine: fast and accurate; tested on the first transcription)")
else:
    say("INFO" if engine != "elevenlabs" else "FIX", "ElevenLabs", "no key",
        "Recommended for the best captions (seconds, more accurate, keeps English words in English inside Arabic).\n"
        "Create a key at https://elevenlabs.io (Developers > API keys) with Speech to Text allowed, then paste it\n"
        f"YOURSELF into {ENV_PATH} as: ELEVENLABS_API_KEY=your-key   (never paste the key in the chat).\n"
        "Without it, the skill uses Whisper on this computer (free).")
if whisper_ok:
    say("OK", "Whisper", f"installed (model {cfg['whisperModel']}; downloads once on first use)")
else:
    say("FIX" if not key else "INFO", "Whisper", "not installed",
        "python -m pip install faster-whisper\n(Free, runs on this computer. Needed when there's no ElevenLabs key, and as the backup.)")
if not user_set("engine") and not key:
    say("ASK", "Engine", "first run",
        "Ask the user: set up ElevenLabs now (recommended), or start with free Whisper?")
if (not key or engine == "whisper") and not cfg.get("styleExample"):
    say("ASK", "Whisper accuracy", "no style example yet",
        "Ask the user for one sentence written exactly how captions should look, in their language and with their\n"
        "English terms (e.g. 'خد الـprompt ده وابعته لـChatGPT'), and the names/terms they say often. Save them in config.")

print()
print("READY" if not fixes else f"NOT READY: {fixes} thing(s) to fix first")
sys.exit(1 if fixes else 0)
