"""Build the D1 rec_card table (migration 0017): each coming stage's recommendation
card, rendered once a day by the Python screen itself.

    python3 cloudflare/scripts/build_cards.py --output /tmp/cards.sql

The recommend screen moved to the Worker (起案者の指示 2026-10-14「おすすめの画面を移して」).
Everything on a card but the rank, the reasons and the poster depends only on
the stage, so it is rendered here with `render_recommend.ticket` (the function
the Python screen uses). What depends on the user or the list is left as markers
(MARK … NO_NOTE below) that the Worker fills per request (src/screens/cards.js;
`compose` here is the same in Python): the stub's number or mark, the reasons,
the poster (uploaded after this step, so the card cannot know), the three-choice
buttons, the 行く日 of an owned stage, and the note boxes. One template serves
the four lists that show cards: おすすめ・興味あり・お気に入り・購入済み.

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
import re
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

# Markers the Worker fills per user (and per list: recommend / interest / favourite / owned).
MARK, WHYH, WHY, POSTER, BTNS, MYTIX, WHY_NOTE, NO_NOTE = (
    "<!--mark-->", "<!--whyh-->", "<!--why-->", "<!--poster-->", "<!--btns-->", "<!--mytix-->",
    "<!--why_note-->", "<!--no_note-->")
POSTER_MARK = POSTER
_RANK_PROBE = 99
_NO_REASON = '<li class="rs none">理由を出せていません</li>'
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
        c["tour_key"] = c.pop("_tour")
    return out


def _swap(html: str, old: str, new: str, sid) -> str:
    if html.count(old) != 1:
        raise ValueError(f"card layout changed: {old[:40]!r} not found once for stage {sid}")
    return html.replace(old, new)


def card_template(c: dict) -> str:
    """`render_recommend.ticket` for this stage with the user's parts replaced by markers.
    `compose` puts them back; the result equals `ticket` in every mode (test_build_cards)."""
    saved = RR.POSTER
    RR.POSTER = lambda _sid: POSTER
    try:
        html = RR.ticket(c, rank=_RANK_PROBE, mode="recommend")
    finally:
        RR.POSTER = saved
    sid = c.get("stage_id")
    for old, new in ((f'<span class="sn">No.{_RANK_PROBE:02d}</span>', MARK),
                     ('おすすめ理由</div><ul class="why">', f'{WHYH}</div><ul class="why">'),
                     (f'<ul class="why">{_NO_REASON}</ul>', f'<ul class="why">{WHY}</ul>'),
                     (RR.buttons(sid), BTNS),
                     (RR.why_note(sid), WHY_NOTE),
                     (RR.no_note(sid, hidden=True), NO_NOTE),
                     ('</div>\n \n <div class="when">', f'</div>\n {MYTIX}\n <div class="when">')):
        html = _swap(html, old, new, sid)
    return html


def mytix_html(c: dict, tickets: list[dict]) -> str:
    """The 行く日 box of an owned stage (render_recommend.ticket, mode "owned")."""
    import icons as IC
    E = RR.E
    rows = []
    for t in tickets:
        tm = f' {E(t["time"])}' if t.get("time") else ""
        sid, dd, tt = (E(str(t.get("sid") or c.get("stage_id") or "")), E(t["date"]), E(t.get("time") or ""))
        if t.get("confirmed"):
            note, btns = "", f'<button data-mt-del="{sid}" data-date="{dd}" data-time="{tt}">取り消す</button>'
        else:
            note = "（未確定）"
            btns = (f'<button data-mt-ok="{sid}" data-date="{dd}" data-time="{tt}">確定する</button>'
                    f'<button data-mt-del="{sid}" data-date="{dd}" data-time="{tt}">違う</button>')
        rows.append(f'<span class="mt-row{"" if t.get("confirmed") else " un"}">{int(t["date"][5:7])}月'
                    f'{int(t["date"][8:10])}日{tm}{note} {btns}</span>')
    lo, hi = RR._period_start(c.get("period") or ""), RR._period_end(c.get("period") or "")
    add_form = ('<span class="mt-add">'
                '<input type="date" class="mt-d" aria-label="行く日"'
                + (f' min="{lo.isoformat()}"' if lo else "") + (f' max="{hi.isoformat()}"' if hi else "") + '>'
                '<input type="time" class="mt-t" aria-label="時刻（任意）">'
                f'<button data-mt-add="{E(str(c["stage_id"]))}">{IC.ico("plus", 13)}行く日を追加</button>'
                '<span class="said"></span></span>')
    return f'<div class="mytix"><b>行く日</b>{"".join(rows)}{add_form}</div>'


def compose(template: str, sid: str, mode: str, *, rank: int | None = None, why: str = "",
            poster: str = "", note: str = "", mytix: str = "", top: str = "") -> str:
    """What the Worker does (src/screens/cards.js), in Python: the reference for the test.
    `top` is ticket's why_html (探す: 「ヒットした箇所」 above the card instead of the reasons)."""
    import icons as IC
    mark = {"recommend": f'<span class="sn">No.{rank:02d}</span>' if rank else "",
            "interest": f'<span class="sn done">{IC.ico("check", 15)}</span>',
            "favourite": '<span class="wax" aria-hidden="true"></span>'}.get(mode, "")
    btns = {"recommend": RR.buttons(sid),
            "interest": RR.interest_buttons(sid),
            "owned": '<button class="wnb" data-btns-open="1">回答を直す</button>' + RR.buttons(sid, hidden=True),
            "favourite": RR.owned_button(sid)}.get(mode, "")
    answer = mode in ("recommend", "interest")
    html = (template.replace('<article class="ticket recommend"', f'<article class="ticket {mode}"', 1)
            .replace(MARK, mark)
            .replace(WHYH, "なぜお知らせしているか" if mode == "favourite" else "おすすめ理由")
            .replace(WHY, why or _NO_REASON)
            .replace(POSTER, poster)
            .replace(BTNS, btns)
            .replace(MYTIX, mytix if mode == "owned" else "")
            .replace(WHY_NOTE, RR.why_note(sid, note, ask=(mode == "interest")) if answer else "")
            .replace(NO_NOTE, RR.no_note(sid, hidden=True) if answer else ""))
    if top:
        html = (html.replace('</h3>\n \n <div class="meta">',
                             f'</h3>\n <div class="whyh top">{IC.ico("eye", 14)}ヒットした箇所：</div>'
                             f'<ul class="why top">{top}</ul>\n <div class="meta">', 1)
                .replace(f'<div class="whyh">{IC.ico("eye", 14)}おすすめ理由</div><ul class="why">{why or _NO_REASON}</ul>', "", 1))
    if mode == "owned":
        # 購入済み公演: おすすめ理由の欄は出さない（起案者の指示 2026-10-15、render_recommend.ticket と同じ）
        html = re.sub(r'<div class="whyh">[\s\S]*?</ul>', "", html, count=1)
    return html.replace('<div class="act"></div>', "").replace('<div class="pcol"></div>', "")


