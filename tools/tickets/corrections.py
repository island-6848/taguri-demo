#!/usr/bin/env python3
"""人が直した公演詳細（題名・上演日・劇場）を置く 1 か所。

## なぜこの口が要るのか

**抽出は題名を頻繁に間違える。** 実データ 129 作品のうち 24 件は括弧が閉じておらず
（「NODA・MAP第28回公演『華氏マイナス320°」「ファーム・ホール』」）、販売側の冠が
題名の一部として残っているもの（「【Premium限定】舞台『悪の花」）もある。
**これは分類ではなく抽出の失敗である。** そして `rate_performances.is_suspect` が
印を付けられたのは 5 件だけで、残りは印が付かないまま画面に並んでいた ──
**当事者は間違いに気づけるが、直す口が無かった。**

直した内容は 3 つの場所に効く。**直したことが 1 回しか効かないなら、直す価値が薄い。**

| どこに効くか | どう効くか |
|---|---|
| **いまの画面と推薦** | `load_purchases` が直した値を返すので、束ね方・上演日・劇場が即座に変わる |
| **次に届くメール**（規則の側） | 同じ発行元が同じ壊れ方をしたら、**uid が違っても**同じ直しを当てる |
| **次の LLM の情報取得** | 直しの実例を指示文に添える（`prompt_block`）。公演ページの検索語にも使う |

## 抽出した値を消さない

**直した値で `title` を上書きしない。** `data/credits/credits.jsonl` は
`(date, mail_title)` を鍵に公演ページと結び付いていて、この鍵は**抽出した題名**で
できている（8 か所が同じ鍵で引いている）。上書きすると、直した公演のクレジットが
全部引けなくなる。**直した値は `title_eff` として別に運ぶ。**

## 置き場所

`data/review/ratings.db` の `fixes` 表。`data/tickets/performances.jsonl` は
取り込みのたびに作り直されるので、そこに書くと直しが消える。
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "review" / "ratings.db"

# **受け付ける項目は列挙したものだけ**（企画書 5 章の守り 4）
FIELDS = ("title", "date", "venue", "time")
LABEL = {"title": "題名", "date": "上演日", "venue": "劇場", "time": "開演時刻"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS fixes (
    uid        TEXT NOT NULL,
    field      TEXT NOT NULL,
    value      TEXT NOT NULL,
    extracted  TEXT NOT NULL DEFAULT '',
    domain     TEXT NOT NULL DEFAULT '',
    subject    TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (uid, field)
);
"""


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def read(con: sqlite3.Connection | None = None) -> dict[str, dict[str, dict]]:
    """uid → 項目 → 行。**行ごと返す**（直す前の値も、指示文の実例に要る）。"""
    own = con is None
    con = con or connect()
    try:
        con.executescript(SCHEMA)          # 他所が開いた接続でも表が無いことがある
        out: dict[str, dict[str, dict]] = {}
        for r in con.execute("SELECT * FROM fixes"):
            out.setdefault(r["uid"], {})[r["field"]] = dict(r)
        return out
    finally:
        if own:
            con.close()


def save(con: sqlite3.Connection, uid: str, field: str, value: str, *,
         extracted: str = "", domain: str = "", subject: str = "") -> dict:
    """1 項目を確定する。**空にすると直しを取り消す**（抽出結果に戻る）。"""
    if field not in FIELDS:
        raise ValueError(f"直せない項目: {field!r}")
    value = _clean_value(field, value)
    con.executescript(SCHEMA)
    with con:
        if not value:
            con.execute("DELETE FROM fixes WHERE uid=? AND field=?", (uid, field))
            return {"uid": uid, "field": field, "value": "", "cleared": True}
        con.execute(
            "INSERT INTO fixes (uid, field, value, extracted, domain, subject, updated_at)"
            " VALUES (?,?,?,?,?,?,datetime('now','localtime'))"
            " ON CONFLICT(uid, field) DO UPDATE SET value=excluded.value,"
            " extracted=excluded.extracted, updated_at=excluded.updated_at",
            (uid, field, value, extracted, domain, subject))
    return {"uid": uid, "field": field, "value": value, "cleared": False}


def _clean_value(field: str, value: str) -> str:
    v = re.sub(r"\s+", " ", str(value or "")).strip()
    if field == "date":
        if not v:
            return ""
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError("上演日は YYYY-MM-DD で入れる")
        return v
    if field == "time":
        if not v:
            return ""
        if not re.fullmatch(r"\d{2}:\d{2}", v):
            raise ValueError("開演時刻は HH:MM で入れる")
        return v
    return v[:200 if field == "title" else 80]


# ---------------------------------------------------------------- 効かせる

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).strip().lower()


