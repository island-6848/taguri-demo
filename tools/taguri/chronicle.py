#!/usr/bin/env python3
"""観劇の年表。**「何本観たか」ではなく「何が変わったか」を年の順に並べる。**

起案者の指示（2026-08-25）──「『眺める』のページで『観劇史』と銘打って表示するくらいなら、
もっとその人の年表らしいものを書いたほうがいい。ちゃんと LLM で分析もつけて」。

## 何が足りなかったのか

眺める画面にあったのは**本数・劇場の頻度・評価の分布**で、これは企画書 3 章が
「観劇史」と呼んでいたものである。**どれも本人の行動をそのまま数えたものなので、
本人が数えなくても知っている**（企画書 2 章の線）。年表と呼べるのは、
**その年に何が始まり、何が終わり、どこで向きが変わったか**が書いてあるものである。

## 事実は規則で作り、読みだけを LLM に書かせる

**担い手を分ける。** 年ごとの件数・初めて行った劇場・その年に出会って続いた作り手・
何度も観た作品・題材の偏りは、**記録を数えれば出る**ので規則で作る（`facts`）。
LLM に渡すのはその結果だけで、**本文も記録も渡さない。**

**LLM が書くのは 3 つだけである。**

| 出すもの | なぜ規則で書けないか |
|---|---|
| **期の名前と説明** | 「帝国劇場に通っていた時期」と「小劇場に移った時期」の境目は、劇場・題材・作り手の変化が**同時に起きた年**を人の言葉でまとめる作業である。閾値では切れない |
| **年ごとの 1 行** | その年の事実のうち**どれが効いたか**の判断が要る。件数の増減を書くだけなら規則で足りるが、それは既に表にある |
| **締めの 1〜2 文** | 全体を通した向きの読み |

**呼び出しは 1 回である。** 年ごとに呼ぶと年をまたぐ話が書けないうえ、記録が増えるたびに
呼ぶ回数が増える。**記録が変わっていなければ呼ばない**（`fingerprint`）。

## 作り話を通さない

**LLM が挙げた題名・劇場・人物が記録に無ければ、その行を落とす**（`_check`）。
年表は「自分の記録」として読まれるので、**1 行でも作り話が混ざると全体が読めなくなる。**
落ちた行は黙って消さず、画面に件数を出す。

## 日付の無い記録は年表に載らない

購入確認メールに公演日が無い記録（ファンクラブ経由など）は年に置けない。**件数を
画面に書く** ── 年表の本数が「観た本数」より少ないのは、そのぶんである。

    python3 tools/taguri/chronicle.py            # いまの事実を見る（LLM は呼ばない）
    python3 tools/taguri/chronicle.py --write    # 記録が変わっていれば読みを作り直す
    python3 tools/taguri/chronicle.py --write --force   # 変わっていなくても作り直す
"""

from __future__ import annotations

import argparse
import ast
import collections
import datetime as dt
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
import llm_gemini as LLM                                            # noqa: E402

E = RR.E
OUT = ROOT / "data" / "review" / "chronicle.json"
THEMES = ROOT / "data" / "credits" / "themes.jsonl"
MODEL = LLM.MODEL
PROMPT_VERSION = "h5"
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
    """年ごとの事実。**LLM に渡すのはこれだけである。**

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
    # LLM には渡さない ── 読みを書くのに鍵は要らないうえ、入力が長くなる）
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
        "n_works": len(dated),
        "n_undated": sum(1 for w in works
                         if not (w.get("first_date") or "")[:4].isdigit()
                         and w.get("bucket") != "upcoming"),
    }


def fingerprint(f: dict) -> str:
    """記録が変わったかどうかの印。**変わっていなければ LLM を呼ばない。**"""
    ys = [(x["year"], x["works"], x["times"], len(x["loved"])) for x in f["years"]]
    return json.dumps([ys, f["n_works"], sorted(f["verdict_tally"].items()),
                       f["n_repeated"], PROMPT_VERSION], ensure_ascii=False)


# ---------------------------------------------------------------- 読み（LLM）
PROMPT = """あなたは、ある人の観劇の記録から「年表の読み」を書く部品である。