def row(c: dict) -> dict:
    """The card and the columns stored with it (migration 0018)."""
    nz = RC.nz
    blob = c["title"] + " " + c.get("group", "") + " " + json.dumps(c.get("fields") or {}, ensure_ascii=False)
    return {"html": card_template(c), "title": c.get("title") or "", "tour": c["tour_key"],
            "start": RC.period_start(c.get("period") or ""), "end": BI._period_end(c.get("period") or ""),
            "pref": c.get("pref") or "", "gnz": nz(c.get("group", "")), "blob": nz(blob),
            "ws": "\n".join(sorted({nz(w) for w in c.get("themes") or [] if w})),
            "synz": nz(c.get("synopsis") or "")}


def build(pool: dict[str, dict], themes: dict, today: datetime.date) -> dict[str, dict]:
    return {sid: row(c) for sid, c in sorted(stage_dicts(pool, themes, today).items())}


COLS = ("html", "title", "tour", "start", "end", "pref", "gnz", "blob", "ws", "synz")


def to_sql(cards: dict[str, dict]) -> list[str]:
    """Insert a version, switch rec_meta 'rec_card' to it, drop the others."""
    ver = hashlib.sha256(json.dumps(cards, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    stmts = [f"DELETE FROM rec_card WHERE ver={BI._q(ver)};"]
    stmts += BI._inserts("rec_card", "ver,stage_id," + ",".join(COLS),
                         [(ver, sid, *(r[k] for k in COLS)) for sid, r in sorted(cards.items())])
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
    sizes = sorted(len(r["html"].encode("utf-8")) for r in cards.values()) or [0]
    print(json.dumps({"stages": len(cards), "sql_bytes": len(body.encode()),
                      "card_bytes": {"median": sizes[len(sizes) // 2], "max": sizes[-1]}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
