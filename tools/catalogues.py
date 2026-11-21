#!/usr/bin/env python3
"""Catalogues page data: PDFs published from Sa hub.

The source of truth is state/catalogues/ (list.json + PDFs + covers); public/ is rebuilt
by build.py, which calls mirror() to copy this folder to public/catalogues/.

  catalogues.py add --id cat --title "..." [--fa "..."] --group collection --pdf F.pdf --cover C.jpg --pages N
      copies the files in, updates list.json (same id = replaced), then mirrors to public/
  catalogues.py remove --id cat
  catalogues.py mirror
Groups: collection, family, technical, projects, other.  Each PDF must stay under 25 MiB.
"""
import os, sys, json, shutil, argparse, datetime, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "state", "catalogues")
DST = os.path.join(ROOT, "public", "catalogues")
LIMIT = 25 * 1048576

def load():
    p = os.path.join(SRC, "list.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"items": []}

def save(d):
    os.makedirs(SRC, exist_ok=True)
    with open(os.path.join(SRC, "list.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

def mirror():
    if not os.path.isdir(SRC): return "no catalogues yet"
    if os.path.isdir(DST): shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    return f"catalogues: {len(load()['items'])} in public/catalogues"

def slug(s): return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")

def add(a):
    from PIL import Image
    size = os.path.getsize(a.pdf)
    if size >= LIMIT: raise SystemExit(f"{a.pdf} is {size/1048576:.1f} MiB; the site limit is 25 MiB")
    os.makedirs(SRC, exist_ok=True); d = load()
    old = next((x for x in d["items"] if x["id"] == a.id), None)
    if old:   # drop the previous files of this catalogue
        for k in ("pdf", "cover"):
            f = os.path.join(ROOT, "state", old[k].lstrip("/"))
            if os.path.exists(f): os.remove(f)
    stamp = datetime.date.today().isoformat()
    t = a.title if a.title.lower().startswith("sa editions") else "Sa Editions " + a.title
    pdf_name = f"{slug(t)}.pdf"
    cov_name = f"{a.id}-cover-{stamp}.jpg"
    shutil.copy(a.pdf, os.path.join(SRC, pdf_name)); shutil.copy(a.cover, os.path.join(SRC, cov_name))
    w, h = Image.open(a.cover).size
    item = {"id": a.id, "title": a.title, "fa": a.fa or "", "g": a.group, "pdf": f"/catalogues/{pdf_name}",
            "cover": f"/catalogues/{cov_name}", "pages": a.pages, "bytes": size, "date": stamp, "cw": w, "ch": h}
    items = [x for x in d["items"] if x["id"] != a.id]
    pos = next((i for i, x in enumerate(d["items"]) if x["id"] == a.id), len(items))
    items.insert(pos, item); d["items"] = items; save(d); print(mirror()); print(json.dumps(item, ensure_ascii=False))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    x = sp.add_parser("add")
    for k in ("id", "title", "group", "pdf", "cover"): x.add_argument("--" + k, required=True)
    x.add_argument("--fa"); x.add_argument("--pages", type=int, default=0)
    r = sp.add_parser("remove"); r.add_argument("--id", required=True)
    sp.add_parser("mirror")
    a = ap.parse_args()
    if a.cmd == "add": add(a)
    elif a.cmd == "remove":
        d = load(); d["items"] = [i for i in d["items"] if i["id"] != a.id]; save(d); print(mirror())
    else: print(mirror())
