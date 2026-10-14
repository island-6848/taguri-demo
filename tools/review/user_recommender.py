"""Local, request-time person recommendations from one user's saved ratings.

This connects the feedback loop; it does not claim improved accuracy. No network,
LLM, shared recommendation writes, or persistent profile cache is used here.
"""
from __future__ import annotations

import copy
import datetime

import measure_nets as M
import recommend2 as RC

VERSION = "person-feedback-v1"
BUNDLES = ("favourites", "ranked", "others", "owned", "tracking", "started", "declined", "unscored")


def independent_ratings(rows: list[dict]) -> list[dict]:
    """Count a linked production once, using its latest dated saved rating.

    Repeated visits must not inflate confidence. Unlinked records retain their
    own keys; titles alone cannot establish that two productions are identical.
    """
    grouped = {}
    for row in sorted(rows, key=lambda r: (r.get("updated_at") or r.get("date") or "",
                                            r.get("key") or "")):
        if row.get("verdict") not in M.GRADES:
            continue
        key = ("stage", str(row["stage_id"])) if row.get("stage_id") else ("work", row["key"])
        grouped[key] = row
    return list(grouped.values())


def candidate_pool(raw: dict, candidates: list[dict]) -> dict[str, dict]:
    """stage_id -> catalog entry considered for person scores.

    Shared with the Cloudflare index builder (`cloudflare/scripts/
    build_recommend_index.py`) so both see the same candidates.
    """
    pool = {}
    # Saved JSON may contain catalog entries unavailable in the source files.
    # Source catalog entries take priority and retain all theaters in a tour.
    for bundle in BUNDLES:
        for entry in raw.get(bundle) or []:
            sid = str(entry.get("stage_id") or "")
            if sid:
                pool.setdefault(sid, entry)
            for tour in entry.get("tours") or []:
                tsid = str(tour.get("stage_id") or "")
                if tsid:
                    pool.setdefault(tsid, dict(entry, **tour, tours=[]))
    for entry in candidates:
        sid = str(entry.get("stage_id") or "")
        if sid:
            pool[sid] = entry
    return pool


