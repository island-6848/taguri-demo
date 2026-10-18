#!/usr/bin/env python3
"""観劇の年表の検査。

    python3 tools/taguri/test_chronicle.py

検査するのは**事実の作り方**（数え方・初出の判定・並び）と、**事実から書く読みの規則**
（期の区切り・年ごとの 1 行・締め）、**記録に無い名前を通さないか**（`_check`）である。
読みは LLM を呼ばずに規則で書くので、文そのものを決め打ちで確かめられる。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import chronicle as CR                                             # noqa: E402

ok = fail = 0


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print(f"  NG  {name}" + (f"  ← {got!r}" if got is not None else ""))


def w(key, title, date, verdict="", times=1, unseen=False, bucket=""):
    return {"work_key": key, "title": title, "first_date": date, "verdict": verdict,
            "times": times, "unseen": unseen, "bucket": bucket, "note_impression": ""}


def r(key, venues, people):
    return {"key": key, "venues": venues, "people": people}


WORKS = [
    w("a#2022", "アルファ", "2022-04-01", "◎", 2),
    w("b#2022", "ベータ", "2022-09-10", "○"),
    w("c#2023", "ガンマ", "2023-05-05", "◎"),
    w("d#2023", "デルタ", "2023-06-06", "△", 8),
    w("e#2024", "イプシロン", "2024-02-02", "◎", 3),
    w("h#2024", "ゼータ", "2024-03-03", "○"),
    w("f#nodate", "日付なし", "", "○"),
    w("g#upcoming", "これから", "2026-12-01", "", 1, False, "upcoming"),
]
RATED = [
    r("a#2022", ["帝国劇場"], [("出演", "甲"), ("演出", "甲"), ("出演", "乙")]),
    r("b#2022", ["帝国劇場"], [("出演", "甲")]),
    r("c#2023", ["本多劇場"], [("演出", "丙"), ("衣裳", "丁")]),
    r("d#2023", ["帝国劇場"], [("出演", "乙")]),
    r("e#2024", ["本多劇場"], [("出演", "乙")]),
    r("h#2024", ["帝国劇場"], [("出演", "甲")]),
]
# **題材とトーンは _themes() 経由で来る**（実物の `themes.jsonl` を読む関数）ので、
# 検査ではその場で差し替える。**原作（固有名詞）を混ぜていないかを検査するために、
# 題材とトーンに加えて意図的に「原作」の要素も入れる。**
CR._themes = lambda: {
    "a#2022": {"elements": [{"kind": "題材", "word": "家族"},
                            {"kind": "トーン", "word": "コメディ"},
                            {"kind": "原作", "word": "太宰治"}]},
    "c#2023": {"elements": [{"kind": "題材", "word": "法廷"},
                            {"kind": "トーン", "word": "シリアス"}]},
}
F = CR.facts(WORKS, RATED)
Y = {y["year"]: y for y in F["years"]}

# ---------------------------------------------------------------- 年に置ける記録
check("年ごとに分かれる", sorted(Y) == ["2022", "2023", "2024"], sorted(Y))
check("日付の無い記録は年表に載せない", F["n_works"] == 6, F["n_works"])
check("載せなかった件数を持つ", F["n_undated"] == 1, F["n_undated"])
check("これから観る公演は年表に入れない",
      all("これから" not in str(y) for y in F["years"]))
check("のべ回数は times で数える", Y["2022"]["times"] == 3, Y["2022"]["times"])

# ---------------------------------------------------------------- 初めての劇場
check("初めて行った劇場が出る", Y["2022"]["new_venues"] == ["帝国劇場"],
      Y["2022"]["new_venues"])
check("2 年目の同じ劇場は「初めて」に数えない",
      Y["2023"]["new_venues"] == ["本多劇場"], Y["2023"]["new_venues"])
check("3 年目は初めての劇場が無い", Y["2024"]["new_venues"] == [],
      Y["2024"]["new_venues"])

# ---------------------------------------------------------------- 作り手
check("同じ人を役ごとに 2 行に割らない",
      [p[0] for p in Y["2022"]["people"]] == ["甲", "乙"],
      Y["2022"]["people"])
check("役は添える", Y["2022"]["people"][0][1] == "出演 2・演出 1",
      Y["2022"]["people"][0])
check("裏方は数えない（観るかどうかを決める役だけ）",
      all(p[0] != "丁" for p in Y["2023"]["people"]), Y["2023"]["people"])
check("2 年目に出た人は「この年に出会った」に入れない",
      all(p[0] != "甲" for p in Y["2023"]["new_people"]), Y["2023"]["new_people"])

# ---------------------------------------------------------------- 「出会い」は ◎ の作品に限る
#
# 起案者の指摘（2026-08-25）──「◎をつけた人を『○○と出会い』って書いてほしい。
# 丸尾丸一郎正直誰？」。実データでは、△ の 1 作品に 3 つの役でクレジットが付いていた
# 人（座組の中で兼任）が、◎ を付けた別の人より「出会った作り手」の上に出ていた。
# **頻度は「よく出るか」を測るが「良かったか」は測らない。**
LOVE_WORKS = [w("p1#2025", "作品1", "2025-01-01", "△", 1),
              w("p2#2025", "作品2", "2025-02-01", "◎", 1)]
LOVE_RATED = [r("p1#2025", ["劇場X"], [("出演", "戊"), ("演出", "戊"), ("脚本", "戊")]),
              r("p2#2025", ["劇場Y"], [("演出", "己")])]
ly = CR.facts(LOVE_WORKS, LOVE_RATED)["years"][0]
check("頻度が高いだけで ◎ が無い人は「出会った」に入れない（不具合の再現）",
      all(nm != "戊" for nm, _, _ in ly["new_people"]), ly["new_people"])
check("◎ の作品に 1 回しか出ていなくても「出会った」に入る",
      any(nm == "己" for nm, _, _ in ly["new_people"]), ly["new_people"])
check("出演でも演出でも、◎ の作品に出ていれば良い（役は問わない）",
      ly["new_people"] == [["己", "演出 1", 1]], ly["new_people"])
check("年をまたいで観ている人が出る",
      any(p[1] == "乙" for p in F["long_people"]), F["long_people"])

# ---------------------------------------------------------------- 劇場の継続と離脱
check("通い続けている劇場（3 年以上）",
      [v[0] for v in F["kept_venues"]] == ["帝国劇場"], F["kept_venues"])
check("最近行っていない劇場は出さない（今年も行っている）",
      all(v[0] != "本多劇場" for v in F["left_venues"]), F["left_venues"])

# ---------------------------------------------------------------- 並び
check("くり返し観た作品は回数の多い順",
      Y["2023"]["repeats"] == [["デルタ", 8]], Y["2023"]["repeats"])
check("◎ を集める", Y["2023"]["loved"] == ["ガンマ"], Y["2023"]["loved"])

# ---------------------------------------------------------------- 題材とトーン
check("題材が年に付く", Y["2022"]["themes"] == [["家族", 1]], Y["2022"]["themes"])
check("トーンは題材と別に持つ", Y["2022"]["tone"] == [["コメディ", 1]], Y["2022"]["tone"])
check("原作（固有名詞）は題材に混ぜない",
      all(w != "太宰治" for w, _ in Y["2022"]["themes"]), Y["2022"]["themes"])
check("原作はトーンにも混ぜない",
      all(w != "太宰治" for w, _ in Y["2022"]["tone"]), Y["2022"]["tone"])
check("題材・トーンが無い年は空のまま", Y["2024"]["themes"] == [] and Y["2024"]["tone"] == [])
check("△× も持つ（読みの材料にする）", Y["2023"]["hard"] == ["デルタ"],
      Y["2023"]["hard"])

# ---------------------------------------------------------------- 記録が変わった印
check("同じ記録なら印は同じ", CR.fingerprint(F) == CR.fingerprint(CR.facts(WORKS, RATED)))
more = WORKS + [w("i#2025", "イータ", "2025-08-08", "◎")]
check("記録が増えたら印が変わる", CR.fingerprint(F) != CR.fingerprint(CR.facts(more, RATED)))

# ---------------------------------------------------------------- 返ってきた文の受け取り
GOOD = {"eras": [{"from": "2022", "to": "2023", "name": "帝国劇場の 2 年",
                  "body": "帝国劇場に通っていました。", "evidence": ["帝国劇場", "甲"]}],
        "years": {"2022": "帝国劇場に通い始めました。", "2023": "本多劇場が加わりました。"},
        "closing": "大きな劇場から小さな劇場へ移っています。"}
got, dropped = CR._check(GOOD, F)
check("正しい読みは通る", len(got["eras"]) == 1 and dropped == 0, (got, dropped))
check("年ごとの 1 行を受け取る", sorted(got["years"]) == ["2022", "2023"], got["years"])

BAD = {"eras": [{"from": "2022", "to": "2023", "name": "作り話",
                 "body": "シアターコクーンに通っていました。",
                 "evidence": ["シアターコクーン"]},
                {"from": "2019", "to": "2020", "name": "記録に無い年",
                 "body": "観ていた時期です。", "evidence": ["帝国劇場"]}],
       "years": {"2022": "よい年でした。", "2019": "記録に無い年です。"},
       "closing": ""}
got, dropped = CR._check(BAD, F)
check("記録に無い劇場を挙げた期は落とす", got["eras"] == [], got["eras"])
check("記録に無い年の期も落とす", dropped == 2, dropped)
check("記録に無い年の 1 行も落とす", sorted(got["years"]) == ["2022"], got["years"])

# ---------------------------------------------------------------- 図
READ = {"eras": [{"from": "2022", "to": "2023", "name": "帝国劇場の 2 年",
                  "body": "帝国劇場に通っていました。", "evidence": ["帝国劇場"]}],
        "years": {}, "closing": ""}
svg = CR._figure(F, READ)
body = svg[:svg.find("</svg>")]
check("図が出る", "<svg" in svg)
check("1 点が 1 作品", body.count('<circle class="dot') == 6,
      body.count('<circle class="dot'))
check("◎ は塗り、それ以外は輪郭",
      body.count('class="dot on"') == 3, body.count('class="dot on"'))
lanes = re.findall(r'class="vlab2"[^>]*><title>([^<]*)</title>', svg)
check("行は劇場で、初めて行った順",
      lanes[:2] == ["帝国劇場", "本多劇場"], lanes)
check("会場の記録が無い公演も落とさない",
      "劇場が記録に無い公演" not in lanes, lanes)   # この標本は全件に会場がある
check("点が左の劇場名の欄に食い込まない",
      all(float(x) >= CR.GUT for x in
          re.findall(r'<circle class="dot[^"]*" cx="([\d.]+)"', body)))
check("期の帯が出る", 'class="eband"' in svg and "帝国劇場の 2 年" in svg)
check("読みが無ければ帯は出ない", "eband" not in CR._figure(F, {}))
check("年の目盛りは年から書く", svg.count('class="ylab') == 3, svg.count('class="ylab'))
check("記録より前から始まる期の帯が、左の劇場名の欄にはみ出さない",
      all(float(x) >= CR.GUT for x in
          re.findall(r'<rect class="eband[^"]*" x="([\d.]+)"', svg)))
check("点から日記帳へ飛べる", 'href="/records/works' in body)
check("表の姿がある", "数字で見る" in svg)
check("記録が少なければ図を出さない",
      CR._figure(CR.facts(WORKS[:1], RATED), {}) == "")

# **最近通い始めた劇場が枠から落ちない。** 初めて行った順のまま頭から切ると落ちる
many = list(WORKS)
many_r = list(RATED)
for i in range(12):
    many.append(w(f"m{i}", f"作品{i}", f"2022-0{i % 9 + 1}-01"))
    many_r.append(r(f"m{i}", [f"劇場{i}"], []))
    many.append(w(f"n{i}", f"別{i}", f"2022-1{i % 2}-01"))
    many_r.append(r(f"n{i}", [f"劇場{i}"], []))
many.append(w("z1", "新しい 1", "2026-01-01"))
many.append(w("z2", "新しい 2", "2026-02-01"))
many_r.append(r("z1", ["いま通い始めた劇場"], []))
many_r.append(r("z2", ["いま通い始めた劇場"], []))
lanes2 = re.findall(r'class="vlab2"[^>]*><title>([^<]*)</title>',
                    CR._figure(CR.facts(many, many_r), {}))
check("最近通い始めた劇場が枠から落ちない", "いま通い始めた劇場" in lanes2, lanes2)
check("枠の数を超えない", len([x for x in lanes2 if not x.startswith("1 回")
                              and x != "劇場が記録に無い公演"]) <= CR.LANES,
      len(lanes2))

# ---------------------------------------------------------------- 全期間の傾向（profile の材料）
#
# 起案者の指摘（2026-08-25）──「これって結局事実の羅列ですよね？　この情報をもとに、
# このユーザーはどんな人であるのかの分析をLLMに行ってもらいたい」。年ごとの事実を
# 積んでも「何が変わったか」しか言えないので、**全期間を通した数え方**を足した。
check("全期間の題材が出る", ("家族", 1) in [tuple(x) for x in F["overall_themes"]],
      F["overall_themes"])
check("全期間のトーンが出る", ("コメディ", 1) in [tuple(x) for x in F["overall_tone"]],
      F["overall_tone"])
check("◎○△× の件数を持つ", F["verdict_tally"] == {"◎": 3, "○": 2, "△": 1},
      F["verdict_tally"])
check("2 回以上観た作品の数を持つ", F["n_repeated"] == 3, F["n_repeated"])

# ---------------------------------------------------------------- profile（どんな観客か）の検査
PGOOD = {"eras": [], "years": {},
         "profile": {"body": "帝国劇場を中心に観る一方、同じ作品を何度も観る傾向があります。",
                     "evidence": ["帝国劇場", "家族"]}, "closing": ""}
got, dropped = CR._check(PGOOD, F)
check("正しい profile は通る", got["profile"] != "" and dropped == 0, (got["profile"], dropped))

PBAD = {"eras": [], "years": {},
        "profile": {"body": "涙もろい優しい人です。",
                     "evidence": ["シアターコクーン"]}, "closing": ""}
got, dropped = CR._check(PBAD, F)
check("記録に無い根拠を挙げた profile は落とす", got["profile"] == "" and dropped == 1,
      (got["profile"], dropped))

PNONE = {"eras": [], "years": {}, "closing": ""}
got, dropped = CR._check(PNONE, F)
check("profile が無ければ空のまま（落とした数にも入れない）",
      got["profile"] == "" and dropped == 0, (got["profile"], dropped))

# ---------------------------------------------------------------- 画面
html = CR.panel(WORKS, RATED)
check("年表が出る", 'class="card chcard wide"' in html)
check("2 カラムに割らず 1 列いっぱいに描く（.figs>.wide）", 'wide' in html)
check("年が縦に並ぶ", html.count('class="chyear"') == 3, html.count('class="chyear"'))
check("題名から日記帳へ飛べる", 'href="/records/works' in html)
check("載せなかった件数を画面に書く", "1 件は" in html or "1 件" in html)
check("作り直す押し口は置かない（読みは表示のたびに書く）", 'data-chron="1"' not in html)
check("年ごとの 1 行が出る", html.count("class='chread'") == 3, html.count("class='chread'"))
check("期が出る", 'class="chera"' in html)
check("締めが出る", 'class="chclose"' in html)
check("訪問者にも同じ年表を出す（読みはその人の事実から書く）",
      CR.panel(WORKS, RATED, owner=False) == html)
check("観た本数を出す", "6 作品" in html)

# 言えることが 2 つに満たない記録では、傾向の帯を出さない
check("profile が無ければ「この記録から見えること」を出さない",
      "この記録から見えること" not in CR.panel(WORKS[:2], RATED[:2]))

# **1 本しか行っていない劇場を「いちばん通った」と書かない**
one = CR.panel([w("z#2025", "ゼータ", "2025-01-01", "○")],
               [r("z#2025", ["ザ・スズナリ"], [])])
check("1 本の年に「いちばん通った劇場」を書かない", "いちばん通った劇場" not in one, one[:200])

check("記録が空でも落ちない", CR.panel([], []) == "")

# ---------------------------------------------------------------- 読み（規則）
#
# 起案者の指示（2026-10-18）── 利用者ごとに LLM を呼ばない。読みは事実だけから規則で書く。
# **期が分かれる記録**: 帝国劇場の 2 年 → 3 年あいて本多劇場の 2 年（劇場・本数・出会い・
# 題材が同じ年に入れ替わる）。Worker の検査（`cloudflare/test/chronicle.test.js`）と同じ標本。
sys.path.insert(0, str(ROOT / "cloudflare" / "test" / "screens"))
import chronicle_fixture as FX                                     # noqa: E402

_themes_real = CR._themes
CR._themes = lambda: FX.THEMES_ERAS
FE = CR.facts(FX.ERAS_WORKS, FX.ERAS_RATED)
CR._themes = _themes_real
RE = CR.reading(FE)
check("LLM を読み込まない", "llm_gemini" not in sys.modules)
check("同じ事実からは同じ読み", CR.reading(FE) == RE)
check("2 つ以上が同じ年に入れ替わったところで期を切る",
      [(e["from"], e["to"]) for e in RE["eras"]] == [("2018", "2019"), ("2022", "2023")],
      RE["eras"])
check("期の名前は通った劇場から", [e["name"] for e in RE["eras"]]
      == ["帝国劇場に通っていた 2 年", "本多劇場に通う 2 年"], [e["name"] for e in RE["eras"]])
check("期の説明に、前の期からの劇場の移り", "通う先は帝国劇場から本多劇場へ移りました。"
      in RE["eras"][1]["body"], RE["eras"][1]["body"])
check("期の説明に、題材の移り（題材があるとき）", "題材は家族から法廷へ移っています。"
      in RE["eras"][1]["body"], RE["eras"][1]["body"])
check("期の説明は 140 字まで", all(len(e["body"]) <= CR.ERA_MAX for e in RE["eras"]))
check("すべての年に 1 行", sorted(RE["years"]) == ["2018", "2019", "2022", "2023"], RE["years"])
check("1 行は 70 字まで", all(len(x) <= CR.YEAR_MAX for x in RE["years"].values()), RE["years"])
check("記録の始まりの年", RE["years"]["2018"].startswith("記録はこの年から始まります。"),
      RE["years"]["2018"])
check("間が空いた年は、そのことから書く",
      RE["years"]["2022"].startswith("2019 年以来、3 年ぶりに観た年です。"), RE["years"]["2022"])
check("「出会い」は ◎ の作品に出ていて、後の年も観ている人", "丙と出会い、その後の年も観ています。"
      in RE["years"]["2022"], RE["years"]["2022"])
check("締めは最初の期と最後の期を比べる", RE["closing"] ==
      "通う先は帝国劇場から本多劇場へ移り、観る本数は年を追って増えています。"
      "題材は家族から法廷へ移っています。", RE["closing"])
check("ですます", all(x.endswith("。") for x in [RE["closing"], *RE["years"].values()]))
flat = CR.facts([w(f"f{i}", f"作{i}", f"202{i}-01-01", "○") for i in (1, 2, 3)],
                [r(f"f{i}", ["同じ劇場"], []) for i in (1, 2, 3)])
check("何も入れ替わらなければ期は 1 つ", len(CR.reading(flat)["eras"]) == 1,
      CR.reading(flat)["eras"])
busy = CR.facts(*FX.busy(1))
check("期は 4 つまで", 1 <= len(CR.reading(busy)["eras"]) <= 4, CR.reading(busy)["eras"])
check("年が 4 つ以上なら 1 年だけの期を作らない",
      all(e["from"] != e["to"] for e in CR.reading(busy)["eras"]), CR.reading(busy)["eras"])
check("記録が空なら読みも空", CR.reading(CR.facts([], []))["eras"] == [])
for nm, ff in (("期の標本", FE), ("最初の標本", F), ("多くの規則を通る標本", busy),
               ("小さい標本", CR.facts(WORKS[:2], RATED[:2]))):
    got, dropped = CR._check(CR.reading(ff), ff)
    check(f"規則の読みは _check で何も落ちない（{nm}）", dropped == 0
          and len(got["eras"]) == len(CR.reading(ff)["eras"]), dropped)
    have = CR._names(ff)
    quoted = re.findall(r"「([^」]+)」", json.dumps(CR.reading(ff), ensure_ascii=False))
    check(f"「」で挙げた題名はすべて記録にある（{nm}）", all(q in have for q in quoted), quoted)

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
