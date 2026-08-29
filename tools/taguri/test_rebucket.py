#!/usr/bin/env python3
"""`app._rebucket`（反応の当て直し）の検査。

    python3 tools/taguri/test_rebucket.py

起案者の報告（2026-08-26）── 「公演カレンダーで『母さん、ラブソングです。』
『ゴースト』『第三舞台2026『パレイドリア』』『舞台「てらこや青義堂 師匠、走る」』
って２個ずつある公演があるのはなぜ？」。

**お気に入り（`c["a"]`、登録した名前に当たった公演）を無条件に足す 1 行が、
下の if/elif チェーンより先にあった。** 「興味あり」を押した公演でも `c["a"]` が
真なら、まず無条件でお気に入りに足され、そのあと `elif interest==1` でも
`tracking` に足される ── 同じ公演が 2 つの束に入っていた。stage_calendar.py
の `rows_of` は「同じ作品が 2 つの束に入ることはない」ことを前提にしているので、
そのまま公演カレンダーに 2 行として出ていた。

**「持っている」だけは例外のまま残す**（起案者の指示・2026-08-26 ──「おすすめに
出ないようにして（お気に入りには出ていてよい）」）。持っている公演は、お気に入り
にも同時に出てよい ── この検査でも両立することを確かめる。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import app as APP                                                  # noqa: E402
import feedback as FB                                               # noqa: E402

ok = fail = 0


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK  {name:<56} {got if got is not None else ''}")
    else:
        fail += 1
        print(f"  NG  {name:<56} ← {got!r}")


def _rebucket_with(react: dict, d: dict) -> dict:
    """`FB.connect`／`reactions`／`tickets` と、メール取り込み・追加索引を
    差し替えて `_rebucket` を呼ぶ。**DB もメールも端末の状態も見ない。**
    """
    _orig_connect, _orig_reactions, _orig_tickets = FB.connect, FB.reactions, FB.tickets
    _orig_auto = APP._auto_own_from_mail
    _orig_idx = APP._upcoming_index
    class _FakeCon:
        def close(self):
            pass
    FB.connect = lambda **_kw: _FakeCon()
    FB.reactions = lambda _con: react
    FB.tickets = lambda _con: {}
    APP._auto_own_from_mail = lambda _today: None
    APP._upcoming_index = lambda: {"rows": {}}
    try:
        return APP._rebucket(d)
    finally:
        FB.connect, FB.reactions, FB.tickets = _orig_connect, _orig_reactions, _orig_tickets
        APP._auto_own_from_mail = _orig_auto
        APP._upcoming_index = _orig_idx


def _titles(rows: list) -> list:
    return [r["title"] for r in rows]


# ---------------------------------------------------------------- 実際に起きた例
# 「母さん、ラブソングです。」── お気に入り登録した「作り手23」に当たり、
# かつ「興味あり」を押してある
CAND = {"stage_id": "461734", "title": "母さん、ラブソングです。",
        "a": ['人「作り手23」'], "period": "2026/08/29 (土) 〜 2026/08/30 (日)"}
D = {"favourites": [CAND], "ranked": [], "others": [], "owned": [],
     "tracking": [], "started": []}

out = _rebucket_with({"461734": {"interest": 1}}, D)
check("興味ありを押した公演は tracking に入る",
      "母さん、ラブソングです。" in _titles(out["tracking"]), None)
check("興味ありを押した公演は favourites には重ねない（実際に起きた重複の再発防止）",
      "母さん、ラブソングです。" not in _titles(out["favourites"]), None)

# ---------------------------------------------------------------- 興味なしも重ねない
out2 = _rebucket_with({"461734": {"interest": 0}}, D)
check("興味なしを押した公演は others に入る",
      "母さん、ラブソングです。" in _titles(out2["others"]), None)
check("興味なしを押した公演も favourites には重ねない",
      "母さん、ラブソングです。" not in _titles(out2["favourites"]), None)

# ---------------------------------------------------------------- 何も押していない
out3 = _rebucket_with({}, D)
check("何も押していないお気に入りは favourites に入る",
      "母さん、ラブソングです。" in _titles(out3["favourites"]), None)
check("何も押していないお気に入りは tracking には入らない",
      "母さん、ラブソングです。" not in _titles(out3["tracking"]), None)

# ------------------------------------------------- 「持っている」だけは両立する
# 起案者の指示（2026-08-26）──「おすすめに出ないようにして（お気に入りには
# 出ていてよい）」。この例外は残す
CAND_OWNED = {"stage_id": "999001", "title": "持っているお気に入り公演",
              "a": ['人「テスト」'], "period": "2099/01/01 (木) 〜 2099/01/02 (金)"}
D_OWNED = {"favourites": [CAND_OWNED], "ranked": [], "others": [], "owned": [],
           "tracking": [], "started": []}
out4 = _rebucket_with({"999001": {"owned": 1}}, D_OWNED)
check("持っている公演は owned に入る",
      "持っているお気に入り公演" in _titles(out4["owned"]), None)
check("持っている公演は、お気に入りにも同時に出る（外さない例外）",
      "持っているお気に入り公演" in _titles(out4["favourites"]), None)

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
