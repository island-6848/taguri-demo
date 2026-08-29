#!/usr/bin/env python3
"""記録を見返す ▸ **たどる。** 1 つの名前を選び、その名前が通っている公演を時間の上で読む。

仕様は [docs/000007-records-trace-spec.md](../../docs/000007-records-trace-spec.md)。
起案者の指示（2026-08-25）── 案 1（名前をつまむと、その名前が通っている公演が手元に
並ぶ）と案 2（そこから次の名前へ乗り換わった道筋）を 1 画面にする。

## この画面が答える問い

**「この名前、前に何で観たか」と「その名前にいつ出会い、そこから何につながったか」**の
2 つだけである。**本数や劇場の集計は出さない** ── 本人が既に知っている事実の確認に
なるからで、それは既にある図の役でもある。

## 既にある図と役が重ならないこと

| 既にあるもの | 言えること | 言えないこと |
|---|---|---|
| 人の網（`people.py`） | 誰と誰が同じ束か | **時間を持たない**（いつ出会ったか） |
| 一緒だった人の流れ（`storyline.py`） | 観る世界が乗り換わっていること | 1 人を選んで深く見る形になっていない |

**1 人を選んで深く見るのは、この画面だけである。** もとは「作り手の再会」
（`timeline.py` の一望する図）と分担していたが、そちらは「眺める」から外した
（起案者の指示・2026-08-26 ──「『眺める』の『作り手の再会』…は消してよい」。
`app.page_records` の docstring 参照）。**入口は新しく作らず、既にある図の名前を
押すとこの画面に着く**という決まり自体は変えていない。

## 比喩は形と動きだけで出す

画面の文字に「たぐる」「糸」と書かない（意匠に付けた呼び名を画面の文章に使わない）。
**線は 1px の直線にしない** ── 撚れ・たるみ・太さのむら・結び目のふくらみを持たせる。
**動きが終わったあとの静止した形だけで読めること。** 動きに情報は載せない。

## 評価で塗らない

作品単位の評価を、関わった個人への評価として使わない。**結び目は全部同じ色**である。
"""

from __future__ import annotations

import collections
import hashlib
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts as CH                                                  # noqa: E402
import icons as IC                                                   # noqa: E402
import people as PE                                                  # noqa: E402

E = lambda s: html.escape(str(s))                                   # noqa: E731

# **糸にできる役は `people.py` にそろえる。** 出演＋作り手 9 役で、裏方は入れない ──
# 判別力がゼロ（検証 018・AUC 0.500）で、理由に出た 7 件のうち決め手に挙がった行が
# 0 件だった（検証 028）。**推薦の理由欄と同じ範囲にする。**
KEEP_ROLES = PE.KEEP_ROLES
MIN_WORKS = 2      # 糸にする下限（1 作品だけの人は線にならない）
BRANCH_MIN = 3     # 次の糸に垂らす下限。1 回の観劇に中央値 19 名が出るので絞らないと毛玉になる
BRANCH_MAX = 4     # 図に垂らす枝の上限（結び目 1 つにつき 1 名まで）
BRANCH_AWAY = 180  # 次の名前が「別の時期にも出てくる」と言える隔たり（日）
TRAIL_MAX = 3      # たどってきた道を出す深さ

HREF = "/records/trace?t=__TAGURI_TOKEN__"
ARROW = "\u2192"          # たどってきた道の区切り（URL に載せる）


# ---------------------------------------------------------------- 材料を組む
def build(rated: list[dict]) -> dict:
    """名前ごとに、観た公演を古い順に並べる。**上演日を持つ記録だけが線に乗る。**

    乗らない件数も返す ── 限界は注記に逃がさず、画面の数字の側に出す。
    """
    dated = [r for r in rated if (r.get("date") or "")]
    dated.sort(key=lambda r: (r["date"], r.get("key") or ""))
    occ: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    roles: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    who: dict[str, set] = {}
    for r in dated:
        ps = set()
        for role, person in r.get("people") or []:
            if role in KEEP_ROLES:
                roles[person][role] += 1
                # **同じ公演は 1 つの結び目。** 役を 2 つ持っていても結び目は増やさない
                occ[person][r["key"]] = r
                ps.add(person)
        who[r["key"]] = ps
    # **その人をはじめて観た公演。** 枝（次の名前）は、この日にはじめて出てくる人に限る
    first: dict[str, str] = {}
    for r in dated:
        for p in who.get(r["key"], ()):
            first.setdefault(p, r["key"])
    threads = {p: sorted(v.values(), key=lambda r: r["date"])
               for p, v in occ.items() if len(v) >= MIN_WORKS}
    return {"threads": threads, "roles": roles, "who": who, "first": first,
            "occ": occ, "n_all": len(rated), "n_dated": len(dated),
            "n_undated": len(rated) - len(dated)}


