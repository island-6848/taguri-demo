#!/usr/bin/env python3
"""おすすめ ▸ **開幕リマインド。** 独立した画面（`/recommend/reminder`）。

起案者の指示（2026-08-25）── 「見逃し」を防ぐのがこの仕組みの中心機能なのに、しばらく
開かないと、前回からの分をさかのぼって読まないと気づけない。

## 対象を、もう 1 度取り違えていた

**1 回目** ── 「興味あり」「お気に入り」に登録した公演だけを対象にしていた。**訂正**
（2026-08-25）── 「興味あり」を押した公演はすでに答えている（見逃してはいない）。
見逃しが起きるのは、候補として挙がったのに答えていない公演のほうである。

**2 回目**（今回）── そこで「候補（`ranked`）＋興味あり＋お気に入り」に直したが、
起案者はさらに訂正した ──

> 一個誤解があるんだけど、ここに表示してほしいのは今週開幕予定の全公演。候補と興味ありと
> 手持ちだけじゃなくて、全部出してほしい。

**`ranked` は「好みに合いそうと判断できた」候補だけである。** `recommend2.json` の
`n_cand`（実測 1300 件）のうち、taste に合わなかった大半（1300 − 250 件ほど）は
`ranked` にも `others` にも載らない ── **スコアの外側にいる公演は、見逃しの対象からも
外れていた。** 見逃しに taste の合う／合わないは関係が無い。**今週開幕する公演は、
好みに関係なく全部出す。**

## 対象の作り方

`data/review/candidates.jsonl`（CoRich から集めた候補）に、`favourites.jsonl`
（お気に入りの名前で直接引いた分）・`calendar.jsonl`（ステイジーズカレンダーから足した分）・
`picked.jsonl`（探して拾った分）を stage_id で重複を除いて足す ── **`recommend2.py` が
候補を組むときと同じ 4 ファイル・同じ順番である**（`recommend2.py` の `main()` 参照）。
好みで絞り込む前の、この仕組みが知っている公演の全部である。

**そこに、いまの反応を重ねる。** 「すでに持っている」「興味あり」「お気に入り」
「興味なし」のどれかに当たれば印を付け、当たらなければ「未回答」にする。**印は捨てる
理由ではない** ── 興味なしも持っているも消さずに出す。全部出すとはそういう意味である。

## 7 日以内に約 160 件ある ── 日付ごとに束ねる

実測（2026-08-26）── 1300 件のうち 7 日以内に開幕するのは 159 件、1 日あたり 5〜44 件。
**平らな 1 本の一覧では多すぎる**ので、初日の日付で見出しを立てて束ねる。

## その場で答えられるようにした（起案者の指示 ①、範囲は 2026-08-26 に訂正）

**答える機能が無い一覧は、見逃し防止の役に立たない。** 「未回答」の行に三択
（`RR.buttons`）を置き、押すとその場で答えが付く（既存の `/api/react` とグローバルな
押し口をそのまま使う ── 専用の JS は書いていない）。

**最初は「興味あり」にも三択を置いていたが、外した**（起案者の指摘 ──「すでに興味あり
とか評価してる公演には『興味あり』などのボタンを表示しないでください」）。この画面の
役目は「まだ何も答えていない公演」に答えさせることで、**すでに「興味あり」と答えた公演は、
この画面の意味では決着している**（見逃しのリスクが無い ── まだ券を取っていないだけ
である）。決着した行にまだボタンを見せると、まだ何かすべきことが残っているように誤って
読める。「お気に入り」は既存の約束で三択を置かない（読むだけの知らせ）。「興味なし」
「持っている」も決着済みなので置かない ── ボタンが付くのは「未回答」だけである。

## ポスターを添えた（起案者の指示 ②）

`DG.POSTER`（`app._poster` を差し込む）で、手元に取り込んだポスターがあれば出す。
無ければ何も出さない ── 枠だけ置かない、既存の約束と同じ。

## 「本日」「明日」だけ太く大きくした（起案者の指示 ④）

新しい色は増やさない（意匠は藍とえんじの 2 本のインクだけ）。太さと大きさだけで
急ぎ度を出す。
"""

