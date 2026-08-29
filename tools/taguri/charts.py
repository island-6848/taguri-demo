#!/usr/bin/env python3
"""記録を見返す画面の図。**inline SVG だけで描く**（外部の描画ライブラリを読まない）。

## 形を先に決め、色を最後に置く

| 図 | データの仕事 | 選んだ形 | なぜ |
|---|---|---|---|
| 年ごとの観劇本数 | 時系列の量 | **縦棒** | 年は順序のある離散の軸である。折れ線にすると年の間を補間しているように読める |
| ◎○△× の分布 | 極性（合っていた ↔ 合っていなかった） | **1 本の積み上げ帯＋発散の配色** | 4 段は順序のある尺度で、◎ と × は反対の意味を持つ。種類の違うものを並べる categorical では意味が落ちる |
| 劇場の頻度 | 識別ごとの量（順位つき） | **横棒** | 劇場名は長いので、縦棒だとラベルが斜めになって読めない |
| 観劇の年輪 | 2 つの周期（月と年）に置いた 1 件ずつ | **極座標の散布図** | 年ごとの本数も月ごとの合計も、**季節の癖が毎年くり返しているのかを答えられない。** 年を半径・月を角度に置くと、同じ方角に点が縦に並ぶかどうかで分かる |
| 行った劇場の地図 | 位置と、位置ごとの量 | **地図＋大きさで量を表す点** | 頻度の横棒は順位を答えるが**距離と広がりを答えない。** 埋まっていない土地が見えることがこの図の中身である |

**地図は 2 枚に分ける。** 全国は都道府県の単位、東京は館の単位である ──
**東京の 15 館は全国の地図では 1 か所に重なり、同心円の模様になる**（実際に描いて確かめた）。

**配色は検証済みの既定パレット**（categorical 4 スロットと、発散の対 blue↔red・中点は灰）。
`node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100" --mode light` は
**全項目 PASS、ただしコントラストが 3:1 を下回るという WARN が出る** ── その救済として
**直接ラベルと表の姿を必ず添える**（この 2 つは省略できない）。

**点数と平均★は出さない。** 件数と分母を必ず添える（企画書 2 章）。
"""

from __future__ import annotations

import collections
import html
import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import icons as IC                                                   # noqa: E402
import venues as VN                                                  # noqa: E402

E = lambda s: html.escape(str(s))                                   # noqa: E731

# 発散の対（blue ↔ red）。**中点は灰**で、色相を置かない。
# 各腕は 2 段で、薄い側は同じ色相の不透明度で作る（腕の中は順序 ＝ 明度で表す）
VERDICT_FILL = {"◎": "var(--pos)", "○": "var(--pos)", "△": "var(--neg)", "×": "var(--neg)"}
VERDICT_OP = {"◎": 1.0, "○": 0.42, "△": 0.42, "×": 1.0}
VERDICT_ORDER = ("◎", "○", "△", "×", "まだ判断できない")


def _table(head: list[str], rows: list[list]) -> str:
    """**表の姿。** コントラストの WARN の救済であり、色を読めない場合の唯一の経路である。"""
    th = "".join(f"<th>{E(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{E(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<details class="tv"><summary>数字で見る</summary>'
            f'<table class="tbl mini"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></details>')


def years_panel(works: list[dict]) -> str:
    """年ごとの観劇本数。**これは「事実」であって推定ではない。**

    **本人が既に知っていることを、分かるようになった価値として数えない**（企画書 2 章）。
    ここに置くのは「自分がこれだけ観てきた」という事実そのものを眺めるためで、
    好みの発見は「比べる」の画面が受け持つ。
    """
    cnt = collections.Counter((w.get("first_date") or "")[:4] for w in works
                              if (w.get("first_date") or "")[:4].isdigit())
    if not cnt:
        return ""
    ys = sorted(cnt)
    mx = max(cnt.values())
    w, gap, h = 46, 12, 150
    width = len(ys) * (w + gap)
    bars = []
    for i, y in enumerate(ys):
        v = cnt[y]
        bh = max(round(v / mx * h), 2)
        x = i * (w + gap)
        bars.append(
            # 4px の丸みを基線側に付けない ── 量の端だけを丸める（marks の規則）
            f'<g class="bar"><title>{E(y)} 年 ── {v} 作品</title>'
            f'<rect x="{x}" y="{h - bh + 20}" width="{w}" height="{bh}" rx="4"'
            f' fill="var(--s1)"/>'
            f'<text x="{x + w / 2}" y="{h - bh + 14}" class="vlab">{v}</text>'
            f'<text x="{x + w / 2}" y="{h + 38}" class="alab">{E(y)}</text></g>')
    return f"""<section class="card">
{IC.h2("chart", "年ごとの本数")}
<p class="lead">記録から数えた作品数です。当日券・招待・ファンクラブ経由は購入確認メールに
残らないので、<b>どの年も実際より少なめに出ます。</b></p>
<svg class="viz" viewBox="0 -6 {width} {h + 48}" width="{width}" height="{h + 48}"
 role="img" aria-label="年ごとの観劇作品数">{"".join(bars)}</svg>
{_table(["年", "作品数"], [[y, cnt[y]] for y in ys])}</section>"""


