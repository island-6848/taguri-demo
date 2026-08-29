#!/usr/bin/env python3
"""「観に行ける場所で絞り込む」の地図と地方の札。

起案者の指示（2026-08-25）──「『観に行ける場所で絞り込む』のところ、地図上で選択
できるものも追加して。あと『関東地方』とか選ぶと、関東の該当の都道府県にチェックが
入るとうれしい」。

## 何を足したのか ── 選ぶ口を増やしただけで、決まり方は変えていない

**選んだ内容を持っているのは、これまでどおりチェックの並びである。** 地図を押しても
地方の札を押しても、動くのはチェックであって、**送られるものは 1 つも変わらない**
（`pref` の並びを GET で返す素の form のまま）。地図と札は**同じ 1 つの状態を別の
形で触るための口**であって、別の絞り込みではない。

**この作りにしたのは、状態が 2 つに分かれるのを避けるためである。** 地図に選択を
持たせると、チェックと地図がずれたときにどちらが本当なのか決められなくなる。
塗りは 47 本の CSS（`input[value="東京都"]:checked` に反応する）で出しているので、
**画面の塗りは必ずチェックと一致する** ── 押し口が JavaScript で、見た目は CSS である。

## 地図の形は自分で描いていない

県ごとの輪郭は OSM の行政境界を 1km で間引いたもので、`tools/geo/fetch_pref_shapes.py`
が 1 度だけ引いて端末内に置く（`data/review/japan_prefs.json`）。**手で多角形を書き
起こすことはしない** ── 根拠の無い形を地図として出すことになる。投影は劇場の地図
（`charts.py`）と同じものを使う。**別に書くと、同じ日本が 2 つの形で並ぶ。**

## 地方の区切りは自分で作っていない

**八地方区分**（総務省などが使う一般的な区切り）をそのまま使う。三重県は近畿、
沖縄県は九州に入れる形である。**自分で括りを作らない** ── 「関東」と言われたときに
入る県は世の中で決まっているので、こちらで決め直すと押した結果が予想と食い違う。

## 0 件の県は押せない

チェックの並びは前から**候補のある県だけ**を出している（押しても何も起きない選択肢を
47 個並べない）。**地図は 47 県すべてを描く** ── 地図なので抜くと形が壊れる。
かわりに**候補の無い県は薄く塗って押せなくする。** どこで何も上演されていないかが
見えること自体が、この地図の中身の半分である。
"""

from __future__ import annotations

import json
from pathlib import Path

import charts as CH
import icons as IC
import render_recommend as RR

ROOT = Path(__file__).resolve().parents[2]
SHAPES = ROOT / "data" / "review" / "japan_prefs.json"

# 八地方区分。**並びは北から南**（`RR.PREFS` と同じ向き）
REGIONS = (
    ("北海道", ("北海道",)),
    ("東北", ("青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県")),
    ("関東", ("茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県")),
    ("中部", ("新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
              "岐阜県", "静岡県", "愛知県")),
    ("近畿", ("三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県")),
    ("中国", ("鳥取県", "島根県", "岡山県", "広島県", "山口県")),
    ("四国", ("徳島県", "香川県", "愛媛県", "高知県")),
    ("九州・沖縄", ("福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県",
                    "鹿児島県", "沖縄県")),
)
W = 430                      # 地図の幅（`viewBox` の中の値）
_SHAPES: dict | None = None


def _shapes() -> dict:
    """県ごとの輪郭。**無ければ空で返す** ── 地図が出ないだけで、絞り込みは動く。"""
    global _SHAPES
    if _SHAPES is None:
        _SHAPES = ((json.loads(SHAPES.read_text(encoding="utf-8")).get("prefs") or {})
                   if SHAPES.exists() else {})
    return _SHAPES


def region_counts(d: dict) -> dict:
    """地方ごとに、**そこで観られる公演の件数**を数える。

    **県ごとの件数を足し算しない。** ツアーは複数の県に立つので、足すと同じ 1 本が
    何度も数えられる（関東だけで実測 2 割増しになる）── **作品を集合で数える。**
    """
    where = {p: r for r, ps in REGIONS for p in ps}
    n: dict = {r: set() for r, _ in REGIONS}
    for c in (d.get("ranked") or d.get("recommend") or []):
        key = str(c.get("stage_id") or c.get("title") or "")
        for p in {v["pref"] for v in RR.venues(c) if v["pref"]}:
            if p in where:
                n[where[p]].add(key)
    return {r: len(v) for r, v in n.items()}