def prepare(raw: dict, candidates: list[dict], rated: list[dict], *,
            multipliers: dict[str, float], role_group, today=None) -> dict:
    """Build fresh scores over the whole local catalog, not the common top 15.

    This stage computes person history; personal impression adjustments follow in app. Old owner's
    theme/person scores and explanations are explicitly replaced. Favorites,
    reactions and geographic filtering are applied by the caller afterwards.
    """
    today = today or datetime.date.today()
    rated = independent_ratings(rated)
    positive = lambda v: float(v == "◎")
    base = sum(positive(r["verdict"]) for r in rated) / max(len(rated), 1)
    roster = M.build_roster(rated, positive)
    titles_of = M.person_titles(rated)       # 理由の行に出す作品名（起案者の指示 2026-10-14）
    pool = candidate_pool(raw, candidates)

    out = {"label": raw.get("label") or today.isoformat(), "today": today.isoformat()}
    out.update({k: [] for k in BUNDLES})
    scored = []
    for sid, entry in pool.items():
        c = copy.deepcopy(entry)
        period = c.get("period") or ""
        end = RC.period_end(period)
        if end and end < today:
            continue
        if any(word in (c.get("title") or "") for word in RC.NOT_PLAY_TITLE):
            continue
        fields = c.get("fields") or {}
        parts = []
        for role, person in sorted(set(M.parse_credits(fields))):
            n, o = roster.get((role, person), (0, 0))
            # A smoothing prior cannot be the only positive evidence. With an
            # all-negative history it otherwise recommends disliked people.
            if not n or not o:
                continue
            multiplier = multipliers.get(role_group(role), 1.0)
            contrib = ((o + M.SMOOTH_A) / (n + M.SMOOTH_B) - base)
            contrib *= n / (n + M.CONF_K) * RC.ROLE_W.get(role, RC.BACKSTAGE_W) * multiplier
            if contrib > 0:
                parts.append([round(contrib, 6), role, person, n])
        parts.sort(key=lambda p: (-p[0], p[1], p[2]))
        b = round(sum(p[0] for p in parts[:M.TOP_N]), 6)
        start = RC.period_start(period)
        c.update(stage_id=sid, b=b, c=0.0, total=b, why_b=parts[:6],
                 why_b_works={f"{p[1]}\t{p[2]}": titles_of[(p[1], p[2])] for p in parts[:6] if (p[1], p[2]) in titles_of},
                 person_parts=parts, why_c=[], why_v="", vr=0.0,
                 n_match=len(parts), strong=sum(multipliers.get(role_group(p[1]), 1.0)
                    for p in parts if p[1] == "出演" or p[3] >= 2),
                 cn=0.0, both=False, a=[], theme=[], declined="",
                 upcoming=not start or start > today.isoformat(),
                 opened=start if start and start <= today.isoformat() else "",
                 days=RC.run_days(period), onsale=RC.onsale(fields, today),
                 url=c.get("url") or RC.url_of(fields.get("公式／劇場サイト", "")),
                 no_c_material=True, _notes={}, recommendation_version=VERSION)
        c.setdefault("themes", [])
        scored.append(c)
    # A fixed scale preserves user multipliers; candidate-dependent p90 would
    # cancel a uniform change in person weights in this person-only model.
    for c in scored:
        c["bn"] = c["s"] = c["b"]
        out["ranked" if c["upcoming"] else "started"].append(c)
    out["ranked"].sort(key=lambda c: (-c["strong"], -c["s"], c["stage_id"]))
    out.update(recommend=[], n_cand=len(scored), n_scored=sum(c["b"] > 0 for c in scored),
               profile={"version": VERSION, "n_rated": len(rated),
                        "n_with_people": sum(bool(r.get("people")) for r in rated),
                        "n_demo": sum(r.get("verdict_source") == "demo" for r in rated),
                        "n_user": sum(r.get("verdict_source") == "user" for r in rated),
                        "n_unknown": sum(r.get("verdict_source") not in ("demo", "user") for r in rated),
                        "base": base, "n_people": len(roster)})
    return out


def finish(d: dict, *, top: int, weights: dict) -> dict:
    """After reactions/favorites, keep only explained recommendations.

    The no-score catalog remains in a separate bundle for reminders/search.
    It must not be described as matching the user's taste.
    """
    rows = d.get("ranked") or []
    keep = [c for c in rows if c.get("b", 0) > 0]
    d["unscored"] = [c for c in rows if c.get("b", 0) <= 0]
    ordered = sorted(keep, key=lambda c: (-c["strong"], -c["s"], c["stage_id"]))
    d["ranked"] = collapse_tours(ordered)
    d["recommend"] = d["ranked"][:top]
    d["n_scored"] = len(d["ranked"])
    d["weights"] = weights
    d["w_dropped"] = 0
    return d


def collapse_tours(rows: list[dict]) -> list[dict]:
    """One slot per production, preserving all distinct tour venues.

    Reusable after personal impression scoring promotes previously unscored rows.
    Title alone is insufficient: producer and complete credits must also match.
    """
    groups = {}
    for c in rows:
        key = (RC.nz(c.get("title") or ""), RC.nz(c.get("group") or ""),
               tuple(M.parse_credits(c.get("fields") or {})))
        if key not in groups:
            groups[key] = copy.deepcopy(c)
            groups[key]["tours"] = list(groups[key].get("tours") or [])
        else:
            representative = groups[key]
            known = {str(representative.get("stage_id") or "")}
            known.update(str(t.get("stage_id") or "") for t in representative["tours"])
            for venue in [c, *(c.get("tours") or [])]:
                sid = str(venue.get("stage_id") or "")
                if sid and sid not in known:
                    representative["tours"].append({k: venue.get(k) or "" for k in
                        ("stage_id", "theater", "pref", "period", "days", "price", "url", "onsale")})
                    known.add(sid)
    return list(groups.values())