from __future__ import annotations

import collections
import datetime
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
for _p in ("review",):
    _s = str(ROOT / "tools" / _p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
import icons as IC                                                   # noqa: E402
import prefmap as PM                                                   # noqa: E402
import recommend2 as RC2                                              # noqa: E402
import render_recommend as RR                                         # noqa: E402

E = lambda s: html.escape(str(s))                                    # noqa: E731

OPEN_WINDOW_DAYS = 7   # 今日を含めて何日先までを対象にするか
TICKET_MAX = 6         # 直近予定（券だけ）に出す上限（あふれた分は件数で書く）

WEEK = "月火水木金土日"

DATA = ROOT / "data" / "review"
CAND, FAV, CALENDAR, PICKED = (DATA / n for n in
                               ("candidates.jsonl", "favourites.jsonl",
                                "calendar.jsonl", "picked.jsonl"))

# **形の区別は `stage_calendar.py` と同じ約束を使う**（藍＝押せる・えんじ＝識別の 2 本の
# インクはここでは運ばない。塗り・枠・破線の形と絵記号で区別する）。並び順は
# 「まだ何もしていない → 気にしている → 決めた」の順にする。
KIND = {
    "unanswered": ("未回答", "inbox", "und"),
    "tracking": ("興味あり", "flag", "trk"),
    "favourites": ("お気に入り", "star", "fav"),
    "declined": ("興味なし", "tag", "dec"),
    "owned": ("持っている", "ticket", "own"),
}
# **三択を置くのは「未回答」だけ。**（起案者の指摘・2026-08-26 ──「すでに興味ありとか
# 評価してる公演には『興味あり』などのボタンを表示しないでください」）
#
# **最初は「興味あり」にも三択を置いていた。** `/recommend/interest` はそこで
# 「持っている」「興味なし」へ進める三択を置いているので、同じ考え方を流用したが、
# **この画面の役目とは合わなかった。** 開幕リマインドが答えさせたいのは「まだ何も
# 答えていない公演」であり、**すでに「興味あり」と答えた公演は、この画面の意味では
# もう決着している**（見逃しのリスクが無い ── まだ券を取っていないだけである）。
# 決着した行にまだボタンを見せると、「これはまだ何かすべきことがある」と誤って読める。
#
# 「お気に入り」は既存の約束（`/recommend/favourites` は読むだけの知らせ）で三択を
# 置かない。「興味なし」「持っている」もすでに決着している。
NEEDS_BUTTONS = {"unanswered"}

# **同じ作品を会場ごとに 1 行へまとめるとき、決着の強いほうを残す並び。**
# `_status_map` が重ねる順（持っている＞興味あり＞お気に入り＞興味なし＞未回答）と同じ
# 強さで、数字が大きいほど決着している。片方の会場だけ答えていれば、その答えを出す。
_STATUS_RANK = {"unanswered": 0, "declined": 1, "favourites": 2, "tracking": 3, "owned": 4}


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]


def all_candidates() -> list[dict]:
    """この仕組みが知っている、これから観られる公演の全部。**好みでは絞らない。**

    `recommend2.py` が候補を組むときと同じ 4 ファイル・同じ順番で重複を除く
    （先に読んだファイルの行を残す）。
    """
    cands = _jsonl(CAND)
    seen = {str(c.get("stage_id") or "") for c in cands}
    for src in (FAV, CALENDAR, PICKED):
        extra = [c for c in _jsonl(src) if str(c.get("stage_id") or "") not in seen]
        seen |= {str(c.get("stage_id") or "") for c in extra}
        cands += extra
    return cands


def _status_map(d: dict) -> dict[str, str]:
    """stage_id → 反応の種類。**優先度の低いものから書き、高いもので上書きする。**

    `app._rebucket` と同じ優先順位（持っている＞興味あり＞お気に入り＞興味なし）で
    重ねる。1 公演が 2 つの束に同時に入ることは無いはずだが、順序で決めておけば
    重なっても崩れない。
    """
    out: dict[str, str] = {}
    for key, kind in (("others", "declined"), ("favourites", "favourites"),
                      ("tracking", "tracking"), ("owned", "owned")):
        for c in d.get(key) or []:
            sid = str(c.get("stage_id") or "")
            if sid:
                out[sid] = kind
    return out