def declared_names() -> set:
    """本人が「お気に入り」に登録した名前。**申告した名前は本人が既に知っている。**"""
    try:
        import recommend as RC
        nz = getattr(RC, "nz", lambda s: s)
        return {nz(x) for xs in RC.DECLARED.values() for x in xs}
    except Exception:                                               # noqa: BLE001
        return set()


def _nz(s: str) -> str:
    try:
        import recommend as RC
        return RC.nz(s) if hasattr(RC, "nz") else s
    except Exception:                                               # noqa: BLE001
        return s


def picks(g: dict) -> list[dict]:
    """つまむ相手の並び。**申告していない名前を先に、そのなかで線の長い順。**

    五十音で 77 名を並べても、どれを押せばよいか分からない。**発見は申告していない側に
    ある**ので（4 回以上観ている 28 人のうち申告は 6 人だけだった）、そちらを先に出す。
    """
    dec = declared_names()
    out = []
    for name, rows in g["threads"].items():
        out.append({
            "name": name,
            "role": "・".join(k for k, _ in g["roles"][name].most_common(2)),
            "n": len(rows),
            "from": rows[0]["date"], "to": rows[-1]["date"],
            "span": _days(rows[0]["date"], rows[-1]["date"]),
            "declared": _nz(name) in dec,
        })
    out.sort(key=lambda x: (x["declared"], -x["span"], -x["n"], x["name"]))
    return out


def _days(a: str, b: str) -> int:
    import datetime
    try:
        return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return 0


def branches(g: dict, name: str) -> dict[str, list]:
    """結び目ごとに、そこから移れる名前。**その公演に居た人は全員が対象である。**

    ## はじめて観た人だけに絞るのをやめた（2026-08-25）

    起案者の指摘 ──「下に垂れている名前を、はじめて観た人だけに限定する意図が
    わからない」。**意図は「いつ知って、そこから何につながったか」を出すことだったが、
    数えると成り立っていなかった。**

    | | はじめて観た人だけ | その公演に居た人すべて |
    |---|---|---|
    | 1 つの結び目から移れる名前 | 平均 0.67・**中央値 0** | 平均 3.1・中央値 2 |
    | **移れる先が 1 つも無い結び目** | **234 個中 186 個（79%）** | ── |
    | **枝が 1 つも出ない糸** | **77 本中 43 本** | ── |

    **移れる先を、道筋の物語のために絞っていた。** はじめて観たかどうかは
    **事実として印を付けるべきもの**であって、**移動できるかどうかを決める条件では
    ない** ── 前に知っていた名前でも、その公演からその人をたどることに意味がある。
    印は残し、絞りだけをやめた。

    ## 残した条件は 2 つだけである

    **① その名前が 3 作品以上に出てくること。** 1 回の観劇に中央値 19 名が出るので、
    絞らないと毛玉になる。

    **② その名前が、いまの公演から半年（180 日）以上離れた公演を持っていること。**
    実測 ── 久山宏一（翻訳）の 6 作品はすべてデカローグなので、たどっても同じ座組から
    出られない。上演日数の中央値は 4 日、この記録で最長の繰り返しも 71 日なので、
    **半年離れた公演を持つことは「その名前が別の時期にも出てくる」ことと同じである。**

    **「直前の公演と作り手が重なる結び目では枝を出さない」という条件は外した。**
    デカローグの結び目に残る候補は上村聡史 1 名だけで、この人は「A・NUMBER」（2022）を
    持っておりデカローグから出られる ── **② が同じ仕事をしており、① と重ねると
    正しい乗り換えまで落ちていた。**

    **同じ名前は 1 本の線に 1 度しか出さない。** デカローグでは 6 つの結び目すべてに
    上村聡史が居るので、そのままだと同じ名前が 6 回垂れる。
    """
    rows = g["threads"].get(name) or []
    out: dict[str, list] = {}
    used = {name}
    for r in rows:
        cand = [p for p in g["who"].get(r["key"], ())
                if p not in used
                and len(g["occ"].get(p, ())) >= BRANCH_MIN
                and _leaves(g, p, r["date"])]
        if not cand:
            continue
        # **はじめて観た名前を先に、そのあとは作品数の多い順。**
        # 印は順番にだけ効かせ、出すかどうかには効かせない
        cand.sort(key=lambda p: (g["first"].get(p) != r["key"], -len(g["occ"][p]), p))
        used |= set(cand)
        out[r["key"]] = [{"name": p, "n": len(g["occ"][p]),
                          "new": g["first"].get(p) == r["key"],
                          "role": "・".join(k for k, _
                                            in g["roles"][p].most_common(2))}
                         for p in cand]
    return out


