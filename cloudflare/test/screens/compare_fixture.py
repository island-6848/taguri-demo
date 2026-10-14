"""compare.pop_note and compare.panel (作りの型) on given counts: the reference for
src/screens/compare.js (test/compare.test.js). The counts stand in for the files
compare.py reads (candidates.jsonl, credits.jsonl): the Worker counts them in D1.

    python3 test/screens/compare_fixture.py
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

POPS = [{"n": 812, "n_upcoming": 500, "n_running": 200, "n_ended": 112, "first": "2026-08-03", "last": "2027-03-20", "other": 4321},
        {"n": 5, "n_upcoming": 5, "n_running": 0, "n_ended": 0, "first": "2026-10-03", "last": "2026-10-20", "other": 0},
        {"n": 3, "n_upcoming": 0, "n_running": 0, "n_ended": 0, "first": None, "last": None, "other": 7},
        {"n": 0, "n_upcoming": 0, "n_running": 0, "n_ended": 0, "first": None, "last": None, "other": 0}]
RATED = [{"date": "2021-08-01"}, {"date": "2024-02-11"}, {"date": ""}, {"date": "2019-12-30"}]
CRAFTS = [({"翻訳劇（翻訳者がクレジットされている）": 6, "音楽劇（作曲者がクレジットされている）": 1, "原作つき（原作がクレジットされている）": 3},
           {"翻訳劇（翻訳者がクレジットされている）": 80, "原作つき（原作がクレジットされている）": 30, "振付つき（振付師がクレジットされている）": 40}, 30, 800),
          ({"翻訳劇（翻訳者がクレジットされている）": 2, "振付つき（振付師がクレジットされている）": 2}, {"翻訳劇（翻訳者がクレジットされている）": 20, "振付つき（振付師がクレジットされている）": 20}, 10, 100),
          ({}, {"翻訳劇（翻訳者がクレジットされている）": 3}, 0, 10)]


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import compare as CP
    labels = [lab for _k, lab in CP.CRAFTS]
    out = {"pop": [], "craft": []}
    for p in POPS:
        d = dict(p, first=p["first"] and datetime.date.fromisoformat(p["first"]),
                 last=p["last"] and datetime.date.fromisoformat(p["last"]))
        CP.population = lambda d=d: d
        for rated in (RATED, []):
            out["pop"].append({"pop": p, "rated": rated, "html": CP.pop_note(rated)})
    CP.theme_rows = lambda *_a, **_k: ([], 0, 0)
    for mine, world, nm, nw in CRAFTS:
        got = (CP._rows(labels, mine, world, nm, nw), nm, nw)
        CP.craft_rows = lambda _r, got=got: got
        out["craft"].append({"mine": mine, "world": world, "nMine": nm, "nWorld": nw,
                             "html": CP.panel([{"key": "x"}], owner=False)})
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
