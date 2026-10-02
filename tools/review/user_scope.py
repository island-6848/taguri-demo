"""利用者ごとのデータ分離（E3）で、表を `user_id` 付きに広げる共通の手順。

`rate_performances.py`（観劇記録の 7 表）・`feedback.py`（反応・券・閲覧）・
`tools/taguri/serve.py`（観ればよかった）が、それぞれの `connect` からこれを呼ぶ。
**移行の手順を 1 か所に置く** ── 表ごとに書くと、後から `ALTER` で足した列を落とす、
主キーの並びを間違える、といった誤りが表ごとに別々に起きる。
"""

from __future__ import annotations

import sqlite3

# `tools/taguri/auth.py` の `LOCAL_USER_ID` と同じ値。これらの表に今まで書いてきたのは
# ローカル（`run.py`）の持ち主 1 人だけなので、既存の行はすべてこの値として持ち越す。
LOCAL_USER_ID = "local"


def scope_table(con: sqlite3.Connection, table: str, key: tuple[str, ...]) -> bool:
    """`table` に `user_id` を足し、主キーを `(user_id, *key)` へ広げる。**何度呼んでもよい。**

    SQLite は主キーを `ALTER TABLE` で変えられないので、正しい形の表を作って写し、
    古い表と差し替える（`rate_performances._widen_attendance_key` と同じ手法）。

    **列は `PRAGMA table_info` から組み直す。** `SCHEMA` の文面を写すと、後から
    `ALTER` で足した列が落ちる。既存の行の `user_id` は列の既定値（`LOCAL_USER_ID`）になる。

    表が無い、またはすでに `user_id` を持っていれば何もせず `False` を返す。
    """
    # (cid, name, type, notnull, dflt_value, pk)
    cols = list(con.execute(f"PRAGMA table_info({table})"))
    if not cols or any(c[1] == "user_id" for c in cols):
        return False
    defs = [f"user_id TEXT NOT NULL DEFAULT '{LOCAL_USER_ID}'"]
    for _cid, name, typ, notnull, dflt, _pk in cols:
        d = f"{name} {typ}"
        if notnull:
            d += " NOT NULL"
        if dflt is not None:
            d += f" DEFAULT {dflt}"
        defs.append(d)
    defs.append(f"PRIMARY KEY (user_id, {', '.join(key)})")
    names = ", ".join(c[1] for c in cols)
    new = f"{table}__by_user"
    with con:
        con.execute(f"DROP TABLE IF EXISTS {new}")
        con.execute(f"CREATE TABLE {new} ({', '.join(defs)})")
        con.execute(f"INSERT INTO {new} ({names}) SELECT {names} FROM {table}")
        con.execute(f"DROP TABLE {table}")
        con.execute(f"ALTER TABLE {new} RENAME TO {table}")
    return True
