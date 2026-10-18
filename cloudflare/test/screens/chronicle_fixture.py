"""chronicle.panel on hand-made records, and chronicle.reading on hand-made facts: the
reference for src/screens/chronicle.js (test/chronicle.test.js).

`cases` compare the whole screen (the Worker has no themes.jsonl, so neither does Python
here). `readings` give the facts as JSON (with themes, which only the owner's batch has)
and the reading Python writes from them, so the rules are compared on themes too.

    python3 test/screens/chronicle_fixture.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def w(key, title, date, verdict="", times=1):
    return {"work_key": key, "title": title, "first_date": date, "verdict": verdict, "times": times, "bucket": "manual"}


A, B, C, D = ("出演", "甲"), ("出演", "乙"), ("演出", "丙"), ("照明", "丁")
WORKS = [w("一#2021-03-01", "一の舞台", "2021-03-01", "◎"), w("二#2021-07-01", "二 & <夜>", "2021-07-01", "○", 3),
         w("三#2022-01-10", "三の舞台はとても長い題名のついた公演でございますのでございます", "2022-01-10", "◎"),
         w("四#2022-09-01", "四の舞台", "2022-09-01", "△", 2), w("五#2023-05-05", "五の舞台", "2023-05-05", "◎"),
         w("六#2023-06-01", "六の舞台", "2023-06-01"), w("七#", "日付なし", ""), w("八#2024-01-01", "八", "2024-01-01", "◎")]
RATED = [{"key": "一#2021-03-01", "people": [A, B, C, D], "venues": ["劇場A"]},
         {"key": "二#2021-07-01", "people": [A, B], "venues": ["劇場B"]},
         {"key": "三#2022-01-10", "people": [A, C], "venues": ["劇場A"]},
         {"key": "四#2022-09-01", "people": [B, C], "venues": ["劇場C"]},
         {"key": "五#2023-05-05", "people": [A, B, C], "venues": ["劇場A"]},
         {"key": "八#2024-01-01", "people": [C], "venues": []}]

# **期が分かれる記録。** 帝国劇場の 2 年 → 3 年あいて本多劇場の 2 年（劇場・本数・出会いが
# 同じ年に入れ替わる）。題材は `THEMES_ERAS` で家族 → 法廷に移る
ERAS_WORKS = [w("k1", "雪", "2018-02-01", "○"), w("k2", "月", "2018-06-01", "◎"), w("k3", "花", "2018-09-01", "○"),
              w("k4", "鳥", "2019-03-01", "○", 2), w("k5", "風", "2019-08-01", "△"),
              w("k6", "法廷1", "2022-01-01", "◎"), w("k7", "法廷2", "2022-03-01", "◎", 4),
              w("k8", "法廷3", "2022-05-01", "○"), w("k9", "街1", "2022-07-01", "◎"),
              w("k10", "街2", "2022-09-01", "○"), w("k11", "街3", "2022-11-01", "○"),
              w("k12", "街4", "2023-02-01", "◎"), w("k13", "街5", "2023-05-01", "○"),
              w("k14", "街6", "2023-08-01", "△")]
ERAS_RATED = [{"key": "k1", "venues": ["帝国劇場"], "people": [("出演", "甲")]},
              {"key": "k2", "venues": ["帝国劇場"], "people": [("出演", "甲")]},
              {"key": "k3", "venues": ["日生劇場"], "people": [("出演", "乙")]},
              {"key": "k4", "venues": ["帝国劇場"], "people": [("出演", "甲")]},
              {"key": "k5", "venues": ["帝国劇場"], "people": [("出演", "乙")]},
              {"key": "k6", "venues": ["本多劇場"], "people": [("演出", "丙")]},
              {"key": "k7", "venues": ["本多劇場"], "people": [("演出", "丙")]},
              {"key": "k8", "venues": ["ザ・スズナリ"], "people": [("作", "丁")]},
              {"key": "k9", "venues": ["本多劇場"], "people": [("演出", "丙")]},
              {"key": "k10", "venues": ["駅前劇場"], "people": []},
              {"key": "k11", "venues": ["ザ・スズナリ"], "people": []},
              {"key": "k12", "venues": ["本多劇場"], "people": [("演出", "丙")]},
              {"key": "k13", "venues": ["本多劇場"], "people": []},
              {"key": "k14", "venues": ["シアタートラム"], "people": []}]
THEMES_ERAS = {k: {"elements": [{"kind": "題材", "word": wd}]}
               for k, wd in (("k3", "家族"), ("k4", "家族"), ("k6", "法廷"), ("k7", "法廷"), ("k8", "法廷"))}


def busy(seed):
    """**多くの規則を通る記録**（区切りが 3 つを超える・初めての劇場が 5 館以上・◎ が 6 本以上・
    何年も通う劇場）。決まった種から作るので、毎回同じ記録になる。"""
    rnd = random.Random(seed)
    vs = [f"劇場{c}" for c in "ABCDEFGHIJ"]
    ps = [("出演", "甲"), ("演出", "乙"), ("作", "丙"), ("出演", "丁"), ("振付", "戊"), ("照明", "己")]
    works, rated = [], []
    for y in (2012, 2013, 2014, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025):
        for i in range(rnd.choice((1, 2, 3, 5, 8))):
            k = f"{seed}-{y}-{i}"
            works.append(w(k, f"作品{y}-{i}", f"{y}-{rnd.randint(1, 12):02d}-01",
                           rnd.choice(("◎", "◎", "○", "△", "×", "")), rnd.choice((1, 1, 1, 2, 3, 6))))
            rated.append({"key": k, "venues": [rnd.choice(vs[:3] if y < 2018 else vs)],
                          "people": rnd.sample(ps, rnd.randint(0, 3))})
    return works, rated


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review"), str(REPO / "tools")]
    import chronicle as CR
    CR.THEMES = Path("/nonexistent")
    sets = [(WORKS, RATED), (WORKS[:2], RATED[:2]), ([], []), (ERAS_WORKS, ERAS_RATED),
            (WORKS[:4], RATED[:4]), busy(1), busy(2), busy(3)]
    cases = [{"works": ws, "rated": rs, "html": CR.panel(ws, rs, owner=False),
              "reading": CR.reading(CR.facts(ws, rs))} for ws, rs in sets]
    # 星で付ける人（issue #177）: いちばん上の評価・下の評価の数え方を Worker の grade.js とそろえる
    star = {"◎": "5/5", "○": "4/5", "△": "2/5", "×": "1/5"}
    stars = [{**x, "verdict": star.get(x["verdict"], x["verdict"])} for x in WORKS]
    star_cases = [{"works": stars, "rated": RATED, "facts": {k: v for k, v in CR.facts(stars, RATED).items() if k not in ("links", "marks")},
                   "reading": CR.reading(CR.facts(stars, RATED))}]
    real = CR._themes
    CR._themes = lambda: THEMES_ERAS
    facts = [CR.facts(ERAS_WORKS, ERAS_RATED), CR.facts(WORKS, RATED)]
    CR._themes = real
    readings = [{"facts": {k: v for k, v in f.items() if k not in ("links", "marks")},
                 "reading": CR.reading(f)} for f in facts]
    print(json.dumps({"cases": cases, "readings": readings, "star_cases": star_cases}, ensure_ascii=False))


if __name__ == "__main__":
    main()