WEEKS = (("this", "今週"), ("next", "来週"))


def week_rows(d: dict, today: datetime.date, window: int = OPEN_WINDOW_DAYS,
             offset: int = 0) -> list[dict]:
    """開幕予定の**全公演**を、絞り込む前の生の行で返す。

    **`offset` は「今日から何 `window` 個ぶん先の窓か」**（今週なら 0・来週なら 1）。
    起案者の指示（2026-08-26）──「今週のページに加えて来週開催公演も追加して。タブで
    切り替えられるように」。窓の長さ（7 日）は変えず、**窓を丸ごとずらす**ことで
    「来週」を作る ── 今週と来週のあいだに漏れる日が出ない。

    絞り込みの札に出す件数（`app.page_reminder` が `RR.pref_counts`／`PM.region_counts`
    に渡す）と、実際に出す一覧（`week_all`）が、同じ元データを見るための共通口。
    """
    lo = today + datetime.timedelta(days=window * offset)
    hi = lo + datetime.timedelta(days=window - 1)
    status = _status_map(d)
    rows = []
    for c in all_candidates():
        s = RC2.period_start(c.get("period") or "")
        if not s:
            continue
        sdate = datetime.date.fromisoformat(s)
        if not (lo <= sdate <= hi):
            continue
        sid = str(c.get("stage_id") or "")
        key = status.get(sid, "unanswered")
        label, icon, cls = KIND[key]
        rows.append({**c, "start": sdate, "stage_id": sid, "kind_key": key,
                    "kind": label, "icon": icon, "cls": cls})
    rows.sort(key=lambda r: (r["start"], r["title"]))
    return rows


def _region_of(pref: str) -> str:
    """都道府県が属す地方。**`prefmap.REGIONS`（八地方区分）と同じ区切りを使う**
    ── 地方の括りをここで作り直さない。分からない値（空文字など）は自分自身を
    そのまま返す（他のどの県ともまとめない、という意味になる）。
    """
    for r, ps in PM.REGIONS:
        if pref in ps:
            return r
    return pref


_DASH = re.compile(r"[ー－‐−―—–]")


def _loose_title(title: str) -> str:
    """会場・日程が完全に一致する行を突き合わせるための、緩い題名の束ね方。

    起案者の指摘（2026-08-26・2 度目）──「『流れる雲よ』とか『どんでん』が２個ある
    けどなんで？」。実測では、候補（`candidates.jsonl`）とカレンダー（`calendar.jsonl`）
    の 2 つの取得元が同じ公演をそれぞれ別の書式の題名で持っていた ──

    - 「『流れる雲よ』27年連続再演舞台!!」／「「流れる雲よ」～令和八年より愛を込めて～」
      ── 先頭の鉤括弧の中身（流れる雲よ）だけが同じで、括弧のあとの言い回しが
      取得元ごとに違う。`RC2.work_key` は先頭 24 文字を切り出すだけなので、この
      言い回しが先頭寄りに来ると別の鍵になる。
    - 「『どんでんー私、反省期ー』」／「どんでん -私、反省期-」── 中身は同じだが、
      長音符「ー」とハイフン「-」という別の文字が使われていた。

    **`RC2.work_key` 本体は変えない。** 先頭の鉤括弧のあとを切り捨てる規則は、
    「「海賊」プロローグ付 全3幕」（劇場3のバレエ）を、別会場の無関係な同名の
    演目「海賊」と束ねてしまう実測があった ── ここでしか使わない緩い鍵にして、
    呼び出す側（`_dedupe_cross_source`）で会場・日程の完全一致を条件にする。
    """
    t = unicodedata.normalize("NFKC", title or "").replace(" ", "").replace("　", "").lower()
    t = _DASH.sub("-", t)
    m = re.match(r"^[『「](.+?)[』」](.+)$", t)
    if m and m.group(2):
        t = m.group(1)
    return re.sub(r"[『』「」]", "", t)


