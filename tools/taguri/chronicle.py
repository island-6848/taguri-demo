#!/usr/bin/env python3
"""観劇の年表。**「何本観たか」ではなく「何が変わったか」を年の順に並べる。**

起案者の指示（2026-08-25）──「『眺める』のページで『観劇史』と銘打って表示するくらいなら、
もっとその人の年表らしいものを書いたほうがいい。ちゃんと LLM で分析もつけて」。

## 何が足りなかったのか

眺める画面にあったのは**本数・劇場の頻度・評価の分布**で、これは企画書 3 章が
「観劇史」と呼んでいたものである。**どれも本人の行動をそのまま数えたものなので、
本人が数えなくても知っている**（企画書 2 章の線）。年表と呼べるのは、
**その年に何が始まり、何が終わり、どこで向きが変わったか**が書いてあるものである。

## 事実も読みも規則で作る

起案者の指示（2026-10-18）の趣旨 ── 利用者は大きく増えうるので、利用者ごとに LLM を
呼ばない。規則でできるだけ LLM の質に近づけ、Claude を呼ぶのは最小限にする（ここでは
呼ばない）。**もとは読み（期の名前と説明・年ごとの 1 行・締めの文）を Gemini に
1 回で書かせていたが、いまは事実だけから決まった規則で書く**（`reading`）。

年ごとの件数・初めて行った劇場・その年に出会って続いた作り手・何度も観た作品・
題材の偏りは、**記録を数えれば出る**ので規則で作る（`facts`）。**読みはこの事実しか
見ない** ── 本文も記録も見ない。同じ事実からは必ず同じ文が出るので、Worker の
`cloudflare/src/screens/chronicle.js` も同じ文を出す（`chronicle.test.js` が突き合わせる）。

| 出すもの | 規則 |
|---|---|
| **期の名前と説明** | 劇場・作り手・題材・本数のうち **2 つ以上が同じ年に入れ替わった**ところで切る（`_turn`）。名前と説明は、その期でいちばん効いた事実を型に入れる |
| **年ごとの 1 行** | その年の事実に点を付け、**いちばん高いもの**を書く（`_year_line`） |
| **締めの 1〜2 文** | 最初の期と最後の期を比べた向き（`_closing`） |

**読みは表示のたびに作る**（年の数に比例する足し算だけで、1 ms もかからない）。
`--write` で `chronicle.json` に書き出すこともでき、事実が変わっていなければ書き直さない
（`fingerprint`）。

## 作り話を通さない

**読みに出てくる題名・劇場・人物は、事実に入っている文字列だけである。** 型に入れる
名前は事実から取るので、`_check`（記録に無い固有名を挙げた行を落とす。LLM の読みを
受けていたときの検査）は作りからして必ず通る ── `test_chronicle.py` で確かめている。

## 日付の無い記録は年表に載らない

購入確認メールに公演日が無い記録（ファンクラブ経由など）は年に置けない。**件数を
画面に書く** ── 年表の本数が「観た本数」より少ないのは、そのぶんである。

    python3 tools/taguri/chronicle.py            # いまの事実を見る
    python3 tools/taguri/chronicle.py --read     # いまの事実から書いた読みを見る
    python3 tools/taguri/chronicle.py --write    # 事実が変わっていれば読みを chronicle.json に書く
    python3 tools/taguri/chronicle.py --write --force   # 変わっていなくても書き直す
"""

from __future__ import annotations

import argparse
import ast
import collections
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools"))
import charts as CH                                                 # noqa: E402
import icons as IC                                                  # noqa: E402
import render_recommend as RR                                       # noqa: E402

E = RR.E
OUT = ROOT / "data" / "review" / "chronicle.json"
THEMES = ROOT / "data" / "credits" / "themes.jsonl"
# **作り手は、観るかどうかを決める役だけ数える。** 衣裳・音響まで入れると、同じ制作会社の
# 座組が並んだだけで「この人を追っている」ように見える（実測で上位が裏方に埋まった）
ROLES = ("出演", "演出", "作", "脚本", "翻訳", "原作", "演出補", "振付", "作曲")


# ---------------------------------------------------------------- 事実（規則）
def _elements(t: dict) -> list:
    el = t.get("elements") or []
    if isinstance(el, str):
        try:
            el = ast.literal_eval(el)
        except (ValueError, SyntaxError):
            el = []
    return [e for e in el if isinstance(e, dict)]


def _themes() -> dict:
    """学習側（観た記録）の題材。**候補側は混ぜない** ── 年表は観たものの話である。"""
    out = {}
    if not THEMES.exists():
        return out
    for line in THEMES.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        t = json.loads(line)
        if t.get("side") == "rated":
            out[t.get("id") or ""] = t
    return out