def verdict_panel(works: list[dict]) -> str:
    """◎○△× の分布。**発散の帯 1 本で描く。**"""
    cnt = collections.Counter(w.get("verdict") or "未評価" for w in works)
    order = [g for g in VERDICT_ORDER if cnt.get(g)] + (["未評価"] if cnt.get("未評価") else [])
    tot = sum(cnt[g] for g in order)
    if not tot:
        return ""
    segs, labs, x = [], [], 0.0
    W = 100.0
    for g in order:
        wpc = cnt[g] / tot * W
        fill = VERDICT_FILL.get(g, "var(--unk)")
        op = VERDICT_OP.get(g, 1.0)
        # **2px の隙間を空ける**（積み上げの段どうしが溶けない）
        segs.append(f'<g class="seg"><title>{E(g)} ── {cnt[g]} 件（{cnt[g] / tot:.0%}）</title>'
                    f'<rect x="{x:.3f}%" y="0" width="{max(wpc - 0.25, 0.2):.3f}%" height="26"'
                    f' fill="{fill}" fill-opacity="{op}" rx="3"/></g>')
        if wpc >= 7:      # **すべての段にラベルを置かない**（狭い段は表の姿で読む）
            labs.append(f'<span class="dl" style="left:{x + wpc / 2:.2f}%">'
                        f'{E(g)} <b>{cnt[g]}</b></span>')
        x += wpc
    return f"""<section class="card">
{IC.h2("star", "付けた評価の分布", f'<span class="badge part">分母 {tot} 作品</span>')}
<p class="lead"><b>基準は「自分に合っていたか」で、作品の出来ではありません。</b>
◎ 側と × 側を左右に分けて置いています。おすすめの材料に数えるのは <b>◎ だけ</b>です。</p>
<div class="dbar"><svg viewBox="0 0 100 26" width="100%" height="26" preserveAspectRatio="none"
 role="img" aria-label="評価の分布">{"".join(segs)}</svg>
<div class="dlabs">{"".join(labs)}</div></div>
{_table(["評価", "件数", "割合"], [[g, cnt[g], f"{cnt[g] / tot:.0%}"] for g in order])}</section>"""


def _venue_block(cnt: collections.Counter, top: int, unit: str, note: str) -> str:
    """劇場の頻度、1 つの数え方ぶん。**棒と表を 1 組にする**（`_table` の規約と同じ）。"""
    rows = cnt.most_common(top)
    if not rows:
        return ""
    mx = rows[0][1]
    bars = "".join(
        f'<div class="hb" title="{E(name)} ── {v} {unit}">'
        f'<span class="hb-l">{E(name)}</span>'
        f'<span class="hb-t"><span class="hb-f" style="width:{v / mx * 100:.1f}%"></span></span>'
        f'<span class="hb-v">{v}</span></div>' for name, v in rows)
    return f"""<div class="vsub">{unit}で数える <span class="badge part">上位 {len(rows)} 館</span></div>
<p class="lead">{note}</p>
<div class="hbars">{bars}</div>
{_table(["劇場", unit], [[n, v] for n, v in rows])}"""


_VENUE_SEP = re.compile(r"[ 　・･\-‐‑‒–—―−]")


def _venue_squash(name: str) -> str:
    """劇場名を突き合わせるための鍵。**空白・中点・ダッシュの違いだけを吸収する。**

    公演ページの劇場名（`venues`）と、購入確認メールから抽出した劇場名（`shows` の
    `venue`）は出どころが別なので、同じ劇場でも表記が違うことがある
    （実測 ──「COOL JAPAN PARK OSAKA・TTホール」と「COOL JAPAN PARK OSAKA TTホール」）。
    """
    return _VENUE_SEP.sub("", unicodedata.normalize("NFKC", name or ""))


