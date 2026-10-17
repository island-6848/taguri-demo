"""Zen Kaku Gothic New（web/assets/fonts の分割 woff2）の字形を SVG の path にする。"""
import glob, math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONTS = {}
def _load(weight):
    if weight not in FONTS:
        fs = []
        for f in sorted(glob.glob(f'/home/user/taguri-demo/web/assets/fonts/zen-kaku-gothic-new/zkgn{weight}-*.woff2')):
            t = TTFont(f)
            fs.append((t, t.getBestCmap(), t.getGlyphSet()))
        FONTS[weight] = fs
    return FONTS[weight]

def glyph(ch, weight=400):
    for t, cmap, gs in _load(weight):
        if ord(ch) in cmap:
            name = cmap[ord(ch)]
            return gs, name, gs[name].width, t['head'].unitsPerEm
    raise KeyError(ch)

def _path(gs, name, a, b, c, d, e, f):
    pen = SVGPathPen(gs)
    gs[name].draw(TransformPen(pen, (a, b, c, d, e, f)))
    return pen.getCommands()

def text(s, x, y, size, spacing=0.0, anchor='start', weight=400):
    """横組みの 1 行。spacing は字送りに足す em。y はベースライン。"""
    adv = []
    for ch in s:
        if ch == ' ':
            adv.append(size * 0.3 + size * spacing); continue
        gs, n, w, upm = glyph(ch, weight)
        adv.append(w / upm * size + size * spacing)
    total = sum(adv) - size * spacing
    x0 = x - (total if anchor == 'end' else total / 2 if anchor == 'middle' else 0)
    out = []
    for ch, a in zip(s, adv):
        if ch != ' ':
            gs, n, w, upm = glyph(ch, weight)
            k = size / upm
            out.append(_path(gs, n, k, 0, 0, -k, x0, y))
        x0 += a
    return ' '.join(out)

def arc_text(s, cx, cy, r, center_deg, size, spacing=0.0, inside=False, weight=400):
    """円に沿った文字。center_deg は真上が 0、時計回り。inside=True は円の下側に、正立して左から読める並び。"""
    advs = []
    for ch in s:
        if ch == ' ':
            advs.append(size * 0.3 + size * spacing); continue
        gs, n, w, upm = glyph(ch, weight)
        advs.append(w / upm * size + size * spacing)
    total = sum(advs) - size * spacing
    out, pos = [], -total / 2
    oy = size * 0.36
    for ch, a in zip(s, advs):
        if ch != ' ':
            gs, n, w, upm = glyph(ch, weight)
            k = size / upm
            mid = pos + w * k / 2
            if inside:
                th = math.radians(center_deg) - mid / r
                rot = th + math.pi
            else:
                th = math.radians(center_deg) + mid / r
                rot = th
            px, py = cx + r * math.sin(th), cy - r * math.cos(th)
            cs, sn, hw = math.cos(rot), math.sin(rot), w * k / 2
            out.append(_path(gs, n, k * cs, k * sn, k * sn, -k * cs, px - hw * cs - oy * sn, py - hw * sn + oy * cs))
        pos += a
    return ' '.join(out)
