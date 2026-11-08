"""Search-engine pages for the public site (called by build.py after public/ is written).

Writes, from what the catalogue itself shows:
  /p/<id>/index.html  one real page per piece (title, description, dimensions,
                      materials, edition, photos with alt text, structured data)
  /pieces/            an index of all pieces
  /about/             the About text and founders
  /og/*.jpg           link-preview pictures (WhatsApp, Telegram, social)
  /sitemap.xml        every page, with its pictures
  /robots.txt
The app itself stays at / ; every static page links into it.
"""
import html, json, os, re, socket, subprocess, sys, time, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from PIL import Image

E = html.escape


def _serve(root):
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    class Q(SimpleHTTPRequestHandler):
        def log_message(self, *a, **k): pass
    h = partial(Q, directory=root)
    srv = ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def scrape(out_dir, tools_dir):
    srv, port = _serve(out_dir)
    try:
        r = subprocess.run(["node", os.path.join(tools_dir, "seo_scrape.js"), f"http://127.0.0.1:{port}/"],
                           capture_output=True, text=True, timeout=900, cwd=tools_dir)
        if r.returncode:
            raise SystemExit("seo scrape failed:\n" + r.stderr[-2000:])
        return json.loads(r.stdout)
    finally:
        srv.shutdown()


def absu(site, p):
    if not p: return None
    p = p.split("?")[0]
    return site.rstrip("/") + "/" + p.lstrip("/")


