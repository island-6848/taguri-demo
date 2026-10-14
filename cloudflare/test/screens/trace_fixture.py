"""trace.body on hand-made rated rows: the reference for src/screens/trace.js
(test/trace.test.js).

    python3 test/screens/trace_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def row(key, title, date, people, venues=()):
    return {"key": key, "title": title, "date": date, "verdict": "◎", "people": sorted(set(people)), "venues": list(venues)}


A, B, C, D, X = ("出演", "甲 & <乙>"), ("出演", "丙"), ("演出", "丁"), ("脚本", "戊"), ("照明", "己")
RATED = [
    row("舞台一#2021-03-01", "舞台一", "2021-03-01", [A, B, C, X], ["劇場A"]),
    row("舞台二#2021-03-20", "舞台二", "2021-03-20", [A, B], ["劇場B"]),
    row("舞台三#2022-01-10", "舞台三 \"夜\"", "2022-01-10", [A, C, D]),
    row("舞台四#2022-09-01", "舞台四", "2022-09-01", [B, C, D], ["劇場A"]),
    row("舞台五#2023-05-05", "舞台五", "2023-05-05", [A, B, C, D]),
    row("舞台六#2023-05-06", "舞台六", "2023-05-06", [D]),
    row("日付なし#", "日付なし", "", [A]),
]


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import trace as TR
    cases = []
    for name, via, declared in (("", "", None), ("", "", {"人": ["丙"]}), ("甲 & <乙>", "", None),
                                ("丁", "丙→甲 & <乙>", {"人": ["丁"]}), ("戊", "", None), ("いない人", "", None)):
        cases.append({"name": name, "via": via, "declared": declared,
                      "html": TR.body(RATED, name, via, declared=declared)})
    print(json.dumps({"rated": RATED, "cases": cases}, ensure_ascii=False))


if __name__ == "__main__":
    main()