def venue_panel(rated: list[dict], top: int = 10,
                shows_by_key: dict[str, list[str]] | None = None) -> str:
    """劇場の頻度。**横棒だが SVG では描かない。**

    **`preserveAspectRatio="none"` の SVG に文字を置くと、横に引き伸ばされて読めなくなる**
    （実際に 1 度そうなった ── viewBox の幅 100 を 950px に写したので文字が 9.5 倍に伸びた）。
    横棒は**ラベル・棒・数値の 3 列**でしかないので、素の HTML で組むほうが確実である。

    ## 数え方を 2 つ出す（起案者の指摘・2026-08-25）

    「これって『本』単位で数えるのと『公演』単位で数える２つがあるといいな」。
    **同じ公演を何度も観た分が、それまでは 1 本にまとめられていた。** 1 つの公演に
    3 回通った劇場と、1 回しか行っていない劇場が同じ「1 本」で並ぶと、
    **実際に足を運んだ回数という意味での「よく行く」が図から消える。**

    **本の数え方は変えていない**（`venues` は作品ごとに重複を除いた集合なので、
    同じ劇場に 3 回通っても 1 本のまま数える）。

    ## 公演の数え方は、近似ではなく回ごとの記録から作る

    最初は「集合の各劇場に観た回数（`times`）を足す」だけで済ませようとしたが、
    **ツアーで複数の劇場に掛かった作品（実測 2 本）で数字が壊れることが、
    実データで画面を見て分かった。** 『ＣＲＩＭＩＮＡＬ ＦＯＵＲ』は
    IMM THEATER で 12 回・COOL JAPAN PARK OSAKA で 4 回（times は合計の 16）
    なのに、集合の両方に 16 を足すと**両方が 16 回行ったことになってしまう。**

    **回ごとの内訳（`shows_by_key`）が引ける作品は、そちらを正とする。** 劇場が
    1 つしか無い作品はどちらの数え方でも同じ答えになるので、内訳が要るのは
    複数の劇場を持つ作品だけである。**内訳の劇場名は `_venue_squash` で本の劇場名に
    寄せる**（出どころが違うので表記が揺れる） ── 寄せられた分は本の表記のまま出し、
    寄せられない分（読み取れなかった劇場名など）だけそのまま出す。
    **内訳が引けない作品（手で足した記録など）は、集合に `times` を足す元の近似に戻す**
    ── 手で足した記録は劇場を 1 つしか持たないので、この近似で数字が壊れることはない。
    """
    cnt_work = collections.Counter(v for r in rated for v in (r.get("venues") or []))
    if not cnt_work:
        return ""
    shows_by_key = shows_by_key or {}
    cnt_show: collections.Counter = collections.Counter()
    for r in rated:
        venues = r.get("venues") or []
        shows = shows_by_key.get(r["key"]) if len(venues) > 1 else None
        if not shows:
            for v in venues:
                cnt_show[v] += r.get("times") or 1
            continue
        by_squash = {_venue_squash(v): v for v in venues}
        for s in shows:
            cnt_show[by_squash.get(_venue_squash(s), s)] += 1
    work = _venue_block(cnt_work, top, "本",
                         "同じ公演を何度も観ても、1 本として数えます。")
    show = _venue_block(cnt_show, top, "公演",
                         "同じ公演を複数回観た分は、その都度数えます ── "
                         "実際に足を運んだ回数です。")
    # **2 つの数え方を横に並べる**（起案者の指示 2026-08-25 ──「横並びにして。
    # まるまるページの横幅使ってよい。1 カラム」）。縦に積むと、比べたい 2 つの
    # 順位が画面をまたいで離れる。年表と同じ理由で `wide` を付け、`.figs` の
    # 2 カラムを使わず横幅いっぱいに広げる（`app.py` の `.figs>.wide`）。
    return f"""<section class="card wide">
{IC.h2("building", "よく行く劇場")}
<p class="lead">作り手の分かっている {len(rated)} 作品をもとに、劇場ごとに数えています。
評価は入れていません。</p>
<div class="vcols"><div class="vcol">{work}</div><div class="vcol">{show}</div></div></section>"""



# ---------------------------------------------------------------- 観劇の年輪
def _polar(day: int, ring: float, cx: float, cy: float) -> tuple[float, float]:
    """1 年を 1 周にした極座標。**12 時の位置を 1 月 1 日にする。**

    時計と同じ向き（右回り）に月が進む。左回りにすると、月の並びを読むために
    いちいち考えることになる。
    """
    a = math.tau * (day / 366.0) - math.tau / 4          # -90° が 1 月 1 日
    return cx + ring * math.cos(a), cy + ring * math.sin(a)


