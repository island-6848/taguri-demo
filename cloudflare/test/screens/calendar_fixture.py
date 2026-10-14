"""stage_calendar.panel / add_ticket_button_html on hand-made lists: the reference for
src/screens/calendar.js (test/calendar.test.js).

    python3 test/screens/calendar_fixture.py
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TODAY = _dt.date(2026, 10, 12)


class FrozenDate(_dt.date):
    @classmethod
    def today(cls):
        return cls(TODAY.year, TODAY.month, TODAY.day)


def c(sid, title, period, pref="東京都", venue="劇場A"):
    return {"stage_id": sid, "title": title, "period": period, "pref": pref, "venue": venue}


D = {
    "owned": [c("301", "持っている舞台", "2026/10/10 ～ 2026/11/03"),
              c("302", "持っている舞台", "2026/11/20 ～ 2026/11/22", pref="大阪府", venue="劇場O"),
              c("303", "一日 & <夜>", "2026/12/24 ～ 2026/12/24", pref="北海道", venue="劇場H")],
    "tracking": [c("304", "興味の舞台", "2026/10/01 ～ 2026/10/31", pref="愛知県", venue="劇場N"),
                 c("305", "終わった興味", "2026/09/01 ～ 2026/09/30"),
                 c("306", "来年の舞台", "2027/01/05 ～ 2027/01/09", pref="福岡県", venue="劇場F"),
                 c("301", "持っている舞台", "2026/10/10 ～ 2026/11/03")],
    "favourites": [c("307", "遠い先の舞台", "2027/12/01 ～ 2027/12/05"),
                   c("308", "お気に入りの舞台", "2026/10/20 ～ 2026/10/22", pref="", venue="")],
}
TICKETS = {"301": [{"date": "2026-10-15", "time": "13:00", "confirmed": 1},
                   {"date": "2026-10-15", "time": "18:00", "confirmed": 1},
                   {"date": "2026-11-02", "time": "", "confirmed": 0},
                   {"date": "2026-12-01", "time": "", "confirmed": 1}],
           "302": [{"date": "2026-11-21", "time": "14:00", "confirmed": 1}]}


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import render_recommend as RR
    import stage_calendar as SC
    RR.date = FrozenDate
    cases = []
    for kinds, prefs in ((None, None), ({"owned"}, None), (None, {"大阪府", "東京都"}), ({"tracking"}, {"沖縄県"})):
        cases.append({"kinds": sorted(kinds) if kinds is not None else None,
                      "prefs": sorted(prefs) if prefs is not None else None,
                      "html": SC.panel(D, TODAY, TICKETS, [], kinds, prefs)})
    print(json.dumps({"today": TODAY.isoformat(), "d": D, "tickets": TICKETS, "cases": cases,
                      "add": SC.add_ticket_button_html(D, TODAY, TICKETS),
                      "empty": SC.panel({}, TODAY, {}, [], None, None)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
