"""Tsukimi Rounded の「たぐり」を絵に組み込んだロゴ（起案者 2026-10-18「このフォントで入れてみて。私のイメージは
劇場のあたたかみ、きらきら、毛糸、糸、スタイリッシュなんだけどどこかあたたかみ丸みのあるデザイン」）。
「ぐ」の濁点は 2 つの星に、「り」の払いの先から糸をのばし、糸の先は毛糸玉。線の端はすべて丸める。"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from glyphs import ftext

HERE = os.path.dirname(os.path.abspath(__file__))
# Tsukimi Rounded は Google Fonts の部分フォント（OFL）を gf/ に置く（リポジトリには入れない）
WEIGHT = os.environ.get('WEIGHT', '400')
FONT = os.path.join(HERE, 'gf', f'Tsukimi_{WEIGHT}.ttf')
OUT = os.environ.get('OUT_DIR', os.path.join(HERE, 'tsukimi') + '/')
INK, BG = '#1d1d1f', '#fbeee2'
T = TTFont(FONT); CMAP = T.getBestCmap(); GS = T.getGlyphSet()
# 字の部品（DecomposingRecordingPen でほどいた輪郭の番号）と、字の単位の位置
DAKUTEN = {0, 1}                       # 「ぐ」の濁点
STAR_BIG, STAR_SMALL = (841, 748), (740, 694)
RI_TIP = (478, -60)                    # 「り」の右の払いの先
TA_START = (135, 590)                  # 「た」の横画の左の端
INK_LEFT = {'た': 129, 'ぐ': 299, 'り': 267}

def contours(ch):
    rp = DecomposingRecordingPen(GS); GS[CMAP[ord(ch)]].draw(rp)
    out, cur = [], []
    for op, a in rp.value:
        cur.append((op, a))
        if op in ('closePath', 'endPath'): out.append(cur); cur = []
    return out

def glyph(ch, x, base, size, skip=()):
    k = size / 1000
    pen = SVGPathPen(GS); tp = TransformPen(pen, (k, 0, 0, -k, x, base))
    for i, c in enumerate(contours(ch)):
        if i in skip: continue
        for op, a in c: getattr(tp, op)(*a)
    return f'<path d="{pen.getCommands()}" fill="{INK}"/>'

def at(x, base, size, p):
    return (x + p[0] * size / 1000, base - p[1] * size / 1000)

def line(d, sw=2.0, extra=''):
    return f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{extra}/>'

def halo(d, sw):
    return f'<path d="{d}" fill="none" stroke="{BG}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'

def sparkle(cx, cy, r, sw=1.2, fill=True):
    # 丸みのある 4 つ角の星（角の先をとがらせすぎない）
    q = r * 0.18
    d = (f'M{cx:.1f} {cy - r:.1f} C{cx + q:.1f} {cy - q:.1f} {cx + q:.1f} {cy - q:.1f} {cx + r:.1f} {cy:.1f} '
         f'C{cx + q:.1f} {cy + q:.1f} {cx + q:.1f} {cy + q:.1f} {cx:.1f} {cy + r:.1f} '
         f'C{cx - q:.1f} {cy + q:.1f} {cx - q:.1f} {cy + q:.1f} {cx - r:.1f} {cy:.1f} '
         f'C{cx - q:.1f} {cy - q:.1f} {cx - q:.1f} {cy - q:.1f} {cx:.1f} {cy - r:.1f}Z')
    return f'<path d="{d}" fill="{INK if fill else "none"}" stroke="{INK}" stroke-width="{sw}" stroke-linejoin="round"/>'

def yarn(cx, cy, r, sw=1.6):
    """毛糸玉: 丸と、ゆるく弧を描いて巻いた 3 本の筋＋交わる 1 本（小さくてもつぶれない本数）。"""
    def pt(deg):
        t = math.radians(deg); return cx + r * math.cos(t), cy + r * math.sin(t)
    b = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="{sw}"/>']
    for a1, a2 in [(235, 55), (272, 18), (198, 92), (150, 320)]:
        (x1, y1), (x2, y2) = pt(a1), pt(a2)
        b.append(f'<path d="M{x1:.1f} {y1:.1f} A{r * 1.6:.1f} {r * 1.6:.1f} 0 0 1 {x2:.1f} {y2:.1f}" fill="none" stroke="{INK}" stroke-width="{sw * 0.75:.2f}" stroke-linecap="round"/>')
    return ''.join(b)

def word(x0, base, size, gap):
    """「たぐり」を組む。gap は字の墨の左端どうしの間隔（px）。返り値: (svg, 各字の左端 x)"""
    xs = [x0 + i * gap - INK_LEFT[ch] * size / 1000 for i, ch in enumerate('たぐり')]
    b = [glyph('た', xs[0], base, size), glyph('ぐ', xs[1], base, size, skip=DAKUTEN)]
    a = at(xs[1], base, size, STAR_BIG); c = at(xs[1], base, size, STAR_SMALL)
    b.append(sparkle(a[0] + size * 0.01, a[1] - size * 0.01, size * 0.085, 0.8))
    b.append(sparkle(c[0], c[1] + size * 0.01, size * 0.05, 0.7))
    b.append(glyph('り', xs[2], base, size))
    return ''.join(b), xs

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="たぐり">\n'
            + '\n'.join(body) + '\n</svg>\n')

def small(text, x, y, size, spacing=0.6, anchor='middle'):
    return f'<path d="{ftext(FONT, text, x, y, size, spacing=spacing, anchor=anchor)}" fill="{INK}"/>'

# ---------------------------------------------------------------- 1 糸でたぐる横組み（毛糸玉で終わる）
def wordmark():
    size, base = 92, 116
    w, xs = word(30, base, size, 86)
    tip = at(xs[2], base, size, RI_TIP)
    tx = xs[0] + INK_LEFT['た'] * size / 1000
    # 「り」の払いの先から出た糸が、字の下をゆるく通って途中で 1 つ輪をつくり、「た」の下の毛糸玉へ
    y0 = base + 22
    d = (f'M{tip[0]:.1f} {tip[1]:.1f} C{tip[0] - 10:.1f} {tip[1] + 20:.1f} {tip[0] - 50:.1f} {y0 + 4:.1f} {tx + 150:.1f} {y0 + 2:.1f} '
         f'C{tx + 128:.1f} {y0 + 1:.1f} {tx + 118:.1f} {y0 - 14:.1f} {tx + 108:.1f} {y0 - 12:.1f} '
         f'C{tx + 96:.1f} {y0 - 10:.1f} {tx + 100:.1f} {y0 + 6:.1f} {tx + 112:.1f} {y0 + 4:.1f} '
         f'C{tx + 124:.1f} {y0 + 2:.1f} {tx + 120:.1f} {y0 - 6:.1f} {tx + 100:.1f} {y0 - 2:.1f} '
         f'C{tx + 70:.1f} {y0 + 4:.1f} {tx + 30:.1f} {y0 + 2:.1f} {tx + 12:.1f} {y0 + 10:.1f}')
    return svg(320, 176, [w, line(d, 1.8), yarn(tx + 2, y0 + 16, 10),
                          sparkle(tx + 10, 24, 5), sparkle(xs[2] + 92, 30, 3.5), sparkle(xs[2] + 104, 46, 2.2),
                          small('TAGURI', 300, base + 48, 8.5, anchor='end')])

# ---------------------------------------------------------------- 2 毛糸玉からほどけた糸が字になる
def unwind():
    size, base = 84, 112
    w, xs = word(86, base, size, 78)
    start = at(xs[0], base, size, TA_START)
    tip = at(xs[2], base, size, RI_TIP)
    yx, yy = 40, 120
    # 毛糸玉からのびた糸が、ゆるく弧を描いて「た」の横画の頭へつながる
    d1 = f'M{yx + 8:.1f} {yy - 7:.1f} C{yx + 18:.1f} {yy - 40:.1f} {start[0] - 34:.1f} {start[1] - 30:.1f} {start[0] - 8:.1f} {start[1] - 6:.1f} L{start[0] + 2:.1f} {start[1]:.1f}'
    # 「り」の払いの先からは糸がのびて、小さく輪をつくり、星へ届く
    d2 = (f'M{tip[0]:.1f} {tip[1]:.1f} C{tip[0] + 2:.1f} {tip[1] + 18:.1f} {tip[0] + 22:.1f} {tip[1] + 22:.1f} {tip[0] + 26:.1f} {tip[1] + 10:.1f} '
          f'C{tip[0] + 30:.1f} {tip[1] - 2:.1f} {tip[0] + 14:.1f} {tip[1] - 6:.1f} {tip[0] + 14:.1f} {tip[1] + 6:.1f} '
          f'C{tip[0] + 14:.1f} {tip[1] + 22:.1f} {tip[0] + 44:.1f} {tip[1] + 14:.1f} {tip[0] + 52:.1f} {tip[1] - 14:.1f}')
    star = (tip[0] + 56, tip[1] - 22)
    return svg(340, 176, [w, line(d1, 1.8), yarn(yx, yy, 14, 1.7), line(d2, 1.8),
                          sparkle(star[0], star[1], 7), sparkle(star[0] + 12, star[1] - 14, 3),
                          sparkle(xs[0] + 6, 30, 3),
                          small('TAGURI', 170, 164, 8.5)])

# ---------------------------------------------------------------- 3 幕の中のたぐり（丸い舞台）
def stage():
    cx, cy, r = 150, 150, 112
    b = []
    a0, a1 = math.radians(186), math.radians(164)
    p0 = (cx + r * math.sin(a0), cy - r * math.cos(a0)); p1 = (cx + r * math.sin(a1), cy - r * math.cos(a1))
    b.append(line(f'M{p0[0]:.1f} {p0[1]:.1f} A{r} {r} 0 1 1 {p1[0]:.1f} {p1[1]:.1f} '
                  f'C{p1[0] + 18:.1f} {p1[1] + 2:.1f} {p1[0] + 30:.1f} {p1[1] + 14:.1f} {p1[0] + 36:.1f} {p1[1] + 24:.1f}', 2.2))
    b.append(yarn(p1[0] + 44, p1[1] + 34, 11, 1.8))
    b.append(line('M70 74 L230 74', 2.0))
    b.append(line('M70 76 ' + ' '.join(f'Q{70 + 16 + 32 * i} 94 {70 + 32 * (i + 1)} 76' for i in range(5)), 1.8))
    b.append(line('M71 78 C70 104 71 126 75 140 C70 156 67 182 66 210', 2.0))
    b.append(line('M80 82 C80 104 78 124 75 140', 1.2))
    b.append(line('M229 78 C230 104 229 126 225 140 C230 156 233 182 234 210', 2.0))
    b.append(line('M220 82 C220 104 222 124 225 140', 1.2))
    for x in (75, 225):
        b.append(f'<circle cx="{x}" cy="141" r="2.8" fill="none" stroke="{INK}" stroke-width="1.4"/>')
        b.append(line(f'M{x - 2} 144 L{x - 3.5} 152 M{x} 144 L{x} 153 M{x + 2} 144 L{x + 3.5} 152', 1.1))
    size, base = 52, 186
    w, xs = word(92, base, size, 48)
    b.append(w)
    tip = at(xs[2], base, size, RI_TIP)
    b.append(line(f'M{tip[0]:.1f} {tip[1]:.1f} C{tip[0] - 4:.1f} {tip[1] + 10:.1f} {tip[0] - 14:.1f} {tip[1] + 10:.1f} {tip[0] - 12:.1f} {tip[1] + 18:.1f} '
                  f'C{tip[0] - 10:.1f} {tip[1] + 24:.1f} {tip[0] + 2:.1f} {tip[1] + 22:.1f} {tip[0]:.1f} {tip[1] + 16:.1f} '
                  f'C{tip[0] - 2:.1f} {tip[1] + 12:.1f} {tip[0] - 24:.1f} 212 {tip[0] - 40:.1f} 212 L64 212', 1.4))
    b.append(line(f'M{tip[0] + 2:.1f} 212 L236 212', 1.4))
    b.append(line('M86 219 L214 219', 1.0, ' stroke-dasharray="0.1 5"'))
    b.append(sparkle(150, 114, 6)); b.append(sparkle(134, 106, 2.4)); b.append(sparkle(166, 106, 2.4))
    b.append(small('TAGURI', 150, 238, 8))
    return svg(300, 316, b)

os.makedirs(OUT, exist_ok=True)
for name, f in [('tsukimi1-wordmark', wordmark), ('tsukimi2-unwind', unwind), ('tsukimi3-stage', stage)]:
    open(f'{OUT}{name}-{WEIGHT}.svg', 'w', encoding='utf-8').write(f())
print('ok', WEIGHT)
