"""Real Logos: a local library of official brand logos, downloaded once and reused in every project.

    python logos.py find <name>                 search the library (id, brand, aliases, variant)
    python logos.py add <file> --brand "<Brand>" --variant <variant> --source <official page url>
                    [--id <id>] [--aliases a,b,c] [--notes "..."] [--from <id>] [--move]
    python logos.py path <name> [--variant <v>] [--format svg|png]   print the full path of the best match
    python logos.py list                        everything in the library
    python logos.py check                       every file still there and unchanged?
    python logos.py where                       print the library folder

The library lives in ~/.real-logos (set REAL_LOGOS_DIR to move it), outside any one project, so every project and
every skill update shares the same logos. Standard library only, no installs.
"""
import datetime, hashlib, json, os, re, shutil, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIB = os.path.abspath(os.path.expanduser(os.environ.get("REAL_LOGOS_DIR") or "~/.real-logos"))
MANIFEST = os.path.join(LIB, "manifest.json")
FORMATS = {"svg", "png", "webp"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load():
    if not os.path.exists(MANIFEST):
        return {"version": 1, "logos": []}
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    os.makedirs(LIB, exist_ok=True)
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, MANIFEST)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def full(entry):
    return os.path.join(LIB, *entry["path"].split("/"))


def flags(args):
    out, pos, i = {}, [], 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            nxt = args[i + 1] if i + 1 < len(args) else None
            if nxt is None or nxt.startswith("--"):
                out[a[2:]] = True
            else:
                out[a[2:]] = nxt
                i += 1
        else:
            pos.append(a)
        i += 1
    return out, pos


def file_problems(path, fmt):
    """Catch the usual bad downloads: an HTML page saved as .svg, a raster hidden in an SVG, a fake PNG."""
    with open(path, "rb") as f:
        head = f.read(4096)
    problems = []
    if fmt == "svg":
        text = open(path, encoding="utf-8", errors="replace").read()
        if re.search(r"<!doctype html|<html[\s>]", text[:2000], re.I):
            problems.append("this is a web page, not an SVG (the download link was wrong)")
        elif not re.search(r"<svg[\s>]", text, re.I):
            problems.append("no <svg> tag: not an SVG file")
        if re.search(r"<image[\s>]", text, re.I) and not re.search(r"<(path|circle|rect|polygon|ellipse|polyline)[\s>]", text, re.I):
            problems.append("it only wraps a picture inside an SVG: not a real vector logo")
        if not re.search(r"viewBox=", text, re.I):
            problems.append("no viewBox: it won't scale cleanly")
    elif fmt == "png" and not head.startswith(b"\x89PNG\r\n\x1a\n"):
        problems.append("not a real PNG file (the download link was wrong)")
    elif fmt == "webp" and not (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
        problems.append("not a real WebP file")
    return problems


def matches(entry, q):
    q = q.lower()
    fields = [entry["id"], entry["brand"], entry["variant"], *entry.get("aliases", [])]
    return any(q in (v or "").lower() for v in fields)


def show(entry):
    ok = os.path.exists(full(entry))
    print(f"{'OK     ' if ok else 'MISSING'} {entry['id']:<34} {entry['brand']} ({entry['variant']}, {entry['format']})  {full(entry)}")


def cmd_find(q):
    hits = [e for e in load()["logos"] if matches(e, q)]
    if not hits:
        print(f'Not in the library yet: "{q}". Find the official logo, then add it (see SKILL.md, step 2).')
        return 1
    for e in hits:
        show(e)
    return 0


def cmd_path(q, opts):
    hits = [e for e in load()["logos"] if matches(e, q) and os.path.exists(full(e))]
    if opts.get("variant"):
        hits = [e for e in hits if opts["variant"].lower() in e["variant"].lower()]
    if opts.get("format"):
        hits = [e for e in hits if e["format"] == opts["format"].lower()]
    if not hits:
        print(f'No matching logo for "{q}".', file=sys.stderr)
        return 1
    exact = [e for e in hits if q.lower() in (e["brand"].lower(), e["id"])]
    best = (exact or hits)[0]
    print(full(best))
    return 0


def cmd_add(src, opts):
    for req in ("brand", "variant"):
        if not opts.get(req) or opts[req] is True:
            raise SystemExit(f"--{req} is required")
    if not opts.get("source") and not opts.get("from"):
        raise SystemExit("--source <official page url> is required (or --from <id> for a file made from a library logo)")
    src = os.path.abspath(src)
    if not os.path.isfile(src):
        raise SystemExit(f"File not found: {src}")
    fmt = os.path.splitext(src)[1].lstrip(".").lower()
    if fmt not in FORMATS:
        raise SystemExit(f"Use an SVG (best), PNG or WebP file, not .{fmt}")

    problems = file_problems(src, fmt)
    if problems:
        raise SystemExit("Refused, this file looks wrong:\n  - " + "\n  - ".join(problems))

    data = load()
    digest = sha256(src)
    dupe = next((e for e in data["logos"] if e["sha256"] == digest), None)
    if dupe:
        print(f'Already in the library as "{dupe["id"]}": reuse it.')
        show(dupe)
        return 0
    parent = None
    if opts.get("from"):
        parent = next((e for e in data["logos"] if e["id"] == opts["from"]), None)
        if not parent:
            raise SystemExit(f'--from: no logo with id "{opts["from"]}"')

    brand = opts["brand"]
    lid = opts.get("id") or f"{slug(brand)}-{slug(opts['variant'])}" + ("" if fmt == "svg" else f"-{fmt}")
    if any(e["id"] == lid for e in data["logos"]):
        raise SystemExit(f'The id "{lid}" is taken. Pass --id with another name, or reuse the one you have.')

    rel = f"{slug(brand)}/{lid}.{fmt}"
    dest = os.path.join(LIB, *rel.split("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    (shutil.move if opts.get("move") else shutil.copy2)(src, dest)

    data["logos"].append({
        "id": lid,
        "brand": brand,
        "variant": opts["variant"],
        "format": fmt,
        "aliases": [a.strip() for a in str(opts.get("aliases") or "").split(",") if a.strip()],
        "path": rel,
        "source": opts.get("source") if isinstance(opts.get("source"), str) else (parent or {}).get("source"),
        "madeFrom": parent["id"] if parent else None,
        "saved": datetime.date.today().isoformat(),
        "sha256": digest,
        "notes": opts.get("notes") if isinstance(opts.get("notes"), str) else "",
    })
    save(data)
    print(f"Saved {lid} -> {dest}")
    return 0


def cmd_list():
    logos = sorted(load()["logos"], key=lambda e: (e["brand"].lower(), e["id"]))
    if not logos:
        print(f"The library is empty ({LIB}).")
    for e in logos:
        show(e)
    return 0


def cmd_check():
    bad = 0
    for e in load()["logos"]:
        p = full(e)
        status = "MISSING" if not os.path.exists(p) else "CHANGED" if sha256(p) != e["sha256"] else "OK"
        bad += status != "OK"
        print(f"{status:<8}{e['id']}  {p}")
    print(f"{bad} problem(s)." if bad else "All logos are in place.")
    return 1 if bad else 0


def main(argv):
    if not argv:
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    opts, pos = flags(rest)
    if cmd == "find" and pos:
        return cmd_find(" ".join(pos))
    if cmd == "path" and pos:
        return cmd_path(" ".join(pos), opts)
    if cmd == "add" and pos:
        return cmd_add(pos[0], opts)
    if cmd == "list":
        return cmd_list()
    if cmd == "check":
        return cmd_check()
    if cmd == "where":
        print(LIB)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
