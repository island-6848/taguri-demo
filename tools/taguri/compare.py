#!/usr/bin/env python3
"""「比べる」に足す 3 つの軸。**自分の割合と、これから上演される公演の割合を並べる。**

起案者の指示（2026-08-25）──「たぐりの『記録を見返すページ』の『比べる』で、たぐりが
扱うデータで、世の中との差を比較できそうな項目を考えて」。**案を出して選んでもらった。**

## きっかけ ── 棚上げの理由が古くなっていた

この画面には「まだ比較できない軸」という節があり、**題材について「母集団の側に要素が
無い。ここが通れば『世の中より翻訳劇を N 倍観ている』が出せるようになり、いちばん効く
軸になります」**と書いてあった。**その前提はもう解けている** ── あらすじの要素は
これから上演される公演の側 649 件に付いている。棚上げした項目は、前提が解けた時点で見直す。

## 足した 3 つ

| 軸 | 何が言えるか | 自分 | これからの公演 |
|---|---|---|---|
| **題材のまとまり** | 家族の話を 2.4 倍観ている／恋の話は 0.4 倍 | 35 作品 | 649 件 |
| **座組の大きさ** | 10〜19 名を 1.8 倍／1〜4 名は 0.36 倍 | 54 作品 | 655 件 |
| **作りの型** | 翻訳劇 2.3 倍・音楽劇 1.6 倍 | 60 作品 | 818 件 |

## 出さないと決めた 2 つ

**上演時期（月・季節）は比較が成立しない。** 数字は出るが「6 月が 35 倍」になる ──
**比べる相手は「これから上演される公演」だけ**なので、その側の月の分布が先の数か月に
偏っているだけである。自分は過去 5 年、相手は今後 7 か月。**並べてはいけない。**

**地域は出さない。** 東京 92% 対 50%（1.9 倍）と出るが、**本人が既に知っている。**

## 語のままでは比べられない ── まとめ直してから比べる

**要素の語をそのまま使うと、1〜2 件で倍率が跳ねる** ── 実測で「ブラックコメディ
35.3 倍」（自分 2 件・相手 1 件）、「兄弟 14.7 倍」（自分 5 件・相手 6 件）。
**既にある分類（`data/credits/theme_groups.json`）でまとめ直すと、倍率は 0.4〜2.4 に
収まった。** 粒度を上げるのではなく、意味の近い語をグループにまとめる操作である。

**原作（実在の作家・作品名）はグループから外してある**（分類の側でそう決めてある）──
「シェイクスピア」は題材ではなく名前なので、名前の網が扱う。

## 形は、この画面に既にあるものに揃える

**「上演日数の偏り」と同じ発散の表にする。** 中心線が「同じ割合」で、右が
「自分のほうが多い」、左が「これからの公演のほうが多い」── **同じ問いには
同じ形を使う。** 図ごとに形を変えると、読み手は毎回読み方を覚え直すことになる。

**色は藍と朱にした。** 以前の緑と赤は、**色覚の型によってはほぼ同じ色に見える**
（検証にかけると deutan で ΔE 2.3・下限 8 を大きく下回る）。藍と朱は ΔE 18.4 で
全項目 PASS である。**そもそも緑と赤は良し悪しの色**で、この図が出しているのは
偏りであって優劣ではない。
"""

from __future__ import annotations

import collections
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))

E = lambda s: html.escape(str(s))                                   # noqa: E731

THEMES = ROOT / "data" / "credits" / "themes.jsonl"
GROUPS = ROOT / "data" / "credits" / "theme_groups.json"
CAND = ROOT / "data" / "review" / "candidates.jsonl"
CREDITS = ROOT / "data" / "credits" / "credits.jsonl"

# **少ない件数で倍率を出さない。** 自分側が 1 件の行は、倍率が分母の揺れをそのまま映す
MIN_MINE = 2
# 座組の大きさの段。**人数そのものではなく段で比べる** ── 11 名と 12 名の差は意味を持たない
CAST_BANDS = ((1, 4, "1〜4 名"), (5, 9, "5〜9 名"), (10, 19, "10〜19 名"), (20, 999, "20 名以上"))
# 作りの型。**クレジットに欄があるかどうかで判定する**（推測はしない）
CRAFTS = (("翻訳", "翻訳劇（翻訳者がクレジットされている）"),
          ("作曲", "音楽劇（作曲者がクレジットされている）"),
          ("原作", "原作つき（原作がクレジットされている）"),
          ("振付", "振付つき（振付師がクレジットされている）"))


