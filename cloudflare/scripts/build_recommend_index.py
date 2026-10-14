"""Build the D1 person-score index from the catalogue (step 1 of moving
recommendations off Render).

    python3 cloudflare/scripts/build_recommend_index.py --output /tmp/rec.sql \
        --stats /tmp/rec-stats.json

The Python recommender (`tools/review/user_recommender.py`) re-reads every
catalogue file and re-parses every credit field on each request. Everything that
does not depend on the user is computed here once:

- rec_stage: candidate stages with run dates and parsed credits
- rec_credit: (role, person) -> stages, with role weight and role group
- rec_people: stage -> parsed credits, to build a user's roster from records
- rec_gram: two-character pieces of title keys, to find a stage by title when
  a user links a record to it (`search_index` is the reference)

The Worker then only reads postings for people the user rated ◎ at least once.
`score_from_index` is the reference for that request-time computation; the
test checks it against `user_recommender.prepare`.

Only public catalogue fields are written. Owner scores, reasons, notes and
reactions (why_b, a, _notes, ...) never enter the index.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))

import measure_nets as M                                           # noqa: E402
import recommend2 as RC                                            # noqa: E402
import user_recommender as UR                                      # noqa: E402

PUBLIC_KEYS = ("title", "group", "theater", "pref", "period", "price", "venue", "fields")
MAX_STATEMENT_BYTES = 90_000       # D1 rejects SQL statements over 100 KB


def _period_end(period: str) -> str:
    end = RC.period_end(period)
    return end.isoformat() if end else ""


def _public_entry(entry: dict) -> dict:
    out = {k: entry[k] for k in PUBLIC_KEYS if entry.get(k)}
    url = str(entry.get("url") or "")
    if url.startswith("https://"):
        out["url"] = url
    return out


THEME_AXIS = "#題材"
MAX_THEME_WORDS = 6


def theme_words(row: dict | None) -> list[str]:
    """Subject words of one stage (#題材 tags): the synopsis elements
    (themes.jsonl, net_c.load_themes) normalised like net_c.words, at least two
    characters, in the order the synopsis gave them, at most MAX_THEME_WORDS."""
    out = []
    for e in (row or {}).get("elements") or []:
        w = RC.nz(e.get("word") or "") if isinstance(e, dict) else ""
        if len(w) >= 2 and w not in out:
            out.append(w)
    return out[:MAX_THEME_WORDS]


def build_index(pool: dict[str, dict], fields_by_stage: dict[str, dict], role_group,
                titles: dict[str, str] | None = None, themes: dict[str, list[str]] | None = None) -> dict:
    """User-independent material. `pool` is `UR.candidate_pool(...)`.

    Kind-of-show tags (UR.stage_tags: form, source, venue) are stored with the
    credits, as ("#axis", value) pairs with role group "theme", so the Worker
    reads them through the same tables. `titles` gives titles of past stages
    (for the form tags); candidates carry their own. `themes`: stage id ->
    subject words (theme_words), stored as ("#題材", word) tags like the others.
    """
    titles = dict(titles or {})
    themes = themes or {}
    stages, postings = {}, []
    for sid, entry in pool.items():
        title = entry.get("title") or ""
        if any(word in title for word in RC.NOT_PLAY_TITLE):
            continue
        period = entry.get("period") or ""
        credits = sorted(set(M.parse_credits(entry.get("fields") or {})))
        titles.setdefault(sid, title)
        tags = UR.stage_tags(title, [(entry.get("fields") or {}).get("劇場", "")], credits,
                             UR.price_texts(entry)) + [(THEME_AXIS, w) for w in themes.get(sid, [])]
        stages[sid] = {"title": title, "tkey": M.R.title_key(title), "grp": entry.get("group") or "",
                       "tour": UR.tour_key(title, entry.get("group") or "", credits),
                       "gkey": RC.nz(entry.get("group") or ""),
                       "start": RC.period_start(period), "end": _period_end(period),
                       "credits": [list(c) for c in credits],
                       "entry": _public_entry(entry)}
        for role, person in credits:
            postings.append((role, person, sid, RC.ROLE_W.get(role, RC.BACKSTAGE_W),
                             role_group(role)))
        for axis, tag in tags:
            postings.append((axis, tag, sid, UR.GENRE_W, "theme"))
    people = {}
    for sid, f in fields_by_stage.items():
        if not f:
            continue
        credits = sorted(set(M.parse_credits(f)))
        tags = UR.stage_tags(titles.get(sid, ""), [f.get("劇場", "")], credits,
                             UR.price_texts(pool.get(sid) or {"fields": f}))
        tags += [(THEME_AXIS, w) for w in themes.get(sid, [])]
        people[sid] = [list(c) for c in sorted(set(credits) | set(tags))]
    for sid, ws in themes.items():
        if sid not in people and ws:
            people[sid] = [[THEME_AXIS, w] for w in sorted(set(ws))]
    people = {sid: p for sid, p in people.items() if p}
    return {"stages": stages, "postings": postings, "people": people}


# ---------------------------------------------------------------- request time (reference)

SEED_ROLES = ("出演", "演出", "脚本", "作", "原作", "翻訳", "潤色", "構成", "振付", "作曲", "音楽")
SEED_KINDS = ("人", "原作者")
MAX_SEED_FAVS = 20
MAX_SEED_STAGES = 60


SEED_GROUP_KINDS = ("団体", "主催")
SEED_WORK_KINDS = ("作品",)
SEED_THEME_KINDS = ("題材",)


def seeds_from_favourites(postings_for, people_of, favourites: list[dict],
                          stages_matching=None) -> tuple[list[dict], set]:
    """Seed productions for the user's favourites (q-favourites-seed).

    People and original authors: the candidate stages crediting them in one of
    SEED_ROLES. Troupes and producers: stages whose producing company contains
    the name; works: stages whose title contains it; subjects: stages with a
    #題材 word that contains the name or is contained in it (the matching rules
    of recommend2.declared_hits / net_c.declared_hits, on normalised text:
    RC.nz / title_key). `stages_matching(groups, works, subjects)` returns those
    stage ids. At most
    MAX_SEED_FAVS names of each kind; the first MAX_SEED_STAGES stage ids in
    order; people from rec_people. Returns (seeds, person names to skip).
    """
    names = sorted({f["name"] for f in favourites if f.get("kind") in SEED_KINDS})[:MAX_SEED_FAVS]
    keys = sorted((role, name) for name in names for role in SEED_ROLES)
    sids = {row[2] for row in postings_for(keys)}
    groups = sorted({g for f in favourites if f.get("kind") in SEED_GROUP_KINDS
                     for g in [RC.nz(f["name"])] if len(g) >= 2})[:MAX_SEED_FAVS]
    works = sorted({w for f in favourites if f.get("kind") in SEED_WORK_KINDS
                    for w in [M.R.title_key(f["name"])] if len(w) >= 2})[:MAX_SEED_FAVS]
    subjects = sorted({t for f in favourites if f.get("kind") in SEED_THEME_KINDS
                       for t in [RC.nz(f["name"])] if len(t) >= 2})[:MAX_SEED_FAVS]
    if (groups or works or subjects) and stages_matching:
        sids |= set(stages_matching(groups, works, subjects))
    seeds = []
    for sid in sorted(sids)[:MAX_SEED_STAGES]:
        people = people_of(sid)
        if people:
            seeds.append({"stage_id": sid, "people": people})
    return seeds, set(names)


def score_from_index(postings_for, stage_of, rated: list[dict], *, multipliers: dict,
                     today: datetime.date, seeds: list[dict] = (), skip: set = frozenset()) -> list[dict]:
    """What the Worker computes per request, using only the index.

    `rated`: the user's records with `verdict`, `stage_id`/`key`, `people`
    (from rec_people), `updated_at`, `date`. `postings_for(keys)` returns
    rec_credit rows for (role, person) keys; `stage_of(sid)` returns rec_stage.
    Returns ranked stages with b > 0, ordered as `UR.finish` orders them
    before tour grouping. `seeds`/`skip` from `seeds_from_favourites`: the
    seed stages themselves are left out (they are the favourites' own shows,
    listed apart).
    """
    rated = UR.independent_ratings(rated)
    values, _scale = UR.person_values(rated, seeds, skip)
    seeded = {r["stage_id"] for r in seeds}
    # person-graded-v2: everyone the user has a non-zero value for can raise or
    # lower a show, so their postings are read.
    keys = sorted(k for k, (n, v) in values.items() if v)
    by_stage: dict[str, list] = {}
    for role, person, sid, role_w, group in postings_for(keys):
        n, value = values[(role, person)]
        contrib = round(value * (role_w * multipliers.get(group, 1.0)), 6)
        if contrib:
            by_stage.setdefault(sid, []).append([contrib, role, person, n, group])
    # person-ordinal-v3: kind-of-show tags ("#axis") add their mean; people
    # add the strongest 3 up and 3 down (UR.b_score).
    out, iso = [], today.isoformat()
    for sid, all_parts in by_stage.items():
        st = stage_of(sid)
        if sid in seeded or st is None or (st["end"] and st["end"] < iso):
            continue
        if st["start"] and st["start"] <= iso:
            continue                     # already running: "started", not "ranked"
        people = [p for p in all_parts if not p[1].startswith("#")]
        kinds = sorted((p for p in all_parts if p[1].startswith("#")), key=lambda p: (p[1], p[2]))
        parts = sorted((p for p in people if p[0] > 0), key=lambda p: (-p[0], p[1], p[2]))
        negative = sorted((p for p in people if p[0] < 0), key=lambda p: (p[0], p[1], p[2]))
        b = UR.b_score(parts, negative, kinds)
        if b <= 0:
            continue
        out.append({"stage_id": sid, "b": b, "strong": b, "tour": st.get("tour") or "",
                    "parts": [p[:4] for p in parts]})
    out.sort(key=lambda c: (-c["strong"], -c["b"], c["stage_id"]))
    return out


def collapse_ranked(ranked: list[dict], top: int) -> list[dict]:
    """The Worker's tour grouping of score_from_index's output (UR.collapse_tours
    on the index): the first `top` productions, each with the stage ids of its
    other tour venues in rank order."""
    groups: dict = {}
    for c in ranked:
        key = c.get("tour") or "stage:" + c["stage_id"]
        if key in groups:
            groups[key]["tours"].append(c["stage_id"])
        else:
            groups[key] = {"stage_id": c["stage_id"], "tours": []}
    return list(groups.values())[:top]


def memory_access(index: dict):
    """Accessors over the in-memory index (same contract as the D1 queries)."""
    by_key: dict = {}
    for row in index["postings"]:
        by_key.setdefault((row[0], row[1]), []).append(row)
    return (lambda keys: [r for k in keys for r in by_key.get(k, [])],
            lambda sid: index["stages"].get(sid))


def memory_matching(index: dict):
    """stages_matching(groups, works, subjects) over the in-memory index."""
    def match(groups, works, subjects=()):
        sids = {sid for sid, st in index["stages"].items()
                if any(g in st["gkey"] for g in groups) or any(w in st["tkey"] for w in works)}
        sids |= {sid for role, word, sid, *_ in index["postings"] if role == THEME_AXIS
                 and any(t in word or (len(word) >= 2 and word in t) for t in subjects)}
        return sorted(sids)
    return match


def memory_people(index: dict):
    """people_of(sid) over the in-memory index (rec_people)."""
    return lambda sid: index["people"].get(sid)


# ---------------------------------------------------------------- title search (reference)

SEARCH_LIMIT = 20
GRAM_PART = 400                    # entries per rec_gram row


def bigrams(key: str) -> list[str]:
    return sorted({key[i:i + 2] for i in range(len(key) - 1)})


def gram_lists(index: dict) -> dict[str, list]:
    """piece -> [[stage_id, tkey, start, end], ...] ordered by stage_id."""
    out: dict[str, list] = {}
    for sid, st in sorted(index["stages"].items()):
        for g in bigrams(st["tkey"]):
            out.setdefault(g, []).append([sid, st["tkey"], st["start"], st["end"]])
    return out


def search_index(entries_for, q: str, date: str = "", limit: int = SEARCH_LIMIT) -> list[str]:
    """Stage ids whose title key contains the query's key, best first.

    Stages running on the record's date come first, then an exact title, then
    a title starting with the query, then shorter titles. Fewer than two
    characters find nothing (like `app.suggest`). `entries_for(grams)` returns
    {gram: entries} for the grams present in the index.
    """
    k = M.R.title_key(q or "")
    if len(k) < 2:
        return []
    grams = bigrams(k)
    lists = entries_for(grams)
    if any(g not in lists for g in grams):
        return []
    hits = []
    for sid, tkey, start, end in min((lists[g] for g in grams), key=len):
        if k not in tkey:
            continue
        miss = 0 if date and start and start <= date and (not end or date <= end) else 1
        score = 0 if tkey == k else 1 if tkey.startswith(k) else 2
        hits.append((miss, score, len(tkey), sid))
    hits.sort()
    return [h[3] for h in hits[:limit]]


def memory_search(index: dict):
    lists = gram_lists(index)
    return lambda grams: {g: lists[g] for g in grams if g in lists}


KEYS_PER_QUERY = 49                # D1 binds at most 100 parameters: ver + 2 per key


def sql_access(con, ver: str, counter: dict | None = None):
    """Accessors over D1/SQLite: the queries the Worker issues.

    `counter["rows"]` accumulates rows read, to estimate the D1 daily quota.
    """
    counter = counter if counter is not None else {}
    counter.setdefault("rows", 0)

    def postings_for(keys):
        out = []
        for i in range(0, len(keys), KEYS_PER_QUERY):
            chunk = keys[i:i + KEYS_PER_QUERY]
            pairs = ",".join("(?,?)" for _ in chunk)
            rows = con.execute(
                "SELECT role,person,stage_id,role_w,role_group FROM rec_credit"
                f" WHERE ver=? AND (role,person) IN (VALUES {pairs})",
                [ver] + [x for k in chunk for x in k]).fetchall()
            counter["rows"] += len(rows)
            out += [tuple(r) for r in rows]
        return out

    def stage_of(sid):
        row = con.execute("SELECT start,end,tour FROM rec_stage WHERE ver=? AND stage_id=?",
                          (ver, sid)).fetchone()
        counter["rows"] += row is not None
        return {"start": row[0], "end": row[1], "tour": row[2]} if row else None

    return postings_for, stage_of


def sql_search(con, ver: str):
    """`entries_for` over D1/SQLite (the Worker's query)."""
    def entries_for(grams):
        rows = con.execute(
            f"SELECT gram,entries FROM rec_gram WHERE ver=? AND gram IN ({','.join('?' for _ in grams)})"
            " ORDER BY gram,part", [ver, *grams]).fetchall()
        out: dict = {}
        for g, entries in rows:
            out.setdefault(g, []).extend(json.loads(entries))
        return out
    return entries_for


# ---------------------------------------------------------------- SQL

def version_of(index: dict) -> str:
    blob = json.dumps(index, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def _q(v) -> str:
    if isinstance(v, (int, float)):
        return repr(float(v))
    return "'" + str(v).replace("'", "''") + "'"


def _inserts(table: str, cols: str, rows: list[tuple]) -> list[str]:
    head = f"INSERT INTO {table}({cols}) VALUES"
    out, cur, size = [], [], len(head)
    for row in rows:
        val = "(" + ",".join(_q(v) for v in row) + ")"
        if cur and size + len(val) + 2 > MAX_STATEMENT_BYTES:
            out.append(head + ",".join(cur) + ";")
            cur, size = [], len(head)
        cur.append(val)
        size += len(val) + 1
    if cur:
        out.append(head + ",".join(cur) + ";")
    return out


ONBOARDING_SIZE = 40


def onboarding_list(index: dict, today: datetime.date, size: int = ONBOARDING_SIZE) -> list[str]:
    """Stages already on (or over) to ask a new user about first (q-first-rating-onboarding).

    Greedy cover of the coming catalogue: each pick adds the most weight of
    people and kind tags not yet covered, a key weighing as many coming stages
    as credit it. Rating these first gives the recommender values for the
    people it will have to rank (eval-onboarding-selection; Rashid et al.
    2002). Uses public catalogue fields only; ties go to the smaller stage id.
    """
    iso = today.isoformat()
    coming = {sid for sid, st in index["stages"].items() if st["start"] and st["start"] > iso}
    weight: dict = {}
    for role, person, sid, *_ in index["postings"]:
        if sid in coming:
            weight[(role, person)] = weight.get((role, person), 0) + 1
    keys_of: dict = {}
    for role, person, sid, *_ in index["postings"]:
        if sid not in coming and index["stages"][sid]["start"]:
            keys_of.setdefault(sid, set()).add((role, person))
    covered: set = set()
    out = []
    for _ in range(min(size, len(keys_of))):
        best, gain = None, 0
        for sid in sorted(keys_of):
            g = sum(weight.get(k, 0) for k in keys_of[sid] - covered)
            if g > gain:
                best, gain = sid, g
        if best is None:
            break
        out.append(best)
        covered |= keys_of.pop(best)
    return out


def to_sql(index: dict, ver: str, onboarding: list[str] | None = None) -> list[str]:
    """Insert `ver`, switch to it, then drop other versions (in that order)."""
    dumps = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True)
    stmts = [f"DELETE FROM {t} WHERE ver={_q(ver)};" for t in TABLES]
    stmts += _inserts("rec_stage", "ver,stage_id,title,tkey,grp,tour,gkey,start,end,credits,entry", [
        (ver, sid, s["title"], s["tkey"], s["grp"], s["tour"], s["gkey"], s["start"], s["end"], dumps(s["credits"]),
         dumps(s["entry"])) for sid, s in sorted(index["stages"].items())])
    stmts += _inserts("rec_credit", "ver,role,person,stage_id,role_w,role_group",
                      [(ver, *r) for r in sorted(set(index["postings"]))])
    stmts += _inserts("rec_people", "ver,stage_id,people",
                      [(ver, sid, dumps(p)) for sid, p in sorted(index["people"].items())])
    stmts += _inserts("rec_gram", "ver,gram,part,entries", gram_rows(index, ver))
    if onboarding is not None:
        stmts.append("INSERT INTO rec_meta(k,v) VALUES('onboarding',"
                     f"{_q(dumps({'ver': ver, 'ids': onboarding}))}) ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts.append(f"INSERT INTO rec_meta(k,v) VALUES('current',{_q(ver)}) "
                 "ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts += [f"DELETE FROM {t} WHERE ver<>{_q(ver)};" for t in TABLES]
    return stmts


TABLES = ("rec_stage", "rec_credit", "rec_people", "rec_gram")


def gram_rows(index: dict, ver: str) -> list[tuple]:
    dumps = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return [(ver, g, i // GRAM_PART, dumps(entries[i:i + GRAM_PART]))
            for g, entries in sorted(gram_lists(index).items())
            for i in range(0, len(entries), GRAM_PART)]


def stats(index: dict, sql_bytes: int) -> dict:
    """Numbers needed to judge the D1 free tier (rows read per request)."""
    per_person: dict = {}
    for role, person, *_ in index["postings"]:
        per_person[(role, person)] = per_person.get((role, person), 0) + 1
    sizes = sorted(per_person.values()) or [0]
    return {"stages": len(index["stages"]), "postings": len(index["postings"]),
            "people": len(per_person), "people_stages": len(index["people"]),
            "postings_per_person": {"median": statistics.median(sizes),
                                    "p90": sizes[int(len(sizes) * 0.9) - 1 if len(sizes) > 1 else 0],
                                    "max": sizes[-1]},
            "gram_rows": len(gram_rows(index, "")),
            # D1 free tier: 100,000 rows written per day. Uploading a version
            # writes every row once, and deleting the previous one writes again.
            "rows_written": len(index["stages"]) + len(set(index["postings"]))
            + len(index["people"]) + len(gram_rows(index, "")),
            "sql_bytes": sql_bytes}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--output", required=True, type=Path, help="SQL for wrangler d1 execute --file")
    p.add_argument("--stats", type=Path, help="write size statistics as JSON")
    p.add_argument("--today", type=datetime.date.fromisoformat,
                   default=(datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date(),
                   help="date (JST) splitting stages to ask about from the coming ones")
    a = p.parse_args()
    import app as APP
    import digest as DG
    import render_recommend as RR
    try:
        raw, _ = RR.load()
    except FileNotFoundError:
        raw = {}
    pool = UR.candidate_pool(raw, DG.all_candidates())
    if not pool:
        p.error("no candidates under data/; fetch the catalogue first")
    # Titles of past stages for the form tags (public page titles only).
    titles = {}
    linked = ROOT / "data" / "credits" / "linked.jsonl"
    if linked.exists():
        for line in linked.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                if r.get("matched") and r.get("stage_id") and r.get("page_title"):
                    titles.setdefault(str(r["stage_id"]), r["page_title"])
    # Subject words of candidate stages (synopsis elements, hand-entered ones overlaid).
    import net_c as C
    themes = {sid: ws for (side, sid), row in C.load_themes().items()
              if side == "candidate" for ws in [theme_words(row)] if ws}
    index = build_index(pool, M._fields_by_stage(), APP.group_of, titles, themes)
    stmts = to_sql(index, version_of(index), onboarding_list(index, a.today))
    body = "\n".join(stmts) + "\n"
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        out.write(body)
    st = stats(index, len(body.encode("utf-8")))
    if a.stats:
        a.stats.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(st, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