def spiral_panel(works: list[dict], top_pad: int = 26) -> str:
    """観劇の年輪。**角度が月、半径が年。1 点が 1 公演である。**

    ## この図が答える問い

    **「毎年、いつ観ているのか」。** 年ごとの本数（縦棒）は「どれだけ観たか」しか
    答えず、月ごとの合計は「どの月に多いか」しか答えない。**どちらも、季節の癖が
    毎年くり返しているのか、ある年だけの偏りなのかを区別できない。** 年を半径に、
    月を角度に置くと、同じ方角に点が縦に並ぶかどうかで、それが 1 枚で分かる。

    ## 1 件ずつ識別できることを崩さない

    振り返りの図は、1 件 1 件が識別できないと意味が無い（同じ指摘を 1 度受けている）。
    **点は 1 公演で、押すと下の記録へ飛ぶ。** 件数を集計した濃淡（よくある形）に
    しないのは、集計にすると「2024 年 5 月に 2 本」までしか戻れないためである。

    ## 色は既にある評価の配色をそのまま使う

    ◎○△× は順序のある尺度なので**発散の対**（青 ↔ 赤・中点は灰）で、
    これは「付けた評価の分布」の帯と同じ色である ── **色は対象に付くもので、
    図ごとに変えると同じ ◎ が別の意味に見える。** 検証は
    `validate_palette.js "#2a78d6,#e34948"` が明暗どちらのモードでも全項目 PASS。
    **色だけで運ばない** ── 塗りと白抜きの違い（◎○ は塗り、△× は輪）を重ねてあり、
    凡例と表の姿も必ず添える。
    """
    rows = [w for w in works if (w.get("first_date") or "")[:4].isdigit()]
    if not rows:
        return ""
    years = sorted({w["first_date"][:4] for w in rows})
    # **年は 1 本ずつ等間隔の輪に置く。** 実際の間隔で置くと、観ていない年で輪が空く
    r0, dr = 38.0, max(min(156.0 / max(len(years), 1), 30.0), 16.0)
    R = r0 + dr * (len(years) - 1)
    size = (R + 34) * 2
    cx = cy = size / 2

    # **軸線は輪の中だけに引く。** 外へ突き出すと放射状の線が図の主役になってしまう
    spokes, mlabs = [], []
    for m in range(12):
        d0 = int(m * 30.5) + 1
        ix, iy = _polar(d0, r0 - 7, cx, cy)
        ox, oy = _polar(d0, R + 5, cx, cy)
        spokes.append(f'<line x1="{ix:.1f}" y1="{iy:.1f}" x2="{ox:.1f}" y2="{oy:.1f}"/>')
        lx, ly = _polar(int(m * 30.5) + 16, R + 20, cx, cy)
        mlabs.append(f'<text class="mo" x="{lx:.1f}" y="{ly:.1f}">{m + 1}</text>')
    rings, ylabs = [], []
    for i, y in enumerate(years):
        rr = r0 + dr * i
        rings.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}"/>')
        # **年は 12 時の軸の上に、地の色の縁を付けて置く**（点の上に来ても読める。
        # `paint-order` で縁を先に塗るので、文字が点に負けない）
        # **年の文字は点より後に描く**（点の下に隠れると、どの輪が何年か読めなくなる）
        ylabs.append(f'<text class="yr" x="{cx:.1f}" y="{cy - rr:.1f}">{E(y)}</text>')

    pts, tally = [], collections.Counter()
    for w in sorted(rows, key=lambda w: w["first_date"]):
        d = date.fromisoformat(w["first_date"])
        rr = r0 + dr * years.index(w["first_date"][:4])
        x, y = _polar(d.timetuple().tm_yday, rr, cx, cy)
        v = w.get("verdict") or ""
        g = v if v in VERDICT_FILL else "未評価"
        tally[g] += 1
        fill = VERDICT_FILL.get(v, "var(--unk)")
        # **塗りと輪で 2 通目の符号を持たせる**（色を読めない場合の経路）
        solid = v in ("◎", "○")
        times = f"・{w['times']} 回" if (w.get("times") or 1) > 1 else ""
        pts.append(
            f'<a href="{ROW_HREF}&amp;w={E(_anchor(w["work_key"]))}'
            f'#w-{E(_anchor(w["work_key"]))}"><g class="pt">'
            f'<title>{E(w["title"])} ── {E(w["first_date"])}{E(times)}'
            f'{"・" + E(v) if v else "・評価なし"}</title>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5"'
            f' fill="{fill if solid else "var(--surf)"}"'
            f' fill-opacity="{VERDICT_OP.get(v, 1.0) if solid else 1}"'
            f' stroke="{fill}" stroke-width="{1.6 if solid else 2}"/></g></a>')

    leg = "".join(
        f'<span class="lg"><svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true">'
        f'<circle cx="6.5" cy="6.5" r="5" fill="{VERDICT_FILL.get(g, "var(--unk)") if g in ("◎", "○") else "var(--surf)"}"'
        f' fill-opacity="{VERDICT_OP.get(g, 1.0) if g in ("◎", "○") else 1}"'
        f' stroke="{VERDICT_FILL.get(g, "var(--base)")}" stroke-width="2"/></svg>'
        f'{E(g)} <b>{tally[g]}</b></span>'
        for g in list(VERDICT_ORDER[:4]) + ["未評価"] if tally.get(g))

    # 表の姿は**月 × 年の普通の格子**にする。図が読めない場合の経路であり、
    # 「何月に何本」を数字で引きたいときはこちらが速い
    grid = collections.Counter((w["first_date"][:4], w["first_date"][5:7]) for w in rows)
    head = ["年"] + [f"{m}月" for m in range(1, 13)] + ["計"]
    trows = [[y] + [grid.get((y, f"{m:02d}"), "") for m in range(1, 13)]
             + [sum(v for (yy, _), v in grid.items() if yy == y)] for y in years]
    mon = collections.Counter(w["first_date"][5:7] for w in rows)
    peak = mon.most_common(1)[0]
    thin = min(mon.items(), key=lambda kv: kv[1]) if len(mon) == 12 else None
    return f"""<section class="card">
{IC.h2("chart", "観劇の年輪 ── 毎年いつ観ているか",
       f'<span class="badge part">{len(rows)} 公演・{len(years)} 年</span>')}
<p class="lead"><b>1 つの点が 1 公演です。</b>時計と同じ向きに月が進み、
<b>内側が {E(years[0])} 年、外側が {E(years[-1])} 年</b>です。
同じ方角に点が縦に並んでいれば、その月に毎年観ているということです。
いちばん多いのは <b>{int(peak[0])} 月の {peak[1]} 公演</b>
{f"、いちばん少ないのは {int(thin[0])} 月の {thin[1]} 公演" if thin else ""}です。
<b>点を押すと、下のその公演の記録に飛びます。</b></p>
<div class="ring"><svg viewBox="0 0 {size:.0f} {size:.0f}" width="100%"
 style="max-width:{size:.0f}px" role="img"
 aria-label="観劇の年輪。角度が月、半径が年で、1 点が 1 公演">
<g class="sp">{"".join(spokes)}</g><g class="rg">{"".join(rings)}</g>
{"".join(mlabs)}{"".join(pts)}
{"".join(ylabs)}</svg></div>
<div class="legend">{leg}</div>
{_table(head, trows)}</section>"""