入力は JSON で、その人が観た公演を年ごとに集計した**事実だけ**が入っている。
years は年ごとの集計（works=作品数、times=のべ回数、venues=劇場と回数、
new_venues=その年に初めて行った劇場、people=よく名前が出た作り手、
**new_people=その年に初めて観て、しかも◎を付けた作品に出ていた作り手（『出会い』
と呼べるのはこの人たちだけである。頻度が高いだけで◎が付いていない人はここに
出てこない）**、themes=あらすじから取った題材（家族・法廷・戦争のような内容の要素）、
tone=あらすじから取った作品のトーン（コメディ・会話劇・群像劇のような雰囲気）、
loved=◎を付けた作品、hard=△×を付けた作品、repeats=同じ作品を観た回数、months=観た月、
notes=本人が書いた感想の抜粋）。
kept_venues=何年も通っている劇場、left_venues=通っていたが最近行っていない劇場、
long_people=何年にもわたって観ている作り手。**overall_themes・overall_tone=全期間を
通した題材・トーンの集計（年ごとの themes・tone とは別に、記録全体でまとめたもの）、
verdict_tally=◎○△×それぞれの件数、n_repeated=2 回以上観た作品の数、n_works=観た
作品数の合計。**

次の 4 つを JSON で返す。**説明や前置きを書かず、JSON だけを返すこと。**

{
  "eras": [{"from": "2022", "to": "2023", "name": "…", "body": "…",
            "evidence": ["…", "…"]}],
  "years": {"2022": "…", "2023": "…"},
  "profile": {"body": "…", "evidence": ["…", "…"]},
  "closing": "…"
}

- eras ── 記録を 2〜4 個の時期に区切る。区切る場所は、**劇場・作り手・題材のうち
  2 つ以上が同じ年に入れ替わったところ**にする。name は 8〜18 字の短い名前
  （例:「帝国劇場に通っていた 2 年」）。body は 60〜140 字で、**何が始まり何が終わったか**を書く。
  **その時期に観ていた作品の内容の傾向（themes・tone に出ている語）も、前後の時期と
  比べて何が増え何が減ったかという形で必ず 1 つ入れる**（例:「家族劇から法廷劇へ移った」
  「コメディが増えた」）。themes・tone に手がかりが無い時期は、その旨を書かず劇場・
  作り手だけで書いてよい。evidence には、その時期の説明の根拠になった**入力に実在する**
  劇場名・作品名・人名・題材・トーンの語を 1〜4 個入れる。
- years ── 入力にあるすべての年に、30〜70 字の 1 行を書く。**その年でいちばん大きい
  変化**を書く。件数だけを言い換えた文（「20 作品を観ました」）は書かない。
  **その年の themes・tone に語があれば、可能な年ではその内容の傾向にも触れる**
  （劇場・作り手の変化と両方は書けないときは、その年でより大きく変わったほうを選ぶ）。
- profile ── **これは年表ではなく、記録全体からこの人がどんな観客であるかの
  傾向を書く 1 つの段落**（100〜200 字）。書く材料の例 ── `n_repeated` と `n_works`
  から、同じ作品にくり返し足を運ぶ・毎回違う作品を観る、どちらの傾向が強いか。
  `verdict_tally` から、◎の割合が高い（選ぶ基準が広い・当てやすい）のか、
  △×も多い（幅広く試している）のか。`kept_venues`・`long_people` から、
  決まった劇場・作り手に忠実か、色々に散らばっているか。`overall_themes`・
  `overall_tone` から、好んで観ている内容・雰囲気。**すべてを詰め込まず、
  入力から根拠のはっきり言える 2〜3 点だけを選ぶ。** evidence には、根拠にした
  劇場名・人名・題材・トーンの語を 2〜4 個入れる。
- closing ── 全体を通した向きを 80〜160 字で書く。**通う劇場・作り手の変化に加えて、
  観る作品の内容の傾向がどう変わってきたかにも触れる。**（profile は「どんな観客か」、
  closing は「どう移り変わってきたか」であり、役割が違う）。

守ること。

- **「出会い」「出会った」という言葉は new_people に挙がっている人にだけ使う。**
  people・long_people は「よく名前が出た作り手」「何年も観ている作り手」であって、
  出会って良かったという意味ではないので、この言葉を使わない。**new_people が
  空の年・時期では、「出会い」という言葉自体を使わない**（劇場や題材の変化だけで書く）。
- **入力に無いことを書かない。** 作品名・劇場名・人名は入力に出てくる文字列だけを使う。
  「おそらく」「〜だろう」で補わない。入力から言えないことは書かない。
- **人柄を決めつけない。**「あなたは〜な人です」と断定せず、「記録からは〜という
  傾向が見えます」のように、**記録から見えることだけを書く**（profile も同じ）。
- **「ですます」で書く。** 読み手は記録の本人である。
- 数字を出すときは入力の値をそのまま使う。割合・平均を自分で計算しない。
- 演劇の一般論・作品の解説を足さない。**この人の記録の話だけを書く。**

