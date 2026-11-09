"""Checks everything the skill needs BEFORE any montage work. Read-only: it changes nothing on the PC.

    python scripts/preflight.py            all checks
    python scripts/preflight.py --quick    only what can change between runs (CapCut closed, version, key)
    python scripts/preflight.py --confirm-signed-in   records that the user confirmed they are signed in to CapCut

Each line is OK, FIX (must be fixed first), ASK (Claude asks the user) or WARN (can continue). Exit code 1 if any FIX.
"""
import argparse, glob, importlib.util, json, os, platform, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import (CONFIG_PATH, ENV_PATH, capcut_root, capcut_running, list_projects, load_config, projects_dir,
                        read_env, save_config)

TESTED = ("9.7",)  # CapCut desktop versions this skill was tested on

ap = argparse.ArgumentParser()
ap.add_argument("--quick", action="store_true")
ap.add_argument("--confirm-signed-in", action="store_true")
args = ap.parse_args()
cfg = load_config()
if args.confirm_signed_in:
    cfg["signedInConfirmed"] = True
    save_config(cfg)
    print("OK    saved: signed in to CapCut")
    sys.exit(0)

results = []
def say(status, check, detail, fix=""):
    results.append(status)
    print(f"{status:<5} {check}: {detail}")
    if fix:
        for line in fix.splitlines():
            print(f"      -> {line}")

# 1. Windows
if platform.system() != "Windows":
    say("FIX", "Windows", platform.system(), "This skill supports Windows only (Mac is not supported).")
    sys.exit(1)
say("OK", "Windows", platform.release())

# 2-3. CapCut desktop installed + version
apps = os.path.join(capcut_root(), "Apps")
versions = sorted((os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(apps, "*", "CapCut.exe"))),
                  key=lambda v: [int(x) for x in re.findall(r"\d+", v)])
if not versions:
    say("FIX", "CapCut desktop", f"not found in {apps}",
        "Install CapCut for Windows from the official site: https://www.capcut.com\nOpen it once, then run this check again.")
    sys.exit(1)
ver = versions[-1]
if any(ver.startswith(t + ".") or ver == t for t in TESTED):
    say("OK", "CapCut version", ver)
else:
    say("WARN", "CapCut version", f"{ver} (tested on {', '.join(TESTED)}.x)",
        "It may still work. The skill always works on a copy and keeps a backup, so your original is safe.")

# 4. Signed in (can't be checked without reading CapCut's account files, which this skill never does)
if cfg.get("signedInConfirmed"):
    say("OK", "Signed in to CapCut", "confirmed by you earlier")
elif not args.quick:
    say("ASK", "Signed in to CapCut", "please confirm",
        "Open CapCut: is your profile picture showing at the top? If not, click Sign in and log in inside CapCut.\n"
        "Never type your CapCut password in this chat. Recommended (needed for Pro effects), then run:\n"
        "python scripts/preflight.py --confirm-signed-in")

# 5-6. Projects exist and are readable
root = projects_dir(cfg)
projects = list_projects(cfg)
if not projects:
    say("FIX", "CapCut projects", f"none found in {root}",
        "Open CapCut, create or open a project, let it save, then close it and run this check again.\n"
        "If you moved CapCut's projects folder, set \"projectsDir\" in " + CONFIG_PATH)
else:
    name = projects[0][0]
    try:
        with open(os.path.join(root, name, "draft_content.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        ok = isinstance(d.get("tracks"), list) and isinstance(d.get("materials"), dict)
    except (UnicodeDecodeError, json.JSONDecodeError):
        ok = False
    if ok:
        say("OK", "CapCut projects", f"{len(projects)} found, readable (newest: \"{name}\")")
    else:
        say("FIX", "CapCut projects", f"\"{name}\" can't be read as plain JSON",
            "This CapCut version stores projects in a format the skill can't read. Nothing can be done safely.")

# 7. CapCut closed
if capcut_running():
    say("WARN", "CapCut closed", "CapCut is running",
        "Fine for now. Before captions or media are added, close the project you're editing in CapCut\n"
        "(the skill can't write to a project that is open).")
else:
    say("OK", "CapCut closed", "yes")

# 8. Python, Pillow, ffmpeg
if not args.quick:
    py = sys.version_info
    if py < (3, 9):
        say("FIX", "Python", platform.python_version(), "Install Python 3.9 or newer: https://www.python.org/downloads/windows/")
    else:
        say("OK", "Python", platform.python_version())
    if importlib.util.find_spec("PIL"):
        say("OK", "Pillow", "installed")
    else:
        say("FIX", "Pillow", "missing", "python -m pip install pillow")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            say("OK", tool, "installed")
        else:
            say("FIX", tool, "missing", "winget install Gyan.FFmpeg\nThen open a NEW terminal so Windows finds it.")

# 9. Transcription
engine = cfg.get("engine", "whisper")
if engine == "elevenlabs":
    if read_env("ELEVENLABS_API_KEY"):
        say("OK", "Transcription", "ElevenLabs key found (it's tested on the first transcription)")
    else:
        say("FIX", "Transcription", "ElevenLabs chosen but no key",
            f"Create a key at https://elevenlabs.io (Developers > API keys) with Speech to Text allowed.\n"
            f"Paste it yourself into {ENV_PATH} as: ELEVENLABS_API_KEY=your-key\n"
            "Never paste the key in this chat. Or switch back to free Whisper: set \"engine\": \"whisper\".")
elif importlib.util.find_spec("faster_whisper"):
    say("OK", "Transcription", f"Whisper ({cfg.get('whisperModel', 'medium')} model, free, on this PC)")
    chosen = False
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            chosen = "engine" in json.load(fh)
    if not args.quick and not chosen:
        say("ASK", "Faster captions", "optional",
            "ElevenLabs transcribes in seconds and is more accurate (especially Arabic mixed with English).\n"
            "It needs an ElevenLabs account; the free plan has monthly credits. Ask the user which one they want.")
else:
    say("FIX", "Transcription", "Whisper isn't installed",
        "python -m pip install faster-whisper\nThe model (hundreds of MB) downloads once, on the first transcription.")

fixes = results.count("FIX")
print()
print("READY" if not fixes else f"NOT READY: {fixes} thing(s) to fix first")
sys.exit(1 if fixes else 0)
