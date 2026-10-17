"""たぐりのロゴ案（黒一色の線画＋手描きの題字）を docs/design/logo/ に書く。"""
# 書体違いの案 1（logo1-fonts/）は、Google Fonts の部分フォント（OFL）を GF_DIR に置いて OUT_DIR=logo1-fonts/ GF_DIR=... python3 make.py で作る
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glyphs import text, arc_text, ftext

INK = '#1d1d1f'
OUT = os.environ.get('OUT_DIR', os.path.dirname(os.path.abspath(__file__)) + '/')

# 題字「たぐり」: 細い一本線で描いた字（1 字 100 の枠、y は下向き）
TAGURI = [
    ['M14 34 L50 30', 'M36 12 C33 38 26 62 12 86', 'M58 52 Q70 49 82 50', 'M56 66 C54 80 62 86 86 84'],
    ['M60 16 C46 32 36 42 30 50 C38 58 50 70 62 86', 'M72 22 L78 32', 'M83 16 L89 26'],
    ['M30 18 C27 36 27 52 31 62 C33 66 36 62 40 54', 'M64 14 C72 38 70 66 42 90'],
]

def lettering(x, y, size, gap=0.9, vertical=False, sw=6.0):
    """左上 (x,y)、1 字の大きさ size。線の太さは 100 の枠で sw。"""
    k = size / 100
    gs = []
    for i, strokes in enumerate(TAGURI):
        dx, dy = (0, i * size * gap) if vertical else (i * size * gap, 0)
        gs.append(f'<g transform="translate({x + dx:.2f} {y + dy:.2f}) scale({k:.4f})">'
                  + ''.join(f'<path d="{d}"/>' for d in strokes) + '</g>')
    return (f'<g fill="none" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">'
            + ''.join(gs) + '</g>')

def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">\n'
            + body + '\n</svg>\n')

def line(d, sw=2.2, extra=''):
    return f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{extra}/>'

def filled(d):
    return f'<path d="{d}" fill="{INK}"/>'

def sparkle(cx, cy, r, sw=1.6):
    return line(f'M{cx} {cy - r} Q{cx} {cy} {cx + r} {cy} Q{cx} {cy} {cx} {cy + r} Q{cx} {cy} {cx - r} {cy} Q{cx} {cy} {cx} {cy - r}Z', sw)

# ---------------------------------------------------------------- 案1 糸の幕（丸い枠の一筆の糸と、開いた幕）
def logo1(font=None, title_size=52, spacing=0.14):
    cx, cy, r = 150, 118, 78
    b = []
    # 円は糸 1 本: 下から右回りにほぼ 1 周し、右下で糸がほどけて結び目の輪をつくる
    a0, a1 = math.radians(180 + 6), math.radians(180 - 14)   # 真上 0・時計回りの角度
    p0 = (cx + r * math.sin(a0), cy - r * math.cos(a0))
    p1 = (cx + r * math.sin(a1), cy - r * math.cos(a1))
    b.append(line(f'M{p0[0]:.1f} {p0[1]:.1f} A{r} {r} 0 1 1 {p1[0]:.1f} {p1[1]:.1f} '
                  f'C{p1[0] + 16:.1f} {p1[1] + 2:.1f} {p1[0] + 30:.1f} {p1[1] + 14:.1f} {p1[0] + 22:.1f} {p1[1] + 22:.1f} '
                  f'C{p1[0] + 14:.1f} {p1[1] + 30:.1f} {p1[0] + 4:.1f} {p1[1] + 18:.1f} {p1[0] + 16:.1f} {p1[1] + 12:.1f} '
                  f'C{p1[0] + 30:.1f} {p1[1] + 6:.1f} {p1[0] + 44:.1f} {p1[1] + 20:.1f} {p1[0] + 50:.1f} {p1[1] + 32:.1f}', 2.4))
    # 幕: 竿・飾り幕（3 つの弧）・左右の幕とひだ・留め紐の房・舞台の床
    b.append(line('M100 64 L200 64', 2.2))
    b.append(line('M100 66 Q116 84 133 67 Q150 85 167 67 Q184 84 200 66', 2.0))
    b.append(line('M101 68 C102 98 110 124 128 138 C118 148 108 164 103 176', 2.2))
    b.append(line('M113 76 C115 102 119 122 128 138', 1.4))
    b.append(line('M199 68 C198 98 190 124 172 138 C182 148 192 164 197 176', 2.2))
    b.append(line('M187 76 C185 102 181 122 172 138', 1.4))
    for x in (128, 172):
        b.append(f'<circle cx="{x}" cy="139" r="3" fill="none" stroke="{INK}" stroke-width="1.6"/>')
        b.append(line(f'M{x - 2.5} 142 L{x - 4} 151 M{x} 142 L{x} 152 M{x + 2.5} 142 L{x + 4} 151', 1.2))
    b.append(line('M98 177 L202 177', 2.2))
    b.append(line('M108 184 L192 184', 1.2, ' stroke-dasharray="6 4"'))
    b.append(sparkle(150, 108, 9, 1.6))
    b.append(sparkle(138, 92, 3.5, 1.1))
    b.append(sparkle(163, 96, 2.8, 1.1))
    if font:
        # 題字・欧文・添え書きを 1 つの書体で組む（起案者 2026-10-18「1いいけど、日本語フォントださい」）
        b.append(filled(ftext(font, 'たぐり', 150, 276, title_size, spacing=spacing, anchor='middle')))
        b.append(filled(ftext(font, 'TAGURI', 150, 297, 10, spacing=0.5, anchor='middle')))
        b.append(line('M84 309.5 L104 309.5 M196 309.5 L216 309.5', 1))
        b.append(filled(ftext(font, '観劇の縁をたぐる', 150, 313, 8, spacing=0.3, anchor='middle')))
    else:
        b.append(lettering(87, 222, 44, gap=0.98, sw=5.2))
        b.append(filled(text('TAGURI', 150, 290, 10, spacing=0.5, anchor='middle')))
        b.append(filled(text('観劇の縁をたぐる', 150, 303.5, 7.5, spacing=0.25, anchor='middle')))
        b.append(line('M84 300.5 L104 300.5 M196 300.5 L216 300.5', 1))
    return svg(300, 326 if font else 316, '\n'.join(b), 'たぐり')