def _dedupe_cross_source(rows: list[dict]) -> list[dict]:
    """会場・日程が完全に一致し、緩い題名（`_loose_title`）まで一致する行を 1 本にする。

    **会場・日程の完全一致を、緩い題名の一致と両方要る条件にする。** 緩い題名だけで
    束ねると誤爆する ── 実際に会場・日程だけが一致して題名が違う組を実測で 9 組
    見つけたが、束ねてよいのはそのうち 3 組（流れる雲よ・どんでん・渋谷能、いずれも
    取得元が違うだけの同じ公演）で、残りは同じ会場・同じ日程で行われる**別の**
    演目や回だった（「青山能〈9月〉1部」「2部」、「三遊亭兼好独演会」「一龍斎貞鏡
    独演会」など）。会場・日程の完全一致だけでは危ない。

    **候補（`candidates.jsonl`）側を残す。** カレンダー側の `stage_id` は「cal」から
    始まる合成の鍵で、値段・URL などの材料を持たないことが多い。

    **日程は `RC2.period_start`／`period_end` で揃えてから比べる。** 生の `period`
    文字列は取得元ごとに書式が違う（実測 ── 候補側は「2026/08/26 (水) ～ 2026/09/06
    (日)」、カレンダー側は「2026/08/26 ~ 2026/09/06」で、曜日の注記と波ダッシュの
    半角・全角が違う）。文字列のまま比べると、日程が本当は同じでも一致しない。
    """
    groups: dict[tuple, list[dict]] = collections.defaultdict(list)
    for r in rows:
        period = r.get("period") or ""
        k = (r.get("theater") or "", RC2.period_start(period), RC2.period_end(period),
             _loose_title(r.get("title") or ""))
        groups[k].append(r)
    out = []
    for (theater, s, e, _lt), members in groups.items():
        if len(members) == 1 or not theater or not s or not e:
            out += members
            continue
        members.sort(key=lambda r: str(r.get("stage_id") or "").startswith("cal"))
        out.append(members[0])
    return out


def _merge_siblings(rows: list[dict]) -> list[dict]:
    """会場ごとに別行で登録されている同じ作品を、**同じ地方どうしだけ 1 行にまとめる。**

    起案者の指摘（2026-08-26）──「開幕リマインドに同じ作品が複数出ているのはなぜ？」。
    `all_candidates()` は `recommend2.py` が畳む前の生データなので、ツアー公演は会場
    ごとに別の行として並ぶ（実測 ── 「ブラスト!」が静岡・大阪の 2 行、「白昼夢」が
    同じ会場・同じ日程で 2 行、これはデータ側の二重登録である）。

    **取得元が違うだけの二重登録は、先に `_dedupe_cross_source` で 1 本にする**
    （同日 2 度目の指摘 ──「『流れる雲よ』とか『どんでん』が2個ある」）。会場ごとの
    ツアー日程を地方でまとめるここの規則とは条件が違う（会場も日程も完全一致という
    もっと狭い条件）ので、別の関数にして先に通す。

    続けての指示 ──「他にも会場ごとに登録されているところがあれば、同じ作品にまとめて
    1 行にして。ただし、同じ週に違う地方での公演が 2 回ある場合は分けて表示して」。
    **まとめる鍵を `recommend2.work_key`＋地方にした。** 作品名だけでまとめると、
    静岡と大阪で開幕日が違う「ブラスト!」が 1 行に潰れ、大阪の開幕がどの日かが
    埋もれてしまう ── **見逃し防止の役目が壊れる。** 地方が違えば別行、同じ地方の
    会場どうしだけ 1 行にする、という指示のとおりにした。

    1 行にまとめたときの他会場は `RR.schedule_html`（`/recommend` の「ツアーの全日程を
    地方ごとに 1 行で並べる」表示）に渡す形（`tours`）で持たせる ── 新しく書かず、
    既存の表示をそのまま使う。
    """
    rows = _dedupe_cross_source(rows)
    groups: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for r in rows:
        k = (RC2.work_key(r.get("title") or "", r["stage_id"]), _region_of(r.get("pref") or ""))
        groups[k].append(r)
    out = []
    for members in groups.values():
        members.sort(key=lambda r: (r["start"], r["stage_id"]))
        head = dict(members[0])
        # **会場・日程がまったく同じ行は、それとして 1 本にする。** データの取得元で
        # 同じ公演が別 stage_id で二重登録されていることがある（「白昼夢」で実測）──
        # 見た目が完全に同じ行を並べても、読み手には何の情報も増えない
        seen = {(head.get("theater"), head.get("period"))}
        tail = []
        for m in members[1:]:
            key = (m.get("theater"), m.get("period"))
            if key in seen:
                continue
            seen.add(key)
            tail.append(m)
        if tail:
            head["tours"] = [
                {"stage_id": m["stage_id"], "theater": m.get("theater") or "",
                 "pref": m.get("pref") or "", "period": m.get("period") or "",
                 "days": m.get("days") or 0, "price": m.get("price") or "",
                 "url": m.get("url") or "", "onsale": m.get("onsale") or "確認できず"}
                for m in tail]
        # **状態は、いちばん決着しているほうを出す。** 片方の会場だけ「持っている」まで
        # 答えていれば、もう片方が未回答でもその答えを出す（`_STATUS_RANK`）
        best_key = max((m["kind_key"] for m in members), key=_STATUS_RANK.get)
        if best_key != head["kind_key"]:
            head["kind_key"] = best_key
            head["kind"], head["icon"], head["cls"] = KIND[best_key]
        out.append(head)
    out.sort(key=lambda r: (r["start"], r["title"]))
    return out


