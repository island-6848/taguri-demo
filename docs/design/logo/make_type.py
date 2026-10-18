"""ひな明朝の「たぐり」を絵に組み込んだロゴ（起案者 2026-10-18「たぐりの文字、図形の下に明記するんじゃなくて
うまく図に組み込めない？ひな明朝がいいかも」）。濁点は 2 つの星（スポットライト）に、「り」の払いの先から糸をのばす。"""
import math, os, sys
from pathlib import Path
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
    pen = SVGPathPen(GS, ntos=lambda v: f'{v:.1f}'.rstrip('0').rstrip('.'))
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

def taper_ring(cx, cy, r, a0, a1, tail, w_top, w_bottom, tip=0.55):
    """強弱のある丸の線と、ほどけた先（起案者 2026-10-18「毛糸っぽくしなくてよい。線の太さ、縁の下ほど太くて
    上ほど細くして強弱つけて」）。太さは高さで決める（丸の上端 w_top → 下端 w_bottom）。先は細くしながら終わる。
    線の太さを場所ごとに変えるため、左右の縁を計算して塗りの形にし、両端は丸く閉じる。
    a0→a1 は真上 0・時計回りの角度。tail は丸の終わりからの 3 次曲線（終わりの点からの相対）。"""
    if a1 <= a0: a1 += 360
    P = lambda th: (cx + r * math.sin(math.radians(th)), cy - r * math.cos(math.radians(th)))
    pts = [P(a0 + (a1 - a0) * i / 140) for i in range(141)]   # 埋め込む大きさを抑えるため、点は少なめ
    n_ring = len(pts)
    cur = pts[-1]
    for c1, c2, e in tail:
        q1, q2, q3 = [(cur[0] + v[0], cur[1] + v[1]) for v in (c1, c2, e)]
        for i in range(1, 17):
            t = i / 16; u = 1 - t
            pts.append((u ** 3 * cur[0] + 3 * u * u * t * q1[0] + 3 * u * t * t * q2[0] + t ** 3 * q3[0],
                        u ** 3 * cur[1] + 3 * u * u * t * q1[1] + 3 * u * t * t * q2[1] + t ** 3 * q3[1]))
        cur = q3
    def width(i, y):
        w = w_top + (w_bottom - w_top) * min(max((y - (cy - r)) / (2 * r), 0), 1)
        if i >= n_ring:                       # ほどけた先は、終わりに向かって細く
            f = (i - n_ring) / max(len(pts) - n_ring - 1, 1)
            w *= 1 - (1 - tip) * f
        return w
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a, c = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tx, ty = c[0] - a[0], c[1] - a[1]; l = math.hypot(tx, ty) or 1
        nx, ny = -ty / l, tx / l
        h = width(i, y) / 2
        left.append((x + nx * h, y + ny * h)); right.append((x - nx * h, y - ny * h))
    h0, h1 = width(0, pts[0][1]) / 2, width(len(pts) - 1, pts[-1][1]) / 2
    d = 'M' + ' '.join(f'{x:.1f} {y:.1f}' for x, y in left)
    d += f' A{h1:.1f} {h1:.1f} 0 0 1 {right[-1][0]:.1f} {right[-1][1]:.1f}'
    d += ' L' + ' '.join(f'{x:.1f} {y:.1f}' for x, y in reversed(right))
    d += f' A{h0:.1f} {h0:.1f} 0 0 1 {left[0][0]:.1f} {left[0][1]:.1f}Z'
    return f'<path d="{d}" fill="{INK}"/>'

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
    b.append(taper_ring(cx, cy, r, 186, 164, [((18, 2), (34, 16), (25, 25)), ((-9, 9), (-21, -4), (-7, -11)), ((16, -7), (32, 8), (38, 22))], 1.6, 5.0))
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
    # 字の墨の上下の真ん中（字の単位で 381）を、丸の中心の高さ cy に合わせる（起案者 2026-10-18「円に対して下よりなので、中央を通るように」）
    # 起案者 2026-10-18「たぐりちょっと右寄りかも。たぐりの文字もうちょっとだけ下でもいい」: 左へ 5、下へ 5
    size = 57
    base = cy + 381 * size / 1000 + 5
    xs = (87, 139, 184)                         # 字ごとの左端（字の幅 1000 を詰めて組む）
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
    # 字の上の星は 3 つを左右対称に（1 つだとかたよって見える。起案者 2026-10-18）
    b.append(sparkle(150, 106, 5, 1.1)); b.append(sparkle(135, 111, 2.6, 1.0)); b.append(sparkle(165, 111, 2.6, 1.0))
    # 英語の表記は入れない（起案者 2026-10-18「ひな明朝のときの1で、英語表記消しがいいかも」）
    return svg(300, 312, b)

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