def title_by_extracted(fixes: dict[str, dict[str, dict]]) -> dict[tuple[str, str], str]:
    """(発行元, 抽出した題名) → 直した題名。

    **uid をまたいで効かせるための表である。** 同じ公演を 3 回買えばメールは 3 通来て、
    どれも同じ壊れ方をする。次に届く 1 通も同じ壊れ方をするので、**1 度直せば
    次からは直った状態で入ってくる**のが、直す作業に見合う唯一の形である。

    同じ組み合わせに違う直しがあれば採らない（どちらが正しいか機械には決められない）。
    """
    cand: dict[tuple[str, str], set[str]] = {}
    for by_field in fixes.values():
        row = by_field.get("title")
        if not row or not row.get("extracted"):
            continue
        cand.setdefault((_norm(row["domain"]), _norm(row["extracted"])),
                        set()).add(row["value"])
    return {k: next(iter(v)) for k, v in cand.items() if len(v) == 1}


def effective(row: dict, fixes: dict[str, dict[str, dict]],
              by_extracted: dict[tuple[str, str], str] | None = None) -> dict:
    """購入 1 行に、直した値を `*_eff` として足す。**抽出した値は消さない。**

    `fixed` には、どの項目が人の手で決まったかが入る。**人が確定した項目には、
    機械の判定を後から当てない**（`is_work` の除外語など） ── 探すのは機械だが、
    確定するのは人である。
    """
    got = fixes.get(str(row.get("uid") or "")) or {}
    out = dict(row)
    fixed: dict[str, str] = {}
    for f in FIELDS:
        v = (got.get(f) or {}).get("value") or ""
        if v:
            fixed[f] = v
        out[f"{f}_eff"] = v or (row.get(f) or "")
    if "title" not in fixed and by_extracted:
        # **同じ発行元が同じ題名を出したら、前に直した内容を当てる**
        v = by_extracted.get((_norm(row.get("from") or ""), _norm(row.get("title") or "")))
        if v:
            out["title_eff"], fixed["title"] = v, v
    out["fixed"] = fixed
    return out


# ---------------------------------------------------------------- LLM に返す

def examples(fixes: dict[str, dict[str, dict]] | None = None, *,
             domain: str = "", limit: int = 12) -> list[dict]:
    """指示文に添える実例。**同じ発行元のものを先に出す。**

    抽出の失敗は発行元の書式ごとに決まった形をしている（雛形の項目名を拾う・
    行の折り返しで題名が切れる）。**同じ発行元の実例が、次の 1 通にいちばん効く。**
    """
    fixes = read() if fixes is None else fixes
    rows = [r for by in fixes.values() for f, r in by.items()
            if f in FIELDS and r.get("extracted") and r["extracted"] != r["value"]]
    d = _norm(domain)
    rows.sort(key=lambda r: (0 if d and _norm(r["domain"]) == d else 1,
                             r.get("updated_at") or ""), reverse=False)
    rows.sort(key=lambda r: 0 if d and _norm(r["domain"]) == d else 1)
    seen, out = set(), []
    for r in rows:
        k = (r["field"], _norm(r["domain"]), _norm(r["extracted"]), _norm(r["value"]))
        if k in seen:
            continue
        seen.add(k)
        out.append({"field": r["field"], "domain": r["domain"], "subject": r["subject"],
                    "extracted": r["extracted"], "correct": r["value"]})
        if len(out) >= limit:
            break
    return out


def prompt_block(fixes: dict[str, dict[str, dict]] | None = None, *,
                 domain: str = "", limit: int = 12) -> str:
    """直しの実例を、LLM に渡す指示文の一部として組む。空なら空文字を返す。

    **実例だけを渡す。** 「こういう語は題名にしない」という規則に言い換えると、
    直した本人が確定していないことを機械が言い出すことになる。実例のまま渡せば、
    当たっていない一般化が指示文に混ざらない。
    """
    ex = examples(fixes, domain=domain, limit=limit)
    if not ex:
        return ""
    lines = ["", "## 当事者が過去に直した実例",
             "以下は、この抽出が出した値を当事者が手で直したものである。"
             "**同じ発行元・同じ書式では同じ間違いが起きる。**同じ形の入力には直した側を出す。"]
    for e in ex:
        lines.append(f'- {LABEL[e["field"]]}（発行元 {e["domain"] or "不明"}）: '
                     f'抽出「{e["extracted"]}」→ 正しくは「{e["correct"]}」')
    lines.append("")
    return "\n".join(lines)


def search_titles(limit: int = 0) -> dict[str, str]:
    """uid → 直した題名。**公演ページを検索する語に使う。**

    抽出が題名を切っていると公演ページが引けない（過去の公演に辿り着けたのは 27%）。
    ここが埋まれば、そのあと LLM に読ませる本文が**正しい公演のもの**になる。
    """
    fx = read()
    out = {u: by["title"]["value"] for u, by in fx.items() if by.get("title")}
    return dict(list(out.items())[:limit]) if limit else out


def stats() -> dict:
    fx = read()
    n = {f: sum(1 for by in fx.values() if by.get(f)) for f in FIELDS}
    return {"uids": len(fx), "by_field": n,
            "generalised": len(title_by_extracted(fx))}


if __name__ == "__main__":
    print(json.dumps(stats(), ensure_ascii=False, indent=1))
    print(prompt_block() or "（まだ 1 件も直していない）")
