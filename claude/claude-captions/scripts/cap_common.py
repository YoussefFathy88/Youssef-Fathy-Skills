"""Shared helpers for claude-captions: settings, the optional ElevenLabs key, and where files go."""
import copy, json, os, sys

if hasattr(sys.stdout, "reconfigure"):  # Arabic and other scripts in the console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Settings and the key live outside the skill folder, so they survive skill updates. CAPTIONS_HOME overrides it (testing).
HOME = os.environ.get("CAPTIONS_HOME") or os.path.join(os.path.expanduser("~"), ".claude-captions")
CONFIG_PATH = os.path.join(HOME, "config.json")
ENV_PATH = os.path.join(HOME, ".env")

DEFAULTS = {
    "engine": "auto",                 # auto = ElevenLabs if a key is found, else Whisper. Or "elevenlabs" / "whisper".
    "language": "auto",               # "auto", or a code like "ar", "en", "fr". Setting it is more accurate than auto.
    "whisperModel": "large-v3-turbo", # tiny, base, small, medium, large-v3-turbo, large-v3: bigger = more accurate, slower
    "styleExample": "",               # one sentence written exactly how captions should look (Whisper copies the style)
    "vocabulary": [],                 # names and terms you say often: ["Claude", "ChatGPT", "CV", "prompt"]
    "elevenlabsKeyterms": False,      # also send "vocabulary" to ElevenLabs as key terms (costs extra per ElevenLabs)
    "spellings": {},                  # fixes applied after transcription: {"superbase": "Supabase"}
    "preset": "reel",                 # "reel": 1 short line (vertical videos) / "video": up to 2 lines (YouTube, landscape)
}


def load_config():
    cfg = copy.deepcopy(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    return cfg


def user_set(key):
    if not os.path.exists(CONFIG_PATH):
        return False
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return key in json.load(fh)


def read_env(name):
    if os.environ.get(name):
        return os.environ[name]
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8-sig") as fh:
            for line in fh:
                k, _, v = line.strip().partition("=")
                if k.strip() == name and v.strip():
                    return v.strip().strip('"').strip("'")
    return None


def out_dir(media):
    """Everything for one video goes in "<video name> captions" next to the video."""
    base = os.path.splitext(os.path.basename(media))[0]
    p = os.path.join(os.path.dirname(os.path.abspath(media)), f"{base} captions")
    os.makedirs(p, exist_ok=True)
    return p, base
