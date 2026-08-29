#!/usr/bin/env python3
"""公演カレンダー。**追いかけている公演を、月ごとの暦の上に期間の帯で並べる。**

起案者の指示（2026-08-24）──「興味ありとお気に入りを一括でカレンダーに表示する
『公演カレンダー』のページが独立してあってもいいんじゃない？」。**乗せるものは
「すでに持っている」を加えた 3 種類**（起案者の選択）。

## 一覧で読めなかったことが 2 つある

**① 同じ日に何本もかかっている。** 追いかけているのは 53 件（すでに持っている 5・
興味あり 33・お気に入り 15）で、**9 月はそのうち 18 件、いちばん混む日は 10 本が同時に
上演中**である（2026-08-24 の実測）。日付順の一覧では 1 行ずつに見えるので、
**重なりがどこにあるのかが出ていなかった。**

**② 楽日が固まる。** 8/30 に楽日が 4 件集まっていた。**「この週末を逃すと 4 本消える」**は、
いま一覧の日付を読み比べないと出てこない。**見逃さないことが企画の中心**（企画書
「このシステムがあると何がいいのか」）なので、ここに直接効く。

## なぜ 7 列の暦にしないのか

**公演は 1 日の予定ではない。** 期間は 2〜31 日（中央 10 日）ある。7 列の暦に置くと、
**同じ題名が 10 マスに出る**か、帯にして週をまたがせることになる。帯にしても、
**1 日公演（母集団の 19% ── `run_days` の説明）は 1 マスぶんの幅しかないので題名が入らない。**

**そこで「月 × 日」の帯にした。** 左に題名を置き、右に日を横に並べて期間を帯で引く。

- **題名はどの公演でも必ず読める** ── 帯の幅に関係なく左の列にある
- **その日に何本かかっているかは、縦に目を落とせば数えられる**
- **帯の右端が楽日、つまり締切である**

**土日に影を敷き、土は青・日は赤で刷る。** 7 列の暦をやめると曜日の並びが消えるが、
**観に行けるのはたいてい週末なので、週末がどこかは残さなければならない。**
影だけでは土と日が地続きに見えて、**2 日ぶんの塊としか読めない**（起案者の指示、
2026-08-25）。暦の色の慣習に合わせて分ける。**意匠の 2 本のインクは使わず、曜日専用の
2 色を暦の中だけに持つ** ── 藍を使うと「押せる」、えんじを使うと「識別」と読めてしまう。

## 3 種類の区別は形で付ける

意匠の 2 本のインクにはすでに役がある（藍は「押せる」、えんじは「識別」）ので、
**束の区別を色で運ばない。** 塗り・枠・破線の 3 つの形と、ナビゲーションで使っている
のと同じ絵記号（券・旗・星）で分ける ── **絵記号の意味は画面をまたいで同じにする。**

## 行く日は帯の上に半券の形で置く（2026-08-25）

起案者の指示 ──「『すでに持っている』公演を、帯の中で一点で表示したい。1 作品に対して
複数持っている場合も考えて」。

**券を 1 枚 1 行で持つことにした**（`feedback.ticket`）。押した印（`reaction.owned`）は
1 か 0 しか持てないので、**期間のどこに行くのかを言えなかった。** 1 枚ずつ持てば、
**同じ公演を 2 回観る**（昼夜・初日と楽日）ことも、**同じ作品のツアーを 2 会場で観る**
ことも、数の問題ではなくなる ── 前者は 1 本の帯に札が 2 つ並び、後者はもともと別の
公演なので帯が 2 本ある。**同じ日の同じ回の 2 枚（連れの分）は 1 つの札に畳む** ──
暦に置きたいのは座席の数ではなく、行く回だからである。

**日にちの出どころは 2 つある。** 購入確認メール（上演日と時刻が入っている）と、
本人の入力（窓口・当日券・譲り受けと、メールから起こした行の直し）である。
**どの公演の券か機械が決められなかった分は、黙って捨てずに暦の下に出す** ──
持っている券が暦に出ていないことに気づけないほうが困る。

**メールから読み取った回は、確定前として出す**（起案者の指示 2026-08-25 ──「メールから
取り込んだ候補は『取り消す』より『確定』が押せるほうがうれしい」）。**読み取りは
間違いうる**ので、機械が起こした行をそのまま「行く日」と言い切らない ── 暦では塗らずに
輪郭だけで置き、押し口の側では「確定」を先に出す。**本人が自分で入れた行は初めから
確定である**（入れたこと自体が確定である）。

## 形は券の形にする

**行く日を丸い点で置くのはやめた**（起案者の指摘 2026-08-25 ──「● だとデザインが
ダサい」）。**丸は帯とも暦とも関係の無い形で、どこに属しているのかが読めない。**
帯の上に浮いた印ではなく、**その日のマスを半券の形に抜く** ── 左右にミシン目を
入れた縦長の札で、帯の一部が切り取られているように見せる。**1 日公演では帯と
同じ幅になる**（その帯そのものが行く日である、という意味になって都合がよい）。

## 「その日は空いているか」には、札があっても答えられない

**札が言うのは「この回に行く」だけである。** 札の無い日が空いているとは限らないし、
**行く日を入れていない券は、いままでどおり期間の帯でしか出せない。** 画面にもそう書く
── 予定表として読めるように見せてはいけない。
"""

from __future__ import annotations

import collections
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import icons as IC                                                  # noqa: E402
import recommend2 as RC2                                            # noqa: E402
import render_recommend as RR                                       # noqa: E402

E = RR.E


