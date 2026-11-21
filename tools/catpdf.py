#!/usr/bin/env python3
"""Build a downloadable catalogue PDF from a Sa hub booklet.

Mirrors the hub's own makePdf: pages in the booklet's saved order, page links
(internal jumps and web links) kept as PDF link annotations, contents as PDF
bookmarks. Each page image is re-encoded once so the whole file stays under the
site's per-file limit (Cloudflare static assets: 25 MiB).

usage: catpdf.py SA_DATA.json ORDER.json BUNDLE_DIR OUT.pdf COVER.jpg [--doc cat] [--mb 23.5]
  SA_DATA.json  the hub's script#sa-data JSON
  ORDER.json    db orders/<doc> document (or {"order":[...]}); refs are "doc:index"
  BUNDLE_DIR    folder holding v/<doc>-NN.jpg bundles from the hub
"""
import sys, json, io, argparse, random
from PIL import Image

def load(a):
    data = json.load(open(a.data))['docs']
    o = json.load(open(a.order)); o = o.get('data', o); order = o['order']
    return data, order

def page_of(data, r):
    d, i = r.split(':'); return d, int(i), data[d]['pages'][int(i)]

def raw_bytes(bdir, d, p, cache={}):
    c, off, ln = p['v']; f = f'{bdir}/v/{d}-{c:02d}.jpg'
    if f not in cache: cache[f] = open(f, 'rb').read()
    return cache[f][off:off+ln]

def encode(b, q, maxw):
    im = Image.open(io.BytesIO(b)); im = im.convert('L' if im.mode == 'L' else 'RGB')
    if im.width > maxw: im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    out = io.BytesIO(); im.save(out, 'JPEG', quality=q, optimize=True, progressive=True, subsampling=2)
    return out.getvalue(), im.width, im.height, (1 if im.mode == 'L' else 3)

def pdfstr(s):
    try: s.encode('latin-1'); return '(' + s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') + ')'
    except UnicodeEncodeError: return '<FEFF' + s.encode('utf-16-be').hex().upper() + '>'

def n2(v): return ('%.2f' % v).rstrip('0').rstrip('.')

