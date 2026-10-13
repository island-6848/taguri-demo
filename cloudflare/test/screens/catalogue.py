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
    # One-day run (its date is part of the label), HTML-special characters, a
    # title whose title_key is empty (left out of the labels), and no theater.
    _stage(104, "一日だけの<舞台> & \"夜\"", "2026/09/05~2026/09/05", theater="劇場 'C'"),
    _stage(105, "「」", "2026/09/01~2026/09/30"),
    _stage(106, "劇場の無い舞台", "2026/12/01~2026/12/03", theater=""),
]
# Stages found on request (fetch_requests.py). 106 is also a candidate: its
# theater comes from here; 201 exists only here.
PICKED = [
    {"stage_id": "106", "title": "劇場の無い舞台（拾った）", "venue": "拾った劇場", "period": "2026/12/01~2026/12/03"},
    {"stage_id": "201", "title": "拾った舞台", "theater": "劇場D", "period": "2026/07/07"},
]


def files() -> dict[str, str]:
    jl = lambda rows: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    raw = {"ranked": [], "recommend": [], "n_cand": 0, "n_scored": 0}
    return {
        "data/review/candidates.jsonl": jl(CANDIDATES),
        "data/review/favourites.jsonl": "",
        "data/review/calendar.jsonl": "",
        "data/review/picked.jsonl": jl(PICKED),
        "data/review/recommend2.json": json.dumps(raw, ensure_ascii=False),
    }


def worker_sql() -> list[str]:
    """The same catalogue as D1 statements (what the EC2 batch uploads)."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "scripts" / "build_stage_labels.py"
    spec = importlib.util.spec_from_file_location("build_stage_labels", path)
    SL = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(SL)
    return SL.to_sql(SL.build(CANDIDATES, PICKED))


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--sql"]:
        print(json.dumps({"today": TODAY, "sql": worker_sql()}, ensure_ascii=False))