def _leaves(g: dict, person: str, date: str) -> bool:
    """その名前をたどると、いまの時期から出られるか。**出られないなら出さない。**"""
    return any(abs(_days(date, r["date"])) > BRANCH_AWAY
               for r in g["occ"].get(person, {}).values())


# ---------------------------------------------------------------- 線を描く
SVG_W, MID_Y, PAD_X = 880.0, 150.0, 52.0
GAP_MIN = 74.0          # 結び目どうしの最小の間隔（近い日付が重なって読めなくなるのを防ぐ）


def _wob(seed: str, lo: float, hi: float) -> float:
    """名前と番号から決まる、毎回同じゆらぎ。**乱数を使わない** ── 開くたびに形が変わると、
    前に見た形と見比べられない。"""
    h = int(hashlib.md5(seed.encode("utf-8")).hexdigest()[:8], 16)
    return lo + (hi - lo) * (h % 1000) / 999.0


def _xs(rows: list[dict]) -> list[float]:
    """結び目の横位置。**横は時間である**が、近すぎる日付は最小の間隔まで押し広げる。"""
    import datetime
    ds = []
    for r in rows:
        try:
            ds.append(datetime.date.fromisoformat(r["date"]).toordinal())
        except (TypeError, ValueError):
            ds.append(ds[-1] if ds else 0)
    lo, hi = min(ds), max(ds)
    span = SVG_W - PAD_X * 2
    xs = [PAD_X + (span * (d - lo) / (hi - lo) if hi > lo else
                   span * i / max(len(ds) - 1, 1)) for i, d in enumerate(ds)]
    for i in range(1, len(xs)):                          # 押し広げる
        xs[i] = max(xs[i], xs[i - 1] + GAP_MIN)
    if xs[-1] > SVG_W - PAD_X:                           # 広げた分を畳んで枠に収める
        k = (SVG_W - PAD_X * 2) / (xs[-1] - xs[0])
        xs = [PAD_X + (x - xs[0]) * k for x in xs]
    return xs


