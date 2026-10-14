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


if __name__ == "__main__":
    print(json.dumps(sql(), ensure_ascii=False))
