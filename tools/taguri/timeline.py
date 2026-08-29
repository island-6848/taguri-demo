#!/usr/bin/env python3
"""作り手の再会タイムライン。**同じ人を何年も追っているのか、1 つの公演を何度も観ただけか。**

## この図が答える問い

**「この人を何年も追っているのか、それとも 1 つの公演を繰り返し観ただけなのか」。**

回数だけを並べると、この 2 つが区別できない。実測（2026-08-24・観劇日のある評価済み
69 件）で確かめた。

| 名前 | 役 | 回数 | いつ観たか |
|---|---|---|---|
| 前田文子 | 衣裳 | 8 回 | 2022-10 〜 **2026-01（4 年に散っている）** |
| 加藤温 | 音響 | 8 回 | 2022-10 〜 2025-11（3 年に散っている） |
| 針生康 | 美術 | 4 回 | **2024-04-21 〜 2024-07-01（10 週間に固まっている）** |
| 久山宏一 | 翻訳 | 4 回 | 2024-04-21 〜 2024-07-01（同じ 10 週間） |

**下 2 人と同じ日付範囲の名前が 9 人いる。** デカローグを 4 回観たので、その座組が丸ごと
「4 回」として並んでいるだけである。**棒グラフでは同じ「4 回」に見えるが、時間軸に置くと
一目で違う。** `build_lookback` が「同じ座組の繰り返し」として言葉で警告していたものを、
**図の形そのもので見せる。**

## なぜ価値があるか

**4 回以上観ている 28 人のうち、本人が申告したのは 6 人だけだった。** 衣裳・音響・
ヘアメイク・舞台監督・照明の人を、名前を挙げないまま何年も観ている ── 企画の中核
（気づいていなかった裏方の名前）そのものである。**申告した人と、していない人を見分けて
出す** ── 申告した人は本人が既に知っているので、発見はしていない側にある。

## 形 ── レーンごとに「線と点」を引く

**線の長さがそのまま「追っている年数」である。** 1 行 1 人、横が時間、点が 1 回の観劇で、
最初と最後を線でつなぐ。**線が長ければ何年も追っている人、点が固まっていれば 1 つの時期に
集中した人**と、1 枚で読める。並び順も**線の長い順**にした ── 長い側が読み手の関心で、
集中した座組は自然に下へ集まる。

## 点は公演であって、人への評価ではない

**レーンごとに ◎ 率のようなものは出さない。** 作品単位の評価を、その作品に関わった個人への
評価として使わない方針である（好き嫌いは本人に名指しで聞く側の話である）。点は
**すべて同じ色**にして、押すとその公演の記録へ飛ぶ。何の公演だったかは点に触れると出る。

## なぜここだけ d3 を使うのか

**`charts.py` は外部の描画ライブラリを読まない**方針で、5 つの図はすべて Python が
SVG を組んでいる。この図だけを分けたのは、**レーンが 54 行・横が 5 年あり、時間軸を
伸ばせないと混んでいる時期が読めない**ためである（2024 年 4〜7 月に 9 人が重なる）。
拡大・縮小は d3 の受け持ちで、**軸の目盛りとレーンの並びは Python 側で決めてある。**

**d3 は同梱している**（`tools/taguri/vendor/`）。画面は「外には何も出していません」と
書いているので、CDN からは読まない。**読み込む札は図の側に置かない** ── d3 を使う図が
2 つになったとき、先に描かれる図の札に後の図がぶら下がる形になっていた。
**並び順に頼らない**ように、`app.page_records` が 1 回だけ置く。
"""

from __future__ import annotations