def _mdays(y: int, m: int) -> int:
    """その月の日数。**標準ライブラリの `calendar` は使えない** ── 同じ `tools/taguri/` に
    `calendar.py`（ステイジーズカレンダーの取り込み）が居るので、`import calendar` は
    そちらを掴む。翌月の 1 日から 1 日引いて数える。
    """
    return (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day

# 束の名前 → 画面に出す言葉・絵記号・帯の形。**並びは「決まっている順」である** ──
# 券がある（確定）→ 興味あり（追いかけている）→ お気に入り（知らせが来ただけ）
#
# **帯の形の名前は、束の名前から取る**（`tracking` → `trk`）。以前は `int` と付けて
# いたが、**この名前は感想の本文（`app.py` の `.int`）がすでに使っており**、そちらは
# `::before` / `::after` で鉤括弧を入れる規則を持っている ── 同じ名前を付けたせいで、
# **暦の「興味あり」の帯が全部「⚑」と鉤括弧付きで出ていた。**
# 意味の違うものに同じ名前を付けない。
KINDS = (("owned", "すでに持っている", "ticket", "own"),
         ("tracking", "興味あり", "flag", "trk"),
         ("favourites", "お気に入り", "star", "fav"))
# **絞り込みの `kind` パラメータを検査する側（`serve.py`）が見る値。** `KINDS` から
# 作るので、束を増やしても書き足す場所が 1 か所で済む
KIND_KEYS = tuple(k for k, *_ in KINDS)
MAX_MONTHS = 12                    # これ以上先は出さない（あふれた分は下に件数で書く）


def rows_of(d: dict, today: dt.date, tickets: dict | None = None) -> list[dict]:
    """暦に置ける行を作る。**楽日を過ぎた公演は出さない**（もう行けない）。

    **同じ作品は基本的に 2 つの束に入らないが、1 つだけ例外がある** ── 「持っている」
    公演がお気に入りの名前にも当たっていると、`app._rebucket` はどちらの束にも
    残す（起案者の指示・2026-08-26 ──「おすすめに出ないようにして（お気に入り
    には出ていてよい）」）。**この暦では同じ会場・同じ日程の行が 2 本に見えて
    しまっていた**（起案者の指摘・2026-08-26 ──「カレンダーには各作品1行だけで
    よい」・実例「お気に入り63」）。同じ stage_id を 2 回置かない ──
    `KINDS` を並べた順（持っている→興味あり→お気に入り）で先に来たほうを残す。

    **これは「同じ stage_id」の重複だけを畳む。** 別会場・別日程のツアー公演
    （実例「ミス・サイゴン」の東京・札幌）は、起案者の判断で今回はそのまま
    別行にした ── 月をまたいで見え方が変わる話で、今回の指摘とは別の話である。

    **持っている券は、上演期間の中の日だけを行に載せる。** 期間の外の日は暦に置く列が
    無いので、**載せると記録はあるのに札が出ない**（画面から見れば消えたのと同じ）。
    """
    out = []
    seen: set = set()
    for key, label, icon, cls in KINDS:
        for c in d.get(key) or []:
            sid = str(c.get("stage_id") or "")
            if sid and sid in seen:
                continue
            s, e = RC2.period_start(c.get("period") or ""), RC2.period_end(c.get("period") or "")
            if not s or not e:
                continue                        # 日付が読めない行は暦に置けない
            start = dt.date.fromisoformat(s)
            if e < today:
                continue
            if sid:
                seen.add(sid)
            tk = [t for t in ((tickets or {}).get(sid) or [])
                  if s <= t.get("date", "") <= e.isoformat()]
            out.append({"sid": sid, "title": c.get("title") or "",
                        "venue": c.get("venue") or "",
                        "pref": c.get("pref") or "", "start": start, "end": e,
                        "days": RC2.run_days(c.get("period") or ""),
                        "period": c.get("period") or "",
                        # **`key` は絞り込みが見る値、`kind` は画面に出す言葉。**
                        # 訳した文字列を突き合わせに使うと、言葉を直したときに
                        # 絞り込みが黙って壊れる
                        "key": key, "kind": label,
                        "icon": icon, "cls": cls, "tickets": tk})
    return out


def _by_day(tk: list[dict]) -> dict[str, list[dict]]:
    """券を日ごとにまとめる。**1 日に 2 回（昼夜）でも札は 1 つ置く** ── 19px の枠に
    札を 2 つ入れると、どちらも判別できない大きさになる。**回数は札の中に数で出す。**
    """
    out: dict[str, list[dict]] = {}
    for t in tk:
        out.setdefault(t["date"], []).append(t)
    return out


def _go_label(tk: list[dict]) -> str:
    """左の列に出す「行く日」。**月日と時刻を書く** ── 札だけでは回が分からない。

    **確定前の回にはそう書く。** 塗りの違いだけで確定の有無を運ぶと、色の濃さを
    見比べないと分からない。
    """
    parts = []
    for day, g in sorted(_by_day(tk).items()):
        d = dt.date.fromisoformat(day)
        tms = "・".join(t["time"] for t in g if t["time"])
        un = "" if any(t.get("confirmed") for t in g) else "（確定前）"
        parts.append(f"{d.month}/{d.day}" + (f" {tms}" if tms else "") + un)
    return "・".join(parts)


# **都道府県の並び順は北から南**（`render_recommend.PREFS` と同じ並び。都道府県の
# 絞り込みの札もこの順で出している）── 新しく順を作ると、暦と絞り込みで県の並びが
# 2 つできる。**分からない県（探して見つけた公演など、値が空のもの）は最後に置く。**
_PREF_RANK = {p: i for i, p in enumerate(RR.PREFS)}


def _place(rows: list[dict], y: int, m: int) -> list[dict]:
    """その月にかかる行だけを、**都道府県ごとにまとめて**返す。

    起案者の指摘（2026-08-25）──「いまカレンダーの縦の並びも都道府県ごっちゃなので、
    都道府県順に並び変えて」。**縦に読むと同じ都道府県の公演が飛び飛びに散っていた**
    ── 「今月、大阪で観られるものは」を知りたいときに、上から下まで全部読む必要が
    あった。

    **県の中は締切の近い順のままにする。** 前はここが並びの決め手（「買うならこの順」）
    だったが、**捨てたのではなく一段下げた** ── 同じ県の中でどれから買うかは、
    依然として締切が答える。
    """
    a, b = dt.date(y, m, 1), dt.date(y, m, _mdays(y, m))
    hit = [r for r in rows if r["start"] <= b and r["end"] >= a]
    return sorted(hit, key=lambda r: (_PREF_RANK.get(r["pref"], len(RR.PREFS)),
                                       r["end"], r["start"], r["title"]))


def _month_block(rows: list[dict], y: int, m: int, today: dt.date) -> str:
    """1 か月ぶんの格子。**すべての要素に行を明示して置く。**

    自動配置には任せられない ── **週末の影を縦に伸ばすと、その列は「埋まっている」ことに
    なり、影を跨ぐ帯が置けずに下の行へ押し出される**（実測。日の見出しも影の列を避けて
    折り返していた）。行を全部書けば、重ねて置くのは格子が許す。
    """
    n = _mdays(y, m)
    a, b = dt.date(y, m, 1), dt.date(y, m, n)
    hit = _place(rows, y, m)
    if not hit:
        return ""
    # 見出しに束ごとの件数を出す。**何を見に来たのかで読む所が変わる**ので、
    # 「18 件」だけでは足りない
    cnt = {label: sum(1 for r in hit if r["kind"] == label) for _, label, _, _ in KINDS}
    tally = "・".join(f"{lb} {cnt[lb]}" for _, lb, _, _ in KINDS if cnt[lb])
    head = (f'<h3>{y} 年 {m} 月 <span class="cnt">{len(hit)} 件'
            f'{f"（{E(tally)}）" if tally else ""}</span></h3>')

    n_rows = 1 + len(hit)                        # 見出し 1 行 ＋ 公演の行
    # 週末の影と今日の線。**影は本文の行だけに敷く**（見出しの行は日の数字が入る）
    stripes = "".join(
        f'<span class="wk {"sun" if dt.date(y, m, i + 1).weekday() == 6 else "sat"}"'
        f' style="grid-column:{i + 2};grid-row:2/-1"></span>'
        for i in range(n) if dt.date(y, m, i + 1).weekday() >= 5)
    now = (f'<span class="now" style="grid-column:{today.day + 1};grid-row:1/-1"></span>'
           if a <= today <= b else "")

    # 日の見出し。**土日はここにも影を付ける**（帯の側の影と縦に繋がって見える）。
    # **土は青、日は赤**（暦の慣習どおり）── 影と同じ色味を数字にも入れる
    hd = ['<span class="hc" style="grid-row:1"></span>']
    for i in range(n):
        day = dt.date(y, m, i + 1)
        w = "日月火水木金土"[(day.weekday() + 1) % 7]
        wk = ("", "", "", "", "", " sat", " sun")[day.weekday()]
        cls = "hd" + wk + (" past" if day < today else "")
        hd.append(f'<span class="{cls}" style="grid-column:{i + 2};grid-row:1">'
                  f'<b>{i + 1}</b><i>{w}</i></span>')

    body = []
    for k, r in enumerate(hit):
        c0 = max(1, (r["start"] - a).days + 1)
        c1 = min(n, (r["end"] - a).days + 1)
        cl = " cl" if r["start"] < a else ""          # 前の月から続いている
        cr = " cr" if r["end"] > b else ""           # 次の月へ続く
        place = f"{r['venue']}" + (f"（{r['pref']}）" if r["pref"] and r["pref"] != "東京都" else "")
        sid = f' data-stage="{E(r["sid"])}"' if r.get("sid") else ""
        # **この月に入る券だけを、左の列にも書く。** 札はその月の格子にしか置けないので、
        # 全部の日を書くと、画面に出ていない札の説明が残る
        here = [t for t in (r.get("tickets") or []) if a <= dt.date.fromisoformat(t["date"]) <= b]
        go = (f'<em class="go">{E(_go_label(here))} に行きます</em>' if here else "")
        body.append(
            f'<span class="nm"{sid} style="grid-row:{k + 2}"><b>{E(r["title"])}</b>'
            f'<i>{RR.period_label(r["period"], r["days"])}'
            f'{"・" + E(place) if place else ""}</i>{go}</span>'
            f'<span class="bar {r["cls"]}{cl}{cr}"{sid}'
            f' style="grid-column:{c0 + 1}/{c1 + 2};grid-row:{k + 2}">'
            f'{IC.ico(r["icon"], 13)}<i class="sr">{E(r["kind"])}</i></span>'
            + _points(here, r, a, k + 2))

    return (f'<div class="mblock">{head}<div class="mscroll">'
            f'<div class="mgrid" data-y="{y}" data-m="{m}" style="--n:{n};'
            f'grid-template-rows:repeat({n_rows},auto)">'
            f'{stripes}{now}{"".join(hd)}{"".join(body)}</div></div></div>')


def _points(tk: list[dict], r: dict, a: dt.date, row: int) -> str:
    """行く日の半券。**帯の上に重ねて置く** ── 帯（期間）と札（回）は別のことを言っている。

    **札は日の列にぴったり置く。** 帯の中の相対位置で置くと、1 日公演と 1 か月公演で
    同じ日が別の場所に出る ── **縦に目を落として同じ日を数える**という、この暦の
    読み方が壊れる。
    """
    out = []
    for day, g in sorted(_by_day(tk).items()):
        d = dt.date.fromisoformat(day)
        col = (d - a).days + 2
        tms = "・".join(t["time"] for t in g if t["time"])
        ok = any(t.get("confirmed") for t in g)
        say = (f'{d.month} 月 {d.day} 日' + (f" {tms}" if tms else "") + " に行きます"
               + ("" if ok else "（購入確認メールから読み取りました。まだ確定していません）"))
        cls = "pt" + ("" if ok else " un") + (" mul" if len(g) > 1 else "")
        out.append(f'<span class="{cls}"'
                   f' data-stage="{E(r.get("sid") or "")}" title="{E(say)}"'
                   f' style="grid-column:{col};grid-row:{row}">'
                   f'{f"<b>{len(g)}</b>" if len(g) > 1 else ""}'
                   f'<i class="sr">{E(r["title"])}・{E(say)}</i></span>')
    return "".join(out)


def filter_html(rows: list[dict], sel_kinds: set[str] | None,
                 sel_prefs: set[str] | None) -> str:
    """束と都道府県で絞り込む。**同時にいくつでも選べる**（都道府県の絞り込みと同じ規約）。

    起案者の指示（2026-08-25）──「公演カレンダーにフィルタリング機能をつけたい」。

    **数はいつも全部から数える。** 選ぶと隠れる束・県も、押せば何件出てくるかを
    知りたい ── 残っている分だけで数えると、外した選択肢が「0 件」に見えて
    選び直せなくなる（`/recommend` の都道府県の絞り込みと同じ判断）。

    **枠は都道府県の絞り込みと同じ `.pbox` を使う。** 同じ「畳んである絞り込み」を
    画面ごとに作り直すと、見た目が少しずつずれていく。
    """
    all_k = {k for k, *_ in KINDS}
    keep_k = sel_kinds if sel_kinds is not None else all_k
    kind_n = {key: sum(1 for r in rows if r["key"] == key) for key, *_ in KINDS}
    kind_chips = "".join(
        f'<label class="pchip{" on" if key in keep_k else ""}">'
        f'<input type="checkbox" name="kind" value="{key}"{" checked" if key in keep_k else ""}>'
        f'{IC.ico(icon, 13)}<span class="pl">{E(label)}</span>'
        f'<span class="pn">{kind_n[key]}</span></label>'
        for key, label, icon, _cls in KINDS)

    keep_p = set(sel_prefs) if sel_prefs is not None else set()
    pref_n = collections.Counter(r["pref"] for r in rows if r["pref"])
    pref_chips = "".join(
        f'<label class="pchip{" on" if p in keep_p else ""}">'
        f'<input type="checkbox" name="pref" value="{E(p)}"{" checked" if p in keep_p else ""}>'
        f'<span class="pl">{E(p)}</span><span class="pn">{pref_n[p]}</span></label>'
        for p in RR.PREFS if pref_n.get(p))

    now_k = ("すべて" if keep_k == all_k else
             "・".join(lb for k, lb, _i, _c in KINDS if k in keep_k) + f"（{len(keep_k)}）")
    now_p = ("すべて" if not keep_p else
             "・".join(p for p in RR.PREFS if p in keep_p) + f"（{len(keep_p)} 県）")
    active = sel_kinds is not None or bool(keep_p)
    return f"""<form class="pfil calfil" method="get" action="/calendar">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<details class="pbox"{" open" if active else ""}>
<summary>{IC.ico("search", 15)}束と都道府県で絞り込む ── 束は<b>{E(now_k)}</b>・場所は<b>{E(now_p)}</b></summary>
<p class="lead">押した束・都道府県だけを、下の暦に出します。<b>いくつでも同時に選べます。</b>
ページの上の「観劇日を追加する」に出す公演は、絞り込みの影響を受けません。</p>
<div class="pchips">{kind_chips}</div>
<div class="pchips">{pref_chips}</div>
<div class="pfoot"><button type="submit">{IC.ico("search")}この条件で絞り込む</button>
<a class="pall" href="/calendar?t=__TAGURI_TOKEN__">すべて表示に戻す</a></div>
</details></form>"""


def panel(d: dict, today: dt.date | None = None, tickets: dict | None = None,
          unplaced: list | None = None, sel_kinds: set[str] | None = None,
          sel_prefs: set[str] | None = None) -> str:
    """画面に出す本体。**凡例を先に置く** ── 形で意味を分けているので、形の説明が要る。"""
    today = today or dt.date.today()
    rows = rows_of(d, today, tickets)
    if not rows:
        return ('<p class="empty">暦に出せる公演がありません。'
                '推薦の画面で「興味あり」を押した公演と、お気に入りに登録した名前で'
                '当たった公演が、ここに並びます。</p>')

    filt = filter_html(rows, sel_kinds, sel_prefs)
    keep_k = sel_kinds if sel_kinds is not None else {k for k, *_ in KINDS}
    # **選択肢の件数（`filt`）はいつも全件（`rows`）から数える。** 絞り込んで隠れた
    # 選択肢も、押せば何件出てくるかを知りたい ── 残っている分だけで数えると、
    # 外した選択肢が「0 件」に見えて選び直せなくなる（`filter_html` と同じ判断）。
    view = [r for r in rows if r["key"] in keep_k
            and (sel_prefs is None or r["pref"] in sel_prefs)]
    if not view:
        return (f'{filt}<p class="empty">選んだ条件に一致する公演がありません。'
                f'<a href="/calendar?t=__TAGURI_TOKEN__">絞り込みを外してください</a>。</p>')

    legend = "".join(
        f'<span class="lg"><span class="bar {cls} sm">{IC.ico(icon, 13)}</span>{E(label)}</span>'
        for _, label, icon, cls in KINDS)
    legend += ('<span class="lg"><span class="bar own sm"><span class="pt"></span></span>'
               '行く日</span>'
               '<span class="lg"><span class="bar own sm"><span class="pt un"></span></span>'
               'メールから読み取った回（確定前）</span>')

    # 出す月。**今月から、いちばん遅い楽日の月まで続けて出す** ── 月送りにすると、
    # 押さない限り先が見えない。見逃しを防ぐ画面で先を隠してはいけない
    last = max(r["end"] for r in view)
    ms: list[tuple[int, int]] = []
    y, m = today.year, today.month
    while (y, m) <= (last.year, last.month) and len(ms) < MAX_MONTHS:
        ms.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    blocks = "".join(_month_block(view, yy, mm, today) for yy, mm in ms)

    over = [r for r in view if (r["start"].year, r["start"].month) > ms[-1]]
    tail = (f'<p class="lead"><b>{len(over)} 件は {MAX_MONTHS} か月より先なので、'
            f'この暦には出していません。</b>「おすすめ ▸ 興味あり／お気に入り」の一覧には'
            f'出ていますので、そちらでご覧ください。</p>' if over else "")

    return (f'{filt}<p class="lead">帯の<b>右端が楽日</b>、つまり締切です。'
            f'縦に目を落とすと、その日に何本かかっているかが数えられます。'
            f'<b>土曜は青、日曜は赤</b>で示してあります。</p>'
            f'<div class="cal-legend">{legend}</div>'
            f'<p class="calnote"><b>券を持っている公演は、行く日を入れると'
            f'その日が半券の形で帯から抜けて見えます。</b>入れていないものは帯だけで'
            f'出しますので、<b>「この期間のどこかに行く」という意味</b>になります。'
            f'印の付いていない日が空いているという意味ではありません。</p>'
            f'{blocks}{tail}{_unplaced_html(unplaced or [])}{JS}')


def ticket_manager_html(unplaced: list | None = None) -> str:
    """暦に出せていない券の知らせと、押し口を動かす `JS` だけを返す。

    起案者の指摘（2026-08-25）──「もうチケットを買っていてこれから観に行く公演に
    ついてまとめられているページがない」。新しく立てた「もう観に行く公演」画面
    （`app.page_tickets`）にも、この道具を置く。

    **行く日を入れる道具そのものは、ここには無い。**（起案者の指示・2026-08-26 ──
    「日程を追加する、があるなら『行く日を入れる』は不要です」）。**ページの上に
    置いた「観劇日を追加する」ボタン（`add_ticket_button_html`）に一本化した** ──
    2 つの入口を持たせると、片方だけ直したときにもう片方が古い形のまま残る。

    **`panel()` を呼ばない。** `panel()` は月の格子まで組むので、格子を持たない画面
    から呼ぶと使わないものまで計算して捨てることになる。`d`／`today`／`tickets` は
    もう使わないので受け取らない ── 呼ぶ側（`app.page_tickets`）は `unplaced`
    （暦に出せていない券）だけを渡す。
    """
    return f'{_unplaced_html(unplaced or [])}{JS}'


def _unplaced_html(left: list[dict]) -> str:
    """**購入確認メールにあるのに、どの公演の券か決められなかった分。**

    黙って捨てない ── 持っている券が暦に出ていないことに、本人は気づけない。
    **どうすれば出せるかまで書く**（その公演を手元に加えるか、行く日を自分で入れる）。
    """
    if not left:
        return ""
    li = "".join(f'<li><b>{E(b["title"])}</b> ── {E(b["date"])}'
                 f'{" " + E(b["time"]) if b.get("time") else ""}</li>' for b in left)
    return (f'<div class="tknot"><h3>暦に出せていない券が {len(left)} 件あります</h3>'
            f'<p class="lead">購入確認メールから読み取りましたが、'
            f'<b>手元の公演一覧に同じ公演が見当たりません</b>ので、暦には出せていません。'
            f'「探す」で題名を引いて「興味あり」を押すと手元に加わり、'
            f'ページの上の「観劇日を追加する」に出てきます。</p><ul>{li}</ul></div>')


def _ticket_li(t: dict, loc: str = "") -> str:
    """入れる口に出す 1 枚。**確定前は「確定」を先に出す**（起案者の指示 2026-08-25）。

    **読み取ったものを、取り消す形でしか触れないのは向きが逆である** ── 合っている
    ほうが多いのだから、押す回数の少ないほうを「合っている」に当てる。**違うときの
    口も残す**（読み取りは間違いうる）が、後ろに置く。

    **`loc` は、複数の会場をまとめた行でだけ渡す。** 1 会場しか無い行では、
    どの会場の券かを毎回書くと同じ言葉が繰り返されるだけになる。

    **押し口に会場の stage_id を持たせる。** 会場をまとめた行では、1 つの入れる口の
    下に別々の会場の券が並ぶ ── 確定・取り消しは**その券が実際にどの会場に付いたか**
    に効かなければならない。行全体の代表会場（`data-stage`）に頼ると、他の会場の
    券まで代表会場のものとして操作してしまう。
    """
    when = (f'{t["date"]}'
            + (f' {t["time"]}' if t["time"] else "（時刻を入れていません）"))
    ok = bool(t.get("confirmed"))
    src = "" if ok else "<i>購入確認メールから</i>"
    sid = E(str(t.get("sid") or ""))
    lb = f'<b class="tkloc">{E(loc)}</b> ' if loc else ""
    btn = (f'<button data-del="1" data-stage="{sid}" data-date="{E(t["date"])}"'
           f' data-time="{E(t["time"])}">取り消す</button>')
    if not ok:
        btn = (f'<button class="go-ok" data-ok="1" data-stage="{sid}"'
               f' data-date="{E(t["date"])}" data-time="{E(t["time"])}">確定</button>'
               f'<button data-del="1" data-stage="{sid}" data-date="{E(t["date"])}"'
               f' data-time="{E(t["time"])}">違う</button>')
    return f'<li class="{"" if ok else "un"}">{lb}<span>{E(when)}{src}</span>{btn}</li>'


def _own_merged(rows: list[dict]) -> list[dict]:
    """券を持っている（または券がある）対象を、**作品ごとに 1 つへまとめる。**

    起案者の指示（2026-08-26）──「行く日は公演の地方ごとにわけるのではなく、
    各作品に対して入力欄は１個で、地方の日程は各作品に対してまとめて羅列して」。

    **なぜ会場ごとに分かれていたか。** 「すでに持っている」はこれまで会場
    （stage_id）ごとに別の反応として記録されていたので、同じ作品を 2 都市で
    追いかけていると、暦の「行く日を入れる」にも別々の行として並んでいた。
    2026-08-26 に反応を作品単位へ広げる直しをした（`serve.Server._siblings`）ので、
    以後はどの会場を押しても揃って `owned` になるが、**それより前に別々に付いた
    反応はそのまま残っている**ので、読む側でもここで畳む必要がある。

    **畳む鍵は `RC2.work_key`。** 推薦がツアーの他会場を畳むのと同じ規則を使う ──
    別の畳み方を作ると、画面によって「同じ作品」の境目が変わる。
    """
    own = [r for r in rows if r["cls"] == "own" or r["tickets"]]
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for r in own:
        k = RC2.work_key(r["title"], r["sid"])
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(r)
    out = []
    for k in order:
        g = sorted(groups[k], key=lambda r: r["start"])
        merged = dict(g[0])
        merged["venues"] = g
        merged["tickets"] = [dict(t, sid=r["sid"]) for r in g for t in r["tickets"]]
        merged["start"] = min(r["start"] for r in g)
        merged["end"] = max(r["end"] for r in g)
        merged["merged"] = len(g) > 1
        out.append(merged)
    return out


def add_ticket_button_html(d: dict, today: dt.date | None = None,
                            tickets: dict | None = None) -> str:
    """ページの上に置く「観劇日を追加する」ボタンと、押すと開くポップアップ。

    起案者の指示（2026-08-26）──「日程を追加する、があるなら『行く日を入れる』は
    不要です。あと名前を『観劇日を追加する』にして」。**「行く日を入れる」は
    廃止し、この入口 1 つにまとめた** ── 2 つの入口を持たせると、片方だけ直した
    ときにもう片方が古い形のまま残る。

    **公演を選ぶと、その公演の地方ごとの日程と、すでに入れてある券を出す**
    （起案者の指示 ──「『公演』を選んだら各地方日程の日付が表示されるように
    なっていて、次の『行く日』入力を支援するように。現在の『行く日を入れる』で
    表示されているような情報」）。**廃止した「行く日を入れる」の中身を、選んだ
    1 件ぶんだけポップアップの中に出す形に移した** ── 47 件ぶん全部を並べて
    畳んでおくのと、選んだ 1 件だけを出すのとでは、後者のほうが「これから入れる
    日」に近い情報しか目に入らない。

    **全会場ぶんを、選択肢ごとに隠して埋め込んでおく。** 選ぶたびに読みに行く
    先が無い（画面から外部・API を叩かない）ので、`<select>` の変更に合わせて
    JS が表示を切り替えるだけで足りる（`tkdSync`）。

    **`<dialog>` を使う。** 外部のライブラリを読み込まずにポップアップを組める
    （企画書 5 章「外部の URL を読み込まない」を破らない）。
    """
    today = today or dt.date.today()
    own = _own_merged(rows_of(d, today, tickets))
    if not own:
        return ""
    opts, infos = [], []
    for r in own:
        tag = f"（{len(r['venues'])} 会場）" if r.get("merged") else ""
        opts.append(f'<option value="{E(r["sid"])}" data-lo="{r["start"].isoformat()}"'
                    f' data-hi="{r["end"].isoformat()}">{E(r["title"])}{tag}</option>')
        merged = r.get("merged")
        # **地方ごとの日程。** `.tourfull`／`.tf-row` は推薦の一覧のツアー全日程と
        # 同じ部品 ── 同じ「地方＋期間」を、画面をまたいで同じ形で出す。1 会場しか
        # 無い公演では、選択肢と入力欄の min/max がすでに期間を言っているので出さない
        sched = ""
        if merged:
            srows = "".join(
                f'<div class="tf-row{" done" if v["end"] < today else ""}">'
                f'<span class="tf-loc">{E(RR.region_label(v["pref"], v["venue"] or "会場未定"))}'
                f'公演</span><span class="tf-when">{E(RR.short_period(v["period"]))}</span>'
                f'</div>' for v in r["venues"])
            sched = f'<div class="tourfull">{srows}</div>'
        # **すでに入れてある券。** 廃止した「行く日を入れる」がここに出していた
        # 一覧と同じ ── 確定・取り消しの押し口も、券自身の会場（`t["sid"]`）を
        # 持たせたまま出す
        li = "".join(
            _ticket_li(t, RR.region_label(
                next((v["pref"] for v in r["venues"] if v["sid"] == t["sid"]), ""))
                if merged else "")
            for t in r["tickets"])
        have = f'<p class="tkihave">入れてある日</p><ul class="tklist">{li}</ul>' if li else ""
        infos.append(f'<div class="tkinfo" data-for="{E(r["sid"])}" hidden>'
                     f'{sched}{have}</div>')
    return f"""<button type="button" class="addtk" data-open-dialog="tkdlg">
{IC.ico("plus", 16)}観劇日を追加する</button>
<dialog id="tkdlg" class="tkdlg">
<form method="dialog" class="tkdform">
<h3>{IC.ico("clock", 16)}観劇日を追加する</h3>
<label>公演<select class="tkd-work">{"".join(opts)}</select></label>
<div class="tkinfos">{"".join(infos)}</div>
<label>行く日<input type="date" class="tkd-date"></label>
<label>時刻（任意）<input type="time" class="tkd-time"></label>
<div class="tkdfoot"><span class="said"></span>
<button type="button" data-dlg-close="1">閉じる</button>
<button type="button" data-dlg-add="1">この回に行く</button></div>
</form></dialog>"""


# **狭い画面では、今日より先が横にあふれる。** 幅が足りているときは 31 日ぶんが収まる
# ので何も起きないが、あふれたときに 1 日から見せると、**いちばん見たい「これから」が
# 画面の外にある。** 今日の線が入っている月だけ、その位置まで横に送っておく。
JS = """<script>
document.querySelectorAll(".mscroll .now").forEach(n => {
  const s = n.closest(".mscroll");
  s.scrollLeft = Math.max(0, n.offsetLeft - s.clientWidth * 0.35);
});

// ---- 「観劇日を追加する」ポップアップ ---------------------------------------
// 起案者の指示（2026-08-26）──「日程を追加する、があるなら『行く日を入れる』は
// 不要です。あと名前を『観劇日を追加する』にして」。**行く日を入れる口はここ
// 1 つにまとめた** ── 券を足す・確定する・取り消すのすべてがこのポップアップの
// 中で完結する。**外部のライブラリは使わない**（`<dialog>` は素の HTML で
// 開閉できる）。

// **選んだ公演に合わせて、日付の範囲と「地方の日程／入れてある日」を切り替える。**
// 起案者の指示 ──「『公演』を選んだら各地方日程の日付が表示されるようになって
// いて、次の『行く日』入力を支援するように」。中身は `add_ticket_button_html` が
// 選択肢ごとに埋め込み済みなので、ここでは表示・非表示を切り替えるだけでよい
// （画面から外部・API を叩かない）。
function tkdSync(dlg) {
  const sel = dlg.querySelector(".tkd-work"), d = dlg.querySelector(".tkd-date");
  const opt = sel && sel.selectedOptions[0];
  if (opt) { d.min = opt.dataset.lo; d.max = opt.dataset.hi; }
  dlg.querySelectorAll(".tkinfo").forEach(e => {
    e.hidden = !sel || e.dataset.for !== sel.value;
  });
}
document.addEventListener("click", ev => {
  const open = ev.target.closest && ev.target.closest("[data-open-dialog]");
  if (open) {
    const dlg = document.getElementById(open.dataset.openDialog);
    if (dlg) { tkdSync(dlg); dlg.showModal(); }
    return;
  }
  const close = ev.target.closest && ev.target.closest("[data-dlg-close]");
  if (close) { close.closest("dialog").close(); return; }
  const add = ev.target.closest && ev.target.closest("[data-dlg-add]");
  if (add) {
    const dlg = add.closest("dialog"), sel = dlg.querySelector(".tkd-work");
    const dd = dlg.querySelector(".tkd-date").value, tt = dlg.querySelector(".tkd-time").value;
    const said = dlg.querySelector(".said");
    if (!dd) { said.textContent = "行く日を入れてください"; return; }
    post("/api/ticket", {stage_id: sel.value, date: dd, time: tt}, dlg, "記録しました")
      .then(r => { if (r) setTimeout(() => location.reload(), 500); });
    return;
  }
  // **すでに入れてある券の「確定」「取り消し」。** ポップアップの中の一覧
  // （`.tkinfo .tklist`）にだけ出る。**押した券自身の会場（`data-stage`）を使う**
  // ── 1 つの公演が複数の会場をまとめて持つことがあるので、選んでいる公演の
  // 代表会場に頼ると、他の会場の券まで代表会場のものとして操作してしまう
  const b = ev.target.closest && ev.target.closest(".tkinfo .tklist button");
  if (!b) return;
  const dlg = b.closest("dialog");
  const body = {stage_id: b.dataset.stage, date: b.dataset.date, time: b.dataset.time,
                action: b.dataset.ok ? "confirm" : "del"};
  const said = {del: "取り消しました", confirm: "確定しました"}[body.action];
  post("/api/ticket", body, dlg, said).then(r => {
    if (r) setTimeout(() => location.reload(), 500);
  });
});
document.addEventListener("change", ev => {
  const sel = ev.target.closest && ev.target.closest(".tkd-work");
  if (sel) tkdSync(sel.closest("dialog"));
});
</script>"""


STYLE = """
/* ---- 公演カレンダー ── 月 × 日の帯 ---------------------------------------
   **左の題名は必ず読める幅を持つ。** 帯の幅は期間で決まるので、1 日公演では
   題名が入らない ── 題名を帯の中に置かない理由がこれである。                 */
.cal-legend{display:flex;flex-wrap:wrap;gap:16px;margin:0 0 12px;font-size:12.5px;
 color:var(--ink2)}
.cal-legend .lg{display:inline-flex;align-items:center;gap:7px}
.cal-legend .bar.sm{width:34px;height:17px;padding:0}
.mblock{margin:0 0 26px}
.mblock h3{font-size:15.5px;margin:0 0 7px;display:flex;align-items:baseline;gap:10px}
.mblock h3 .cnt{font-size:12px;font-weight:400;color:var(--mute)}
/* **横にあふれたら、この枠の中だけで動かす。** 本文ごと横に動くのは避ける */
.mscroll{overflow-x:auto;padding-bottom:4px}
.mgrid{display:grid;grid-template-columns:230px repeat(var(--n),minmax(19px,1fr));
 align-items:center;row-gap:3px;position:relative;min-width:700px;
 border-top:1px solid var(--grid)}
/* **影と今日の線は、行いっぱいに伸ばす。** 格子は `align-items:center` なので、
   中身を持たないこの 2 つは指定しないと高さ 0 になり、**敷いたつもりで何も出ない**
   （実測 ── 見出しの行だけ影が出て、本文には出ていなかった）。 */
/* **土は青、日は赤。** 暦でいちばん強い慣習なので、これを外すと曜日を数え直すことに
   なる。**意匠の 2 本のインク（藍＝押せる・えんじ＝識別）は使わない** ── 暦の色に
   使うと「押せるのか」「識別なのか」をまた確かめることになる。**この 2 色は曜日
   専用に別に持ち、暦の外では使わない。** 影は薄く、数字ははっきり出す。          */
.mgrid{--sat:#2f6fb0;--sun:#b8434e}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])) .mgrid{
 --sat:#7fb0e8;--sun:#dd7f88}}
:root[data-theme=dark] .mgrid{--sat:#7fb0e8;--sun:#dd7f88}
.mgrid .wk{z-index:0;align-self:stretch}
.mgrid .wk.sat{background:color-mix(in srgb,var(--sat) 9%,transparent)}
.mgrid .wk.sun{background:color-mix(in srgb,var(--sun) 9%,transparent)}
.mgrid .now{border-left:2px solid var(--curtain);z-index:2;pointer-events:none;
 align-self:stretch}
.mgrid .hc{grid-column:1}
.mgrid .hd{position:relative;z-index:1;text-align:center;line-height:1.15;
 padding:5px 0 6px;font-size:10px;color:var(--ink2)}
.mgrid .hd b{display:block;font-size:11.5px;font-weight:600}
.mgrid .hd i{font-style:normal;font-size:9px;color:var(--mute)}
.mgrid .hd.past{opacity:.42}
.mgrid .hd.sat{background:color-mix(in srgb,var(--sat) 9%,transparent)}
.mgrid .hd.sun{background:color-mix(in srgb,var(--sun) 9%,transparent)}
.mgrid .hd.sat b,.mgrid .hd.sat i{color:var(--sat)}
.mgrid .hd.sun b,.mgrid .hd.sun i{color:var(--sun)}
/* 行く日の半券。**帯の上に重ねる。** 帯は期間、札は回で、言っていることが違う。
   **丸い点はやめた**（起案者の指摘 ──「● だとデザインがダサい」）── 丸は帯とも
   暦とも関係の無い形で、どこに属しているのかが読めない。**その日のマスをそのまま
   半券の形に抜く**ので、日の列とも帯とも辻褄が合う。左右のミシン目は紙の色で入れる。 */
.pt{height:21px;border-radius:3px;background:var(--ink);color:var(--surf);
 border-left:2px dotted var(--surf);border-right:2px dotted var(--surf);
 display:flex;align-items:center;justify-content:center;z-index:3;position:relative}
.pt b{font-size:9.5px;font-weight:700;line-height:1;font-style:normal}
/* 確定前（購入確認メールから読み取ったまま）は塗らない。**読み取りは間違いうる**ので、
   確定した回と同じ濃さで置くと、確かめていないものを確かめたように見せることになる */
.pt.un{background:color-mix(in srgb,var(--ink) 17%,transparent);color:var(--ink);
 border:1px dashed color-mix(in srgb,var(--ink) 62%,transparent)}
/* 凡例では帯の見本の中に置く ── 単独の札だけ見せても、どこに出るのか分からない */
.cal-legend .bar.sm{justify-content:center}
.cal-legend .pt{height:15px;width:12px;flex:none}
.mgrid .nm{grid-column:1;position:relative;z-index:1;padding:1px 12px 1px 0;min-width:0}
/* 行く日は題名の下に書く。**札だけでは回（昼夜）が分からない。**
   頭の印は帯の中の札と同じ形にする ── 同じことを指すものは同じ形で出す */
.mgrid .nm .go{display:block;font-style:normal;font-size:10.5px;font-weight:600;
 color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mgrid .nm .go::before{content:"";display:inline-block;width:6px;height:11px;
 border-radius:2px;background:var(--ink);margin-right:6px;vertical-align:-1px;
 border-left:1px dotted var(--surf);border-right:1px dotted var(--surf)}
.mgrid .nm b{display:block;font-size:13px;font-weight:600;line-height:1.35;
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mgrid .nm i{display:block;font-style:normal;font-size:10.5px;color:var(--mute);
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 帯。**塗り・枠・破線の 3 つの形で束を分ける**（色では分けない）。
   **お気に入りだけ例外で色も持つ**（起案者の指示・2026-08-26 ──「サイトで統一して
   お気に入りにはこのテーマに合う黄色をつけて」）。形の違いは残したまま、封蝋と
   同じ `--wax` を差し込む ── 色を増やすのはこの束だけで、持っている・興味ありは
   形だけで見分ける決まりのままにする。 */
/* **箱の性質は帯そのものに持たせる。** `.mgrid .bar` に書いていたため、格子の外に
   ある凡例の見本には効かず、**絵記号が箱の下にはみ出していた**（実測）。 */
.bar{height:21px;border-radius:5px;display:flex;align-items:center;padding:0 4px;
 overflow:hidden;color:var(--ink2)}
.mgrid .bar{position:relative;z-index:1}
/* **束の名前は帯に書かない。** 凡例と形で分かるので、53 本すべてに同じ語を刷ると
   読む量だけが増える。**読み上げには残す**（絵記号は読み上げから外してある）。 */
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);
 white-space:nowrap}
.bar.own{background:color-mix(in srgb,var(--ink) 16%,transparent);
 border:1px solid color-mix(in srgb,var(--ink) 42%,transparent);color:var(--ink)}
.bar.trk{background:var(--surf);border:1px solid var(--base)}
.bar.fav{background:color-mix(in srgb,var(--wax) 12%,transparent);
 border:1px dashed var(--wax);color:var(--wax)}
/* 月をまたぐ帯は、その端の丸みを落とす（切れていることが分かるように） */
.mgrid .bar.cl{border-top-left-radius:0;border-bottom-left-radius:0;border-left-style:dotted}
.mgrid .bar.cr{border-top-right-radius:0;border-bottom-right-radius:0;border-right-style:dotted}
/* **`.note` を上書きしない。** 同じ名前が `render_recommend.py` と `charts.py` に
   あり、この画面の都合で共有の見た目を変えることになる。 */
/* `ch`→`em`（render_recommend.py の `.lead` と同じ理由） */
.calnote{font-size:12.5px;color:var(--ink2);border-left:2px solid var(--base);
 padding:2px 0 2px 11px;margin:0 0 20px;max-width:70em}
/* ---- すでに入れてある券の一覧（ポップアップの中） --------------------------
   **「行く日を入れる」は廃止した**（起案者の指示・2026-08-26 ──「日程を追加する、
   があるなら『行く日を入れる』は不要です」）。以前は暦と同じ画面に常に出す枠
   だったが、いまは「観劇日を追加する」ポップアップの中で、選んだ公演の分だけ
   出す（`.tkinfo`）。ここに残っているのは、その一覧の行そのものの見た目である。 */
.tklist{list-style:none;margin:7px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:7px}
.tklist li{display:inline-flex;align-items:center;gap:7px;font-size:12px;
 border:1px solid var(--base);border-radius:999px;padding:3px 5px 3px 12px}
/* 確定前は破線で出す ── 暦の側の札と同じ約束（確かめていないものは塗らない） */
.tklist li.un{border-style:dashed}
.tklist li i{font-style:normal;font-size:10.5px;color:var(--mute);margin-left:7px}
/* **まとめた行では、券がどの会場のものかを頭に付ける。** 1 会場しか無い行では
   付けない（`_ticket_li` の `loc`） */
.tklist li .tkloc{font-size:10.5px;color:var(--ink2);font-weight:600}
.tklist button{font:inherit;font-size:11px;color:var(--ink2);background:none;
 border:0;cursor:pointer;padding:3px 8px;border-radius:999px}
.tklist button:hover{background:var(--plane);color:var(--ink)}
/* **「確定」を先に、濃く出す。** 読み取ったものは合っていることのほうが多いので、
   押す回数の少ないほうを「合っている」に当てる（起案者の指示 2026-08-25） */
.tklist button.go-ok{background:var(--ink);color:var(--surf);font-weight:600}
.tklist button.go-ok:hover{background:var(--acc);color:var(--surf)}
.tknot{border-left:2px solid var(--curtain);padding:2px 0 2px 12px;margin:22px 0 0}
.tknot h3{font-size:14px;margin:0 0 4px}
.tknot ul{margin:6px 0 0;padding-left:18px;font-size:12.5px}
@media(max-width:700px){.mgrid{grid-template-columns:150px repeat(var(--n),minmax(15px,1fr))}}

/* ---- 「観劇日を追加する」ボタンとポップアップ ----------------------------------
   起案者の指示（2026-08-26）──「日程を追加する、があるなら『行く日を入れる』は
   不要です。あと名前を『観劇日を追加する』にして」。**行く日を入れる口はここ
   1 つにまとめた**ので、押し口は目立たせる（藍地に白文字 ── このアプリで
   「押せる」の既定）。                                                        */
.addtk{font:inherit;font-size:13.5px;font-weight:600;padding:9px 18px;
 border-radius:99px;border:1px solid var(--acc);background:var(--acc);
 color:var(--surf);cursor:pointer;display:inline-flex;align-items:center;gap:7px;
 margin:0 0 18px}
.addtk:hover{opacity:.9}
/* **`<dialog>` は既定の見た目を消し、他の道具と同じ紙の色・枠に合わせる。** */
.tkdlg{border:1px solid var(--ring);border-radius:14px;padding:0;
 background:var(--surf);color:var(--ink);max-width:380px;width:92vw}
.tkdlg::backdrop{background:rgba(0,0,0,.42)}
.tkdform{padding:20px 22px 18px;display:flex;flex-direction:column;gap:12px}
.tkdform h3{margin:0;font-size:15.5px;display:flex;align-items:center;gap:8px}
.tkdform label{display:flex;flex-direction:column;gap:4px;font-size:12px;
 color:var(--ink2)}
.tkdform select,.tkdform input{font:inherit;font-size:13px;padding:7px 9px;
 border:1px solid var(--base);border-radius:7px;background:var(--plane);
 color:var(--ink)}
/* **選んだ公演の地方の日程・すでに入れてある日。**（起案者の指示・2026-08-26 ──
   「『公演』を選んだら各地方日程の日付が表示されるようになっていて、次の
   『行く日』入力を支援するように」）。地に薄い色を敷き、入力欄と読む欄の境目を
   はっきりさせる ── 全部が同じ地だと、どこまでが「選んだ結果」なのか読みにくい */
.tkinfos{margin:-4px 0 0}
.tkinfo{background:var(--plane);border-radius:8px;padding:10px 12px;
 font-size:12.5px}
.tkinfo .tourfull{margin:0}
.tkinfo .tkihave{margin:8px 0 4px;font-size:11px;color:var(--mute);font-weight:600}
.tkinfo:has(.tourfull)>.tkihave{margin-top:10px}
.tkdfoot{display:flex;align-items:center;gap:10px;margin:4px 0 0}
.tkdfoot .said{flex:1;font-size:11.5px;color:var(--mute)}
.tkdfoot button{font:inherit;font-size:12.5px;padding:7px 14px;border-radius:7px;
 cursor:pointer;border:1px solid var(--ring);background:var(--plane);color:var(--ink)}
.tkdfoot button[data-dlg-add]{border-color:var(--acc);background:var(--acc);
 color:var(--surf)}
"""
