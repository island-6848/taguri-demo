"""Local, request-time person recommendations from one user's saved ratings.

This connects the feedback loop; it does not claim improved accuracy. No network,
LLM, shared recommendation writes, or persistent profile cache is used here.
"""
from __future__ import annotations

import collections
import copy
import datetime
import math
import re

import measure_nets as M
import recommend2 as RC

VERSION = "person-ordinal-v3"
# person-graded-v2 (2026-10-13): every grade counts, relative to how this user
# usually rates. ◎○△× become 4/3/2/1, then (grade − the user's mean) / the
# user's spread, so a strict user's ◎ weighs more than a lenient user's, and a
# lenient user's ○ counts as "below usual". A person's value is the shrunken
# mean of that over the productions they were in (n/(n+CONF_K)); a show's score
# is its strongest 3 positive parts plus its strongest 3 negative parts.
# Chosen over person-feedback-v1 (◎ only) on public data from 500 real users:
# better for 62–82% of them and rising about twice as fast with use
# (docs/research/person-reco-eval.md).
# person-ordinal-v3 (2026-10-13): two changes on top of v2, both checked on the
# same public data with users not used to choose them (docs/research/
# person-reco-eval.md, eval_design_choices.py):
# - a rating is read as an order, not an equal-step number: its mid-rank
#   among the user's own ratings on the same scale ("where it sits for this
#   person"), standardised. No better or worse than equal steps there, but it
#   does not assume ◎−○ = ○−△ = △−×, and treats a change of scale the same way.
# - the user's own preference for kinds of show (form, source, venue — the
#   theatre counterpart of a film genre) is added: +0.024–0.036 AUC, better for
#   63–76% of users.
GENRE_W = 1.0           # weight of the kind-of-show term (chosen range 1–2 on public data)
SQRT12 = math.sqrt(12)  # standardises a mid-rank position (uniform on −0.5..0.5)
# Favourites as pseudo ratings before real ones (q-favourites-seed,
# eval_favourite_seed.py): the favourite's productions count as rated in the
# user's top fifth, weighted SEED_K / (SEED_K + real ratings).
SEED_Z = 0.4 * SQRT12
SEED_K = 3
GRADE_VALUE = {"◎": 4, "○": 3, "△": 2, "×": 1}
# Users may choose their own scale (2–11 levels, 5 by default; dec-user-scale-range).
# Such a rating is stored as "value/levels", e.g. "4/5"; ◎○△× are a 4-level scale.
MIN_LEVELS, MAX_LEVELS = 2, 11
_SCALED = re.compile(r"(\d{1,2})/(\d{1,2})")


def grade_of(verdict) -> tuple[int, int] | None:
    """(value, levels) of a saved rating, or None if it is not a rating
    (empty, 「まだ判断できない」, malformed)."""
    if verdict in GRADE_VALUE:
        return GRADE_VALUE[verdict], 4
    m = _SCALED.fullmatch(str(verdict or ""))
    if m:
        value, levels = int(m.group(1)), int(m.group(2))
        if MIN_LEVELS <= levels <= MAX_LEVELS and 1 <= value <= levels:
            return value, levels
    return None
BUNDLES = ("favourites", "ranked", "others", "owned", "tracking", "started", "declined", "unscored")


def independent_ratings(rows: list[dict]) -> list[dict]:
    """Count a linked production once, using its latest dated saved rating.

    Repeated visits must not inflate confidence. Unlinked records retain their
    own keys; titles alone cannot establish that two productions are identical.
    """
    grouped = {}
    for row in sorted(rows, key=lambda r: (r.get("updated_at") or r.get("date") or "",
                                            r.get("key") or "")):
        if grade_of(row.get("verdict")) is None:
            continue
        key = ("stage", str(row["stage_id"])) if row.get("stage_id") else ("work", row["key"])
        grouped[key] = row
    return list(grouped.values())


# Kinds of show (dec: q-theme-preference). No official genre list exists for
# stage productions, so they are read from what every catalogue entry has:
# words in the title, the credits (原作・翻訳・music roles) and the venue.
# Tags are ("#axis", value) pairs and travel with the credits (rec_people, the
# index) so the Worker needs no extra table.
_FORM_WORDS = (("ミュージカル", "ミュージカル"), ("朗読", "朗読"), ("リーディング", "朗読"),
               ("人形劇", "人形劇"), ("バレエ", "ダンス"), ("ダンス", "ダンス"),
               ("歌舞伎", "古典"), ("狂言", "古典"), ("文楽", "古典"),
               ("落語", "お笑い"), ("コント", "お笑い"), ("漫才", "お笑い"))
_MUSIC_ROLES = {"作曲", "音楽", "編曲", "音楽監督", "歌唱指導"}
# Ticket price band (#値段), from the highest yen amount in the price text, so
# that "not worth the price" can land on price rather than on the people.
_YEN = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{3,6})\s*円")
PRICE_BANDS = ((5000, "5千円未満"), (9000, "5千〜9千円"), (13000, "9千〜1万3千円"), (None, "1万3千円以上"))