def week_all(d: dict, today: datetime.date, window: int = OPEN_WINDOW_DAYS,
             prefs=(), offset: int = 0) -> dict:
    """開幕予定の**全公演**（好みに合うかどうかは問わない）を、日付ごとに束ねる。

    **都道府県で絞り込める**（起案者の指示・2026-08-26 ──「開幕リマインドにも都道府県の
    フィルタリング機能をつけて」）。絞り込みは会場ごとの生の行に対して行う ── `pref`
    をそのまま比べればよい（`RR.filtered` のような会場マッチングは要らない）。**そのあと
    で会場ごとの行を同じ作品・同じ地方どうしにまとめる**（`_merge_siblings`）ので、
    絞り込んで大阪府だけにした結果と、まとめたあとの行の数が食い違うことはない。

    **`offset` は `week_rows` にそのまま渡す**（今週なら 0・来週なら 1）。
    """
    lo = today + datetime.timedelta(days=window * offset)
    hi = lo + datetime.timedelta(days=window - 1)
    rows = week_rows(d, today, window, offset)
    if prefs:
        keep = set(prefs)
        rows = [r for r in rows if r.get("pref") in keep]
    rows = _merge_siblings(rows)
    days: dict[datetime.date, list[dict]] = collections.defaultdict(list)
    for r in rows:
        days[r["start"]].append(r)
    return {"days": sorted(days.items()), "n": len(rows), "window": window,
           "lo": lo, "hi": hi}


def near_tickets(owned: list[dict], tickets: dict, today: datetime.date,
                  cap: int = TICKET_MAX) -> dict:
    """「すでに持っている」公演のうち、今日以降の券だけを日付順に。

    **確定前（メールから読み取ったが本人がまだ確かめていない）の券も出すが、印を付ける。**
    隠すと「券を入れたのに、ここに出ない」という別の分からなさを生む
    （`stage_calendar.py` と同じ判断）。
    """
    by_title = {str(c.get("stage_id") or ""): c for c in owned if c.get("stage_id")}
    rows = []
    for sid, tk in tickets.items():
        c = by_title.get(sid)
        if not c:
            continue                            # 券はあるが、束からは外れた公演
        for t in tk:
            if (t.get("date") or "") < today.isoformat():
                continue
            rows.append({"title": c.get("title") or "", "venue": c.get("venue") or "",
                        "date": t["date"], "time": t.get("time") or "",
                        "confirmed": bool(t.get("confirmed"))})
    rows.sort(key=lambda r: (r["date"], r["time"]))
    return {"rows": rows[:cap], "n": len(rows)}


