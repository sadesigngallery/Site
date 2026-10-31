#!/usr/bin/env python3
"""Build the public SA Design site from the app page.

Usage:
  python3 tools/build.py APP_HTML PHOTOS_DIR FILMS_DIR

APP_HTML    the app's index.html (as published in the claude.ai artifact)
PHOTOS_DIR  folder holding the app's p/*.webp files
FILMS_DIR   folder holding the app's v/*.mp4 files

What it does:
  * bakes the studio settings kept in state/*.json (room, lights, editions,
    Subjects layout, edition sales) into the page, because the public site
    has no access to the app's shared store;
  * moves the large embedded pictures (IMG and AL in the asset pack) out of
    the page into separate, content-hashed files under public/i and public/a,
    so the first visit downloads far less;
  * copies photos and films, and writes public/_headers for long caching of
    the hashed files.
The result is written to public/, which Cloudflare Pages serves.
"""
import base64, hashlib, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public")
STATE = os.path.join(ROOT, "state")
EXT = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png",
       "image/gif": "gif", "image/svg+xml": "svg"}


def load_state(name, default):
    p = os.path.join(STATE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def js(o):
    t = json.dumps(o, separators=(",", ":"), ensure_ascii=False)
    if "</" in t:
        raise SystemExit("refusing to bake data containing '</'")
    return t


def main(app_html, photos, films):
    s = open(app_html, encoding="utf-8").read()

    # 1) bake studio settings just before the app's first render
    bake = ("/* public site: studio settings baked in */try{"
            f"ROOMCFG={js(load_state('room.json', None))};"
            f"Object.assign(LIGHTS,{js(load_state('lights.json', {}))});"
            f"Object.assign(EDB,{js(load_state('editions.json', {}))});"
            f"Object.assign(SJPOS,{js(load_state('subj.json', {}))});"
            f"EDSOLD=Object.assign({{}},{js(load_state('edsold.json', {}))},EDSOLD)"
            "}catch(_){}\n")
    anchor = "renderChrome(); route();"
    if s.count(anchor) != 1:
        raise SystemExit("render anchor not found exactly once")
    s = s.replace(anchor, bake + anchor)

    # 2) move embedded pictures out of the asset pack
    i = s.find("const PACK=")
    j = s.find("\n", i)
    body = s[i + len("const PACK="):j].rstrip().rstrip(";")
    pack = json.loads(body)
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    moved = 0
    for group, folder in (("IMG", "i"), ("AL", "a")):
        os.makedirs(os.path.join(OUT, folder), exist_ok=True)
        for key, val in list(pack.get(group, {}).items()):
            m = re.match(r"data:([a-z]+/[a-z0-9.+-]+);base64,(.*)$", val or "", re.S)
            if not m or m.group(1) not in EXT:
                continue
            raw = base64.b64decode(m.group(2))
            h = hashlib.sha1(raw).hexdigest()[:10]
            safe = re.sub(r"[^A-Za-z0-9_-]", "_", key)
            name = f"{folder}/{safe}.{h}.{EXT[m.group(1)]}"
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(raw)
            pack[group][key] = name
            moved += 1
    s = s[:i] + "const PACK=" + json.dumps(pack, separators=(",", ":"), ensure_ascii=False) + ";" + s[j:]

    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(s)

    # 3) photos, films, caching rules
    shutil.copytree(photos, os.path.join(OUT, "p"))
    shutil.copytree(films, os.path.join(OUT, "v"))
    with open(os.path.join(OUT, "_headers"), "w") as f:
        f.write("/i/*\n  Cache-Control: public, max-age=31536000, immutable\n"
                "/a/*\n  Cache-Control: public, max-age=31536000, immutable\n"
                "/p/*\n  Cache-Control: public, max-age=604800\n"
                "/v/*\n  Cache-Control: public, max-age=604800\n"
                "/\n  Cache-Control: no-cache\n"
                "/index.html\n  Cache-Control: no-cache\n")
    size = os.path.getsize(os.path.join(OUT, "index.html"))
    print(f"moved {moved} pictures out of the page; index.html is now {size/1e6:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