def _lines(p: Path):
    return (p.read_text(encoding="utf-8").split("\n") if p.exists() else [])


def _cand_fields() -> list[dict]:
    out = []
    for line in _lines(CAND):
        if line.strip():
            out.append(json.loads(line).get("fields") or {})
    return out


def _rated_fields(rated: list[dict]) -> list[dict]:
    """自分が観た作品のクレジット。**公演の id で引く。**"""
    by_id = {}
    for line in _lines(CREDITS):
        if not line.strip():
            continue
        c = json.loads(line)
        if c.get("stage_id"):
            by_id[str(c["stage_id"])] = c.get("fields") or {}
    return [by_id[str(r["stage_id"])] for r in rated
            if r.get("stage_id") and str(r["stage_id"]) in by_id]


# ---------------------------------------------------------------- 3 つの軸
def theme_rows() -> tuple[list[dict], int, int]:
    """題材のまとまり。**作品ごとに、そのまとまりに入るかどうかを数える**
    （1 作品に要素が 5 つあっても、同じまとまりは 1 回だけ数える）。"""
    if not GROUPS.exists():
        return [], 0, 0
    g = json.loads(GROUPS.read_text(encoding="utf-8"))
    w2g, exc, names = g["word_to_group"], set(g["excluded"]), g["groups"]
    mine: collections.Counter = collections.Counter()
    world: collections.Counter = collections.Counter()
    n_mine = n_world = 0
    for line in _lines(THEMES):
        if not line.strip():
            continue
        t = json.loads(line)
        side = t.get("side")
        if side not in ("rated", "candidate"):
            continue
        gs = {w2g[e["word"]] for e in (t.get("elements") or [])
              if isinstance(e, dict) and e.get("word")
              and e["word"] not in exc and e["word"] in w2g}
        if not gs:
            continue
        if side == "rated":
            n_mine += 1
            for x in gs:
                mine[x] += 1
        else:
            n_world += 1
            for x in gs:
                world[x] += 1
    return _rows(names, mine, world, n_mine, n_world), n_mine, n_world


def cast_rows(rated: list[dict]) -> tuple[list[dict], int, int]:
    """座組の大きさ。**出演の欄に並んだ人数で段に分ける。**"""
    import measure_nets as M

    def n_cast(fields: dict) -> int:
        return len([1 for role, _p in M.parse_credits(fields) if role == "出演"])

    def band(n: int) -> str:
        for lo, hi, lab in CAST_BANDS:
            if lo <= n <= hi:
                return lab
        return ""

    mine: collections.Counter = collections.Counter()
    world: collections.Counter = collections.Counter()
    n_mine = n_world = 0
    for r in rated:
        n = len([1 for role, _p in (r.get("people") or []) if role == "出演"])
        if n:
            n_mine += 1
            mine[band(n)] += 1
    for f in _cand_fields():
        n = n_cast(f)
        if n:
            n_world += 1
            world[band(n)] += 1
    return (_rows([lab for _lo, _hi, lab in CAST_BANDS], mine, world, n_mine, n_world),
            n_mine, n_world)


def craft_rows(rated: list[dict]) -> tuple[list[dict], int, int]:
    """作りの型。**クレジットに欄があるかどうかだけを見る**（あらすじからは推測しない）。"""
    mf = _rated_fields(rated)
    wf = _cand_fields()
    mine: collections.Counter = collections.Counter()
    world: collections.Counter = collections.Counter()
    for key, lab in CRAFTS:
        mine[lab] = sum(1 for f in mf if (f or {}).get(key))
        world[lab] = sum(1 for f in wf if (f or {}).get(key))
    return (_rows([lab for _k, lab in CRAFTS], mine, world, len(mf), len(wf)),
            len(mf), len(wf))


def _rows(names, mine, world, n_mine, n_world) -> list[dict]:
    """割合と倍率を組む。**倍率が出せない行も落とさず、出せないと書く。**

    **相手側が 0 件の行で倍率を出さない** ── 0 で割った値は「無限に多く観ている」では
    なく「比べる相手がいない」である。
    """
    if not n_mine or not n_world:
        return []
    out = []
    for nm in names:
        a, b = mine.get(nm, 0), world.get(nm, 0)
        pa, pb = a / n_mine * 100, b / n_world * 100
        out.append({"label": nm, "mine": pa, "pop": pb, "n": a, "n_pop": b,
                    "ratio": (pa / pb) if pb else None,
                    "thin": a < MIN_MINE})
    # **自分のほうが多い順に並べる。** 倍率が出せない行は最後に置く
    out.sort(key=lambda r: (r["ratio"] is None, -(r["ratio"] or 0)))
    return out