# **同梱した `app._poster` を差し込む。** 何も差し込まれていなければポスターは出さない
# （枠だけ置かない、既存の約束と同じ）。
POSTER = None


def _jd(d: datetime.date) -> str:
    return f"{d.month}月{d.day}日（{WEEK[d.weekday()]}）"


def _until(d: datetime.date, today: datetime.date) -> tuple[str, bool]:
    """「あと N 日」と、**急ぎの度合い**（本日・明日は強調する）。"""
    n = (d - today).days
    if n == 0:
        return "本日開幕", True
    if n == 1:
        return "明日開幕", True
    return f"あと{n}日", False


def _kind_badge(cls: str, icon: str, label: str) -> str:
    return f'<span class="dgk {cls}">{IC.ico(icon, 13)}{E(label)}</span>'


def _row(r: dict, today: datetime.date) -> str:
    until, urgent = _until(r["start"], today)
    poster = POSTER(r["stage_id"]) if POSTER and r["stage_id"] else ""
    btns = RR.buttons(r["stage_id"]) if r["kind_key"] in NEEDS_BUTTONS and r["stage_id"] else ""
    # **同じ地方にまとめた他会場は、`/recommend` と同じ「ツアーの全日程」表示で出す**
    # （`_merge_siblings` が `tours` を持たせている行だけ、`RR.schedule_html` が反応する）。
    tour_html = RR.schedule_html(r) if r.get("tours") else ""
    return (f'<li class="dgli {r["cls"]}{" dgurgent" if urgent else ""}" '
            f'data-stage="{E(r["stage_id"])}">'
            f'{poster}<div class="dgbody">'
            f'{_kind_badge(r["cls"], r["icon"], r["kind"])}'
            f'<b class="dgt">{E(r["title"])}</b>'
            f'<span class="dgw">{E(until)}'
            f'{"・" + E(r.get("venue") or "") if r.get("venue") else ""}'
            f'{"・" + E(r.get("pref") or "") if r.get("pref") else ""}</span>'
            f'{tour_html}</div>'
            f'{btns}</li>')


def _week_span(wk: dict) -> str:
    """帯の範囲を日本語で言う。**「7 日以内」は今週にしか通用しない**（来週は 8〜14 日後）
    ので、`week_all` が返す `lo`／`hi` からそのつど言葉を作る。"""
    lo, hi = wk["lo"], wk["hi"]
    return f"{lo.month}/{lo.day}〜{hi.month}/{hi.day}"


