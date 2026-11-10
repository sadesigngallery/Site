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

# Brand names. BRAND is the name Google should show; ALT_NAMES are the other
# spellings people search for (WebSite / Organization "alternateName").
BRAND = "Sa-editions"
ALT_NAMES = ["Sa Editions", "Sa Edition", "Sa-edition", "Sa Design", "Sa"]
FOUNDERS = ["Alireza Emtiaz", "Saqar Khakdan"]
WHATSAPP = "14039229905"
# The contact e-mail is read once from state/site.json ("email") by build().
CFG = {"email": "Sadesigngallery@gmail.com"}
ABOUT_LINE = ("Sa-editions — also known as Sa Editions, or simply Sa — is the work of SA, "
              "a design house founded in 2010 by architects Alireza Emtiaz and Saqar Khakdan.")
# Persian letter names; a piece whose Persian name is one letter, or one of these names, belongs to "Letters".
LETTER_NAMES = {"سین", "میم", "نون", "صاد", "واو", "کاف", "عین", "طا", "رِ", "جیم", "شین", "ضاد", "ظا", "غین", "قاف", "گاف", "لام", "دال", "ذال", "الف"}


def mail():
    return CFG["email"]


def is_letter(fa):
    f = (fa or "").strip()
    return len(f) == 1 or f in LETTER_NAMES


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
.crumb{font-size:.8rem;color:#555;margin:0 0 4px}.crumb a{text-decoration:none}.ed .por{font-weight:500;color:#111}"""


def page(site, path, title, desc, body, og=None, jsonld=None, lang="en"):
    canon = site.rstrip("/") + path
    j = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>' for o in (jsonld or []))
    ogi = f'<meta property="og:image" content="{E(absu(site, og))}"><meta name="twitter:image" content="{E(absu(site, og))}">' if og else ""
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(canon)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(canon)}">{ogi}<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>{CSS}</style>{j}</head><body>
<header class="sb"><a href="/" aria-label="{BRAND}"><img src="/sa-logo.png" alt="{BRAND} logo" width="120" height="46"></a><span>EDITIONS</span></header>
<p class="tg">Sculptural furniture, handmade in limited editions</p>
{body}
<footer><nav><a href="/pieces/">All pieces</a><a href="/collections/">Collections</a><a href="/designers/">Designers</a><a href="/editions/">Editions</a><a href="/about/">About</a><a href="/contact/">Contact</a><a href="https://www.instagram.com/sa_editions_/" rel="noopener">Instagram</a><a href="mailto:{E(mail())}">Email</a><a href="/#/discover">Discover</a><a href="/#/trade">Download</a></nav>
<p>Copyright © 2026 {BRAND}. All rights reserved</p></footer></body></html>"""


def short(text, n=155):
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def _pdf_font():
    """A Unicode font for the spec sheets (Ā, ×, Ø, quotes); Helvetica if none is installed."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for reg, bold in (("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),):
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("SaR", reg)); pdfmetrics.registerFont(TTFont("SaB", bold))
            return "SaR", "SaB", False
    return "Helvetica", "Helvetica-Bold", True


