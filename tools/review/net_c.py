#!/usr/bin/env python3
"""網 C（内容の傾向）── あらすじから抽出した要素で、強さを出して測る。

## 2 本立てにする理由

企画書 4 章の網 C は「◎ を付けた公演のあらすじに出た要素の**持ち上がり**（lift）」だが、
それだけでは**申告した題材が拾えない。** 検証 021 の指摘 4 ──「ガリレイの生涯は題材3に
当てはまると思うが、なぜ理由に無いのか」── は、申告した「題材3」を**題名と本文の文字列一致**で
探していたために起きた。題名に「題材3」の字は無い。**題材は語の一致では取れず、内容の理解でしか取れない。**

そこで網 C を 2 本に分ける。

| | 何を見るか | 学習データが要るか |
|---|---|---|
| **C-申告** | 抽出した要素が、申告した題材・原作者に当たるか | **要らない。** 最初から効く |
| **C-推定** | ◎ を付けた作品に多い要素か（lift） | 要る。**学習側であらすじが取れた分しか作れない** |

## lift の数え方

要素 e について `lift_e =（◎ 作品での出現率）−（全作品での出現率）`。
**件数が少ない要素は信頼度 `n_e / (n_e + 3)` で弱める**（網 B と同じ思想）。
公演の強さは**寄与が正の上位 3 個の和**にする（網 B の「上位 3 名の和」と揃える。
全部足すと要素をたくさん書けたページが機械的に有利になる）。

    python3 tools/review/net_c.py
"""

from __future__ import annotations

import collections
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_nets as M                                    # noqa: E402
from recommend import DECLARED                              # noqa: E402

import hand_themes as HT                                      # noqa: E402

THEMES = ROOT / "data" / "credits" / "themes.jsonl"
CONF_K = 3
TOP_N = 3
DECLARED_THEME = [w for w in DECLARED["題材"] + DECLARED["原作者"] if w]


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).replace(" ", "").replace("　", "").lower()


def load_themes() -> dict[tuple[str, str], dict]:
    if not THEMES.exists():
        return {}
    out: dict[tuple[str, str], dict] = {}
    for l in THEMES.read_text(encoding="utf-8").split("\n"):
        if not l.strip():
            continue
        r = json.loads(l)
        out[(r["side"], str(r["id"]))] = r          # 後の行が前の行を上書きする（引き直し）
    # **手で入れた内容をここで重ねる。** 読む口を 1 つにしておかないと、
    # 「画面には出るのに推薦には効かない」という食い違いが生まれる（`hand_themes`）。
    return HT.apply(out)


def words(row: dict | None) -> list[str]:
    """要素の語。**kind は落として語だけで数える** ── 同じ語が題材と舞台設定に揺れるため。"""
    if not row:
        return []
    return sorted({nz(e.get("word", "")) for e in row.get("elements", []) if e.get("word")})


def build_lift(rated: list[dict], themes: dict, positive) -> dict[str, float]:
    """語 → 寄与（(◎ での出現率 − 全体での出現率) × 信頼度）。

    **申告した題材・原作者は、この表から除く。** 申告した語で当たった公演は
    「お気に入り」へ行く（推薦には出さない）と決まっているのに、
    **同じ語が推定側の持ち上がりの表にも入っていた** ── 実測で「題材3」+0.0066、
    「作品3」+0.0066 が残っていた。起案者の指摘 ──「**そもそも「題材3、題材1、
    作品3」は申告したので推薦じゃなくて見逃したくない情報では？**」。

    **除かないと、推定の成果に申告の分が混ざる。** 企画書 4 章は「申告はスコアに足さない」
    と決めており（検証 012 で、申告を加点として混ぜると AUC が 0.744 → 0.660 に下がった）、
    **推定側の表に残すのは同じ誤りである。**
    """
    skip = {nz(w) for w in DECLARED_THEME if nz(w)}
    docs = [(words(themes.get(("rated", r["key"]))), float(positive(r["verdict"])))
            for r in rated]
    docs = [d for d in docs if d[0]]
    if not docs:
        return {}
    n_all, n_pos = len(docs), sum(1 for _, y in docs if y) or 1
    cnt_all: collections.Counter = collections.Counter()
    cnt_pos: collections.Counter = collections.Counter()
    for ws, y in docs:
        for w in ws:
            cnt_all[w] += 1
            if y:
                cnt_pos[w] += 1
    lift = {}
    for w, c in cnt_all.items():
        if any(s in nz(w) or nz(w) in s for s in skip):     # 申告した語は推定に数えない
            continue
        raw = cnt_pos[w] / n_pos - c / n_all
        lift[w] = raw * (c / (c + CONF_K))
    return lift


def rated_counts(rated: list[dict], themes: dict) -> collections.Counter:
    """語 → その語が出た評価済み作品の本数。

    **理由に本数を添えるために要る。** 網 B は「履歴 N 本」を書いているのに網 C は書いておらず、
    **3 本から出た語と 10 本から出た語が同じ顔で並んでいた** ── 検証 021 の ④ と同じ誤りである
    （n=1 の人物が同点を量産して順位が付かなかった）。実際に 2026-08-21 の推薦では
    **「サスペンス」1 語だけで 7 件が同点**になり、その語の裏づけは評価済み 3 本だった。
    """
    c: collections.Counter = collections.Counter()
    for r in rated:
        for w in words(themes.get(("rated", r["key"]))):
            c[w] += 1
    return c