def panel(d: dict, today: datetime.date, tickets: dict | None = None, prefs=(),
         week: str = "this") -> str:
    """帯そのもの。**空でも「無い」と言い切る**（読み手が「まだ読んでいないだけ」と
    勘違いしないようにする）。

    **都道府県の絞り込みは「開幕する公演（全部）」にだけ効かせる。**
    「直近の観劇予定」は券を入れてある＝すでに決めた公演の一覧で、`app.py` の設定画面が
    「もう決めた予定は都道府県で隠さない」と決めたのと同じ理由で、ここも絞り込まない
    （選んだ県の外に行く予定を、絞り込みのせいで見落としては本末転倒である）。

    **今週に加えて来週も見られる**（起案者の指示・2026-08-26 ──「今週のページに加えて
    来週開催公演も追加して。タブで切り替えられるように」）。**タブは既存の索引の耳
    （`RR.index_tabs`）を使う** ── 月の絞り込み・興味あり・お気に入りと同じ「1 つ選ぶと
    一覧の中身が入れ替わる」操作なので、ここだけ別の見た目にしない。**タブの件数は
    両方の週を計算して出す**（選んでいない週の件数も、押す前に分かったほうがよい ──
    都道府県の札と同じ判断）。
    """
    keys = [k for k, _lab in WEEKS]
    week = week if week in keys else "this"
    wks = {k: week_all(d, today, prefs=prefs, offset=i) for i, k in enumerate(keys)}
    wk = wks[week]
    tk = near_tickets(d.get("owned") or [], tickets or {}, today)

    tabs = RR.index_tabs(
        [(k, lab, wks[k]["n"]) for k, lab in WEEKS], week,
        lambda k: f"/recommend/reminder?t=__TAGURI_TOKEN__&w={k}", "週で切り替える")

    where = "・".join(prefs) if 0 < len(prefs) <= 3 else (
        f"{prefs[0]}ほか {len(prefs) - 1} 県" if prefs else "")
    span = _week_span(wk)
    if wk["days"]:
        # **日にちごとに畳む**（起案者の指摘・2026-08-26 ──「関東を選ぶと100件近く
        # 表示されて、ページ全体が見づらい」）。実測では関東で98件のうち88件が
        # 未回答で、答え済みの分を畳んでも大きくは減らない ── **好みに関係なく全部
        # 出すという約束は崩さず**、開いたまま見せる日を絞ることで初回の量を減らす。
        # **既定で開くのは本日・明日だけ**（`_until` が急ぎと判定する日と同じ基準）。
        # それより先の日は畳んでおき、押せば開く（消さない・件数は見出しに出す）。
        days_html = "".join(
            f'<details class="dgday"{" open" if (day - today).days <= 1 else ""}>'
            f'<summary>{_jd(day)} ── {len(rows)} 件</summary>'
            f'<ul class="dglist">{"".join(_row(r, today) for r in rows)}</ul></details>'
            for day, rows in wk["days"])
        lead = (f'<b>{E(where)}</b>で観られる、{E(span)} に開幕する公演が '
                f'<b>{wk["n"]} 件</b>あります。' if prefs else
                f'<b>{E(span)} に開幕する公演が {wk["n"]} 件</b>あります。')
        open_html = (f'<p class="dglead">{lead}好みに関係なく全部出しています。</p>'
                    f'{days_html}')
    elif prefs:
        open_html = (f'<p class="dgempty"><b>{E(where)}</b>で {E(span)} に'
                     f'開幕する公演はありません。</p>')
    else:
        open_html = (f'<p class="dgempty">{E(span)} に開幕する公演は'
                     f'ありません。</p>')

    if tk["rows"]:
        li2 = "".join(
            f'<li><b class="dgt">{E(r["title"])}</b>'
            f'<span class="dgw">{_jd(datetime.date.fromisoformat(r["date"]))}'
            f'{" " + E(r["time"]) if r["time"] else ""}'
            f'{"・" + E(r["venue"]) if r["venue"] else ""}'
            f'{"　<i class=\"dgun\">確定前</i>" if not r["confirmed"] else ""}</span></li>'
            for r in tk["rows"])
        more2 = (f'<p class="dgmore">ほかに {tk["n"] - len(tk["rows"])} 件、'
                 f'券を入れてあります。</p>' if tk["n"] > len(tk["rows"]) else "")
        tk_html = f'<ul class="dglist">{li2}</ul>{more2}'
    else:
        tk_html = ('<p class="dgempty">今日より先の券はまだありません。'
                    '<a href="/tickets?t=__TAGURI_TOKEN__">持っているチケット</a>'
                    'に日を入れると、ここに出ます。</p>')

    return f"""{tabs}
<section class="dgcard dgmain">{IC.h2("inbox", f"{dict(WEEKS)[week]}開幕する公演（全部）")}
{open_html}</section>
<section class="dgcard">{IC.h2("ticket", "直近の観劇予定")}
<p class="dglead">チケットを入れてある公演だけです。</p>
{tk_html}</section>"""