def _thread_svg(name: str, rows: list[dict], brs: dict, nxt: str) -> str:
    """1 本の線と結び目。**線は 3 本重ねて撚りに見せる。**"""
    xs = _xs(rows)
    ys = [MID_Y + _wob(f"{name}#{i}#y", -5.0, 5.0) for i in range(len(rows))]
    segs, hi = [], []
    for i in range(len(rows) - 1):
        x0, y0, x1, y1 = xs[i], ys[i], xs[i + 1], ys[i + 1]
        sag = _wob(f"{name}#{i}#s", 7.0, 17.0)           # たるみ
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + sag
        w = _wob(f"{name}#{i}#w", 4.6, 6.2)              # 太さのむら
        d = f"M{x0:.1f} {y0:.1f}Q{cx:.1f} {cy:.1f} {x1:.1f} {y1:.1f}"
        segs.append(f'<path d="{d}" class="ln" stroke-width="{w:.1f}"/>')
        segs.append(f'<path d="{d}" class="ln2" stroke-width="{w * .3:.1f}"'
                    f' transform="translate(0,-1.1)"/>')
        hi.append(f'<path d="{d}" class="ln3" stroke-width="{w * .26:.1f}"'
                  f' transform="translate(0,1.2)"/>')
    knots, labs, brh = [], [], []
    max_stack = 0      # 枝を出す結び目のうち、いちばん多く垂れた人数（図の高さに使う）
    for i, r in enumerate(rows):
        x, y = xs[i], ys[i]
        a = CH._anchor(r["key"])
        rr = 7.2 + _wob(f"{name}#{i}#r", -0.9, 1.3)      # ふくらみは一定にしない
        knots.append(
            f'<a href="{CH.ROW_HREF}&amp;w={E(a)}#w-{E(a)}"><g class="kn">'
            f'<title>{E(r["title"])} ── {E(_jdate(r["date"]))}</title>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr + 2.6:.1f}" class="kh"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" class="kc"/>'
            f'<text x="{x:.1f}" y="{y + 3.6:.1f}" class="kn-n">{i + 1}</text>'
            f'</g></a>')
        labs.append(f'<text x="{x:.1f}" y="{y - 20:.1f}" class="kd">'
                    f'{E(r["date"][:4])}<tspan class="kd2">.{E(r["date"][5:7])}</tspan></text>')
        bs = brs.get(r["key"])
        if not bs or len(brh) >= BRANCH_MAX:
            continue
        # **図に垂らすのは、その結び目から移れる名前の全員である**（起案者の指示・
        # 2026-08-26 ──「その人名は一人にせず垂らせる人全員だしてほしい」。もとは
        # いちばん上の1名だけを垂らし、残りは下の並びに文字で出していた）。**1本の
        # 枝の下に、縦に積んで並べる** ── 図だけを見ても「誰に移れるか」が全員分
        # 分かるようにする。下の並び（文字の一覧）は、こちらでは省いた作品数や
        # 出典を添える役目のまま残す
        #
        # **右端に近い結び目は、左向きに垂らす**（起案者の指摘・2026-08-26 ──
        # 「図の一番右の垂らしているやつが見切れている」）。名前の文字は結び目の
        # 右へ伸びる形で置いていたので、いちばん右の結び目（`xs` の右端は
        # `SVG_W - PAD_X`）では文字が `viewBox` の外へはみ出ていた。**ラベル 1 行分
        # （円・余白・文字・件数の注記）に要る幅を見積もり、右に収まらない結び目だけ
        # 左向きに反転する**。
        ROW_H = 17.5
        LABEL_W = 230.0    # 名前＋件数の注記が要る横幅の見積もり
        flip = x + 30 + LABEL_W > SVG_W - PAD_X
        bx, by0 = (x - 30 if flip else x + 30), y + 74
        max_stack = max(max_stack, len(bs))
        parts = [f'<path d="M{x:.1f} {y:.1f}Q{x:.1f} {y + 46:.1f} {bx:.1f} {by0:.1f}"'
                 f' class="br"/>']
        for j, b in enumerate(bs):
            by = by0 + j * ROW_H
            if j:
                parts.append(f'<path d="M{bx:.1f} {by - ROW_H:.1f}V{by:.1f}" class="br"/>')
            tx = bx - 11 if flip else bx + 11
            parts.append(
                f'<a href="{nxt}{E(_q(b["name"]))}">'
                f'<g class="bn"><circle cx="{bx:.1f}" cy="{by:.1f}" r="5.4" class="kc"/>'
                f'<text x="{tx:.1f}" y="{by + 4.2:.1f}" class="bl"'
                f'{" text-anchor=\"end\"" if flip else ""}>'
                f'{E(b["name"])}<tspan class="bl2"> {b["n"]} 作品{"・はじめて" if b["new"] else ""}</tspan></text></g></a>')
        brh.append("".join(parts))
    h = MID_Y + (74 + max_stack * ROW_H + 24 if brh else 62)
    return (f'<div class="thr"><svg viewBox="0 0 {SVG_W:.0f} {h:.0f}" width="100%"'
            f' style="max-width:{SVG_W:.0f}px" role="img" aria-label="'
            f'{E(name)}が関わった公演を、観た日の順に線で結んだ図。結び目 1 つが 1 公演">'
            f'<g class="pull">{"".join(segs)}{"".join(hi)}{"".join(brh)}'
            f'{"".join(labs)}{"".join(knots)}</g></svg></div>')


def _jdate(s: str) -> str:
    """**年から書く。**何年ぶんも混ざる並びで月日だけにすると読めない。"""
    try:
        y, m, d = s.split("-")
        return f"{int(y)}年{int(m)}月{int(d)}日"
    except (ValueError, AttributeError):
        return s or ""


def _q(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s)