def _latin(t, strict):
    # Persian script cannot be shaped by the PDF library: drop it (the Latin name is kept).
    t = re.sub(r"[؀-ۿ‌‏]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.encode("latin-1", "replace").decode("latin-1") if strict else t


SPEC_PDF = "spec/sa-editions-spec-sheets.pdf"  # one file, one A4 page per piece (keeps the site under 1,000 files)


def spec_book(out_dir):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    os.makedirs(os.path.join(out_dir, "spec"), exist_ok=True)
    c = canvas.Canvas(os.path.join(out_dir, SPEC_PDF), pagesize=A4)
    c.setTitle(f"{BRAND} — specification sheets"); c.setAuthor(BRAND); c.setSubject("Specification sheets")
    c._sa_font = _pdf_font()
    return c


def spec_page(c, out_dir, x, cat1, site):
    """One A4 sheet on canvas c: picture, dimensions, specification, edition, contact."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    R_, B_, strict = c._sa_font
    L = lambda t: _latin(t, strict)
    W, H = A4; m = 48
    c.bookmarkPage(x["id"]); c.addOutlineEntry(x["name"], x["id"])
    y = H - m
    lg = os.path.join(out_dir, "sa-logo.png")
    if os.path.exists(lg):
        im = Image.open(lg); k = 34 / im.height
        c.drawImage(ImageReader(lg), m, y - 34, width=im.width * k, height=34, mask="auto")
    c.setFont(R_, 8); c.drawRightString(W - m, y - 12, BRAND.upper() + "  ·  SPECIFICATION SHEET"); c.drawRightString(W - m, y - 24, site.replace("https://", ""))
    y -= 62
    c.setFont(B_, 24); c.drawString(m, y, L(x["name"]))
    c.setFont(R_, 10); y -= 16
    c.drawString(m, y, L(cat1.upper() + (f"  ·  {x['year']}" if x.get("year") else "")))
    y -= 14
    src = x.get("hero") or x.get("thumb")
    if src and os.path.exists(os.path.join(out_dir, src.split("?")[0])):
        im = Image.open(os.path.join(out_dir, src.split("?")[0])).convert("RGBA")
        bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if bb: im = im.crop(bb)
        bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.getchannel("A"))
        bg.thumbnail((1000, 1000))
        import io
        buf = io.BytesIO(); bg.save(buf, "JPEG", quality=82, optimize=True); buf.seek(0)
        bw, bh = W - 2 * m, 300; k = min(bw / bg.width, bh / bg.height)
        iw, ih = bg.width * k, bg.height * k
        c.drawImage(ImageReader(buf), m + (bw - iw) / 2, y - bh + (bh - ih) / 2, width=iw, height=ih)
        y -= bh + 18
    if x.get("dims"):
        c.setStrokeColorRGB(.85, .85, .85); c.line(m, y, W - m, y)
        cw = (W - 2 * m) / len(x["dims"])
        for n, (k_, v) in enumerate(x["dims"]):
            cx = m + cw * n + cw / 2
            c.setFont(R_, 8); c.drawCentredString(cx, y - 14, L(k_)); c.setFont(B_, 14); c.drawCentredString(cx, y - 32, L(v))
        y -= 42; c.line(m, y, W - m, y); y -= 20
    rows = list(x["spec"])
    for k_, v in rows:
        c.setFont(R_, 9); c.setFillColorRGB(.33, .33, .33); c.drawString(m, y, L(k_)); c.setFillColorRGB(0, 0, 0)
        words = L(v).split(" "); line = ""; first = True
        for w in words:
            t = (line + " " + w).strip()
            if c.stringWidth(t, R_, 9) > W - 2 * m - 120:
                c.drawString(m + 120, y, line); y -= 12; line = w
            else:
                line = t
        c.drawString(m + 120, y, line); y -= 15
        if y < 120: break
    c.setFont(B_, 10); y -= 6
    c.drawString(m, y, L(" · ".join(t for t in [x.get("edition"), x.get("editionNote"), "Price on request"] if t)))
    c.setFont(R_, 8); c.setFillColorRGB(.33, .33, .33)
    c.drawString(m, m + 14, L(f"Enquiries: {mail()}  ·  WhatsApp +1 403 922 9905  ·  instagram.com/sa_editions_"))
    c.drawString(m, m, L(f"{site.rstrip('/')}/p/{x['id']}/  ·  Copyright © 2026 {BRAND}"))
    c.showPage()


def enquiry_href(name):
    from urllib.parse import quote
    body = (f"Hello, I would like to enquire about {name}.\n\nName:\nCountry:\n"
            "I am a: private client / architect / gallery\nMessage:\n")
    return f"mailto:{mail()}?subject={quote(BRAND + ' — enquiry: ' + name)}&body={quote(body)}"


def tile(x):
    return (f'<a href="/p/{E(x["id"])}/"><img src="/{E(x["thumb"] or x["hero"] or "")}" alt="{E(x["name"])} by {BRAND}" loading="lazy">'
            f'<b>{E(x["name"])}</b><small>{E(x["edition"])}</small></a>')


def write(out_dir, path, text):
    d = os.path.join(out_dir, path.strip("/"))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(text)


def build(out_dir, tools_dir, site, assets, email=None):
    if email:
        CFG["email"] = email
    data = scrape(out_dir, tools_dir)
    # brand files for the static pages
    for name, src in assets.items():
        if src and os.path.exists(src):
            with open(src, "rb") as f, open(os.path.join(out_dir, name), "wb") as g: g.write(f.read())
    pieces = data["pieces"]
    root = site.rstrip("/") + "/"
    org = {"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "alternateName": ALT_NAMES,
           "url": root, "logo": absu(site, "sa-logo.png"), "foundingDate": "2010",
           "founder": [{"@type": "Person", "name": n} for n in FOUNDERS],
           "email": mail(), "sameAs": ["https://www.instagram.com/sa_editions_/"],
           "contactPoint": [{"@type": "ContactPoint", "contactType": "sales", "telephone": "+98-939-713-3918", "areaServed": "IR"},
                            {"@type": "ContactPoint", "contactType": "sales", "telephone": "+1-403-922-9905", "areaServed": "CA"}]}

    def crumbs(*items):
        el = [{"@type": "ListItem", "position": 1, "name": BRAND, "item": root}]
        for n, (name, path) in enumerate(items):
            el.append({"@type": "ListItem", "position": n + 2, "name": name, "item": site.rstrip("/") + path})
        return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": el}

    urls = [("/", [absu(site, "og/home.jpg")]), ("/pieces/", []), ("/collections/", []), ("/designers/", []),
            ("/editions/", []), ("/about/", []), ("/contact/", [])]
    # piece pages
    book = spec_book(out_dir)
    for pno, x in enumerate(pieces, 1):
        pid = x["id"]; path = f"/p/{pid}/"
        imgs = [i for i in [x["hero"]] + x["photos"] + ([x["drawing"]] if x["drawing"] else []) if i]
        og = og_image(out_dir, x["hero"] or x["thumb"], pid)
        cat1 = re.sub(r"s$", "", x["cat"]) if x["cat"] else ""
        spec_rows = list(x["spec"])
        if not any(k.lower().startswith("design") and k != "Designed" for k, _ in spec_rows):
            at = 1 if spec_rows and spec_rows[0][0] == "Category" else 0
            spec_rows.insert(at, ("Designers", " & ".join(FOUNDERS)))
        x["spec"] = spec_rows
        spec_page(book, out_dir, x, cat1, site)
        pdf = f"{SPEC_PDF}#page={pno}"
        title = f"{x['name']} — {cat1} | {BRAND}"
        d0 = " ".join(x["desc"]) if x["desc"] else ""
        mat = dict(spec_rows).get("Material", "")
        desc = short(f"{x['name']} ({x['fa']}), {cat1.lower()} by {BRAND}. {x['edition']}{'. ' if x['edition'] else ''}{mat + '. ' if mat else ''}{d0}")
        dims = "".join(f"<div><small>{E(k)}</small><b>{E(v)}</b></div>" for k, v in x["dims"])
        spec = "".join(f"<dt>{E(k)}</dt><dd>{E(v)}</dd>" for k, v in spec_rows)
        ph = "".join(f'<img src="/{E(i)}" alt="{E(x["name"])} {E(cat1.lower())} by {BRAND} — photo {n + 1}" loading="lazy">' for n, i in enumerate(x["photos"]))
        dr = f'<img src="/{E(x["drawing"])}" alt="{E(x["name"])} — technical drawing" loading="lazy">' if x["drawing"] else ""
        hero = f'<img class="hero" src="/{E(x["hero"])}" alt="{E(x["name"])} {E(cat1.lower())} by {BRAND}" width="1600" height="1600">' if x["hero"] else ""
        yt = (f'<div style="position:relative;aspect-ratio:16/9;margin:6px 0 18px;background:#000"><iframe src="https://www.youtube-nocookie.com/embed/{E(x["yt"])}?rel=0&modestbranding=1&playsinline=1" title="{E(x["name"])} — film" loading="lazy" style="position:absolute;inset:0;width:100%;height:100%;border:0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>') if x.get("yt") else ""
        ed = (f'<div class="ed">{"<b>" + E(x["edition"]) + "</b>" if x["edition"] else ""}{"<span>" + E(x["editionNote"]) + "</span>" if x["editionNote"] else ""}'
              f'<span class="por">Price on request</span></div>')
        rel = [y for y in pieces if y["catId"] == x["catId"] and y["id"] != pid]
        if len(rel) < 3:
            rel += [y for y in pieces if y.get("grp", [""])[0] == x.get("grp", [""])[0] and y["id"] != pid and y not in rel]
        rel = rel[:4]
        related = (f"<h2>Related pieces</h2><div class='grid'>{''.join(tile(y) for y in rel)}</div>") if rel else ""
        body = f"""<main><p class="crumb"><a href="/pieces/">All pieces</a> / {E(x['cat'])}</p><h1>{E(x['name'])}</h1><p class="fa" lang="fa" dir="rtl">{E(x['fa'])}</p><p class="cat">{E(cat1)}{' · ' + str(x['year']) if x['year'] else ''}</p>
{hero}<div class="dims">{dims}</div>{ed}{yt}<div class="desc">{''.join('<p>' + E(p) + '</p>' for p in x['desc'])}</div><dl>{spec}</dl>
<div class="cta"><a class="p" href="{E(enquiry_href(x['name']))}">Enquire</a><a href="https://wa.me/{WHATSAPP}?text={E(('Hello, about ' + x['name']).replace(' ', '%20'))}" rel="noopener">WhatsApp</a><a href="/{E(pdf)}" rel="noopener">Spec sheet (PDF)</a><a href="/#/p/{E(pid)}">View in the catalogue</a></div>
<div class="ph">{ph}{dr}</div>{related}</main>"""
        prod = {"@context": "https://schema.org", "@type": "Product", "name": x["name"], "alternateName": x["fa"], "sku": pid,
                "category": cat1, "description": d0 or desc, "image": [absu(site, i) for i in imgs], "url": site.rstrip("/") + path,
                "brand": {"@type": "Brand", "name": BRAND}, "manufacturer": {"@type": "Organization", "name": BRAND}}
        if mat: prod["material"] = mat
        write(out_dir, path, page(site, path, title, desc, body, og, [prod, crumbs(("All pieces", "/pieces/"), (x["name"], path))]))
        urls.append((path, [absu(site, i) for i in imgs]))
    book.save()
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
        return (f'<a href="/p/{E(x["id"])}/"><span class="eb" style="width:{bw + 4:.0f}px"><img src="/{E(x["thumb"])}" alt="{E(x["name"])} by {BRAND}" loading="lazy" '
                f'style="height:{ih:.1f}px;width:{iw:.1f}px;left:{left:.1f}px;bottom:{bot:.1f}px"></span><b>{E(x["name"])}</b><small>{E(x["edition"])}</small></a>')

    def block(c, xs):
        g = xs[0].get("grp") or ["", c.upper()]
        head = f"<h2 class='ch'><b>{E(g[0])} /</b> {E(g[1])}</h2>"
        if xs[0].get("catId") == "dining" and all(eqtile(x) for x in xs):
            return head + "<div class='eq'>" + "".join(eqtile(x) for x in xs) + "</div>"
        return head + "<div class='grid'>" + "".join(tile(x) for x in xs) + "</div>"
    body = "<main><h1>All pieces</h1>" + "".join(block(c, xs) for c, xs in groups.items()) + "</main>"
    write(out_dir, "/pieces/", page(site, "/pieces/", f"All pieces — sculptural furniture, pianos and lighting | {BRAND}",
                                    short(f"The full {BRAND} collection: dining tables, desks, side and coffee tables, consoles, lighting, benches, chairs, armchairs, sofas and pianos — each handmade in a limited, numbered edition."),
                                    body, "og/home.jpg", [org, crumbs(("All pieces", "/pieces/"))]))
    # collections (only groupings that follow from the catalogue itself)
    letters = [x for x in pieces if is_letter(x["fa"])]
    pianos = [x for x in pieces if x["catId"] == "piano"]
    lt = "".join(f'<a href="/p/{E(x["id"])}/"><img src="/{E(x["thumb"] or x["hero"] or "")}" alt="{E(x["name"])} by {BRAND}" loading="lazy">'
                 f'<b>{E(x["name"])}</b><small lang="fa" dir="rtl">{E(x["fa"])}</small></a>' for x in letters)
    body = ("<main><h1>Collections</h1>"
            + (f"<h2 class='ch'><b>Letters</b></h2><p style='text-align:center'>Pieces named after letters of the Persian alphabet.</p><div class='grid'>{lt}</div>" if letters else "")
            + (f"<h2 class='ch'><b>Pianos</b></h2><div class='grid'>{''.join(tile(x) for x in pianos)}</div>" if pianos else "")
            + '<div class="cta"><a class="p" href="/pieces/">All pieces</a></div></main>')
    write(out_dir, "/collections/", page(site, "/collections/", f"Collections — Letters and Pianos | {BRAND}",
                                         short(f"{BRAND} collections: pieces named after letters of the Persian alphabet, and limited-edition pianos."),
                                         body, "og/home.jpg", [org, crumbs(("Collections", "/collections/"))]))
    # about + designers
    a = data.get("about") or {"title": "About SA", "paras": [], "bios": []}
    btxt = [b["text"] for b in a["bios"]]
    bio_html = lambda b: f'<div class="bio">{"<img src=" + chr(34) + "/" + E(b["img"]) + chr(34) + " alt=" + chr(34) + E(b["name"]) + chr(34) + ">" if b.get("img") else ""}<div><b>{E(b["name"])}</b><p>{E(b["text"])}</p></div></div>'
    bios = "".join(bio_html(b) for b in a["bios"])
    body = (f"<main><h1>{E(a['title'])}</h1><p>{E(ABOUT_LINE)}</p>" + "".join(f"<p>{E(p)}</p>" for p in a["paras"] if p not in btxt)
            + (f"<h2>Founders</h2>{bios}" if bios else "")
            + '<div class="cta"><a class="p" href="/">Enter the catalogue</a><a href="/designers/">Designers</a><a href="/contact/">Contact</a></div></main>')
    write(out_dir, "/about/", page(site, "/about/", f"About {BRAND} — Alireza Emtiaz & Saqar Khakdan",
                                   short(f"{ABOUT_LINE} Every piece is made by hand in a limited edition."),
                                   body, "og/home.jpg", [org, crumbs(("About", "/about/"))]))
    people = [{"@context": "https://schema.org", "@type": "Person", "name": b["name"], "description": b["text"],
               "worksFor": {"@type": "Organization", "name": BRAND}, **({"image": absu(site, b["img"])} if b.get("img") else {})} for b in a["bios"]]
    body = (f"<main><h1>Designers</h1><p style='text-align:center'>Every {BRAND} piece is designed by the studio's two founders.</p>{bios}"
            f"<h2>Pieces</h2><div class='grid'>{''.join(tile(x) for x in pieces)}</div></main>")
    write(out_dir, "/designers/", page(site, "/designers/", f"Designers — Alireza Emtiaz & Saqar Khakdan | {BRAND}",
                                       short(f"Alireza Emtiaz and Saqar Khakdan, the architects and designers behind {BRAND}, and the pieces they have designed."),
                                       body, "og/home.jpg", people + [crumbs(("Designers", "/designers/"))]))
    # editions
    sizes = {}
    for x in pieces:
        m_ = re.search(r"(\d[\d,]*)", x["edition"] or "")
        key = int(m_.group(1).replace(",", "")) if m_ and "one" not in (x["edition"] or "").lower() else 1
        sizes.setdefault(key, []).append(x)
    rows = "".join(f"<h2>{'One of a kind' if k == 1 else 'Edition of ' + str(k)}</h2><div class='grid'>"
                   + "".join(f'<a href="/p/{E(x["id"])}/"><img src="/{E(x["thumb"] or x["hero"] or "")}" alt="{E(x["name"])} by {BRAND}" loading="lazy"><b>{E(x["name"])}</b><small>{E(x["editionNote"] or x["edition"])}</small></a>' for x in xs)
                   + "</div>" for k, xs in sorted(sizes.items()))
    body = (f"<main><h1>Editions</h1><p>Every {BRAND} piece is made by hand under the founders' direct supervision, using a stencil technique developed in-house. "
            "This is what allows each work to exist in a limited, numbered edition, or as a single piece. The size of each edition is fixed and is shown on every piece, "
            "together with how many of the edition have been sold.</p>" + rows + "</main>")
    write(out_dir, "/editions/", page(site, "/editions/", f"Editions — limited, numbered and one-of-a-kind pieces | {BRAND}",
                                      short(f"How {BRAND} editions work: every piece is handmade in a limited, numbered edition or as a single piece. Edition sizes and pieces sold."),
                                      body, "og/home.jpg", [org, crumbs(("Editions", "/editions/"))]))
    # contact
    body = (f"<main><h1>Contact</h1><p style='text-align:center'>All prices are on request. Tell us which piece you are interested in, where you are, "
            "and whether you are a private client, an architect or a gallery.</p>"
            f"<dl><dt>Email</dt><dd><a href='mailto:{E(mail())}'>{E(mail())}</a></dd><dt>WhatsApp</dt><dd><a href='https://wa.me/{WHATSAPP}' rel='noopener'>+1 403 922 9905</a></dd>"
            "<dt>Phone (Iran)</dt><dd><a href='tel:+989397133918'>+98 939 713 3918</a></dd><dt>Phone (Canada)</dt><dd><a href='tel:+14039229905'>+1 403 922 9905</a></dd>"
            "<dt>Instagram</dt><dd><a href='https://www.instagram.com/sa_editions_/' rel='noopener'>@sa_editions_</a></dd></dl>"
            f'<div class="cta"><a class="p" href="{E(enquiry_href("a piece"))}">Send an enquiry</a><a href="/#/contact">Contact in the catalogue</a></div></main>')
    write(out_dir, "/contact/", page(site, "/contact/", f"Contact — enquiries and prices on request | {BRAND}",
                                     short(f"Contact {BRAND}: enquiries, prices on request, trade and gallery requests by email, WhatsApp or Instagram."),
                                     body, "og/home.jpg", [org, crumbs(("Contact", "/contact/"))]))
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


HOME_MARK = ("<!--sa-seo-->", "<!--/sa-seo-->")


def home_head(site, org, pieces):
    title = f"{BRAND} (Sa Editions) — Sculptural furniture, handmade in limited editions"
    desc = f"{BRAND}: sculptural furniture, pianos and lighting by architects Alireza Emtiaz and Saqar Khakdan, handmade in limited, numbered editions since 2010."
    web = {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "alternateName": ALT_NAMES, "url": site.rstrip("/") + "/"}
    links = "".join(f'<li><a href="/p/{E(x["id"])}/">{E(x["name"])} — {E(x["cat"])}</a></li>' for x in pieces)
    head = (HOME_MARK[0] + f'<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(site.rstrip("/") + "/")}">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{E(title)}">'
            f'<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(site.rstrip("/") + "/")}"><meta property="og:image" content="{E(absu(site, "og/home.jpg"))}">'
            f'<meta name="twitter:card" content="summary_large_image"><link rel="sitemap" type="application/xml" href="/sitemap.xml">'
            f'<script type="application/ld+json">{json.dumps(org, ensure_ascii=False)}</script><script type="application/ld+json">{json.dumps(web, ensure_ascii=False)}</script>' + HOME_MARK[1])
    noscript = (f'<noscript><main><h1>{BRAND}</h1><p>{E(ABOUT_LINE)}</p><p>{E(desc)}</p><ul>{links}</ul>'
                '<p><a href="/pieces/">All pieces</a> · <a href="/collections/">Collections</a> · <a href="/designers/">Designers</a> · '
                '<a href="/editions/">Editions</a> · <a href="/about/">About</a> · <a href="/contact/">Contact</a></p></main></noscript>')
    return head, noscript
