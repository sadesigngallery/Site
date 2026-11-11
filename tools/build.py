#!/usr/bin/env python3
"""Build the public Sa Editions site from the app page.

Usage:
  python3 tools/build.py APP_HTML PHOTOS_DIR FILMS_DIR
  python3 tools/build.py --seo-only     rewrite only the search-engine pages and
                                        the home page head, on the public/ already built

APP_HTML    the app's index.html (as published in the claude.ai artifact)
PHOTOS_DIR  folder holding the app's p/*.webp files
FILMS_DIR   folder holding the app's v/*.mp4 files

What it does:
  * bakes the studio settings kept in state/*.json (room, lights, editions,
    Subjects layout, edition sales, photo order) into the page, because the public site
    has no access to the app's shared store;
  * moves the large embedded pictures (IMG and AL in the asset pack) out of
    the page into separate, content-hashed files under public/i and public/a,
    so the first visit downloads far less;
  * copies photos and films, and writes public/_headers for long caching of
    the hashed files;
  * removes the claude.ai page wrapper, so the site is one clean HTML document;
  * writes the search-engine pages (tools/seo.py): one page per piece, an
    index of all pieces, About, link-preview pictures, sitemap.xml, robots.txt,
    and the home page's title, description and structured data.
The site address and the contact e-mail used in those pages are read from
state/site.json ("url", "email"): change the e-mail there, once, to change it everywhere.
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


def unwrap(s):
    """The app as saved from claude.ai sits inside a small host page:
    <!doctype html><html><head>HOST STYLE</head><body> APP DOCUMENT  LATE SCRIPTS </body></html>.
    Keep the app document, move the host style into its head and the late scripts into its body."""
    m = re.match(r"(?is)\s*<!doctype html><html><head>(.*?)</head><body>\s*(<!DOCTYPE html>.*)$", s)
    if not m:
        return s
    host_head, rest = m.group(1), m.group(2)
    end = rest.rfind("</body>")
    inner_end = rest.find("</body>\n</html>")
    if inner_end < 0 or end <= inner_end:
        return s
    inner, late = rest[:inner_end], rest[inner_end + len("</body>\n</html>"):end]
    style = "".join(re.findall(r"(?is)<style>.*?</style>", host_head))
    inner = inner.replace("<head>", "<head>" + style, 1)
    return inner + late + "</body>\n</html>\n"


def main(app_html, photos, films):
    s = open(app_html, encoding="utf-8").read()

    # 1) bake studio settings just before the app's first render
    bake = ("/* public site: studio settings baked in */window.SA_SITE=true;try{"
            f"ROOMCFG={js(load_state('room.json', None))};"
            f"Object.assign(LIGHTS,{js(load_state('lights.json', {}))});"
            f"Object.assign(EDB,{js(load_state('editions.json', {}))});"
            f"Object.assign(SJPOS,{js(load_state('subj.json', {}))});"
            f"EDSOLD=Object.assign({{}},{js(load_state('edsold.json', {}))},EDSOLD)"
            "}catch(_){}"
            f"try{{Object.assign(FILMFIT,{js(load_state('filmfit.json', {}))});filmFitApply()}}catch(_){{}}"
            f"try{{Object.assign(IXS,{js(load_state('ixscale.json', {}))})}}catch(_){{}}"
            f"try{{Object.assign(LAY,{js(load_state('layout.json', {}))});layApply()}}catch(_){{}}"
            f"try{{Object.assign(ORD,{js(load_state('photoord.json', {}))});ordAll()}}catch(_){{}}\n")
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

    s = unwrap(s)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(s)

    # 3) photos, films, caching rules
    shutil.copytree(photos, os.path.join(OUT, "p"))
    shutil.copytree(films, os.path.join(OUT, "v"))
    with open(os.path.join(OUT, "_headers"), "w") as f:
        f.write("/i/*\n  Cache-Control: public, max-age=31536000, immutable\n"
                "/a/*\n  Cache-Control: public, max-age=31536000, immutable\n"
                "/p/*\n  Cache-Control: public, max-age=86400\n"
                "/v/*\n  Cache-Control: public, max-age=604800\n"
                "/\n  Cache-Control: no-cache\n"
                "/index.html\n  Cache-Control: no-cache\n"
                "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n"
                "  X-Frame-Options: SAMEORIGIN\n  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()\n"
                "  Strict-Transport-Security: max-age=15552000\n"
                "  Content-Security-Policy: upgrade-insecure-requests; frame-ancestors 'self'; object-src 'none'; base-uri 'self'\n")
    # 4) search-engine pages, then the home page's own head
    s = seo_pages(s)
    # tab icons as real files: Safari ignores data: icons and falls back to a letter in a circle
    brand = os.path.join(STATE, "brand")
    for n, out in (("favicon.ico", "favicon.ico"), ("favicon-32.png", "favicon-32.png"), ("favicon-512.png", "favicon-512.png"), ("sa-apple180.png", "apple-touch-icon.png")):
        shutil.copy(os.path.join(brand, n), os.path.join(OUT, out))
    s = re.sub(r'<link rel="(?:icon|apple-touch-icon)"[^>]*>', "", s)
    s = s.replace("</head>", '<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="icon" type="image/png" sizes="512x512" href="/favicon-512.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png"></head>', 1)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(s)
    size = os.path.getsize(os.path.join(OUT, "index.html"))
    print(f"moved {moved} pictures out of the page; index.html is now {size/1e6:.1f} MB")


def seo_pages(s):
    """Write the static pages and put the home page's head and <noscript> into s (the app page)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import seo
    cfg = load_state("site.json", {})
    site = cfg.get("url", "https://sa-editions.com")
    brand = os.path.join(STATE, "brand")
    org, pieces = seo.build(OUT, os.path.dirname(os.path.abspath(__file__)), site,
                            {n: os.path.join(brand, n) for n in ("sa-logo.png", "sa-k64.png", "sa-w64.png", "sa-apple180.png")},
                            email=cfg.get("email"))
    head, noscript = seo.home_head(site, org, pieces)
    a, b = seo.HOME_MARK
    if a in s:  # page built before: replace the previous head and noscript
        s = s[:s.index(a)] + head + s[s.index(b) + len(b):]
        s = re.sub(r"(?s)<noscript><main><h1>.*?</noscript>", lambda _: noscript, s, count=1)
    elif s.count("<title>Sa</title>") == 1 and "<title>Sa</title><meta name=\"description\"" not in s:
        s = s.replace("<title>Sa</title>", head, 1)
        s = s.replace("<body>", "<body>" + noscript, 1)
    else:  # public/ built by the older version of this script (head without markers)
        n0 = len(s)
        s = re.sub(r'(?s)<title>[^<]*</title><meta name="description".*?<link rel="sitemap"[^>]*>(?:<script type="application/ld\+json">.*?</script>){2}',
                   lambda _: head, s, count=1)
        if len(s) == n0 and head not in s:
            raise SystemExit("home head not found")
        s = re.sub(r"(?s)<noscript><main><h1>.*?</noscript>", lambda _: noscript, s, count=1)
    s = re.sub(r"<html lang=\"fa\" dir=\"rtl\">", '<html lang="en" dir="ltr">', s, count=1)
    print(f"wrote {len(pieces)} piece pages and spec sheets, /pieces/, /collections/, /designers/, /editions/, /about/, /contact/, sitemap.xml, robots.txt for {site}")
    return s


def seo_only():
    p = os.path.join(OUT, "index.html")
    s = open(p, encoding="utf-8").read()
    s = seo_pages(s)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


if __name__ == "__main__":
    if sys.argv[1:] == ["--seo-only"]:
        seo_only()
    elif len(sys.argv) != 4:
        raise SystemExit(__doc__)
    else:
        main(*sys.argv[1:])