def og_image(out_dir, src_rel, name):
    """1200x630 JPEG on white, piece centred."""
    if not src_rel: return None
    src = os.path.join(out_dir, src_rel.split("?")[0])
    if not os.path.exists(src): return None
    os.makedirs(os.path.join(out_dir, "og"), exist_ok=True)
    im = Image.open(src).convert("RGBA")
    bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if bb: im = im.crop(bb)
    W, H = 1200, 630
    k = min((W * .84) / im.width, (H * .80) / im.height)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    bg = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    bg.alpha_composite(im, ((W - im.width) // 2, (H - im.height) // 2))
    rel = f"og/{name}.jpg"
    bg.convert("RGB").save(os.path.join(out_dir, rel), quality=86, optimize=True)
    return rel


CSS = """*{box-sizing:border-box}body{margin:0;background:#fff;color:#111;font:300 16px/1.65 -apple-system,BlinkMacSystemFont,"Inter","Helvetica Neue",Arial,sans-serif}
a{color:inherit}header.sb{display:flex;align-items:flex-end;justify-content:center;gap:8px;padding:26px 16px 10px}header.sb img{height:46px;width:auto}header.sb span{font-size:.74rem;letter-spacing:.12em}
.tg{text-align:center;margin:0 16px 26px;font-size:.78rem;letter-spacing:.06em;color:#4a4a4a}
main{max-width:860px;margin:0 auto;padding:0 18px 40px}h1{font-weight:500;font-size:2.3rem;line-height:1.1;margin:10px 0 2px;text-align:center}
.fa{text-align:center;color:#444;margin:0 0 4px}.cat{text-align:center;color:#4a4a4a;font-size:.86rem;letter-spacing:.06em;text-transform:uppercase;margin:0 0 20px}
.hero{display:block;width:100%;height:auto;margin:6px 0 18px}.dims{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #e6e6e6;border-bottom:1px solid #e6e6e6;margin:0 0 18px}
.dims div{text-align:center;padding:12px 0}.dims div+div{border-left:1px solid #e6e6e6}.dims small{display:block;color:#555;font-size:.78rem}.dims b{font-weight:500;font-size:1.3rem}
.ed{display:flex;flex-wrap:wrap;gap:6px 14px;justify-content:center;align-items:center;padding:10px 0 16px}.ed b{font-weight:600;font-size:.78rem;letter-spacing:.08em;text-transform:uppercase}.ed span{color:#444;font-size:.84rem}
.desc p{margin:0 0 14px}dl{display:grid;grid-template-columns:max-content 1fr;gap:6px 22px;margin:22px 0;font-size:.92rem}dt{color:#555}dd{margin:0}
.ph{display:grid;gap:10px;margin:22px 0}.ph img{width:100%;height:auto;display:block}
.cta{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:26px 0}.cta a{border:1px solid rgba(0,0,0,.5);border-radius:999px;padding:10px 18px;text-decoration:none;font-weight:500;font-size:.9rem}.cta a.p{background:#000;color:#fff;border-color:#000}
.grid{display:flex;flex-wrap:wrap;justify-content:center;gap:22px 16px;margin:16px 0}.grid a{text-decoration:none;text-align:center;flex:0 0 150px}.grid img{width:100%;height:120px;object-fit:contain;display:block}.grid b{display:block;font-weight:500;margin-top:6px}.grid small{color:#555;font-size:.76rem}
h2{font-weight:500;font-size:.9rem;letter-spacing:.08em;text-transform:uppercase;margin:34px 0 8px;border-top:1px solid #eee;padding-top:18px}
h2.ch{text-align:center;border:0;font-weight:300;font-size:1rem;letter-spacing:.04em;margin:44px 0 14px;padding:0}h2.ch b{font-weight:600}
.eq{display:flex;flex-wrap:wrap;justify-content:center;align-items:flex-end;gap:22px 26px;margin:16px 0}.eq a{text-decoration:none;text-align:center}
.eq .eb{position:relative;display:block;height:96px;margin:0 auto}.eq .eb img{position:absolute;max-width:none}.eq b{display:block;font-weight:500;margin-top:6px}.eq small{color:#555;font-size:.76rem}
.bio{display:grid;grid-template-columns:120px 1fr;gap:16px;margin:18px 0}.bio img{width:120px;height:auto}
footer{border-top:1px solid #e6e6e6;max-width:860px;margin:10px auto 0;padding:20px 16px 40px;text-align:center}footer nav{display:flex;flex-wrap:wrap;gap:8px 20px;justify-content:center;font-size:.84rem}footer nav a{text-decoration:none}footer p{color:#555;font-size:.74rem;margin:14px 0 0}
.crumb{font-size:.8rem;color:#555;margin:0 0 4px}.crumb a{text-decoration:none}"""


def page(site, path, title, desc, body, og=None, jsonld=None, lang="en"):
    canon = site.rstrip("/") + path
    j = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>' for o in (jsonld or []))
    ogi = f'<meta property="og:image" content="{E(absu(site, og))}"><meta name="twitter:image" content="{E(absu(site, og))}">' if og else ""
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(canon)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Sa Editions"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(canon)}">{ogi}<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>{CSS}</style>{j}</head><body>
<header class="sb"><a href="/" aria-label="Sa Editions"><img src="/sa-logo.png" alt="Sa Editions logo" width="120" height="46"></a><span>EDITIONS</span></header>
<p class="tg">Sculptural furniture, handmade in limited editions</p>
{body}
<footer><nav><a href="/about/">About</a><a href="/#/contact">Contact</a><a href="https://www.instagram.com/sa_editions_/" rel="noopener">Instagram</a><a href="mailto:Sadesigngallery@gmail.com">Email</a><a href="/pieces/">All pieces</a><a href="/#/discover">Discover</a><a href="/#/trade">Trade</a></nav>
<p>Copyright © 2026 Sa Inc. All rights reserved</p></footer></body></html>"""


def short(text, n=155):
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def build(out_dir, tools_dir, site, assets):
    data = scrape(out_dir, tools_dir)
    # brand files for the static pages
    for name, src in assets.items():
        if src and os.path.exists(src):
            with open(src, "rb") as f, open(os.path.join(out_dir, name), "wb") as g: g.write(f.read())
    pieces = data["pieces"]
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "Sa Editions", "alternateName": ["Sa", "SA Editions"],
           "url": site.rstrip("/") + "/", "logo": absu(site, "sa-logo.png"), "foundingDate": "2010",
           "founder": [{"@type": "Person", "name": "Alireza Emtiaz"}, {"@type": "Person", "name": "Saqar Khakdan"}],
           "email": "Sadesigngallery@gmail.com", "sameAs": ["https://www.instagram.com/sa_editions_/"],
           "contactPoint": [{"@type": "ContactPoint", "contactType": "sales", "telephone": "+98-939-713-3918", "areaServed": "IR"},
                            {"@type": "ContactPoint", "contactType": "sales", "telephone": "+1-403-922-9905", "areaServed": "CA"}]}
    urls = [("/", [absu(site, "og/home.jpg")]), ("/pieces/", []), ("/about/", [])]
    # piece pages
    for x in pieces:
        pid = x["id"]; path = f"/p/{pid}/"
        imgs = [i for i in [x["hero"]] + x["photos"] + ([x["drawing"]] if x["drawing"] else []) if i]
        og = og_image(out_dir, x["hero"] or x["thumb"], pid)
        cat1 = re.sub(r"s$", "", x["cat"]) if x["cat"] else ""
        title = f"{x['name']} — {cat1} | Sa Editions"
        d0 = " ".join(x["desc"]) if x["desc"] else ""
        mat = dict(x["spec"]).get("Material", "")
        desc = short(f"{x['name']} ({x['fa']}), {cat1.lower()} by Sa Editions. {x['edition']}{'. ' if x['edition'] else ''}{mat + '. ' if mat else ''}{d0}")
        dims = "".join(f"<div><small>{E(k)}</small><b>{E(v)}</b></div>" for k, v in x["dims"])
        spec = "".join(f"<dt>{E(k)}</dt><dd>{E(v)}</dd>" for k, v in x["spec"])
        ph = "".join(f'<img src="/{E(i)}" alt="{E(x["name"])} {E(cat1.lower())} by Sa Editions — photo {n + 1}" loading="lazy">' for n, i in enumerate(x["photos"]))
        dr = f'<img src="/{E(x["drawing"])}" alt="{E(x["name"])} — technical drawing" loading="lazy">' if x["drawing"] else ""
        hero = f'<img class="hero" src="/{E(x["hero"])}" alt="{E(x["name"])} {E(cat1.lower())} by Sa Editions" width="1600" height="1600">' if x["hero"] else ""
        yt = (f'<div style="position:relative;aspect-ratio:16/9;margin:6px 0 18px;background:#000"><iframe src="https://www.youtube-nocookie.com/embed/{E(x["yt"])}?rel=0&modestbranding=1&playsinline=1" title="{E(x["name"])} — film" loading="lazy" style="position:absolute;inset:0;width:100%;height:100%;border:0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>') if x.get("yt") else ""
        ed = f'<div class="ed"><b>{E(x["edition"])}</b>{"<span>" + E(x["editionNote"]) + "</span>" if x["editionNote"] else ""}</div>' if x["edition"] else ""
        body = f"""<main><p class="crumb"><a href="/pieces/">All pieces</a> / {E(x['cat'])}</p><h1>{E(x['name'])}</h1><p class="fa" lang="fa" dir="rtl">{E(x['fa'])}</p><p class="cat">{E(cat1)}{' · ' + str(x['year']) if x['year'] else ''}</p>
{hero}<div class="dims">{dims}</div>{ed}{yt}<div class="desc">{''.join('<p>' + E(p) + '</p>' for p in x['desc'])}</div><dl>{spec}</dl>
<div class="cta"><a class="p" href="/#/p/{E(pid)}">View in the catalogue</a><a href="https://wa.me/14039229905?text={E(('Hello, about ' + x['name']).replace(' ', '%20'))}" rel="noopener">WhatsApp</a><a href="mailto:Sadesigngallery@gmail.com?subject=Sa%20Editions%20%E2%80%94%20{E(x['name'])}">Email</a></div>
<div class="ph">{ph}{dr}</div></main>"""
        prod = {"@context": "https://schema.org", "@type": "Product", "name": x["name"], "alternateName": x["fa"], "sku": pid,
                "category": cat1, "description": d0 or desc, "image": [absu(site, i) for i in imgs], "url": site.rstrip("/") + path,
                "brand": {"@type": "Brand", "name": "Sa Editions"}, "manufacturer": {"@type": "Organization", "name": "Sa Editions"}}
        if mat: prod["material"] = mat
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Sa Editions", "item": site.rstrip("/") + "/"},
            {"@type": "ListItem", "position": 2, "name": "All pieces", "item": site.rstrip("/") + "/pieces/"},
            {"@type": "ListItem", "position": 3, "name": x["name"], "item": site.rstrip("/") + path}]}
        os.makedirs(os.path.join(out_dir, "p", pid), exist_ok=True)
        with open(os.path.join(out_dir, "p", pid, "index.html"), "w", encoding="utf-8") as f:
            f.write(page(site, path, title, desc, body, og, [prod, crumbs]))
        urls.append((path, [absu(site, i) for i in imgs]))
    # all pieces
    groups = {}
    for x in pieces: groups.setdefault(x["cat"], []).append(x)

    def eqtile(x):
        # dining tables: every table drawn at the same body height
        b, ts = x.get("tbb"), x.get("ts")
        if not (b and ts and x.get("thumb")):
            return None
        a = ts[0] / ts[1]; bh = 80; ih = bh / (b[3] - b[1]); iw = ih * a; bw = iw * (b[2] - b[0])
        left = bw / 2 + 2 - iw * (b[0] + b[2]) / 2; bot = 4 - ih * (1 - b[3])
        return (f'<a href="/p/{E(x["id"])}/"><span class="eb" style="width:{bw + 4:.0f}px"><img src="/{E(x["thumb"])}" alt="{E(x["name"])} by Sa Editions" loading="lazy" '
                f'style="height:{ih:.1f}px;width:{iw:.1f}px;left:{left:.1f}px;bottom:{bot:.1f}px"></span><b>{E(x["name"])}</b><small>{E(x["edition"])}</small></a>')

    def block(c, xs):
        g = xs[0].get("grp") or ["", c.upper()]
        head = f"<h2 class='ch'><b>{E(g[0])} /</b> {E(g[1])}</h2>"
        if xs[0].get("catId") == "dining" and all(eqtile(x) for x in xs):
            return head + "<div class='eq'>" + "".join(eqtile(x) for x in xs) + "</div>"
        return head + "<div class='grid'>" + "".join(
            f'<a href="/p/{E(x["id"])}/"><img src="/{E(x["thumb"] or x["hero"] or "")}" alt="{E(x["name"])} by Sa Editions" loading="lazy"><b>{E(x["name"])}</b><small>{E(x["edition"])}</small></a>' for x in xs) + "</div>"
    body = "<main><h1>All pieces</h1>" + "".join(block(c, xs) for c, xs in groups.items()) + "</main>"
    os.makedirs(os.path.join(out_dir, "pieces"), exist_ok=True)
    with open(os.path.join(out_dir, "pieces", "index.html"), "w", encoding="utf-8") as f:
        f.write(page(site, "/pieces/", "All pieces — sculptural furniture, pianos and lighting | Sa Editions",
                     short("The full Sa Editions collection: dining tables, desks, side and coffee tables, consoles, lighting, benches, chairs, armchairs, sofas and pianos — each handmade in a limited, numbered edition."),
                     body, "og/home.jpg", [org]))
    # about
    a = data.get("about") or {"title": "About SA", "paras": [], "bios": []}
    bios = "".join(f'<div class="bio">{"<img src=" + chr(34) + "/" + E(b["img"]) + chr(34) + " alt=" + chr(34) + E(b["name"]) + chr(34) + ">" if b.get("img") else ""}<div><b>{E(b["name"])}</b><p>{E(b["text"])}</p></div></div>' for b in a["bios"])
    body = f"<main><h1>{E(a['title'])}</h1>" + "".join(f"<p>{E(p)}</p>" for p in a["paras"] if p not in [b['text'] for b in a['bios']]) + (f"<h2>Founders</h2>{bios}" if bios else "") + \
           '<div class="cta"><a class="p" href="/">Enter the catalogue</a><a href="/#/contact">Contact</a></div></main>'
    os.makedirs(os.path.join(out_dir, "about"), exist_ok=True)
    with open(os.path.join(out_dir, "about", "index.html"), "w", encoding="utf-8") as f:
        f.write(page(site, "/about/", "About Sa Editions — Alireza Emtiaz & Saqar Khakdan",
                     short("Sa Editions is a design house founded in 2010 by architects Alireza Emtiaz and Saqar Khakdan, working across Objects, Collectibles and Spaces. Every piece is made by hand in a limited edition."),
                     body, "og/home.jpg", [org]))
    # home preview picture: the logo on white
    lg = os.path.join(out_dir, "sa-logo.png")
    if os.path.exists(lg):
        im = Image.open(lg).convert("RGBA"); k = min(700 / im.width, 300 / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        bg = Image.new("RGBA", (1200, 630), (255, 255, 255, 255)); bg.alpha_composite(im, ((1200 - im.width) // 2, (630 - im.height) // 2))
        os.makedirs(os.path.join(out_dir, "og"), exist_ok=True); bg.convert("RGB").save(os.path.join(out_dir, "og", "home.jpg"), quality=88)
    # sitemap + robots
    today = time.strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for path, imgs in urls:
        sm.append(f"<url><loc>{E(site.rstrip('/') + path)}</loc><lastmod>{today}</lastmod>" + "".join(f"<image:image><image:loc>{E(i)}</image:loc></image:image>" for i in imgs if i) + "</url>")
    sm.append("</urlset>")
    with open(os.path.join(out_dir, "sitemap.xml"), "w", encoding="utf-8") as f: f.write("\n".join(sm))
    with open(os.path.join(out_dir, "robots.txt"), "w") as f: f.write(f"User-agent: *\nAllow: /\n\nSitemap: {site.rstrip('/')}/sitemap.xml\n")
    return org, pieces


def home_head(site, org, pieces):
    title = "Sa — Sculptural furniture in limited editions | Sa Editions"
    desc = "Sa Editions: sculptural furniture, pianos and lighting by architects Alireza Emtiaz and Saqar Khakdan, handmade in limited, numbered editions since 2010."
    web = {"@context": "https://schema.org", "@type": "WebSite", "name": "Sa Editions", "alternateName": ["Sa", "SA Editions"], "url": site.rstrip("/") + "/"}
    links = "".join(f'<li><a href="/p/{E(x["id"])}/">{E(x["name"])} — {E(x["cat"])}</a></li>' for x in pieces)
    head = (f'<title>Sa</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(site.rstrip("/") + "/")}">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="Sa Editions"><meta property="og:title" content="{E(title)}">'
            f'<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(site.rstrip("/") + "/")}"><meta property="og:image" content="{E(absu(site, "og/home.jpg"))}">'
            f'<meta name="twitter:card" content="summary_large_image"><link rel="sitemap" type="application/xml" href="/sitemap.xml">'
            f'<script type="application/ld+json">{json.dumps(org, ensure_ascii=False)}</script><script type="application/ld+json">{json.dumps(web, ensure_ascii=False)}</script>')
    noscript = f'<noscript><main><h1>Sa Editions — sculptural furniture in limited editions</h1><p>{E(desc)}</p><ul>{links}</ul><p><a href="/about/">About</a> · <a href="/pieces/">All pieces</a></p></main></noscript>'
    return head, noscript
