"""Undo: puts back the timeline saved before the last captions.py / add.py run.

    python scripts/restore.py "<project> Edit"            undo the last change
    python scripts/restore.py "<project> Edit" --list     show the saved backups
    python scripts/restore.py "<project> Edit" --pick 20261109-142030-captions

Hand changes made in CapCut AFTER that backup are lost by a restore, so check --list first. The project must be closed.
"""
import argparse, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import load_config, require_closed, save_draft, work_dir

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--list", action="store_true")
ap.add_argument("--pick")
args = ap.parse_args()
cfg = load_config()
root = os.path.join(work_dir(args.project), "backups")
saved = sorted(n for n in os.listdir(root) if not n.startswith("_restored-")) if os.path.isdir(root) else []
if not saved:
    raise SystemExit(f'No backups for "{args.project}".')
if args.list:
    for s in saved:
        print(s)
    sys.exit(0)
pick = args.pick or saved[-1]
if pick not in saved:
    raise SystemExit(f"No backup named {pick}. Use --list.")
require_closed(args.project, cfg)
with open(os.path.join(root, pick, "draft_content.json"), encoding="utf-8") as fh:
    d = json.load(fh)
save_draft(args.project, d, cfg)
shutil.move(os.path.join(root, pick), os.path.join(root, "_restored-" + pick))  # the next undo goes one step further back
print(f'"{args.project}" is back to how it was before {pick}.')
