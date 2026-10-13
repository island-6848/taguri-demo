"""Synthetic public catalogue shared by the Python and Worker screen tests.

No private data. `files()` is what the Python app reads under data/; the
Worker gets the same catalogue through the D1 build scripts.
"""
from __future__ import annotations

import json

TODAY = "2026-10-12"


def _stage(sid, title, period, *, group="劇団甲", theater="劇場A", pref="東京都", fields=None):
    return {"stage_id": str(sid), "title": title, "group": group, "theater": theater, "pref": pref,
            "period": period, "fields": fields or {}, "url": f"https://stage.example/{sid}"}


CANDIDATES = [
    _stage(101, "舞台ひとつめ", "2026/11/01~2026/11/10", fields={"出演": "俳優甲、俳優乙", "演出": "演出家丙"}),
    _stage(102, "舞台ふたつめ", "2026/10/01~2026/10/20", group="劇団乙", theater="劇場B", pref="大阪府",
           fields={"出演": "俳優乙", "脚本": "作家丁"}),
    _stage(103, "終わった舞台", "2026/08/01~2026/08/10", fields={"出演": "俳優甲"}),
]


def files() -> dict[str, str]:
    jl = lambda rows: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    raw = {"ranked": [], "recommend": [], "n_cand": 0, "n_scored": 0}
    return {
        "data/review/candidates.jsonl": jl(CANDIDATES),
        "data/review/favourites.jsonl": "",
        "data/review/calendar.jsonl": "",
        "data/review/picked.jsonl": "",
        "data/review/recommend2.json": json.dumps(raw, ensure_ascii=False),
    }


def worker_sql() -> list[str]:
    """The same catalogue as D1 statements (what the EC2 batch uploads)."""
    return []


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--sql"]:
        print(json.dumps({"today": TODAY, "sql": worker_sql()}, ensure_ascii=False))