def facts(works: list[dict], rated: list[dict]) -> dict:
    """年ごとの事実。**読み（`reading`）が見るのはこれだけである。**

    `works` は観た記録（`app._records_base()["seen"]`）、`rated` はクレジットと
    突き合わせた行（`measure_nets.load_rated()`）。
    """
    rr = {r.get("key"): r for r in rated}
    th = _themes()
    dated = sorted((w for w in works
                    if (w.get("first_date") or "")[:4].isdigit()
                    and w.get("bucket") != "upcoming"),
                   key=lambda w: w["first_date"])
    by_year: dict[str, list] = collections.defaultdict(list)
    for w in dated:
        by_year[w["first_date"][:4]].append(w)

    seen_v: set = set()                       # これまでに行った劇場
    first_year: dict = {}                     # 作り手 → 初めて観た年
    ppl_years: dict = collections.defaultdict(set)
    ppl_n: collections.Counter = collections.Counter()
    ven_years: dict = collections.defaultdict(set)
    overall_subj: collections.Counter = collections.Counter()   # 全期間の題材
    overall_tone: collections.Counter = collections.Counter()   # 全期間のトーン
    years = []
    for y in sorted(by_year):
        g = by_year[y]
        ven: collections.Counter = collections.Counter()
        ppl: collections.Counter = collections.Counter()
        # **題材とトーンは別に数える。** どちらも `elements` の `kind` で分かれているが、
        # 混ぜて数えると「原作」（クシシュトフ・キェシロフスキ、のような固有名詞）が
        # 「多かった題材」に混ざる（実測 ── 原作者名が題材の欄に出ていた）。
        # **「内容の傾向」として読めるのは題材とトーンで、原作は作り手の話である**
        # （原作は `ROLES` 経由で人物として既に数えている）。
        subj: collections.Counter = collections.Counter()      # 題材（家族・法廷・戦争…）
        tone: collections.Counter = collections.Counter()      # トーン（コメディ・会話劇…）
        loved_names: set = set()          # ◎ を付けた作品に出ている作り手（この年）
        for w in g:
            r = rr.get(w.get("work_key")) or {}
            for v in (r.get("venues") or []):
                ven[v] += 1
                ven_years[v].add(y)
            for pair in (r.get("people") or []):
                role, name = (list(pair) + ["", ""])[:2]
                if role in ROLES:
                    ppl[(role, name)] += 1
                    ppl_years[(role, name)].add(y)
                    ppl_n[(role, name)] += 1
                    if w.get("verdict") == "◎":
                        loved_names.add(name)
            for e in _elements(th.get(w.get("work_key")) or {}):
                if not e.get("word"):
                    continue
                if e.get("kind") == "題材":
                    subj[e["word"]] += 1
                elif e.get("kind") == "トーン":
                    tone[e["word"]] += 1
        overall_subj.update(subj)
        overall_tone.update(tone)
        new_v = [v for v in ven if v not in seen_v]
        seen_v |= set(ven)
        # **人は名前で 1 つにまとめる。** 役ごとに数えたままだと「作り手12（演出 3 本）・
        # 作り手12（出演 2 本）」と同じ人が 2 度並ぶ（実測）。**役は添える**
        # ── 出演で観ているのか演出で観ているのかは、観るかどうかの決まり方が違う
        by_name: dict = collections.defaultdict(collections.Counter)
        for (role, nm), n in ppl.items():
            by_name[nm][role] += n
        # **「出会った」と書けるのは、◎ を付けた作品に出ていた人だけにする**（起案者の
        # 指摘 2026-08-25 ──「丸尾丸一郎と出会い、って書いてあるけど正直誰？」）。
        # **それまでは登場回数だけで選んでいた**ので、△ の作品に 3 つの役でクレジットが
        # 付いていた人（1 本の座組の中で兼任していただけ）が、◎ を付けた別の人より
        # 上に出ていた ── 頻度は「よく出るか」を測るが「良かったか」は測らない。
        # **回数のしきい値（2 本以上）は落とす** ── ◎ の作品に 1 役でも出ていれば、
        # それ自体が「出会って良かった」の証拠であり、回数は要らない。
        new_p = [(nm, c) for nm, c in
                 sorted(by_name.items(), key=lambda x: -sum(x[1].values()))
                 if nm in loved_names and all((r, nm) not in first_year for r in c)]
        for k in ppl:
            first_year.setdefault(k, y)
        years.append({
            "year": y,
            "works": len(g),
            "times": sum(int(w.get("times") or 1) for w in g),
            "venues": [[v, n] for v, n in ven.most_common(4)],
            "new_venues": new_v[:5],
            "people": [[nm, "・".join(f"{r} {n}" for r, n in c.most_common()),
                        sum(c.values())]
                       for nm, c in sorted(by_name.items(),
                                           key=lambda x: -sum(x[1].values()))[:5]],
            "new_people": [[nm, "・".join(f"{r} {n}" for r, n in c.most_common()),
                            sum(c.values())] for nm, c in new_p][:4],
            "themes": [[w_, n] for w_, n in subj.most_common(5)],
            "tone": [[w_, n] for w_, n in tone.most_common(4)],
            "loved": [w["title"] for w in g if w.get("verdict") == "◎"][:6],
            "hard": [w["title"] for w in g if w.get("verdict") in ("△", "×")][:3],
            # **多く観た順に切る。** 記録の順で切ると、その年でいちばん通った作品が
            # 落ちる（実測 ── 8 回観た 1 本が落ち、2 回の 3 本が残っていた）
            "repeats": sorted(([w["title"], int(w["times"])] for w in g
                               if int(w.get("times") or 1) > 1),
                              key=lambda x: -x[1])[:5],
            "months": sorted(collections.Counter(
                w["first_date"][5:7] for w in g).items()),
            "notes": [(w.get("note_impression") or "").strip()[:120]
                      for w in g if (w.get("note_impression") or "").strip()][:3],
        })

    ys = [x["year"] for x in years]
    # **題名 → 記録の行の鍵。** 年表から 1 件に降りる道を作るために持つ（画面だけで使い、
    # 読みには使わない ── 読みを書くのに鍵は要らない）
    links = {w["title"]: w.get("work_key") or "" for w in dated}
    # **図の材料。1 点が 1 作品である。** 集計ではなく 1 件ずつ持つ ── 振り返りの図は
    # 1 件 1 件が識別できないと無価値である（点を押すと日記帳の行へ飛ぶ）
    marks = [{"d": w["first_date"], "t": w["title"], "k": w.get("work_key") or "",
              "v": ((rr.get(w.get("work_key")) or {}).get("venues") or [""])[0],
              "verdict": w.get("verdict") or "",
              "times": int(w.get("times") or 1)} for w in dated]
    # **通い続けている劇場と、離れた劇場。** どちらも年をまたがないと出ない事実である
    keep_v = sorted(((v, sorted(s)) for v, s in ven_years.items() if len(s) >= 3),
                    key=lambda x: (-len(x[1]), x[0]))[:6]
    left_v = sorted(((v, sorted(s)) for v, s in ven_years.items()
                     if len(s) >= 2 and ys and max(s) < ys[-1]),
                    key=lambda x: (x[1][-1], -len(x[1])))[:6]
    long_p = sorted(((role, nm, sorted(s), ppl_n[(role, nm)])
                     for (role, nm), s in ppl_years.items()
                     if len(s) >= 2 and ppl_n[(role, nm)] >= 3),
                    key=lambda x: (-x[3], x[1]))[:8]
    # **どんな観客であるかの傾向を書くための材料。** 年ごとの事実を積んでも
    # 「何が変わったか」しか言えないので、**全期間を通した数え方**を別に持つ ──
    # くり返し観る／広く観る、◎○△× の割合、通し方の題材とトーンである
    verdict_tally = collections.Counter(w.get("verdict") or "" for w in dated)
    verdict_tally.pop("", None)
    n_repeated = sum(1 for w in dated if int(w.get("times") or 1) > 1)
    n_loved = sum(1 for w in dated if w.get("verdict") == "◎")
    n_hard = sum(1 for w in dated if w.get("verdict") in ("△", "×"))
    return {
        "links": links,
        "marks": marks,
        "years": years,
        "kept_venues": [[v, s[0], s[-1], len(s)] for v, s in keep_v],
        "left_venues": [[v, s[0], s[-1]] for v, s in left_v],
        "long_people": [[role, nm, s[0], s[-1], n] for role, nm, s, n in long_p],
        "overall_themes": [[w_, n] for w_, n in overall_subj.most_common(8)],
        "overall_tone": [[w_, n] for w_, n in overall_tone.most_common(6)],
        "verdict_tally": dict(verdict_tally),
        "n_repeated": n_repeated,
        "n_loved": n_loved,
        "n_hard": n_hard,
        "n_works": len(dated),
        "n_undated": sum(1 for w in works
                         if not (w.get("first_date") or "")[:4].isdigit()
                         and w.get("bucket") != "upcoming"),
    }