# ---------------------------------------------------------------- 画面を組む
def pick_panel(g: dict) -> str:
    """まだ何もつまんでいないときに出す、名前の一覧。

    **全員を垂らす**（起案者の指示・2026-08-26 ──「たどれる人の名前は全部下に
    垂らしてほしい」）。**上位 12 名に絞っていたのを撤回した。** 絞っていたのは
    「まだ何もつまんでいない画面に91名を五十音で並べても、どれを押せばよいか
    分からない」ためだったが、**この一覧はすでに五十音ではなく、意味のある順
    （申告していない名前を先に・線の長い順）に並んでいる。** 並びに意味がある
    以上、途中で切って「残りは探すで」と誘導する理由が無い。

    ## 名前で絞り込む欄を足した（2026-08-26）

    起案者の指摘 ──「ただ85名の名前を羅列するってセンスないんだけど、どう
    並べたらユーザーは見やすいかな」。**役割で束ねる案・出会った年で束ねる案は、
    実データで検討して外した** ── 役割は出演が 64/85（75%）に偏っており、
    年も 2022 年だけで 45/85（53%）を占める。**どちらで区切っても、1 つの
    束に大半が残るだけで見やすくならない。** 起案者と相談し、**探している人が
    だいたい分かっているときに絞り込める検索欄**を選んだ。

    **サーバーには何も送らない。** すでに描いた 85 枚の札を、打った文字で
    その場で出し分けるだけの JS（`app.py` の共有スクリプト、`data-pk-filter`）
    にした ── 名前は全部すでに手元にあるので、探す画面（サーバーに問い合わせる）
    と同じ仕組みにする理由が無い。
    """
    ps = picks(g)
    if not ps:
        return ('<section class="card"><p class="empty">2 つ以上の公演で観た名前が、'
                'まだありません。観た記録が増えると出るようになります。</p></section>')
    rows = "".join(
        f'<li><a href="{HREF}&amp;name={E(_q(p["name"]))}" class="pk">'
        f'<span class="pk-n">{E(p["name"])}</span>'
        f'<span class="pk-r">{E(p["role"])}</span>'
        f'<span class="pk-c">{p["n"]} 作品</span>'
        f'<span class="pk-s">{E(_jdate(p["from"]))} 〜 {E(_jdate(p["to"]))}</span>'
        f'{"<span class=\"pk-d\">お気に入りに登録済み</span>" if p["declared"] else ""}'
        f'</a></li>' for p in ps)
    n_dec = sum(1 for p in ps if p["declared"])
    return f"""<section class="card">
{IC.h2("light", "どの名前をたどりますか",
       f'<span class="badge part">{len(ps)} 名</span>')}
<p class="lead"><b>2 つ以上の公演で観た名前です。</b>お気に入りに登録していない名前を先に、
そのなかで<b>最初に観た日から最後に観た日までが長い順</b>に並べています
（登録済みの {n_dec} 名は、すでにご存じの名前なので後ろにしています）。</p>
<div class="pk-search">{IC.ico("search", 15)}
<input type="text" data-pk-filter="1" placeholder="名前で絞り込む" autocomplete="off"
 aria-label="つまむ相手を名前で絞り込む"></div>
<ol class="picks">{rows}</ol>
<p class="empty pk-none" hidden>その名前は見つかりませんでした。</p></section>"""