def price_band(texts) -> str:
    """Band of the highest price found in `texts` ('' when none)."""
    yen = [int(x.replace(",", "")) for t in texts or () for x in _YEN.findall(str(t or ""))]
    yen = [y for y in yen if y >= 500]
    if not yen:
        return ""
    top = max(yen)
    return next(name for limit, name in PRICE_BANDS if limit is None or top < limit)


def price_texts(entry: dict) -> list[str]:
    """Price text of a catalogue entry: its price field and 料金… credit fields."""
    fields = entry.get("fields") or {}
    return [entry.get("price") or ""] + [v for k, v in sorted(fields.items())
                                          if k.startswith("料金") and isinstance(v, str)]


def stage_tags(title: str, venues, credits, prices=()) -> list[tuple[str, str]]:
    """Kind-of-show tags of one production. `credits`: (role, person) pairs;
    `prices`: price texts (price_texts)."""
    roles = {role for role, _ in credits if not role.startswith("#")}
    tags = set()
    t = M.norm(title or "")
    form = next((name for word, name in _FORM_WORDS if word in t), "")
    if not form and roles & _MUSIC_ROLES:
        form = "音楽劇"
    if form:
        tags.add(("#形式", form))
    if roles:
        tags.add(("#原作", "原作もの" if roles & {"原作", "原案"} else "オリジナル"))
        if "翻訳" in roles:
            tags.add(("#翻訳", "翻訳劇"))
    for v in venues or ():
        v = M.norm(v)
        if v:
            tags.add(("#会場", v))
    band = price_band(prices)
    if band:
        tags.add(("#値段", band))
    return sorted(tags)


# 詳細 (q-rating-aspects, stage-roles): each aspect of a production can be
# marked as good ("+code") or a trouble ("code"). Which roles an aspect points
# at: share 1 = mainly, 0.5 = a little, 0.2 = only slightly (acting → director,
# as the owner asked); roles and tag axes not listed get 0.
# A rating above the user's middle (z > 0) lands mainly on what was good, one
# below it (z < 0) mainly on what was a trouble; the roles the other side
# points at get that much less. Signs never flip. With nothing marked the
# rating lands on everyone as before.
ASPECTS = {
    "story": ("話・脚本・構成", {"脚本": 1.0, "作": 1.0, "原作": 1.0, "原案": 1.0, "翻訳": 1.0, "潤色": 1.0,
                              "構成": 1.0, "演出": 0.5, "演出・振付": 0.5,
                              "#形式": 0.5, "#原作": 0.5, "#翻訳": 0.5}),
    "direction": ("演出・見せ方", {"演出": 1.0, "演出・振付": 1.0, "美術": 0.5, "照明": 0.5, "音響": 0.5,
                               "映像": 0.5, "#形式": 0.5}),
    "acting": ("演技・出演", {"出演": 1.0, "演出": 0.2, "演出・振付": 0.2}),
    "music": ("歌・音楽", {"作曲": 1.0, "音楽": 1.0, "編曲": 1.0, "音楽監督": 1.0, "歌唱指導": 1.0,
                        "出演": 0.5, "#形式": 0.5}),
    "dance": ("ダンス", {"振付": 1.0, "演出・振付": 1.0, "出演": 0.5}),
    "design": ("美術・衣裳", {"美術": 1.0, "衣裳": 1.0, "衣装": 1.0, "ヘアメイク": 1.0, "メイク": 1.0,
                         "小道具": 1.0, "演出": 0.5}),
    "price": ("値段", {"#値段": 1.0}),
    "venue": ("会場・座席", {"#会場": 1.0}),
}


def parse_aspects(value) -> tuple[list[str], list[str]]:
    """(troubles, goods): known codes of a record's aspects (list or comma-separated
    text; "+code" = good), each in ASPECTS order."""
    given = set(value.split(",") if isinstance(value, str) else value or ())
    return ([c for c in ASPECTS if c in given], [c for c in ASPECTS if "+" + c in given])


def aspect_codes(value) -> list[str]:
    """The troubles of a record (parse_aspects)."""
    return parse_aspects(value)[0]


def aspect_share(troubles, goods, role: str, positive: bool) -> float:
    """How much of a rating lands on `role` (or tag axis): mainly the side the
    rating leans to (goods when positive), less what the other side points at."""
    main, other = (goods, troubles) if positive else (troubles, goods)
    s = max((ASPECTS[c][1].get(role, 0.0) for c in main), default=1.0)
    o = max((ASPECTS[c][1].get(role, 0.0) for c in other), default=0.0)
    return s * (1.0 - o)


