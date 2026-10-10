#!/usr/bin/env python3
"""公開デモの見本の記録（`app.seed_demo_works`）の検査。

    python3 tools/taguri/test_seed_demo.py

本物の保存先には触らず、一時ディレクトリの DB を使う。
"""

from __future__ import annotations

import datetime
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import feedback as FB                                               # noqa: E402
import rate_performances as R                                      # noqa: E402

TMP = Path(tempfile.mkdtemp())
R.DB = TMP / "test.db"
FB.DB = TMP / "feedback.db"
import app as APP                                                  # noqa: E402
import auth as AU                                                  # noqa: E402

ok = fail = 0


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print(f"  NG  {name}" + (f"  ← {got!r}" if got is not None else ""))


VISITOR = "f" * 32
n = APP.seed_demo_works(VISITOR)
check("見本をすべて入れる", n == len(APP.DEMO_SEED_WORKS), n)
works = APP._works(VISITOR)
check("記録の画面に見本が出る", len(works) == len(APP.DEMO_SEED_WORKS), len(works))
check("架空の評価を実在公演に結び付けない",
      all(not w["stage_id"] and not w["venue"] for w in works if w["verdict"]))
check("購入由来の96件がある", len(APP.DEMO_PURCHASE_WORKS) == 96)
check("日時の違う同日公演を両方残す",
      sum(w["last_date"] == "2024-08-14" for w in works) == 2)
check("ゴドーの会場と時刻を保存する", any(
      w["title"] == "ゴドーを待ちながら" and w["last_date"] == "2026-10-19"
      and w["venue"] == "サンモールスタジオ" and w["time"] == "19:00" for w in works))
check("新しい順に並ぶ", [w["last_date"] for w in works]
      == sorted((w["last_date"] for w in works), reverse=True))
# **ツアーの「◎○△× をつける」段で押すものが要る**
today = datetime.date.today().isoformat()
expected_waiting = sum(not s["verdict"] and s["date"] <= today for s in APP.DEMO_SEED_WORKS)
check("上演済みの未評価だけが評価待ちになる",
      len(APP.waiting_rows(VISITOR, today)) == expected_waiting)
check("将来の公演は評価待ちに入らない",
      all(w["last_date"] <= today for w in APP.waiting_rows(VISITOR, today)))

# **2 度呼んでも重ならない**
check("2 度目は何も入れない", APP.seed_demo_works(VISITOR) == 0)
check("2 度目のあとも件数は同じ", len(APP._works(VISITOR)) == len(APP.DEMO_SEED_WORKS))

# **評価を付けた分は、もう一度呼んでも見本に戻さない**
k = next(w["work_key"] for w in works if not w["verdict"])
APP.save_work_field(VISITOR, k, verdict="○")
APP.seed_demo_works(VISITOR)
check("付けた評価は残る", next(w for w in APP._works(VISITOR) if w["work_key"] == k)["verdict"] == "○")

# **持ち主の記録には混ぜない**（持ち主の記録は購入確認メールから組む本物）
check("持ち主には入れない", APP.seed_demo_works(AU.LOCAL_USER_ID) == 0)
con = R.connect()
check("持ち主の表は空のまま", not R.read_works(con, user_id=AU.LOCAL_USER_ID))
# **他の訪問者の記録とも混ざらない**（E3）
check("別の訪問者には入っていない", not R.read_works(con, user_id="e" * 32))
con.close()

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
