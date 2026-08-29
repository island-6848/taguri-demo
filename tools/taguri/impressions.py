#!/usr/bin/env python3
"""感想（本人が自分の言葉で書いた一文）を集める仕組み。

起案者の指示（2026-08-24）── 可視化の提案 2 件のうち「感情の標高（等高線）」は
**いまのデータでは描くと嘘になる**と測ったうえで、詰まっているのは入力の側なので
「先に感想が集まる形を作る」ほうを選んだ。**これはその入力側である。**

## なぜ「感想がたまらない」のか ── 測ってから決めた

**動機の問題ではない。書く場所が、書く瞬間に無かった。**

| | 件数 |
|---|---|
| 評価（◎○△×）が付いた作品 | 94 |
| 感想が書かれた作品 | **8** |
| ◎ を付けた作品 | 35 |
| ◎ のうち感想がある | **5** |

（ほかに「まだ判断できない」が 1 件ある。評価の段階を選んでいないので、上の 94 には
数えていない。）

**感想の欄は「記録を見返す」の行と、評価が付いていない記録の一覧にしか無かった。**
評価そのものを付ける「観た公演の評価」の評価待ちの行には欄が無い ── **観た帰りに
◎ を押す瞬間が、いちばん言葉が出てくる瞬間**なのに、そこに置いていなかった。

## 返りが無い入力は設計しない ── 何が返るかを測った

**測るためだけの入力は作らない**（企画書 2 章・検証 021 で 1 度取り下げた）。
そこで、既にある返りの経路（`reasons.py` の「理由から拾った名前」＝ 文に出てきた名前を
お気に入りの登録候補として出す）を、**手元の感想 8 件に通して測った。**

    感想 8 件 → 名前の一致 1 件（作り手31・すでに登録済み）→ 新しい候補 0 件

**効かない。** 「興味あり」に添える理由（26 件 → 候補 7 件）とは文の性質が違う ──
理由は観る前に書くので名前の羅列になるが、**感想は観た後に書くので気持ちの言葉になり、
人物は「小川さん」「末満」のように姓だけ、団体は「劇団5」のように通称で出る。**
`reasons.py` は「姓だけ・愛称・略称は拾えない」と限界を明記してあるので、これは
想定どおりの結果である。**この経路を感想の返りとして売ってはいけない。**

## 返りは「次に迷ったときに、自分の言葉が出てくる」ことにした

**推薦の理由の欄は、いま名前と本数しか出していない。**

    人物  演出 末満健一（◎ を付けた作品での実績・履歴 1 本）

**この行だけでは、観るかどうかが決まらない。** 名簿（網 B）は ◎ を付けた作品の
クレジットから作り手を機械的に全員拾うので、1 作品あたり 20〜50 人が入る
（実データで 1,008 人／43 作品）── **その中のどれが自分にとっての決め手だったかは、
◎ という記号には残っていない。** 感想には残っている。

    人物  演出 末満健一（◎ を付けた作品での実績・履歴 1 本）
          《ダーウィン・ヤング》に「とにかく苦しくて最高だった」と書いています

**これが感想を書く返りである。** 内部の指標（寄与・スコア）は出さない ── 出すのは
本人が書いた文と作品名という、生活の言葉だけである。

**実測 ── いまの感想 5 件で、推薦 1/15 枚・興味あり 8/27 枚に出る。書くほど増える。**
お気に入りの枠には出ない（あの束は「登録した名前に当たった」ことだけを理由に出すので、
人物の理由をそもそも混ぜない）。

## 溜まっている分は、有限の束にして出す

**古い観劇の感想は、思い出しでは書けない。** ◎ の 30 件を一度に並べると答えられないので、
**書ける見込みが高い順（何度も観た順・新しい順）に 15 件ずつ**出す。量で網羅を作らない。

**◎ に限る理由は、返りが ◎ にしか無いからである。** 推薦の理由に出てくるのは ◎ を
付けた作品の作り手だけなので、○ や △ に書いた感想は上の引用に出てこない。
**書けないのではなく、いま返りが無い** ── 書きたいときは「記録を見返す」の欄がある。
"""

from __future__ import annotations

import html
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M                                           # noqa: E402

DB = ROOT / "data" / "review" / "ratings.db"

# **引用は ◎ の作品からしか出さない。** 推薦の理由（網 B）は ◎ を付けた作品の
# クレジットから作るので、○ の作品の感想を引くと、理由と根拠が食い違う
QUOTE_GRADE = "◎"
ROUND = 15          # 1 度に出す件数（量で網羅を作らない）
QUOTE_LEN = 90      # 引用の長さ。**切ったことが分かる形で切る**


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def notes() -> dict[str, dict]:
    """感想が書かれている作品。work_key → 行。"""
    con = _con()
    rows = {r["work_key"]: dict(r) for r in con.execute(
        "SELECT work_key, title, first_date, verdict, times, note_impression"
        " FROM works WHERE note_impression IS NOT NULL"
        " AND TRIM(note_impression) <> ''")}
    con.close()
    return rows


