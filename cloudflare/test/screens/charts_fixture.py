"""charts.venue_panel and charts.spiral_panel on hand-made records: the reference
for src/screens/charts.js (test/charts.test.js).

    python3 test/screens/charts_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def w(key, title, date, verdict="", times=1):
    return {"work_key": key, "title": title, "first_date": date, "verdict": verdict, "times": times}


def r(key, venues, times=1):
    return {"key": key, "venues": venues, "times": times}


SMALL = [w("一#2021-03-01", "一の舞台", "2021-03-01", "◎"), w("二#2021-07-01", "二 & <夜>", "2021-07-01", "○", 3),
         w("三#2022-01-10", "三", "2022-01-10", "△"), w("四#2022-09-01", "四 \"x\"", "2022-09-01", "×", 2),
         w("五#2023-05-05", "五", "2023-05-05", "まだ判断できない"), w("六#2023-06-01", "六", "2023-06-01"),
         w("七#", "日付なし", ""), w("八#2024-12-31", "八", "2024-12-31", "◎")]
# Every month, a leap year, many years (the ring step is clamped), ties in the peak month.
FULL = [w(f"k{i}", f"作品{i}", f"{2017 + i % 9}-{1 + i % 12:02d}-{1 + (i * 7) % 28:02d}",
          ["◎", "○", "△", "×", ""][i % 5], 1 + i % 3) for i in range(40)]
FULL.append(w("閏", "閏日", "2024-02-29", "◎"))
VENUES = [r("a", ["劇場A"]), r("b", ["劇場B", "劇場A"], 3), r("c", ["劇場C & <D>"], 2), r("d", []),
          r("e", ["劇場A"], 5)] + [r(f"v{i}", [f"館{i % 12}"]) for i in range(30)]


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import charts as CH
    print(json.dumps({"spiral": [{"works": x, "html": CH.spiral_panel(x)} for x in (SMALL, FULL, [], [SMALL[6]])],
                      "venue": [{"rated": x, "html": CH.venue_panel(x)} for x in (VENUES, VENUES[:5], [r("z", [])])]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