入力:
"""


def ask(f: dict, model: str = MODEL, timeout: int = 600) -> dict:
    """LLM に読みを書かせる。**返らなかったときは空を返す**（事実の年表は出る）。"""
    # **渡すのは集計だけである。** 1 件ずつの材料（`marks`）と日記帳への鍵（`links`）は
    # 読みを書くのに要らないうえ、渡すと入力が記録そのものに近づく
    keep = ("years", "kept_venues", "left_venues", "long_people", "n_works", "n_undated",
            "overall_themes", "overall_tone", "verdict_tally", "n_repeated")
    body = json.dumps({k: f[k] for k in keep if k in f}, ensure_ascii=False)
    # **スキーマは付けない。** `years` は年をキーにした辞書（`{"2022": "…"}`）で、
    # キーが年によって変わる ── Gemini の構造化出力は決め打ちのプロパティ名を
    # 前提にしており、動的なキーには向かない。JSON モードだけ付けて、崩れた
    # 自由文が返ることは防ぎつつ、形そのものは `_check` が実データで検査する。
    try:
        got, _meta = LLM.ask(PROMPT + body, model=model, timeout=timeout)
    except (LLM.LLMError, LLM.SafetyBlocked):
        return {}
    return got if isinstance(got, dict) else {}


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
    """**記録に無い固有名を挙げた行を落とす。** 落とした数も返す（画面に出す）。

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


def write(model: str = MODEL, force: bool = False) -> dict:
    """読みを作って保存する。**記録が変わっていなければ何もしない。**"""
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app                                                      # noqa: PLC0415
    d = app._records_base()
    f = facts(d["seen"], d["rated_rows"])
    fp = fingerprint(f)
    old = load()
    if not force and old.get("fingerprint") == fp and old.get("eras"):
        return {"ok": True, "skipped": True, "line": "記録は変わっていません"}
    read, dropped = _check(ask(f, model), f)
    if not read["eras"] and not read["years"]:
        return {"ok": False, "line": "読みを作れませんでした（LLM から返りませんでした）"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {**read, "fingerprint": fp, "dropped": dropped, "model": model,
         "prompt_version": PROMPT_VERSION,
         "at": dt.date.today().isoformat()}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return {"ok": True, "line": f'年表の読みを作りました（{len(read["eras"])} 期）',
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
            f'並べていますので、<b>行の始まりと終わりが、通い始めた時期と'
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


def panel(works: list[dict], rated: list[dict]) -> str:
    """年表。**読みが無くても事実の年表は出す** ── LLM は足し算であって前提ではない。"""
    f = facts(works, rated)
    if not f["years"]:
        return ""
    read = load()
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

    profile = (f'<div class="chprofile"><h3>この記録から見えること</h3>'
              f'<p>{E(read["profile"])}</p></div>' if read.get("profile") else "")
    closing = (f'<p class="chclose">{E(read["closing"])}</p>'
               if read.get("closing") else "")
    if read.get("at"):
        # **記録が変わっているかどうかを、その場で言う。**（`specify-when-it-runs`）
        # 週次の実行では作り直さない ── 1 分かかる仕事を毎回の起動に挟むと、
        # 「数秒で一覧が開く」という週次の性質が壊れる。**押したときだけ走らせる。**
        stale = read.get("fingerprint") != fingerprint(f)
        made = (f'<p class="chnote">この年表の文（時期の名前・年ごとの 1 行・'
                f'どんな観客であるかの傾向・締めの文）は、'
                f'上に並んでいる事実だけを材料に、{E(read["at"])} に作りました。'
                + ("<b>そのあとで記録が変わっていますので、作り直せます。</b>"
                   if stale else "記録が増えたら作り直せます。")
                + (f'記録に無い名前を挙げた {read["dropped"]} 件は載せていません。'
                   if read.get("dropped") else "") + "</p>")
        btn = '<button data-chron="1">年表の文を作り直す</button>'
    else:
        made = ('<p class="chnote"><b>年表の文はまだ作っていません。</b>'
                'いまは記録から数えた事実だけが並んでいます。'
                '押すと、この事実を材料に時期の区切りと年ごとの 1 行を書きます'
                '（1 分ほどかかります）。</p>')
        btn = '<button data-chron="1">年表の文を作る</button>'
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
<div class="chfoot">{made}{btn}<span class="said"></span></div>
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
    ap.add_argument("--write", action="store_true", help="読みを作って保存する")
    ap.add_argument("--force", action="store_true", help="記録が変わっていなくても作り直す")
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    if a.write:
        r = write(a.model, a.force)
        print(r.get("line", ""))
        return 0 if r.get("ok") else 1
    import app                                                      # noqa: PLC0415
    d = app._records_base()
    print(json.dumps(facts(d["seen"], d["rated_rows"]), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
