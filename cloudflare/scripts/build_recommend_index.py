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
- rec_affil: (affiliation, person, stage) from the 「名前（所属）」 of the cast field
  (measure_nets.affiliations): the troupe / agency / group as the parent of its
  people (dec-affiliation-table). Not read by the Worker yet
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
import re
import statistics
import sys
import unicodedata
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
MAX_THEME_WORDS = 16   # 照合に使う 6 種類と原作の上限の合計
# 種類ごとの上限と推薦の重さ（起案者の判断 2026-10-18「6＋2 に組み替えて」。dec-theme-kinds-6p2）。
# ジャンル・題材・テーマ・味わいは好みの中心で 1.0（推定の多さは根拠の重さで別に下げるので、種類では下げない）。
# 語り口（会話劇・群像劇）は多くの公演に共通で公演を見分けにくいので 0.7、舞台設定は背景なので 0.5。
# モチーフはその作品にしか無い言葉でほかの公演と当たらないので索引に入れない（カードの言葉には残す）。
# 原作は「原作者」のお気に入りが #題材 の言葉で当てているので残す。
# 関係・感情・構造は初めの g5（8 種類）の、トーンは g4 までの種類で、読み直すまでの行のために残す。
# 種類の無い言葉（手で入れた題材）と知らない種類は、全体の上限まで重さ 1
THEME_KIND_W = {"ジャンル": (2, 1.0), "題材": (4, 1.0), "テーマ": (3, 1.0), "味わい": (3, 1.0), "原作": (2, 1.0),
                "語り口": (2, 0.7), "舞台設定": (2, 0.5), "モチーフ": (0, 0.0),
                "関係・感情": (3, 1.0), "構造": (2, 0.7), "トーン": (2, 0.7)}
# 根拠の強さ（g5 の basis）。g4 までの行は本文から取った言葉なので 1
# 知識（本文に名前の出た作品の定まった事実）0.5・定評（本文に名前の出た作家・劇団の作風）0.3（dec-theme-knowledge）
THEME_BASIS_W = {"本文": 1.0, "推定": 0.7, "作風": 0.5, "知識": 0.5, "定評": 0.3}


def theme_terms(row: dict | None) -> list[tuple[str, float]]:
    """Subject words of one stage (#題材 tags) with their weight: the synopsis elements
    (themes.jsonl, net_c.load_themes) normalised like net_c.words, at least two characters,
    in the order the synopsis gave them, up to each kind's cap (THEME_KIND_W) and
    MAX_THEME_WORDS in all. The weight is the kind's times the basis's; a word given
    twice keeps the larger."""
    out: dict[str, float] = {}
    per: dict[str, int] = {}
    for e in (row or {}).get("elements") or []:
        if not isinstance(e, dict):
            continue
        w = RC.nz(e.get("word") or "")
        kind = e.get("kind") or ""
        cap, kw = THEME_KIND_W.get(kind, (MAX_THEME_WORDS, 1.0))
        if len(w) < 2 or per.get(kind, 0) >= cap:
            continue
        per[kind] = per.get(kind, 0) + 1
        x = round(kw * THEME_BASIS_W.get(e.get("basis") or "本文", 1.0), 6)
        if w not in out and len(out) >= MAX_THEME_WORDS:
            continue
        out[w] = max(out.get(w, 0.0), x)
    return list(out.items())


def theme_words(row: dict | None) -> list[str]:
    """The words of theme_terms (past stages and the people lists carry no weight)."""
    return [w for w, _ in theme_terms(row)]