def strength(ws: list[str], lift: dict[str, float]) -> tuple[float, list]:
    """(強さ, 理由に使える上位) を返す。**寄与が正の上位 3 個の和。**"""
    parts = sorted(((round(lift.get(w, 0.0), 4), w) for w in ws), reverse=True)
    parts = [p for p in parts if p[0] > 0]
    return round(sum(p[0] for p in parts[:TOP_N]), 4), parts[:TOP_N]


def declared_hits(ws: list[str], synopsis: str = "") -> list[str]:
    """申告した題材・原作者に当たった語。**要素と申告の双方向の部分一致で見る。**"""
    out = []
    for d in DECLARED_THEME:
        nd = nz(d)
        if any(nd in w or w in nd for w in ws) or (synopsis and nd in nz(synopsis)):
            out.append(d)
    return sorted(set(out))


def main() -> int:
    themes = load_themes()
    rated = M.load_rated()
    pos = lambda v: 1.0 if v == "◎" else 0.0                # noqa: E731（検証 009）
    have = [r for r in rated if words(themes.get(("rated", r["key"])))]
    print(f"評価済み {len(rated)} 作品のうち、要素が取れたのは {len(have)} 作品"
          f"（◎ は {sum(1 for r in have if pos(r['verdict']))} 件）")

    lift = build_lift(rated, themes, pos)
    top = sorted(lift.items(), key=lambda kv: -kv[1])[:15]
    print("\n■ 持ち上がりの上位（語 / 寄与）")
    for w, v in top:
        print(f"   {w:<12} {v:+.3f}")

    # 網 C だけの判別力 ── 1 件を伏せて残りから lift を作る
    pairs = []
    for i, r in enumerate(have):
        rest = have[:i] + have[i + 1:]
        lf = build_lift(rest, themes, pos)
        s, _ = strength(words(themes.get(("rated", r["key"]))), lf)
        pairs.append((s, bool(pos(r["verdict"]))))
    print(f"\n■ 網 C だけで ◎ を当てる AUC = {M.auc(pairs)}（n={len(pairs)}）")

    # **B に足すと上がるのか。** 同じ分割で B だけ／B+C を比べる（V37）
    pairs_b, pairs_bc = [], []
    for i, r in enumerate(have):
        rest = have[:i] + have[i + 1:]
        lf = build_lift(rest, themes, pos)
        rest_all = [x for x in rated if x["key"] != r["key"]]
        roster = M.build_roster(rest_all, pos)
        base = sum(float(pos(x["verdict"])) for x in rest_all) / len(rest_all)
        b = M.score(r, roster, base, by_role=True)
        c, _ = strength(words(themes.get(("rated", r["key"]))), lf)
        y = bool(pos(r["verdict"]))
        pairs_b.append((b, y))
        pairs_bc.append((b + c, y))
    print(f"   同じ標本で 網 B だけ = {M.auc(pairs_b)} ／ 網 B ＋ C = {M.auc(pairs_bc)}")

    # **単一の数字で決めない。** 検証 009・014 で「1 回の AUC を比べて逆の結論を出した」失敗が
    # あるので、標本を取り直して 40 回ぶんのばらつきを見る（同じ分割で B と B+C を比べる）。
    import random
    rnd = random.Random(20260821)
    diffs, cs = [], []
    for _ in range(40):
        samp = [have[rnd.randrange(len(have))] for _ in range(len(have))]
        keys = {r["key"] for r in samp}
        if len({bool(pos(r["verdict"])) for r in samp}) < 2:
            continue
        lf = build_lift(samp, themes, pos)
        rest_all = [x for x in rated if x["key"] not in keys] or rated
        roster = M.build_roster(rest_all, pos)
        base2 = sum(float(pos(x["verdict"])) for x in rest_all) / len(rest_all)
        pb, pbc, pc = [], [], []
        for r in have:
            if r["key"] in keys:
                continue                      # 学習に使った作品では測らない
            b = M.score(r, roster, base2, by_role=True)
            c, _ = strength(words(themes.get(("rated", r["key"]))), lf)
            y = bool(pos(r["verdict"]))
            pb.append((b, y)); pbc.append((b + c, y)); pc.append((c, y))
        ab, abc, ac = M.auc(pb), M.auc(pbc), M.auc(pc)
        if None in (ab, abc, ac):
            continue
        diffs.append(abc - ab); cs.append(ac)
    if diffs:
        mean = sum(diffs) / len(diffs)
        sd = (sum((d - mean) ** 2 for d in diffs) / max(len(diffs) - 1, 1)) ** 0.5
        cm = sum(cs) / len(cs)
        csd = (sum((c - cm) ** 2 for c in cs) / max(len(cs) - 1, 1)) ** 0.5
        print(f"\n■ 取り直し {len(diffs)} 回 ── 網 C だけ AUC = {cm:.3f} ± {csd:.3f}")
        print(f"   B+C − B の差 = {mean:+.3f} ± {sd:.3f}"
              f"（上がった回 {sum(1 for d in diffs if d > 0)}/{len(diffs)}）")

    # 候補側で何件に強さが付くか
    cand = [(k[1], v) for k, v in themes.items() if k[0] == "candidate"]
    n_syn = sum(1 for _, v in cand if v.get("synopsis"))
    n_str = sum(1 for _, v in cand if strength(words(v), lift)[0] > 0)
    n_dec = sum(1 for _, v in cand if declared_hits(words(v), v.get("synopsis", "")))
    print(f"\n■ 候補 {len(cand)} 件 ── あらすじが取れた {n_syn} 件／"
          f"C-推定で強さが付く {n_str} 件／C-申告に当たる {n_dec} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
