#!/usr/bin/env python3
"""「記録を見返す画面」のモックを、実際の観劇記録から組む。

企画書 3 章（効果 3）で挙げた 5 つの可視化を、実データで組めるかを確かめるために作る。
図の形が実データで破綻する箇所（名簿の行数・感想の語の少なさ・客席数の欠落）は、
組んで見ないと分からない。

  python3 tools/review/build_lookback.py

読む: data/review/ratings.db（評価）/ data/credits/credits.jsonl（クレジット）/
      data/credits/pages（団体名のキャッシュ）
出す: data/review/lookback.json（**端末内のみ。** 観劇履歴そのものなので外に出さない）
      図の HTML は tools/review/render_lookback.py が、この json から組む
"""
from __future__ import annotations

import collections
import html
import itertools
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M      # noqa: E402
import rate_performances as R  # noqa: E402
import recommend as RC        # noqa: E402

OUT = ROOT / "data" / "review" / "lookback.html"
CREDITS = ROOT / "data" / "credits" / "credits.jsonl"

# 検証 001 で実際に調べた会場だけ。**調べていない会場に数字を置かない。**
CAPACITY = {
    "劇場3 小劇場": (358, 468), "IMM THEATER": (705, 705),
    "紀伊國屋サザンシアターTAKASHIMAYA": (468, 468), "座・高円寺1": (233, 233),
    "劇団4スタジオ": (60, 100),
}
BANDS = [("〜100 席", 0, 100), ("101〜300 席", 101, 300),
         ("301〜700 席", 301, 700), ("701 席〜", 701, 10**6)]


def _lines(path) -> list[str]:
    """**まだ取り寄せていないファイルを、失敗として扱わない。**

    初めて使う人の端末には `credits.jsonl` も `candidates.jsonl` も無い。ここで
    例外を投げると記録を見返す画面の材料が組めず、画面に内部の失敗文言が出る
    （2026-08-24 の実測）。**無いことは「まだ 0 件」という意味である。**
    """
    # **splitlines() を使わない。** U+2028（行区切り）でも分割してしまい、
    # json.dumps(ensure_ascii=False) はこれを escape しないため、1 レコードが割れる
    # ── 実際に candidates.jsonl の 1 件が 9 行に割れて、この段が落ちた（2026-08-24）
    return path.read_text("utf-8").split("\n") if path.exists() else []


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).strip()


def load() -> list[dict]:
    """評価が付いた作品に、団体名・劇場名・観た日を付けて返す。"""
    purchases = R.load_purchases()
    con = R.connect()
    state = R.State("lookback", con, purchases)
    saved = R.read_works(con)
    credits = {(c.get("date"), c.get("mail_title")): c
               for c in (json.loads(l) for l in _lines(CREDITS) if l.strip())}

    works = []
    for w in state.works:
        row = saved.get(w["work_key"]) or {}
        people, troupes, venues, dates = [], [], [], []
        run_days, prices = [], []
        for s in w["shows"]:
            p = state.by_uid[s["uid"]]
            dates.append(p.get("date") or "")
            c = credits.get((p.get("date"), p.get("title")))
            if not c:
                continue
            f = c.get("fields") or {}
            people += M.parse_credits(f)
            if _days(f.get("期間")):
                run_days.append(_days(f["期間"]))
            if _price(f.get("料金（1枚あたり）")):
                prices.append(_price(f["料金（1枚あたり）"]))
            if nz(f.get("劇場")):
                venues.append(nz(f["劇場"]))
            t = RC.troupe_of(c.get("stage_id") or "")
            if t:
                troupes.append(nz(t))
        works.append({
            "key": w["work_key"], "title": w["title_display"],
            "dates": sorted(d for d in dates if d), "times": w["times"],
            "verdict": row.get("verdict") or "", "people": sorted(set(people)),
            "troupe": collections.Counter(troupes).most_common(1)[0][0] if troupes else "",
            "venue": collections.Counter(venues).most_common(1)[0][0] if venues else "",
            "impression": (row.get("note_impression") or "").strip(),
            "run_days": max(run_days) if run_days else None,
            "price": max(prices) if prices else None,
        })
    con.close()
    return works


# ------------------------------------------------------------------ 母集団との比較
CANDIDATES = ROOT / "data" / "review" / "candidates.jsonl"
_DATE = re.compile(r"(\d{4})/(\d{2})/(\d{2})")
_YEN = re.compile(r"([\d,]{3,7})\s*円")