import collections
import datetime
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
for _p in ("review",):
    _s = str(ROOT / "tools" / _p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
import charts as CH                                                  # noqa: E402
import icons as IC                                                   # noqa: E402

E = lambda s: html.escape(str(s))                                   # noqa: E731

# **役は本人の言葉のまま出す。** 「網 B」「寄与」のような内部の言い方は画面に出さない
MIN_TIMES = 4          # 何回以上観た人を並べるか（3 にすると 54 人・4 で 28 人）
ROW_H = 20             # 1 レーンの高さ
LEFT = 176             # 名前の欄の幅
PAD_R = 24
# **「たどる」への飛び先。** 道を図の側に直書きすると、画面の構成を変えるたびに
# 図のコードを直すことになる（`CH.ROW_HREF` と同じ考え方）
TR_HREF = "/records/trace?t=__TAGURI_TOKEN__&name="


def _d(s: str):
    try:
        return datetime.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def build(rated: list[dict], min_times: int = MIN_TIMES) -> dict:
    """レーンを組む。**観劇日のある記録だけが載る**（載らない件数も返す）。

    1 人の 1 レーンに入るのは「その人が関わった公演を観た日」で、**同じ日に同じ人が
    複数の役で出ていても 1 点にまとめる** ── 役の数だけ点が増えると、多い役を持つ人の
    レーンだけ濃く見える。
    """
    import recommend as RC

    dated = [r for r in rated if _d(r.get("date") or "")]
    seen: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    roles: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in dated:
        for role, person in r.get("people") or []:
            roles[person][role] += 1
            # 同じ日は 1 点（役をまたいで数えない）
            seen[person][r["date"]] = {"date": r["date"], "key": r["key"],
                                       "title": r["title"]}
    declared = {RC.nz(x) for xs in RC.DECLARED.values() for x in xs} \
        if hasattr(RC, "nz") else {x for xs in RC.DECLARED.values() for x in xs}

    def nz(s):
        return RC.nz(s) if hasattr(RC, "nz") else s

    lanes = []
    for person, byday in seen.items():
        if len(byday) < min_times:
            continue
        pts = sorted(byday.values(), key=lambda x: x["date"])
        a, b = _d(pts[0]["date"]), _d(pts[-1]["date"])
        lanes.append({
            "name": person,
            # **役は多い順に 2 つまで。** 全部並べるとレーンの名前が図より広くなる
            "role": "・".join(k for k, _ in roles[person].most_common(2)),
            "n": len(pts),
            "span": (b - a).days,
            "declared": nz(person) in declared,
            "points": [{"date": p["date"], "title": p["title"],
                        "anchor": CH._anchor(p["key"])} for p in pts],
            # **まとめるための印。** 観た公演の並びが同じ人は同じ座組として囲う
            "sig": "|".join(p["key"] for p in pts),
        })
    groups = _groups(lanes)
    # **まとまりごとに並べる。** まとまりの中は名前順、まとまりの外は線の長い順 ──
    # 追っている年数が読み手の関心で、1 つの時期に集中した座組は自然に下へ集まる
    order = {g["sig"]: i for i, g in enumerate(groups)}
    lanes.sort(key=lambda x: (order[x["sig"]], x["name"]))
    for i, ln in enumerate(lanes):
        ln["row"] = i
    for g in groups:
        rows = [ln["row"] for ln in lanes if ln["sig"] == g["sig"]]
        g["row0"], g["row1"] = min(rows), max(rows)
    days = [_d(p["date"]) for ln in lanes for p in ln["points"]]
    return {"lanes": lanes, "groups": [g for g in groups if g["n_people"] >= 2],
            "from": min(days).isoformat() if days else "",
            "to": max(days).isoformat() if days else "",
            "min_times": min_times,
            "n_dated": len(dated), "n_all": len(rated),
            "n_people": len({p for r in dated for _r, p in (r.get("people") or [])})}


def _groups(lanes: list[dict]) -> list[dict]:
    """**観た公演の並びが完全に同じ人を、1 つのまとまりにする。**（起案者の指示・2026-08-24）

    ## 何を同じとみなすか ── 「常に一緒に出てくる人」だけ

    **一致を要求するのは、その人が出ている公演の並びそのものである。** 一部でも重なれば
    まとめる形にはしなかった。**そうすると、記録の中でいちばん大事な区別が消える** ──
    前田文子（衣裳）はデカローグ 6 作品に出ているが、それ以外に「A・NUMBER」など別の
    公演にも 4 年にわたって出ている。重なりでまとめると**デカローグの座組に吸い込まれ、
    「何年も追っている人」が座組の一部として消える。**

    完全一致だけで囲うと、まとまりについて言えることが**そのまま真になる** ──
    「この人たちは、あなたの記録の中では常に同じ公演に一緒に出ています」。実測では
    デカローグの 10 人が 1 つのまとまりになり、前田文子・加藤温・鎌田直樹は別に残った。

    ## 並べる順

    まとまりの代表は**線がいちばん長い人**で、その長さでまとまりごと並べる。1 人しか
    いないまとまりは囲わない（囲う意味が無い）。
    """
    by: dict[str, list[dict]] = {}
    for ln in lanes:
        by.setdefault(ln["sig"], []).append(ln)
    out = []
    for sig, members in by.items():
        span = max(m["span"] for m in members)
        names = sorted(m["name"] for m in members)
        pts = members[0]["points"]           # 並びが同じなので、どれで見ても同じ
        out.append({"sig": sig, "n_people": len(members), "span": span,
                    # **数えているのは観に行った回数である。** 1 回に複数の演目を観た日が
                    # あるので（デカローグ）、これを「作品数」と書くと合わない
                    "names": names, "n": len(pts),
                    "from": pts[0]["date"], "to": pts[-1]["date"],
                    # **共通の題名があるときだけ名前を付ける**（無ければ空）
                    "label": _common_title(pts)})
    out.sort(key=lambda g: (-g["span"], -g["n_people"], g["names"][0]))
    return out


def _common_title(points: list[dict]) -> str:
    """まとまりの呼び名。**題名に共通の頭があるときだけ、それを使う。**

    **共通の頭が無いときは名前を付けない**（空を返す）。はじめは「いちばん古い公演の題名」を
    代わりに使っていたが、**それは嘘になる** ── 作り手18・作り手26のまとまりは
    「作品1」と「ダブル・トラブル」など別の公演にまたがっており、片方の題名を
    まとまりの名前にすると、**そのまとまりがその公演のことだと読める。**

    名前が無くても言えることは残る ──「この人たちは、記録の中では常に一緒に出ています」。
    """
    ts = [p["title"].strip("「」『』 ") for p in points]
    if not ts:
        return ""
    head = ts[0]
    for t in ts[1:]:
        i = 0
        while i < min(len(head), len(t)) and head[i] == t[i]:
            i += 1
        head = head[:i]
    head = head.strip("「」『』 ・-−ー〜~　")
    return head if len(head) >= 3 else ""


def _group_lead(groups: list[dict]) -> str:
    """囲いの説明。**何人が、どの公演で常に一緒なのかを文で言う。**

    **図の形だけに頼らない。** 囲いは「同じ座組を何度も観ただけ」を見分けるために
    置いてあるので、**その読み方を文でも書く** ── 囲いの意味が伝わらないと、
    ただ 10 行が薄く塗られているだけに見える。
    """
    if not groups:
        return ""
    head = ("<b>点線で囲んだ方々は、記録の中では必ず一緒に出ています。</b>"
            "一緒に囲われている理由は<b>線の長さで読み分けてください</b> ── ")
    # **囲いの意味を言い過ぎない。** はじめは「その公演を何度も観たので回数が増えている
    # だけで、何年も追っているわけではありません」と書いていたが、**これは嘘だった** ──
    # 作り手18・作り手26のまとまりは 10 本・2.9 年にわたっており、まさに何年も追っている。
    # **「必ず一緒」の理由は 2 通りある**ので、どちらなのかは線の長さが答える。
    short = [g for g in groups if g["span"] < 120]
    longs = [g for g in groups if g["span"] >= 365]
    parts = []
    if short:
        b = max(short, key=lambda g: g["n_people"])
        parts.append(f'囲いが短いものは、1 つの公演を何度も観たために全員の回数が'
                     f'増えたものです（{"「" + b["label"] + "」の " if b["label"] else ""}'
                     f'<b>{b["n_people"]} 人</b>は、{b["from"]} から {b["to"]} までの '
                     f'{b["n"]} 回で出会っています）')
    if longs:
        b = max(longs, key=lambda g: g["span"])
        parts.append(f'囲いが長いものは、何年もずっと同じ顔ぶれで観ている方々です'
                     f'（<b>{"・".join(b["names"][:3])}</b> は '
                     f'{b["span"] / 365:.1f} 年で {b["n"]} 回、いつも一緒です）')
    return head + "、".join(parts) + "。"


def panel(rated: list[dict], min_times: int = MIN_TIMES) -> str:
    """図とその説明。**載らなかった件数を必ず書く。**"""
    d = build(rated, min_times)
    lanes = d["lanes"]
    if not lanes:
        return ""
    n_dec = sum(1 for x in lanes if x["declared"])
    height = len(lanes) * ROW_H + 46
    long_ones = [x for x in lanes if x["span"] >= 365]
    tight = [x for x in lanes if x["span"] < 120]
    # **囲いの中の人は、表でもそれが分かるようにする。** 図で囲われている理由が
    # 表から辿れないと、色を読めない人には囲いの意味が届かない
    gof = {}
    for g in d["groups"]:
        for nm in g["names"]:
            gof[nm] = (g["label"] or "") + f'（{g["n_people"]} 人が常に一緒）'
    tbl = CH._table(
        ["名前", "役", "観た回数", "はじめて観た日", "最後に観た日", "またぐ年数", "まとまり"],
        [[x["name"], x["role"], f'{x["n"]} 回', x["points"][0]["date"],
          x["points"][-1]["date"], f'{x["span"] / 365:.1f} 年', gof.get(x["name"], "")]
         for x in lanes])
    payload = json.dumps({"lanes": lanes, "groups": d["groups"],
                          "from": d["from"], "to": d["to"],
                          "rowH": ROW_H, "left": LEFT, "padR": PAD_R,
                          # 点を押したときの飛び先（1 公演ごとの記録は別の画面にある）
                          "rowHref": CH.ROW_HREF,
                          # **名前を押すと「たどる」に移る**（起案者の指示・2026-08-25）。
                          # この図は一望（どの線が長いか）で、たどるは 1 本である ──
                          # **入口を新しく作らず、既にある図の名前をそのまま口にする**
                          "traceHref": TR_HREF},
                         ensure_ascii=False)
    return f"""<div class="card wide">{IC.h2("clock", "作り手の再会")}
<p class="lead">1 行が 1 人、横が時間、点が 1 回の観劇です。<b>線が長い人ほど、長く追っている人で、
点が固まっている人は、短い時期に集中して観た座組です</b> ── どちらも「{min_times} 回観た」ですが、
意味が違います。<br>
{min_times} 回以上観た方が <b>{len(lanes)} 人</b>いて、<b>そのうち {len(lanes) - n_dec} 人は
お気に入りに登録されていません。</b>1 年以上にわたって観ている方が {len(long_ones)} 人、
4 か月以内に集中している方が {len(tight)} 人です。<br>
この図に載るのは<b>観劇日が入っている {d["n_dated"]} 件</b>です
（記録は {d["n_all"]} 件で、残りは観劇日が空のため置けません）。
<b>点を押すとその公演の記録へ、左の名前を押すとその方 1 人の「たどる」へ移動します。</b>
横に引っぱると時間を伸ばせます。<br>
{_group_lead(d["groups"])}</p>
<div class="tl-legend"><span class="tl-k tl-dec">お気に入りに登録済み</span>
 <span class="tl-k">登録していない方</span>
 <span class="tl-k tl-ring">常に一緒に出ている方々</span>
 <span class="tl-hint">（{d["from"]} 〜 {d["to"]}）</span></div>
<div id="tl" class="tl" data-h="{height}"></div>
<p class="tl-fallback">この図は画面上で描いています。{tbl}</p>
</div>
<script id="tl-data" type="application/json">{payload}</script>""" \
        + f"<script>{SCRIPT}</script>"


STYLE = """
/* ---- 作り手の再会タイムライン ------------------------------------------------- */
.tl{margin:10px 0 2px;overflow-x:auto}
.tl svg{display:block}
.tl a.nml{cursor:pointer}
.tl a.nml:hover .nm,.tl a.nml:focus .nm{text-decoration:underline}
.tl .lane-bg{fill:var(--plane)}
.tl .lane-bg.alt{fill:transparent}
/* **線の長さが「追っている年数」である。** 太さは意味を持たせない */
.tl .span{stroke:var(--ring);stroke-width:2;stroke-linecap:round}
.tl .dot{fill:var(--ink2);cursor:pointer}
.tl .dot:hover{fill:var(--pos)}
/* **申告した人は名前の側で分ける。** 点の色は変えない ── 点は公演であって、
   その人への評価ではないので、レーン全体が色づくと人への印に見える */
.tl .nm{font-size:11.5px;fill:var(--ink2)}
.tl .nm.dec{font-weight:700;fill:var(--pos)}
.tl .rl{font-size:10.5px;fill:var(--mute)}
.tl .ax text{font-size:11px;fill:var(--mute)}
.tl .ax line,.tl .ax path{stroke:var(--grid)}
.tl .grid line{stroke:var(--grid);stroke-dasharray:2 3}
/* **囲いは面で示す。** 線だけだと点と線に紛れる。中の点は隠さないので薄く塗る */
.tl .ring-box{fill:var(--pos);fill-opacity:.07;stroke:var(--pos);stroke-opacity:.42;
 stroke-width:1.5;stroke-dasharray:4 3}
.tl .ring-lb{font-size:10.5px;fill:var(--pos);fill-opacity:.9}
.tl-legend{display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:12px;
 color:var(--mute);margin:6px 0 0}
.tl-k{display:inline-flex;align-items:center;gap:5px}
.tl-k::before{content:"";width:9px;height:9px;border-radius:99px;background:var(--ink2)}
.tl-k.tl-dec::before{background:var(--pos)}
.tl-k.tl-ring::before{background:transparent;border:1.5px dashed var(--pos);
 width:14px;height:11px;border-radius:5px}
.tl-hint{margin-left:auto}
.tl-fallback{font-size:12.5px;color:var(--mute);margin:8px 0 0}
.tl-tip{position:fixed;z-index:40;pointer-events:none;max-width:280px;
 background:var(--plane);border:1px solid var(--ring);border-radius:8px;
 padding:7px 10px;font-size:12.5px;line-height:1.6;color:var(--ink2);
 box-shadow:0 6px 20px rgba(0,0,0,.18)}
"""


# **描くのは d3 だが、決めるのは Python 側である。** レーンの並び・役の出し方・
# 何人載せるかはすべて `build` で決めてあり、ここは軸と拡大縮小だけを受け持つ
SCRIPT = """
(function () {
  const host = document.getElementById("tl");
  const src = document.getElementById("tl-data");
  if (!host || !src || typeof d3 === "undefined") return;
  const D = JSON.parse(src.textContent);
  const lanes = D.lanes, rowH = D.rowH, left = D.left, padR = D.padR;
  const axisH = 26;
  // **上に余白を取る。** まとまりの名前をレーンの上に置くので、いちばん上の行が
  // まとまりだったときに文字が切れる
  const top = 15;
  const h = lanes.length * rowH + axisH + top;
  // **横幅は入れ物に合わせる。** 図を切らずに、狭い画面では入れ物ごと横に流す
  const w = Math.max(host.clientWidth || 720, 560);
  const x0 = new Date(D.from), x1 = new Date(D.to);
  // 端に点が張り付かないよう、前後に 3 週間の余白を置く
  const pad = 21 * 864e5;
  const x = d3.scaleUtc().domain([new Date(+x0 - pad), new Date(+x1 + pad)])
    .range([left, w - padR]);
  let xz = x;

  const svgRoot = d3.select(host).append("svg")
    .attr("width", w).attr("height", h)
    .attr("viewBox", [0, 0, w, h]);
  // **中身はまとめて下げる。** 一つずつ足すと、足し忘れた要素だけがずれる
  const svg = svgRoot.append("g").attr("transform", "translate(0," + top + ")");

  // 縞。**1 行を目で追えるようにする**（54 行あると隣の行とずれる）
  svg.append("g").selectAll("rect").data(lanes).join("rect")
    .attr("class", (d, i) => "lane-bg" + (i % 2 ? " alt" : ""))
    .attr("x", 0).attr("y", (d, i) => i * rowH)
    .attr("width", w).attr("height", rowH);

  const nm = svg.append("g");
  nm.selectAll("a.nml").data(lanes).join("a")
    .attr("class", "nml")
    .attr("href", d => D.traceHref + encodeURIComponent(d.name))
    .append("text")
    .attr("class", d => "nm" + (d.declared ? " dec" : ""))
    .attr("x", 8).attr("y", (d, i) => i * rowH + rowH * 0.62)
    .append("tspan")
    .text(d => d.name.length > 11 ? d.name.slice(0, 10) + "…" : d.name);
  nm.selectAll("text.rl").data(lanes).join("text")
    .attr("class", "rl").attr("text-anchor", "end")
    .attr("x", left - 10).attr("y", (d, i) => i * rowH + rowH * 0.62)
    .text(d => d.role + " " + d.n + "回");

  const clip = svg.append("clipPath").attr("id", "tl-clip");
  clip.append("rect").attr("x", left).attr("y", -top)
    .attr("width", w - padR - left).attr("height", h);
  const plot = svg.append("g").attr("clip-path", "url(#tl-clip)");
  const grid = plot.append("g").attr("class", "grid");
  const rings = plot.append("g");          // **点と線の後ろに置く。** 囲いが点を隠さない
  const spans = plot.append("g");
  const dots = plot.append("g");
  const ax = svg.append("g").attr("class", "ax")
    .attr("transform", `translate(0,${lanes.length * rowH})`);

  const tip = d3.select("body").append("div").attr("class", "tl-tip")
    .style("display", "none");

  function draw() {
    ax.call(d3.axisBottom(xz).ticks(Math.max(Math.round((w - left) / 90), 2))
      .tickFormat(d3.utcFormat("%Y-%m")));
    grid.selectAll("line").data(xz.ticks(Math.max(Math.round((w - left) / 90), 2)))
      .join("line")
      .attr("x1", d => xz(d)).attr("x2", d => xz(d))
      .attr("y1", 0).attr("y2", lanes.length * rowH);
    // **同じ公演にしか一緒に出てこない人を、まとめて囲う。**（起案者の指示・2026-08-24）
    // まとまりの中は点の位置が完全に同じなので、囲いは最初と最後の点をつなぐ 1 つの角丸で足りる
    const gsel = rings.selectAll("g.ring").data(D.groups, d => d.sig)
      .join(enter => {
        const g = enter.append("g").attr("class", "ring");
        g.append("rect").attr("class", "ring-box");
        g.append("text").attr("class", "ring-lb");
        return g;
      });
    gsel.select("rect")
      .attr("x", d => xz(new Date(d.from)) - 11)
      .attr("y", d => d.row0 * rowH + 2)
      .attr("width", d => Math.max(xz(new Date(d.to)) - xz(new Date(d.from)) + 22, 22))
      .attr("height", d => (d.row1 - d.row0 + 1) * rowH - 4)
      .attr("rx", 11);
    // **名前は囲いの上に置く。** 何人が、どの公演で常に一緒なのかをその場で言う
    gsel.select("text")
      .attr("x", d => xz(new Date(d.from)) - 11)
      .attr("y", d => d.row0 * rowH - 3)
      .text(d => (d.label ? d.label + "｜" : "") + d.n_people + "人が常に一緒");

    spans.selectAll("line").data(lanes).join("line")
      .attr("class", "span")
      .attr("x1", d => xz(new Date(d.points[0].date)))
      .attr("x2", d => xz(new Date(d.points[d.points.length - 1].date)))
      .attr("y1", (d, i) => i * rowH + rowH / 2)
      .attr("y2", (d, i) => i * rowH + rowH / 2);
    const flat = [];
    lanes.forEach((ln, i) => ln.points.forEach(p =>
      flat.push({ ...p, row: i, name: ln.name, role: ln.role })));
    dots.selectAll("circle").data(flat).join("circle")
      .attr("class", "dot").attr("r", 4)
      .attr("cx", d => xz(new Date(d.date)))
      .attr("cy", d => d.row * rowH + rowH / 2)
      .on("mouseenter", (ev, d) => {
        tip.style("display", "block")
          .text(d.name + "（" + d.role + "）｜" + d.date + "｜" + d.title);
      })
      .on("mousemove", ev => tip.style("left", (ev.clientX + 14) + "px")
        .style("top", (ev.clientY + 14) + "px"))
      .on("mouseleave", () => tip.style("display", "none"))
      // **行は別の画面にある**（記録を見返すを 3 つに分けた）。同じ画面の目印を
      // 書き換えるだけでは届かないので、行の画面へ目印付きで移る
      // **日記帳に「どの記録か」を渡す**（紙が 15 件ずつなので目印だけでは届かない）
      .on("click", (ev, d) => {
        location.href = D.rowHref + "&w=" + encodeURIComponent(d.anchor) + "#w-" + d.anchor;
      });
  }
  draw();

  // **時間だけを伸ばす。** 2024 年 4〜7 月に 9 人が重なるので、そこを開けないと読めない。
  // 縦は動かさない（行の位置が変わると、名前と点の対応を目で追えなくなる）
  svgRoot.call(d3.zoom().scaleExtent([1, 40])
    .translateExtent([[left, 0], [w - padR, h]])
    .extent([[left, 0], [w - padR, h]])
    .on("zoom", ev => { xz = ev.transform.rescaleX(x); draw(); }));
})();
"""