# **1 公演ごとの記録が置かれている画面。** 図の点を押すとその公演の行へ飛ぶが、
# **図と行が別の画面になった**ので（2026-08-24・記録を見返すを 3 つに分けた）、
# 同じ画面の中の目印（`#w-…`）だけでは届かない。**行の側の画面を差し込めるようにする** ──
# 図の側にパスを直書きすると、画面の構成を変えるたびに図のコードを直すことになる。
# **点の行き先には、どの記録かを載せる。** 日記帳は年の耳で 1 枚 15 件ずつに
# 切ってあるので（2026-08-24）、**断片だけを渡すと、その行が載っていない紙が開く。**
# `w=` を受けた側が、その記録が載っている耳と紙を選ぶ（`app.page_works`）
ROW_HREF = "/records/works?t=__TAGURI_TOKEN__"


def _anchor(work_key: str) -> str:
    """記録の行へ飛ぶための名前。**鍵をそのまま使えない**（記号と空白が入る）。"""
    return re.sub(r"[^0-9A-Za-z぀-ヿ一-鿿-]", "_", work_key)[:80]


# ---------------------------------------------------------------- 行った劇場の地図
# 全国の枠（緯度経度）。**沖縄まで入れる。** 行っていない土地が見えることが
# この図の中身なので、行った範囲に切り詰めると「どこまで行ったか」が読めなくなる
JP = (122.0, 24.0, 146.5, 45.8)


def _bbox(pts: list[tuple[float, float]], pad: float = 0.12) -> tuple:
    """点の並びを囲む枠。**拡大図の範囲は決め打ちにしない。**

    決め打ちの枠にすると、館が寄っている側に余白が残り（実際に描いて確かめた ──
    枠の下半分と右側が空いていた）、点どうしが必要以上に近くなる。**行った館から
    枠を作れば、次に別の街の劇場が増えても枠が付いてくる。**
    """
    xs = [x for x, _ in pts] or [139.7]
    ys = [y for _, y in pts] or [35.7]
    dx, dy = max(max(xs) - min(xs), 0.02), max(max(ys) - min(ys), 0.02)
    return (min(xs) - dx * pad, min(ys) - dy * pad,
            max(xs) + dx * pad, max(ys) + dy * pad)


def _proj(lon: float, lat: float, box: tuple, w: float, h: float) -> tuple[float, float]:
    """緯度経度を枠の中の位置にする。**緯度の向きは上下反転する。**

    **枠の縦横比は `_frame` が決める。** ここで経度側に緯度の余弦をかけても、
    同じ係数で割ることになって何も起きない（一度そう書いていた）── 形が伸びるのを
    防ぐのは、投影ではなく**枠の高さの取り方**である。
    """
    x0, y0, x1, y1 = box
    return (w * (lon - x0) / (x1 - x0), h * (y1 - lat) / (y1 - y0))


def _frame(box: tuple, w: float) -> float:
    """幅 `w` の枠に対する高さ。**この 1 行が地図の形を決める。**

    緯度 36 度では経度 1 度の東西距離が緯度 1 度の 0.81 倍しかない。高さを縦横比を
    無視して決めると**日本の形が横に伸びる** ── 同じ種類の失敗を SVG の
    `preserveAspectRatio="none"` で 1 度やっている（劇場の横棒で文字が 9.5 倍に伸びた）。
    """
    x0, y0, x1, y1 = box
    k = math.cos(math.radians((y0 + y1) / 2))
    return w * (y1 - y0) / max((x1 - x0) * k, 1e-9)