def rated_keys(r: dict) -> list[tuple]:
    """People and kind-of-show tags of one rated record."""
    people = {tuple(p) for p in r.get("people") or []}
    credits = [p for p in people if not p[0].startswith("#")]
    return sorted(people | set(stage_tags(r.get("title") or "", r.get("venues") or [], credits,
                                          r.get("prices") or ())))


def person_values(rated: list[dict], seeds: list[dict] = (), skip: set = frozenset()) -> tuple[dict, dict]:
    """(role, person) -> (n, value) and the user's scale {mean, spread}.

    value = Σ z / (n + CONF_K), z = (grade − mean) / spread: the mean of z,
    shrunk towards 0 while few productions back it.

    z is the rating's place among the user's own ratings on the same scale:
    ((how many are lower) + ½ (how many are equal)) / n − ½, times √12. Ratings
    on different scales (a user who changed their scale) are each placed among
    their own scale, so old ratings keep counting without a conversion table
    (eval_rating_scales.py: as good as or better than stretching scales to 0–1).

    `seeds`: productions of the user's favourites (each with "people"), added
    as pseudo ratings z = SEED_Z with weight w = SEED_K / (SEED_K + ratings),
    skipping the favourites themselves (`skip`, person names). They add to the
    weight in the denominator but not to n (n counts the user's own ratings).
    """
    # Integer counts and plain float operations in this order, so the
    # Worker's port (cloudflare/src/recommend.js) gets bit-identical values.
    by_scale: dict = {}
    for r in rated:
        value, levels = grade_of(r["verdict"])
        by_scale.setdefault(levels, []).append(value)
    tally = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for r in rated:
        value, levels = grade_of(r["verdict"])
        vals = by_scale[levels]
        below = sum(1 for v in vals if v < value)
        same = sum(1 for v in vals if v == value)
        z = ((below + 0.5 * same) / len(vals) - 0.5) * SQRT12
        troubles, goods = parse_aspects(r.get("aspects")) if z else ([], [])
        for key in rated_keys(r):
            tally[key][0] += 1
            tally[key][1] += z * aspect_share(troubles, goods, key[0], z > 0) if troubles or goods else z
            tally[key][2] += 1.0
    w = SEED_K / (SEED_K + len(rated))
    for r in seeds:
        for key in rated_keys(r):
            if key[1] in skip:
                continue
            tally[key][1] += w * SEED_Z
            tally[key][2] += w
    values = {k: (n, s / (wt + M.CONF_K)) for k, (n, s, wt) in tally.items()}
    return values, {str(k): len(v) for k, v in sorted(by_scale.items())}


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
    values, scale = person_values(rated)
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
        parts, negative, kinds = [], [], []
        credits = sorted(set(M.parse_credits(fields)))
        for role, person in credits:
            if (role, person) not in values:
                continue
            n, value = values[(role, person)]
            multiplier = multipliers.get(role_group(role), 1.0)
            contrib = round(value * (RC.ROLE_W.get(role, RC.BACKSTAGE_W) * multiplier), 6)
            if contrib > 0:
                parts.append([contrib, role, person, n])
            elif contrib < 0:
                negative.append([contrib, role, person, n])
        for axis, tag in stage_tags(c.get("title") or "", [fields.get("劇場", "")], credits,
                                    price_texts(c)):
            if (axis, tag) in values:
                n, value = values[(axis, tag)]
                contrib = round(value * (GENRE_W * multipliers.get("theme", 1.0)), 6)
                if contrib:
                    kinds.append([contrib, axis, tag, n])
        parts.sort(key=lambda p: (-p[0], p[1], p[2]))
        negative.sort(key=lambda p: (p[0], p[1], p[2]))
        b = b_score(parts, negative, kinds)
        start = RC.period_start(period)
        # Reasons shown to the user are the positive parts; the negative ones
        # only lower the score. `strong` (the first sort key everywhere) is the
        # score itself in v2: tiers by the number of strong matches were part of
        # v1 and were not what the comparison validated.
        c.update(stage_id=sid, b=b, c=0.0, total=b, why_b=parts[:6], why_b_neg=negative[:M.TOP_N],
                 why_kind=kinds,
                 person_parts=parts, why_c=[], why_v="", vr=0.0,
                 n_match=len(parts), strong=b,
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
                        "scale": scale, "n_people": len(values)})
    return out


def plain_sum(values) -> float:
    """Left-to-right float addition. Python 3.12+ `sum()` compensates rounding
    errors for floats, which the Worker's port (plain `+=`) cannot reproduce."""
    total = 0.0
    for v in values:
        total += v
    return total


def b_score(parts, negative, kinds) -> float:
    """A show's score: strongest 3 people up, strongest 3 down, plus the mean
    of its kind-of-show tags (kinds in (axis, tag) order)."""
    kind = plain_sum(k[0] for k in kinds) / len(kinds) if kinds else 0.0
    return round(plain_sum(p[0] for p in parts[:M.TOP_N])
                 + plain_sum(p[0] for p in negative[:M.TOP_N]) + kind, 6)


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
