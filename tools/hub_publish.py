#!/usr/bin/env python3
"""Publish a Sa hub booklet to the site's Catalogues page (sa-editions.com/#/catalogues).

Two steps, run from the repo root after downloading from the Sa hub artifact:
  1) python3 tools/hub_publish.py needs  --tab K --hub-html HUB.html [--order ORDER.json]
       prints the bundle paths (v/<doc>-NN.jpg) to download from the hub artifact
  2) python3 tools/hub_publish.py build  --tab K --hub-html HUB.html [--order ORDER.json] --bundles DIR
       builds the PDF (<25 MiB, links and bookmarks kept) and adds it to state/catalogues + public/catalogues
ORDER.json is the hub db document orders/<K>; without it the booklet's own page list (or refs) is used.
"""
import os, sys, re, json, argparse, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
# tab -> (English title, Persian title, group on the Catalogues page). No dashes in titles.
HUB = {
    "cat":  ("Sa Editions Catalogue", "کاتالوگ سا ادیشنز", "collection"),
    "ct":   ("Catalogue · Text Edition", "کاتالوگ · نسخهٔ متنی", "collection"),
    "pn":   ("Piano", "پیانو", "family"),
    "lt":   ("Lighting", "نورپردازی", "family"),
    "dt":   ("Dining and Coffee Tables", "میز نهارخوری و جلومبلی", "family"),
    "se":   ("Seating", "نشیمن", "family"),
    "info": ("Technical Book", "کتاب فنی", "technical"),
    "sg":   ("Seating Guide", "راهنمای نشیمن", "technical"),
    "s1":   ("Sa × Lotfi House · Set 01", "سا × لطفی هاوس · ست ۰۱", "projects"),
    "s2":   ("Sa × Lotfi House · Set 02", "سا × لطفی هاوس · ست ۰۲", "projects"),
    "gift": ("The Butterfly Effect · Gift Catalogue", "اثر پروانه‌ای · کاتالوگ هدیه", "other"),
    "pl":   ("Price List", "لیست قیمت", "other"),
    "tb":   ("Single Sheets", "تک‌برگ‌ها", "other"),
}

def hub_data(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r'<script[^>]*id="sa-data"[^>]*>(.*?)</script>', s, re.S)
    if not m: raise SystemExit("script#sa-data not found in " + path)
    return json.loads(m.group(1))

def order_of(data, tab, order_path):
    if order_path and os.path.exists(order_path):
        o = json.load(open(order_path)); o = o.get("data", o)
        if o.get("order"): return o["order"]
    d = data["docs"][tab]
    return d.get("refs") or [f"{tab}:{i}" for i in range(len(d["pages"]))]

def needs(data, order):
    out = set()
    for r in order:
        doc, i = r.split(":"); out.add(f"v/{doc}-{data['docs'][doc]['pages'][int(i)]['v'][0]:02d}.jpg")
    return sorted(out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["needs", "build"])
    ap.add_argument("--tab", required=True); ap.add_argument("--hub-html", required=True)
    ap.add_argument("--order"); ap.add_argument("--bundles"); ap.add_argument("--mb", type=float, default=23.5)
    a = ap.parse_args()
    data = hub_data(a.hub_html); order = order_of(data, a.tab, a.order)
    if a.cmd == "needs":
        print("\n".join(needs(data, order))); sys.exit()
    title, fa, group = HUB.get(a.tab, (data["docs"][a.tab].get("name", a.tab).replace("_", " "), "", "other"))
    tmp = tempfile.mkdtemp()
    dj = os.path.join(tmp, "sa-data.json"); json.dump(data, open(dj, "w"))
    oj = os.path.join(tmp, "order.json"); json.dump({"order": order}, open(oj, "w"))
    pdf = os.path.join(tmp, "out.pdf"); cov = os.path.join(tmp, "cover.jpg")
    r = subprocess.run([sys.executable, os.path.join(HERE, "catpdf.py"), dj, oj, a.bundles, pdf, cov, "--doc", a.tab, "--mb", str(a.mb)],
                       capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    info = json.loads(r.stdout.strip().splitlines()[-1])
    r = subprocess.run([sys.executable, os.path.join(HERE, "catalogues.py"), "add", "--id", a.tab, "--title", title, "--fa", fa,
                        "--group", group, "--pdf", pdf, "--cover", cov, "--pages", str(info["pages"])], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    print(r.stdout.strip()); print(json.dumps(info))