# ---------------------------------------------------------------- 案2 オペラグラスの糸
def logo2():
    b = []
    for x in (70, 132):
        b.append(f'<circle cx="{x}" cy="104" r="26" fill="none" stroke="{INK}" stroke-width="2.4"/>')
        b.append(f'<circle cx="{x}" cy="104" r="19" fill="none" stroke="{INK}" stroke-width="1.2"/>')
        b.append(line(f'M{x - 12} 82 L{x - 9} 70 L{x + 9} 70 L{x + 12} 82', 2.2))
        b.append(line(f'M{x - 9} 96 Q{x - 6} 90 {x} 89', 1.4))       # 光
    b.append(line('M92 92 Q101 84 110 92', 2.2))
    b.append(line('M96 100 Q101 96 106 100', 1.4))
    # 柄は糸になってほどけ、下で小さな糸玉へ
    b.append(line('M46 114 C34 130 30 150 36 168 C40 182 54 184 56 172 C58 160 42 160 42 174 C42 190 56 198 70 196', 2.2))
    b.append(f'<circle cx="80" cy="198" r="10" fill="none" stroke="{INK}" stroke-width="2.2"/>')
    b.append(line('M72 192 Q80 202 88 192 M71 199 Q80 208 89 199 M74 190 Q84 196 86 206', 1.2))
    b.append(sparkle(160, 60, 6, 1.4))
    b.append(sparkle(38, 66, 3.5, 1.1))
    b.append(lettering(180, 70, 44, gap=0.96, sw=5.2))
    b.append(filled(text('TAGURI', 245, 146, 10, spacing=0.5, anchor='middle')))
    b.append(line('M180 160 L310 160', 1))
    b.append(filled(text('観劇の縁をたぐる', 245, 176, 8, spacing=0.3, anchor='middle')))
    return svg(330, 224, '\n'.join(b), 'たぐり')

# ---------------------------------------------------------------- 案3 スポットライトの丸印
def logo3():
    cx, cy = 150, 150
    b = []
    b.append(f'<circle cx="{cx}" cy="{cy}" r="122" fill="none" stroke="{INK}" stroke-width="2.2"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="{INK}" stroke-width="1.2"/>')
    b.append(filled(arc_text('TAGURI  ·  THEATRE  LOG', cx, cy, 109, 0, 11, spacing=0.28)))
    b.append(filled(arc_text('観劇の縁をたぐる', cx, cy, 109, 180, 11, spacing=0.4, inside=True)))
    for deg in (90, 270):
        x, y = cx + 109 * math.sin(math.radians(deg)), cy - 109 * math.cos(math.radians(deg))
        b.append(sparkle(round(x, 1), round(y, 1), 4, 1.2))
    # 光: 上半分に放つ線と半円
    b.append(line(f'M{cx - 20} 112 A20 20 0 0 1 {cx + 20} 112', 1.8))
    for i in range(-6, 7):
        a = math.radians(i * 13)
        r0, r1 = 26, 44 if i % 2 == 0 else 37
        b.append(line(f'M{cx + r0 * math.sin(a):.1f} {112 - r0 * math.cos(a):.1f} L{cx + r1 * math.sin(a):.1f} {112 - r1 * math.cos(a):.1f}', 1.3))
    b.append(line(f'M{cx - 60} 114 L{cx + 60} 114', 1.4))
    b.append(lettering(cx - 66, 124, 46, gap=0.97, sw=5.4))
    # 下: 幕のすそ（弧の並び）と舞台の二重線
    # 下: 舞台のふち（フットライトの小さな灯りと光）と二重線
    b.append(line('M84 200 L216 200', 1.4))
    for i in range(7):
        x = 96 + i * 18
        b.append(line(f'M{x - 4} 200 A4 4 0 0 1 {x + 4} 200', 1.3))
        b.append(line(f'M{x} 192 L{x} 189 M{x - 5} 194 L{x - 7} 192 M{x + 5} 194 L{x + 7} 192', 1))
    b.append(line('M90 207 L210 207 M100 213 L200 213', 1.2))
    return svg(300, 300, '\n'.join(b), 'たぐり')