def regions_html(counts: dict, rcounts: dict) -> str:
    """地方の札。**押すと、その地方の県のチェックが一斉に入る。**

    **候補の無い県は入れない。** 「関東地方」で 7 県すべてに印を付けても、候補が
    0 件の県は絞り込みに何も足さない ── **押した結果が変わらない印を付けない。**
    候補が 1 県も無い地方は、札そのものを出さない。
    """
    out = []
    for r, ps in REGIONS:
        live = [p for p in ps if counts.get(p)]
        if not live:
            continue
        out.append(
            f'<button type="button" class="prg" data-prefs="{" ".join(live)}">'
            f'{r}地方<span class="pn">{rcounts.get(r, 0)}</span></button>')
    return (f'<div class="prgs" role="group" aria-label="地方でまとめて選ぶ">'
            f'<span class="prgl">地方でまとめて選ぶ</span>{"".join(out)}'
            f'<button type="button" class="prg clr">選択を消す</button></div>')


def map_html(counts: dict) -> str:
    """押せる日本地図。**選んだかどうかは 1 つも持たない**（塗りは CSS が決める）。"""
    sh = _shapes()
    if not sh:
        return ""
    h = CH._frame(CH.JP, W)
    paths = []
    for p in RR.PREFS:
        rings = sh.get(p)
        if not rings:
            continue
        n = counts.get(p, 0)
        d = "".join(
            "M" + " ".join(
                "{:.1f},{:.1f}".format(*CH._proj(lon, lat, CH.JP, W, h))
                for lon, lat in ring) + "Z"
            for ring in rings)
        paths.append(
            f'<path class="pf{"" if n else " off"}" data-pref="{p}" d="{d}">'
            f'<title>{p}{f" {n} 件" if n else " ── 候補なし"}</title></path>')
    # **読み上げからは外す。** 地図はチェックの並びを別の形で触るための口であって、
    # **同じ選択肢を 2 度読み上げさせても選びやすくならない** ── 件数も名前も
    # チェックの札の側に文字で出ている
    return (f'<svg class="pmap" viewBox="0 0 {W:.0f} {h:.0f}" width="100%"'
            f' aria-hidden="true" focusable="false">{"".join(paths)}</svg>')


def panel(counts: dict, rcounts: dict) -> str:
    """地方の札と地図をまとめた一段。**チェックの並びの上に置く。**"""
    m = map_html(counts)
    # **説明は地図の上に置く。** 地図は幅いっぱい（430px）まで使うので、横に文を
    # 置くと地図が半分になる ── **小さい県が押せなくなるのは、幅を削ったときである。**
    # **下の札から選べることを書く。** 大阪府・滋賀県・奈良県・香川県・埼玉県は
    # 地図の上で 11〜13px しかない（実測）── 押しにくいときの道を先に言う
    # **輪郭がまだ無いときは、無いと言って取り方を書く。** 黙って地図が出ないと、
    # 「この画面には地図が無い」と読まれる ── 1 度だけ走らせれば出るものである
    if not m:
        return (f'{regions_html(counts, rcounts)}'
                f'<p class="pmaplead">{IC.ico("search", 14)}'
                f'<b>地図から選ぶには、県の輪郭を 1 度だけ取り寄せる必要があります。</b>'
                f'いったんこの画面を閉じて、次の 1 行を実行してください（1 分ほどです）。'
                f'<br><code class="cmd">python3 tools/geo/fetch_pref_shapes.py</code></p>')
    return (f'{regions_html(counts, rcounts)}'
            f'<div class="pmapbox">'
            f'<p class="pmaplead">{IC.ico("search", 14)}'
            f'<b>地図の県を押しても選べます。</b>'
            f'薄い県は、いま観られる公演がありません。'
            f'小さくて押しにくい県は、下の札からも選べます。</p>{m}</div>')


# **塗りは 47 本の規則で出す。** チェックが本当の状態なので、`:has(...:checked)` で
# 地図の側を追わせる ── JavaScript は `checked` を反転させるだけで、塗りに触らない。
# **状態を 2 つ持たないための作りである**（ずれたときにどちらが本当か決められない）
# **`.pfil` で囲う。** `.pbox` は畳んである道具の枠として 4 か所で使い回している
# 名前なので（推薦の効かせ方・お気に入り・出さない語）、そちらの中の入力にも当たる
_ON = "".join(
    f'.pfil:has(input[value="{p}"]:checked) .pmap [data-pref="{p}"]{{'
    f'fill:var(--acc);stroke:var(--acc)}}' for p in RR.PREFS)