def by_person(rated: list[dict] | None = None) -> dict[str, list[dict]]:
    """作り手の名前 → その人が関わった ◎ の作品のうち、感想が書かれているもの。

    **突き合わせは名前そのもので行う。** 推薦の理由に出てくる名前はクレジットから
    取った文字なので、感想の側の表記を推測する必要が無い ── `rated` の `people` と
    同じ一覧を引くだけである。

    **1 人が複数の作品に出てくることがある。** そのときは何度も観た作品を先に置く
    （**重なった根拠を先に出す**のと同じ理由で、思い入れの強い側から引用する）。
    """
    have = notes()
    rated = rated if rated is not None else M.load_rated()
    out: dict[str, list[dict]] = {}
    for r in rated:
        if r.get("verdict") != QUOTE_GRADE:
            continue
        n = have.get(r["key"])
        if not n:
            continue
        item = {"work_key": r["key"], "title": r["title"], "date": r.get("date") or "",
                "times": r.get("times") or 1, "note": n["note_impression"].strip()}
        for _role, person in r.get("people") or []:
            out.setdefault(person, [])
            if all(x["work_key"] != item["work_key"] for x in out[person]):
                out[person].append(item)
    for v in out.values():
        v.sort(key=lambda d: (-d["times"], _neg_date(d["date"])))
    return out


def clip(s: str, n: int = QUOTE_LEN) -> str:
    """引用を切る。**切ったことが分かる形で切る** ── 途中で終わった文を、
    本人が書いた文として読ませない。"""
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n] + "…"


def pending(works: list[dict], limit: int | None = ROUND) -> list[dict]:
    """◎ なのに感想が無い作品を、**書ける見込みが高い順**に。

    `works` は `app._works()` の行（題名・回数・日付・評価・感想を持つ）。

    **順序は「何度も観た順 → 新しい順」である。** 思い出せる度合いがそのまま
    書ける見込みなので、**溜まった順（古い順）に出すと、いちばん書けないものが
    先頭に来る。** 観ていない記録（`unseen`）は数えない。
    """
    rows = [w for w in works
            if w.get("verdict") == QUOTE_GRADE
            and not (w.get("note_impression") or "").strip()
            and not w.get("unseen")]
    rows.sort(key=lambda w: (-(w.get("times") or 1),
                             _neg_date(w.get("first_date") or "")))
    # **`limit=None` は「全件」である。** 束の見出しに出す件数と、束の中に出す一覧を
    # 同じ材料から数えるために要る（別々に数えると件数が一覧と合わない）
    return rows if limit is None else rows[:limit]


def _neg_date(d: str) -> str:
    """新しい順に並べるための鍵。**日付の無い記録は最後に置く** ──
    いつ観たか分からないものは、いちばん思い出しにくい。"""
    return "".join(chr(ord("9") - int(ch)) if ch.isdigit() else ch
                   for ch in d) if d else "~"


def stats() -> dict:
    con = _con()
    n_rated = con.execute("SELECT COUNT(*) FROM works WHERE verdict IN"
                          " ('◎','○','△','×')").fetchone()[0]
    n_note = con.execute("SELECT COUNT(*) FROM works WHERE note_impression IS NOT NULL"
                         " AND TRIM(note_impression) <> ''").fetchone()[0]
    n_top = con.execute("SELECT COUNT(*) FROM works WHERE verdict = ?",
                        (QUOTE_GRADE,)).fetchone()[0]
    n_top_note = con.execute(
        "SELECT COUNT(*) FROM works WHERE verdict = ? AND note_impression IS NOT NULL"
        " AND TRIM(note_impression) <> ''", (QUOTE_GRADE,)).fetchone()[0]
    con.close()
    return {"評価が付いた作品": n_rated, "感想が書かれた作品": n_note,
            "◎ の作品": n_top, "◎ のうち感想がある": n_top_note}


# ---------------------------------------------------------------- 画面に出す部品
#
# **HTML はここで組む。** 差し込み先（`render_recommend.reason_rows` と `wait_row`、
# `app.page_rate`）は別の作業で書き換わっている最中なので、**向こうが落ち着いたときに
# 1 行入れるだけで済む形**にしてある。文言と組み立ての判断はこのファイルに集める。


def quote_row(persons: list[str], notes_by_person: dict[str, list[dict]]) -> str:
    """推薦の理由に添える「あなたの言葉」の 1 行。無ければ空文字。

    **主語は作品である。** 感想は作品について書いたものなので、
    「〈人名〉について、あなたはこう書いています」とは書かない ── **作品単位の評価を、
    その作品に関わった個人への評価として読ませてはいけない。** 出すのは
    「その人が関わった作品に、あなたはこう書いています」という事実だけである。

    **1 行だけ出す。** 4 人ぶん並べると理由の欄が感想の一覧になり、
    いま決めたいこと（この公演を観るか）から目が離れる。
    """
    for p in persons:
        ws = notes_by_person.get(p) or []
        if not ws:
            continue
        w = ws[0]
        times = f"（{w['times']} 回観た作品です）" if (w.get("times") or 1) > 1 else ""
        return (f'<li class="rs q"><b>あなたの言葉</b> '
                f'《{_e(w["title"])}》に「{_e(clip(w["note"]))}」と書いています'
                f'<span class="n">── 上の {_e(p)} さんが関わった作品です{_e(times)}</span></li>')
    return ""


