"""ひな明朝の「たぐり」を絵に組み込んだロゴ（起案者 2026-10-18「たぐりの文字、図形の下に明記するんじゃなくて
うまく図に組み込めない？ひな明朝がいいかも」）。濁点は 2 つの星（スポットライト）に、「り」の払いの先から糸をのばす。"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from glyphs import ftext

HERE = os.path.dirname(os.path.abspath(__file__))
# ひな明朝は Google Fonts の部分フォント（OFL）を gf/ に置く（リポジトリには入れない）
FONT = os.environ.get('HINA', os.path.join(HERE, 'gf', 'Hina_Mincho.ttf'))
OUT = os.environ.get('OUT_DIR', os.path.join(HERE, 'type') + '/')
INK, BG = '#1d1d1f', '#fbeee2'
T = TTFont(FONT); CMAP = T.getBestCmap(); GS = T.getGlyphSet()
DAKUTEN = {'ぐ': {1, 2}}       # 濁点の輪郭（独立した 2 つ）
RI_TIP = (350, -50)            # 「り」の払いの先（字の単位）

def contours(ch):
    rp = RecordingPen(); GS[CMAP[ord(ch)]].draw(rp)
    out, cur = [], []
    for op, a in rp.value:
        cur.append((op, a))
        if op in ('closePath', 'endPath'): out.append(cur); cur = []
    return out

def glyph(ch, x, base, size, skip=(), rot=0.0, vertical=False):
    """字の左端 x・ベースライン base に、大きさ size で置いた輪郭（skip の輪郭は除く）。"""
    k = size / 1000
    pen = SVGPathPen(GS)
    tp = TransformPen(pen, (k, 0, 0, -k, x, base))
    for i, c in enumerate(contours(ch)):
        if i in skip: continue
        for op, a in c: getattr(tp, op)(*a)
    return f'<path d="{pen.getCommands()}" fill="{INK}"/>'

def at(x, base, size, p):      # 字の単位の点を、置いた先の座標へ
    k = size / 1000
    return (x + p[0] * k, base - p[1] * k)

def line(d, sw=2.0, extra=''):
    return f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{extra}/>'

def halo(d, sw):               # 交差させるときの、地の色のふち（糸が字の上を通るように見せる）
    return f'<path d="{d}" fill="none" stroke="{BG}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'

def sparkle(cx, cy, r, sw=1.4, fill=False):
    d = f'M{cx:.1f} {cy - r:.1f} Q{cx:.1f} {cy:.1f} {cx + r:.1f} {cy:.1f} Q{cx:.1f} {cy:.1f} {cx:.1f} {cy + r:.1f} Q{cx:.1f} {cy:.1f} {cx - r:.1f} {cy:.1f} Q{cx:.1f} {cy:.1f} {cx:.1f} {cy - r:.1f}Z'
    return f'<path d="{d}" fill="{INK if fill else "none"}" stroke="{INK}" stroke-width="{sw}" stroke-linejoin="round"/>'

def dakuten_stars(x, base, size):
    """濁点の 2 つの点の位置に、2 つの星（大小）。"""
    a = at(x, base, size, (720, 555)); b = at(x, base, size, (640, 485))
    return sparkle(a[0] + size * 0.02, a[1] - size * 0.02, size * 0.062, 1.0, fill=True) + sparkle(b[0] + size * 0.03, b[1] - size * 0.01, size * 0.04, 0.9, fill=True)

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="たぐり">\n'
            + '\n'.join(body) + '\n</svg>\n')

# ---------------------------------------------------------------- 1 幕の中のたぐり（案 1 の丸い枠の舞台に字を立たせる）
def stage():
    cx, cy, r = 150, 150, 112
    b = []
    a0, a1 = math.radians(186), math.radians(164)
    p0 = (cx + r * math.sin(a0), cy - r * math.cos(a0)); p1 = (cx + r * math.sin(a1), cy - r * math.cos(a1))
    b.append(line(f'M{p0[0]:.1f} {p0[1]:.1f} A{r} {r} 0 1 1 {p1[0]:.1f} {p1[1]:.1f} '
                  f'C{p1[0] + 18:.1f} {p1[1] + 2:.1f} {p1[0] + 34:.1f} {p1[1] + 16:.1f} {p1[0] + 25:.1f} {p1[1] + 25:.1f} '
                  f'C{p1[0] + 16:.1f} {p1[1] + 34:.1f} {p1[0] + 4:.1f} {p1[1] + 21:.1f} {p1[0] + 18:.1f} {p1[1] + 14:.1f} '
                  f'C{p1[0] + 34:.1f} {p1[1] + 7:.1f} {p1[0] + 50:.1f} {p1[1] + 22:.1f} {p1[0] + 56:.1f} {p1[1] + 36:.1f}', 2.3))
    # 幕: 竿・飾り幕・左右の幕（外へ寄せて留め、字の舞台を空ける）
    b.append(line('M70 74 L230 74', 2.0))
    b.append(line('M70 76 ' + ' '.join(f'Q{70 + 16 + 32 * i} 94 {70 + 32 * (i + 1)} 76' for i in range(5)), 1.8))
    b.append(line('M71 78 C70 104 71 126 75 140 C70 160 67 192 66 218', 2.0))
    b.append(line('M80 82 C80 104 78 124 75 140', 1.2))
    b.append(line('M229 78 C230 104 229 126 225 140 C230 160 233 192 234 218', 2.0))
    b.append(line('M220 82 C220 104 222 124 225 140', 1.2))
    for x in (75, 225):
        b.append(f'<circle cx="{x}" cy="141" r="2.8" fill="none" stroke="{INK}" stroke-width="1.4"/>')
        b.append(line(f'M{x - 2} 144 L{x - 3.5} 152 M{x} 144 L{x} 153 M{x + 2} 144 L{x + 3.5} 152', 1.1))
    # 字: 舞台の真ん中。濁点は星に、「り」の払いの先から糸が床へ垂れて、床の線になる
    size, base = 62, 200
    xs = (84, 141, 190)                         # 字ごとの左端（字の幅 1000 を詰めて組む）
    b.append(glyph('た', xs[0] - 141 * size / 1000 + 4, base, size))
    gx = xs[1] - 241 * size / 1000
    b.append(glyph('ぐ', gx, base, size, skip=DAKUTEN['ぐ']))
    b.append(dakuten_stars(gx, base, size))
    rx = xs[2] - 270 * size / 1000
    b.append(glyph('り', rx, base, size))
    tip = at(rx, base, size, RI_TIP)
    b.append(line(f'M{tip[0]:.1f} {tip[1]:.1f} C{tip[0] - 6:.1f} {tip[1] + 8:.1f} {tip[0] - 14:.1f} {tip[1] + 10:.1f} {tip[0] - 12:.1f} {tip[1] + 18:.1f} '
                  f'C{tip[0] - 10:.1f} {tip[1] + 24:.1f} {tip[0] + 2:.1f} {tip[1] + 22:.1f} {tip[0]:.1f} {tip[1] + 16:.1f} '
                  f'C{tip[0] - 2:.1f} {tip[1] + 10:.1f} {tip[0] - 24:.1f} 220 {tip[0] - 40:.1f} 220 L66 220', 1.4))
    b.append(line(f'M{tip[0] + 2:.1f} 220 L234 220', 1.4))
    b.append(line('M88 228 L212 228', 1.0, ' stroke-dasharray="5 4"'))
    b.append(sparkle(150, 118, 6.5, 1.2))
    # 英語の表記は入れない（起案者 2026-10-18「ひな明朝のときの1で、英語表記消しがいいかも」）
    return svg(300, 300, b)

# ---------------------------------------------------------------- 2 糸でたぐる横組み（ヘッダー向け）
def wordmark():
    b = []
    size, base = 96, 118
    xs = (24, 118, 204)
    tx = xs[0] - 141 * size / 1000
    gx = xs[1] - 241 * size / 1000
    rx = xs[2] - 270 * size / 1000
    b.append(glyph('た', tx, base, size))
    b.append(glyph('ぐ', gx, base, size, skip=DAKUTEN['ぐ']))
    b.append(dakuten_stars(gx, base, size))
    b.append(glyph('り', rx, base, size))
    tip = at(rx, base, size, RI_TIP)
    # 「り」の払いから出た糸が、字の下をくぐって左へ戻り、「た」の脚に一巻きして、左で小さな輪になる
    d = (f'M{tip[0]:.1f} {tip[1]:.1f} C{tip[0] - 20:.1f} {tip[1] + 22:.1f} {tip[0] - 60:.1f} {base + 26:.1f} {gx + 30:.1f} {base + 22:.1f} '
         f'C{tx + 90:.1f} {base + 18:.1f} {tx + 40:.1f} {base + 4:.1f} {tx + 34:.1f} {base - 16:.1f} '
         f'C{tx + 30:.1f} {base - 30:.1f} {tx + 10:.1f} {base - 30:.1f} {tx + 8:.1f} {base - 14:.1f} '
         f'C{tx + 6:.1f} {base + 2:.1f} {tx + 24:.1f} {base + 12:.1f} {tx + 6:.1f} {base + 24:.1f} '
         f'C{tx - 6:.1f} {base + 32:.1f} {tx - 4:.1f} {base + 44:.1f} {tx + 8:.1f} {base + 44:.1f}')
    b.append(halo(d, 6.5))
    b.append(line(d, 1.8))
    b.append(sparkle(xs[0] + 16, 22, 5, 1.2)); b.append(sparkle(xs[2] + 70, 34, 3.5, 1.1))
    b.append(f'<path d="{ftext(FONT, "TAGURI", 280, base + 42, 9, spacing=0.6, anchor="end")}" fill="{INK}"/>')
    return svg(300, 172, b)

# ---------------------------------------------------------------- 3 縦組みと糸（幕の間に立つ縦の字）
def vertical():
    b = []
    size = 80
    x0 = 60
    tops = (34, 108, 182)                       # 字ごとの上端
    for ch, top in zip('たぐり', tops):
        base = top + 812 * size / 1000
        if ch == 'ぐ':
            b.append(glyph(ch, x0, base, size, skip=DAKUTEN['ぐ'])); b.append(dakuten_stars(x0, base, size))
        else:
            b.append(glyph(ch, x0, base, size))
        if ch == 'り':
            tip = at(x0, base, size, RI_TIP)
    d = (f'M{tip[0]:.1f} {tip[1]:.1f} C{tip[0] - 8:.1f} {tip[1] + 18:.1f} {tip[0] - 4:.1f} {tip[1] + 34:.1f} {tip[0] + 8:.1f} {tip[1] + 40:.1f} '
         f'C{tip[0] + 22:.1f} {tip[1] + 46:.1f} {tip[0] + 30:.1f} {tip[1] + 30:.1f} {tip[0] + 18:.1f} {tip[1] + 26:.1f} '
         f'C{tip[0] + 6:.1f} {tip[1] + 22:.1f} {tip[0] + 4:.1f} {tip[1] + 44:.1f} {tip[0] + 30:.1f} {tip[1] + 52:.1f} L{tip[0] + 90:.1f} {tip[1] + 52:.1f}')
    b.append(line(d, 1.5))
    # 左右に細い幕（上の竿から垂れる 2 本の線とひだ）
    b.append(line('M30 20 L170 20', 1.6))
    b.append(line('M30 22 C34 80 30 160 22 250 M42 22 C44 70 42 120 38 160', 1.4))
    b.append(line('M170 22 C166 80 170 160 178 250 M158 22 C156 70 158 120 162 160', 1.4))
    b.append(f'<path d="{"".join(ftext(FONT, ch, 146, 120 + i * 12, 9, anchor="middle") for i, ch in enumerate("TAGURI"))}" fill="{INK}"/>')
    b.append(sparkle(150, 60, 4, 1.1))
    return svg(200, 300, b)

for name, f in [('type1-stage', stage), ('type2-wordmark', wordmark), ('type3-vertical', vertical)]:
    open(OUT + name + '.svg', 'w', encoding='utf-8').write(f())
print('ok')