RUN_BANDS = [("1 日だけ", 1, 1), ("2〜3 日", 2, 3), ("4〜7 日", 4, 7),
             ("8〜14 日", 8, 14), ("15 日以上", 15, 10 ** 6)]


def _days(period: str):
    m = _DATE.findall(period or "")
    if len(m) < 2:
        return None
    import datetime
    a = datetime.date(*map(int, m[0]))
    b = datetime.date(*map(int, m[1]))
    return (b - a).days + 1 if b >= a else None


def _price(text: str):
    v = [int(x.replace(",", "")) for x in _YEN.findall(text or "")]
    return max(v) if v else None


def population() -> list[dict]:
    """これから観られる公演（母集団）。**比較対象が無いと好みは見えない。**

    自分の記録を単独で集計すると「よく観た順」しか出ない。上演されていた公演全体と
    比べたときにだけ、自分の偏り（＝言葉にできていなかった好み）が現れる。
    しかもこの比較は **◎○△× を必要としない** ので、記録だけを残す人にも成立する。
    """
    if not CANDIDATES.exists():
        return []
    out = []
    for line in _lines(CANDIDATES):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue   # 別セッションが書き込み中の行を飛ばす
        # **終わった公演は母集団に入れない。** `fetch_candidates.py --keep-days` が手で
        # 足す欄のために残している行で、**入れると母集団が 3 倍ほどに増える。**
        # 比べる相手が変われば「自分の偏り」の出方も変わるので、**手で足す欄を直した
        # ついでに、この図の数字が動くのは筋が違う。** 母集団に足すかどうかは別に決める
        if r.get("ended"):
            continue
        out.append({"days": _days(r.get("period")), "price": _price(r.get("price"))})
    return out


