"""Shared helpers for capcut-claude-montage (Windows, CapCut desktop).

CapCut keeps every project as a folder of JSON files. This module finds those folders, reads a project's timeline,
and writes it back to every place CapCut keeps a copy. It never touches the user's original project: the skill only
writes to the "<project> Edit" copy that projects.py creates.

The project format is not documented by CapCut, so everything here was learned from real projects (tested on
CapCut desktop 9.7.1, Windows). A CapCut update can change it.
"""
import copy, datetime, json, os, shutil, subprocess, sys, uuid

if hasattr(sys.stdout, "reconfigure"):  # Arabic text in the console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Settings, key, work files: outside the skill folder, so they survive skill updates. CCM_HOME overrides it (testing).
HOME = os.environ.get("CCM_HOME") or os.path.join(os.path.expanduser("~"), ".capcut-claude-montage")
CONFIG_PATH = os.path.join(HOME, "config.json")
ENV_PATH = os.path.join(HOME, ".env")
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "projectsDir": None,              # None = CapCut's default folder
    "language": "auto",              # "auto", or a code like "ar", "en", "fr"
    "engine": "whisper",             # "whisper" (free, on this PC) or "elevenlabs" (faster, more accurate, needs a key)
    "whisperModel": "medium",        # tiny, base, small, medium, large-v3: bigger = more accurate and slower
    "captions": {
        "font": "C:/Windows/Fonts/arialbd.ttf",
        "color": "#FFFFFF",          # the phrase
        "highlight": "#F29900",      # the word being spoken
        "outline": "#000000",
        "outlineWidth": 0.08,
        "size": 12,                  # CapCut's text size
        "y": 1000,                   # vertical centre in pixels on the canvas (1920 tall for a reel)
        "maxWords": 5,
        "maxChars": 24,
    },
}


def load_config():
    cfg = copy.deepcopy(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            user = json.load(fh)
        caps = {**cfg["captions"], **user.get("captions", {})}
        cfg.update(user)
        cfg["captions"] = caps
    return cfg


def save_config(cfg):
    os.makedirs(HOME, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


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


def capcut_root():
    return os.path.join(os.environ.get("LOCALAPPDATA", ""), "CapCut")


def projects_dir(cfg=None):
    cfg = cfg or load_config()
    return cfg.get("projectsDir") or os.path.join(capcut_root(), "User Data", "Projects", "com.lveditor.draft")


def project_path(name, cfg=None):
    return os.path.join(projects_dir(cfg), name)


def list_projects(cfg=None):
    root = projects_dir(cfg)
    if not os.path.isdir(root):
        return []
    out = []
    for n in os.listdir(root):
        p = os.path.join(root, n, "draft_content.json")
        if os.path.isfile(p):
            out.append((n, os.path.getmtime(p)))
    return sorted(out, key=lambda x: -x[1])


def capcut_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"], capture_output=True, text=True).stdout
    return "CapCut.exe" in out


def is_open(name, cfg=None):
    return os.path.exists(os.path.join(project_path(name, cfg), ".locked"))


def require_closed(name, cfg=None):
    if is_open(name, cfg):
        raise SystemExit(f'"{name}" is open in CapCut. Close the project (or CapCut), then run this again. Nothing changed.')


def load_draft(name, cfg=None):
    p = os.path.join(project_path(name, cfg), "draft_content.json")
    if not os.path.exists(p):
        raise SystemExit(f'No CapCut project named "{name}". Run: python scripts/projects.py list')
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SystemExit(f'"{name}" is not plain JSON. This CapCut version stores projects in a format the skill can\'t read.')


def timeline_files(name, draft, cfg=None):
    """Every file where CapCut keeps this timeline. All of them must be written, or CapCut shows an old version."""
    root = project_path(name, cfg)
    files = [os.path.join(root, f) for f in ("draft_content.json", "draft_content.json.bak", "template-2.tmp")]
    tl = os.path.join(root, "Timelines", draft.get("id", ""))
    if draft.get("id") and os.path.isdir(tl):
        files += [os.path.join(tl, f) for f in ("draft_content.json", "draft_content.json.bak", "template-2.tmp")]
    return files


def work_dir(name):
    p = os.path.join(HOME, "work", name)
    os.makedirs(p, exist_ok=True)
    return p


def backup(name, cfg=None, label="change"):
    """Saves the current timeline before a change; restore.py brings the newest one back."""
    src = os.path.join(project_path(name, cfg), "draft_content.json")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    root = os.path.join(work_dir(name), "backups")
    n = 1  # numbered, so two runs in the same second still sort in the right order
    while any(os.path.exists(os.path.join(root, p + f"{stamp}-{n:02d}-{label}")) for p in ("", "_restored-")):
        n += 1
    dst = os.path.join(root, f"{stamp}-{n:02d}-{label}")
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(src, os.path.join(dst, "draft_content.json"))
    return dst


def save_draft(name, draft, cfg=None):
    data = json.dumps(draft, ensure_ascii=False, separators=(",", ":"))
    for p in timeline_files(name, draft, cfg):
        if os.path.exists(p) or p.endswith("draft_content.json"):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(data)


def new_id():
    return str(uuid.uuid4()).upper()


class Canvas:
    """Pixel positions <-> CapCut's coordinates (centre = 0, edges = +-1, y up) and seconds <-> microseconds on frames."""

    def __init__(self, draft):
        c = draft.get("canvas_config") or {}
        self.w, self.h = c.get("width") or 1080, c.get("height") or 1920
        self.fps = draft.get("fps") or 30.0
        self.frame = 1_000_000 / self.fps

    def snap(self, sec):
        return int(round(round(sec * self.fps) * self.frame))

    def to_x(self, px):
        return (px - self.w / 2) / (self.w / 2)

    def to_y(self, py):
        return (self.h / 2 - py) / (self.h / 2)


def hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def clone_refs(seg, source, target, skip=("effects", "drafts")):
    """A copied clip needs its own copies of the small helper entries it points to (speed, canvas, animations...)."""
    refs = []
    for r in seg.get("extra_material_refs", []):
        for kind, items in source.items():
            if kind in skip or not isinstance(items, list):
                continue
            hit = next((x for x in items if isinstance(x, dict) and x.get("id") == r), None)
            if hit is not None:
                c = copy.deepcopy(hit)
                c["id"] = new_id()
                target.setdefault(kind, []).append(c)
                refs.append(c["id"])
    seg["extra_material_refs"] = refs


def our_track(draft, name, kind):
    """The skill names its tracks ("ccm-captions", "ccm-media"), so a rerun replaces only its own work."""
    for t in draft["tracks"]:
        if t.get("name") == name and t["type"] == kind:
            return t
    return None


def new_track(kind, name, segments):
    return {"id": new_id(), "type": kind, "flag": 1 if kind == "text" else 2, "attribute": 0, "name": name,
            "is_default_name": False, "segments": segments}
