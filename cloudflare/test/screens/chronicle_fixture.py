"""chronicle.panel(owner=False) on hand-made records: the reference for
src/screens/chronicle.js (test/chronicle.test.js).

    python3 test/screens/chronicle_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def w(key, title, date, verdict="", times=1):
    return {"work_key": key, "title": title, "first_date": date, "verdict": verdict, "times": times, "bucket": "manual"}


A, B, C, D = ("出演", "甲"), ("出演", "乙"), ("演出", "丙"), ("照明", "丁")
WORKS = [w("一#2021-03-01", "一の舞台", "2021-03-01", "◎"), w("二#2021-07-01", "二 & <夜>", "2021-07-01", "○", 3),
         w("三#2022-01-10", "三の舞台はとても長い題名のついた公演でございますのでございます", "2022-01-10", "◎"),
         w("四#2022-09-01", "四の舞台", "2022-09-01", "△", 2), w("五#2023-05-05", "五の舞台", "2023-05-05", "◎"),
         w("六#2023-06-01", "六の舞台", "2023-06-01"), w("七#", "日付なし", ""), w("八#2024-01-01", "八", "2024-01-01", "◎")]
RATED = [{"key": "一#2021-03-01", "people": [A, B, C, D], "venues": ["劇場A"]},
         {"key": "二#2021-07-01", "people": [A, B], "venues": ["劇場B"]},
         {"key": "三#2022-01-10", "people": [A, C], "venues": ["劇場A"]},
         {"key": "四#2022-09-01", "people": [B, C], "venues": ["劇場C"]},
         {"key": "五#2023-05-05", "people": [A, B, C], "venues": ["劇場A"]},
         {"key": "八#2024-01-01", "people": [C], "venues": []}]


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review"), str(REPO / "tools")]
    import chronicle as CR
    CR.THEMES = Path("/nonexistent")
    cases = [{"works": WORKS, "rated": RATED, "html": CR.panel(WORKS, RATED, owner=False)},
             {"works": WORKS[:2], "rated": RATED[:2], "html": CR.panel(WORKS[:2], RATED[:2], owner=False)},
             {"works": [], "rated": [], "html": CR.panel([], [], owner=False)}]
    print(json.dumps(cases, ensure_ascii=False))


if __name__ == "__main__":
    main()