def compare(works: list[dict]) -> dict:
    pop = population()
    mine = []
    for w in works:
        mine.append({"days": w.get("run_days"), "price": w.get("price")})

    def band(rows, key, lo, hi):
        v = [r[key] for r in rows if r.get(key)]
        return (sum(1 for x in v if lo <= x <= hi), len(v))

    runs = []
    for label, lo, hi in RUN_BANDS:
        pn, pt = band(pop, "days", lo, hi)
        mn, mt = band(mine, "days", lo, hi)
        if not pt or not mt:
            continue
        pp, mp = pn / pt * 100, mn / mt * 100
        runs.append({"label": label, "pop": pp, "mine": mp,
                     "ratio": (mp / pp) if pp else None, "n": mn})

    # 料金は上演日数で交絡する（ロングランは商業公演なので高い）。
    # **同じ上演日数の帯の中で比べ直す**（残差）。畳まないと同じ 1 つのことを二重に数える。
    price = []
    for label, lo, hi in [("1〜3 日", 1, 3), ("4〜14 日", 4, 14), ("15 日以上", 15, 10 ** 6)]:
        pv = sorted(r["price"] for r in pop if r.get("price") and r.get("days")
                    and lo <= r["days"] <= hi)
        mv = sorted(r["price"] for r in mine if r.get("price") and r.get("days")
                    and lo <= r["days"] <= hi)
        if len(pv) < 5 or len(mv) < 5:
            continue
        med = lambda a: a[len(a) // 2] if len(a) % 2 else (a[len(a) // 2 - 1] + a[len(a) // 2]) / 2
        price.append({"label": label, "pop": med(pv), "mine": med(mv),
                      "diff": med(mv) - med(pv), "n": len(mv)})
    return {"pop_n": len(pop), "runs": runs, "price": price}


# ------------------------------------------------------------------ 1. 名簿
SHARED = 2   # 他の作り手を 2 人以上共有していたら「同じ人たちが並ぶ公演」とみなす


def face_groups(ws: list[dict], me: str) -> list[int]:
    """その人の出演作を共演者の重なりでまとめ、各まとまりの作品数を返す。

    返す個数が「**別々の公演**」＝共演者が重ならない公演が何通りあったか。
    1 なら、いつも同じ人たちと一緒の公演でしか観ていない。
    **「顔ぶれ」という自作の比喩は使わない**（2026-08-20 の指摘。名前は何を数えたかにする）。

    **団体名で割ってはいけない。** 団体は交絡を打ち消すために内部で使った軸であって、
    当事者が関心を持っている軸ではない（2026-08-20 の指摘）。交絡の正体は
    「いつも同じ座組で観ているので、誰を追っているのか区別が付かない」ことなので、
    共演者の重なりで直接まとめる。実データでは、団体名で割ると常に共演している
    劇団1の 3 人が「3 団体で観た＝独立」と出てしまい、分けられていないものを分けていた。
    """
    names = [set(n for _, n in w["people"] if n != me) for w in ws]
    parent = list(range(len(ws)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in itertools.combinations(range(len(ws)), 2):
        if len(names[i] & names[j]) >= SHARED:
            parent[find(i)] = find(j)
    g: dict[int, int] = collections.Counter(find(i) for i in range(len(ws)))
    return sorted(g.values(), reverse=True)


def roster(works: list[dict]) -> dict[str, list[dict]]:
    """役職 → 行。棒を「同じ人たちが並ぶ公演で観た分」と「別の人たちの公演で観た分」に割る。

    1 本の棒で長さだけを見せると、同じ座組を繰り返し観たことが
    そのまま「好きな人」として読まれる（検証 016）。
    **別々の公演が 1 通りでも「好みでない」ではない** ── 座組の効果と切り分けられないだけである。
    """
    by_person: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for w in works:
        for key in w["people"]:
            by_person[key].append(w)
    declared = {nz(x) for xs in RC.DECLARED.values() for x in xs}

    out: dict[str, list[dict]] = collections.defaultdict(list)
    for (role, name), ws in by_person.items():
        if len(ws) < 2:
            continue
        g = face_groups(ws, name)
        out[role].append({
            "name": name, "n": len(ws), "in_face": g[0], "across": len(ws) - g[0],
            "faces": len(g), "declared": nz(name) in declared,
            "titles": [w["title"] for w in ws],
        })
    for role in out:
        out[role].sort(key=lambda r: (-r["faces"], -r["n"], r["name"]))
    return out


# ------------------------------- まだ言葉になっていない作り手（検証 033 追記 4）
def unspoken(works: list[dict]) -> dict:
    """**当事者がまだ言葉にしていない作り手**を返す。

    「好みを言葉にできない」をカバーするのが目的なので、**既に言葉になっている分を
    全部引いた残差だけ**を出す。引かないと、**本人が自分で申告した好みを
    「気づいていなかった発見」として返すことになり、発見に見えて循環する。**

    引くものは 4 つで、順に効いた（[検証 033](../../docs/verification/033-net-c-on-candidates.md) 追記 4）。

    | 引くもの | なぜ | 実測（n≥3 の裏方 34 人） |
    |---|---|---|
    | **申告済みの名前** | 既に言葉になっている | ── |
    | **業界での出やすさ** | 誰の履歴にも入る人がいる（音響 山本浩一は候補 818 件中 23 件） | 34 人が残る |
    | **同じ座組の繰り返し** | 同じ顔ぶれの公演を続けて観ただけ | 32 人が残る |
    | **いちばん多い劇場** | **これが支配的だった** ── 劇場3 小劇場 THE PIT に 9 本集中 | **6 人しか残らない** |

    **「好み」とは書けない。** 34 人の ◎ 率は 0.37 で全体の基準 0.378 と同じなので、
    書けるのは「**この人の仕事を N 本観ている**」までである。

    **これから観られる公演を必ず添える。** 名前だけを見せても読み手にできることが無い。
    申告に上げれば網 A が無条件で拾うので、**その場で効果が見える形にする。**
    """
    import datetime
    NC_ROWS = [json.loads(l) for l in _lines(CANDIDATES) if l.strip()]
    # 業界での出やすさ ── 候補での出現回数
    freq: collections.Counter = collections.Counter()
    upcoming: dict = collections.defaultdict(list)
    today = datetime.date.today()
    for c in NC_ROWS:
        # **終わった公演は「業界での出やすさ」の分母に入れない。** この数（候補 N 件中
        # M 件に出る）で人を落としているので、**分母が動くと落ちる人が変わる。**
        # 引き継いだ終演公演はクレジットを持っているため、入れると静かに効いてしまう
        if c.get("ended"):
            continue
        ms = _DATE.findall(c.get("period") or "")
        alive = bool(ms) and datetime.date(*map(int, ms[-1])) >= today
        for role, person in set(M.parse_credits(c["fields"])):
            freq[person] += 1
            if alive and len(upcoming[person]) < 4:
                upcoming[person].append({"title": c["title"], "theater": c.get("theater", ""),
                                         "pref": c.get("pref", ""), "period": c.get("period", ""),
                                         "role": role})
    by_person: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for w in works:
        for key in w["people"]:
            by_person[key].append(w)
    declared = {nz(x) for xs in RC.DECLARED.values() for x in xs}

    rows, dropped = [], collections.Counter()
    for (role, name), ws in by_person.items():
        if len(ws) < 3:
            continue
        dropped["対象（3 本以上で観た作り手）"] += 1
        if nz(name) in declared:
            dropped["申告済みなので外した"] += 1
            continue
        exp = len(works) * freq.get(name, 0) / max(len(NC_ROWS), 1)
        if len(ws) - exp < 2:
            dropped["業界で出やすいだけなので外した"] += 1
            continue
        if len(face_groups(ws, name)) < 2:
            dropped["同じ座組の繰り返しなので外した"] += 1
            continue
        vs = collections.Counter(w["venue"] for w in ws if w["venue"])
        top = vs.most_common(1)[0] if vs else ("", 0)
        if len(ws) - top[1] < 2:
            dropped["いちばん多い劇場で説明がつくので外した"] += 1
            continue
        rows.append({
            "role": role, "name": name, "n": len(ws),
            "maru": sum(1 for w in ws if w["verdict"] == "◎"),
            "graded": sum(1 for w in ws if w["verdict"] in M.GRADES),
            "main_venue": top[0], "main_n": top[1], "outside": len(ws) - top[1],
            "venues": [{"venue": v, "n": k} for v, k in vs.most_common()],
            "cand_freq": freq.get(name, 0),
            "titles": [{"title": w["title"], "verdict": w["verdict"], "venue": w["venue"]}
                       for w in sorted(ws, key=lambda x: x["dates"][0] if x["dates"] else "")],
            "upcoming": upcoming.get(name, []),
        })
    rows.sort(key=lambda r: (-r["outside"], -r["n"], r["name"]))

    # **1 人 1 行だけでは足りない。** 行を読めば個々の名前は分かるが、
    # **「自分の繰り返しが何で起きているか」は集計しないと出ない**（起案者の指摘）。
    # 2 つとも当事者が自分では数えられない量である。
    #
    #  ① 繰り返しの正体 ── 人ではなく座組と劇場で説明がつく割合
    #  ② 言葉にしている領域と、実際に繰り返し出会っている領域のずれ
    n_all = dropped.get("対象（3 本以上で観た作り手）", 0)
    by_cause = {
        "同じ座組で説明がつく": dropped.get("同じ座組の繰り返しなので外した", 0),
        "同じ劇場で説明がつく": dropped.get("いちばん多い劇場で説明がつくので外した", 0),
        "業界で出やすいだけ": dropped.get("業界で出やすいだけなので外した", 0),
        "すでに登録している": dropped.get("申告済みなので外した", 0),
        "人そのものが残った": len(rows),
    }
    ROLE_GROUP = (lambda r: "出演" if r == "出演"
                  else ("作り手（演出・脚本）" if r in ("演出", "脚本", "作", "原作", "翻訳")
                        else "裏方・制作"))
    # 申告した名前が、履歴のクレジットでどの役職に当たるかを数える
    role_by_name: dict = collections.defaultdict(collections.Counter)
    for (role, name), ws in by_person.items():
        role_by_name[nz(name)][role] += len(ws)
    dec = collections.Counter()
    for x in RC.DECLARED["人"]:
        rs = role_by_name.get(nz(x))
        dec[ROLE_GROUP(rs.most_common(1)[0][0]) if rs else "履歴に無い"] += 1
    got = collections.Counter(ROLE_GROUP(r["role"]) for r in rows)
    return {"rows": rows, "funnel": dict(dropped), "n_cand": len(NC_ROWS),
            "n_all": n_all, "by_cause": by_cause,
            "declared_roles": dict(dec), "found_roles": dict(got),
            "n_declared": len(RC.DECLARED["人"])}


# ------------------------------------------------------------------ 2. 探索と再訪
def by_year(works: list[dict]) -> dict:
    """年ごとに、クレジットを「初めて観た人」と「前にも観た人」に分ける。

    団体別の構成をやめた軸。**当事者が自分では数えられない切り口**であり、
    「その年は広げていたのか、固まってきたのか」に答える。企画書 3 章で挙げた
    狭窄（学習が提示の傾向に偏る）を、そのまま目で見る図にもなる。
    """
    seen: set[str] = set()
    per: dict[str, list] = collections.defaultdict(lambda: [0, 0, 0])
    for w in sorted((w for w in works if w["dates"] and w["people"]),
                    key=lambda w: w["dates"][0]):
        y = w["dates"][0][:4]
        per[y][2] += 1
        for _, name in w["people"]:
            if name in seen:
                per[y][1] += 1
            else:
                per[y][0] += 1
                seen.add(name)
    return {"rows": [{"year": y, "first": v[0], "again": v[1], "works": v[2],
                      "rate": v[1] / (v[0] + v[1]) if v[0] + v[1] else 0}
                     for y, v in sorted(per.items())]}


# ------------------------------------------------------------------ 3. 評価語の反転
# 一般のクチコミでは否定として読まれる語。**自分の中では肯定である**ことを示す。
FLIP = ["難し", "苦し", "イライラ", "泣け", "重い", "しんど", "怖", "痛"]


def flips(works: list[dict]) -> list[dict]:
    out = []
    for w in works:
        t = w["impression"]
        if not t:
            continue
        hit = [k for k in FLIP if k in t]
        if hit:
            out.append({"title": w["title"], "verdict": w["verdict"],
                        "words": hit, "text": t})
    return out


# ------------------------------------------------------------------ 4. 劇場規模
def by_capacity(works: list[dict]) -> list[dict]:
    band = collections.Counter()
    unknown = collections.Counter()
    for w in works:
        v = w["venue"]
        if not v:
            unknown["（劇場名が取れていない）"] += 1
            continue
        cap = CAPACITY.get(v)
        if not cap:
            unknown[v] += 1
            continue
        mid = (cap[0] + cap[1]) / 2
        for label, lo, hi in BANDS:
            if lo <= mid <= hi:
                band[label] += 1
    return [{"label": l, "n": band.get(l, 0)} for l, _, _ in BANDS] + \
           [{"label": "不明（客席数を調べていない）", "n": sum(unknown.values()),
             "unknown_venues": len(unknown)}]


# ------------------------------------------------------------------ 5. 感想の語
def words(works: list[dict]) -> dict:
    notes = [w for w in works if w["impression"]]
    tok = collections.Counter()
    for w in notes:
        for t in re.findall(r"[ぁ-んァ-ヶ一-龥ａ-ｚA-Za-z]{2,}", w["impression"]):
            tok[t] += 1
    return {"notes": len(notes), "total": len(works),
            "top": tok.most_common(15), "chars": sum(len(w["impression"]) for w in notes)}


def main() -> None:
    works = load()
    data = {
        "works": len(works),
        "rated": sum(1 for w in works if w["verdict"] in M.GRADES),
        "with_credits": sum(1 for w in works if w["people"]),
        "with_troupe": sum(1 for w in works if w["troupe"]),
        "roster": roster(works),
        "unspoken": unspoken(works),
        "years": by_year(works),
        "compare": compare(works),
        "flips": flips(works),
        "timeline": sorted(({"date": w["dates"][0], "title": w["title"], "venue": w["venue"],
                             "verdict": w["verdict"], "times": w["times"]}
                            for w in works if w["dates"]), key=lambda r: r["date"]),
        "capacity": by_capacity(works),
        "words": words(works),
    }
    u = data["unspoken"]
    print("■ まだ言葉になっていない作り手 ── 絞り込みの内訳")
    for k, v in u["funnel"].items():
        print(f"   {k}: {v}")
    print(f"   → 残った: {len(u['rows'])} 人")
    print("   繰り返しの正体:", u["by_cause"])
    print("   登録した名前の役職:", u["declared_roles"], "／残った人の役職:", u["found_roles"])
    for r in u["rows"]:
        print(f"      {r['role']} {r['name']}  {r['n']} 本（◎ {r['maru']}）"
              f"／主劇場 {r['main_venue'][:18]} {r['main_n']} 本・外 {r['outside']} 本"
              f"／これから {len(r['upcoming'])} 件")
    print(json.dumps({k: v for k, v in data.items()
                      if k not in ("roster", "timeline", "unspoken")},
                     ensure_ascii=False, indent=1)[:1200])
    for role, rows in sorted(data["roster"].items(), key=lambda kv: -len(kv[1])):
        print(f"{role}: {len(rows)} 行  別々の公演が 2 通り以上は "
              f"{sum(1 for r in rows if r['faces'] > 1)} 行")
    (ROOT / "data" / "review" / "lookback.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