# ---------------------------------------------------------------- 案4 縦書きと針の糸
def logo4():
    b = []
    b.append(lettering(70, 70, 64, gap=0.96, vertical=True, sw=4.8))
    # 右に 1 本の糸: 上の針の穴から垂れて、下で結ぶ
    b.append(line('M168 30 L168 40', 2.2))
    b.append(f'<ellipse cx="168" cy="48" rx="3" ry="7" fill="none" stroke="{INK}" stroke-width="2"/>')
    b.append(line('M168 56 L168 66', 2.2))
    b.append(line('M168 28 L168 22', 2.6))
    b.append(line('M168 66 C168 140 160 200 164 270 C166 300 176 300 174 286 C172 274 158 280 166 298 C172 312 184 316 190 326', 1.6))
    # 星と細い斜めの線
    b.append(line('M30 40 L120 22', 1))
    b.append(line('M40 330 L150 300', 1))
    b.append(sparkle(140, 40, 6, 1.3))
    b.append(sparkle(46, 120, 3.5, 1.1))
    b.append(sparkle(150, 230, 3, 1.1))
    # 左の小さな縦書き
    for i, ch in enumerate('観劇の縁をたぐる'):
        b.append(filled(text(ch, 40, 196 + i * 13, 10, anchor='middle')))
    b.append(filled(text('TAGURI', 112, 344, 9, spacing=0.5, anchor='middle')))
    return svg(220, 360, '\n'.join(b), 'たぐり')

# ---------------------------------------------------------------- 案5 半券と糸
def logo5():
    b = []
    b.append(line('M30 60 H222 A9 9 0 0 0 240 60 H270 V170 H240 A9 9 0 0 0 222 170 H30 Z', 2.2))
    b.append(line('M34 66 H218 M34 164 H218', 0.9))
    b.append(line('M231 74 V156', 1.6, ' stroke-dasharray="0.1 6"'))
    b.append(lettering(52, 88, 52, gap=0.96, sw=5.0))
    b.append(filled(text('TAGURI · 観劇の縁をたぐる', 126, 156, 8, spacing=0.2, anchor='middle')))
    # 半券の穴に糸を通し、外へたぐる
    b.append(f'<circle cx="255" cy="96" r="5" fill="none" stroke="{INK}" stroke-width="1.8"/>')
    b.append(line('M255 91 C262 70 286 70 288 92 C290 116 262 124 264 146 C266 168 290 168 300 186 C306 198 300 210 290 206 C282 202 288 190 298 196', 1.8))
    b.append(sparkle(254, 132, 5, 1.2))
    b.append(filled(text('No.', 254, 154, 7, anchor='middle')))
    return svg(320, 230, '\n'.join(b), 'たぐり')

import os
GF = os.environ.get('GF_DIR')
if GF:
    for key, label in [('Kaisei_Decol_wght_400', 'Kaisei Decol'), ('Zen_Old_Mincho_wght_400', 'Zen Old Mincho'),
                       ('Shippori_Mincho_B1_wght_500', 'Shippori Mincho B1'), ('Klee_One_wght_400', 'Klee One'),
                       ('Hina_Mincho', 'Hina Mincho'), ('Zen_Antique_Soft', 'Zen Antique Soft'),
                       ('Yuji_Syuku', 'Yuji Syuku'), ('Zen_Kurenaido', 'Zen Kurenaido')]:
        open(f'{OUT}font-{key}.svg', 'w', encoding='utf-8').write(logo1(f'{GF}/{key}.ttf'))
    raise SystemExit
for name, f in [('logo1-thread-curtain', logo1), ('logo2-opera-glasses', logo2), ('logo3-spotlight-seal', logo3),
                ('logo4-vertical-needle', logo4), ('logo5-ticket-thread', logo5)]:
    open(OUT + name + '.svg', 'w', encoding='utf-8').write(f())
print('ok')