def thread_panel(g: dict, name: str, trail: list[str]) -> str:
    """つまんだ 1 本。**結び目には年月日・公演名・劇場を必ず出す。**

    振り返りの図は 1 件 1 件が識別できないと無価値になる。点だけを並べて
    「8 回観ています」で終わらせない。
    """
    rows = g["threads"].get(name)
    if not rows:
        return (f'<section class="card"><p class="empty">'
                f'<b>{E(name)}</b>の記録は、上演日のあるものが 2 件そろっていません。'
                f'この線は 2 件目から引けます。</p></section>')
    brs = branches(g, name)
    # **枝を押したときは、たどってきた道を持ち回る。** 道が消えると「どこから来たか」が
    # 画面から無くなり、3 手の道筋という形が成り立たない
    nxt = (f'{HREF}&amp;via={E(_q(ARROW.join((trail + [name])[-TRAIL_MAX:])))}'
           f'&amp;name=')
    dec = "（お気に入りに登録済みです）" if _nz(name) in declared_names() else ""
    role = "・".join(k for k, _ in g["roles"][name].most_common(3))
    lis = []
    for i, r in enumerate(rows):
        a = CH._anchor(r["key"])
        # **劇場が引けていない記録がある**（63/97）。**器ごと出さない** ── 空のまま組むと
        # 「／」だけが残り、何かが入るはずの場所が壊れているように見える
        ven = (r.get("venues") or [None])[0]
        bs = brs.get(r["key"]) or []
        # **図が枝を出さない結び目（`BRANCH_MAX` の外）の分も、ここには全部出す。**
        # 図が全員を垂らすようになった（2026-08-26）あとも、この文字の並びは
        # 図に出ない結び目の受け皿として要る。打ち切った先がどこにも無い状態を作らない
        links = "、".join(
            f'<a href="{nxt}{E(_q(b["name"]))}">{E(b["name"])}</a>'
            f'（{E(b["role"])}・{b["n"]} 作品{"・この公演がはじめて" if b["new"] else ""}）'
            for b in bs)
        bh = "" if not bs else f'<p class="brl">この公演から移れます ── {links}</p>' 
        lis.append(
            f'<li><span class="no">{i + 1}</span><div>'
            f'<a href="{CH.ROW_HREF}&amp;w={E(a)}#w-{E(a)}" class="ti">{E(r["title"])}</a>'
            f'<p class="me">{E(_jdate(r["date"]))}'
            f'{"　" + E(ven) if ven else ""}</p>{bh}</div></li>')
    return f"""<section class="card">
{IC.h2("light", f"{name} ── {len(rows)} 作品",
       f'<span class="badge part">{_jdate(rows[0]["date"])} 〜 '
       f'{_jdate(rows[-1]["date"])}</span>')}
<p class="lead"><b>{E(role)}</b>として観た公演を、古いほうから順に結んでいます{E(dec)}。
<b>結び目 1 つが 1 公演です。</b>押すと日記帳のその記録に飛びます。
{"下に垂れている名前を押すと、その名前に移ります。"
 "その公演ではじめて観た名前には、その旨を書いています。"
 if brs else "この線からは、次の名前に移れる公演がありませんでした。"}</p>
{_thread_svg(name, rows, brs, nxt)}
<ol class="knots">{"".join(lis)}</ol></section>"""


def trail_html(trail: list[str], name: str) -> str:
    """たどってきた道。**3 手までしか出さない** ── それより先は道筋として読めなくなる。"""
    if not trail:
        return ""
    ks = (trail + [name])[-(TRAIL_MAX + 1):]
    # **戻るときも、その手前までの道を持たせる。** 道を落として戻すと、
    # 押した先で道筋が消える
    parts = " → ".join(
        (f'<b>{E(k)}</b>' if i == len(ks) - 1 else
         f'<a href="{HREF}&amp;via={E(_q(ARROW.join(ks[:i])))}'
         f'&amp;name={E(_q(k))}">{E(k)}</a>') for i, k in enumerate(ks))
    return f'<p class="trail">たどってきた道　{parts}</p>'


def body(rated: list[dict], name: str = "", via: str = "") -> str:
    g = build(rated)
    trail = [t for t in (via or "").split(ARROW) if t.strip()][-TRAIL_MAX:]
    und = ("" if not g["n_undated"] else
           f'<p class="lead"><b>上演日が分からない記録が {g["n_undated"]} 件あります。'
           f'</b>この線には載りません。日記帳の「公演詳細を直す」から日付を入れると'
           f'載るようになります。</p>')
    main = thread_panel(g, name, trail) if name else pick_panel(g)
    back = ("" if not name else
            f'<p class="lead"><a href="{HREF}" class="back">ほかの名前を選ぶ</a></p>')
    return f"{trail_html(trail, name) if name else ''}{main}{und}{back}"