def wait_note_html(work_key: str, note: str = "", *, open_: bool = False) -> str:
    """評価待ちの行に置く感想の欄。**評価を押すまで開かない。**

    **評価が先である。** 観た帰りに開く画面なので、15 行ぶんの入力欄が最初から開いていると、
    **評価を付ける画面が「書かされる画面」に見える。** 押した直後に 1 つだけ開けば、
    いま気持ちが動いている 1 件にだけ場所ができる。

    **任意であることを書く。** 書かなくても評価は成立し、推薦の材料にもなる ──
    感想が足すのは「◎ の中のどれが自分にとっての決め手だったか」だけである。

    **欄の中で返りを約束しない。** 引用が出るのは ◎ の作品だけなので（推薦の理由は ◎ を
    付けた作品の作り手から作る）、**どの評価でも同じ欄に「次にお見せします」と書くと、
    × や △ に書いた人に対して嘘になる。** 返りは束の頭の文で、条件付きで書く。

    **開いた状態で出す場所もある**（`open_`）── ◎ に感想を書き足す 1 枚では、書くこと
    自体がその画面の用なので、押して開かせる段を挟む理由が無い。
    """
    return (f'<div class="wnote"{"" if open_ else " hidden"}>'
            f'<textarea data-note="{_e(work_key)}" rows="2"'
            f' placeholder="どう感じましたか（任意）">{_e(note)}</textarea>'
            f'<span class="said"></span></div>')


def pending_html(rows: list[dict], n_all: int) -> str:
    """◎ なのに感想が無い作品の束。**有限であることを件数で示す。**

    **「まだ 30 件あります」とだけ書くと終わらない作業に見える。** 出すのは 15 件で、
    残りが何件かを併記する ── 1 セット答えれば次のセットに入れ替わる。
    """
    if not rows:
        return ('<p class="empty">◎ を付けた作品には、すべて感想が書かれています。</p>')
    more = (f"残りは次の {n_all - len(rows)} 件です。" if n_all > len(rows) else "")
    # **行の形は評価待ちと同じものを使う**（`RR.wait_shell`）。ここで自分で組んでいた
    # ため、`.wait` が 3 列（耳・ミシン目・本文）に変わったときに崩れた ── 余白と間隔を
    # 持つ `.wbody` を省いていたので、**題名と日付がくっつき、入力欄が題名の長さで
    # 左右にずれていた**（起案者の指摘・2026-08-24）。
    # **取り込みは関数の中で行う** ── `render_recommend` はこの module を取り込むので、
    # 頭に書くと循環する
    import render_recommend as RR                                   # noqa: PLC0415
    items = "".join(
        RR.wait_shell(
            w, f'<span class="wt">{_e(w["title"])}</span>'
               f'<span class="wm">{_e(_jdate(w.get("first_date")))}'
               + (f'・{w["times"]} 回観た' if (w.get("times") or 1) > 1 else "")
               + "</span>"
               + wait_note_html(w["work_key"], w.get("note_impression") or "", open_=True))
        for w in rows)
    return (f'<p class="lead">◎ を付けたのに感想が無い作品が {n_all} 件あります。'
            f'<b>思い出せるものだけで結構です。</b>{_e(more)}<br>'
            f'一文書いておくと、次に同じ作り手の公演が出てきたときに、'
            f'その言葉をおすすめの理由に添えて出します。</p>'
            f'<div class="waits">{items}</div>')


def _jdate(s: str) -> str:
    """`2024-12-11` を `2024年12月11日` にする。**日付の表記は画面の他と揃える。**

    **耳に出ている日付を、行の中でも出す必要がある。** 耳（`_wait_stub`）は
    `aria-hidden` なので、行から日付を落とすと**読み上げでは日付がどこにも無くなる。**
    表記だけを揃えて、重複はそのまま残す（耳と行の重複は `_wait_stub` の約束である）。
    """
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", (s or "")[:10])
    return f"{int(m[1])}年{int(m[2])}月{int(m[3])}日" if m else "日付不明"


def _e(s) -> str:
    return html.escape(str(s or ""), quote=True)


if __name__ == "__main__":
    print(stats())
    bp = by_person()
    print(f"引用を出せる作り手: {len(bp)} 名")
    for p, ws in sorted(bp.items(), key=lambda kv: -len(kv[1]))[:12]:
        print(f'  {p}: 《{ws[0]["title"][:22]}》「{clip(ws[0]["note"], 40)}」')