def fingerprint(f: dict) -> str:
    """読みの材料が変わったかどうかの印。**同じ事実からは必ず同じ読みが出る**ので、
    `write()` はこれが変わっていなければ書き直さない。
    """
    keep = ("years", "kept_venues", "left_venues", "long_people", "n_works",
            "n_repeated", "n_loved", "n_hard", "verdict_tally")
    body = json.dumps([{k: f.get(k) for k in keep}, READING_VERSION],
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(body.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 読み（規則）
#
# 起案者の指示（2026-10-18）の趣旨 ── 利用者は大きく増えうるので、利用者ごとに LLM を
# 呼ばない。規則で LLM の質にできるだけ近づける。**読みは事実だけから、決まった規則で
# 書く。** 同じ事実からは必ず同じ文が出る（Worker の `chronicle.js` も同じ文を出す）。
#
# | 出すもの | 規則 |
# |---|---|
# | **期** | 隣り合う 2 年の「変わり目の点」（`_turn`）が 2 以上の年で切る ── 旧い指示文の「劇場・作り手・題材のうち 2 つ以上が同じ年に入れ替わったところ」をそのまま数にした。多すぎれば点の高い 3 か所、無ければ点が 1 以上の 1 か所 |
# | **期の名前と説明** | その期でいちばん効いている事実（通った劇場・初めての劇場・出会い・くり返し）を、優先順の決まった型に入れる。説明は始まったこと → 前の期との違い → 終わったことの順に 3 文まで |
# | **年ごとの 1 行** | その年の事実を候補にして点を付け（`_year_line`）、いちばん高いものを書く。2 番目も 70 字に収まれば足す |
# | **締め** | 最初の期と最後の期を比べた向き（通う先・本数）と、年をまたいで続いているもの |
#
# **固有名は事実に入っている文字列しか使わない**（劇場・人・題名・題材）── `_check` は
# 作りからして必ず通る（`test_chronicle.py` で確かめている）。
# **長さは文字数（コードポイント）で数える。** JS の側も `Array.from` で数える。
READING_VERSION = "r1"
YEAR_MAX = 70                  # 年ごとの 1 行に 2 つ目の事実を足してよい長さ
ERA_MAX = 140                  # 期の説明の長さの上限
MAX_CUTS = 3                   # 期の区切りの数（期は 4 つまで）


def _ulen(s: str) -> int:
    return len(s)


def _and(xs: list) -> str:
    """「A」「AとB」「A、B、C」。**中黒では並べない** ── 劇場名にも中黒が入る。"""
    xs = list(xs)
    if len(xs) <= 1:
        return "".join(xs)
    if len(xs) == 2:
        return f"{xs[0]}と{xs[1]}"
    return "、".join(xs)


def _top_venue(y: dict) -> str:
    """その年にいちばん通った劇場。**1 本だけなら「通った」とは言わない**（画面と同じ）。"""
    return y["venues"][0][0] if y["venues"] and y["venues"][0][1] >= 2 else ""


def _top_word(rows: list, least: int = 1) -> str:
    """いちばん多い語（題材・トーン）。`least` 回に満たなければ空。"""
    return rows[0][0] if rows and rows[0][1] >= least else ""


def _appear(f: dict) -> dict:
    """作り手 → 名前が出た年（`people` は年ごとの上位 5 人）。"""
    out: dict = {}
    for y in f["years"]:
        for nm, _, _ in y["people"]:
            out.setdefault(nm, []).append(y["year"])
    return out


def _continued(y: dict, appear: dict) -> list:
    """**その年に出会って、後の年にも観ている作り手。**"""
    return [nm for nm, _, _ in y["new_people"]
            if any(yy > y["year"] for yy in appear.get(nm, []))]


def _turn(p: dict, y: dict, appear: dict) -> int:
    """前の年 `p` から `y` への変わり目の点。**1 つの事実が 1 点**で、2 点で期を切る。"""
    s = 0
    if int(y["year"]) - int(p["year"]) >= 2:                       # 間が空いた
        s += 1
    a, b = p["works"], y["works"]
    if (b >= 2 * a or 2 * b <= a) and abs(b - a) >= 2:              # 本数が倍・半分
        s += 1
    tp, ty = _top_venue(p), _top_venue(y)
    if tp and ty and tp != ty:                                      # 通う先が替わった
        s += 1
    nv = len(y["new_venues"])
    if nv >= 2 and 2 * nv > len(y["venues"]):                       # 劇場の多くが初めて
        s += 1
    if _continued(y, appear):                                       # 続く出会い
        s += 1
    hp, hy = _top_word(p["themes"]), _top_word(y["themes"])
    if hp and hy and hp != hy:                                      # 題材が替わった
        s += 1
    if y["repeats"] and y["repeats"][0][1] >= 3 and not p["repeats"]:   # くり返しが始まった
        s += 1
    return s


def _cuts(f: dict, appear: dict) -> list:
    """期の区切り（その期の最初の年の添字）。**点の高い順に取り、`MAX_CUTS` まで。**

    年が 4 つ以上あるときは **1 年だけの期を作らない** ── 記録の初めの数年は何もかもが
    「初めて」なので、そのまま切ると 1 年ずつの期が並ぶ（実測）。
    """
    ys = f["years"]
    n = len(ys)
    score = {i: _turn(ys[i - 1], ys[i], appear) for i in range(1, n)}
    order = sorted(score, key=lambda i: (-score[i], i))

    def fits(i: int, got: list) -> bool:
        return n < 4 or (i >= 2 and n - i >= 2 and all(abs(i - c) >= 2 for c in got))

    cuts: list = []
    for i in order:
        if score[i] >= 2 and len(cuts) < MAX_CUTS and fits(i, cuts):
            cuts.append(i)
    if not cuts and n >= 3:
        best = [i for i in order if score[i] >= 1 and fits(i, [])]
        cuts = best[:1]
    return sorted(cuts)


def _sum_era(g: list) -> dict:
    """1 つの期の事実を足し合わせる。"""
    ven: dict = {}
    th: dict = {}
    new_v, new_p, reps = [], [], []
    for y in g:
        for v, n in y["venues"]:
            ven[v] = ven.get(v, 0) + n
        for w_, n in y["themes"]:
            th[w_] = th.get(w_, 0) + n
        new_v += [v for v in y["new_venues"] if v not in new_v]
        new_p += [nm for nm, _, _ in y["new_people"] if nm not in new_p]
        reps += y["repeats"]
    top = sorted(ven.items(), key=lambda x: -x[1])
    tops = sorted(th.items(), key=lambda x: -x[1])
    reps = sorted(reps, key=lambda x: -x[1])
    return {"from": g[0]["year"], "to": g[-1]["year"], "k": int(g[-1]["year"]) - int(g[0]["year"]) + 1,
            "works": sum(y["works"] for y in g), "n": len(g),
            "top": top[0][0] if top and top[0][1] >= 2 else "",
            "top_n": top[0][1] if top else 0,
            "theme": tops[0][0] if tops and tops[0][1] >= 2 else "",
            "new_venues": new_v, "new_people": new_p, "repeats": reps}


def _era_name(s: dict, i: int, last: bool, prev) -> str:
    span = "年" if s["k"] == 1 else f' {s["k"]} 年'
    if s["top"] and 2 * s["top_n"] >= s["works"]:
        return f'{s["top"]}に通う{span}' if last else f'{s["top"]}に通っていた{span}'
    if len(s["new_venues"]) >= 3 and 2 * len(s["new_venues"]) >= s["works"]:
        return f"劇場を広げていった{span}"
    if s["new_people"]:
        return (f'{s["new_people"][0]}と出会った年' if s["k"] == 1
                else f'{s["new_people"][0]}と出会ってからの{span}')
    if s["repeats"] and s["repeats"][0][1] >= 3:
        return f"同じ作品に通った{span}"
    if i == 0:
        return f"観劇の記録が始まった{span}"
    if prev and s["works"] * prev["k"] > prev["works"] * s["k"]:
        return f"観る本数が増えた{span}"
    if prev and s["works"] * prev["k"] < prev["works"] * s["k"]:
        return f"本数を絞った{span}"
    return f"前の流れが続いた{span}"


def _era_body(s: dict, prev, nxt, f: dict, appear: dict) -> tuple:
    """期の説明（3 文まで・`ERA_MAX` 字まで）と、使った固有名。"""
    cand = []                                 # (文, 使った名前) を優先の順に
    nv = s["new_venues"]
    if nv:
        more = "など" if len(nv) > 2 else ""
        cand.append((f"この時期に初めて行った劇場は{_and(nv[:2])}{more}です。", nv[:2]))
    if prev and prev["top"] and s["top"] and prev["top"] != s["top"]:
        cand.append((f'通う先は{prev["top"]}から{s["top"]}へ移りました。',
                     [prev["top"], s["top"]]))
    elif not prev and s["top"]:
        cand.append((f'いちばん通ったのは{s["top"]}です。', [s["top"]]))
    if s["theme"]:
        if prev and prev["theme"] and prev["theme"] != s["theme"]:
            cand.append((f'題材は{prev["theme"]}から{s["theme"]}へ移っています。',
                         [prev["theme"], s["theme"]]))
        elif not prev or prev["theme"] != s["theme"]:
            cand.append((f'題材では{s["theme"]}が目立ちます。', [s["theme"]]))
    if s["new_people"]:
        np_ = s["new_people"][:2]
        cont = [nm for nm in np_ if any(yy > s["to"] for yy in appear.get(nm, []))]
        tail = f"{cont[0]}はこの時期のあとも観ています。" if cont else ""
        cand.append((f"{_and(np_)}に出会ったのもこの時期です。{tail}", np_))
    if prev:
        if s["works"] * prev["k"] >= 2 * prev["works"] * s["k"]:
            cand.append(("前の時期より観る本数が増えています。", []))
        elif 2 * s["works"] * prev["k"] <= prev["works"] * s["k"]:
            cand.append(("前の時期より観る本数は減っています。", []))
    if nxt:
        gone = [(v, b) for v, a, b in f["left_venues"] if s["from"] <= b <= s["to"]]
        if gone:
            v, b = gone[0]
            cand.append((f"{v}には {b} 年を最後に行っていません。", [v]))
    if s["repeats"] and s["repeats"][0][1] >= 3:
        t, n = s["repeats"][0]
        cand.append((f"「{t}」は {n} 回観ています。", [t]))
    body, ev, n = "", [], 0
    for text, names in cand:
        if n >= 3 or (body and _ulen(body) + _ulen(text) > ERA_MAX):
            continue
        body += text
        n += 1
        ev += [x for x in names if x not in ev]
    if not body:
        body = f'{s["works"]} 作品を観ています。'
    return body, ev[:3]


def _year_line(i: int, f: dict, appear: dict) -> str:
    """年ごとの 1 行。**候補に点を付けて、いちばん高い事実を書く。**"""
    ys = f["years"]
    y = ys[i]
    p = ys[i - 1] if i else None
    c = []                                    # (点, 文, 挙げた題名)。同点は足した順
    lead = ""                                 # 1 行の頭に置く枠（始まり・間が空いた）
    if not p:
        lead = "記録はこの年から始まります。"
    elif int(y["year"]) - int(p["year"]) >= 2:
        lead = f'{p["year"]} 年以来、{int(y["year"]) - int(p["year"])} 年ぶりに観た年です。'
    last = ys[-1]["year"]
    for v, a, b, n in f["kept_venues"]:
        if a == y["year"]:
            c.append((46, f"{v}に通い始めた年で、いまも通っています。" if b == last
                      else f"{v}に通い始めた年で、{b} 年まで {n} 年通いました。", ""))
            break
    cont = _continued(y, appear)
    if cont:
        c.append((50, f"{cont[0]}と出会い、その後の年も観ています。", ""))
    elif y["new_people"]:
        c.append((32, f'{y["new_people"][0][0]}と出会った年です。', ""))
    tp, ty = (_top_venue(p) if p else ""), _top_venue(y)
    if tp and ty and tp != ty:
        c.append((38, f"いちばん通った劇場が{tp}から{ty}に変わりました。", ""))
    nv = y["new_venues"]
    if not p and nv:
        c.append((30, f"最初に行った劇場は{nv[0]}です。", ""))
    elif len(nv) >= 2:
        k = len(nv)                           # `new_venues` は 5 館で切ってある
        c.append((20 + 4 * k, f"{nv[0]}など、初めての劇場が {k} 館ありました。" if k < 5
                  else f"{nv[0]}など、初めての劇場が 5 館以上ありました。", ""))
    elif nv:
        c.append((14, f"{nv[0]}に初めて行きました。", ""))
    if p:
        a, b = p["works"], y["works"]
        if b >= 2 * a and b - a >= 2:
            c.append((34, f"前の年の {a} 作品から {b} 作品に増えました。", ""))
        elif 2 * b <= a and a - b >= 2:
            c.append((26, f"前の年の {a} 作品から {b} 作品に減りました。", ""))
    if y["repeats"]:
        t, n = y["repeats"][0]
        c.append((24 + 2 * min(n, 10) if n >= 3 else 16, f"「{t}」を {n} 回観ています。", t))
    hy, hp = _top_word(y["themes"]), (_top_word(p["themes"]) if p else "")
    if hy and hp and hp != hy:
        c.append((30, f"題材が{hp}から{hy}に移りました。", ""))
    elif _top_word(y["themes"], 2):
        c.append((22, f"題材では{hy}が目立ちます。", ""))
    elif _top_word(y["tone"], 2):
        c.append((18, f'{_top_word(y["tone"])}の作品が多い年です。', ""))
    if y["loved"]:
        k = len(y["loved"])
        c.append((10 + 2 * min(k, 6),
                  f'「{y["loved"][0]}」にいちばん上の評価を付けています。' if k == 1 else
                  f'「{y["loved"][0]}」など {k} 本にいちばん上の評価を付けています。' if k < 6 else
                  f'「{y["loved"][0]}」など 6 本以上にいちばん上の評価を付けています。',
                  y["loved"][0]))
    if ty:
        c.append((8, f"{ty}を中心に観ています。", ""))
    if p:
        c.append((2, "前の年と同じ流れが続いています。", ""))
    c.append((1, f'{y["works"]} 作品を観ています。', ""))
    c = sorted(c, key=lambda x: -x[0])
    if lead:
        return lead + c[0][1] if _ulen(lead) + _ulen(c[0][1]) <= YEAR_MAX else lead
    # **2 つ目の事実は、点が 8 以上で 70 字に収まり、同じ題名を 2 度挙げないものだけ足す**
    line = c[0][1]
    for sc, text, title in c[1:2]:
        if sc >= 8 and _ulen(line) + _ulen(text) <= YEAR_MAX and not (title and title == c[0][2]):
            line += text
    return line


def _closing(f: dict, eras: list) -> str:
    """締めの 1〜2 文。**最初の期と最後の期を比べた向き**と、年をまたいで続くもの。"""
    ys = f["years"]
    first, last = ys[0]["year"], ys[-1]["year"]
    where = ("", "")                          # (続ける形, 言い切る形)
    kept = [v for v, a, b, n in f["kept_venues"] if a == first and b == last]
    if kept:
        where = (f"{kept[0]}には記録の初めから通い続けていて、",
                 f"{kept[0]}には記録の初めから通い続けています。")
    elif len(eras) >= 2 and eras[0]["top"] and eras[-1]["top"] and eras[0]["top"] != eras[-1]["top"]:
        where = (f'通う先は{eras[0]["top"]}から{eras[-1]["top"]}へ移り、',
                 f'通う先は{eras[0]["top"]}から{eras[-1]["top"]}へ移ってきました。')
    elif len(eras) >= 2 and len(eras[-1]["new_venues"]) >= 2:
        where = ("いまも新しい劇場に足を延ばしていて、", "いまも新しい劇場に足を延ばしています。")
    n = len(ys)
    much = ""
    if n >= 2:
        h = n // 2
        a = sum(y["works"] for y in ys[:h])
        b = sum(y["works"] for y in ys[h:])
        if 2 * b * h >= 3 * a * (n - h):
            much = "観る本数は年を追って増えています。"
        elif 3 * b * h <= 2 * a * (n - h):
            much = "観る本数は前より落ち着いています。"
        else:
            much = "観る本数はほぼ一定です。"
    out = []
    if much:
        out.append(where[0] + much)
    elif where[1]:
        out.append(where[1])
    if len(eras) >= 2 and eras[0]["theme"] and eras[-1]["theme"] and eras[0]["theme"] != eras[-1]["theme"]:
        out.append(f'題材は{eras[0]["theme"]}から{eras[-1]["theme"]}へ移っています。')
    elif f["long_people"]:
        role, nm, a, b, k = f["long_people"][0]
        out.append(f"{nm}は {a} 年から {b} 年まで {k} 本観ている、いちばん長く続いている作り手です。")
    if not out:
        out.append(f'{first} 年から {last} 年までの {f["n_works"]} 作品の記録です。')
    return "".join(out[:2])


def _profile(f: dict) -> tuple:
    """「この記録から見えること」。**全期間の数え方から、言える 2〜3 点だけを書く。**"""
    out, ev = [], []
    nw, nr = f["n_works"], f["n_repeated"]
    if nw >= 3:
        if nr >= 2 and 4 * nr >= nw:
            out.append(f"同じ作品に何度も足を運ぶ傾向が記録から見えます（{nw} 作品のうち "
                       f"{nr} 作品を 2 回以上）。")
        elif nr == 0:
            out.append("同じ作品を 2 度観ることはなく、毎回ちがう作品を選んでいます。")
        else:
            out.append(f"多くは 1 回ずつ観ていて、くり返し観たのは {nr} 作品です。")
    t = sum(f["verdict_tally"].values())
    if t >= 3:
        if 2 * f["n_loved"] >= t:
            out.append(f'評価を付けた {t} 作品のうち {f["n_loved"]} 作品がいちばん上で、'
                       "選んだ作品が当たりやすい傾向が見えます。")
        elif 4 * f["n_hard"] >= t:
            out.append(f'低い評価も {f["n_hard"]} 作品あり、幅広く試している様子が記録に出ています。')
    if f["overall_themes"] and f["overall_themes"][0][1] >= 2:
        w_, n = f["overall_themes"][0]
        out.append(f"題材では{w_}の作品を多く観ています（{n} 作品）。")
        ev.append(w_)
    elif f["overall_tone"] and f["overall_tone"][0][1] >= 2:
        w_, n = f["overall_tone"][0]
        out.append(f"{w_}の作品を多く観ています（{n} 作品）。")
        ev.append(w_)
    if f["kept_venues"]:
        v, a, b, n = f["kept_venues"][0]
        out.append(f"{v}には {a}〜{b} 年のうち {n} 年通っていて、決まった劇場に足を運ぶ傾向があります。")
        ev.append(v)
    if len(out) < 2:
        return "", []
    return "".join(out[:3]), ev[:3]


def reading(f: dict) -> dict:
    """事実から読みを書く。**LLM は呼ばない。** 返す形は旧い LLM の読みと同じ
    （`_check` を通る）。
    """
    ys = f["years"]
    if not ys:
        return {"eras": [], "years": {}, "profile": {}, "closing": ""}
    appear = _appear(f)
    cuts = _cuts(f, appear)
    bounds = [0] + cuts + [len(ys)]
    sums = [_sum_era(ys[bounds[k]:bounds[k + 1]]) for k in range(len(bounds) - 1)]
    eras = []
    for k, s in enumerate(sums):
        prev = sums[k - 1] if k else None
        nxt = sums[k + 1] if k + 1 < len(sums) else None
        body, ev = _era_body(s, prev, nxt, f, appear)
        eras.append({"from": s["from"], "to": s["to"],
                     "name": _era_name(s, k, nxt is None, prev),
                     "body": body, "evidence": ev})
    p_body, p_ev = _profile(f)
    return {"eras": eras,
            "years": {y["year"]: _year_line(i, f, appear) for i, y in enumerate(ys)},
            "profile": {"body": p_body, "evidence": p_ev} if p_body else {},
            "closing": _closing(f, sums)}


def _names(f: dict) -> set:
    """記録に実在する固有名の一覧。**照合はこれとしか行わない。**"""
    out: set = set()
    for y in f["years"]:
        out |= {v for v, _ in y["venues"]} | set(y["new_venues"])
        out |= {nm for nm, _, _ in y["people"]} | {nm for nm, _, _ in y["new_people"]}
        out |= set(y["loved"]) | set(y["hard"]) | {t for t, _ in y["repeats"]}
        out |= {w for w, _ in y["themes"]} | {w for w, _ in y["tone"]}
    out |= {v for v, *_ in f["kept_venues"]} | {v for v, *_ in f["left_venues"]}
    out |= {nm for _, nm, *_ in f["long_people"]}
    out |= {w for w, _ in f["overall_themes"]} | {w for w, _ in f["overall_tone"]}
    return {x for x in out if x}


def _check(read: dict, f: dict) -> tuple[dict, int]:
    """**記録に無い固有名を挙げた行を落とす。** 落とした数も返す。

    LLM の読みを受けていたときの検査で、いまは `reading` の出力の検査に使う
    （規則の読みは作りからして落ちるものが無い ── `test_chronicle.py`）。

    照合は「挙げた根拠（evidence）が記録にあるか」で行う。本文そのものを名前で
    走査すると、題名の一部（「家族」「戦争」）が普通の語として出ただけで落ちる。
    """
    have = _names(f)
    ys = {y["year"] for y in f["years"]}
    dropped = 0
    eras = []
    for e in (read.get("eras") or []):
        ev = [x for x in (e.get("evidence") or []) if isinstance(x, str)]
        if not isinstance(e.get("body"), str) or not e.get("body").strip():
            dropped += 1
            continue
        bad = [x for x in ev if x not in have]
        if bad or str(e.get("from")) not in ys or str(e.get("to")) not in ys:
            dropped += 1
            continue
        eras.append({"from": str(e["from"]), "to": str(e["to"]),
                     "name": str(e.get("name") or "")[:40],
                     "body": e["body"].strip()[:400], "evidence": ev[:3]})
    eras.sort(key=lambda e: e["from"])
    years = {str(k): str(v).strip()[:200]
             for k, v in (read.get("years") or {}).items()
             if str(k) in ys and isinstance(v, str) and v.strip()}
    # **profile も、era と同じ規則で検査する** ── 根拠（evidence）が記録に無ければ
    # 落とす。「どんな観客か」の 1 段落は、他のどの行より断定的に読まれやすいので、
    # 作り話をそのまま通す代償がいちばん大きい。
    profile = read.get("profile") or {}
    p_body = profile.get("body") if isinstance(profile, dict) else None
    p_ev = ([x for x in (profile.get("evidence") or []) if isinstance(x, str)]
            if isinstance(profile, dict) else [])
    if isinstance(p_body, str) and p_body.strip() and not [x for x in p_ev if x not in have]:
        profile_out = p_body.strip()[:400]
    else:
        profile_out = ""
        if profile:
            dropped += 1
    return ({"eras": eras, "years": years, "profile": profile_out,
             "closing": str(read.get("closing") or "").strip()[:400]}, dropped)


def write(force: bool = False) -> dict:
    """読みを `chronicle.json` に書き出す。**事実が変わっていなければ何もしない。**

    画面は表示のたびに `reading` を作るので、このファイルは見返す・比べるための控えである。
    """
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app                                                      # noqa: PLC0415
    import auth as AU                                               # noqa: PLC0415
    d = app._records_base(AU.LOCAL_USER_ID)
    f = facts(d["seen"], d["rated_rows"])
    fp = fingerprint(f)
    old = load()
    if not force and old.get("fingerprint") == fp and old.get("eras"):
        return {"ok": True, "skipped": True, "line": "記録は変わっていません"}
    read, dropped = _check(reading(f), f)
    if not read["eras"] and not read["years"]:
        return {"ok": False, "line": "年表に置ける記録がありません"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {**read, "fingerprint": fp, "dropped": dropped,
         "reading_version": READING_VERSION,
         "at": dt.date.today().isoformat()}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return {"ok": True, "line": f'年表の読みを書きました（{len(read["eras"])} 期）',
            "eras": len(read["eras"]), "dropped": dropped}


def load() -> dict:
    if not OUT.exists():
        return {}
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------- 画面
# ---------------------------------------------------------------- 図
#
# 起案者の指示（2026-08-25）──「図を用いて年表の可視化を行ってほしい」。
#
# ## 形を先に決める
#
# **この図が答える問いは「いつ、どこに通い、それがいつ入れ替わったか」である。**
# 本数の棒はこれに答えない ── 20 本の年が 2 つ並んでいても、通っている劇場が
# 入れ替わっていれば別の年である。**劇場を横のレーンに置き、観た日に点を打つ。**
# レーンは**初めて行った順**に上から並べる ── そうすると、通いが始まった劇場が
# 下へ、途切れた劇場が上に残り、**入れ替わりが階段の形で見える。**
#
# | 決めたこと | なぜ |
# |---|---|
# | **1 点 = 1 作品**（集計しない） | 振り返りの図は 1 件 1 件が識別できないと無価値である。点を押すと日記帳の行へ飛ぶ |
# | **色は 1 色**（`--s1`） | この図の仕事は時間と劇場であって、評価ではない。評価の分布は同じ画面に別の図がある。**◎ だけは塗りと輪郭で分ける**（色を足さずに 2 通目の符号を持たせる） |
# | 期の帯は**地の色**で敷く | 期は読みであって値ではない。データの色を使うと、点と同じ強さで読まれる |
#
# **`--pos` と `--neg`（◎ の緑と × の赤）は使わない。** 検証すると deutan で
# ΔE 2.3 しか離れておらず（`validate_palette.js`、下限は 8）、**色覚の型によっては
# 同じ色に見える。** この図では色を評価に使わないので、そもそも対にする必要が無い。
# **2 回以上行った劇場だけをレーンにする。** 実測では 32 館のうち 3 本以上は 4 館しかなく、
# 3 本で切ると 60 作品中 41 が「そのほか」に落ちて、**入れ替わりが見えなくなる。**
# **1 回だけの劇場は畳むが、捨てずに 1 本のレーンにする** ── その行が厚くなる時期は
# 「あちこち観に行った時期」そのものなので、これも年表の中身である。
LANES = 10                     # 個別のレーンにする劇場の数（残りは下の 2 行に畳む）
LANE_MIN = 2                   # レーンにする最低の本数
LH = 25                        # レーンの高さ
GUT = 176                      # 左の劇場名の幅
FW = 900                       # 図の横幅（viewBox の座標）
TOP = 38                       # 期の帯の名前を置く帯


def _ym(d: str) -> int:
    """年月を通し番号にする。**月の粒で置く** ── 日まで使うと、同じ月の 2 本が重なる。"""
    return int(d[:4]) * 12 + int(d[5:7]) - 1


def _figure(f: dict, read: dict) -> str:
    """年表の図。**劇場を横のレーン、時間を横軸、1 点を 1 作品とする。**"""
    marks = [m for m in f["marks"] if m["d"]]
    if len(marks) < 3:
        return ""
    lo, hi = min(_ym(m["d"]) for m in marks), max(_ym(m["d"]) for m in marks)
    span = max(hi - lo, 1)
    plot = FW - GUT - 14

    def x(ym: float) -> float:
        return GUT + (ym - lo) / span * plot

    def cx(ym: float) -> float:
        """**図の枠に収める。** 期は年の初めから始まるが、記録はその年の途中から
        始まることがある ── 素の位置に置くと、**帯も年の目盛りも左の劇場名の欄に
        はみ出す**（実測で 1 つ目の帯が x=93 に出ていた。名前の欄は 176 まである）。
        """
        return min(max(x(ym), GUT), FW - 14)

    # レーン ── **初めて行った順**に並べる（入れ替わりが階段になる）
    cnt: collections.Counter = collections.Counter(m["v"] for m in marks if m["v"])
    first: dict = {}
    for m in marks:
        if m["v"]:
            first.setdefault(m["v"], _ym(m["d"]))
    # **枠に収まらないときの選び方。** 初めて行った順のまま頭から切ると、
    # **最近通い始めた劇場が必ず落ちる** ── いちばん見たい「いま何が始まっているか」が
    # 消える。回数の多い順だけで選んでも同じで、**通い始めたばかりの劇場は回数で負ける。**
    # そこで**枠の 3 つを「最近始まった順」に取り分けてから**、残りを回数の多い順で埋める。
    qual = [v for v, n in cnt.items() if n >= LANE_MIN]
    keep = sorted(qual, key=lambda v: (-cnt[v], first[v]))[:max(LANES - 3, 1)]
    late = sorted((v for v in qual if v not in keep),
                  key=lambda v: -first[v])[:max(LANES - len(keep), 0)]
    big = sorted(keep + late, key=lambda v: first[v])
    rest = [m for m in marks if m["v"] and m["v"] not in big]
    none = [m for m in marks if not m["v"]]
    lanes = list(big)
    if rest:
        lanes.append(f'1 回だけ行った劇場（{len({m["v"] for m in rest})} 館）')
    if none:
        lanes.append("劇場が記録に無い公演")
    row = {v: i for i, v in enumerate(lanes)}
    fall = lanes[len(big)] if rest else (lanes[-1] if none else "")
    h = TOP + len(lanes) * LH + 26

    # 期の帯（読みがあるときだけ）。**地の色で敷く** ── 期は読みであって値ではない
    bands = []
    for i, e in enumerate(read.get("eras") or []):
        a, b = cx(int(e["from"]) * 12), cx(int(e["to"]) * 12 + 11)
        bands.append(
            f'<rect class="eband{" alt" if i % 2 else ""}" x="{a:.1f}" y="{TOP - 16:.0f}"'
            f' width="{max(b - a, 2):.1f}" height="{len(lanes) * LH + 16:.0f}" rx="4"/>'
            f'<text class="elab" x="{a + 6:.1f}" y="{TOP - 22:.0f}">{E(e["name"])}</text>')

    # 年の目盛り。**年から書く**（月日だけでは何年の話か分からない）
    grid = []
    for y in range(lo // 12, hi // 12 + 1):
        gx, edge = cx(y * 12), x(y * 12) < GUT
        grid.append(("" if edge else
                     f'<line class="gl" x1="{gx:.1f}" y1="{TOP - 16:.0f}"'
                     f' x2="{gx:.1f}" y2="{TOP + len(lanes) * LH:.0f}"/>')
                    + f'<text class="ylab{" st" if edge else ""}" x="{gx:.1f}"'
                    f' y="{h - 8:.0f}">{y}</text>')

    rows_svg, dots = [], []
    for v in lanes:
        i = row[v]
        cy = TOP + i * LH + LH / 2
        rows_svg.append(
            f'<line class="lane" x1="{GUT}" y1="{cy:.1f}" x2="{FW - 14}" y2="{cy:.1f}"/>'
            f'<text class="vlab2" x="{GUT - 10}" y="{cy + 4:.1f}">'
            f'<title>{E(v)}</title>{E(_cut(v, 15))}</text>')
    for m in marks:
        v = (m["v"] if m["v"] in row
             else ("劇場が記録に無い公演" if not m["v"] and none else fall))
        if v not in row:
            continue
        cy = TOP + row[v] * LH + LH / 2
        cx = x(_ym(m["d"]))
        solid = m["verdict"] == "◎"
        say = (f'{m["t"]} ── {m["d"]}'
               + (f'・{m["times"]} 回' if m["times"] > 1 else "")
               + (f'・{m["verdict"]}' if m["verdict"] else ""))
        a = CH._anchor(m["k"]) if m["k"] else ""
        dot = (f'<circle class="dot{" on" if solid else ""}" cx="{cx:.1f}"'
               f' cy="{cy:.1f}" r="4.5"><title>{E(say)}</title></circle>')
        dots.append(f'<a href="{CH.ROW_HREF}&amp;w={E(a)}#w-{E(a)}">{dot}</a>'
                    if a else dot)

    n_lane = sum(cnt[v] for v in big)
    # **表の姿。** 図が読めないときの経路であり、「この劇場に何年に何本」を
    # 数字で引きたいときはこちらが速い（既存の図と同じ約束）
    ys_lab = [f"{y} 年" for y in range(lo // 12, hi // 12 + 1)]
    tbl = []
    for v in lanes:
        got = [m for m in marks
               if (m["v"] if m["v"] in row else
                   ("劇場が記録に無い公演" if not m["v"] and none else fall)) == v]
        per = collections.Counter(m["d"][:4] for m in got)
        tbl.append([v] + [per.get(str(y), "") for y in range(lo // 12, hi // 12 + 1)]
                   + [len(got)])
    # **横幅は 100% にする**（起案者の指示 2026-08-25）── 990px の枠に固定していたが、
    # 図の中身（年の範囲・劇場の数）に上限は無いので、**広い画面ではその分だけ広げてよい。**
    # `viewBox` の座標系は変えない ── 文字と点の大きさは `FW` を基準に決めているので、
    # 座標だけ変えると文字が伸び縮みする
    return (f'<div class="chfig"><svg viewBox="0 0 {FW} {h}" width="100%"'
            f' role="img"'
            f' aria-label="観劇の年表。横が時間、1 本の行が 1 つの劇場、1 点が 1 作品">'
            f'{"".join(bands)}{"".join(grid)}{"".join(rows_svg)}{"".join(dots)}'
            f'</svg></div>'
            f'<div class="legend chleg">'
            f'<span class="lg"><svg width="13" height="13" viewBox="0 0 13 13"'
            f' aria-hidden="true"><circle class="dot on" cx="6.5" cy="6.5" r="4.5"/>'
            f'</svg>◎ を付けた作品</span>'
            f'<span class="lg"><svg width="13" height="13" viewBox="0 0 13 13"'
            f' aria-hidden="true"><circle class="dot" cx="6.5" cy="6.5" r="4.5"/>'
            f'</svg>そのほかの作品</span>'
            f'<span class="lgn">行は劇場です。<b>初めて行った順</b>に上から'
            f'並べているので、<b>行の始まりと終わりが通い始めた時期と'
            f'途切れた時期です。</b>'
            f'{LANE_MIN} 回以上行った {len(big)} 館（{n_lane} 作品）を 1 行ずつにし、'
            f'1 回だけの劇場は下に 1 行でまとめています。</span></div>'
            + CH._table(["劇場"] + ys_lab + ["計"], tbl))


def _chips(y: dict, links: dict) -> str:
    """その年の事実。**1 件 1 件が識別できる形で出す** ── 題名は日記帳の行へ飛ぶ。

    **区切りは「／」にする。** 劇場名にも題名にも中黒が入る（「COOL JAPAN PARK
    OSAKA・TT ホール」「札幌市教育文化会館・大ホール」）ので、中黒で並べると
    **どこまでが 1 館なのか読めない。**
    """
    out = []
    if y["new_venues"]:
        out.append(f'<li><b>初めて行った劇場</b>{E("／".join(y["new_venues"][:3]))}</li>')
    if y["new_people"]:
        out.append('<li><b>この年に出会った作り手</b>'
                   + E("／".join(f'{nm}（{_roles(roles)}）'
                                 for nm, roles, _ in y["new_people"][:3])) + "</li>")
    if y["repeats"]:
        out.append('<li><b>くり返し観た作品</b>'
                   + "／".join(f'{_work_link(t, links)}（{n} 回）'
                               for t, n in y["repeats"][:3]) + "</li>")
    if y["loved"]:
        out.append('<li><b>◎ を付けた作品</b>'
                   + "／".join(_work_link(t, links) for t in y["loved"][:3])
                   + (f'　ほか {len(y["loved"]) - 3} 本' if len(y["loved"]) > 3 else "")
                   + "</li>")
    if y["themes"]:
        out.append(f'<li><b>多かった題材</b>{E("／".join(w for w, _ in y["themes"][:4]))}</li>')
    if y["tone"]:
        out.append(f'<li><b>多かったトーン</b>{E("／".join(w for w, _ in y["tone"][:4]))}</li>')
    return f'<ul class="chfacts">{"".join(out)}</ul>' if out else ""


def _roles(roles: str) -> str:
    """「演出 3・出演 2」→「演出 3 本・出演 2 本」。**役は 2 つまでにする** ── 3 つ並ぶと
    名前より役のほうが長くなり、誰の話なのかが読めない。
    """
    return "・".join(f"{x} 本" for x in roles.split("・")[:2])


def _cut(title: str, n: int = 34) -> str:
    """題名を詰める。**切ったことが分かるようにする** ── 切った跡が無いと、
    途中で終わっている題名がそういう題名に見える。
    """
    return title if len(title) <= n else title[:n] + "…"


def _work_link(title: str, links: dict) -> str:
    """題名から日記帳の行へ。**図から 1 件に降りる道を切らない**（`charts.ROW_HREF`）。

    鍵が引けないときは**飛べない文字のまま出す** ── 押しても何も起きない押し口を
    作らない。
    """
    key = links.get(title) or ""
    if not key:
        return E(_cut(title))
    a = CH._anchor(key)
    return (f'<a href="{CH.ROW_HREF}&amp;w={E(a)}#w-{E(a)}"'
            f' title="{E(title)}">{E(_cut(title))}</a>')


def panel(works: list[dict], rated: list[dict], *, owner: bool = True) -> str:
    """年表。**読みは表示のたびに、その人の事実から規則で書く**（`reading`）。

    **持ち主にも訪問者にも同じものを出す。** もとは読みがローカルの持ち主の記録から
    作った 1 ファイル（`chronicle.json`）しか無かったので、訪問者（`owner=False`）には
    出さなかった（E3）。いまの読みは見ている人自身の事実から書くので、他人の読みが
    載ることは無い。`owner` は呼び出し側との形を保つために残している。
    """
    f = facts(works, rated)
    if not f["years"]:
        return ""
    read = reading(f)
    eras = read.get("eras") or []
    era_of = {}
    for e in eras:
        for y in f["years"]:
            if e["from"] <= y["year"] <= e["to"]:
                era_of.setdefault(y["year"], e)

    rows, shown_era = [], set()
    for y in f["years"]:
        e = era_of.get(y["year"])
        if e and id(e) not in shown_era:
            shown_era.add(id(e))
            ev = ("".join(f'<span class="ev">{E(x)}</span>' for x in e["evidence"])
                  if e["evidence"] else "")
            rows.append(f'<div class="chera"><h3>{E(e["from"])}〜{E(e["to"])} '
                        f'{E(e["name"])}</h3><p>{E(e["body"])}</p>{ev}</div>')
        line = read.get("years", {}).get(y["year"]) or ""
        # **1 本しか行っていない劇場を「いちばん通った」とは書かない。**
        # 数えれば 1 位だが、通ったとは言えない
        top = (y["venues"][0][0] if y["venues"] and y["venues"][0][1] >= 2 else "")
        rows.append(
            f'<div class="chyear"><div class="chy"><b>{E(y["year"])}</b>'
            f'<i>{y["works"]} 作品・のべ {y["times"]} 回</i></div>'
            f'<div class="chbody">'
            f'{f"<p class=\'chread\'>{E(line)}</p>" if line else ""}'
            f'{f"<p class=\'chtop\'>いちばん通った劇場は{E(top)}です。</p>" if top else ""}'
            f'{_chips(y, f["links"])}</div></div>')

    kept = ("／".join(f'{v}（{a}〜{b} 年に {n} 年）' for v, a, b, n in f["kept_venues"][:3])
            if f["kept_venues"] else "")
    long_p = ("／".join(f'{nm}（{role}・{a}〜{b} 年に {n} 本）'
                        for role, nm, a, b, n in f["long_people"][:3])
              if f["long_people"] else "")
    across = ""
    if kept or long_p:
        across = ('<div class="chacross"><h3>年をまたいで続いているもの</h3><ul>'
                  + (f'<li><b>通い続けている劇場</b>{E(kept)}</li>' if kept else "")
                  + (f'<li><b>何年も観ている作り手</b>{E(long_p)}</li>' if long_p else "")
                  + "</ul></div>")

    p_body = (read.get("profile") or {}).get("body") or ""
    profile = (f'<div class="chprofile"><h3>この記録から見えること</h3>'
               f'<p>{E(p_body)}</p></div>' if p_body else "")
    closing = (f'<p class="chclose">{E(read["closing"])}</p>'
               if read.get("closing") else "")
    # **作り直す押し口は置かない** ── 読みは表示のたびに今の事実から書くので、古くならない
    made = ('<p class="chnote">この年表の文（時期の名前・年ごとの 1 行・'
            'どんな観客であるかの傾向・締めの文）は、上に並んでいる事実だけを材料に、'
            '決まった規則で書いています。記録が増えると書き変わります。</p>')
    undated = (f'<p class="chnote">公演日が記録に無い {f["n_undated"]} 件は、'
               f'年に置けないのでこの年表には出していません。'
               f'「日記帳」には残っています。</p>' if f["n_undated"] else "")

    # **1 列いっぱいに描く。**（起案者の指示 2026-08-25 ──「2 カラムじゃなくて
    # 1 カラムとして横幅まるまる使って描画して」）。横のレーンで劇場を並べる図なので、
    # 半分の幅では**レーンの本数だけ縦に伸びて、時間の軸が詰まる** ── 地図・人の網と
    # 同じ理由で `wide` を付ける（`app.py` の `.figs>.wide`）。
    return f"""<section class="card chcard wide">
{IC.h2("book", "観劇の年表", f'<span class="badge part">{f["n_works"]} 作品</span>')}
<p class="lead">記録を年の順に並べ、<b>その年に何が始まったか</b>を出しています。
本数だけでは同じに見える年でも、通う劇場と観る作り手は入れ替わっています。
<b>図の 1 点が 1 作品です。点を押すと、その公演の記録に飛びます。</b></p>
{profile}
{_figure(f, read)}
{"".join(rows)}{across}{closing}
<div class="chfoot">{made}<span class="said"></span></div>
{undated}</section>{JS}"""


STYLE = """
/* ---- 観劇の年表 ------------------------------------------------------------
   **年が縦に流れる形にする。** 棒の高さで年を比べる図は既に別に持っており、
   ここで見たいのは高さではなく順序と切れ目である。                           */
/* **この節の `max-width` は `ch` ではなく `em` にする**（起案者の指摘 2026-08-26
   ──「なぜか途中で改行されてしまっている」）。理由は render_recommend.py の
   `.lead` にある ── `ch` は全角文字では約半分の文字数しか入らない。         */
.chcard .chera{border-left:3px solid var(--curtain);padding:2px 0 2px 14px;
 margin:22px 0 10px}
.chcard .chera h3{font-size:15px;margin:0 0 5px}
.chcard .chera p{margin:0;font-size:13px;line-height:1.75;color:var(--ink2);max-width:74em}
.chcard .ev{display:inline-block;font-size:11px;color:var(--mute);
 border:1px solid var(--grid);border-radius:999px;padding:1px 9px;margin:7px 6px 0 0}
.chyear{display:flex;gap:16px;padding:11px 0;border-top:1px solid var(--grid)}
.chyear .chy{flex:none;width:104px;text-align:right}
.chyear .chy b{display:block;font-size:19px;font-weight:600;line-height:1.2;
 font-family:var(--mincho)}
.chyear .chy i{font-style:normal;font-size:11px;color:var(--mute)}
.chyear .chbody{min-width:0;flex:1}
.chyear .chread{margin:0 0 4px;font-size:13.5px;line-height:1.7}
.chyear .chtop{margin:0 0 4px;font-size:12px;color:var(--ink2)}
.chfacts{list-style:none;margin:4px 0 0;padding:0;font-size:12px;color:var(--ink2)}
.chfacts li{margin:2px 0;line-height:1.65}
.chfacts b{display:inline-block;min-width:9.5em;font-weight:600;color:var(--mute);
 font-size:11px;margin-right:6px}
/* ---- 年表の図 ── 横が時間、1 行が 1 劇場、1 点が 1 作品 ------------------- */
.chfig{overflow-x:auto;margin:4px 0 6px}
.chfig svg{display:block;min-width:620px}
.chfig .eband{fill:color-mix(in srgb,var(--base) 13%,transparent)}
.chfig .eband.alt{fill:color-mix(in srgb,var(--base) 6%,transparent)}
.chfig .elab{font-size:11px;fill:var(--ink2);font-weight:600}
.chfig .gl{stroke:var(--grid);stroke-width:1}
.chfig .ylab{font-size:11px;fill:var(--mute);text-anchor:middle}
.chfig .ylab.st{text-anchor:start}
.chfig .lane{stroke:var(--grid);stroke-width:1}
.chfig .vlab2{font-size:11.5px;fill:var(--ink2);text-anchor:end}
/* **色は 1 色。** この図の仕事は時間と劇場であって評価ではない。
   ◎ だけは塗りと輪郭で分ける ── 色を足さずに 2 通目の符号を持たせる */
.dot{fill:var(--surf);stroke:var(--s1);stroke-width:2}
.dot.on{fill:var(--s1);stroke:var(--surf);stroke-width:1.5}
.chfig a:hover .dot{stroke:var(--curtain)}
.chleg{margin:0 0 14px}
/* **`.lg`（`inline-flex`）は付けない。** 付けると、中に挟んだ `<b>` の前後で
   文が別々の箱（匿名 flex item）に割れ、箱ごとに幅を持たされて狭い所で
   折り返される（実測 ── 「初めて行った順」が「初めて行っ」「た順」に千切れて
   いた）。`flex-basis:100%` で、短い凡例（◎など）と同じ行には並べず、
   必ず自分の行にする */
.chleg .lgn{display:block;flex-basis:100%;color:var(--mute);font-size:11px;
 line-height:1.6}
.chacross{margin:18px 0 0;padding:12px 14px;background:var(--plane);border-radius:8px}
.chacross h3{font-size:13.5px;margin:0 0 6px}
.chacross ul{list-style:none;margin:0;padding:0;font-size:12px;color:var(--ink2)}
.chacross b{display:inline-block;min-width:11em;font-weight:600;color:var(--mute);
 font-size:11px;margin-right:6px}
/* **「この記録から見えること」は、年ごとの読みより一段強く出す。** 年表全体を
   見て初めて言える 1 段落なので、いちばん上に帯の形で置く。**`--curtain-w` は
   幕のえんじの上に置く文字の色**であって地の色ではない（`app.py` の帯・見出しの
   約束）ので、地に使うと暗い画面で文字が読めなくなる。ここは既存の `.chera` と
   同じ形（幕のえんじの左帯＋通常の地色）に揃える。                             */
.chprofile{background:var(--surf);border:1px solid var(--grid);border-left:3px solid var(--curtain);
 border-radius:0 8px 8px 0;padding:14px 16px;margin:2px 0 18px}
.chprofile h3{font-size:12.5px;margin:0 0 6px;color:var(--curtain);font-weight:600}
.chprofile p{margin:0;font-size:14px;line-height:1.75;color:var(--ink);max-width:74em}
.chclose{margin:16px 0 0;font-size:13.5px;line-height:1.8;border-left:2px solid var(--base);
 padding-left:12px;max-width:74em}
.chfoot{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:16px 0 0}
.chfoot button{font:inherit;font-size:12.5px;padding:6px 14px;border-radius:6px;
 border:1px solid var(--acc);background:var(--acc);color:var(--surf);cursor:pointer}
.chfoot .said{font-size:11.5px;color:var(--mute)}
.chnote{font-size:11.5px;color:var(--mute);margin:8px 0 0;max-width:74em;line-height:1.7}
.chcard .chfoot .chnote{margin:0;flex:1 1 100%}
@media(max-width:700px){.chyear{flex-direction:column;gap:4px}
 .chyear .chy{width:auto;text-align:left;display:flex;align-items:baseline;gap:8px}}
"""

JS = """<script>
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest("[data-chron]");
  if (!b) return;
  const box = b.closest(".chfoot");
  box.querySelector(".said").textContent = "書いています…（1 分ほどかかります）";
  post("/api/chronicle", {}, box, null).then(r => {
    box.querySelector(".said").textContent =
      r ? (r.line || "作りました") + "　画面を読み込み直すと出ます" : "";
  });
});
</script>"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--read", action="store_true", help="事実から書いた読みを見る")
    ap.add_argument("--write", action="store_true", help="読みを chronicle.json に書く")
    ap.add_argument("--force", action="store_true", help="事実が変わっていなくても書き直す")
    a = ap.parse_args()
    if a.write:
        r = write(a.force)
        print(r.get("line", ""))
        return 0 if r.get("ok") else 1
    import app                                                      # noqa: PLC0415
    import auth as AU                                               # noqa: PLC0415
    d = app._records_base(AU.LOCAL_USER_ID)
    f = facts(d["seen"], d["rated_rows"])
    print(json.dumps(reading(f) if a.read else f, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
