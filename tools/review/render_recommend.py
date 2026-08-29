#!/usr/bin/env python3
"""今週の推薦を、企画書 2 章「1 件に表示するもの」の形で組む（recommend2.json を読む）。

  python3 tools/review/recommend2.py --today 2026-08-21 && python3 tools/review/render_recommend.py

## なぜ表ではなくカードか

**表にすると、識別（題名・劇場・日程）と理由（誰が・何が）が同じ幅の欄に押し込まれる。**
検証 021 の指摘 1 は「**あらすじも合わせて表示しないと、興味があると断言できない**」で、
あらすじは 3〜4 行ある ── 表の 1 セルに入る量ではない。企画書 2 章の実例もカードの形である。

## 出力は端末内に置く

理由の欄に「観た N 本中 M 本が ◎」という**観劇履歴そのもの**が出るので、
`data/review/` に書く（`.gitignore` 済み。`lookback.html` と同じ扱い）。

## ボタンは本物である（2026-08-24）

**ボタンはこれまで文字列だった。** そのため反応 50 件はすべて会話から入っており
（`ratings.db` の `source='chat'`）、企画の中核である輪が画面の側で閉じていなかった。
**`tools/taguri/serve.py` が `127.0.0.1` に立てた口へ押した内容を送る形に変えた。**

**トークンはこのファイルに書かない。** `__TAGURI_TOKEN__` の位置に、配る直前に
起動ごとの乱数が入る。**このファイルを直接開いた場合は置換が起きないので、画面側が
ボタンを無効にして「書き戻せない」と表示する** ── 押せたのに記録されていない、という
状態を作らない。

## 表示できない項目は「確認できず」と書いて出す

企画書 2 章は**買える最終期限（買える窓）**と**販売終了・完売**を表示項目に挙げているが、
どちらも母集団（CoRich の一覧と公演ページの表）には無い。**空欄にせず、取れていないことを
画面に書く** ── 順位を下げるだけで消さないのが企画書の決めた扱いである。
"""
from __future__ import annotations

import collections
import html
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import icons as IC                                                   # noqa: E402
import impressions as IM                                             # noqa: E402
SRC = ROOT / "data" / "review" / "recommend2.json"
OUT = ROOT / "data" / "review" / "recommend.html"
E = lambda s: html.escape(str(s))                                       # noqa: E731

ROLE_SRC = "公演ページのクレジット"

# **ポスターの差し込み口。** `tools/taguri/app.py` が「端末内の道を返す関数」を入れる。
# **ここで外部の URL を返してはいけない** ── 画面から外部サイトを叩かないという守り
# （企画書 5 章の 5）を、画像 1 枚で破ることになる。既定は何も出さない。
POSTER = None

# **感想の差し込み口。** `tools/taguri/app.py` が「作り手の名前 → 感想を書いた ◎ の作品」
# を入れる（`impressions.by_person()`）。**既定は空** ── 感想が 1 件も無い状態でも
# 理由の欄はそのまま成立する。
NOTES_BY_PERSON: dict = {}


def poster(stage_id, fallback: str = "") -> str:
    """**取り込み済みのポスターを出す。当たらなければ同じ作品の別会場で引き直す。**

    都道府県で絞り込むと、カードの主たる会場がツアーの他会場に入れ替わる。**その会場の
    ページからポスターを取り込んでいるとは限らない**ので、代表の会場でも引く ──
    同じ作品なので絵は同じである。
    """
    if not POSTER:
        return ""
    return POSTER(stage_id) or (POSTER(fallback) if fallback and fallback != stage_id else "")
CORICH = ROOT / "data" / "credits" / "pages"


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", re.sub(r"\s+", "", s or ""))


def synopsis_source(stage_id: str, syn: str) -> tuple[str, bool]:
    """あらすじの出どころを判定して返す（表示名, 疑いがあるか）。

    **出典は「読み手が事実を確かめられること」のために出す**（企画書 2 章）。ところが
    抽出の材料は CoRich の公演ページと公式サイトの 2 本で、**公式サイトの URL 欄には
    劇団のトップページや劇場のラインナップ表が入っていることがある** ── その場合、
    **別公演のあらすじを掴む。** 実際に「Closeted Life クローゼットライフ」の URL は
    OFF・OFFシアターのラインナップ（`honda-geki.com/offoff`）で、出たあらすじは
    その劇場の別公演のものだった（CoRich の公演ページには当該の語が 1 つも無い）。

    **その公演自身のページ（CoRich）に本文が見つかるかどうかで割る。** 見つからないものは
    公式サイト由来なので、**混ざりうることを画面に書く**（消さずに疑いを添える）。
    """
    f = CORICH / f"https___stage_corich_jp_stage_{stage_id}.html"
    if not f.exists() or not syn:
        return "公式サイト", True
    t = _norm(re.sub(r"<[^>]+>", " ", f.read_text(encoding="utf-8", errors="ignore")))
    # **先頭 30 字の一致では判定を誤る。** LLM が抜き出すのは本文の途中からのことが多く、
    # 「懺悔と七面鳥」「春よ来い、マジで来い」は CoRich に本文があるのに公式扱いになっていた。
    # **12 字の窓を等間隔に 5 つ取り、3 つ以上が一致すること**で見る
    # （`extract_theme_llm.verbatim` と同じ規則にそろえた）。
    a = _norm(syn)
    if len(a) < 24:
        return "公式サイト", True
    win = 12
    hit = sum(1 for i in range(5) if a[int(i * (len(a) - win) / 4):][:win] in t)
    return ("CoRich の公演ページ", False) if hit >= 3 else ("公式サイト", True)


def period_label(period: str, days: int) -> str:
    """「9/5〜9/27・23 日間」「10/3 のみ・1 日公演」。**日数を必ず添える**（企画書 2 章）。

    **日数を渡されなかったら、期間から数える。** 一覧の控えから来た行は `days` を持って
    いない ── そこで `days` の有無だけで「1 日公演」と決めていたため、**4/6〜3/31 の
    ロングランが「4/6 のみ・1 日公演」と出ていた**（探す画面の月の一覧で見つけた）。
    **持っていない値を 0 と読んで、事実でないことを書かない。**
    """
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return E(period)
    fs = f"{int(ms[0][1])}/{int(ms[0][2])}"
    if len(ms) == 1 or ms[0] == ms[-1]:
        return f"{fs} のみ・<b>1 日公演</b>"
    if days <= 1:
        try:
            a = date(*map(int, ms[0]))
            b = date(*map(int, ms[-1]))
            days = (b - a).days + 1
        except ValueError:
            days = 0
    tail = f"・{days} 日間" if days > 1 else ""
    return f"{fs}〜{int(ms[-1][1])}/{int(ms[-1][2])}{tail}"


def short_period(period: str) -> str:
    """他会場の行に出す短い日程（「10/2〜10/3」）。年は同じ年しか出ないので落とす。"""
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return period
    a = f"{int(ms[0][1])}/{int(ms[0][2])}"
    b = f"{int(ms[-1][1])}/{int(ms[-1][2])}"
    return a if a == b else f"{a}〜{b}"


def _period_end(period: str) -> date | None:
    """期間の文字列から楽日を取り出す。**読めなければ何も言わない**（`None`）。"""
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return None
    try:
        return date(*map(int, ms[-1]))
    except ValueError:
        return None


def _period_start(period: str) -> date | None:
    """期間の文字列から初日を取り出す。**読めなければ何も言わない**（`None`）。
    行く日の入力欄の `min` に使う ── `_period_end` と対にする。
    """
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return None
    try:
        return date(*map(int, ms[0]))
    except ValueError:
        return None


# 都道府県から削る語。**北海道だけは削らない**（「北海」という地名が無いため）
_PREF_SUFFIX = "都道府県"


def region_label(pref: str, fallback: str = "") -> str:
    """都道府県から、ふだん使う短い呼び名を作る（「東京都」→「東京」）。

    **市区町村までは読み取らない。** 会場名の表記は揺れが大きく、機械的に安定して
    取り出せない ── 都道府県ならデータに必ず入っている値なので、確実に出せる。
    """
    if not pref:
        return fallback
    if pref == "北海道":
        return pref
    return pref[:-1] if pref[-1] in _PREF_SUFFIX else pref


def schedule_html(c: dict) -> str:
    """ツアーの全日程を、地方ごとに 1 行で並べる。**終わった日程には線を引く。**

    起案者の指摘（2026-08-26）──「興味あるんだけどその地方公演だといけない…って
    パターンがよくある。ので、ここでの表示はツアー全日程表示してほしい。たとえば…
    『東京公演○○、可児公演○○』って改行して書いてほしい。終わった日程は線を引いて
    消して」。続けて（2026-08-26）──「各公演の詳細で、『東京公演』とかのあとに
    本当の会場の名前も書いてください」。**「東京公演」は都道府県から作った呼び名で、
    どの劇場かは書いていなかった**（同じ都道府県に複数の劇場があるツアーでは、
    どこの劇場か分からないと足を運べるかどうかを判断できない）。会場名が取れて
    いれば「／」で続けて出す。取れていない行は「会場未定」のままにする。

    **主催会場も同じ並びに入れる。** 主催会場だけ上の日程欄にしか出ないと、
    「東京公演」がこの一覧に無いように見える ── `venues()` が組む「代表も他会場も
    同じ形にする」並びをそのまま使う。

    **上限で切らない。** 前は 4 会場までにして残りを「ほか N 会場」とまとめていたが、
    **「地方公演だと行けない」を判断するには、どの地方がいつなのかを全部読める必要が
    ある。** 4 件目以降にこそ、行けるかどうかを知りたい会場が入っている。

    **消すのではなく、線を引いて残す。** 終わった日程を一覧から消すと、
    ツアー全体が何都市を回ったのかが分からなくなる。
    """
    vs = venues(c)
    if len(vs) < 2:
        return ""                       # 1 会場しか無い公演には出さない（二重に書くだけ）
    today = date.today()
    rows = []
    for v in vs:
        end = _period_end(v["period"])
        done = bool(end) and end < today
        loc = region_label(v["pref"], v["theater"] or "会場未定")
        # **都道府県の呼び名（「東京公演」）だけでは、どの劇場かが分からない。**
        # 会場名が取れていれば添える ── 同じ都道府県に複数の劇場があるツアーでは、
        # 都道府県だけでは足を運べるかどうかを判断できない。会場名がそのまま
        # `loc` に入っている（`pref` が空の）行では、二重に書かない。
        theater = (f'<span class="tf-th">／{E(v["theater"])}</span>'
                  if v["theater"] and v["pref"] else "")
        rows.append(
            f'<div class="tf-row{" done" if done else ""}">'
            f'<span class="tf-loc">{E(loc)}公演{theater}</span>'
            f'<span class="tf-when">{E(short_period(v["period"]))}</span></div>')
    return f'<div class="tourfull">{"".join(rows)}</div>'


# ---------------------------------------------------------------- 都道府県で絞り込む
#
# **既定は全国である**（起案者の指示 ──「デフォルトは全国でいい」）。選ぶまでは何も絞らない。
#
# ## 判定は「その県で観られるか」で行う ── ツアーの他会場も数える
#
# 推薦の 1 件は**作品単位に畳んである**（同じ作品の巡業 8 会場が一覧を占領しないため）。
# 代表として残るのはスコアがいちばん高い 1 会場なので、**代表の県だけで判定すると、
# 東京で初日を迎えて大阪にも来る作品が、大阪で絞ったときに消える。**
#
# **実測 ── 大阪府で観られる公演は 19 件あるが、代表の県で数えると 8 件しかない。**
# 半分以上が「行けるのに出てこない」。順位の付いた 112 件のうち 24 件が複数の県で上演される。
#
# **当たった会場を、そのカードの主たる会場として出す。** 県だけ合わせて東京の日程を出すと、
# 読み手は自分の県の日程を知らないまま「行ける」と判断することになる。
#
# ## 切る位置を計算の側から画面の側へ移した
#
# 全国の上位 15 件を切ったあとの一覧では、**どの県で絞っても 15 件に届かない**
# （大阪府で観られる 19 件のうち、全国の上位 15 件に入っているのは 1 件だけである）。
# `recommend2.py` が順位の付いた全件を `ranked` に残し、**15 件で切るのはここで行う。**
PREFS = ("北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
         "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
         "岐阜県", "静岡県", "愛知県", "三重県",
         "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
         "鳥取県", "島根県", "岡山県", "広島県", "山口県",
         "徳島県", "香川県", "愛媛県", "高知県",
         "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県")
TOP = 15


def _start(period: str) -> str:
    """初日を並べ替えできる形（YYYY-MM-DD）で返す。**月日は 0 詰めしてから比べる。**"""
    m = re.search(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    return f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}" if m else ""


def venues(c: dict) -> list[dict]:
    """1 件（＝ 1 作品）が上演される会場を全部返す。**代表も他会場も同じ形にする。**

    **古い `recommend2.json` にも当たる。** 他会場の行に発売の状況や上演日数が無い版が
    あるので、無い項目は空にして落とさない（**取れていないことと、行けないことは別である**）。
    """
    out = [{"stage_id": str(c.get("stage_id") or ""), "theater": c.get("theater") or "",
            "pref": c.get("pref") or "", "period": c.get("period") or "",
            "days": c.get("days") or 0, "price": c.get("price") or "",
            "url": c.get("url") or "", "onsale": c.get("onsale") or "確認できず"}]
    for t in (c.get("tours") or []):
        out.append({"stage_id": str(t.get("stage_id") or ""), "theater": t.get("theater") or "",
                    "pref": t.get("pref") or "", "period": t.get("period") or "",
                    "days": t.get("days") or 0, "price": t.get("price") or "",
                    "url": t.get("url") or "", "onsale": t.get("onsale") or "確認できず"})
    return out


def pref_counts(d: dict) -> dict:
    """都道府県ごとに、**そこで観られる公演の件数**を数える（順位の付いた全件が母数）。

    **選べる県だけを画面に出すために使う。** 0 件の県を並べると、押しても何も起きない
    選択肢を 47 個見せることになる。
    """
    n: dict = collections.Counter()
    for c in (d.get("ranked") or d.get("recommend") or []):
        for p in {v["pref"] for v in venues(c) if v["pref"]}:
            n[p] += 1
    return n


def filtered(d: dict, prefs=(), top: int = TOP) -> tuple[list, int]:
    """絞り込んだ一覧と、**絞り込みに当たった総数**を返す。

    **総数を一緒に返すのは、切り落とした件数を画面に書くためである** ── 15 件で切ったこと
    だけを書いて、残りが何件あるのかを書かないと、一覧が全部だと読まれる。
    """
    rows = d.get("ranked") or d.get("recommend") or []
    if not prefs:
        return [dict(c, home_stage_id=str(c.get("stage_id") or "")) for c in rows[:top]], len(rows)
    keep = set(prefs)
    out = []
    for c in rows:
        vs = venues(c)
        hit = [v for v in vs if v["pref"] in keep]
        if not hit:
            continue
        # **選んだ県の中でいちばん早い日程を主たる会場にする。** 買い忘れを防ぐ用途なので、
        # 同じ県に 2 会場あるときは締切が近いほうを出す
        v = min(hit, key=lambda x: _start(x["period"]) or "9999")
        rest = [x for x in vs if x["stage_id"] != v["stage_id"]]
        out.append(dict(c, home_stage_id=str(c.get("stage_id") or ""), tours=rest, **v))
    return out[:top], len(out)


# **1 画面に出すチケットの枚数。** 推薦の 15 件（`TOP`）とは別に持つ ── あちらは
# 「今週これだけ出す」という中身の上限だが、こちらは**全件を月に分けて出すときの
# 1 画面ぶん**である（起案者の指示・2026-08-24）。1 枚が 500〜660px あるので、
# 31 件を並べると画面 25 枚ぶんになっていた。
LIST_TOP = 8


def month_key(c: dict) -> str:
    """その 1 件が入る月。**並べ替えに使う日付と同じ日付で決める**（初日）。

    **別の日付で切ると、並び順と札の数が合わなくなる。** 一覧は初日の近い順なので、
    月も初日で切る ── 「9 月 12 件」と書いた札を押して、9 月に始まらない公演が
    混ざっていたら、その数字は何を数えたものか分からない。
    """
    return _start(c.get("period") or "")[:7]


