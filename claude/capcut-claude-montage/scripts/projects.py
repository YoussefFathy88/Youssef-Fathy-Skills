"""List CapCut projects, or make the "<project> Edit" copy the skill works on. The original is never written to.

    python scripts/projects.py list
    python scripts/projects.py copy "<project>"            makes "<project> Edit"
    python scripts/projects.py copy "<project>" --name "My Edit"

One Edit copy per video: if it already exists, keep working on it (captions.py / add.py change it in place and keep
the user's hand changes). If CapCut is running, only the folder is copied (CapCut usually lists it by itself);
CapCut's project list is edited only while CapCut is closed, after a backup.
"""
import argparse, json, os, shutil, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccm_common import capcut_running, list_projects, load_config, new_id, project_path, projects_dir, work_dir

ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("list")
c = sub.add_parser("copy")
c.add_argument("project")
c.add_argument("--name")
args = ap.parse_args()
cfg = load_config()

if args.cmd == "list":
    projects = list_projects(cfg)
    if not projects:
        raise SystemExit(f"No projects in {projects_dir(cfg)}")
    for name, mtime in projects:
        with open(os.path.join(project_path(name, cfg), "draft_content.json"), encoding="utf-8") as fh:
            secs = json.load(fh).get("duration", 0) / 1e6
        print(f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))}  {secs:6.1f} s  {name}")
    sys.exit(0)

name = args.name or f"{args.project} Edit"
src, dst = project_path(args.project, cfg), project_path(name, cfg)
if not os.path.exists(os.path.join(src, "draft_content.json")):
    raise SystemExit(f'No CapCut project named "{args.project}". Run: python scripts/projects.py list')
if os.path.exists(dst):
    raise SystemExit(f'"{name}" already exists. Keep working on it (captions.py / add.py), or delete it in CapCut first.')
running = capcut_running()  # CapCut rewrites its project list while it runs: then only the folder is copied
if os.path.exists(os.path.join(src, ".locked")):
    print(f'Note: "{args.project}" is open in CapCut, so the copy has what was last SAVED there.')

shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".locked"))
meta_path = os.path.join(dst, "draft_meta_info.json")
with open(meta_path, encoding="utf-8") as fh:
    meta = json.load(fh)
fold = dst.replace("\\", "/")
meta.update(draft_id=new_id(), draft_name=name, draft_fold_path=fold)
with open(meta_path, "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False)

# Add the copy to CapCut's project list (backed up first). If anything is odd, CapCut usually finds the folder by itself.
lst = os.path.join(projects_dir(cfg), "root_meta_info.json")
listed = False
if os.path.exists(lst) and not running:
    shutil.copy2(lst, os.path.join(work_dir(name), "root_meta_info.before-copy.json"))
    with open(lst, encoding="utf-8") as fh:
        m = json.load(fh)
    store = m.get("all_draft_store")
    if isinstance(store, list) and store and not any(x.get("draft_name") == name for x in store):
        e = json.loads(json.dumps(store[0]))
        e.update(draft_id=meta["draft_id"], draft_name=name, draft_fold_path=fold,
                 draft_json_file=fold + "/draft_content.json", draft_cover=fold + "/draft_cover.jpg")
        store.insert(0, e)
        if isinstance(m.get("draft_ids"), int):
            m["draft_ids"] += 1
        with open(lst, "w", encoding="utf-8") as fh:
            json.dump(m, fh, ensure_ascii=False)
        listed = True
hint = "" if listed else (" CapCut is running, so it should pick the copy up by itself; if it isn't in the list, restart CapCut."
                          if running else " CapCut will list it when it opens.")
print(f'Made "{name}" from "{args.project}". Original untouched.' + hint)
