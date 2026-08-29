#!/usr/bin/env python3
"""網 C を「語」ではなく「グループ」で作って測る（検証 040）。

## なぜグループにするか

語のままでは突き合わせが成立していない。**学習側 96 語のうち 49 語は候補 818 件に
1 件も出てこない**（「兄弟」は学習側 4 件・候補 0 件）。起案者の指摘 ──「重なりだけじゃなくて、
その語の分析をして同じグループの語を見極める分析をすればいいのでは？」

**粒度を上下させることと、意味の近い語をまとめることは別の操作である。** まとめると
(1) 書かれ方のずれを吸収し、(2) 1 まとめあたりの標本が増える。

グループの案は `data/credits/theme_groups.json`（版 g1・LLM が作り、起案者が確定する）。
**原作（実在の作家・原作作品）はグループに入れず、網 C から外す** ── 内容ではなく名前なので、
お気に入り・名簿の側で扱うべきものである。

測るのは 3 つ。
  ① グループごとに、◎ 群と全体で出現率に差が立つか
  ② 名簿（網 B）に足して判別力が上がるか（取り直し 40 回）
  ③ 候補側で強さが付く件数（週の必要量が変わるので 検証 037 の測り直しが要る）

    python3 tools/review/net_c_groups.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_nets as M                                    # noqa: E402
import net_c as C                                           # noqa: E402

TABLE = ROOT / "data" / "credits" / "theme_groups.json"


def load_map() -> tuple[dict[str, str], set[str]]:
    t = json.loads(TABLE.read_text(encoding="utf-8"))
    return {C.nz(k): v for k, v in t["word_to_group"].items()}, {C.nz(w) for w in t["excluded"]}


W2G, EXCLUDED = load_map()


def group_words(row: dict | None) -> list[str]:
    """要素の語をグループ名に置き換えて返す。

    **申告した題材・原作者に当たる語は、グループに入れる前に落とす。** 網 C（語版）は
    lift の表から申告語を除いていた（検証 012）。グループにしたあとで除くと、
    「題材3」1 語のために「未来と題材3」ごと消えてしまうので、除くのは語の段でやる。
    """
    if not row:
        return []
    skip = {C.nz(w) for w in C.DECLARED_THEME if C.nz(w)}
    out = set()
    for e in row.get("elements", []):
        w = C.nz(e.get("word", ""))
        if not w or w in EXCLUDED:
            continue
        if any(s in w or w in s for s in skip):
            continue
        g = W2G.get(w)
        if g:
            out.add(g)
    return sorted(out)


WORD_MODE = "--words" in sys.argv     # 語版を同じ手順（漏れを直した版）で測るための比較用
if not WORD_MODE:
    C.words = group_words              # 以降 net_c の関数はすべてグループで動く
else:
    group_words = C.words              # noqa: F811（語のまま測る）


def main() -> int:
    themes = C.load_themes()
    rated = M.load_rated()
    pos = lambda v: 1.0 if v == "◎" else 0.0                # noqa: E731（検証 009）
    have = [r for r in rated if group_words(themes.get(("rated", r["key"])))]
    n_pos = sum(1 for r in have if pos(r["verdict"]))
    print(f"グループ表 版 {json.loads(TABLE.read_text(encoding='utf-8'))['version']}"
          f"／{len(set(W2G.values()))} グループ・{len(W2G)} 語")
    print(f"評価済み {len(rated)} 作品のうち、グループが付いたのは {len(have)} 作品（◎ {n_pos} 件）")

    # ① グループごとの出現率の差
    cand = [(k[1], v) for k, v in themes.items() if k[0] == "candidate"]
    cnt_c: collections.Counter = collections.Counter()
    for _, v in cand:
        for g in group_words(v):
            cnt_c[g] += 1
    lift = C.build_lift(rated, themes, pos)
    rows = []
    for g in sorted(set(W2G.values())):
        n = sum(1 for r in have if g in group_words(themes.get(("rated", r["key"]))))
        o = sum(1 for r in have if g in group_words(themes.get(("rated", r["key"])))
                and pos(r["verdict"]))
        if not n:
            rows.append((g, 0, 0, None, None, cnt_c.get(g, 0)))
            continue
        raw = o / max(n_pos, 1) - n / len(have)
        rows.append((g, n, o, raw, lift.get(g), cnt_c.get(g, 0)))
    print("\n■ ① グループごと（学習側の作品数 n・うち ◎・◎ 群と全体の出現率の差・寄与・候補側の件数）")
    for g, n, o, raw, lf, nc in sorted(rows, key=lambda r: -(r[3] if r[3] is not None else -9)):
        s_raw = f"{raw:+.3f}" if raw is not None else "  ──  "
        s_lf = f"{lf:+.4f}" if lf else "   ──   "
        print(f"   {g:<12} n={n:<3} ◎={o:<3} 差 {s_raw}  寄与 {s_lf}  候補 {nc:>4}")

    # ② 判別力（語版と同じ手順）
    pairs = []
    for i, r in enumerate(have):
        rest = have[:i] + have[i + 1:]
        lf = C.build_lift(rest, themes, pos)
        s, _ = C.strength(group_words(themes.get(("rated", r["key"]))), lf)
        pairs.append((s, bool(pos(r["verdict"]))))
    print(f"\n■ ② 網 C（グループ）だけで ◎ を当てる AUC = {M.auc(pairs)}（n={len(pairs)}）")

    pairs_b, pairs_bc = [], []
    for i, r in enumerate(have):
        rest = have[:i] + have[i + 1:]
        lf = C.build_lift(rest, themes, pos)
        rest_all = [x for x in rated if x["key"] != r["key"]]
        roster = M.build_roster(rest_all, pos)
        base = sum(float(pos(x["verdict"])) for x in rest_all) / len(rest_all)
        b = M.score(r, roster, base, by_role=True)
        c, _ = C.strength(group_words(themes.get(("rated", r["key"]))), lf)
        y = bool(pos(r["verdict"]))
        pairs_b.append((b, y)); pairs_bc.append((b + c, y))
    print(f"   同じ標本で 網 B だけ = {M.auc(pairs_b)} ／ 網 B ＋ C = {M.auc(pairs_bc)}")

    import random
    rnd = random.Random(20260821)
    diffs, cs, bs = [], [], []
    for _ in range(40):
        samp = [have[rnd.randrange(len(have))] for _ in range(len(have))]
        keys = {r["key"] for r in samp}
        if len({bool(pos(r["verdict"])) for r in samp}) < 2:
            continue
        lf = C.build_lift(samp, themes, pos)
        pb, pbc, pc = [], [], []
        for r in have:
            if r["key"] in keys:
                continue
            # **測る作品自身を名簿から外す。** net_c.py はここで rest_all（標本の外）から
            # 名簿を作っており、測る作品も標本の外なので**自分自身が名簿に入っていた**。
            # その漏れがあると網 B の AUC は 1.000 になり、足し算はどう転んでも下がる。
            rest_all = [x for x in rated if x["key"] not in keys and x["key"] != r["key"]] or rated
            roster = M.build_roster(rest_all, pos)
            base2 = sum(float(pos(x["verdict"])) for x in rest_all) / len(rest_all)
            b = M.score(r, roster, base2, by_role=True)
            c, _ = C.strength(group_words(themes.get(("rated", r["key"]))), lf)
            y = bool(pos(r["verdict"]))
            pb.append((b, y)); pbc.append((b + c, y)); pc.append((c, y))
        ab, abc, ac = M.auc(pb), M.auc(pbc), M.auc(pc)
        if None in (ab, abc, ac):
            continue
        diffs.append(abc - ab); cs.append(ac); bs.append(ab)
    if diffs:
        f = lambda xs: (sum(xs) / len(xs),                    # noqa: E731
                        (sum((x - sum(xs) / len(xs)) ** 2 for x in xs) / max(len(xs) - 1, 1)) ** 0.5)
        cm, csd = f(cs); bm, bsd = f(bs); dm, dsd = f(diffs)
        print(f"   取り直し {len(diffs)} 回 ── 網 C だけ {cm:.3f} ± {csd:.3f}"
              f"／網 B だけ {bm:.3f} ± {bsd:.3f}")
        print(f"   B+C − B の差 = {dm:+.3f} ± {dsd:.3f}"
              f"（上がった回 {sum(1 for d in diffs if d > 0)}/{len(diffs)}）")

    # ③ 候補側で強さが付く件数
    n_syn = sum(1 for _, v in cand if v.get("synopsis"))
    n_grp = sum(1 for _, v in cand if group_words(v))
    n_str = sum(1 for _, v in cand if C.strength(group_words(v), lift)[0] > 0)
    print(f"\n■ ③ 候補 {len(cand)} 件 ── あらすじが取れた {n_syn} 件／"
          f"グループが付いた {n_grp} 件／強さが正 {n_str} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
