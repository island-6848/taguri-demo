#!/usr/bin/env python3
"""開幕リマインドの検査。

    python3 tools/taguri/test_digest.py
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import digest as DG                                                # noqa: E402

ok = fail = 0
TODAY = dt.date(2026, 8, 26)


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK  {name:<48} {got if got is not None else ''}")
    else:
        fail += 1
        print(f"  NG  {name:<48} ← {got!r}")


# ---------------------------------------------------------------- 候補の重複除去
# **起案者の訂正（2026-08-26）── 「候補と興味ありと手持ちだけじゃなくて、全部出して
# ほしい」に対する検査。** 好みのスコアに関係なく、候補ファイル全部を対象にする。
_orig_jsonl = DG._jsonl


def fake_jsonl(path):
    data = {DG.CAND: [{"stage_id": "1", "title": "候補A", "period": "2026/08/26 (水)"},
                       {"stage_id": "2", "title": "候補B", "period": "2026/08/27 (木)"}],
            DG.FAV: [{"stage_id": "2", "title": "候補B（重複）",
                      "period": "2026/08/27 (木)"},
                     {"stage_id": "3", "title": "お気に入り経由", "period": "2026/08/28 (金)"}],
            DG.CALENDAR: [{"stage_id": "4", "title": "カレンダー経由",
                          "period": "2026/08/29 (土)"}],
            DG.PICKED: [{"stage_id": "5", "title": "拾った公演", "period": "2026/08/30 (日)"}]}
    return data.get(path, [])


DG._jsonl = fake_jsonl
cands = DG.all_candidates()
check("4 つのファイルを合わせる", len(cands) == 5, len(cands))
check("重複は先に読んだファイルの行を残す（候補B が 2 つにならない）",
      sum(1 for c in cands if c["stage_id"] == "2") == 1)
check("先に読んだ行の題名が残る", next(c for c in cands if c["stage_id"] == "2")["title"] == "候補B")
DG._jsonl = _orig_jsonl

# ---------------------------------------------------------------- 取得元が違うだけの二重登録
#
# 起案者の指摘（2026-08-26・2 度目）──「『流れる雲よ』とか『どんでん』が２個ある
# けどなんで？」。実データから採った、候補（数字の stage_id）とカレンダー（cal 始まり）
# の題名の組。
REAL_A = {"stage_id": "449654", "title": "『流れる雲よ』27年連続再演舞台!!",
          "theater": "シアターサンモール", "period": "2026/08/26 (水) ～ 2026/09/06 (日)"}
REAL_A2 = {"stage_id": "cal57806", "title": "「流れる雲よ」～令和八年より愛を込めて～",
           "theater": "シアターサンモール", "period": "2026/08/26 ~ 2026/09/06"}
REAL_B = {"stage_id": "473948", "title": "『どんでんー私、反省期ー』",
          "theater": "「劇」小劇場", "period": "2026/08/26 (水) ～ 2026/08/30 (日)"}
REAL_B2 = {"stage_id": "cal58087", "title": "どんでん -私、反省期-",
           "theater": "「劇」小劇場", "period": "2026/08/26 ~ 2026/08/30"}
check("緩い題名は、括弧のあとの言い回しの違いを無視する",
      DG._loose_title(REAL_A["title"]) == DG._loose_title(REAL_A2["title"]),
      (DG._loose_title(REAL_A["title"]), DG._loose_title(REAL_A2["title"])))
check("緩い題名は、長音符とハイフンの違いも無視する",
      DG._loose_title(REAL_B["title"]) == DG._loose_title(REAL_B2["title"]),
      (DG._loose_title(REAL_B["title"]), DG._loose_title(REAL_B2["title"])))

deduped = DG._dedupe_cross_source([REAL_A, REAL_A2, REAL_B, REAL_B2])
check("会場・日程・緩い題名が揃えば 1 本にまとまる（実際の重複が消える）",
      len(deduped) == 2, len(deduped))
check("残るのは候補（cal で始まらない）側",
      {r["stage_id"] for r in deduped} == {"449654", "473948"},
      {r["stage_id"] for r in deduped})

# **日程は生の文字列ではなく `period_start`／`period_end` で揃えてから比べる**（実測 ──
# 候補側は曜日の注記入り、カレンダー側は無しで、生の文字列では一致しない）。
# 上の「1 本にまとまる」検査は、この 2 つの `period` 文字列が違うままでも
# 束ねられていることの確認でもある
check("候補とカレンダーで期間の生の文字列は違う（それでも束ねられている）",
      REAL_A["period"] != REAL_A2["period"], (REAL_A["period"], REAL_A2["period"]))

# **会場・日程だけの一致では束ねない。** 同じ会場・同じ日程で行われる別の演目・別の
# 回を、誤って 1 本にしないことの確認（実データにあった実例）
DIFF1 = {"stage_id": "463390", "title": "青山能〈9月〉1部",
         "theater": "銕仙会能楽研修所", "period": "2026/09/27 (日) ～ 2026/09/27 (日)"}
DIFF2 = {"stage_id": "463391", "title": "青山能〈9月〉2部",
         "theater": "銕仙会能楽研修所", "period": "2026/09/27 (日) ～ 2026/09/27 (日)"}
check("同じ会場・同じ日程でも、緩い題名まで一致しなければ束ねない（別の回を潰さない）",
      len(DG._dedupe_cross_source([DIFF1, DIFF2])) == 2, None)

# **緩い題名だけの一致では束ねない。** 会場が違う無関係な同名の演目を、誤って
# 1 本にしないことの確認（実データにあった実例 ── 劇場3のバレエと、
# 別会場の無関係な演目が、どちらも「海賊」という短い題名を持つ）
KAIZOKU1 = {"stage_id": "468993", "title": "「海賊」プロローグ付 全3幕",
            "theater": "劇場3 オペラ劇場", "period": "2026/10/01 ～ 2026/10/05"}
KAIZOKU2 = {"stage_id": "479585", "title": "海賊",
            "theater": "戸塚区民文化センターさくらプラザ", "period": "2026/10/01 ～ 2026/10/05"}
check("会場が違えば、緩い題名が一致しても束ねない",
      len(DG._dedupe_cross_source([KAIZOKU1, KAIZOKU2])) == 2, None)

# ---------------------------------------------------------------- 週の全部（好みで絞らない）
D = {"tracking": [{"title": "興味あり・3日後", "period": "2026/08/29 (土)",
                    "venue": "劇場C", "stage_id": "3"}],
     "favourites": [{"title": "お気に入り・明日", "period": "2026/08/27 (木)",
                      "venue": "劇場D", "stage_id": "4"}],
     "others": [{"title": "興味なし・4日後", "period": "2026/08/30 (日)",
                 "venue": "劇場F", "stage_id": "6"}],
     "owned": [{"title": "持っている・5日後", "period": "2026/08/31 (月)",
                "venue": "劇場G", "stage_id": "7"}]}


def fake_all():
    return [{"stage_id": "1", "title": "未回答・本日", "period": "2026/08/26 (水)"},
            {"stage_id": "8", "title": "未回答・8日後（窓の外）", "period": "2026/09/03 (木)"},
            {"stage_id": "3", "title": "興味あり・3日後", "period": "2026/08/29 (土)",
             "venue": "劇場C"},
            {"stage_id": "4", "title": "お気に入り・明日", "period": "2026/08/27 (木)",
             "venue": "劇場D"},
            {"stage_id": "6", "title": "興味なし・4日後", "period": "2026/08/30 (日)",
             "venue": "劇場F"},
            {"stage_id": "7", "title": "持っている・5日後", "period": "2026/08/31 (月)",
             "venue": "劇場G"}]


DG.all_candidates = fake_all
wk = DG.week_all(D, TODAY)
all_titles = [r["title"] for day, rows in wk["days"] for r in rows]
check("好みでスコアされていない公演（未回答）も出る",
      "未回答・本日" in all_titles, all_titles)
check("興味なし・持っている公演も落とさずに出す ── これが「全部」の本体",
      {"興味なし・4日後", "持っている・5日後"} <= set(all_titles), all_titles)
check("窓の外（8 日後）は出ない", "未回答・8日後（窓の外）" not in all_titles)
check("7 日以内の 5 件が出る（窓の外の 1 件を除く）", wk["n"] == 5, wk["n"])
check("日付ごとに束ねてある", len(wk["days"]) == 5, [d.isoformat() for d, _ in wk["days"]])

kind_of = {r["title"]: r["kind_key"] for _d, rows in wk["days"] for r in rows}
check("反応の種類を正しく振り分ける",
      kind_of == {"未回答・本日": "unanswered", "興味あり・3日後": "tracking",
                 "お気に入り・明日": "favourites", "興味なし・4日後": "declined",
                 "持っている・5日後": "owned"}, kind_of)

# ---------------------------------------------------------------- 帯そのもの（HTML）
h = DG.panel(D, TODAY, {})
check("見出しが 2 つ出る", "今週開幕する公演（全部）" in h and "直近の観劇予定" in h)
check("日付の見出しが並ぶ", h.count("<h3>") == 5, h.count("<h3>"))
# **三択が付くのは「未回答」だけ。**（起案者の指摘・2026-08-26 ──「すでに興味ありとか
# 評価してる公演には『興味あり』などのボタンを表示しないでください」で「興味あり」を外した）
check("未回答 には三択が付く",
      h.count('data-stage="1"') and 'data-stage="1"' in h and
      h[h.index('data-stage="1"'):].split("</li>")[0].count('class="btns"') == 1)
check("興味あり には三択を置かない ── 今回の訂正の本体",
      h[h.index('data-stage="3"'):].split("</li>")[0].count('class="btns"') == 0)
check("お気に入り には三択を置かない（既存の約束）",
      h[h.index('data-stage="4"'):].split("</li>")[0].count('class="btns"') == 0)
check("興味なし には三択を置かない（決着済み）",
      h[h.index('data-stage="6"'):].split("</li>")[0].count('class="btns"') == 0)
check("持っている には三択を置かない（決着済み）",
      h[h.index('data-stage="7"'):].split("</li>")[0].count('class="btns"') == 0)
def _li_of(h, stage_id):
    """`data-stage="{id}"` を含む `<li ...>` の開始タグ全体を取り出す。"""
    m = re.search(r'<li class="[^"]*" data-stage="' + stage_id + r'">', h)
    return m.group(0) if m else ""


check("本日開幕には急ぎの印が付く（<li> の class に dgurgent が入る）",
      "dgurgent" in _li_of(h, "1"), _li_of(h, "1"))
check("3 日後には急ぎの印が付かない",
      "dgurgent" not in _li_of(h, "3"), _li_of(h, "3"))
check("空のときは「ありません」と言い切る（0 件の帯）",
      "ありません" in DG.panel({}, TODAY, {}))
check("券が無いときは入れる先を案内する",
      "/tickets?t=__TAGURI_TOKEN__" in DG.panel({}, TODAY, {}))


# ---------------------------------------------------------------- 直近予定（券だけ）── 未変更の確認
TICKETS = {"10": [{"date": "2026-09-01", "time": "18:00", "confirmed": 1}],
           "11": [{"date": "2026-09-15", "time": "", "confirmed": 0}],
           "12": [{"date": "2026-08-20", "time": "", "confirmed": 1}]}
OWNED = [{"title": "券あり公演", "venue": "劇場E", "stage_id": "10"},
         {"title": "券あり・確定前", "venue": "劇場F", "stage_id": "11"},
         {"title": "券は今日より前", "venue": "劇場G", "stage_id": "12"}]
tk = DG.near_tickets(OWNED, TICKETS, TODAY)
tk_titles = [r["title"] for r in tk["rows"]]
check("今日以降の券だけが出る", tk_titles == ["券あり公演", "券あり・確定前"], tk_titles)
check("確定前の券にも印が付く",
      any(not r["confirmed"] for r in tk["rows"] if r["title"] == "券あり・確定前"))

# ---------------------------------------------------------------- お気に入りだけ色を持つ
#
# 起案者の指示（2026-08-26）──「サイトで統一してお気に入りにはこのテーマに合う
# 黄色（オレンジ寄りにして色を見やすいように）をつけてください」。封蝋
# （`RR.STYLE` の `--wax`）と同じ色を、行の左線・札の枠に差し込む。**興味あり
# （`--curtain`）とは別の色**であることも確かめる ── 混ざると「強調している」
# ことしか分からず、どちらの状態かが色からは読めなくなる
print("\nお気に入りだけ色を持つ")
check("お気に入りの行の左線は封蝋と同じ色（--wax）",
      ".dgli.fav{border-left:3px solid var(--wax)}" in DG.STYLE, None)
check("お気に入りの札の枠も --wax",
      ".dgk.fav{border:1px dashed var(--wax);color:var(--wax)}" in DG.STYLE, None)
check("興味ありは --wax ではなく --curtain のまま（お気に入りと混ざらない）",
      ".dgli.trk{border-left:3px solid var(--curtain)}" in DG.STYLE, None)

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