def build_index(pool: dict[str, dict], fields_by_stage: dict[str, dict], role_group,
                titles: dict[str, str] | None = None, themes: dict[str, list[str]] | None = None,
                past: list[dict] | None = None) -> dict:
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
        tags = UR.stage_tags(title, [(entry.get("fields") or {}).get("劇場", ""), entry.get("venue") or "", entry.get("theater") or ""], credits,
                             source=UR.source_text(entry.get("fields") or {}), group=entry.get("group") or "")
        # 題材の言葉は種類と根拠で重さが違う（theme_terms）。言葉だけの古い形（重さ 1）も受ける
        terms = [(t, 1.0) if isinstance(t, str) else (t[0], t[1]) for t in themes.get(sid, [])]
        own = {tag for axis, tag in tags if axis == THEME_AXIS}
        tags += [(THEME_AXIS, w) for w, _ in terms if w not in own]
        tw = dict(terms)
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
            x = tw.get(tag, 1.0) if axis == THEME_AXIS else 1.0
            postings.append((axis, tag, sid, round(UR.GENRE_W * x, 6), "theme"))
    people = {}
    for sid, f in fields_by_stage.items():
        if not f:
            continue
        credits = sorted(set(M.parse_credits(f)))
        row = pool.get(sid) or {}
        tags = UR.stage_tags(titles.get(sid, ""), [f.get("劇場", ""), row.get("venue") or "", row.get("theater") or ""], credits,
                             source=UR.source_text(f), group=(pool.get(sid) or {}).get("group") or "")
        tags += [(THEME_AXIS, t if isinstance(t, str) else t[0]) for t in themes.get(sid, [])]
        people[sid] = [list(c) for c in sorted(set(credits) | set(tags))]
    for sid, ws in themes.items():
        if sid not in people and ws:
            people[sid] = [[THEME_AXIS, w] for w in sorted({t if isinstance(t, str) else t[0] for t in ws})]
    people = {sid: p for sid, p in people.items() if p}
    src = [(sid, e.get("fields") or {}, RC.period_start(e.get("period") or "") or "", e.get("group") or "") for sid, e in pool.items()]
    src += [(sid, f, "", (pool.get(sid) or {}).get("group") or "") for sid, f in fields_by_stage.items() if f and sid not in pool]
    src += [(str(r.get("stage_id") or ""), r.get("fields") or {}, r.get("start") or "", r.get("group") or "") for r in past or []]
    return {"stages": stages, "postings": postings, "people": people, "affil": affiliation_rows(src)}


# 所属の種類（目安）。主催の団体名と同じなら「劇団」。名前の言葉で劇団・事務所・グループに分け、分からなければ空
AFFIL_KINDS = (
    ("劇団", re.compile(r"劇団|劇場|演劇|一座|座$|カンパニー|company|theat(?:re|er)|シアター|ユニット|unit|プロデュース|produce|"
                       r"企画|団$|クラブ|倶楽部|俱楽部|バレエ|ballet|オペラ|歌劇", re.I)),
    ("事務所", re.compile(r"プロダクション|プロモーション|エンタテ|エンターテ|事務所|オフィス|office|株式会社|有限会社|マネジメント|"
                         r"management|アーツ|artists?$|芸能|興業|プロ$|pro$|agency|エージェン", re.I)),
    ("グループ", re.compile(r"\d{2}$|jr\.?$|group$|グループ", re.I)),
)
# 所属に見えて実は人の名前（「役名（演じる人）」「芸名（本名）」）。出演欄に人として出てくる名前は、
# 所属の言葉（AFFIL_KINDS）を含まない限り所属にしない（実データで「堂前透」「岡部道子」など）
def affiliation_rows(src: list[tuple[str, dict, str, str]]) -> list[tuple]:
    """(stage_id, fields, start, group) の並びから rec_affil の行 (affil, person, stage_id, start, kind)。

    所属は時期で変わる（移籍・退団）ので、人と所属の 1 本の線ではなく「この公演ではこう書かれていた」を
    公演ごとに残す。今の所属は、読む側が start の新しい行で決める。
    """
    groups = {RC.nz(g) for _sid, _f, _st, g in src if g}
    cast = {}
    for sid, f, start, _g in src:
        if sid and f.get("出演"):
            cast[sid] = (start, M.affiliations(f["出演"]))
    persons = {n for sid, f, _st, _g in src if f.get("出演") for n in M._names(f["出演"])}
    rows = set()
    for sid, (start, pairs) in cast.items():
        for person, affil in pairs:
            kind = "劇団" if RC.nz(affil) in groups else next((k for k, rx in AFFIL_KINDS if rx.search(affil)), "")
            if affil in persons and not kind:
                continue
            rows.add((affil, person, sid, start, kind))
    return sorted(rows)


# ---------------------------------------------------------------- request time (reference)

SEED_ROLES = ("出演", "演出", "脚本", "作", "原作", "翻訳", "潤色", "構成", "振付", "作曲", "音楽")
SEED_KINDS = ("人", "原作者")
MAX_SEED_FAVS = 20
MAX_SEED_STAGES = 60