# ---------------------------------------------------------------- 小さい版（タブ・ホーム画面のアイコン）
def icon(small=False):
    """強弱のある丸の中にオペラグラス（起案者 2026-10-18「アイコンにするときはぐ、じゃなくてオペラグラスのイラスト」）。
    small=True は 16〜32px 向け: 線を太くし、レンズの内側の輪・光・星を省き、糸の先は短いはね 1 つ。"""
    cx, cy, r = 31, 29.5, 22.5
    # 16〜32px では先の輪がつぶれるので、ほどけた先は短いはね 1 つにする
    tail = [((4, 1), (8, 4), (10, 9))] if small else [((5, 1), (9, 4), (7, 7.5)), ((-2, 2.5), (-5.5, -0.5), (-2.5, -2.5)), ((3.5, -2), (8.5, 1), (10.5, 4.5))]
    b = [taper_ring(cx, cy, r, 192, 160, tail, 2.4 if small else 1.4, 5.2 if small else 3.8)]
    lw = 2.6 if small else 1.9           # オペラグラスの線
    lr = 6.6 if small else 6.2           # レンズの半径
    lx, rx, ly = cx - 8, cx + 8, cy + 3
    for x in (lx, rx):
        b.append(f'<circle cx="{x}" cy="{ly}" r="{lr}" fill="none" stroke="{INK}" stroke-width="{lw}"/>')
        # 接眼の筒（レンズの上の台形）
        b.append(line(f'M{x - 3.6:.1f} {ly - lr - 0.6:.1f} L{x - 2.6:.1f} {ly - lr - 4.2:.1f} L{x + 2.6:.1f} {ly - lr - 4.2:.1f} L{x + 3.6:.1f} {ly - lr - 0.6:.1f}', lw * 0.85))
        if not small:
            b.append(f'<circle cx="{x}" cy="{ly}" r="{lr - 2.4:.1f}" fill="none" stroke="{INK}" stroke-width="0.9"/>')
            b.append(line(f'M{x - 3.2:.1f} {ly - 0.6:.1f} Q{x - 2.6:.1f} {ly - 3:.1f} {x - 0.4:.1f} {ly - 3.4:.1f}', 0.9))   # レンズの光
    # 二つのレンズをつなぐ橋
    b.append(line(f'M{lx + lr - 0.4:.1f} {ly - 2:.1f} Q{cx} {ly - 6:.1f} {rx - lr + 0.4:.1f} {ly - 2:.1f}', lw * 0.85))
    # 柄（左のレンズから斜め下へ）
    b.append(line(f'M{lx - lr * 0.7:.1f} {ly + lr * 0.7:.1f} L{lx - lr * 0.7 - 5:.1f} {ly + lr * 0.7 + 6:.1f}', lw))
    if not small:   # 上にきらきら（劇場のあかり）
        b.append(sparkle(cx, 15.5, 2.6, 0.6, fill=True))
        b.append(sparkle(cx - 6.5, 17.5, 1.4, 0.5, fill=True)); b.append(sparkle(cx + 6.5, 17.5, 1.4, 0.5, fill=True))
    return svg(64, 64, b)

# ---------------------------------------------------------------- サイトに入れる（ヘッダー・タブ・ホーム画面）
def row():
    """横組み: オペラグラスのアイコンと「たぐり」（電話の幅の上の帯に置く）。"""
    inner = icon(True).split('\n', 1)[1].rsplit('</svg>', 1)[0]
    size, base = 44, 32 + 381 * 44 / 1000
    gap = 41
    xs = [74 + i * gap - {'た': 141, 'ぐ': 241, 'り': 270}[ch] * size / 1000 for i, ch in enumerate('たぐり')]
    b = [f'<g>{inner}</g>', glyph('た', xs[0], base, size), glyph('ぐ', xs[1], base, size, skip=DAKUTEN['ぐ']),
         dakuten_stars(xs[1], base, size), glyph('り', xs[2], base, size)]
    return svg(200, 64, b)

def inline(svg_text, cls, label):
    """HTML に埋め込む形: 色は currentColor（置いた場所の文字の色＝暗い表示でも読める）、読み上げは label。"""
    body = svg_text.split('\n', 1)[1].rsplit('</svg>', 1)[0].replace(INK, 'currentColor')
    vb = svg_text.split('viewBox="', 1)[1].split('"', 1)[0]
    return f'<svg class="{cls}" viewBox="{vb}" role="img" aria-label="{label}">{body}</svg>'

def favicon_href():
    """タブの絵（data: で埋め込む）。暗いタブでは明るい色にする（タブの地はページの明暗と一致しない）。"""
    from urllib.parse import quote
    body = icon(True).split('\n', 1)[1].rsplit('</svg>', 1)[0]
    style = ('<style>[fill="#1d1d1f"]{fill:#1d1d1f}[stroke="#1d1d1f"]{stroke:#1d1d1f}'
             '@media(prefers-color-scheme:dark){[fill="#1d1d1f"]{fill:#f2f2f3}[stroke="#1d1d1f"]{stroke:#f2f2f3}}</style>')
    return 'data:image/svg+xml,' + quote(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{style}{body}</svg>', safe='')

def embed(index_html):
    """web/index.html のロゴ（<!--brand-->〜<!--/brand-->）とタブの絵（<!--favicon-->〜<!--/favicon-->）を差し替える。"""
    t = Path(index_html).read_text(encoding='utf-8')
    # 帯の a には行き先の押し口の形が付くので、ロゴは span のまま（以前と同じ）
    brand = ('<!--brand--><span class="tglock brand">'
             + inline(stage(), 'tgl-full', 'たぐり') + inline(row(), 'tgl-row', 'たぐり') + '</span><!--/brand-->')
    fav = (f'<!--favicon--><link rel="icon" href="{favicon_href()}">'
           '<link rel="apple-touch-icon" href="/taguri-demo/assets/logo/apple-touch-icon.png"><!--/favicon-->')
    import re
    t = re.sub(r'<!--brand-->.*?<!--/brand-->', lambda m: brand, t, flags=re.S)
    t = re.sub(r'<!--favicon-->.*?<!--/favicon-->', lambda m: fav, t, flags=re.S)
    Path(index_html).write_text(t, encoding='utf-8')

if len(sys.argv) > 2 and sys.argv[1] == '--embed':
    embed(sys.argv[2]); print('embedded'); raise SystemExit

for name, f in [('icon', icon), ('icon-small', lambda: icon(True)), ('row', row), ('type1-stage', stage), ('type2-wordmark', wordmark), ('type3-vertical', vertical)]:
    open(OUT + name + '.svg', 'w', encoding='utf-8').write(f())
print('ok')
