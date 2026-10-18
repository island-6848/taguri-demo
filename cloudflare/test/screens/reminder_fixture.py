"""digest.panel on hand-made candidates: the reference for src/screens/reminder.js
(test/reminder.test.js). Covers tours in one region and across regions, a stage
listed twice by two sources, answered stages, tickets, prefectures and both weeks.

    python3 test/screens/reminder_fixture.py
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


def cand(sid, title, period, pref="東京都", theater="劇場A", venue="", group="劇団甲", **kw):
    return {"stage_id": sid, "title": title, "period": period, "pref": pref, "theater": theater,
            "venue": venue or theater, "group": group, "price": kw.get("price", ""), "url": kw.get("url", "")}


CANDS = [
    cand("201", "今日の舞台", "2026/10/12 ～ 2026/10/20"),
    cand("202", "明日の舞台 & <夜>", "2026/10/13 ～ 2026/10/13", pref="大阪府", theater="劇場B"),
    # A tour: Tokyo and Kanagawa (one region, one row), Osaka (another region, its own row)
    cand("203", "旅の舞台", "2026/10/15 ～ 2026/10/18"),
    cand("204", "旅の舞台", "2026/10/16 ～ 2026/10/17", pref="神奈川県", theater="劇場K"),
    cand("205", "旅の舞台", "2026/10/16 ～ 2026/10/19", pref="大阪府", theater="劇場O"),
    # The same stage from two sources (calendar ids start with "cal")
    cand("cal9", "『流れる雲よ』27年連続", "2026/10/14 ～ 2026/10/20", theater="劇場C"),
    cand("206", "「流れる雲よ」～令和～", "2026/10/14 ～ 2026/10/20", theater="劇場C"),
    cand("207", "来週の舞台", "2026/10/21 ～ 2026/10/30", pref="北海道", theater="劇場H"),
    cand("208", "答えた舞台", "2026/10/17 ～ 2026/10/18", pref="愛知県", theater="劇場N"),
    cand("209", "持っている舞台", "2026/10/18 ～ 2026/10/25"),
    cand("210", "遠い舞台", "2026/12/01 ～ 2026/12/03"),
]
STATUS = {"208": "declined", "209": "owned", "201": "tracking", "204": "favourites"}
TICKETS = {"209": [{"date": "2026-10-19", "time": "18:00", "confirmed": 1},
                   {"date": "2026-10-11", "time": "", "confirmed": 1},
                   {"date": "2026-10-24", "time": "", "confirmed": 0}]}


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import digest as DG
    import render_recommend as RR
    RR.date = FrozenDate
    DG.all_candidates = lambda: [dict(c) for c in CANDS]
    keys = {"declined": "others", "favourites": "favourites", "tracking": "tracking", "owned": "owned"}
    d = {v: [] for v in keys.values()}
    for sid, k in STATUS.items():
        c = next(c for c in CANDS if c["stage_id"] == sid)
        d[keys[k]].append({"stage_id": sid, "title": c["title"], "venue": c["venue"]})
    cases = []
    for prefs in ([], ["大阪府"], ["東京都", "神奈川県", "大阪府", "北海道"], ["沖縄県"]):
        for week in ("this", "next"):
            cases.append({"prefs": prefs, "week": week,
                          "html": DG.panel(d, TODAY, prefs, week)})
    # 券の有る無しで違う「直近の観劇予定」の枠は外した（起案者の指示 2026-10-18）。券の有る無しの 2 通りは比べない
    print(json.dumps({"today": TODAY.isoformat(), "cands": CANDS, "status": STATUS, "owned": d["owned"],
                      "tickets": TICKETS, "cases": cases}, ensure_ascii=False))


if __name__ == "__main__":
    main()