def population() -> dict:
    """比べる相手が何なのかを、**そのつど数えて**返す。

    起案者の問い（2026-08-25）──「『世の中』ってなに？」。**答えられなかったので、
    画面から『世の中』という言い方をやめた。**

    ## なぜ言い換えたか

    比べる相手は日本の演劇すべてではない ── **CoRich という 1 つの情報サイトに載っている、
    これから上演される公演**である。「世の中」はそれより広いものを指す語で、
    **何を数えたのかが名前から分からない。**

    ## 数字を書き置きにしない

    **件数も期間もここで数える。** 同じ画面の「まだ比較できない軸」は、書いた時点の
    事実を文に埋め込んだまま古くなり、**解けた前提を「まだできない」と言い続けていた。**
    数えて出せば古くならない。
    """
    import datetime
    import re as _re
    rows = [json.loads(x) for x in _lines(CAND) if x.strip()]
    days = []
    for r in rows:
        ms = _re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", r.get("period") or "")
        if ms:
            days.append((datetime.date(*map(int, ms[0])), datetime.date(*map(int, ms[-1]))))
    today = datetime.date.today()
    other = sum(1 for x in _lines(ROOT / "data" / "review" / "calendar.jsonl") if x.strip())
    return {"n": len(rows), "n_upcoming": sum(1 for a, _b in days if a > today),
            "n_running": sum(1 for a, b in days if a <= today <= b),
            "n_ended": sum(1 for _a, b in days if b < today),
            "first": min((a for a, _b in days), default=None),
            "last": max((a for a, _b in days), default=None),
            "other": other}


def pop_note(rated: list[dict]) -> str:
    """比べる相手を名指しする 1 段落。**3 つの図の前に 1 回だけ置く。**"""
    d = population()
    if not d["n"]:
        return ""
    ds = sorted(r["date"] for r in rated if r.get("date"))

    def ym(d: str) -> str:
        # **月の 0 を落とす。** 「2021 年 08 月」は日付の書式であって、読む文ではない
        y, m = d[:4], d[5:7]
        return f"{y} 年 {int(m)} 月"

    span = (f'あなたの記録は <b>{ym(ds[0])}から{ym(ds[-1])}まで</b>の分で、'
            if ds else "")
    months = 0 if not d["first"] else max(
        1, (d["last"].year - d["first"].year) * 12 + d["last"].month - d["first"].month)
    per = ("" if not d["first"] else
           f'（初日が {d["first"].year} 年 {d["first"].month} 月〜'
           f'{d["last"].year} 年 {d["last"].month} 月）')
    return f"""<section class="card">
<h2>比べる相手は何か</h2>
<p class="why"><b>比べる相手は、演劇の情報サイト CoRich に載っている
「これから上演される公演」{d["n"]} 件です</b>{per} ──
まだ初日前が {d["n_upcoming"]} 件、上演中が {d["n_running"]} 件、
最近終わった分が {d["n_ended"]} 件です。</p>
<p class="note"><b>日本の演劇すべてではありません。</b>そのサイトに載っていない公演は
入りません。<br>
<b>時期がずれています。</b>{span}比べる相手は先の <b>{months} か月</b>ぶんの公演なので、
<b>過去のご自分と、これからの公演を並べている</b>ことになります。<br>
手元にはもう 1 つ公演の一覧（{d["other"]} 件）がありますが、劇場名と日付しか無いので、
出演者や題材を使う図では数えていません。<br>
<b>図ごとに件数が違います。</b>あらすじや出演者が取れた分だけを数えているので、
件数はそれぞれの図に書いてあります。</p></section>"""


