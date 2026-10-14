"""The person-score index and the recommendation cards for the synthetic catalogue
(catalogue.py), as D1 statements: what the daily batch uploads
(build_recommend_index.py, build_cards.py). Used by test/recommend-screen.test.js.

    python3 test/screens/recommend_fixture.py
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "scripts"
sys.path.insert(0, str(HERE))
import catalogue as CAT                                              # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sql() -> list[str]:
    BI, BC = _load("build_recommend_index"), _load("build_cards")
    import app as APP
    import user_recommender as UR
    pool = UR.candidate_pool({}, CAT.CANDIDATES)
    fields = {c["stage_id"]: c["fields"] for c in CAT.CANDIDATES if c["fields"]}
    index = BI.build_index(pool, fields, APP.group_of)
    today = datetime.date.fromisoformat(CAT.TODAY)
    return BI.to_sql(index, BI.version_of(index)) + BC.to_sql(BC.build(pool, {}, today))


def golden() -> list[dict]:
    """Cards filled by build_cards.compose (the reference for src/screens/cards.js)."""
    BC = _load("build_cards")
    import render_recommend as RR
    import user_recommender as UR
    today = datetime.date.fromisoformat(CAT.TODAY)
    pool = UR.candidate_pool({}, CAT.CANDIDATES)
    stages, cards = BC.stage_dicts(pool, {}, today), BC.build(pool, {}, today)
    tickets = [{"date": "2026-11-02", "time": "18:30", "confirmed": 1},
               {"date": "2026-11-05", "time": "", "confirmed": 0, "sid": "101"}]
    out = []
    for sid, r in sorted(cards.items()):
        t = r["html"]
        c = stages[sid]
        lo, hi = RR._period_start(c.get("period") or ""), RR._period_end(c.get("period") or "")
        for mode, kw in (("recommend", {"rank": 7, "why": "<li>x $& y</li>", "poster": "<img>"}),
                         ("interest", {"note": "俳優甲 & <乙> $1"}), ("interest", {}),
                         ("favourite", {"why": "<li>登録</li>"}),
                         ("owned", {"tickets": tickets}), ("owned", {"tickets": []}),
                         ("recommend", {"top": "<li>出演 $&</li>"}), ("interest", {"top": "<li>題名</li>"})):
            args = dict(kw)
            if mode == "owned":
                args = {"mytix": BC.mytix_html(c, kw["tickets"])}
            out.append({"template": t, "sid": sid, "mode": mode, "kw": kw,
                        "start": lo.isoformat() if lo else "", "end": hi.isoformat() if hi else "",
                        "html": BC.compose(t, sid, mode, **args)})
    return out


if __name__ == "__main__":
    print(json.dumps({"sql": sql(), "golden": golden()}, ensure_ascii=False))