def map_panel(works: list[dict], top: int = 0) -> str:
    """行った劇場を地図に置く。**点の大きさは足を運んだ回数である。**

    ## この図が答える問い

    **「自分はどこまで行ったのか」。** 頻度の横棒は順位を答えるが、**距離と広がりを
    答えない** ── 「東京の外に出たのは 7 回だけ」「北は札幌、西は福岡」は、地図でしか
    形にならない。埋まっていない土地が見えることが、この図の中身である。

    ## 座標が取れていない館を、地図の外に隠さない

    OSM に名前が無い館があり（名前の言い換えを 3 通り試して当たらなかったもの）、
    **その館は点にできない。** 上限や打ち切りで「破綻しない」と言うときは、あふれた分の
    行き先を必ず言う ── 地図の下に名前と回数を並べる。**回数の多い館が入っていない
    ことを、地図の見た目で隠さない。**

    ## 色は 1 色でよい

    量は点の大きさが運んでいるので、**色に別の仕事をさせない**（等級の色分けを重ねると、
    同じ量を 2 通の符号で言うだけで読みにくくなる）。都道府県の色分けもしない ──
    行った県は 7 つで、塗り分けても順位も量も表さない。
    """
    geo = _geo()
    vis = VN.visits(works)
    at = VN.works_at(works)
    if not vis:
        return ""
    placed = [(k, n) for k, n in vis.most_common() if (geo.get(k) or {}).get("lat")]
    missing = [(k, n) for k, n in vis.most_common() if not (geo.get(k) or {}).get("lat")]
    if not placed:
        return ""
    mx = max(n for _, n in placed)
    # **拡大図は「東京都」の館で作る。** 都道府県は座標と一緒に取れているので、
    # 緯度経度で線を引くより確かで、横浜（神奈川）を巻き込まない
    tk = [k for k, _ in placed if (geo[k] or {}).get("pref") == "東京都"]
    TOKYO = _bbox([(geo[k]["lon"], geo[k]["lat"]) for k in tk])
    prefs = collections.Counter()
    for k, n in placed:
        p = (geo[k] or {}).get("pref") or ""
        if p:
            prefs[p] += n

    def dots(box: tuple, w: float, h: float, labels: int = 0) -> str:
        """館ごとの点。**大きい点を先に置く**（小さい点が下に隠れない）。"""
        out, taken, dots_at = [], [], []
        for k, n in sorted(placed, key=lambda t: -t[1]):
            g = geo[k]
            if not (box[0] <= g["lon"] <= box[2] and box[1] <= g["lat"] <= box[3]):
                continue
            x, y = _proj(g["lon"], g["lat"], box, w, h)
            r = 4 + 9 * (n / mx) ** 0.5          # 面積が回数に比例するよう平方根で
            ws = at.get(k) or []
            last = ws[0].get("first_date") if ws else ""
            dots_at.append((x, y, r))
            out.append(
                f'<g class="vp"><title>{E(VN.label(k))} ── {n} 回'
                + (f'・{len(ws)} 作品' if ws else "")
                + (f'・最近は {E(last)}' if last else "") + "</title>"
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/></g>')
            # **すべての点に名前を書かない**（規則）。回数の多い順に、**先に置いた名前と、
            # 既に置いた点の両方**と重ならないものだけ書く ── 点との重なりを見ないと、
            # いちばん大きい点の真上に名前が乗る（実際に描いて確かめた）
            ly = y - r - 7
            if (len(taken) < labels
                    and all(abs(x - px) > 54 or abs(ly - py) > 10 for px, py in taken)
                    and all(abs(x - px) > 30 + rr or abs(ly - py) > rr + 6
                            for px, py, rr in dots_at[:-1])):
                taken.append((x, ly))
                out.append(f'<text class="vl" x="{x:.1f}" y="{ly:.1f}">'
                           f'{E(VN.label(k)[:9])} {n}</text>')
        return "".join(out)

    def pref_dots(w: float, h: float) -> str:
        """全国図は**都道府県ごとに 1 点**にまとめる。

        館ごとに置くと、**東京の 24 館が 1 か所で重なって同心円の模様になる**
        （実際に描いて確かめた）── 回数も館数も読めない。全国図が答える問いは
        「どこまで行ったか」なので、県の単位で足りる。**館の単位は東京の拡大図が持つ。**
        """
        out, lab, pmx = [], [], max(prefs.values())
        for pf, n in prefs.most_common():
            ks = [k for k, _ in placed if (geo[k] or {}).get("pref") == pf]
            la = sum(geo[k]["lat"] for k in ks) / len(ks)
            lo = sum(geo[k]["lon"] for k in ks) / len(ks)
            x, y = _proj(lo, la, JP, w, h)
            # **半径の上限を抑える。** 東京の点が大きすぎると隣県（横浜まで 4px）を
            # 飲み込む。量は数字を添えるので、大きさは目安でよい
            r = 4.5 + 7.5 * (n / pmx) ** 0.5
            out.append(f'<g class="vp"><title>{E(pf)} ── {len(ks)} 館・{n} 回</title>'
                       f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/></g>')
            ly = y
            while any(abs(ly - py) < 11 for py in lab):
                ly += 11            # 名前が重なる県は下へずらす（東京と神奈川）
            lab.append(ly)
            if abs(ly - y) > 2:
                # **ずらした名前には引き出し線を引く。** 線が無いと、東京の下に
                # 押し出された「神奈川県」が海の上の劇場のように見える（描いて確かめた）
                out.append(f'<line class="lead" x1="{x + r + 2:.1f}" y1="{y:.1f}"'
                           f' x2="{x + r + 5:.1f}" y2="{ly:.1f}"/>')
            out.append(f'<text class="vl" x="{x + r + 7:.1f}" y="{ly:.1f}"'
                       f' text-anchor="start">{E(pf)} {n}</text>')
        return "".join(out)

    W = 300.0
    HJ, HT = _frame(JP, W), _frame(TOKYO, W)
    # 東京の地 ── 枠にかかる区だけ描く。**区の名前も置く**（点の名前より薄く、
    # 下に敷く）。どこの区なのかが読めないと、境界の線はただの模様になる
    ward_shape, ward_labs = [], []
    for wd, rings in _wards().items():
        seen = False
        for ring in rings:
            if not any(TOKYO[0] <= lo <= TOKYO[2] and TOKYO[1] <= la <= TOKYO[3]
                       for lo, la in ring):
                continue
            seen = True
            ward_shape.append(
                '<path d="M' + " ".join(
                    f'{_proj(lo, la, TOKYO, W, HT)[0]:.1f},'
                    f'{_proj(lo, la, TOKYO, W, HT)[1]:.1f}' for lo, la in ring) + 'Z"/>')
        if seen:
            pts = [pt for ring in rings for pt in ring
                   if TOKYO[0] <= pt[0] <= TOKYO[2] and TOKYO[1] <= pt[1] <= TOKYO[3]]
            if len(pts) >= 4:
                lx, ly = _proj(sum(q[0] for q in pts) / len(pts),
                               sum(q[1] for q in pts) / len(pts), TOKYO, W, HT)
                ward_labs.append(f'<text x="{lx:.1f}" y="{ly:.1f}">{E(wd)}</text>')
    ward_shape, ward_labs = "".join(ward_shape), "".join(ward_labs)
    # 全国の島の輪郭
    shape = "".join(
        '<path d="M' + " ".join(
            f'{_proj(lon, lat, JP, W, HJ)[0]:.1f},{_proj(lon, lat, JP, W, HJ)[1]:.1f}'
            for lon, lat in ring) + 'Z"/>'
        for ring in _outline())
    n_pref = len(prefs)
    # **座標の出どころを表に書く。** 施設そのもので引けた館と、住所から丁目の中心で
    # 置いた館は精度が違う（後者は 100〜300m ずれる）── 同じ点に見えるので、
    # 違いは表でしか伝えられない
    src = {"nominatim": "施設名", "corich-address": "住所（丁目の中心）",
           "hand-address": "住所（手で指定）", "hand": "手で指定"}
    tbl = [[VN.label(k), n, len(at.get(k) or []), (geo[k] or {}).get("pref") or "──",
            src.get((geo[k] or {}).get("source") or "", "──")]
           for k, n in sorted(placed, key=lambda t: -t[1])]
    tbl += [[VN.label(k) + "（地図に無し）", n, len(at.get(k) or []), "──", "取れていない"]
            for k, n in missing]
    n_tokyo = sum(1 for k, _ in placed
                  if TOKYO[0] <= geo[k]["lon"] <= TOKYO[2]
                  and TOKYO[1] <= geo[k]["lat"] <= TOKYO[3])
    return f"""<section class="card wide">
{IC.h2("building", "行った劇場の地図",
       f'<span class="badge part">{len(placed)} 館・{n_pref} 都道府県</span>')}
<p class="lead"><b>点の大きさは、足を運んだ回数です。</b>
<b>左は都道府県ごと、右は東京の館ごと</b>です ──
東京の {n_tokyo} 館は全国の地図では 1 か所に重なるので、分けています。
地図に出ているのは<b>座標が分かった {len(placed)} 館ぶんの {sum(n for _, n in placed)} 回</b>で
（{E("・".join(f"{p} {n} 回" for p, n in prefs.most_common(4)))}）、
<b>行った回数の全部ではありません</b> ── 残りは下の注記にあります。</p>
<div class="maps">
 <figure><svg viewBox="0 0 {W:.0f} {HJ:.0f}" width="100%" role="img"
   aria-label="都道府県ごとの観劇回数">
  <g class="land">{shape}</g>
  <g class="pins">{pref_dots(W, HJ)}</g></svg>
  <figcaption>全国 ── 点は都道府県ごとの回数</figcaption></figure>
 <figure><svg viewBox="0 0 {W:.0f} {HT:.0f}" width="100%" role="img"
   aria-label="東京の劇場">
  <g class="ward">{ward_shape}</g><g class="wardl">{ward_labs}</g>
  <g class="pins">{dots(TOKYO, W, HT, labels=8)}</g></svg>
  <figcaption>東京 ── 点は劇場 1 館。地は区の境界で、行った館の範囲に合わせています
  </figcaption></figure>
</div>
{f'''<p class="note"><b>{len(missing)} 館・{sum(n for _, n in missing)} 回は
地図に置けていません</b>
（{E("・".join(f"{VN.label(k)} {n} 回" for k, n in missing))}）。
場所を調べられなかった館です。<b>下の表には入っています。</b></p>'''
 if missing else ""}
{_table(["劇場", "行った回数", "作品数", "都道府県", "座標の出どころ"], tbl)}</section>"""


_GEO: dict | None = None
_SHAPE: list | None = None
_WARDS: dict | None = None


def _geo() -> dict:
    global _GEO
    if _GEO is None:
        f = ROOT / "data" / "review" / "venue_geo.json"
        _GEO = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return _GEO


def _wards() -> dict:
    """東京の区市の境界。**拡大図の地である。**

    全国の輪郭（2km まで間引いたもの）を東京の枠に写すと、**枠いっぱいが 1 色に
    塗られるだけで地図にならない** ── 実際にその状態で出してしまい、「都内の地図が
    表示されていない」という指摘を受けた（起案者）。**地の絵は、枠の縮尺に合った
    ものを別に持つ。**
    """
    global _WARDS
    if _WARDS is None:
        f = ROOT / "data" / "review" / "tokyo_wards.json"
        _WARDS = (json.loads(f.read_text(encoding="utf-8")).get("wards") or {}) \
            if f.exists() else {}
    return _WARDS


def _outline() -> list:
    global _SHAPE
    if _SHAPE is None:
        f = ROOT / "data" / "review" / "japan_outline.json"
        _SHAPE = (json.loads(f.read_text(encoding="utf-8")).get("rings") or []) \
            if f.exists() else []
    return _SHAPE


CSS = """
.viz{max-width:100%;overflow:visible}
.viz .vlab{font-size:11px;fill:var(--ink2);text-anchor:middle;font-weight:600}
.viz .alab{font-size:11px;fill:var(--mute);text-anchor:middle}
.viz .a-l{text-anchor:start;font-size:11.5px;fill:var(--ink2)}
.viz .v-l{text-anchor:start;font-weight:600}
.viz .bar:hover rect{stroke:var(--ink);stroke-width:1.5}
.viz text{dominant-baseline:middle}
.dbar{position:relative;margin:6px 0 30px}
.dbar svg{display:block;border-radius:4px}
.dlabs{position:relative;height:18px}
.dlabs .dl{position:absolute;transform:translateX(-50%);font-size:11.5px;color:var(--ink2);
 white-space:nowrap;margin:0;padding:0;border:0;background:none}
.vcols{display:grid;grid-template-columns:1fr 1fr;gap:0 28px;align-items:start;margin:6px 0 0}
@media(max-width:820px){.vcols{grid-template-columns:1fr}}
.vsub{font-size:13.5px;font-weight:600;color:var(--ink);margin:16px 0 2px;
 display:flex;gap:8px;align-items:baseline}
.vcol>.vsub:first-child{margin-top:0}
.hbars{margin:4px 0 0}
.hb{display:grid;grid-template-columns:minmax(0,15em) 1fr 2.4em;gap:12px;align-items:center;
 padding:3px 0;font-size:13px}
.hb-l{color:var(--ink2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hb-t{background:var(--grid);border-radius:4px;height:14px;overflow:hidden}
.hb-f{display:block;height:100%;background:var(--s1);border-radius:4px}
.hb-v{color:var(--ink2);font-weight:600;text-align:right}
.hb:hover .hb-f{filter:brightness(1.12)}
@media(max-width:560px){.hb{grid-template-columns:minmax(0,9em) 1fr 2.4em}}
.tv{margin:10px 0 0}
.tv summary{cursor:pointer;font-size:12px;color:var(--mute)}
.tbl{border-collapse:collapse;margin:8px 0 0;font-size:12.5px}
.tbl th,.tbl td{padding:3px 12px 3px 0;text-align:left;color:var(--ink2);
 border-bottom:1px solid var(--grid)}
.tbl th{color:var(--mute);font-weight:600}

/* ---- 観劇の年輪 -----------------------------------------------------------
   地と軸は退かせ、点だけを前に出す。**格子と軸線は読み取りの邪魔をしない濃さにする。** */
.ring{margin:10px 0 0;display:flex;justify-content:center}
.ring .sp line,.ring .rg circle{stroke:var(--grid);stroke-width:1;fill:none}
.ring .mo{font-size:10.5px;fill:var(--mute);text-anchor:middle;dominant-baseline:middle}
/* **年の文字は点の上に来ても読めるようにする。** 地の色で縁を先に塗る
   （`paint-order:stroke`）── 位置をずらして逃げると、どの輪の年なのかが分からなくなる */
.ring .yr{font-size:10px;fill:var(--ink2);text-anchor:middle;dominant-baseline:middle;
 font-weight:600;paint-order:stroke;stroke:var(--surf);stroke-width:3.5;
 stroke-linejoin:round}
/* **重なった点は地の色の輪で分ける**（2px の隙間を作る規則） */
.ring .pt circle{paint-order:stroke;stroke-linejoin:round}
.ring a{cursor:pointer}
.ring .pt:hover circle{stroke:var(--ink);stroke-width:2.4}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0 0;font-size:12.5px;
 color:var(--ink2);justify-content:center}
.legend .lg{display:inline-flex;gap:5px;align-items:center}

/* ---- 行った劇場の地図 ------------------------------------------------------
   陸は面として退かせ、点は 1 色。**量は大きさだけが運ぶ。** */
.maps{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:12px 0 0}
@media(max-width:640px){.maps{grid-template-columns:1fr}}
.maps figure{margin:0}
.maps figcaption{font-size:11.5px;color:var(--mute);margin:4px 0 0;text-align:center}
.maps .land path{fill:var(--grid);stroke:var(--base);stroke-width:.4}
/* 区の境界は**地**なので、線を細く薄くする（点と名前より後ろに退く） */
.maps .ward path{fill:var(--grid);stroke:var(--surf);stroke-width:.8}
.maps .wardl text{font-size:6.5px;fill:var(--mute);text-anchor:middle;
 dominant-baseline:middle}
.maps .lead{stroke:var(--base);stroke-width:.8}
.maps .pins circle{fill:var(--acc);fill-opacity:.72;stroke:var(--surf);stroke-width:1.5}
.maps .vp{cursor:default}
.maps .vp:hover circle{fill-opacity:1;stroke:var(--ink);stroke-width:1.8}
/* 直接ラベル。**点の上に重なっても読めるように地の色の縁を付ける** */
.maps .vl{font-size:9.5px;fill:var(--ink2);text-anchor:middle;dominant-baseline:middle;
 paint-order:stroke;stroke:var(--surf);stroke-width:3;stroke-linejoin:round}
.note{color:var(--ink2);font-size:12.5px;margin:10px 0 0}
"""