# ---------------------------------------------------------------- 図
def _table(rows: list[dict], head: str, unit: str) -> str:
    mx = max((abs(r["mine"] - r["pop"]) for r in rows), default=1) or 1
    body = []
    for r in rows:
        d = r["mine"] - r["pop"]
        w = abs(d) / mx * 50
        cls, left = ("pos", 50.0) if d >= 0 else ("neg", 50.0 - w)
        # **倍率が出せない行は、数字の代わりに理由を書く**（空欄にして黙って落とさない）
        if r["ratio"] is None:
            ratio = '<span class="dim">比べる相手なし</span>'
        elif r["thin"]:
            ratio = f'<span class="dim">{r["ratio"]:.1f} 倍（{r["n"]} 件）</span>'
        elif abs(r["ratio"] - 1) < 0.05:
            # **同じ割合の行に、多い／少ないの色を付けない。** 20% 対 20% で
            # 小数点以下が僅かに下回っただけの行が「自分のほうが少ない」の色になっていた
            ratio = f'<span class="dim">{r["ratio"]:.1f} 倍（同じ割合）</span>'
        else:
            ratio = (f'<span class="{"up" if d >= 0 else "dn"}">'
                     f'{r["ratio"]:.1f} 倍</span>')
        body.append(
            f'<tr><td class="nm">{E(r["label"])}</td>'
            f'<td class="dv"><span class="axis"></span>'
            f'<span class="dvbar {cls}" style="left:{left:.1f}%;width:{w:.1f}%"></span></td>'
            f'<td class="num">{r["pop"]:.0f}%</td>'
            f'<td class="num strong">{r["mine"]:.0f}%</td>'
            f'<td class="num">{ratio}</td>'
            f'<td class="num dim">{r["n"]}</td></tr>')
    return (f'<table class="tbl"><thead><tr><th>{E(head)}</th>'
            f'<th class="th-dv">これからの公演との差</th><th class="num">これからの公演</th>'
            f'<th class="num">自分</th><th class="num">倍率</th>'
            f'<th class="num">{E(unit)}</th></tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


LEGEND = ('<div class="legend"><span class="lg"><i class="sw s-pos"></i>'
          '自分のほうが多い</span>'
          '<span class="lg"><i class="sw s-neg"></i>これからの公演のほうが多い</span>'
          '<span class="lg">中心線＝同じ割合</span></div>')


def panel(rated: list[dict]) -> str:
    """軸をまとめて返す。**取れなかった軸は、その軸だけ出さない。**

    **「座組の大きさ」は外した**（起案者の指示・2026-08-26 ──「『比べる』の…
    『座組の大きさ』…は消してよい」）。`cast_rows` 自体は残す ── 単独で
    `python3 compare.py` を動かして数字だけ見る用途（`__main__` の下）は崩さない。
    **見出しの番号を外した。**「比べる」は「眺める」に統合されて 1 枚の画面に
    なり（同日の指示）、上に積む図の数がその日の実装で変わる ── 固定の番号を
    付けると、外した番号が歯抜けになる（実際に 1・2・6 番を外してそうなった）。
    """
    out = []

    th, tm, tw = theme_rows()
    if th:
        out.append(f"""<section class="card">
<h2>題材の偏り ── 何の話を観ているか</h2>
<p class="why"><b>あらすじから取り出した題材を、意味の近いものでまとめて比べています。</b>
語のまま比べると、1〜2 件しかない語で倍率が大きく振れてしまうためです。</p>
{LEGEND}
{_table(th, "題材のまとまり", "作品")}
<p class="note">ご自分の側はあらすじの取れた <b>{tm} 作品</b>、比べる相手は
<b>{tw} 件</b>です。<b>1 作品が複数のまとまりに入ります</b>ので、割合を足しても
100% にはなりません。あらすじが取れていない作品はこの図に入っていないので、
偏りの向きは読めますが、大きさは目安とお考えください。
実在の作家名・原作名（シェイクスピアなど）は題材から外しています。</p>
</section>""")

    ks, km, kw = craft_rows(rated)
    if ks:
        out.append(f"""<section class="card">
<h2>作りの型 ── 翻訳劇・音楽劇をどれだけ観ているか</h2>
<p class="why"><b>公演ページのクレジットに、その欄があるかどうかで数えています。</b>
翻訳者の名前が載っていれば翻訳劇、作曲者が載っていれば音楽劇です。
あらすじからの推測はしていません。</p>
{LEGEND}
{_table(ks, "作りの型", "作品")}
<p class="note">ご自分の側はクレジットの取れた <b>{km} 作品</b>、比べる相手は
<b>{kw} 件</b>です。<b>{MIN_MINE} 件に満たない行は薄く出しています</b> ──
件数が少ないと倍率が大きく振れるためです。
クレジットに欄が無いだけで実際には翻訳劇である公演は、数えられていません。</p>
</section>""")

    if not out:
        return ""
    return "".join(out)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import measure_nets as M
    r = M.load_rated()
    for name, (rows, a, b) in (("題材", theme_rows()), ("座組", cast_rows(r)),
                               ("作り", craft_rows(r))):
        print(f"== {name}（自分 {a} / これからの公演 {b}）")
        for x in rows:
            rt = "—" if x["ratio"] is None else f'{x["ratio"]:.2f}'
            print(f'   {x["label"]:24s} 自分 {x["mine"]:>5.0f}%  相手 {x["pop"]:>5.0f}%'
                  f'  倍 {rt:>5s}  n={x["n"]}')