CSS = """
/* ---- 地方の札 ---------------------------------------------------------------
   **県の札と同じ形にしない。** 同じ丸い札にすると、47 個の中に 8 個が紛れて
   「押すと何が起きるのか」が見た目から消える ── 角の立った札にして、
   1 行目に置く（押す順が上から下になる）                                      */
.prgs{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:12px 0 0}
.prgl{font-size:12px;color:var(--mute);margin-right:2px}
.prg{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:8px;cursor:pointer;
 display:inline-flex;gap:6px;align-items:center;
 border:1px solid var(--ring);background:var(--plane);color:var(--ink2)}
.prg:hover{color:var(--ink);border-color:var(--base)}
.prg.on{border-color:var(--acc);color:var(--acc);background:var(--surf);font-weight:600}
.prg .pn{font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.prg.on .pn{color:var(--acc)}
.prg.clr{margin-left:auto;color:var(--mute)}
/* ---- 地図 -------------------------------------------------------------------
   **幅は 430px で止める。** 絞り込みの箱の中の 1 部品なので、広い画面で本文の幅
   いっぱいに伸びると、地図を見に来たように見える                              */
.pmapbox{margin:14px 0 0}
/* **幅は使えるだけ使う（上限 430px）。** 大阪府・滋賀県・奈良県・香川県・埼玉県は
   430px の地図の上でも 11〜13px しかない（実測）── ここを削ると押せなくなる */
.pmap{display:block;width:100%;max-width:430px;margin:8px auto 0}
.pmaplead{font-size:12.5px;color:var(--mute);line-height:1.7;margin:0}
.pmap .pf{fill:var(--plane);stroke:var(--ring);stroke-width:.6;cursor:pointer;
 transition:fill .12s}
/* **触れている県は線でも出す。** 小さい県は塗りが 11px しか変わらないので、
   塗りだけでは「いまどこに触れているか」が読めない */
.pmap .pf:hover{fill:var(--base);stroke:var(--ink2);stroke-width:1.1}
/* **候補の無い県は押せない。** 薄いだけにして消さない ── どこで何も上演されて
   いないかが見えることが、この地図の中身の半分である                          */
.pmap .pf.off{fill:color-mix(in srgb,var(--plane) 55%,transparent);
 stroke:color-mix(in srgb,var(--ring) 55%,transparent);cursor:default;
 pointer-events:none}
@media(prefers-reduced-motion:reduce){.pmap .pf{transition:none}}
""" + _ON

JS = """
// **地図と地方の札は、チェックを反転させるだけである。**（`prefmap.py` の説明）
// 塗りは CSS が `:checked` から決めるので、ここでは見た目に触らない ──
// **状態を 2 つ持つと、ずれたときにどちらが本当か決められない。**
(() => {
  // **`.pfil`（場所の絞り込みの form）だけを見る。** `.pbox` は畳んである道具の枠
  // として使い回している名前なので、最初の 1 つが場所の箱とはかぎらない
  const box = document.querySelector("form.pfil");
  if (!box) return;
  const cb = v => box.querySelector('input[name="pref"][value="' + CSS.escape(v) + '"]');
  // 地方の札は「その地方の県が全部入っているか」で光る。全部入っていれば外す側に働く
  const marks = () => box.querySelectorAll(".prg[data-prefs]").forEach(b => {
    const ps = b.dataset.prefs.split(" ");
    b.classList.toggle("on", ps.every(p => cb(p) && cb(p).checked));
  });
  box.addEventListener("click", ev => {
    const pf = ev.target.closest && ev.target.closest(".pmap .pf");
    if (pf) {
      const c = cb(pf.dataset.pref);
      if (c) { c.checked = !c.checked; marks(); }
      return;
    }
    const rg = ev.target.closest && ev.target.closest(".prg");
    if (!rg) return;
    if (rg.classList.contains("clr")) {
      box.querySelectorAll('input[name="pref"]').forEach(c => { c.checked = false; });
      marks();
      return;
    }
    const ps = rg.dataset.prefs.split(" ");
    // **全部入っているときは外す。** 同じ札を 2 度押して何も起きないのは、
    // 押し口として壊れている
    const all = ps.every(p => cb(p) && cb(p).checked);
    ps.forEach(p => { const c = cb(p); if (c) c.checked = !all; });
    marks();
  });
  marks();
})();
"""