def build(data, order, bdir, doc, budget, maxw=1300):
    N = len(order); pos = {r: x for x, r in enumerate(order)}
    raws = []
    for r in order:
        d, i, p = page_of(data, r); raws.append(raw_bytes(bdir, d, p))
    # pick one quality for the whole book from a sample, then confirm on the full set
    step = max(1, N // 80); sample = list(range(0, N, step))
    def est(q, w):
        s = sum(len(encode(raws[x], q, w)[0]) for x in sample); return s * N / len(sample)
    cands = [(82, 1300), (74, 1300), (66, 1300), (60, 1300), (56, 1300), (56, 1200), (52, 1200),
             (52, 1100), (46, 1100), (42, 1000), (36, 1000), (30, 900)]
    enc = None
    for i, choice in enumerate(cands):
        if i < len(cands) - 1 and est(*choice) > budget * 0.98: continue
        enc = [encode(b, *choice) for b in raws]
        if sum(len(e[0]) for e in enc) < budget: break
    # ---- write the PDF ----
    parts = []; at = [0]; off = {}
    def put(x):
        b = x.encode('latin-1') if isinstance(x, str) else x; parts.append(b); at[0] += len(b)
    def obj(num, *body):
        off[num] = at[0]; put(f'{num} 0 obj\n'); [put(b) for b in body]; put('\nendobj\n')
    P = lambda x: 3 + x * 3; nxt = 3 + N * 3
    links = []
    for x, r in enumerate(order):
        d, i, p = page_of(data, r); L2 = []
        for L in p.get('l', []):
            if L.get('u'): L2.append((L, None))
            elif 'p' in L:
                t = f"{L.get('d', d)}:{L['p']}"
                if t in pos: L2.append((L, t))
        links.append(L2)
    ann = []
    for L2 in links: ann.append(list(range(nxt, nxt + len(L2)))); nxt += len(L2)
    ol = [dict(o) for o in data[doc].get('ol', []) if f"{doc}:{o['p']}" in pos]
    for o in ol: o['pos'] = pos[f"{doc}:{o['p']}"]
    olroot = nxt if ol else 0; nxt += 1 if ol else 0
    for o in ol: o['num'] = nxt; nxt += 1
    put(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    obj(1, f"<< /Type /Catalog /Pages 2 0 R{f' /Outlines {olroot} 0 R /PageMode /UseOutlines' if ol else ''} >>")
    obj(2, f"<< /Type /Pages /Count {N} /Kids [{' '.join(f'{P(x)} 0 R' for x in range(N))}] >>")
    for x, r in enumerate(order):
        d, i, p = page_of(data, r); W, H = p['pw'], p['ph']; b, w, h, c = enc[x]
        a = ann[x]
        obj(P(x), f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {n2(W)} {n2(H)}] /Resources << /XObject << /Im0 {P(x)+1} 0 R >> >> /Contents {P(x)+2} 0 R{(' /Annots [' + ' '.join(f'{v} 0 R' for v in a) + ']') if a else ''} >>")
        obj(P(x)+1, f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace {'/DeviceGray' if c == 1 else '/DeviceRGB'} /BitsPerComponent 8 /Filter /DCTDecode /Length {len(b)} >>\nstream\n", b, '\nendstream')
        cnt = f'q {n2(W)} 0 0 {n2(H)} 0 0 cm /Im0 Do Q'; obj(P(x)+2, f'<< /Length {len(cnt)} >>\nstream\n{cnt}\nendstream')
        for j, (L, t) in enumerate(links[x]):
            x0 = W*L['x']/100; y1 = H - H*L['y']/100; x1 = x0 + W*L['w']/100; y0 = y1 - H*L['h']/100
            if L.get('u'): act = f"/A << /S /URI /URI {pdfstr(L['u'])} >>"
            else:
                td, ti, tp = page_of(data, t); top = tp['ph'] * (1 - L['t']/100) if L.get('t') is not None else tp['ph']
                act = f"/Dest [{P(pos[t])} 0 R /XYZ null {n2(top)} null]"
            obj(a[j], f"<< /Type /Annot /Subtype /Link /Rect [{n2(x0)} {n2(y0)} {n2(x1)} {n2(y1)}] /Border [0 0 0] {act} >>")
    if ol:
        tops = []; last = None
        for o in ol:
            if o.get('d', 0) == 0 or not last: o['kids'] = []; o['par'] = olroot; tops.append(o); last = o
            else: o['par'] = last['num']; last['kids'].append(o)
        def link(a):
            for i, o in enumerate(a): o['prev'] = a[i-1] if i else None; o['next'] = a[i+1] if i+1 < len(a) else None
        link(tops); [link(t['kids']) for t in tops]
        obj(olroot, f"<< /Type /Outlines /First {tops[0]['num']} 0 R /Last {tops[-1]['num']} 0 R /Count {len(tops)} >>")
        for o in ol:
            k = o.get('kids') or []; tp = page_of(data, f"{doc}:{o['p']}")[2]
            obj(o['num'], f"<< /Title {pdfstr(o['n'])} /Parent {o['par']} 0 R" + (f" /Prev {o['prev']['num']} 0 R" if o.get('prev') else '') + (f" /Next {o['next']['num']} 0 R" if o.get('next') else '') + (f" /First {k[0]['num']} 0 R /Last {k[-1]['num']} 0 R /Count -{len(k)}" if k else '') + f" /Dest [{P(o['pos'])} 0 R /XYZ null {n2(tp['ph'])} null] >>")
    xref = at[0]; xs = f'xref\n0 {nxt}\n0000000000 65535 f \n'
    for i in range(1, nxt): xs += (f'{off[i]:010d} 00000 n \n' if i in off else '0000000000 65535 f \n')
    put(xs + f'trailer\n<< /Size {nxt} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n')
    return b''.join(parts), raws[0], choice

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    for x in ('data', 'order', 'bundles', 'out', 'cover'): ap.add_argument(x)
    ap.add_argument('--doc', default='cat'); ap.add_argument('--mb', type=float, default=23.5)
    a = ap.parse_args(); data, order = load(a)
    pdf, cov, choice = build(data, order, a.bundles, a.doc, a.mb * 1048576)
    open(a.out, 'wb').write(pdf)
    im = Image.open(io.BytesIO(cov)).convert('RGB'); im.thumbnail((720, 1100), Image.LANCZOS); im.save(a.cover, 'JPEG', quality=84, optimize=True, progressive=True)
    print(json.dumps({'pages': len(order), 'bytes': len(pdf), 'quality': choice[0], 'width': choice[1], 'cover': [im.width, im.height]}))