STYLE = """
/* ---- 開幕リマインド ---------------------------------------------------------- */
.dgcard{background:var(--surf);border:1px solid var(--ring);border-radius:14px;
 padding:18px 20px 16px;margin:0 0 20px}
.dglead{font-size:13px;color:var(--ink2);margin:0 0 10px}
.dgday{margin:0 0 18px}
.dgday:last-child{margin-bottom:0}
/* **文字を大きくした。**（起案者の指摘・2026-08-26 ──「各日付の文字サイズをもっと
   大きくして」）。13.5px は本文の注記と同じ大きさで、7 つある日付の見出しが
   本文に埋もれていた。一般の h3（17.5px）より少し大きくし、色も薄い `--ink2` から
   `--ink` に上げて、日付が実際に見出しとして立つようにした */
/* **見出し（旧 h3）を summary にした**（起案者の指摘・2026-08-26 ──「関東を選ぶと
   100件近く表示されて見づらい」）。押して開閉できる印（▸/▾）は `.nn` と同じ規約を使う
   ── この画面だけの見た目を作らない */
.dgday summary{font-size:19px;font-weight:700;color:var(--ink);margin:0 0 10px;
 padding-bottom:5px;border-bottom:1px solid var(--grid);cursor:pointer;
 list-style:none;display:flex;align-items:center;gap:8px}
.dgday summary::-webkit-details-marker{display:none}
.dgday summary::before{content:"▸";color:var(--mute);font-size:15px}
.dgday[open]>summary::before{content:"▾"}
.dglist{list-style:none;margin:0;padding:0;display:grid;gap:9px}
.dgli{display:flex;flex-wrap:wrap;align-items:center;gap:10px;
 padding:9px 0;border-bottom:1px solid var(--grid)}
.dglist li:last-child{border-bottom:none}
.dgbody{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;flex:1 1 auto;min-width:0}
.dgt{flex:1 1 auto;min-width:0}
.dgw{color:var(--mute);font-size:12.5px;white-space:nowrap}
.dgun{color:var(--mute);font-weight:400;font-style:normal;font-size:11.5px}
/* **本日・明日だけ太く大きくする。** 新しい色は増やさず、太さと大きさだけで急ぎ度を
   出す（起案者の指示・2026-08-26） */
.dgurgent .dgw{font-size:14.5px;font-weight:700;color:var(--ink)}
/* **決着済み（興味なし・持っている）は静かにする。** 答える必要が無い行に注意を
   引きすぎない */
.dgli.dec{opacity:.72}
.dgli.own .dgw{color:var(--ink2)}
/* **興味あり・お気に入りは、行の左に印を引いて目立たせる**（起案者の指摘・2026-08-26
   ──「興味があるだったりお気に入りのものはもうちょっと強調してもよいと思う」）。
   興味ありは、評価の判子・索引の耳の「現在地」と同じ意味を持つえんじ（`--curtain`）
   を流用する。太い左線と、行の背景を `--plane` にわずかに沈めるだけにする。 */
.dgli.trk,.dgli.fav{background:var(--plane);
 padding:9px 10px;border-radius:0 8px 8px 0;margin:0 0 0 -1px}
.dgli.trk{border-left:3px solid var(--curtain)}
.dgli.trk .dgt,.dgli.fav .dgt{font-weight:700}
/* **お気に入りだけ、封蝋と同じ黄色を左線に使う**（起案者の指示・2026-08-26 ──
   「サイトで統一してお気に入りにはこのテーマに合う黄色をつけて」）。新しい色は
   増やさない、という上の決まりに対する、お気に入りだけの例外である */
.dgli.fav{border-left:3px solid var(--wax)}
/* ポスター。既存のカードと同じ枠（.pwrap）をそのまま使うので、寸法だけここで決める */
.dgli .pwrap{flex:none;width:46px;height:64px;border-radius:6px}
/* **形は stage_calendar.py の 3 種類と同じ約束にする。** 藍とえんじは押せる・識別の
   意味をすでに持っているので、ここでは色を運ばない ── **お気に入りだけ、上と同じ
   理由で例外にする。**「未回答」は見逃しリスクの本体だが、形を目立たせるのは行の
   中身（太字の題名・急ぎ度）の役目にして、バッジ自体は静かにする */
.dgk{display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:2px 8px;
 border-radius:99px;flex:none;color:var(--mute)}
.dgk.trk{border:1px solid var(--base);color:var(--ink2)}
.dgk.fav{border:1px dashed var(--wax);color:var(--wax)}
.dgk.own{background:color-mix(in srgb,var(--ink) 12%,transparent);color:var(--ink2)}
.dgk.dec{color:var(--mute)}
.dgempty{font-size:13px;color:var(--mute);margin:0}
.dgmore{font-size:12px;color:var(--mute);margin:8px 0 0}
/* 三択ボタン（RR.buttons）は既存の .btns の見た目のまま。行の右端に置く */
.dgli .btns{flex:none;margin-left:auto}
"""
