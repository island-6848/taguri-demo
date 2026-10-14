"""Build the D1 rec_card table (migration 0017): each coming stage's recommendation
card, rendered once a day by the Python screen itself.

    python3 cloudflare/scripts/build_cards.py --output /tmp/cards.sql

The recommend screen moved to the Worker (起案者の指示 2026-10-14「おすすめの画面を移して」).
Everything on a card but the rank, the reasons and the poster depends only on
the stage, so it is rendered here with `render_recommend.ticket` (the function
the Python screen uses) and the Worker fills three markers per request:

- RANK_MARK   in the stub's number ("No.<!--rank-->")
- WHY_MARK    inside <ul class="why"> (the user's reasons)
- POSTER_MARK inside <div class="pcol"> (the poster, if one is in R2 yet:
  posters are uploaded after this step, so the card cannot know)

Only public catalogue fields are used: no user's hand-entered credits, notes or
reactions. Dates on a card (初日／最終日 in the stub, finished tour dates, 発売)
are as of `--today`; the daily run renders them again.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))

_spec = importlib.util.spec_from_file_location("build_recommend_index", HERE / "build_recommend_index.py")
BI = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BI)

import measure_nets as M                                            # noqa: E402
import recommend2 as RC                                             # noqa: E402
import render_recommend as RR                                       # noqa: E402
import user_recommender as UR                                       # noqa: E402

RANK_MARK = "<!--rank-->"
WHY_MARK = "<!--why-->"
POSTER_MARK = "<!--poster-->"
_RANK_PROBE = 99
_NO_REASON = '<ul class="why"><li class="rs none">理由を出せていません</li></ul>'
TOUR_KEYS = ("stage_id", "theater", "pref", "period", "days", "price", "url", "onsale")


def stage_dicts(pool: dict[str, dict], themes: dict, today: datetime.date) -> dict[str, dict]:
    """stage_id -> the candidate dict the Python screen hands to `ticket` (UR.prepare,
    app._overlay_one, UR.collapse_tours), for stages not yet over. `themes` is
    net_c.load_themes()."""
    out: dict[str, dict] = {}
    for sid, entry in pool.items():
        c = copy.deepcopy(entry)
        period = c.get("period") or ""
        end = RC.period_end(period)
        if end and end < today:
            continue
        if any(word in (c.get("title") or "") for word in RC.NOT_PLAY_TITLE):
            continue
        fields = c.get("fields") or {}
        c.update(stage_id=sid, days=RC.run_days(period), onsale=RC.onsale(fields, today),
                 url=c.get("url") or RC.url_of(fields.get("公式／劇場サイト", "")), tours=[])
        t = themes.get(("candidate", sid)) or {}
        c["themes"] = [e["word"] for e in (t.get("elements") or []) if e.get("word")]
        c["themes_by"] = t.get("elements_by") or ""
        if t.get("synopsis"):
            c["synopsis"] = t["synopsis"]
            c["synopsis_by"] = t.get("synopsis_by") or ""
        c["_tour"] = UR.tour_key(c.get("title") or "", c.get("group") or "", M.parse_credits(fields))
        out[sid] = c
    # Every venue of a production lists the others (schedule_html shows the whole tour,
    # marking the card's own venue), in the order collapse_tours keeps them.
    by_tour: dict[str, list[str]] = {}
    for sid in sorted(out):
        by_tour.setdefault(out[sid]["_tour"], []).append(sid)
    for sids in by_tour.values():
        for sid in sids:
            out[sid]["tours"] = [{k: out[o].get(k) or "" for k in TOUR_KEYS} for o in sids if o != sid]
    for c in out.values():
        del c["_tour"]
    return out


def card_template(c: dict) -> str:
    """`render_recommend.card` for this stage, with the three markers in place."""
    saved = RR.POSTER
    RR.POSTER = lambda _sid: POSTER_MARK
    try:
        html = RR.ticket(c, rank=_RANK_PROBE, mode="recommend")
    finally:
        RR.POSTER = saved
    probe = f'<span class="sn">No.{_RANK_PROBE:02d}</span>'
    if html.count(probe) != 1 or html.count(_NO_REASON) != 1:
        raise ValueError(f"card layout changed: markers not found for stage {c.get('stage_id')}")
    return (html.replace(probe, f'<span class="sn">No.{RANK_MARK}</span>')
                .replace(_NO_REASON, f'<ul class="why">{WHY_MARK}</ul>'))


def build(pool: dict[str, dict], themes: dict, today: datetime.date) -> dict[str, str]:
    return {sid: card_template(c) for sid, c in sorted(stage_dicts(pool, themes, today).items())}


def to_sql(cards: dict[str, str]) -> list[str]:
    """Insert a version, switch rec_meta 'rec_card' to it, drop the others."""
    ver = hashlib.sha256(json.dumps(cards, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    stmts = [f"DELETE FROM rec_card WHERE ver={BI._q(ver)};"]
    stmts += BI._inserts("rec_card", "ver,stage_id,html", [(ver, sid, h) for sid, h in sorted(cards.items())])
    stmts.append(f"INSERT INTO rec_meta(k,v) VALUES('rec_card',{BI._q(ver)}) "
                 "ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts.append(f"DELETE FROM rec_card WHERE ver<>{BI._q(ver)};")
    return stmts


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--output", required=True, type=Path, help="SQL for wrangler d1 execute --file")
    p.add_argument("--today", type=datetime.date.fromisoformat,
                   default=(datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date())
    a = p.parse_args()
    import digest as DG
    import net_c as C
    try:
        raw, _ = RR.load()
    except FileNotFoundError:
        raw = {}
    pool = UR.candidate_pool(raw, DG.all_candidates())
    if not pool:
        p.error("no candidates under data/; fetch the catalogue first")
    cards = build(pool, C.load_themes(), a.today)
    body = "\n".join(to_sql(cards)) + "\n"
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        out.write(body)
    sizes = sorted(len(h.encode("utf-8")) for h in cards.values()) or [0]
    print(json.dumps({"stages": len(cards), "sql_bytes": len(body.encode()),
                      "card_bytes": {"median": sizes[len(sizes) // 2], "max": sizes[-1]}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