STYLE = """
/* **線は押せないので地の色、結び目は押せるので藍にする。** この画面のためだけに
   色を増やさない ── 藍は「押せる・書ける」ところにしか使わないという既存の線をそのまま
   守る。**線に藍を引くと、線そのものが押せるように見える。** */
.thr{margin:6px 0 2px;overflow-x:auto}
.thr svg{display:block}
.ln{fill:none;stroke:var(--base);stroke-linecap:round}
.ln2{fill:none;stroke:var(--surf);stroke-linecap:round;opacity:.55}
.ln3{fill:none;stroke:var(--ink);stroke-linecap:round;opacity:.13}
.br{fill:none;stroke:var(--base);stroke-width:2.6;stroke-linecap:round;
    stroke-dasharray:1 6}
.kh{fill:var(--surf);stroke:var(--surf);stroke-width:3}
.kc{fill:var(--acc);stroke:var(--surf);stroke-width:1.6}
.kn-n{fill:var(--surf);font-size:10.5px;font-weight:700;text-anchor:middle}
.kn circle.kc,.bn circle.kc{transition:r .12s}
.kn:hover circle.kc,.kn:focus circle.kc{r:10}
.kd{fill:var(--mute);font-size:12px;text-anchor:middle;font-variant-numeric:tabular-nums}
.kd2{font-size:11px}
.bl{fill:var(--ink);font-size:12.5px;font-weight:600}
.bl2{fill:var(--mute);font-weight:400}
.bn:hover .bl,.bn:focus .bl{text-decoration:underline}
/* **名前で絞り込む欄**（起案者の指示・2026-08-26 ──「85名の名前を羅列するって
   センスないんだけど、どう並べたらユーザーは見やすいかな」への答え）。
   `input[type=text]` の見た目は共通規約（`app.py`）に任せ、ここでは並びと
   絵記号の位置だけを決める。 */
.pk-search{display:flex;align-items:center;gap:8px;margin:14px 0 4px;
    color:var(--mute)}
.pk-search input{flex:1 1 auto;max-width:22em}
.pk-none{margin-top:14px}
/* **3 カラムぐらいで並べる**（起案者の指示・2026-08-26 ──「たどるの名前を、
   たどるのページ内で3カラムくらいで表示してほしい」）。80 名を 1 列で並べると
   縦にとても長くなる（全員出すようにしたのは同日の別の指示）。**列数は決め打ちに
   しない** ── `auto-fill` と `minmax` で、1 枚のカードが 230px を切らない範囲で
   並べるだけにする。ページの本文幅（`.wrap`）だと 3 列前後になるが、狭い画面では
   自然に 1〜2 列へ畳まれるので、別に分岐を書く必要が無い。 */
.picks{list-style:none;margin:10px 0 0;padding:0;display:grid;
    grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px 16px}
/* **カード 1 枚の中は横並びから縦並びに変えた。** 名前・役職・作品数・観た期間の
   4 つを横 1 列に収めるには、3 列に割ったカードの幅（230px 前後）が足りない。
   縦に積めば、どの幅でも同じ組み方で読める */
.pk{display:flex;flex-direction:column;gap:2px;padding:9px 12px;
    border:1px solid var(--grid);border-radius:9px;
    text-decoration:none;color:inherit;min-width:0}
.pk:hover,.pk:focus{border-color:var(--acc);background:var(--plane)}
.pk-n{font-weight:700}
.pk-r,.pk-c,.pk-s{color:var(--mute);font-size:.82rem}
.pk-s{font-variant-numeric:tabular-nums}
.pk-d{color:var(--mute);font-size:.78rem}
.knots{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:10px}
.knots li{display:grid;grid-template-columns:2em 1fr;gap:10px;align-items:start}
.knots .no{display:inline-grid;place-items:center;width:1.9em;height:1.9em;border-radius:50%;
    background:var(--acc);color:var(--surf);font-size:.8rem;font-weight:700}
.knots .ti{font-weight:600;color:var(--ink);text-decoration:none}
.knots .ti:hover,.knots .ti:focus{text-decoration:underline}
.knots .me{margin:2px 0 0;color:var(--mute);font-size:.9rem}
.brl{margin:4px 0 0;font-size:.9rem}
/* **移れる名前は押せることが分かる色にする**（`.hit .why` と同じ既定色）。
   何も指定しないと既定の青・下線が出る ── ブラウザの既定は「案A」の色ではない */
.brl a{color:var(--acc);text-decoration:none}
.brl a:hover,.brl a:focus{text-decoration:underline}
.trail{margin:0 0 12px;color:var(--mute)}
.trail a{color:var(--ink2);text-decoration:none}
.trail a:hover,.trail a:focus{color:var(--ink);text-decoration:underline}
.back{color:var(--acc);text-decoration:none}
.back:hover,.back:focus{text-decoration:underline}
/* **動きは 1 度きりで、終わったあとの形だけで読める。** 動きに情報は載せない */
.pull{animation:pullin .34s ease-out both}
@keyframes pullin{from{opacity:0;transform:translateX(22px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.pull{animation:none}}
"""