SEED_GROUP_KINDS = ("団体", "主催")
SEED_WORK_KINDS = ("作品",)
SEED_THEME_KINDS = ("題材",)


def person_key(name: str) -> str:
    """登録した人の名前を索引の書き方に寄せる（NFKC、空白を詰める: measure_nets._names）。"""
    return re.sub(r"[\s\u3000]", "", unicodedata.normalize("NFKC", str(name or "")))


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
    # 「堂本 光一」と空白を入れて登録しても、索引の「堂本光一」で引く（索引の名前は NFKC で空白を詰めてある。
    # Worker の recommend.personKey と同じ、2026-10-18 fix-fav-only-no-reco）
    lookup = {n for name in names for n in (name, person_key(name)) if n}
    keys = sorted((role, name) for name in lookup for role in SEED_ROLES)
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
    return seeds, lookup


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
        # 点を上げた人物か公演の種類が無い公演は出さない（user_recommender.finish と同じ）
        if b <= 0 or not UR.has_reason(parts, kinds):
            continue
        # 理由に出す種類: 点を上げたものだけ、公演そのものの種類を先に（render_recommend の並び）
        shown = sorted((k for k in kinds if k[0] > 0), key=lambda k: (k[1] not in UR.CONTENT_AXES, -k[0], k[1], k[2]))
        out.append({"stage_id": sid, "b": b, "strong": b, "tour": st.get("tour") or "",
                    "parts": [p[:4] for p in parts], "kinds": [k[:4] for k in shown]})
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


def _inserts(table: str, cols: str, rows: list[tuple], tail: str = "") -> list[str]:
    # **大きさはバイトで数える。** 文字数で数えていたので、日本語（UTF-8 で 1 字 3 バイト）の多い
    # 行では 1 文が上限の約 3 倍になり、D1 が SQLITE_TOOBIG で断った（2026-10-14 の past_stage）
    head = f"INSERT INTO {table}({cols}) VALUES"
    nbytes = lambda t: len(t.encode("utf-8"))                      # noqa: E731
    out, cur, size = [], [], nbytes(head)
    for row in rows:
        val = "(" + ",".join(_q(v) for v in row) + ")"
        n = nbytes(val)
        if cur and size + n + 2 > MAX_STATEMENT_BYTES:
            out.append(head + ",".join(cur) + tail + ";")
            cur, size = [], nbytes(head)
        cur.append(val)
        size += n + 1
    if cur:
        out.append(head + ",".join(cur) + tail + ";")
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
    stmts += _inserts("rec_affil", "ver,affil,person,stage_id,start,kind",
                      [(ver, *r) for r in index.get("affil", [])])
    stmts += _inserts("rec_gram", "ver,gram,part,entries", gram_rows(index, ver))
    if onboarding is not None:
        stmts.append("INSERT INTO rec_meta(k,v) VALUES('onboarding',"
                     f"{_q(dumps({'ver': ver, 'ids': onboarding}))}) ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts.append(f"INSERT INTO rec_meta(k,v) VALUES('current',{_q(ver)}) "
                 "ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts += [f"DELETE FROM {t} WHERE ver<>{_q(ver)};" for t in TABLES]
    return stmts


TABLES = ("rec_stage", "rec_credit", "rec_people", "rec_affil", "rec_gram")

# ---------------------------------------------------------------- 差分で入れる（q-index-incremental）
# 起案者の指示（2026-10-15）。版ごとに全部入れて前の版を消すと、1 日の書き込みが行数の約 4 倍になり、
# 索引が 2 万行を越えると D1 の無料枠（1 日 10 万行）に収まらない（d1-writes-undercounted）。
# 行はいつも同じ版 LIVE に置き、前回入れた行のハッシュ（--prev-hashes）と比べて、変わった行だけを
# upsert し、無くなった行だけを消す。Worker は rec_meta 'current'（= LIVE）で読むので変えない。
# 推薦の控えを捨てる合図は rec_meta 'index_rev'（中身のハッシュ）に移す。
LIVE = "live"
TABLE_COLS = {
    "rec_stage": (("stage_id",), ("title", "tkey", "grp", "tour", "gkey", "start", "end", "credits", "entry")),
    "rec_credit": (("role", "person", "stage_id"), ("role_w", "role_group")),
    "rec_people": (("stage_id",), ("people",)),
    "rec_affil": (("affil", "person", "stage_id"), ("start", "kind")),
    "rec_gram": (("gram", "part"), ("entries",)),
}


def live_rows(index: dict) -> dict[str, list[tuple]]:
    """table -> rows without the ver column, in the column order of TABLE_COLS (keys first)."""
    dumps = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True)             # noqa: E731
    return {
        "rec_stage": [(sid, s["title"], s["tkey"], s["grp"], s["tour"], s["gkey"], s["start"], s["end"],
                       dumps(s["credits"]), dumps(s["entry"])) for sid, s in sorted(index["stages"].items())],
        "rec_credit": [tuple(r) for r in sorted(set(index["postings"]))],
        "rec_people": [(sid, dumps(p)) for sid, p in sorted(index["people"].items())],
        "rec_affil": [tuple(r) for r in index.get("affil", [])],
        "rec_gram": [tuple(r[1:]) for r in gram_rows(index, LIVE)],
    }


