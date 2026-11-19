"""Checks a CapCut project for problems that would show up as a broken edit: a clip linked to a compound clip (CapCut
plays the compound instead and empties the clip's path on save), an emptied or missing file. Run it after any change
and after the user saves in CapCut, before saying the edit is ready.

    python scripts/verify.py "<project> Edit"          prints OK or each problem (exit 1 on problems)
    python scripts/verify.py "<project> Edit" --fix    also removes the wrong compound links (project must be closed)
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import backup, check_draft, load_config, load_draft, project_path, repair_draft, require_closed, save_draft

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--fix", action="store_true")
args = ap.parse_args()
cfg = load_config()
d = load_draft(args.project, cfg)
if args.fix and repair_draft(load_draft(args.project, cfg)):
    require_closed(args.project, cfg)
    backup(args.project, cfg, "verify-fix")
    save_draft(args.project, d, cfg)
    d = load_draft(args.project, cfg)
problems = check_draft(d, project_path(args.project, cfg))
cc = d.get("canvas_config", {})
if cc.get("width") and cc.get("height") and abs(cc["width"] / cc["height"] - 9 / 16) > 0.01:
    print(f"NOTE canvas {cc['width']}x{cc['height']} is not 9:16: set the ratio to 9:16 in CapCut for Reels / Shorts / TikTok")
for p in problems:
    print("PROBLEM:", p)
print("OK" if not problems else f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
