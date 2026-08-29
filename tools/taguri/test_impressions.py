#!/usr/bin/env python3
"""感想を集める仕組みの検査。

    python3 tools/taguri/test_impressions.py

**実データを読む検査と、作った値で確かめる検査を分けてある。** 並び順と文言は
手元の 8 件では確かめられないので（1 件の作品しか多重に観ていない）、作った値で見る。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import impressions as IM                                           # noqa: E402

ok = fail = 0


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print(f"  NG  {name}" + (f"  ← {got!r}" if got is not None else ""))


# ---------------------------------------------------------------- 並び順
W = [
    {"work_key": "a", "title": "1 回・古い", "first_date": "2023-01-01",
     "times": 1, "verdict": "◎", "note_impression": ""},
    {"work_key": "b", "title": "3 回・古い", "first_date": "2023-05-05",
     "times": 3, "verdict": "◎", "note_impression": ""},
    {"work_key": "c", "title": "1 回・新しい", "first_date": "2026-08-01",
     "times": 1, "verdict": "◎", "note_impression": ""},
    {"work_key": "d", "title": "日付なし", "first_date": "",
     "times": 1, "verdict": "◎", "note_impression": ""},
    {"work_key": "e", "title": "感想あり", "first_date": "2026-08-02",
     "times": 9, "verdict": "◎", "note_impression": "書いた"},
    {"work_key": "f", "title": "○ の作品", "first_date": "2026-08-03",
     "times": 9, "verdict": "○", "note_impression": ""},
    {"work_key": "g", "title": "行かなかった", "first_date": "2026-08-04",
     "times": 9, "verdict": "◎", "note_impression": "", "unseen": True},
]
p = IM.pending(W)
check("回数の多い順が先", [w["work_key"] for w in p][0] == "b", p)
check("同じ回数なら新しい順", [w["work_key"] for w in p][1:3] == ["c", "a"],
      [w["work_key"] for w in p])
check("日付の無い記録は最後", [w["work_key"] for w in p][-1] == "d",
      [w["work_key"] for w in p])
# **感想がある作品を聞き直さない。** 一度答えたことを聞き直す画面にしない
check("感想があるものは出さない", "e" not in [w["work_key"] for w in p])
# **◎ に限る。** 引用が出るのは ◎ の作品だけなので、○ を並べると返りの無い入力になる
check("◎ 以外は出さない", "f" not in [w["work_key"] for w in p])
# **観ていない記録に感想は無い。** 券を買って行かなかった分を聞くと、答えられない
check("行かなかった記録は出さない", "g" not in [w["work_key"] for w in p])
MANY = [dict(W[0], work_key=str(i)) for i in range(40)]
check("1 度に出すのは 15 件まで", len(IM.pending(MANY)) == IM.ROUND)
# **件数と一覧を同じ材料から数えるために要る。** 別々に数えると、束の見出しの件数が
# 中に出ている一覧と合わない（実データで 30 件と書いて 29 件しか出せなかった）
check("limit=None は全件", len(IM.pending(MANY, limit=None)) == 40)

# ---------------------------------------------------------------- 引用の文
BP = {"末満健一": [{"work_key": "x", "title": "ダーウィン・ヤング",
                    "date": "2024-06-01", "times": 4,
                    "note": "とにかく苦しくて最高だった。"}]}
q = IM.quote_row(["いない人", "末満健一"], BP)
check("感想がある人まで探す", "ダーウィン・ヤング" in q, q)
# **主語は作品である。** 作品の評価を個人への評価として読ませない
check("作品を主語にする", "《ダーウィン・ヤング》に「" in q, q)
check("人物を主語にしない", "末満健一さんについて" not in q, q)
check("関わったという事実だけを書く", "関わった作品です" in q, q)
check("観た回数を添える", "4 回観た作品です" in q, q)
check("誰も当たらなければ何も出さない", IM.quote_row(["いない人"], BP) == "")
check("内部の指標を出さない",
      not any(k in q for k in ("スコア", "寄与", "AUC", "0.")), q)

# ---------------------------------------------------------------- 引用の長さ
long_note = "あ" * 200
BP2 = {"甲": [{"work_key": "y", "title": "題", "date": "", "times": 1, "note": long_note}]}
q2 = IM.quote_row(["甲"], BP2)
check("長い感想は切る", "あ" * (IM.QUOTE_LEN + 1) not in q2)
# **切ったことが分かる形で切る。** 途中で終わった文を、本人が書いた文として読ませない
check("切ったことが分かる", "…" in q2, q2)

# ---------------------------------------------------------------- 文字の逃がし
BP3 = {"甲": [{"work_key": "z", "title": "<b>題</b>", "date": "", "times": 1,
               "note": '"& <script>'}]}
q3 = IM.quote_row(["甲"], BP3)
check("題名を逃がす", "《&lt;b&gt;題&lt;/b&gt;》" in q3, q3)
check("感想を逃がす", "<script>" not in q3, q3)

# ---------------------------------------------------------------- 評価待ちの欄
w = IM.wait_note_html("k&1", "書いた<b>")
check("押すまで開かない", "hidden" in w, w)
check("保存の宛先を持つ", 'data-note="k&amp;1"' in w, w)
check("書いた文を欄に出す", "書いた&lt;b&gt;" in w, w)
check("任意だと書く", "任意" in w, w)
# **欄の中で返りを約束しない。** 引用が出るのは ◎ だけなので、どの評価でも同じ欄に
# 「次にお見せします」と書くと、× や △ に書いた人に対して嘘になる
check("欄の中で返りを約束しない", "お見せします" not in w, w)

# ---------------------------------------------------------------- 溜まった分の束
h = IM.pending_html(IM.pending(W), 30)
check("全体の件数を出す", "30 件" in h, h)
check("残りの件数を出す", "残りは次の" in h, h)
check("思い出せるものだけでよいと書く", "思い出せるものだけ" in h, h)
check("空のときは聞かない", "すべて感想が書かれています"
      in IM.pending_html([], 0))

# ---------------------------------------------------------------- 会場が感想に紛れない
#
# **手で足すときの会場が、感想の欄に入っていた**（起案者の報告 2026-08-24）。`works` に
# 会場の列が無かったため `app.add_work` が「劇場: 〜」を `note_impression` に書いており、
# **感想の件数に数えられ、◎ の作品なら推薦の理由に「あなたの言葉」として引用された。**
# 実データでは 12 件のうち 2 件がこれで、10 名の作り手がこの引用を持ちうる状態だった。
import shutil                                                       # noqa: E402
import sqlite3                                                      # noqa: E402
import tempfile                                                     # noqa: E402

_tmp = Path(tempfile.mkdtemp())
shutil.copy(IM.DB, _tmp / "ratings.db")
sys.path.insert(0, str(ROOT / "tools" / "review"))
import rate_performances as _R                                      # noqa: E402
_R.DB = _tmp / "ratings.db"
_c = sqlite3.connect(_tmp / "ratings.db")
_c.execute("UPDATE works SET note_impression='劇場: 検査用ホール', venue=''"
           " WHERE work_key=(SELECT work_key FROM works LIMIT 1)")
_c.commit()
_c.close()
# **`connect` が移行を行う。** 開くたびに確かめるので、古い DB を持ち込んでも直る
_c2 = _R.connect()
_row = dict(_c2.execute("SELECT venue, note_impression FROM works"
                        " WHERE venue='検査用ホール'").fetchone() or {})
_left = _c2.execute("SELECT COUNT(*) FROM works"
                    " WHERE note_impression LIKE '劇場: %'").fetchone()[0]
_c2.close()
check("会場を会場の列へ移す", _row.get("venue") == "検査用ホール", _row)
# **本人が書いていないものを、書いたことにしない**
check("移したあとの感想は空にする", _row.get("note_impression") == "", _row)
check("感想に残らない", _left == 0, _left)
shutil.rmtree(_tmp, ignore_errors=True)
_R.DB = ROOT / "data" / "review" / "ratings.db"

# 引用に会場が混じらないこと（実データ）
_q = [w["note"] for ws in IM.by_person().values() for w in ws]
check("引用に「劇場: 〜」が混じらない",
      not any(n.startswith("劇場:") for n in _q), _q[:2])


# ---------------------------------------------------------------- 実データ
st = IM.stats()
check("実データを読める", st["評価が付いた作品"] > 0, st)
check("◎ の件数が全体を超えない", st["◎ の作品"] <= st["評価が付いた作品"], st)
check("感想がある ◎ は ◎ を超えない", st["◎ のうち感想がある"] <= st["◎ の作品"], st)
bp = IM.by_person()
check("引用を出せる作り手がいる", len(bp) > 0, len(bp))
check("引用の元は ◎ の作品だけ",
      all(w["note"].strip() for ws in bp.values() for w in ws))

# ---------------------------------------------------------------- 行の形
#
# **崩れていたのは、行の外枠を 2 か所で別々に組んでいたからである。** `.wait` を 3 列
# （耳・ミシン目・本文）に組み替えたときに感想の束を直しておらず、余白と間隔を持つ
# `.wbody` が無いまま文と入力欄が並んで、**題名と日付がくっつき、入力欄が題名の長さで
# 左右にずれていた**（起案者の指摘・2026-08-24）。**外枠は 1 つの関数から出す。**
import render_recommend as RR                                      # noqa: E402

W = {"work_key": "k", "title": "確かめ用の作品", "first_date": "2024-12-11",
     "times": 7, "verdict": "◎", "note_impression": "", "shows": []}
html_one = IM.pending_html([W], 1)
check("耳が付いている", 'class="wstub"' in html_one, html_one[:120])
check("ミシン目が付いている", 'class="wperf"' in html_one)
check("本文の器が付いている（余白と間隔はここが持つ）", 'class="wbody"' in html_one)
check("評価待ちと同じ外枠を通っている",
      html_one.count('<div class="wait">') == 1
      and RR.wait_shell(W, "X").startswith('<div class="wait">'))
check("感想の欄が開いている", 'class="wnote"' in html_one and 'class="wnote" hidden' not in html_one)
check("評価待ちの欄は閉じたまま", 'class="wnote" hidden' in RR.wait_row(W))
check("日付は日本語の表記", "2024年12月11日" in html_one, html_one)
check("観た回数を添える", "7 回観た" in html_one)
check("日付が無い記録は「日付不明」", "日付不明" in IM.pending_html(
    [dict(W, first_date="", shows=[])], 1))
# **`wait_row` も同じ外枠を通ること。** どちらかが自分で組み始めたら、また片方だけが
# 古い形で残る
check("評価待ちの行も外枠を共有している",
      RR.wait_row(W).startswith('<div class="wait">')
      and 'class="wstub"' in RR.wait_row(W) and 'class="wbody"' in RR.wait_row(W))

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