def _row_hash(row: tuple) -> str:
    return hashlib.sha1(json.dumps(row, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def _delete_sql(table: str, gone: list[str]) -> list[str]:
    """消す行は鍵の値で選ぶ（row value IN）。鍵は "\x1f" でつないで控えている。"""
    keys = TABLE_COLS[table][0]
    nk = len(keys)
    vals = [tuple(k.split("\x1f")) for k in gone]
    if table == "rec_gram":                       # part is an INTEGER column
        vals = [(g, int(n)) for g, n in vals]
    kcols = "(" + ",".join(keys) + ")" if nk > 1 else keys[0]
    head = f"DELETE FROM {table} WHERE ver={_q(LIVE)} AND {kcols} IN ("
    out, cur = [], []
    size = len(head.encode("utf-8"))
    for v in vals:
        lit = ("(" + ",".join(_q(x) for x in v) + ")") if nk > 1 else _q(v[0])
        if cur and size + len(lit.encode("utf-8")) + 3 > MAX_STATEMENT_BYTES:
            out.append(head + ",".join(cur) + ");")
            cur, size = [], len(head.encode("utf-8"))
        cur.append(lit)
        size += len(lit.encode("utf-8")) + 1
    if cur:
        out.append(head + ",".join(cur) + ");")
    return out


def _stage_of(table: str, key: str) -> str:
    """The stage a row belongs to (rec_gram rows belong to none)."""
    parts = key.split("\x1f")
    return {"rec_stage": parts[0], "rec_people": parts[0], "rec_credit": parts[-1], "rec_affil": parts[-1]}.get(table, "")


def diff_sql(index: dict, prev: dict, onboarding: list[str] | None = None,
             limit: int | None = None) -> tuple[list[str], dict, dict]:
    """(statements, hashes to keep for next time, counts). prev: table -> {key: hash} from last delivery.

    limit: at most this many rows changed or deleted in one delivery (the day's D1 write budget). When the
    diff is larger (the first delivery is the whole index, about 5 万行), whole stages go first, soonest
    first, then title pieces; what is left keeps its old hash and is sent the next day (q-index-first-load).
    """
    dumps = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True)             # noqa: E731
    stmts: list[str] = [f"DELETE FROM {t} WHERE ver<>{_q(LIVE)};" for t in TABLES]   # rows of the old versioned scheme
    hashes: dict = {t: dict(prev.get(t) or {}) for t in TABLES}
    counts = {"upserted": 0, "deleted": 0, "stages_upserted": 0, "left": 0}
    # Every change: (table, key, hash or None for a deletion, row)
    changes: list[tuple] = []
    for table, rows in live_rows(index).items():
        nk = len(TABLE_COLS[table][0])
        old = prev.get(table) or {}
        now = {"\x1f".join(str(v) for v in r[:nk]): (_row_hash(r), r) for r in rows}
        changes += [(table, k, h, r) for k, (h, r) in sorted(now.items()) if old.get(k) != h]
        changes += [(table, k, None, None) for k in sorted(old) if k not in now]
    if limit is not None and len(changes) > limit:
        starts = {sid: s.get("start") or "9999" for sid, s in index["stages"].items()}
        by_stage: dict[str, list] = {}
        for c in changes:
            by_stage.setdefault(_stage_of(c[0], c[1]), []).append(c)
        deletions = [c for c in changes if c[2] is None]
        chosen = deletions[:limit]
        room = limit - len(chosen)
        # 所属（rec_affil）の行しか変わらない公演（過去の公演）は推薦の材料が変わらないので、題名のかけら（""）より後に回す
        affil_only = {sid for sid, cs in by_stage.items() if sid and all(c[0] == "rec_affil" for c in cs)}
        order = sorted((sid for sid in by_stage if sid and sid not in affil_only),
                       key=lambda sid: (starts.get(sid, "9999"), sid))
        rest = sorted(affil_only)
        for sid in order + [""] + rest:           # "" = title pieces, after every stage
            group = [c for c in by_stage[sid] if c[2] is not None] if sid in by_stage else []
            if group and len(group) <= room:
                chosen += group
                room -= len(group)
        counts["left"] = len(changes) - len(chosen)
        changes = chosen
    for table in TABLES:
        keys, cols = TABLE_COLS[table]
        gone = [k for t, k, h, _r in changes if t == table and h is None]
        upsert = [(k, h, r) for t, k, h, r in changes if t == table and h is not None]
        if gone:
            stmts += _delete_sql(table, gone)
            for k in gone:
                hashes[table].pop(k, None)
        if upsert:
            tail = (f" ON CONFLICT(ver,{','.join(keys)}) DO UPDATE SET "
                    + ",".join(f"{c}=excluded.{c}" for c in cols))
            stmts += _inserts(table, "ver," + ",".join(keys + cols), [(LIVE, *r) for _k, _h, r in upsert], tail)
            for k, h, _r in upsert:
                hashes[table][k] = h
        counts["upserted"] += len(upsert)
        counts["deleted"] += len(gone)
        if table == "rec_stage":
            counts["stages_upserted"] = len(upsert) + len(gone)
    rev = version_of(index)
    # 途中まで入れた日は、控えを捨てる合図を「版-残り件数」にする（全部入ってから版そのものにする）
    shown = rev if not counts["left"] else f"{rev}-left{counts['left']}"
    if onboarding is not None:
        stmts.append("INSERT INTO rec_meta(k,v) VALUES('onboarding',"
                     f"{_q(dumps({'ver': LIVE, 'ids': onboarding}))}) ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts.append(f"INSERT INTO rec_meta(k,v) VALUES('index_rev',{_q(shown)}) ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts.append(f"INSERT INTO rec_meta(k,v) VALUES('current',{_q(LIVE)}) ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    counts["rev"] = rev
    return stmts, hashes, counts


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
            + len(index["people"]) + len(index.get("affil", [])) + len(gram_rows(index, "")),
            "affil_rows": len(index.get("affil", [])),
            "sql_bytes": sql_bytes}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--output", required=True, type=Path, help="SQL for wrangler d1 execute --file")
    p.add_argument("--stats", type=Path, help="write size statistics as JSON")
    p.add_argument("--hashes-out", type=Path,
                   help="差分で入れる: 変わった行だけの SQL を出し、次回のための行のハッシュをここに書く")
    p.add_argument("--prev-hashes", type=Path, help="前回入れた行のハッシュ（無ければ全部を入れる）")
    p.add_argument("--max-rows", type=int, help="1 回に変える行の上限（D1 の書き込みの残りから。残りは次回）")
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
              if side == "candidate" for ws in [theme_terms(row)] if ws}
    # 過去の公演（fetch_past_stages の控え）は、所属の表（rec_affil）にだけ使う
    past_path = ROOT / "data" / "past" / "stages.jsonl"
    past = [json.loads(x) for x in past_path.read_text(encoding="utf-8").split("\n") if x.strip()] if past_path.exists() else []
    index = build_index(pool, M._fields_by_stage(), APP.group_of, titles, themes, past)
    counts = None
    if a.hashes_out:
        prev = json.loads(a.prev_hashes.read_text(encoding="utf-8")) if a.prev_hashes and a.prev_hashes.exists() else {}
        stmts, hashes, counts = diff_sql(index, prev, onboarding_list(index, a.today), a.max_rows)
        a.hashes_out.write_text(json.dumps(hashes, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    else:
        stmts = to_sql(index, version_of(index), onboarding_list(index, a.today))
    body = "\n".join(stmts) + "\n"
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        out.write(body)
    st = stats(index, len(body.encode("utf-8")))
    if counts is not None:
        st["diff"] = counts
    if a.stats:
        a.stats.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(st, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