def month_label(m: str) -> str:
    y, _, mo = m.partition("-")
    return f"{y} 年 {int(mo)} 月" if mo else "上演日が分からない公演"


def paginate(rows: list, page: int, per: int, url, unit: str = "件") -> tuple[list, str, str]:
    """行を 1 画面ぶんに切り、**あふれた分の行き先を必ず書いて返す。**

    返り値は (出す行, 状態の 1 文, 一覧の下に置く送り)。`url(pg)` が pg ページ目の道を返す。

    **`month_pick` を呼ばずにこちらを足したのは、あちらの状態の文が月の名前と
    織り合わさっているからである**（「2026 年 10 月の 7 件で、1〜8 件目を…」）。
    月の札を作らない画面から呼ぶと、要らない札が付いてくる。**送りの形は同じもの**
    （`.mfoot` / `.mpage`）を使うので、画面ごとに送りの見た目を覚え直すことはない。

    **上限を書くときは、あふれた分がどこにあるかを一緒に書く** ── 書かないと、
    一覧がそれで全部だと読まれる（`month_pick` と同じ約束）。
    """
    last = max(1, -(-len(rows) // per))
    page = min(max(page, 1), last)
    show = rows[(page - 1) * per:page * per]
    first = (page - 1) * per + 1
    if last <= 1:
        return show, f"{len(rows)} {unit}すべてを表示しています。", ""
    now = (f"<b>{first}〜{first + len(show) - 1} {unit}目</b>を表示しています"
           f"（全 {len(rows)} {unit}）。<b>残りは下の「次の {per} {unit}」で"
           f"見られます。</b> ")
    prev = (f'<a class="mpage" href="{url(page - 1)}">← 前の {per} {unit}</a>'
            if page > 1 else f'<span class="mpage off">最初のページです</span>')
    nxt = (f'<a class="mpage" href="{url(page + 1)}">'
           f'次の {min(per, len(rows) - page * per)} {unit} →</a>'
           if page < last else '<span class="mpage off">これで最後です</span>')
    foot = (f'<div class="mfoot">{prev}'
            f'<span class="mp">{page} / {last} ページ</span>{nxt}</div>')
    return show, now, foot


def index_tabs(items, sel: str, url, label: str, *, show_label: bool = False) -> str:
    """帳面に挟んだ索引の耳（起案者の指示・2026-08-24）。

    `items` は (鍵, 見出し, 件数) の並びで、`url(鍵)` がその耳を開く道を返す。

    **押せる耳は紙の色に藍の文字、開いている耳はえんじの白抜き**（起案者の指示）。
    開いている耳は帳面の上端の線と同じ色なので、耳と紙の境が消えて 1 枚につながる。

    **「1 つ選ぶと一覧の中身が入れ替わる」操作は、画面をまたいで全部これである** ──
    評価一覧・日記帳・興味あり・お気に入り・探す。**別々に書くと片方だけ直したときに
    2 つの形になる。** 実際にそうなっていた ── 評価と日記帳を耳に変えたときに、
    月の絞り込み（`month_pick`）と探すの札は丸いピルのまま残り、**同じ操作に
    2 つの見た目が並んでいた。**

    **空の束の耳は呼ぶ側で外す** ── 押しても何も出ない選択肢を並べない。

    ## 開いている耳に、色に頼らない印を足した（起案者の指摘・2026-08-25）

    「今どっちを選択しているのか わかりにくい色になっている」。**耳が 2 枚しか無い
    画面（探すの暦）で指摘を受けた** ── 3〜5 枚並ぶ評価一覧・日記帳では他の耳との
    対比で開いている耳が浮くが、**2 枚だけだと「塗りつぶし」と「藍の文字」という
    別々の見た目のどちらが『選ばれている』側なのかを、色の意味を知らない限り
    毎回考え直すことになる。**

    このアプリは他の場所でも**色だけで意味を運ばない**（人の網の「外すと割れる人」は
    輪の太さでも示す・評価は塗りと白抜きの両方で示す）。耳にも同じ規則を適用し、
    **開いている耳にだけ、check の印を置いた。** 藍とえんじの意味を知らなくても、
    どちらが選ばれているかは印の有無だけで読める。

    ## `show_label` ── 耳が2段以上重なる画面だけ、見出しを文字でも出す（2026-08-29）

    `label`はもともと`aria-label`（スクリーンリーダー専用）にしか使っておらず、
    晴眼者には見えなかった。評価一覧のように「評価で切り替える」耳の下に
    「年で絞る」耳がもう1段重なる画面では、**どちらの耳が何の絞り込みなのかが
    見た目だけでは読めない**（起案者の指摘）。耳が1段しかない画面（探すの暦等）は
    見出しが無くても迷わないので、呼ぶ側が明示的に選んだときだけ文字を出す
    （既定は今までどおり非表示、他の画面の見た目は変えない）。
    """
    out = []
    for k, lab, n in items:
        on = k == sel
        mark = IC.ico("check", 14, "ixck") if on else ""
        out.append(f'<a class="ix{" on" if on else ""}"'
                   f'{" aria-current=\"page\"" if on else ""}'
                   f' href="{url(k)}">{mark}{E(lab)}'
                   f'<span class="mn">{n}</span></a>')
    head = f'<span class="idx-lab">{E(label)}</span>' if show_label else ""
    return f'{head}<nav class="idx" aria-label="{E(label)}">{"".join(out)}</nav>'


def month_pick(rows: list, sel: str, page: int, action: str) -> tuple[list, str, str]:
    """月で絞り込む札と、続きへの送りを組み、**画面に出す行を決めて返す。**

    返り値は (出す行, 一覧の上に置くもの, 一覧の下に置くもの)。

    起案者の指示（2026-08-24）──「興味あり・お気に入りが今全件羅列されるようになって
    いるので、月で絞り込みできるようにして。1 ページあたりの表示件数を減らしてください」。

    ## どの見方でも 1 画面 `LIST_TOP` 枚に揃える

    **月は大きさが揃わない。** 実データでは 9 月に 12 件あり、月で切っただけでは
    画面 14 枚ぶんになって、31 件を全部並べていたときと大差がない。**月は「どれを見るか」
    を選ぶもので、1 画面の量を決めるものではない。** 量は枚数で決め、続きは送りで見る。

    ## 消していない ── 切ったぶんの行き先を必ず書く

    上限を書くときは、あふれた分がどこにあるかを一緒に書かなければ、**一覧がそれで
    全部だと読まれる。** ここでは「何件中の何件目か」と、次の送りと、月の札の 3 つが
    その行き先である。

    ## 月は 1 つだけ選ぶ

    都道府県（`pref_form`）は同時にいくつでも選べるが、**月は 1 つで足りる** ── 複数の月を
    まとめて見たいときは「近い順」に戻せばよく、2 つの選び方が同じことをするなら片方は
    要らない。そのため素のリンクにした（form も JavaScript も要らない）。

    ## 札には件数を書く

    押す前に、その月に何件あるかが分かるほうがよい（都道府県の札と同じ判断）。
    **0 件の月は札を出さない** ── 押しても何も起きない選択肢を並べない。
    """
    counts: dict[str, int] = {}
    for c in rows:
        k = month_key(c) or "none"
        counts[k] = counts.get(k, 0) + 1
    months = sorted(k for k in counts if k != "none")
    if "none" in counts:
        months.append("none")
    sel = sel if sel in counts else ""
    if sel == "none":
        hit = [c for c in rows if not month_key(c)]
    elif sel:
        hit = [c for c in rows if month_key(c) == sel]
    else:
        hit = list(rows)
    last = max(1, -(-len(hit) // LIST_TOP))
    page = min(max(page, 1), last)
    show = hit[(page - 1) * LIST_TOP:page * LIST_TOP]
    link = f"{action}?t=__TAGURI_TOKEN__"

    def url(m: str, pg: int) -> str:
        return link + (f"&amp;m={E(m)}" if m else "") + (f"&amp;p={pg}" if pg > 1 else "")

    # **月の切り替えも索引の耳で出す**（`index_tabs`）。以前はここだけ丸いピルで、
    # 評価一覧と日記帳の耳と 2 つの形が並んでいた ── **やっていることは同じ
    # 「1 つ選ぶと一覧の中身が入れ替わる」なので、画面ごとに形を覚え直させない。**
    #
    # **「すべて」の耳はここには置く。** 評価一覧では置かないと決めてあるが（98 件を
    # 1 本に並べると札にした意味が消える）、**月はもともと「近い順に全部」が既定の
    # 読み方**で、月で切るのはそこから絞る操作である。戻り先が無いほうが困る。
    tabs = index_tabs(
        [("", "すべて", len(rows))]
        + [(m, month_label("" if m == "none" else m), counts[m]) for m in months],
        sel, lambda m: url(m, 1), "月で切り替える")
    where = ("上演日の近い順" if not sel
             else f"<b>{E(month_label('' if sel == 'none' else sel))}</b>の "
                  f"{len(hit)} 件")
    first = (page - 1) * LIST_TOP + 1
    if len(hit) <= LIST_TOP:
        now = f"{where}で、{len(hit)} 件すべてを表示しています。"
    else:
        now = (f"{where}の <b>{first}〜{first + len(show) - 1} 件目</b>を"
               f"表示しています（全 {len(hit)} 件）。"
               f"<b>残りは下の「次の {LIST_TOP} 件」か、上の索引の耳で見られます。</b>")
    # **耳の下は帳面である。** 耳は下端の 2px を帳面の上端に重ねて 1 枚につながる形なので、
    # 受ける面が無いと耳だけが宙に浮く（`.idxsheet` を閉じるのは `foot` の側）。
    head = f'{tabs}<div class="idxsheet loose"><p class="mnow">{now}</p>'
    if last <= 1:
        return show, head, "</div>"
    prev = (f'<a class="mpage" href="{url(sel, page - 1)}">← 前の {LIST_TOP} 件</a>'
            if page > 1 else '<span class="mpage off">最初のページです</span>')
    nxt = (f'<a class="mpage" href="{url(sel, page + 1)}">'
           f'次の {min(LIST_TOP, len(hit) - page * LIST_TOP)} 件 →</a>'
           if page < last else '<span class="mpage off">これで最後です</span>')
    foot = (f'</div><div class="mfoot">{prev}'
            f'<span class="mp">{page} / {last} ページ</span>{nxt}</div>')
    return show, head, foot


# **地図と地方の札の差し込み口。** `tools/taguri/serve.py` が入れる（ポスターと同じ形）
EXTRA = None


_PREF_NOTE = (f'都道府県は<b>いくつでも同時に選べます</b>。選んだ県で観られる公演を、'
              f'好みに合いそうな順に <b>{TOP} 件</b>まで表示します。数字は、その県で'
              f'観られる件数です。<b>選ばなければ全国です。</b>ツアーで来る公演も'
              f'入ります ── 本拠が他県でも、選んだ県に来るものは、その会場の日程で出します。')


def pref_form(counts: dict, prefs=(), action: str = "/recommend", note: str = "",
              hidden: dict | None = None) -> str:
    """都道府県の選び方。**同時にいくつでも選べる**（起案者の指示）。

    **`action`・`note` は呼び出す画面ごとに違う。** `/recommend/reminder`（開幕リマインド）
    も同じ形の絞り込みを持つ（起案者の指示・2026-08-26）── **選んだ都道府県は
    `srv.prefs` を共有するので、どちらの画面で選んでも両方に効く。** 送る先の URL だけが
    画面ごとに違う。`note` を渡さない既定は `/recommend` の文（順位が付く・件数に上限が
    ある）のままにする ── 開幕リマインドは順位も上限も無い「全部出す」画面なので、
    そちらは `app.page_reminder` が自分の文を渡す。

    **押した数を書いた札にする。** 「大阪府」とだけ出ていると、押してから 3 件しかないと
    分かることになる ── **押す前に、その県で何件観られるかが分かるほうがよい。**

    **JavaScript を使わない素の form にした。** 選んで「絞り込む」を押すと `/recommend`
    へ GET で戻るだけである。画面の側で組み替える形にすると、**15 件より下の公演を画面に
    渡しておく必要がある** ── 順位の付いた 112 件ぶんのあらすじとクレジットを毎回
    ブラウザに送ることになり、読む速さと引き換えになる。

    **地図と地方の札は、この上に差し込む**（`EXTRA`／`tools/taguri/prefmap.py`）。
    起案者の指示（2026-08-25）で足したものだが、**送るものは 1 つも変わらない** ──
    どちらもここのチェックを反転させるだけの押し口で、選んだ内容を持っているのは
    最後までこの並びである。**差し込み口にしたのは、地図が画面の側の部品だからである**
    （この関数は `run.py` が 1 枚の HTML を書き出すときにも通る）。

    **`hidden` は、この絞り込みと同時に画面が持っている別の状態を運ぶ。** 開幕リマインドの
    週タブ（`w=this`／`w=next`）がその例 ── 「来週」を見ている途中で都道府県を絞り込むと、
    ここで運ばないと「今週」に戻ってしまう。押し口が 2 つ（送信ボタンと「全国に戻す」の
    素のリンク）あるので、両方に同じ値を付ける。

    **既定は畳んでおく**（起案者の指示・2026-08-26 ──「『観に行ける場所を絞り込む』は
    デフォルトで折りたたんでいてください」）。**以前は絞り込み中（`keep` が空でない）
    なら開いたままにしていたが、それも畳む。** 設定画面の既定の都道府県（起案者の指示・
    同日）が入ると、開いた時点で毎回この帯が開いていることになり、押したいカードまでの
    距離が伸びる。**`summary` に「いまは○○」と現在の絞り込みを文字で出している**ので、
    畳んでいても何を選んでいるかは見える ── 開いて確かめる必要はない。
    """
    keep = set(prefs)
    chips = "".join(
        f'<label class="pchip{" on" if p in keep else ""}">'
        f'<input type="checkbox" name="pref" value="{E(p)}"{" checked" if p in keep else ""}>'
        f'<span class="pl">{E(p)}</span><span class="pn">{counts[p]}</span></label>'
        for p in PREFS if counts.get(p))
    now = ("全国" if not keep else
           "・".join(p for p in PREFS if p in keep) + f"（{len(keep)} 県）")
    hidden_in = "".join(f'<input type="hidden" name="{E(k)}" value="{E(v)}">'
                        for k, v in (hidden or {}).items())
    hidden_qs = "".join(f"&amp;{E(k)}={E(v)}" for k, v in (hidden or {}).items())
    return f"""<form class="pfil" method="get" action="{E(action)}">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<input type="hidden" name="f" value="1">
{hidden_in}
<details class="pbox">
<summary>{IC.ico("search", 15)}観に行ける場所で絞り込む ── いまは<b>{E(now)}</b></summary>
<p class="lead">{note or _PREF_NOTE}</p>
{EXTRA() if EXTRA else ""}
<div class="pchips">{chips}</div>
<div class="pfoot"><button type="submit">{IC.ico("search")}この都道府県で絞り込む</button>
<a class="pall" href="{E(action)}?t=__TAGURI_TOKEN__&amp;f=1{hidden_qs}">全国に戻す</a></div>
</details></form>"""


# 名前の並びを崩さずに切る区切り。**中黒では切らない**
# ── 「作り手3」のような名前が真ん中で割れる
NAME_SEP = re.compile(r"[、，,／/\n\r\t]+|\s{2,}")
# 出演者の欄の末尾に付く「他」「ほか」。**人名として並べない**
ETC = ("他", "ほか", "ほか出演者", "他多数")
# 作り手として一緒に出す役職。**裏方は出さない** ── 30 名を超える欄があり、
# 読む量が増えるばかりで、観るかどうかの判断には使われていないと実測されている
MAKER_ROLES = ("演出", "脚本", "作", "原作", "翻訳", "音楽", "作曲", "振付", "演出・振付")
CAST_SHOWN = 12          # まず出す人数（残りは押すと開く）


def split_names(raw: str) -> list[str]:
    """欄の文字列を、**並び順のまま**名前に切る。

    **`parse_credits` は使わない。** あちらは名寄せのために並べ替えて重複を潰すので、
    **序列（誰が主演か）が消える。** 画面に出すのは事実の並びなので、元の順を保つ。
    """
    out = []
    for x in NAME_SEP.split(raw or ""):
        x = x.strip().strip("　")
        if not x or x in ETC or len(x) > 40:
            continue
        if x not in out:
            out.append(x)
    return out


def cast_block(c: dict) -> str:
    """**出演者と作り手を、推薦の理由とは別に、事実として出す。**

    起案者の指示 ──「一応出演者情報も明記してほしい。推薦理由とは別に、そっちを見て
    興味ありにすることもあり得るので」。

    **理由の欄には、名簿に入っている人しか出てこない。** 名簿は「◎ を付けた公演の作り手」
    しか材料に持てないので、**まだ 1 度も観ていない人はどれだけ気になる名前でも理由に出ない。**
    出演者の一覧をそのまま出せば、その名前は読み手自身が見つけられる。
    """
    f = c.get("fields") or {}
    cast = split_names(f.get("出演", ""))
    makers = [(r, split_names(f.get(r, ""))) for r in MAKER_ROLES if f.get(r)]
    makers = [(r, ns) for r, ns in makers if ns]
    if not cast and not makers:
        return ('<div class="cast none">出演者のクレジットを取れませんでした'
                '（公演ページに欄がありません）</div>')
    rows = []
    if cast:
        head = "、".join(E(n) for n in cast[:CAST_SHOWN])
        rest = cast[CAST_SHOWN:]
        more = (f'<span class="rest">、{"、".join(E(n) for n in rest)}</span>'
                f'<button class="mrb" data-more="1">ほか {len(rest)} 名を見る</button>'
                if rest else "")
        rows.append(f'<div class="cr"><span class="cl">出演</span>'
                    f'<span class="cv">{head}{more}</span></div>')
    for role, ns in makers:
        rows.append(f'<div class="cr"><span class="cl">{E(role)}</span>'
                    f'<span class="cv">{"、".join(E(n) for n in ns[:6])}'
                    + (f'ほか {len(ns) - 6} 名' if len(ns) > 6 else "") + "</span></div>")
    return (f'<div class="cast">{"".join(rows)}'
            f'<span class="src">［出典: {E(ROLE_SRC)}］</span></div>')


def reason_rows(c: dict) -> str:
    """理由を、網ごとに 1 行ずつ。**出典を必ず添える**（事実であることを読み手が確かめられる）。

    ## 自分が書いた感想を 1 行だけ添える（2026-08-24）

    **人物の行は名前と本数しか出していない** ──「演出 末満健一（履歴 1 本）」。
    名簿は ◎ を付けた作品のクレジットから作り手を機械的に全員拾うので、1 作品あたり
    20〜50 人が入る（実データで 1,008 人／43 作品）。**そのうち誰が自分にとっての決め手
    だったかは、◎ という記号には残っていない。感想には残っている。**

    **これが感想を書く返りである**（測るためだけの入力は作らない・企画書 2 章）。
    実測では、いまの感想 5 件で**推薦 1/15 枚・興味あり 8/27 枚**に出る。**書くほど増える。**
    **お気に入りの枠には出ない** ── あの枠は「登録した名前に当たった」ことだけを理由に
    出す束で、人物・内容の理由をそもそも混ぜない（`declared_rows`）。

    **主語は作品にする**（`impressions.quote_row`）── 作品単位の評価を、その作品に
    関わった個人への評価として読ませない。

    ## 各行に「今後この理由では出さない」の押し口を付ける（2026-08-26）

    起案者の指示 ──「『なぜ出てきたか』は各項目に×ボタンをつけて不要な推薦は
    今後消せるようにしてほしい」。**新しい仕組みは作らず、既にある 2 つの除外の
    仕組みへそのままつないだ。**

    - **網 a（申告）の行は、その名前の登録を外す**（`/api/favourite {action:"remove"}`）。
      この行が出ている理由そのものが「その名前を登録したから」なので、消すべきは
      登録の側である。「出さない語」に足しても、申告（お気に入り）が勝つ規則
      （`recommend2.py`）のせいで効かない。
    - **網 b（人物）・網 c（内容）の行は、名前／語を「出さない語」に足す**
      （`/api/decline {action:"add"}`）。どちらもすでにある「見送った理由から
      拾った語を出さないにする」画面（`app._declined_html`）と同じ入口で、
      粒度（語ひとつ）もそのまま流用できる。
    """
    out = []
    for w in c.get("a", []):
        # `recommend2.py` が作る形は必ず `{kind}「{name}」` なので、崩れていない前提で割る
        m = re.match(r'^(.+?)「(.+)」$', w)
        rmbtn = (f'<button class="rsx" data-kind="{E(m.group(1))}" data-name="{E(m.group(2))}"'
                 f' title="この登録をやめる">✕</button>' if m else "")
        out.append(f'<li class="rs a"><span class="net">申告</span>{E(w)}'
                   f'<span class="src">［出典: {E(ROLE_SRC)}］</span>{rmbtn}</li>')
    for contrib, role, person, n in c.get("why_b", [])[:4]:
        # **本数を書く。** 「履歴 1 本」と「履歴 8 本」を同じ顔で並べると、偶然を好みとして読ませる
        #
        # **◎ を付けた作品だけとは言い切らなくなった**（起案者の指示・2026-08-26 ──
        # 「観れば良かった」で挙がった人名は興味ありと同じ扱いで名簿に混ぜるようにした
        # ため。この本数には、観て良かった（◎）作品だけでなく、気になった（興味あり・
        # 観ればよかった）作品も混ざっている ── どちらの割合かはここでは分からないので、
        # 「◎ を付けた作品」と言い切る文言のままにしておくと、実際より強い実績に読める
        out.append(f'<li class="rs b"><span class="net">人物</span>'
                   f'{E(role)} <b>{E(person)}</b>'
                   f'<span class="n">（◎ を付けた・気になった作品での実績・履歴 {n} 本）</span>'
                   f'<span class="src">［出典: {E(ROLE_SRC)}］</span>'
                   f'<button class="rsx" data-word="{E(person)}"'
                   f' title="この人物を理由に出さない">✕</button></li>')
    # **人物の行の直後に置く。** 引用は上の名前に紐づく事実なので、離すと何の話か分からない
    out.append(IM.quote_row([p[2] for p in c.get("why_b", [])[:4]], NOTES_BY_PERSON))
    _src, _doubt = synopsis_source(str(c["stage_id"]), c.get("synopsis") or "")
    for it in c.get("why_c", [])[:3]:
        word = it[1] if isinstance(it, (list, tuple)) and len(it) > 1 else it
        n_rated = it[2] if isinstance(it, (list, tuple)) and len(it) > 2 else None
        # **何本の記録から出た要素かを書く。** 3 本から出た語と 10 本から出た語を同じ顔で
        # 並べると、偶然を好みとして読ませる（網 B で本数を書くのと同じ理由）
        n_txt = f"（◎ を付けた作品に多い要素・記録 {n_rated} 本）" if n_rated else "（◎ を付けた作品に多い要素）"
        out.append(f'<li class="rs c{" doubt" if _doubt else ""}"><span class="net">内容</span>あらすじに '
                   f'<b>{E(word)}</b><span class="n">{E(n_txt)}</span>'
                   f'<span class="src">［出典: {E(_src)}のあらすじ］</span>'
                   f'<button class="rsx" data-word="{E(word)}"'
                   f' title="この語を理由に出さない">✕</button></li>')
    # **空の行を数えない。** 引用は無いことがあるので、`out` の中身で判定すると
    # 「理由を出せていません」が出るべきときに出なくなる
    out = [r for r in out if r]
    if not out:
        out.append('<li class="rs none">理由を出せていません</li>')
    return "".join(out)


def register_button(c: dict) -> str:
    """**上演が終わった公演を、その場で観た記録として登録するボタン。**

    起案者の指摘（2026-08-26）──「探すで CoRich の検索結果が終わった上演だと弾かれて
    しまう。終わった上演も表示して検索結果のページからも直で登録できるようにして
    ほしい」。

    **経路は「公演情報の登録」②（手で足す）と同じ `/api/add_work` にする。** 探す画面
    専用の受け口を新しく作ると、同じ「観た記録を足す」操作が 2 通りの規則を持つことに
    なる ── どちらから足しても、できる記録は同じでなければならない。

    **見た目は三択（`buttons`）と同じ `.btns` に載せる**（起案者の指摘・2026-08-26 ──
    「ボタンのデザインをサイトとあったものにして」）。以前はここだけ素の `<button>`
    のままで、丸い錠剤形（`.btns button`／`.rb button` の規約）を持つ他の押し口と
    違って見えていた。
    """
    d = _start(c.get("period") or "")
    return (f'<span class="btns"><button data-add-found="{E(c["stage_id"])}"'
            f' data-title="{E(c["title"])}" data-date="{E(d)}"'
            f' data-venue="{E(c.get("theater") or "")}">'
            f'{IC.ico("plus")}観た記録として登録する</button><span class="said"></span></span>')


def buttons(stage_id, *, hidden: bool = False) -> str:
    """三択。**押した本人に返りがあるものだけを置く**（企画書 2 章・検証 021）。

    - **すでに持っている** → 観る予定に移り、推薦枠から出る
    - **興味あり** → 追いかける枠に入る（上演日の近い順。買い忘れを防ぐ用途）
    - **興味なし** → 「その他」に畳まれ、二度と推薦枠に出ない

    **「知っていたか」は聞かない**（2026-08-20 に撤回）。1 つのボタンに「何をしてほしいか」と
    「知っていたか」の 2 軸が混ざり、**両方に当てはまる利用者がどちらを押すか決まらない。**

    **`hidden` は、答え直す口として出すときに立てる**（`ticket` の `interest` の分。
    起案者の指摘・2026-08-26 ── 「興味あり」の一覧に、答え直す以外の役目が無い三択が
    毎行フルサイズで出ていた）。
    """
    # **ボタンには押した結果だけを書く。** 「もぎる」という言い方は、この仕組みが
    # チケットの絵に付けた呼び名であって、**利用者がふだん使う言葉ではない**
    # （起案者の指示・2026-08-24）。動き（`.torn`）はそのまま残す ── 形で結果が
    # 分かることと、その動きに名前を付けて画面に書くことは別である
    return (f'<span class="btns"{" hidden" if hidden else ""} data-stage="{E(stage_id)}">'
            '<button data-v="owned">すでに持っている</button>'
            '<button data-v="interest">興味あり</button>'
            '<button data-v="nointerest">興味なし</button>'
            '<span class="said"></span></span>')


def why_note(stage_id, note: str = "", *, open_: bool = False, ask: bool = False) -> str:
    """**「興味あり」に添える理由。任意である。**

    **測るためだけの入力にしない**（企画書 2 章）。書くと返りがある ── **文に出てきた
    名前が「お気に入り」への昇格候補として出てくる**ので、登録すればその人・その団体の
    公演が件数の制限なしに新着に出るようになる（`tools/taguri/reasons.py`）。

    **押す前は出さない。** 15 件すべてに空欄を並べると、読む画面が書く画面に見える。
    もぎった直後にだけ開く。

    **すでにもぎった公演の一覧（興味あり）では見せ方を変える**（`ask`）。そこは
    「なぜ気になったのか」を読み返す場所なので、**書いてあるものは文として出し**、
    書いていないものは空欄ではなく**押すと開く 1 つのボタン**にする ── 入力欄が 19 個
    並ぶと、追いかける一覧が入力用紙に見える。
    """
    box = (f'<div class="why-note" data-stage="{E(stage_id)}"{"" if open_ else " hidden"}>'
           f'<label>なぜ気になったか<span class="opt">任意</span></label>'
           f'<textarea placeholder="例: 作り手30の脚本だから／作品4に興味がある／'
           f'題材が題材3そう" rows="2">{E(note)}</textarea>'
           f'<div class="wn-foot"><span class="hint">書いた文に出てきた名前は、'
           f'「お気に入り」に登録する候補として出てきます</span>'
           f'<span class="said"></span></div></div>')
    if open_ or not ask:
        return box
    # **書いたものは、入力欄ではなく文として読み返せる形で出す。** 追いかけている 19 件の
    # うち 16 件には理由が書かれている ── それを textarea のまま並べると、読みに来た画面が
    # 入力用紙になる。**読む形で出し、直したいときだけ入力欄に変える。**
    if note:
        head = (f'<div class="wnr"><span class="wnl">なぜ気になったか</span>'
                f'<span class="wnt">{E(note)}</span>'
                f'<button class="wnb" data-why="1">書き直す</button></div>')
    else:
        head = ('<button class="wnb" data-why="1">なぜ気になったかを書く'
                '<span class="opt">任意</span></button>')
    return f'<div class="wnw">{head}{box}</div>'


def no_note(stage_id, note: str = "", *, hidden: bool = False) -> str:
    """**「興味なし」に添える、見送った理由。任意で、折りたたんで出す。**

    起案者の指示（2026-08-24）──「興味なしも、なんで興味がないのか任意で入力できると
    良い。ただ、書く頻度はあまり少ないため、折りたたんで記述欄を表示してほしい」。

    ## 折りたたむ ── 書く頻度が低い入力を、開いた欄で置かない

    興味ありの理由欄はもぎった直後に開くが、**こちらは開かない。** 書く頻度が低い入力を
    開いた状態で並べると、**読む画面の面積を、ほとんど使われない欄が占める。** `<details>`
    にしたので JavaScript を要さず、閉じている状態が既定である。

    ## 返りは「あとで拾い直せること」である

    **測るためだけの入力にしない**（企画書 2 章）。この束（その他）は**消さずに残して
    ある** ── 「興味なし」の多くは好みの問題ではなく日程・場所・予算の都合なので、消すと
    「観ればよかった」を後から拾えないからである。ところが**残っているのは題名と日程だけ
    で、どれが都合で見送ったものかが分からなかった。** 書いた理由は畳んだ見出しにその場で
    出るので、**一覧を開けば、都合で見送ったものだけを目で拾える。**

    ## 興味ありの理由とは別の列に入れる

    **`note` に入れてはいけない。** あちらは文に出てきた名前を「お気に入り」への昇格候補
    にする列なので（`tools/taguri/reasons.py`）、**「この人が出ているから観たくない」と
    書いた名前が登録候補として出てくる。** 列を分ければ、否定の文を読み分ける必要が無い。
    """
    has = bool((note or "").strip())
    summary = (f'見送った理由<span class="nnv">{E(note)}</span>' if has
               else '見送った理由を書く<span class="opt">任意</span>')
    return (f'<details class="nn" data-stage="{E(stage_id)}"{" hidden" if hidden else ""}>'
            f'<summary>{summary}</summary>'
            f'<textarea data-nono="{E(stage_id)}" rows="2" placeholder="例: 日程が合わない／'
            f'会場が遠い／予算が合わない／この題材は好みではない">{E(note)}</textarea>'
            f'<div class="wn-foot"><span class="hint">この一覧は消さずに残してあります。'
            f'理由を書いておくと、あとで「観ればよかった」を拾い直すときに、'
            f'都合で見送ったものと好みに合わなかったものを見分けられます</span>'
            f'<span class="said"></span></div></details>')


def perf_dates(w: dict, limit: int = 3) -> str:
    """観に行った回の上演日を、**年から書く。**

    起案者の指示（2026-08-24）──「観た公演の評価、はそれが何年に観たやつなのかまで
    年月日で書いたほうがいい。結構過去のもあるので」。

    **年が要るのは、評価待ちに何年も前の公演が並ぶからである。** 実データでは 2022 年から
    2026 年までが同じ一覧に混ざっており、**月日だけでは「どの公演のことか」を思い出せない。**

    **書くのは、券を持っていた回の上演日である**（作品の上演期間の最終日ではない）──
    「2025-11-08 まで」と出していたのは公演が終わる日で、本人が客席に居た日とは限らない。
    **「行かなかった」と答えた回は入れない**（`attended`）。

    **「観た日」とは書かない。** この行には「行かなかった」と答えられる口があるので、
    観たことを前提にした言葉を焼き付けない（耳と同じ約束）。
    """
    ds = sorted({(s.get("date") or "")[:10] for s in (w.get("shows") or [])
                 if s.get("date") and s.get("attended", True)})
    if not ds:
        # 手で足した記録は回を持たない。作品の側の日付で代わりを出す
        d = (w.get("first_date") or w.get("last_date") or "")[:10]
        ds = [d] if d else []
    if not ds:
        return "上演日が分かりません"
    out, prev_y = [], ""
    for d in ds[:limit]:
        try:
            y, m, dd = d.split("-")
        except ValueError:
            continue
        # **年は変わったときだけ書き直す。** 同じ年の 3 回に年を 3 回書くと、
        # 読む側が数字を追うことになる
        out.append((f"{int(y)}年" if y != prev_y else "") + f"{int(m)}月{int(dd)}日")
        prev_y = y
    if not out:
        return "上演日が分かりません"
    txt = "・".join(out)
    if len(ds) > limit:
        txt += f" ほか {len(ds) - limit} 回"
    return txt


def wait_row(w: dict) -> str:
    """評価待ちの 1 行。**通知を送らない構成なので、ここが唯一の催促である**（企画書 2 章）。

    **評価は作品ごとに 1 つで、観た回ごとには聞かない**（企画書 4 章）── 回ごとに聞くと
    答える中身が「その回の出来」に変わり、好みの証拠にならない。観た回数は事実として添える。

    ## 感想の欄を、評価を押した直後に置いた（2026-08-24）

    起案者の指示で「先に感想が集まる形を作る」ほうを選んだ（等高線の可視化は入力が
    足りないと測ったため）。**感想が 95 件の評価に対して 8 件しか無かったのは、動機では
    なく置き場所の問題である** ── 欄は「記録を見返す」の行にしか無く、**評価そのものを
    付けるこの行には無かった。観た帰りに ◎ を押す瞬間が、いちばん言葉が出てくる瞬間**な
    のに、そこに置いていなかった。

    **押すまで開かない**（`impressions.wait_note_html`）。15 行ぶんの入力欄が最初から
    並んでいると、評価を付ける画面が「書かされる画面」に見える。
    """
    n = w.get("times") or 1
    times = f"・{n} 回観た" if n > 1 else ""
    key = E(w["work_key"])
    return wait_shell(
        w, f'<span class="wt">{E(w["title"])}</span>'
           f'<span class="wm">上演日 {E(perf_dates(w))}{E(times)}</span>'
           f'<span class="rb" data-work="{key}">'
           + "".join(f'<button data-v="{v}">{v}</button>' for v in ("◎", "○", "△", "×"))
           + '<button data-v="まだ判断できない" class="pend">まだ判断できない</button>'
             '<span class="said"></span></span>'
           + _not_seen(w)
           + IM.wait_note_html(w["work_key"], w.get("note_impression") or ""))


def wait_shell(w: dict, body: str) -> str:
    """評価待ちの 1 行の外枠 ── **耳・ミシン目・本文の 3 列。中身だけを差し替える。**

    **同じ形の行が 2 か所にある。** 評価待ち（`wait_row`）と、◎ に感想を書き足す束
    （`impressions.pending_html`）である。**外枠を関数にしていなかったので、片方だけが
    古い形で残っていた** ── `.wait` を 3 列に組み替えたとき（「評価待ちの行も、もぎられる
    形にする」）に感想の束を直しておらず、**題名と日付がくっつき、入力欄が題名の長さで
    左右にずれる**崩れた行になっていた（起案者の指摘・2026-08-24）。

    **崩れたのは、余白が `.wbody` に付いているからである。** `.wait` は
    `display:flex` の 3 列で、間隔と余白は本文の側（`.wbody`）が持つ。`.wbody` を
    省いて `.wait` の直下に文と入力欄を並べると、**間隔 0 の flex 項目が横に並ぶ。**
    """
    return (f'<div class="wait">{_wait_stub(w)}'
            f'<span class="wperf" aria-hidden="true"></span>'
            f'<div class="wbody">{body}</div></div>')


def _wait_stub(w: dict) -> str:
    """評価待ちの 1 行に付ける耳。**もぎられる側である。**

    起案者の指示（2026-08-24）──「評価し終わったあとにもぎるアニメーションを付ける」。
    **半券がもぎられるのは観に行ったときであって、券を選んでいるときではない。**
    推薦の枠でもぎる動きを出していたのは、まだ買ってもいない公演だった。

    **耳に置くのは事実だけである**（`_stub` と同じ約束）。飾りの文字は書かない。
    出すのは上演日で、**「観た日」とは書かない** ── この行には「行かなかった」と
    答えられる口があるので、観たことを前提にした言葉を耳に焼き付けられない。

    **同じ日付が行の中にも出ている**ので、耳は `aria-hidden` にする。読み上げでは
    日付が 2 度読まれるだけになる。
    """
    # **年を耳にも出す**（起案者の指示・2026-08-24）── 月日だけでは、2022 年の公演と
    # 2026 年の公演が同じ顔で並ぶ。**耳はいちばん先に目に入る場所**なので、ここに年が
    # 無いと、行の文まで読まないとどの年か分からない
    ds = sorted({(s.get("date") or "")[:10] for s in (w.get("shows") or [])
                 if s.get("date") and s.get("attended", True)})
    d = (ds[0] if ds else (w.get("first_date") or w.get("last_date") or "")).strip()
    ms = re.findall(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", d)
    if ms:
        y, md = ms[0][0], f"{int(ms[0][1])}/{int(ms[0][2])}"
    else:
        y, md = "", "未定"
    lab = "上演日"
    return (f'<span class="wstub" aria-hidden="true">'
            + (f'<span class="sy">{E(y)}</span>' if y else "")
            + f'<b>{E(md)}</b><span class="sk">{E(lab)}</span></span>')


def _not_seen(w: dict) -> str:
    """評価待ちから外す口。**気づいた場所に置く**（起案者の指示・2026-08-24）。

    ## 理由を 2 つに書き分ける

    **「券を買ったが行かなかった」と「舞台ではないものが取り込まれた」は別のことである。**
    前者は記録として正しく（買った事実は残る）、後者は記録そのものが間違っている。
    **1 つのボタンにまとめると、行かなかった公演が記録から消える** ── 観ていないのに買った
    ことを、後から数えられなくなる。**両方に当てはまる記録は無い**ので、どちらを押すかは
    迷わない。

    ## 畳んで置く

    押す頻度の低い口である。15 行すべてに開いた選択肢を並べると、**評価を付ける画面が
    「外す画面」に見える**（「興味なし」の理由欄と同じ判断）。`<details>` なので
    JavaScript を要さず、閉じているのが既定である。

    ## 手で足した記録には、行かなかったを出さない

    回（購入）を持たないので `attendance` に書けない。**押せるのに記録されない口を作らない**
    ので、その記録には「取り消す」だけを出す。
    """
    has_shows = bool(w.get("shows"))
    skip = (f'<button data-unseen="{E(w["work_key"])}">行かなかった'
            f'（券は買いましたが、観ていません）</button>' if has_shows else "")
    return (f'<details class="ns"><summary>この公演を観ていない</summary>'
            f'<div class="ns-body">'
            f'<p>どちらもあとで戻せます。'
            + ("" if has_shows else
               "<b>この記録は手で足したものなので、「行かなかった」は付けられません。</b>")
            + '</p>'
            + skip
            + f'<button class="danger" data-drop="{E(w["work_key"])}">'
              f'舞台ではないものが取り込まれています</button>'
            f'<span class="said"></span></div></details>')


def _stub(rank, c: dict, mark: str = "") -> str:
    """チケットの耳（もぎる側）。**「入場券」とは書かない。**

    起案者の指示（2026-08-24）──「チケットデザインに『入場券』って文字は不要。
    ユーザーに誤解を与えるような文字は明記してはいけない」。

    **形は券に似せるが、券に見える文字は置かない。** 「入場券」と縦に入れると、この 1 枚が
    本当の券（買った証し・入場できる証し）だと読める余地が出る。**まだ買っていない公演を
    並べる画面なので、その誤解はそのまま損害になる。**

    **代わりに耳へ出すのは、もぎる前に本人が知りたい 1 つの日付**である。飾りの文字を
    別の飾りの文字に取り替えたのではなく、**飾りだった場所を事実に替えた。**

    **どの日を出すかは、今日から見て決める。** まだ始まっていなければ初日を出し、
    すでに始まっていれば**間に合う最後の日**を出す ── 始まっている公演に「初日」と
    書くと、過ぎた日を目安の日として読ませることになる。
    """
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", c.get("period") or "")
    if not ms:
        md, lab = "未定", "上演日"
    else:
        first, last = date(*map(int, ms[0])), date(*map(int, ms[-1]))
        today = date.today()
        # **「初日」と書けるのは、初日がまだ来ていないときだけである。** すでに始まって
        # いる公演に「初日」と書くと、過ぎた日を目安の日として読ませる。**始まっている
        # ものに要るのは、間に合う最後の日**なので、そちらを出す
        if first >= today:
            md, lab = f"{first.month}/{first.day}", ("上演日" if first == last else "初日")
        elif last >= today:
            md, lab = f"{last.month}/{last.day}", "最終日"
        else:
            md, lab = f"{last.month}/{last.day}", "終了"
    # **順位は推薦の枠にしか無い。** 興味あり・お気に入りは順位を付けない束なので
    # （企画書 1 章）、番号を振ると付けていない順位を付けたように見える
    n = f'<span class="sn">No.{rank:02d}</span>' if rank else mark
    return (f'<div class="stub" aria-hidden="true">{n}'
            f'<span class="sd"><b>{E(md)}</b><span class="sk">{E(lab)}</span></span></div>')


def declared_rows(c: dict) -> str:
    """お気に入りの 1 枚に出す「なぜ出てきたか」。**当たった申告だけを出す。**

    **推薦の理由（人物・内容）を混ぜない。** お気に入りは順位を付けないお知らせであり、
    出てきた理由は「その名前を登録したから」の 1 つに尽きる（企画書 1 章）。同じ枠に
    網ごとの理由を並べると、**順位を付けていないものが順位付きの推薦に見える。**
    """
    a = c.get("a") or []
    if not a:
        return ('<li class="rs none">お気に入りに登録した名前に当たった公演ですが、'
                'どの登録に当たったかを取れていません</li>')
    return "".join(f'<li class="rs a"><span class="net">お気に入り</span>'
                   f'登録した{E(w)}の公演です'
                   f'<span class="src">［出典: {E(ROLE_SRC)}］</span></li>' for w in a)


def syn_block(c: dict) -> str:
    """あらすじの枠を組む。**枠ごと組み直せるようにしてある** ── 内容を手で入れた直後に、
    この枠だけを差し替えて画面へ出すためである（`/api/hand_theme`）。

    出る形は 3 通りある。**「取れませんでした」で終わらせない** ──
    [検証 048](../../docs/verification/048-empty-and-cap.md) で、取れなかった 344 件のうち
    45% は本文がどこにも書かれておらず、**抽出をどう直しても埋まらない**と分かった。
    残る道は本人が入れることなので、**取れなかった枠には必ず入れ口を置く。**
    """
    syn = (c.get("synopsis") or "").strip()
    hand = c.get("hand") or {}
    by_hand_syn = c.get("synopsis_by") == "手入力"
    by_hand_tags = c.get("themes_by") == "手入力"
    # **公演ページから読み取った題材を「#」のタグで並べる**（起案者の指示 2026-08-25）。
    # **畳む対象の外に置く。** あらすじは 3 行で畳むが、タグは 1〜2 行に収まるうえ、
    # **並べて見比べるときにいちばん先に目に入ってほしいのがここ**である ──
    # 本文を読まなくても「どんな話か」が分かるのが、この一覧でタグを出す理由である。
    tags = [str(w).strip() for w in (c.get("themes") or []) if str(w).strip()]
    tag_html = ('<div class="tags">'
                + "".join(f'<span class="tag">#{E(w)}</span>' for w in tags)
                + (' <span class="tag mine">自分で入れた分</span>' if by_hand_tags else "")
                + "</div>") if tags else ""
    form = hand_form(c, hand)
    if syn:
        if by_hand_syn:
            # **手で入れた文に、公演ページとの照合を掛けない。** 照合は「モデルが本文に
            # 無いことを書いていないか」の検査で、本人が入れた文には当たらない
            cls, cite = "", '<span class="src">［自分で入れた内容です］</span>'
        else:
            src, doubt = synopsis_source(str(c["stage_id"]), syn)
            cls = " doubt" if doubt else ""
            cite = (f'<span class="src">［出典: {E(src)}］</span>' if not doubt
                    else f'<span class="src warn">［出典: {E(src)} ── '
                         f'この公演自身のページに同じ本文がありません。'
                         f'別の公演の紹介が混ざっている可能性があります］</span>')
        # **3 行で畳む。** 15 枚を並べる一覧で 4〜5 行のあらすじを全部開くと、
        # 1 枚が画面の高さを超えて「並べて見比べる」ができなくなる。**消さずに畳む**
        return (f'<div class="syn{cls}" data-stage="{E(c["stage_id"])}">'
                f'<p class="txt">{E(syn)}</p>{tag_html}{cite}'
                f'<button class="mrb" data-more="1">続きを読む</button>{form}</div>')
    if tags:
        # **あらすじが無くてもタグは出る。** 筋書きを持たない催し（落語会・フェス・
        # オムニバス）や、宣伝文しか載っていないページがこれに当たる（検証 048）。
        # **「取れませんでした」だけを出していた枠に、取れたものを出す。**
        head = ("あらすじは公演ページに載っていません。次の題材を自分で入れました。"
                if by_hand_tags else
                "あらすじは公演ページに載っていませんでしたが、内容の手がかりは読み取れました。")
        return (f'<div class="syn part" data-stage="{E(c["stage_id"])}">{head}'
                f'{tag_html}{form}</div>')
    return (f'<div class="syn no" data-stage="{E(c["stage_id"])}">'
            f'あらすじを取れませんでした（公演ページに本文がありません）{form}</div>')


# **手で入れられる出演者・作り手の欄。** `tools/taguri/app.py` の `HAND_FIELDS`
# （日記帳の「手で入れる」）と同じ役職名・同じ形にする ── 役職名がずれると
# `measure_nets.parse_credits` が読み分けられない
CAST_FIELDS = (
    ("出演", "出演者", "1 行に 1 名でも、読点や中黒で区切っても構いません"),
    ("演出", "演出", ""),
    ("脚本", "脚本・原作・翻訳", ""),
    ("スタッフ", "そのほかの作り手", "「美術：〇〇」のように役職を添えると、"
     "役職ごとに数えられます。役職が分からないものは名前だけで構いません"),
)


def hand_form(c: dict, hand: dict) -> str:
    """**内容・クレジットを修正する口。**（起案者の問い 2026-08-25 ──「『あらすじを
    取れませんでした』の作品を自分で追加することはできる？」／起案者の指摘・
    2026-08-26 ──「corich とかにもちゃんと出演者情報が載ってるのに拾うのに
    失敗している」）

    ## あらすじ・題材と、出演者・作り手で、重なり方が違う

    **あらすじ・題材は、入れると公演ページの分に置き換わる**（`hand_themes.blend`）。
    1 つの公演に説明文は 1 つしか出せないので、手で入れた分があればそちらを
    正としを採る。**出演者・作り手は、公演ページの分に足す**（`hand_themes.merge_fields`、
    日記帳の「手で入れる」と同じ規則）── 役職ごとに 1 行しか拾えない抽出があり、
    「取れている」役職でも全員は取れていないことがあるので、消さずに補う。

    **常に出す。** 前は「機械が取れている公演には出さない」（空いている枠を
    埋める口）だったが、**機械の抽出が間違っていることもある**ので、
    直す口としても使えるように、機械が取れているかどうかに関わらず出す。

    **見出しは「内容を自分で入れる・直す」→「内容・クレジットを修正する」に改めた**
    （起案者の指示・2026-08-26）。出演者・作り手を足す機能（2026-08-26）を
    この口に載せた後も見出しの言葉が「あらすじ・題材」寄りのままだったので、
    クレジットも直せることが見出しから分かる形にした。
    """
    words = "、".join((w.get("word") or "") if isinstance(w, dict) else str(w)
                     for w in (hand.get("words") or []))
    hf = hand.get("fields") or {}
    cast_boxes = "".join(
        f'<label class="hl">{E(label)}'
        + (f'<span class="hn">{E(hint)}</span>' if hint else "")
        + f'<textarea class="ht-cast" data-hand="{E(field)}"'
          f' rows="{3 if field == "スタッフ" else 2}">{E(hf.get(field) or "")}</textarea></label>'
        for field, label, hint in CAST_FIELDS)
    return f"""<details class="handt"><summary>内容・クレジットを修正する</summary>
<p class="lead"><b>あらすじ・題材は、入れると公演ページの分に置き換わります。</b>
出演者・作り手は、公演ページの分に足されます（消えません）。</p>
<label class="hl">題材
 <input class="ht-w" type="text" value="{E(words)}" placeholder="落語、人情、女形"
  aria-label="題材"></label>
<span class="hn">読点か空白で区切ってください。おすすめの並べ替えに使っているのは
 題材の語です。</span>
<label class="hl">あらすじ
 <textarea class="ht-s" rows="3" placeholder="別の場所で見つけた紹介文を貼ってください"
  aria-label="あらすじ">{E(hand.get("synopsis") or "")}</textarea></label>
<span class="hn">貼ると、その文章から題材も読み取ります（読み取りには少し時間がかかります）。</span>
<label class="hl">公演ページの URL
 <input class="ht-u" type="url" value="{E(hand.get("url") or "")}"
  placeholder="https://" aria-label="公演ページの URL"></label>
<span class="hn">公式サイトの欄が SNS やリンク集を指しているときは、ここに公演ページの
 URL を入れてください。取りに行って読み取ります。</span>
{cast_boxes}
<button class="hb" data-handtheme="{E(c["stage_id"])}">保存する</button></details>"""


def ticket(c: dict, *, rank=None, mode: str = "recommend", note: str = "",
           why_html: str = "", my_tickets: list[dict] | None = None) -> str:
    """1 公演を 1 枚のチケットの形で出す。**推薦・興味あり・お気に入りで同じ枠を使う。**

    起案者の指示（2026-08-24）──「お気に入りのページの公演一覧も、推薦ページと同じような
    情報（値段やあらすじ、出演者など）を載せて、チケットっぽいデザインにして」。

    **同じ枠にした理由は、読む側がする判断が同じだからである。** 推薦であれお知らせであれ、
    観るかどうかを決めるのに要るのは**値段・日程・あらすじ・出演者という同じ事実**である。
    お気に入りだけ 1 行に潰していたのは、**出どころが違うという作り手側の都合**であって、
    読み手の都合ではなかった。実際、お気に入りの新着 19 件はどれも値段・あらすじ・出演者を
    持っている（`recommend2.json`）── 出せる事実を、束の名前を理由に隠していた。

    **性質が本当に違うのは「なぜ出てきたか」の欄と、押せるかどうかだけである。**

    | mode | 耳 | なぜ出てきたか | 押し口 |
    |---|---|---|---|
    | `recommend` | 順位と初日 | 網ごとの理由 | 三択と、理由の欄 |
    | `interest` | 初日だけ | 網ごとの理由と、自分が書いた理由 | 三択と、理由の欄 |
    | `favourite` | 初日だけ | 当たった申告だけ | **無し（読むだけ）** |
    | `owned` | 初日だけ | 網ごとの理由（推薦から来た分） | **無し（読むだけ）** |

    ## 「すでに持っている」に三択を置かない理由（2026-08-25）

    起案者の指摘 ──「もうチケットを買っていてこれから観に行く公演についてまとめられて
    いるページがない」。**この束はもう答えが決まっている**（券を持っている）ので、
    お気に入りと同じ理由で三択を置かない ── 「興味あり」「興味なし」を押しても、
    束の割り振りは「持っている」を最初に見るので何も動かない。**理由の欄
    （なぜ気になったか・見送った理由）も、答える前提の入力なので一緒に外した。**
    押せるのは「行く日を入れる」だけで、それはこの画面ではなく暦・チケット一覧の
    共通の道具（`stage_calendar.ticket_manager_html`）が受け持つ。

    ## お気に入りに三択を置かない理由

    起案者の判断（2026-08-24）──「お気に入りは読むだけのお知らせのページで良いです」。

    **「興味なし」は押しても何も起きていなかった。** 束の割り振りは「持っている →
    興味あり → **お気に入りに当たっている** → 興味なし」の順に見るので、お気に入りの
    公演は「興味なし」に届く前にお気に入りへ戻る。実データで**画面から 3 件押されて
    いたが、3 件とも一覧に残っていた**（`source='screen'`）。見送った理由の欄まで開く
    ので、書いた文も効かないまま残っていた。

    **「興味あり」「すでに持っている」は効いていた**（追いかけている 35 件のうち 24 件が
    お気に入り由来、うち 12 件はこの画面のボタンから）。**それでも外す** ── 起案者が
    この画面の役割を「読むだけのお知らせ」に決めたためである。**代わりの経路は用意して
    いない**（お気に入りの新着を「興味あり」のページへ送る手段は無くなる）。
    """
    # **取れなかった欄の器を出さない。** 団体と都道府県は一覧のページにしか無いので、
    # 探して拾った公演では空になる ── そのまま組むと「／」と「（）」だけが残り、
    # **何かが入るはずの場所が壊れているように見える**
    meta = "".join(x for x in (
        f'<span class="grp">{E(c.get("group") or "")}</span>' if c.get("group") else "",
        '<span class="sep">／</span>' if c.get("group") and c.get("theater") else "",
        E(c.get("theater") or ""),
        f'<span class="pref">（{E(c.get("pref") or "")}）</span>' if c.get("pref") else "",
    ) if x)
    t_html = schedule_html(c)
    syn_html = syn_block(c)
    onsale = c.get("onsale") or "確認できず"
    cls = "warn" if onsale == "確認できず" else ("soon" if "発売" in onsale and onsale != "発売済み" else "ok")
    # **探した結果は「なぜ出てきたか」ではなく「ヒットした箇所」を出す。**（言い方を
    # 起案者の指示で「当たったところ」→「ヒットした箇所：」に変えた・2026-08-26）
    # 探す画面から来た 1 枚は、推薦の理由で出ているのではなく、**打った言葉に当たった
    # から出ている。**
    #
    # **カードの上に出す。** 以前はあらすじ・出演者より下（`.act` の直前）にしか出て
    # いなかったが、**探した結果を読む人がいちばん先に知りたいのは「なぜこれが出たか」**
    # である ── あらすじまで読んで初めて分かる場所には置かない（起案者の指示・
    # 2026-08-26 ──「各カードの上に明記してほしい」）。**推薦・お気に入りの理由
    # （`why_html` が無いとき）は元の場所のまま**にする ── そちらは「読んだ結果として
    # 納得する」ためのもので、読む前に知る必要があるものではない。
    top_why = ""
    if why_html:
        top_why = (f'<div class="whyh top">{IC.ico("eye", 14)}ヒットした箇所：</div>'
                   f'<ul class="why top">{why_html}</ul>')
    else:
        whyh = "なぜお知らせしているか" if mode == "favourite" else "なぜ出てきたか"
        why = declared_rows(c) if mode == "favourite" else reason_rows(c)
    # **もぎった 1 枚は、傾けずに印を付ける。** 押した瞬間に耳を傾ける動き（`.torn`）は
    # **一瞬だから意味がある**もので、19 枚すべてを傾けたまま並べると演出ではなく体裁に
    # なる。しかも耳を薄くして傾けると、**この画面でいちばん要る値（間に合う最後の日）が
    # 読めなくなる。** 済んだことは耳の上の印で出す
    # **お気に入りの耳には封蝋を押す。** 順位を付けない束なので番号の場所が空いていた ──
    # **空けておくより、その 1 枚が約束で出ていることを言う印を置く**
    mark = (f'<span class="sn done">{IC.ico("check", 15)}</span>' if mode == "interest"
            else '<span class="wax" aria-hidden="true"></span>' if mode == "favourite"
            else "")
    # **「興味あり」の一覧では、三択を答え直す口として畳む。** ここに並ぶ 1 枚はどれも
    # すでに「興味あり」を押した後なので、三択がフルサイズで出続ける理由が無い ──
    # 「評価一覧」の「評価を押し直す」と同じ形にそろえる（起案者の指摘・2026-08-26）
    if mode in ("favourite", "owned"):
        act_btns = ""
    elif mode == "interest":
        act_btns = ('<button class="wnb" data-btns-open="1">回答を変える</button>'
                    + buttons(c["stage_id"], hidden=True))
    elif mode == "ended":
        # **上演が終わった公演には、三択ではなく登録の口を出す。**「興味あり」等は
        # これから観るかどうかを決める押し口なので、終わった公演には意味が無い
        act_btns = register_button(c)
    elif mode == "ended_added":
        # **すでに登録した公演には、押し口ではなく結果を出す。**（起案者の指摘・
        # 2026-08-26 ──「実際に CoRich の検索から...ボタンを押して追加した公演には、
        # 『追加済みです』などを赤文字で出して」）。ボタンを出したままだと、
        # もう一度押せてしまい、二重に登録しようとして「もう登録してある」の
        # エラーだけが返る ── 押す前に、すでに済んでいることを言い切る。
        act_btns = '<span class="added-note">追加済みです</span>'
    else:
        act_btns = buttons(c["stage_id"])
    # **公式サイトへの導線を、ポスターの下に立てる**（起案者の指摘・2026-08-26 ──
    # 「もうちょっと主張してほしい」）。**カードの下端の文字だけの 1 行は、
    # 三択やあらすじを読んだ先にあって見落とされやすい。** ポスターは絵として先に
    # 目に入るので、その真下に置けば「この絵の公演を見に行く」動きに沿う。
    # URL が無いときは何も出さない ── その旨は下の `.act` にだけ書く（1 か所で言えば足りる）。
    poster_html = poster(c["stage_id"], c.get("home_stage_id"))
    site_btn = (f'<a class="sitebtn" href="{E(c["url"])}" target="_blank" rel="noopener noreferrer">'
                f'{IC.ico("link", 14)}公式サイト</a>' if c.get("url") else "")
    pcol = (f'<div class="pcol">{poster_html}{site_btn}</div>'
            if poster_html or site_btn else "")
    nolink = "" if c.get("url") else '<span class="nolink">公式サイトの URL がありません</span>'
    act = (f'<div class="act">{nolink}{act_btns}</div>' if nolink or act_btns else "")
    # **実際に持っている券の日時を、カードにも出す**（起案者の指摘・2026-08-26 ──
    # 「購入済み公演には、実際にチケットを持っている公演の日時も表示して」）。
    # 「行く日を入れる」道具（暦・購入済み公演の下の帯）には出ていたが、
    # カード自身は上演期間（`.when`）までしか言っておらず、**何回もある公演で
    # どの回の券を持っているかがカードだけでは分からなかった。**
    mytix_html = ""
    if mode == "owned":
        # **確定前の券には、確定・違うの押し口を付ける。**（起案者の指示・2026-08-26
        # ──「『観劇日を追加する』のボタンを消して、各公演ごとに観劇日を追加できる
        # 欄を設けてください」）。もとは公演を選ぶポップアップの中にあった一覧
        # （`stage_calendar._ticket_li`）と同じ操作を、カード自身に持たせる。
        # **押し口には券自身の stage_id を持たせる**（`t.get("sid")`）── 券は
        # このカードの代表 stage_id とは違う会場に付いていることがある
        # （`app._react_groups` の docstring・フタマツヅキ・ミス・サイゴン）。
        def _mt_row(t: dict) -> str:
            tm = f' {E(t["time"])}' if t.get("time") else ""
            sid, dd, tt = (E(str(t.get("sid") or c.get("stage_id") or "")),
                           E(t["date"]), E(t.get("time") or ""))
            if t.get("confirmed"):
                note, btns = "", f'<button data-mt-del="{sid}" data-date="{dd}" data-time="{tt}">取り消す</button>'
            else:
                note = "（未確定）"
                btns = (f'<button data-mt-ok="{sid}" data-date="{dd}" data-time="{tt}">確定する</button>'
                        f'<button data-mt-del="{sid}" data-date="{dd}" data-time="{tt}">違う</button>')
            return (f'<span class="mt-row{"" if t.get("confirmed") else " un"}">{int(t["date"][5:7])}月'
                    f'{int(t["date"][8:10])}日{tm}{note} {btns}</span>')
        lo, hi = _period_start(c.get("period") or ""), _period_end(c.get("period") or "")
        add_form = (
            '<span class="mt-add">'
            f'<input type="date" class="mt-d" aria-label="行く日"'
            + (f' min="{lo.isoformat()}"' if lo else "")
            + (f' max="{hi.isoformat()}"' if hi else "") + '>'
            '<input type="time" class="mt-t" aria-label="時刻（任意）">'
            f'<button data-mt-add="{E(str(c["stage_id"]))}">{IC.ico("plus", 13)}行く日を追加</button>'
            '<span class="said"></span></span>')
        rows = "".join(_mt_row(t) for t in (my_tickets or []))
        mytix_html = f'<div class="mytix"><b>行く日</b>{rows}{add_form}</div>'
    return f"""<article class="ticket {E(mode)}" data-stage="{E(c["stage_id"])}">
{_stub(rank, c, mark)}
<div class="perf" aria-hidden="true"></div>
<div class="body">{pcol}
<div class="main">
 <h3>{E(c["title"])}</h3>
 {top_why}
 <div class="meta">{meta}</div>
 {mytix_html}
 <div class="when">{period_label(c.get("period", ""), c.get("days", 0))}
  <span class="price">{E(c.get("price") or "料金を取れませんでした")}</span></div>
 {t_html}
 <div class="sale"><span class="pill {cls}">{E(onsale)}</span></div>
 {cast_block(c)}
 {syn_html}
 {'' if top_why else f'<div class="whyh">{IC.ico("eye", 14)}{whyh}</div><ul class="why">{why}</ul>'}
 {act}
 {'' if mode in ("favourite", "owned", "ended", "ended_added") else why_note(c["stage_id"], note, ask=(mode == "interest"))}
 {'' if mode in ("favourite", "owned", "ended", "ended_added") else no_note(c["stage_id"], hidden=True)}
</div></div></article>"""


def card(i: int, c: dict) -> str:
    """推薦の 1 枚。**順位を耳に出す**（推薦だけが順位を持つ束である）。"""
    return ticket(c, rank=i, mode="recommend")


# ---- 判子と封蝋の版 ---------------------------------------------------------
#
# **`STYLE` を読み込む画面には、必ずこれも入れる。** CSS の `filter:url(#…)` は
# **参照先が無いとその要素ごと描かれない**（Chrome / Firefox）ので、定義を置き忘れると
# 判子が消える。データ URI で CSS の中に埋める手は Chrome が受け付けないため、
# **HTML 側に 1 枚だけ置く**しかない。
#
# **判子は高い周波数で細かく崩し、封蝋は低い周波数で大きくうねらせる。** ゴム版の輪郭は
# 縁が毛羽立つが、蝋は表面張力で丸くうねる ── 同じフィルタを使い回すと、蝋がゴム版に見える。
FILTERS = """<svg width="0" height="0" aria-hidden="true" focusable="false"
 style="position:absolute">
<filter id="tg-ink" x="-25%" y="-25%" width="150%" height="150%"
 color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency="0.58" numOctaves="3" seed="11" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="1.7"
 xChannelSelector="R" yChannelSelector="G"/></filter>
<filter id="tg-wax" x="-30%" y="-30%" width="160%" height="160%"
 color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency="0.055" numOctaves="2" seed="5" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="4.2"
 xChannelSelector="R" yChannelSelector="G"/></filter></svg>"""

STYLE = """
*{box-sizing:border-box}
:root{color-scheme:light;
 /* ---- 地と紙 ---------------------------------------------------------------
    **読むところだけを紙の色で抜き、その外側は客席の壁の色にする。** 灰に緑を寄せて
    あるのは、紙の白を際立たせるためである（黄を寄せると紙が沈む）。            */
 --plane:#e7eae6;--surf:#f8f9f6;--ink:#191b18;--ink2:#4e534d;--mute:#828880;
 --grid:#dde2d9;--base:#c2c9bd;--ring:rgba(25,27,24,.13);
 /* ---- インクは 2 本だけ ------------------------------------------------------
    **`--acc`（藍）は押せるところと書けるところにしか使わない。**
    **`--curtain`（幕のえんじ）は識別にしか使わない** ── 左の帯・年の耳・評価の印。
    以前は `--acc` の青 1 色が「押せる」「現在地」「見出しの強調」をすべて担っており、
    **青が出てくるたびに押せるかどうかを確かめることになっていた。**             */
 --acc:#26467d;--curtain:#7a1e2b;--curtain-w:#f6efe9;
 /* **お気に入りだけの色。**（起案者の指示・2026-08-26 ──「サイトで統一してお気に入り
    にはこのテーマに合う黄色（オレンジ寄りにして見やすいように）をつけて」）。
    「新しい色を増やさない」という上の決まりに対する、お気に入りだけの例外である。
    封蝋（約束の印）と同じ色にする ── 封蝋はもともと「お気に入り＝件数も条件も
    付けずに必ず出す約束」の印としてお気に入りにしか使っていないので、色を変える
    だけで済む。暦の帯（`stage_calendar.py` の `.bar.fav`）・開幕リマインドの札
    （`digest.py` の `.dgk.fav`／`.dgli.fav`）にも、この 1 つの色を差し込む。 */
 --wax:#995c0c;--wax-hi:#db9730;
 /* ---- 値の色。**意匠の色とは別に持つ** ── ◎ と × は好みの値であって飾りではない */
 --pos:#1e6b48;--neg:#8a3b3b;--good:#1e6b48;--warn:#8a6d2a;
 --s1:#2f5590;--s2:#b1592c;--s3:#1d7d59;--s4:#8a6d2a;
 --oth:#c2c9bd;--deemp:#c2c9bd;
 /* ---- 明朝。**端末にあるものだけを並べる** ── 外部からフォントを読み込むと、
    端末内のデータだけで作るという守り（企画書 5 章）が 1 か所破れる。
    **どれも無い端末ではゴシックに落ちる**ので、帳面らしさは書体ではなく
    余白・罫・日付・印で作り、書体は乗ったときに効く上乗せとして扱う。          */
 --mincho:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
 /* 判子の刷り。明るい地では紙に染むように重ね、暗い地では抜くように重ねる */
 --stamp-blend:multiply;--stamp-ink:.88}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){color-scheme:dark;
 --plane:#101210;--surf:#191c18;--ink:#eef0ec;--ink2:#b6bbb2;--mute:#7f857c;
 --grid:#2c302b;--base:#3c423b;--ring:rgba(238,240,236,.12);
 /* **暗い地では幕のえんじが沈むので明るい側へ振る。**紙も白くしない（暗い部屋で読めない） */
 --acc:#86aae8;--curtain:#b03a4a;--curtain-w:#fbf1ef;
 --wax:#cc9029;--wax-hi:#ebba59;
 --pos:#3f9a6f;--neg:#c86a6a;--good:#3f9a6f;--warn:#c9a552;
 --s1:#6f9ad8;--s2:#d07a4a;--s3:#3f9a6f;--s4:#c9a552;
 --oth:#4e534d;--deemp:#4e534d;
 --stamp-blend:screen;--stamp-ink:.94}}
:root[data-theme=dark]{color-scheme:dark;
 --plane:#101210;--surf:#191c18;--ink:#eef0ec;--ink2:#b6bbb2;--mute:#7f857c;
 --grid:#2c302b;--base:#3c423b;--ring:rgba(238,240,236,.12);
 /* **暗い地では幕のえんじが沈むので明るい側へ振る。**紙も白くしない（暗い部屋で読めない） */
 --acc:#86aae8;--curtain:#b03a4a;--curtain-w:#fbf1ef;
 --wax:#cc9029;--wax-hi:#ebba59;
 --pos:#3f9a6f;--neg:#c86a6a;--good:#3f9a6f;--warn:#c9a552;
 --s1:#6f9ad8;--s2:#d07a4a;--s3:#3f9a6f;--s4:#c9a552;
 --oth:#4e534d;--deemp:#4e534d;
 --stamp-blend:screen;--stamp-ink:.94}
body{margin:0;padding:32px 20px 72px;background:var(--plane);color:var(--ink);
 font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.7;font-size:15px}
/* **リンクの既定色を、意匠案 A のとおり藍にする。**（起案者の指摘・2026-08-25 ──
   「デザイン案を見直して。画像のページなど、デザイン案にあったデザインではなくなってる」）

   意匠案（`docs/` に置いた案 A のページ）は `a{color:var(--indigo)}` を 1 行だけ
   全体の既定として持っている。**実装のこちら側にはその 1 行が無かった** ── 各部品が
   自分でリンクの色を決める作りになっていたので、色を決め忘れた部品はブラウザの既定
   （下線つきの青）のまま表示されていた。「たどる」画面の名前のリンクがそれで、
   意匠と関係の無い色が出ていた。

   **1 か所に既定を置く。** 個別の部品が `color` を指定していれば、詳細度で
   そちらが勝つので壊れない（`.pk{color:inherit}` や `.side a{color:...}` など）。
   決め忘れた部品だけが、ここで意匠の色に落ち着く。 */
a{color:var(--acc)}
.wrap{max-width:900px;margin:0 auto}
/* ---- 見出しと題名は明朝で組む ------------------------------------------------
   **当日パンフの題名が明朝で組まれているのと同じ理由である** ── 公演の名前は読み上げる
   ものではなく眺めるものなので、字面が残る書体のほうが識別に効く。
   **押し口はゴシックのまま残す**（`button` は `font:inherit` を上書きしない）──
   明朝の押し口は文章に見えて、押せることが伝わらない。                          */
h1{font-family:var(--mincho);font-size:26px;font-weight:600;margin:0 0 4px;
 line-height:1.42;letter-spacing:.01em}
.sub{color:var(--ink2);margin:0 0 6px;font-size:14px}
.bundles{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 26px;font-size:12.5px;color:var(--ink2)}
.bundles span{border:1px solid var(--ring);border-radius:99px;padding:3px 11px}
h2{font-family:var(--mincho);font-size:18.5px;font-weight:600;margin:30px 0 6px;
 line-height:1.45}
/* **読みやすい行の長さは `ch` では作れない。** `ch` は半角数字「0」の幅を基準に
   するため、全角の日本語では 1 文字が「1ch」の約 2 倍になり、`74ch` は実際には
   全角 37 字ほどしか入らない（起案者の指摘 2026-08-26 ──「なぜか途中で改行され
   てしまっている」）。**`em` に替えた** ── 全角文字はおおむね 1 文字 = 1em なので、
   同じ数値でも意図した文字数に近づく。この画面をまたいで同じ値を使っている場所
   （`app.py` の `.lede`・`.chnote` など）も同様に直した。                     */
.lead{margin:0 0 18px;color:var(--ink2);font-size:13.5px;max-width:74em}
/* ---- 1 件 1 枚を「チケット」として組む -------------------------------------
   **公演を眺める行為に形を合わせる。** 表の行や無地のカードだと、識別（題名・劇場・日程）
   と理由が同じ重みで並び、どこから読むのかが決まらない。**チケットには読む順序が
   もともとある** ── 番号と日付の耳（もぎる側）を左に置き、本文を右に置く。
   もぎる操作（興味あり）に動きを付けているのも同じ理由で、**押した結果が形で分かる。**  */
.ticket{position:relative;display:flex;background:var(--surf);border:1px solid var(--ring);
 border-radius:12px;margin:0 0 18px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
/* **耳に出すのは事実だけ。** 縦書きの札は外した（理由は `_stub` にある）── ここは
   配られる直前の HTML なので、飾りの文字はこの注記にも書かない。 */
.ticket .stub{flex:none;width:70px;display:flex;flex-direction:column;align-items:center;
 justify-content:flex-start;gap:9px;padding:20px 0;border-radius:12px 0 0 12px;
 background:linear-gradient(180deg,var(--plane),var(--surf));
 transition:transform .5s cubic-bezier(.34,1.1,.3,1),opacity .5s}
.ticket .stub .sn{font-size:10.5px;letter-spacing:.09em;color:var(--mute)}
.ticket .stub .sd{display:flex;flex-direction:column;align-items:center;line-height:1.15}
.ticket .stub .sd b{font-size:19px;font-weight:700;color:var(--acc);
 font-variant-numeric:tabular-nums}
.ticket .stub .sk{font-size:10px;letter-spacing:.16em;color:var(--mute);margin:3px 0 0}
/* ミシン目と、切り取り線の端のくぼみ */
.ticket .perf{flex:none;width:2px;margin:10px 0;opacity:.9;
 background-image:radial-gradient(circle at 1px 3.5px,var(--base) 1.1px,transparent 1.3px);
 background-size:2px 9px}
.ticket::before,.ticket::after{content:"";position:absolute;left:65px;width:11px;height:11px;
 border-radius:50%;background:var(--plane);border:1px solid var(--ring)}
.ticket::before{top:-6px}
.ticket::after{bottom:-6px}
/* **ポスターは本文の左に立てる。** 題名の隣にだけ置くと、絵の高さのぶん右が空いて
   「読むところが無い帯」ができる。本文の全体と並べれば、絵の高さが無駄にならない */
.ticket .body{flex:1;min-width:0;padding:20px 22px 18px;display:flex;gap:18px}
.ticket .main{flex:1;min-width:0}
/* **枠（`.pwrap`）に寸法を持たせる。** 絵そのものの `.poster` は枠いっぱいを埋めるだけ
   にしてある（`app.py` の `.pwrap .poster`）── 読み込み中の文字を重ねるため、
   起案者の指摘（2026-08-25）で `_poster()` が絵を `<span class="pwrap">` で囲む
   ようになった。ポスターの無い公演は `poster()` が空文字を返すので、この枠は出ない。 */
.ticket .pcol{flex:none;width:132px;display:flex;flex-direction:column;gap:8px}
.ticket .pcol .pwrap{width:132px;height:186px}
/* **公式サイトへの導線を、ポスターの真下に立てる**（起案者の指摘・2026-08-26 ──
   「もうちょっと主張してほしい」）。文字だけの下端の 1 行は、三択やあらすじを
   読んだ先にあって見落とされやすかった。絵の下ならボタンだと一目で分かる */
.ticket .sitebtn{display:flex;align-items:center;justify-content:center;gap:6px;
 font-size:12.5px;font-weight:600;padding:8px 6px;border-radius:99px;
 border:1px solid var(--acc);color:var(--acc);text-decoration:none;text-align:center}
.ticket .sitebtn:hover{background:var(--acc);color:var(--surf)}
@media(max-width:640px){.ticket .body{flex-direction:column}
 .ticket .pcol{width:104px}
 .ticket .pcol .pwrap{width:104px;height:146px}}
/* **もぎった状態。** 押した結果が形で分かる（reduced-motion では動かさない） */
.ticket.torn .stub{transform:translate(-15px,11px) rotate(-9deg);opacity:.38}
.ticket.torn .perf{opacity:.25}
.ticket.torn{box-shadow:none;border-style:dashed}
@media (prefers-reduced-motion:reduce){.ticket .stub{transition:none}}
@media(max-width:560px){.ticket .stub{width:52px;padding:12px 0;gap:6px}
 .ticket .stub .sd b{font-size:15px}
 .ticket::before,.ticket::after{left:47px}}
/* **もぎった 1 枚（興味あり）。** 傾けない ── 耳の日付がこの画面の主役なので薄くしない。
   済んだことは印（✓）と、ミシン目を薄くすることで出す。 */
.ticket.interest .stub{transition:none}
.ticket.interest .perf{opacity:.35}
.ticket .stub .sn.done{color:var(--good)}
.tickets{margin:0 0 8px}
/* ---- 月で絞り込む ------------------------------------------------------------
   **耳は素のリンクにした。** 月は 1 つ選べば足りるので、都道府県のような複数選択の
   form も、それを組み替える JavaScript も要らない。**押す前に件数が分かる**ように
   耳に数字を書く（0 件の月は耳を出さない）。

   **丸い札（`.mchip`）はやめた。** 評価一覧と日記帳を索引の耳に変えたときに、
   ここと探すの札だけがピルのまま残り、**同じ「1 つ選ぶと一覧の中身が入れ替わる」
   操作に 2 つの見た目が並んでいた。** 耳の指定は `app.py` の `APP_CSS` に 1 か所ある。 */
.mnow{margin:0 0 9px;color:var(--ink2);font-size:13px;max-width:74em}
/* 続きへの送り。**一覧の下に置く** ── 読み終えた場所に次の口がある */
.mfoot{display:flex;gap:14px;align-items:center;justify-content:space-between;
 flex-wrap:wrap;margin:4px 0 26px;font-size:13.5px}
.mpage{text-decoration:none;color:var(--acc);border:1px solid var(--ring);
 border-radius:99px;padding:7px 16px;background:var(--surf)}
.mpage:hover{border-color:var(--acc)}
.mpage.off{color:var(--mute);border-style:dashed;background:none}
.mfoot .mp{color:var(--mute);font-size:12.5px;font-variant-numeric:tabular-nums}
/* 理由の欄 */
.why-note{margin:12px 0 0;padding:12px 14px;border:1px dashed var(--ring);
 border-radius:10px;background:var(--plane)}
.why-note label{font-size:12px;color:var(--ink2);display:block;margin:0 0 6px}
/* **「任意」の小さな枠は、置かれた場所に関係なく同じ形にする。** 以前は
   `.why-note .opt` と欄の中に閉じて書いてあったため、**同じ部品をボタンの中に置いた
   45 か所（評価一覧・未評価・日記帳・探す）では枠も余白も大きさも失われ、
   「感想を書く任意」と字がくっついて出ていた。** 部品の見た目は部品の側で決める。   */
.opt{font-size:10.5px;color:var(--mute);border:1px solid var(--ring);
 border-radius:99px;padding:1px 7px;margin-left:8px}
.why-note textarea{width:100%;font:inherit;font-size:13px;padding:8px 11px;
 border:1px solid var(--ring);border-radius:8px;background:var(--surf);color:var(--ink);
 resize:vertical}
.wn-foot{display:flex;gap:10px;align-items:center;margin:6px 0 0;flex-wrap:wrap}
/* **空欄を並べない。** 追いかける一覧は読む画面なので、書く場所は押したときに開く */
.wnw{margin:12px 0 0}
/* ---- 封蝋 --------------------------------------------------------------------
   起案者の指示（2026-08-24）──「他の箇所にもシーリングとかつかうとおしゃれかも」。

   **押す場所を選んだ。** 封蝋は約束の印なので、**お気に入りにだけ使う** ── 登録した
   名前は「内容を問わず、件数も条件も付けずに必ず出す」と決めたものであり（企画書 1 章）、
   点数を付けて並べた推薦とは性質が違う。**一覧の耳に封蝋があれば、その 1 枚が順位では
   なく約束で出ていることが、理由の文を読む前に分かる。**

   **飾りとして各所に散らさない。** 意味の無い場所にも押すと、印であることが消えて
   ただの模様になる。                                                             */
.wax{position:relative;flex:none;width:25px;height:25px;display:grid;place-items:center;
 border-radius:47% 53% 51% 49% / 52% 47% 53% 48%;
 background:radial-gradient(circle at 33% 27%,var(--wax-hi),var(--wax) 64%);
 box-shadow:inset -1px -2px 3px rgba(0,0,0,.32),inset 1px 1px 2px rgba(255,255,255,.28),
  0 1px 2px rgba(0,0,0,.26);
 filter:url(#tg-wax);
 font-family:var(--mincho);font-size:12px;font-weight:600;line-height:1;
 color:var(--curtain-w)}
.wnb{font:inherit;font-size:12.5px;padding:5px 14px;border-radius:99px;
 border:1px dashed var(--ring);background:transparent;color:var(--acc);cursor:pointer}
.wnb:hover{border-style:solid}
.wnb .opt{border-color:var(--ring)}
.wnw .why-note{margin:0}
/* **自分が書いた理由。** 引用（あらすじ）と同じ形にそろえるが、線の色は変える ──
   あちらは外から来た文、こちらは自分が書いた文である。 */
.wnr{display:flex;gap:11px;align-items:baseline;flex-wrap:wrap;padding:9px 14px;
 border-left:3px solid var(--s2);background:var(--plane);border-radius:0 8px 8px 0;
 font-size:13px}
.wnl{flex:none;font-size:11px;color:var(--mute)}
.wnt{color:var(--ink);min-width:0}
.wnr .wnb{margin-left:auto;border:0;padding:0;font-size:11.5px}
.wnr .wnb:hover{text-decoration:underline}
/* **見送った理由。** 書く頻度が低い入力なので、閉じているのが既定である。
   `<details>` にしたので JavaScript を要さない。 */
.nn{margin:11px 0 0;font-size:12.5px}
.fav .nn{flex-basis:100%;margin:8px 0 0}
.nn>summary{cursor:pointer;color:var(--acc);list-style:none;display:inline-flex;
 gap:2px;align-items:baseline;flex-wrap:wrap}
.nn>summary::-webkit-details-marker{display:none}
.nn>summary::before{content:"▸";color:var(--mute);margin-right:6px}
.nn[open]>summary::before{content:"▾"}
.nn .nnv{color:var(--ink);margin-left:9px}
.nn[open]{border:1px dashed var(--ring);border-radius:10px;padding:10px 13px;
 background:var(--plane)}
.nn textarea{width:100%;margin:8px 0 0;font:inherit;font-size:13px;padding:8px 11px;
 border:1px solid var(--ring);border-radius:8px;background:var(--surf);color:var(--ink);
 resize:vertical}
.hint{font-size:11.5px;color:var(--mute)}
.body{flex:1;min-width:0}
h3{font-family:var(--mincho);font-size:17.5px;font-weight:600;margin:0 0 3px;
 line-height:1.45}
.meta{font-size:13.5px;color:var(--ink2);margin:0 0 2px}
.grp{color:var(--ink)}
.sep{color:var(--base);margin:0 5px}
.pref{color:var(--mute)}
.when{font-size:13.5px;margin:0 0 6px}
.price{color:var(--mute);font-size:12.5px;margin-left:12px}
/* **持っている券の日時。** 上演期間（`.when`）とは別のことを言っている ── 期間は
   公演全体がいつやるか、これは本人がどの回の券を持っているかである。何回もある
   公演では前者だけでは分からないので、目立つ色で分けて先に出す */
.mytix{margin:0 0 10px;font-size:13px}
.mytix>b{display:block;color:var(--ink);font-weight:600;margin:0 0 4px}
.mt-row{display:inline-flex;align-items:center;gap:6px;color:var(--acc);
 font-variant-numeric:tabular-nums;margin:0 10px 5px 0}
.mt-row.un{color:var(--mute)}
.mt-row button{font:inherit;font-size:11px;padding:1px 8px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.mt-row button:hover{border-color:var(--acc);color:var(--acc)}
.mt-add{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap}
.mt-add input{font:inherit;font-size:12.5px;padding:3px 8px;border-radius:6px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink)}
.mt-add button{font:inherit;font-size:12px;padding:4px 11px;border-radius:99px;
 border:1px solid var(--acc);background:var(--surf);color:var(--acc);cursor:pointer;
 display:inline-flex;align-items:center;gap:4px}
.mt-add button:hover{background:var(--acc);color:var(--surf)}
.mt-add .said{font-size:11.5px;color:var(--mute)}
/* ---- ツアーの全日程 ---------------------------------------------------------
   起案者の指摘（2026-08-26）──「興味あるんだけどその地方公演だといけない…って
   パターンがよくある。ツアー全日程表示してほしい。終わった日程は線を引いて消して」。
   **地方ごとに 1 行、上限なしで並べる。** 横一列に詰めて省略していたのをやめた ──
   「地方公演だと行けない」を判断するには、どの地方がいつなのかを全部読める必要がある。 */
.tourfull{margin:0 0 10px;font-size:12.5px;line-height:1.9}
.tf-row{display:flex;gap:8px;align-items:baseline}
.tf-loc{color:var(--ink2);font-weight:600;flex:none}
/* 会場名は都道府県の呼び名より軽くする ── 太字が並ぶと、どちらが地名でどちらが
   劇場名か読み分けにくい */
.tf-th{font-weight:400;color:var(--mute)}
.tf-when{color:var(--ink2)}
/* **終わった日程は消さず、取り消し線で「もう行けない」と示す。** 消すと、
   ツアー全体が何都市を回ったのかが読めなくなる */
.tf-row.done{color:var(--mute)}
.tf-row.done .tf-loc,.tf-row.done .tf-when{text-decoration:line-through}
.sale{margin:8px 0 10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.pill{font-size:12px;font-weight:600;padding:2px 10px;border-radius:99px;border:1px solid var(--ring)}
.pill.ok{color:var(--good);border-color:#0ca30c55}
.pill.soon{color:var(--acc);border-color:#2a78d655}
.pill.warn{color:var(--warn);border-color:#c9850055}
/* **出演者は事実として出す。** 理由の欄（名簿に当たった人だけ）とは別の節にする */
.cast{margin:0 0 10px;font-size:13px;line-height:1.75}
.cast .cr{display:flex;gap:10px}
.cast .cl{flex:none;width:3.4em;color:var(--mute);font-size:11.5px;padding-top:.15em}
.cast .cv{color:var(--ink);min-width:0}
.cast .rest{display:none}
.cast.open .rest{display:inline}
.cast.open .mrb{display:none}
.cast .mrb{font:inherit;font-size:11.5px;padding:0 0 0 6px;border:0;background:none;
 color:var(--acc);cursor:pointer}
.cast.none{color:var(--mute);font-size:12.5px}
.cast .src{color:var(--base);font-size:11px;margin-left:3.4em;display:inline-block}
.syn{font-size:13.5px;color:var(--ink2);margin:0 0 12px;padding:10px 14px;
 border-left:3px solid var(--grid);background:var(--plane);border-radius:0 8px 8px 0}
.syn .txt{margin:0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;
 overflow:hidden}
.syn.open .txt{display:block}
.syn .mrb{font:inherit;font-size:11.5px;padding:0;margin:4px 0 0;border:0;background:none;
 color:var(--acc);cursor:pointer;display:block}
.syn.open .mrb::after{content:"を閉じる"}
.syn.open .mrb{font-size:0}
.syn.open .mrb::after{font-size:11.5px;content:"畳む"}
.syn.no{color:var(--mute);font-size:12.5px}
.syn.part{font-size:12.5px}
/* **札は押し口ではない。** 藍（--acc）は押せるものの色なので使わない ──
   同じ見た目のものは同じ働きをする、を崩さないためである */
.syn .tags{display:flex;flex-wrap:wrap;gap:4px 5px;margin:7px 0 0}
.syn .tag{font-size:11.5px;line-height:1.5;color:var(--ink2);background:var(--surf);
 border:1px solid var(--grid);border-radius:999px;padding:1px 9px;white-space:nowrap}
.syn .tag.mine{color:var(--mute);border-style:dashed}
/* **入れ口は畳んでおく。** 15 枚を並べる一覧なので、開いたままだと 1 枚が伸びて
   見比べられなくなる。**空いている枠にだけ出す**ので、押す人は目的があって押す */
.handt{margin:8px 0 0}
.handt>summary{font-size:11.5px;color:var(--acc);cursor:pointer;list-style:none;
 display:inline-block;padding:1px 0}
.handt>summary::-webkit-details-marker{display:none}
.handt>summary::before{content:"＋ "}
.handt[open]>summary::before{content:"− "}
.handt .lead{font-size:11.5px;color:var(--ink2);margin:6px 0 8px;line-height:1.7}
.handt .hl{display:block;font-size:11px;color:var(--mute);margin:7px 0 0}
.handt input,.handt textarea{display:block;width:100%;box-sizing:border-box;margin:3px 0 0;
 font:inherit;font-size:12.5px;color:var(--ink);background:var(--surf);
 border:1px solid var(--grid);border-radius:6px;padding:5px 8px}
.handt textarea{resize:vertical;line-height:1.6}
.handt .hn{display:block;font-size:10.5px;color:var(--mute);margin:3px 0 0;line-height:1.6}
.handt .hb{margin:10px 0 0;font:inherit;font-size:12px;cursor:pointer;
 color:var(--curtain-w);background:var(--acc);border:0;border-radius:6px;padding:5px 14px}
.syn .hsaid{font-size:11.5px;color:var(--pos);margin:7px 0 0}
.syn.doubt{border-left-color:var(--warn)}
.src.warn{color:var(--warn)}
/* **「なぜ出てきたか」は、この一覧の存在理由そのものである。** あらすじや値段と同じ
   灰色で置くと、付帯情報の 1 つに見える ── 幕の色で言う（押し口ではないので藍は使わない） */
.whyh{font-size:11.5px;letter-spacing:.13em;font-weight:700;color:var(--curtain);
 margin:0 0 5px}
.why{list-style:none;margin:0;padding:0}
/* **探した結果は、題名の直下に面で置く。**（起案者の指示・2026-08-26 ──「各カードの
   上に明記してほしい」）。あらすじや値段と同じ並びに置くと、下まで読まないと出てこない
   ── **見た目でも「これが出た理由」だと分かるように、幕の色を薄く敷いた面にする。**
   `.whyh`（見出し）は既存の色のままにし、面の側だけ足す */
.whyh.top{margin:8px 0 6px;letter-spacing:.08em}
.why.top{margin:0 0 14px;padding:8px 12px;border-radius:9px;
 background:color-mix(in srgb,var(--curtain) 8%,var(--surf));
 border:1px solid color-mix(in srgb,var(--curtain) 22%,var(--ring))}
.why.top .rs{padding:2px 0}
.rs{font-size:13.5px;padding:3px 0 3px 0;line-height:1.65}
.net{display:inline-block;font-size:11px;font-weight:600;padding:1px 8px;border-radius:99px;
 margin-right:9px;border:1px solid var(--ring);color:var(--ink2)}
/* **縁の色は系統の色から作る。** 以前は `#eb683455` のように値を直に書いていたので、
   意匠の色を差し替えても縁だけが古い色のまま残っていた */
.rs.a .net{color:var(--s2);border-color:color-mix(in srgb,var(--s2) 42%,transparent)}
.rs.b .net{color:var(--s1);border-color:color-mix(in srgb,var(--s1) 42%,transparent)}
.rs.c .net{color:var(--s3);border-color:color-mix(in srgb,var(--s3) 42%,transparent)}
.rs.none{color:var(--mute);font-size:12.5px}
.n{color:var(--mute);font-size:12.5px}
.src{color:var(--base);font-size:11.5px;margin-left:8px}
.rsx{font:inherit;font-size:11px;border:0;background:transparent;color:var(--mute);
 cursor:pointer;margin-left:6px;padding:0 2px}
.rsx:hover{color:#e34948}
.act{margin:14px 0 0;display:flex;gap:16px;align-items:center;flex-wrap:wrap;
 border-top:1px solid var(--grid);padding-top:12px}
.act a{color:var(--acc);font-size:13px;text-decoration:none}
.act a:hover{text-decoration:underline}
.nolink{font-size:12.5px;color:var(--mute)}
/* **すでに登録した公演の印。** 起案者の指示（2026-08-26）で赤文字にする ──
   ×（好みの否定）と同じ意味の赤ではないが、**この仕組みが持つ赤はこの 1 色だけ**
   なので、新しい赤を持ち込まず `--neg` を借りる（濃淡はテーマごとに調整済み） */
.added-note{margin-left:auto;color:var(--neg);font-size:13px;font-weight:600}
.btns{display:flex;gap:8px;align-items:center;margin-left:auto;flex-wrap:wrap}
/* **`hidden` 属性は、同じ強さの `display` 指定に負ける。** 上の `display:flex` が
   既定を上書きするので、答え直す口で畳むにはここが要る（`.rb[hidden]` と同じ理由） */
.btns[hidden]{display:none}
.btns button,.rb button{font:inherit;font-size:12.5px;padding:4px 12px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.btns button:hover,.rb button:hover{border-color:var(--acc);color:var(--acc)}
.btns.done button,.rb.done button{opacity:.35;pointer-events:none}
.btns.dead,.rb.dead{opacity:.4;pointer-events:none}
.said{font-size:12px;color:var(--good);min-width:0}
.waits{margin:0 0 8px}
/* ---- 評価待ちの行も、もぎられる形にする ------------------------------------
   **もぎるのは、観てきた 1 枚である。** 半券がもぎられるのは劇場に入るときなので、
   まだ買ってもいない推薦の枠ではなく、**観終わって評価を付けた瞬間**に耳が外れる。
   耳に出すのは上演日で、飾りの文字は書かない（`_wait_stub`）。                  */
/* **耳は行の高さいっぱいに立てる。** 折り返す本文と同じ flex 行に置くと、耳が
   1 行目の高さしか持たず、下が空いた欠けた券になる。**外側は 3 列（耳・ミシン目・
   本文）に固定し、折り返しは本文の中だけで起こす。**                            */
/* **左端に「まだ答えていない」の印を持たせる。** 急ぎの催促ではなく宿題なので、
   赤ではなく金で置く ── 評価は輪を閉じる操作だが、期限があるものではない */
.wait{position:relative;display:flex;align-items:stretch;
 background:var(--surf);border:1px solid var(--ring);border-left:3px solid var(--warn);
 border-radius:0 10px 10px 0;margin:0 0 9px;font-size:13.5px}
.wait .wbody{flex:1;min-width:0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;
 padding:11px 16px 11px 12px}
.wait .wstub{flex:none;width:60px;display:flex;flex-direction:column;
 align-items:center;justify-content:center;line-height:1.15;border-radius:0;
 background:linear-gradient(180deg,var(--plane),var(--surf));
 transition:transform .5s cubic-bezier(.34,1.1,.3,1),opacity .5s}
/* **年を月日の上に置く。** 耳の幅は 60px しかないので、同じ行に並べると読めない。
   小さくても、**2022 年の公演と 2026 年の公演が同じ顔で並ばない**ことが要る */
.wait .wstub .sy{font-size:10.5px;color:var(--mute);letter-spacing:.02em;
 font-variant-numeric:tabular-nums}
.wait .wstub b{font-size:15px;color:var(--acc);font-variant-numeric:tabular-nums}
.wait .wstub .sk{font-size:9.5px;letter-spacing:.13em;color:var(--mute);margin:2px 0 0}
.wait .wperf{flex:none;width:2px;margin:9px 0;
 background-image:radial-gradient(circle at 1px 3.5px,var(--base) 1.1px,transparent 1.3px);
 background-size:2px 9px}
.wait::before,.wait::after{content:"";position:absolute;left:56px;width:9px;height:9px;
 border-radius:50%;background:var(--plane);border:1px solid var(--ring)}
.wait::before{top:-5px}
.wait::after{bottom:-5px}
/* **もぎれた状態。** 評価を押した結果が形で分かる（記録できなかったら元に戻す） */
.wait.torn .wstub{transform:translate(-14px,10px) rotate(-9deg);opacity:.38}
.wait.torn .wperf{opacity:.25}
.wait.torn{border-style:dashed;box-shadow:none}
@media (prefers-reduced-motion:reduce){.wait .wstub{transition:none}}
@media(max-width:560px){.wait .wstub{width:48px}
 .wait .wstub b{font-size:13px}
 .wait .wstub .sy{font-size:9.5px}
 .wait::before,.wait::after{left:44px}}
.wait .wt{font-weight:600}
.wait .wm{color:var(--mute);font-size:12.5px}
.rb{display:flex;gap:6px;align-items:center;margin-left:auto;flex-wrap:wrap}
.rb button{min-width:36px;font-size:15px;padding:2px 10px}
.rb button.pend{font-size:12px;min-width:0}
/* 感想の欄。**行の幅いっぱいに折り返して置く** ── ◎○△× の横に並べると、
   ボタンと同じ大きさの入力欄になって何を書く場所か分からない */
.wnote{flex:1 0 100%;display:flex;gap:10px;align-items:flex-start;
 border-top:1px solid var(--grid);padding-top:10px;margin-top:2px}
/* **`display` を書いたら `hidden` を書き直す。** `[hidden]` の display:none は
   ブラウザの既定の指定なので、こちらで display:flex を書くと**押す前から開いた状態で
   出てしまう**（`.why-note` は display を書いていないので無事だった） */
.wnote[hidden]{display:none}
.wnote textarea{flex:1;font:inherit;font-size:13px;line-height:1.6;resize:vertical;
 padding:8px 11px;border-radius:9px;border:1px solid var(--ring);
 background:var(--bg);color:var(--ink)}
.wnote textarea::placeholder{color:var(--mute)}
.wnote .said{padding-top:9px;white-space:nowrap}
/* 自分が書いた感想の引用。**網の色は付けない** ── これは網ではなく、
   本人が書いた文を返している行である */
.rs.q{color:var(--ink2);padding-left:2px}
.rs.q b{color:var(--ink);font-weight:600;margin-right:7px}
.dead-note{background:var(--surf);border:1px solid #c9850055;color:var(--warn);
 border-radius:12px;padding:12px 18px;margin:0 0 22px;font-size:13px}
.foot{margin:28px 0 0;display:flex;justify-content:flex-end}
.foot button{font:inherit;font-size:13px;padding:7px 18px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.favs{margin:0 0 8px}
.fav{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;background:var(--surf);
 border:1px solid var(--ring);border-radius:10px;padding:11px 16px;margin:0 0 7px;font-size:13.5px}
.fav .ft{font-weight:600}
.fav .fm{color:var(--ink2);font-size:12.5px}
.fav .fa{color:var(--s2);font-size:12px;margin-left:auto}
.fav a{color:var(--acc);font-size:12px;text-decoration:none}
/* ---- 観に行ける場所で絞り込む ----------------------------------------------
   **畳んでおく。** 既定が全国なので、開いていると「選ばないといけない」ように見える。
   選んでいるときだけ開いた状態で出し、いま何で絞っているのかを見出しに書く。 */
.pfil{margin:0 0 22px}
.pbox{background:var(--surf);border:1px solid var(--ring);border-radius:12px;padding:12px 18px}
/* **三角の印を消さない。** summary を flex にすると印が消え、押せる場所に見えなくなる */
.pbox summary{cursor:pointer;font-size:13.5px;font-weight:600}
.pbox summary .ico{margin-right:7px}
.pbox summary b{color:var(--acc)}
.pchips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 0}
/* 札そのものを押せるようにする。**チェック箱だけを的にしない** ── 47 個並ぶので、
   小さな箱を狙わせると押し間違える */
.pchip{display:inline-flex;gap:6px;align-items:center;font-size:12.5px;cursor:pointer;
 border:1px solid var(--ring);border-radius:99px;padding:4px 11px;color:var(--ink2);
 background:var(--plane);user-select:none}
.pchip:hover{color:var(--ink);border-color:var(--base)}
.pchip.on,.pchip:has(input:checked){border-color:var(--acc);color:var(--acc);
 font-weight:600;background:var(--surf)}
.pchip input{margin:0;accent-color:var(--acc)}
.pchip .pn{font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.pchip.on .pn,.pchip:has(input:checked) .pn{color:var(--acc)}
.pfoot{display:flex;gap:14px;align-items:center;margin:14px 0 0;flex-wrap:wrap}
.pfoot button{font:inherit;font-size:13px;padding:7px 18px;border-radius:99px;
 border:1px solid var(--acc);background:var(--surf);color:var(--acc);font-weight:600;
 cursor:pointer;display:inline-flex;gap:6px;align-items:center}
.pall{font-size:12.5px;color:var(--mute)}
.pnow{font-size:13px;color:var(--ink2);margin:0 0 14px;background:var(--surf);
 border:1px solid var(--ring);border-left:3px solid var(--acc);border-radius:0 10px 10px 0;
 padding:11px 16px}
.note{margin:16px 0 0;color:var(--mute);font-size:12.5px;line-height:1.7;
 background:var(--surf);border:1px solid var(--ring);border-radius:12px;padding:16px 20px}
b{font-weight:600;color:var(--ink)}
@media(max-width:560px){.rec{flex-direction:column;gap:6px}.rk{text-align:left}}
"""


WAITING = ROOT / "data" / "review" / "waiting.json"



def simple_row(c: dict, tag: str = "", note_no: str | None = None) -> str:
    """束に畳む行。**識別と日程だけを出す**（理由は推薦枠の役目なので繰り返さない）。

    **例外は「見送った理由」である**（`note_no` を渡した束だけ）。これは推薦枠が持って
    いない情報で、**この束を残している目的そのものに要る** ── 後から「観ればよかった」を
    拾い直すときに、都合で見送ったものと好みに合わなかったものを見分けるためである。
    """
    return (f'<div class="fav">{poster(c["stage_id"])}<span class="ft">{E(c.get("title") or "")}</span>'
            f'<span class="fm">{E(c.get("group") or "")} ／ {E(c.get("theater") or "")}'
            f'（{E(c.get("pref") or "")}）{period_label(c.get("period", ""), c.get("days", 0))}</span>'
            + (f'<span class="fa">{E(tag)}</span>' if tag else "")
            + (f'<a href="{E(c["url"])}" target="_blank" rel="noopener noreferrer">公式</a>' if c.get("url") else "")
            + buttons(c["stage_id"])
            + (no_note(c["stage_id"], note_no) if note_no is not None else "")
            + "</div>")


def bundle(title: str, lead: str, rows: list, tag: str = "",
           notes_no: dict | None = None) -> str:
    """**畳んで残す束。** 消さないので開けばいつでも見られる（企画書 2 章）。

    **開く前に何が入っているかを見出しに書く。** 「その他 N 件」だけでは開く理由が無く、
    実質開かれない（問題 E3）。件数と、何の束なのかを必ず添える。
    """
    if not rows:
        return ""
    return (f'<details class="bundle"><summary>{E(title)} {len(rows)} 件</summary>'
            f'<p class="lead">{lead}</p>'
            + '<div class="favs">'
            + "".join(simple_row(c, tag,
                                 None if notes_no is None
                                 else notes_no.get(str(c["stage_id"]), ""))
                      for c in rows)
            + '</div></details>')


def declared_form() -> str:
    """**お気に入りの登録と解除。推薦の画面の中に置く**（企画書 1 章）。

    別の画面を立てない理由は、**新着が出るのと同じ場所に登録があるほうが、登録したことを
    忘れたまま増え続けるのを防げる**からである。登録した名前は母集団に頼らず公式サイトを
    直接見るので、件数の制限は付けない。
    """
    import recommend as RC
    d = RC.load_declared()
    kinds = "".join(f'<option value="{E(k)}">{E(k)}</option>' for k in RC.KINDS)
    cur = "".join(
        f'<span class="tag" data-kind="{E(k)}" data-name="{E(n)}">{E(k)}「{E(n)}」'
        f'<button data-fav="remove">✕</button></span>'
        for k in RC.KINDS for n in d.get(k, []))
    return f"""<details class="bundle fav-edit"><summary>お気に入りの登録と解除 {sum(len(v) for v in d.values())} 件</summary>
<p class="lead">ここに登録した名前の公演は、<b>件数の制限も条件も付けずに新着として出ます。</b>
観た記録に無い名前も登録できます。</p>
<div class="fav-add"><select id="fav-kind">{kinds}</select>
 <input id="fav-name" type="text" placeholder="団体名・人名・作品名・題材" size="28">
 <button data-fav="add">登録する</button><span class="said"></span></div>
<div class="tags">{cur}</div></details>"""


def waiting_html(wait: list, lead: bool = True) -> str:
    """評価待ち。**通知を送らない構成では、ここが唯一の催促である**（企画書 2 章）。

    `lead=False` で前置きを落とす。**評価の一覧の中に細い帯として置くときは、
    同じ基準の説明がページの前置きにも出るので、2 回言わない**（2026-08-24）。
    """
    if not wait:
        return '<p class="empty">評価待ちはありません。上演が終わった公演が出てくると、ここに並びます。</p>'
    if not lead:
        return f'<div class="waits">{"".join(wait_row(w) for w in wait)}</div>'
    return ('<p class="lead">おすすめは、ここで ◎ を付けた公演の作り手から作ります。'
            '<b>付ける基準は「自分に合っていたか」で、作品の出来ではありません。</b>'
            '評価は作品ごとに 1 つです。</p>'
            '<p class="lead">評価を押すと、<b>感想を書く欄が開きます（任意です）。</b>'
            '◎ を付けた作品に一文書いておくと、次に同じ作り手の公演が出てきたときに、'
            'その言葉をおすすめの理由に添えて出します。</p>'
            f'<div class="waits">{"".join(wait_row(w) for w in wait)}</div>')


def favourites_html(d: dict, rows: list | None = None) -> str:
    """お気に入りの新着。**推薦ではなくお知らせだが、出す事実は推薦と同じにする。**

    **1 行に潰すのをやめた**（2026-08-24）。値段・あらすじ・出演者を持っているのに
    題名と日程だけを出していたので、**この画面だけでは観るかどうかが決まらず、
    毎回 CoRich を開き直すことになっていた。**
    """
    favs = d.get("favourites") if rows is None else rows
    if not favs:
        return '<p class="empty">登録した名前に当たる新着はありません。</p>'
    # **見出しの文と同じことを書かない。** 「お知らせであること」「内容を問わず出すこと」は
    # `page_favourites` の見出しの下に書いてある ── ここに要るのは、**この一覧で何が
    # できるか（読むだけである）**と、並び順である
    return (f'<p class="lead"><b>ここは読むだけです。押すボタンはありません。</b>'
            f'<b>上演日の近い順</b>に並んでいます。順位は付けていません。'
            f'観ると決めたら、公式サイトから券を求めてください。</p>'
            f'<div class="tickets">'
            f'{"".join(ticket(c, mode="favourite") for c in favs)}</div>')


def tracking_html(d: dict, notes: dict | None = None,
                  rows: list | None = None) -> str:
    """「興味あり」を押した公演。**畳んだ束から 1 つの画面に出した**（2026-08-24）。

    **束の中では追いかけられない。** 買い忘れを防ぐための一覧なのに、`<details>` の中に
    題名と日程だけの行で入っていたので、**開くまで見えず、開いても値段と発売状況が
    分からなかった。** 推薦から興味ありへ、興味ありからお気に入りへという流れの
    2 段目にあたるので、画面として立てる。

    **並びは上演日の近い順のままにする**（買うならここから買う）。順位は付けない。
    """
    rows = (d.get("tracking") or []) if rows is None else rows
    notes = notes or {}
    if not rows:
        return ('<p class="empty">追いかけている公演はありません。'
                '「おすすめ」の画面で「興味あり」を押すと、ここに並びます。</p>')
    return ('<p class="lead"><b>上演日の近い順</b>に並んでいます。順位は付けていません。</p>'
            '<div class="tickets">'
            + "".join(ticket(c, mode="interest", note=notes.get(str(c["stage_id"]), ""))
                        for c in rows)
            + "</div>")


def cards_html(d: dict, rows: list | None = None) -> str:
    """**出す一覧は呼ぶ側が決める。** 絞り込みは画面の側で行うので、ここでは受け取るだけ。"""
    return "".join(card(i, c) for i, c in enumerate(
        d["recommend"] if rows is None else rows, 1))


def bundles_html(d: dict, notes_no: dict | None = None) -> str:
    """判断が済んだ公演の束。**畳むが消さない。**

    **「追いかけている（興味あり）」はここから外した**（2026-08-24）── 畳んだ束ではなく
    1 つの画面になったので、両方に置くと同じ一覧が 2 か所にある状態になる
    （`tracking_html`）。

    **「観る予定（すでに持っている）」も、同じ理由でここから外した**（2026-08-26・
    起案者の指摘 ──「今週のおすすめの下にあるのは位置がおかしい気がする」）。
    「購入済み公演」（`/tickets`）が独立した画面になった 2026-08-25 の時点で、
    ここには消し忘れて残っていた ── `page_tickets` と同じ `d.get("owned")` を
    もう一度出しており、同じ一覧が 2 か所（今週のおすすめの下・購入済み公演）に
    ある状態だった。**ここに残すのは、興味なし（と、語で自動的に外れた分）だけである。**
    """
    return (bundle("その他（興味なしと答えた公演）",
                     "消さずに残しています。<b>見送った理由は 1 件ずつ書けます</b>"
                     "（任意・畳んであります）── 書いておくと、都合で見送ったものと"
                     "好みに合わなかったものを後から見分けられます。",
                     d.get("others") or [], "興味なし",
                     notes_no if notes_no is not None else {})
            + _declined_bundle(d))


def _declined_bundle(d: dict) -> str:
    """出さないと決めた語に当たった公演の束。**消さずに畳む。**

    **何に当たって外れたのかを 1 件ずつ書く。** 「22 件を外しました」とだけ書くと、
    何が外れたのか確かめようがない ── **本人が語を外せば全部戻る**ことも、ここで言う。
    """
    rows = d.get("declined") or []
    if not rows:
        return ""
    words = sorted({c.get("declined") or "" for c in rows} - {""})
    return bundle(
        "出さないと決めた語に当たった公演",
        "<b>出さないと決めた語</b>（"
        + "・".join(f"「{E(w)}」" for w in words)
        + "）が、題名・団体・劇場・出演者・題材のどれかに出てくる公演です。"
        "消していないので、<b>「お気に入り」の画面で語を外せば次の一覧から戻ります。</b>"
        "お気に入りに登録した名前の公演は、ここに入りません。",
        rows, "出さない語")


def limits_html(d: dict, rows: list | None = None) -> str:
    """**満たせていない表示項目を、画面に書く。** 空欄にして黙って落とさない（企画書 2 章）。

    **数えるのは、いま画面に出ている一覧である。** 絞り込んだときに全国の 15 件で数えると、
    「あらすじを表示できた」件数が目の前の一覧と合わなくなる。
    """
    rec = d["recommend"] if rows is None else rows
    if not rec:
        return ""
    n_syn = sum(1 for c in rec if (c.get("synopsis") or "").strip())
    return f"""<p class="note"><b>この {len(rec)} 件で、出せていない情報です。</b><br>
・<b>券が買える期限と、販売終了・完売</b> ── 手元の情報には無いので出せません。
残っているかは公式サイトでお確かめください<br>
・<b>あらすじ</b> ── {n_syn}/{len(rec)} 件で出せました。残りは公演のページに載っていませんでした<br>
・<b>答えなかった公演は、翌週も同じ順位で出てきます。</b>
そのぶん枠が埋まるので、新しい公演が出にくくなります</p>"""


def load() -> tuple[dict, list]:
    """推薦の材料を読む。**評価待ちは `tools/taguri/run.py` の 2 段目が書く。**"""
    d = json.loads(SRC.read_text(encoding="utf-8"))
    wait = json.loads(WAITING.read_text(encoding="utf-8")) if WAITING.exists() else []
    return d, wait


def main() -> int:
    """**単体の 1 枚を書き出す確認用の入口。**

    利用者が使うのは `tools/taguri/run.py` が開く 1 つのシステム（ナビゲーションで
    画面を移動する形）である。**このファイルを直接開いてもボタンは効かない** ──
    トークンが入らないので、画面側が押せないようにする。
    """
    d, wait = load()
    rec = d["recommend"]
    inner = (f"<h1>今週の推薦 {len(rec)} 件</h1>"
             + f'<h2>評価待ち</h2>{waiting_html(wait)}'
             + declared_form()
             + "<h2>今週の推薦</h2>" + cards_html(d)
             + f'<h2>追いかけている {len(d.get("tracking") or [])} 件</h2>{tracking_html(d)}'
             + f'<h2>お気に入りの新着 {len(d["favourites"])} 件</h2>{favourites_html(d)}'
             + "<h2>畳んである束</h2>" + bundles_html(d) + limits_html(d))
    OUT.write_text(f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>今週の推薦 {len(rec)} 件</title><style>{STYLE}</style></head><body>{FILTERS}
<div class="wrap">
<div class="dead-note"><b>このページのボタンは効かない。</b>
 確認用に書き出した 1 枚で、押した内容を書き戻す先が無い。
 <code>python3 tools/taguri/run.py</code> から開くこと。</div>
{inner}</div></body></html>""", encoding="utf-8")
    print(f"書き出し: {OUT}（{len(rec)} 件・確認用の 1 枚）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
