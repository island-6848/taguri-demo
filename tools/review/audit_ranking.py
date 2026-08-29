#!/usr/bin/env python3
"""検証: recommend2.py の「並べ替え」そのものが効いているかを測る。

## 何を測るのか

[検証 035](../../docs/verification/035-scoring-constants-audit.md) は**採点の式の定数**を測った。
この検証が測るのは**その後ろの並べ替え**である ── recommend2.py は点の大きい順ではなく
`(tier, -strong, -s)` の 3 つの鍵で並べており、この 3 段のどれも、まだ一度も測っていない。

    ① 提示した順が当たっていたか  実際に答えが付いた 4 回の一覧で、rank と興味ありの一致を見る
    ② 並べ替えの鍵が当たるか      評価済み作品を 1 件伏せて、鍵の組み合わせを差し替えて測る
    ③ 順位が付いているか          いまの出力の上位 15 件が、鍵で何段に割れているか

    python3 tools/review/audit_ranking.py
"""
from __future__ import annotations

import json
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M            # noqa: E402
import net_c as C                   # noqa: E402
import recommend2 as R2             # noqa: E402

DB = ROOT / "data" / "review" / "ratings.db"
OUT2 = ROOT / "data" / "review" / "recommend2.json"


# ------------------------------------------------------------------ 汎用

def auc_key(items, key):
    """key(x) が小さいほど上位。◎ が上に来ているかを 0〜1 で返す（同点は 0.5）。"""
    pos = [key(x) for x in items if x["y"]]
    neg = [key(x) for x in items if not x["y"]]
    if not pos or not neg:
        return None
    w = sum((a < b) + 0.5 * (a == b) for a in pos for b in neg)
    return w / (len(pos) * len(neg))


# ------------------------------------------------------------------ ① 実際の反応

def part1():
    print("=" * 78)
    print("① 提示した順が当たっていたか（実際に答えが付いた一覧）")
    print("=" * 78)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = list(con.execute(
        "select p.label, p.rank, p.score, r.interest, p.title"
        " from presented p join reaction r on p.label=r.label and p.stage_id=r.stage_id"
        " where p.bundle='recommend' and r.interest is not null order by p.label, p.rank"))
    con.close()
    labels = sorted({r["label"] for r in rows})
    print(f"反応が付いた推薦枠 {len(rows)} 件／{len(labels)} 回分\n")
    print(f"{'一覧':16} {'件数':>4} {'興味あり':>6} {'順位の当たり(AUC)':>18}  上位半分／下位半分の興味あり率")
    pooled = []
    for lab in labels:
        rs = [r for r in rows if r["label"] == lab]
        items = [{"y": r["interest"] == 1, "rank": r["rank"]} for r in rs]
        a = auc_key(items, lambda x: x["rank"])
        h = len(rs) // 2
        top = [r for r in rs[:h]]
        bot = [r for r in rs[len(rs) - h:]]
        tr = sum(1 for r in top if r["interest"] == 1) / max(len(top), 1)
        br = sum(1 for r in bot if r["interest"] == 1) / max(len(bot), 1)
        print(f"{lab:16} {len(rs):>4} {sum(1 for r in rs if r['interest']==1):>6}"
              f" {('  ──' if a is None else f'{a:>18.3f}')}   {tr:.2f} / {br:.2f}")
        pooled += [(lab, r["rank"], r["interest"] == 1) for r in rs]
    # 一覧をまたいで rank を比べない（回ごとに母集団が違う）。同じ一覧の中の対だけ数える。
    def pooled_auc(sample):
        w = t = 0
        for lab in {s[0] for s in sample}:
            ps = [s[1] for s in sample if s[0] == lab and s[2]]
            ns = [s[1] for s in sample if s[0] == lab and not s[2]]
            for a in ps:
                for b in ns:
                    w += (a < b) + 0.5 * (a == b)
                    t += 1
        return w / t if t else None
    base = pooled_auc(pooled)
    rnd = random.Random(20260821)
    boots = [pooled_auc([pooled[rnd.randrange(len(pooled))] for _ in pooled])
             for _ in range(400)]
    boots = sorted(b for b in boots if b is not None)
    lo, hi = boots[int(len(boots) * .05)], boots[int(len(boots) * .95)]
    npair = sum(len([s for s in pooled if s[0] == l and s[2]])
                * len([s for s in pooled if s[0] == l and not s[2]])
                for l in {p[0] for p in pooled})
    print(f"\n同じ一覧の中の対だけで合成した AUC = {base:.3f}"
          f"（90% 区間 {lo:.3f}〜{hi:.3f}、対の数 {npair}）")
    print(f"0.5 を超えた回の割合（取り直し 400 回）= "
          f"{sum(1 for b in boots if b > 0.5) / len(boots):.0%}")
    return base


def part1b():
    """**理由の種類ごとの興味あり率。** 順位は鍵の積み上げなので、鍵の材料そのものが
    実際の答えと相関しているかを、順位を経由せずに直に見る。"""
    import collections
    print()
    print("── 反応が付いた 49 件を、理由の種類で割る（全体の興味あり率と比べる）")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = list(con.execute(
        "select p.reasons, r.interest from presented p"
        " join reaction r on p.label=r.label and p.stage_id=r.stage_id"
        " where p.bundle='recommend' and r.interest is not null"))
    con.close()
    agg = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        rs = json.loads(r["reasons"])
        st = sum(1 for x in rs.get("b") or [] if x[1] == "出演" or x[3] >= 2)
        for k in ("網 B の理由あり" if rs.get("b") else "網 B の理由なし",
                  "網 C の理由あり" if rs.get("c") else "網 C の理由なし",
                  "両方かかった（重なり）" if (rs.get("b") and rs.get("c")) else "片方だけ",
                  f"効く一致 {st} 件" if st < 2 else "効く一致 2 件以上"):
            agg[k][0] += 1
            agg[k][1] += r["interest"] == 1
    for k in sorted(agg):
        n, y = agg[k]
        print(f"  {k:22} n={n:>2}  興味あり {y:>2} = {y/n:.0%}")
    print(f"  {'（全体）':22} n={len(rows):>2}  興味あり "
          f"{sum(1 for r in rows if r['interest']==1):>2} = "
          f"{sum(1 for r in rows if r['interest']==1)/len(rows):.0%}")


# ------------------------------------------------------------------ ② 鍵の比較

def build_rows():
    """評価済み作品ごとに、1 件伏せて b・strong・c・材料の有無を出す。"""
    rated = M.load_rated()
    themes = C.load_themes()
    pos = lambda v: 1.0 if v == "◎" else 0.0            # noqa: E731（検証 009）
    out = []
    for i, r in enumerate(rated):
        rest = rated[:i] + rated[i + 1:]
        roster = M.build_roster(rest, pos)
        base = sum(pos(x["verdict"]) for x in rest) / len(rest)
        lift = C.build_lift(rest, themes, pos)
        parts = []
        for role, person in r["people"]:
            n, o = roster.get((role, person), (0, 0))
            if n == 0:
                continue
            rr = (o + M.SMOOTH_A) / (n + M.SMOOTH_B)
            w = R2.ROLE_W.get(role, R2.BACKSTAGE_W)
            c = (rr - base) * (n / (n + M.CONF_K)) * w
            if c > 0:
                parts.append((c, role, person, n))
        parts.sort(reverse=True)
        ws = C.words(themes.get(("rated", r["key"])))
        cval, _ = C.strength(ws, lift)
        out.append({
            "key": r["key"], "title": r["title"], "y": r["verdict"] == "◎",
            "b": round(sum(p[0] for p in parts[:M.TOP_N]), 4),
            "strong": sum(1 for p in parts if p[1] == "出演" or p[3] >= 2),
            "c": cval, "no_c": not ws,
        })
    return out


def add_norm(rows):
    """recommend2 と同じ正規化（母集団の 90 パーセンタイルで割って 1.5 で止める）。"""
    def p90(vals):
        v = sorted(x for x in vals if x > 0)
        return v[int(len(v) * 0.9)] if v else 1.0
    nb, nc = p90([x["b"] for x in rows]), p90([x["c"] for x in rows])
    for x in rows:
        x["bn"], x["cn"] = min(x["b"] / nb, 1.5), min(x["c"] / nc, 1.5)
        x["s"] = round(x["bn"] + x["cn"], 3)
        x["both"] = x["b"] > 0 and x["c"] > 0
        x["tier"] = 0 if (x["both"] or (x["no_c"] and x["strong"] >= 2)) else 1
    return rows, nb, nc


KEYS = {
    "現行 (重なり → 効く一致 → 正規化スコア)": lambda x: (x["tier"], -x["strong"], -x["s"]),
    "重なりを外す (効く一致 → 正規化スコア)": lambda x: (-x["strong"], -x["s"]),
    "効く一致を外す (重なり → 正規化スコア)": lambda x: (x["tier"], -x["s"]),
    "正規化スコアだけ": lambda x: (-x["s"],),
    "名簿の点だけ（検証 035 の式）": lambda x: (-x["b"],),
    "生の和 b+c（8/20 に出した順）": lambda x: (-round(x["b"] + x["c"], 4),),
    "効く一致の数だけ": lambda x: (-x["strong"],),
    "重なりだけ": lambda x: (x["tier"],),
}


def part2(rows):
    print()
    print("=" * 78)
    print("② 並べ替えの鍵が当たるか（評価済み作品、1 件伏せ）")
    print("=" * 78)
    rows, nb, nc = add_norm([dict(r) for r in rows])
    n_pos = sum(1 for r in rows if r["y"])
    print(f"標本 {len(rows)} 作品（◎ {n_pos} 件）／正規化の分母 b {nb:.4f}・c {nc:.4f}")
    print(f"重なった作品 {sum(1 for r in rows if r['both'])} 件"
          f"／あらすじが無い {sum(1 for r in rows if r['no_c'])} 件"
          f"／tier=0 {sum(1 for r in rows if r['tier']==0)} 件\n")
    cur = auc_key(rows, KEYS["現行 (重なり → 効く一致 → 正規化スコア)"])
    rnd = random.Random(20260821)
    samples = [[rows[rnd.randrange(len(rows))] for _ in rows] for _ in range(200)]
    print(f"{'並べ方':44} {'AUC':>6} {'現行との差':>9} {'現行に勝った割合':>10}")
    for name, k in KEYS.items():
        a = auc_key(rows, k)
        wins, diffs = 0, 0
        for s in samples:
            x, y = auc_key(s, k), auc_key(s, KEYS["現行 (重なり → 効く一致 → 正規化スコア)"])
            if x is None or y is None:
                continue
            diffs += 1
            wins += x > y
        print(f"{name:44} {a:>6.3f} {a-cur:>+9.3f} {wins/max(diffs,1):>10.0%}")
    return rows, cur


def part2b(rows):
    """どの鍵が実際に順位を決めているか（対の何割をその鍵が割ったか）。"""
    print()
    print("── 上位の並びを、実際に決めているのはどの鍵か（総当たりの対で数える）")
    tot = tier = strong = s = tie = 0
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            tot += 1
            if a["tier"] != b["tier"]:
                tier += 1
            elif a["strong"] != b["strong"]:
                strong += 1
            elif a["s"] != b["s"]:
                s += 1
            else:
                tie += 1
    print(f"重なりで決まった {tier/tot:.0%}／効く一致で決まった {strong/tot:.0%}"
          f"／正規化スコアで決まった {s/tot:.0%}／同点のまま {tie/tot:.0%}")


# ------------------------------------------------------------------ ③ 同点

def part3():
    print()
    print("=" * 78)
    print("③ いまの出力の上位 15 件に、順位が付いているか（V48）")
    print("=" * 78)
    d = json.loads(OUT2.read_text(encoding="utf-8"))
    rec = d["recommend"]
    print(f"{'順':>2} {'重なり':>4} {'効く一致':>6} {'正規化':>7}  題名")
    groups = {}
    for i, c in enumerate(rec, 1):
        k = (c.get("tier"), c.get("strong"), c.get("s"))
        groups.setdefault(k, []).append(i)
        print(f"{i:>2} {c.get('tier'):>4} {c.get('strong'):>6} {c.get('s'):>7.3f}"
              f"  {c.get('title','')[:38]}")
    tied = sum(len(v) for v in groups.values() if len(v) > 1)
    print(f"\n段の数 {len(groups)}／同点の中にいる件数 {tied} / {len(rec)}"
          f"（V48 の合格条件は半分未満 = {len(rec)//2} 件未満）")
    print("→ " + ("合格" if tied < len(rec) / 2 else "不成立"))


def main() -> int:
    part1()
    part1b()
    rows = build_rows()
    rows, _ = part2(rows)
    part2b(rows)
    part4(rows)
    part3()
    part5()
    return 0




# ------------------------------------------------------------------ ④ 条件を揃えて測る

def part4(rows):
    """**あらすじが取れた作品だけで測り直す。**

    評価済み 91 作品のうち**あらすじが取れているのは 31 件**で、候補側の 64% と違う。
    「重なり」の鍵は両方の網がかかったかを見るので、片方の材料が無い母集団で測ると
    鍵そのものではなく**材料の欠けを測ってしまう**。条件を揃えて確かめる。
    """
    print()
    print("=" * 78)
    print("④ あらすじが取れた作品だけで測り直す（材料の欠けを測っていないか）")
    print("=" * 78)
    sub = [r for r in rows if not r["no_c"]]
    print(f"標本 {len(sub)} 作品（◎ {sum(1 for r in sub if r['y'])} 件）"
          f"／うち重なった {sum(1 for r in sub if r['both'])} 件")
    cur = auc_key(sub, KEYS["現行 (重なり → 効く一致 → 正規化スコア)"])
    rnd = random.Random(20260821)
    samples = [[sub[rnd.randrange(len(sub))] for _ in sub] for _ in range(200)]
    print(f"\n{'並べ方':44} {'AUC':>6} {'現行との差':>9} {'現行に勝った割合':>10}")
    for name, k in KEYS.items():
        a = auc_key(sub, k)
        wins = diffs = 0
        for s in samples:
            x, y = auc_key(s, k), auc_key(s, KEYS["現行 (重なり → 効く一致 → 正規化スコア)"])
            if x is None or y is None:
                continue
            diffs += 1
            wins += x > y
        print(f"{name:44} {a:>6.3f} {a-cur:>+9.3f} {wins/max(diffs,1):>10.0%}")

    print()
    print("── 重なりの鍵が、点の高いものを下に落としている件数")
    lo = [r for r in rows if r["tier"] == 1]
    hi = [r for r in rows if r["tier"] == 0]
    bad = sum(1 for a in lo for b in hi if a["s"] > b["s"])
    tot = len(lo) * len(hi) or 1
    print(f"tier=1（下の層）が tier=0（上の層）より正規化スコアで上だった対"
          f" = {bad}/{tot} = {bad/tot:.0%}")
    print(f"tier=1 のうち効く一致 2 件以上を持つ作品 = "
          f"{sum(1 for r in lo if r['strong'] >= 2)} / {len(lo)} 件"
          f"（◎ 率 {sum(1 for r in lo if r['strong']>=2 and r['y'])/max(sum(1 for r in lo if r['strong']>=2),1):.2f}"
          f" ／全体 {sum(1 for r in rows if r['y'])/len(rows):.2f}）")

# ------------------------------------------------------------------ ⑤ 二軸で見る

def part5():
    """**順位が付くか（同点しないか）と、当たるか（AUC）は別の軸である。**

    「重なり」の鍵は精度を上げるために入れたものではなく、**1 つの網だけで上位が埋まって
    同点になるのを防ぐために**入れた（recommend2.py の並べ替えの註）。だから精度だけで
    判定してはいけない ── 同じ表で両方を並べる。
    """
    import collections
    print()
    print("=" * 78)
    print("⑤ 順位が付くか（同点）と、当たるか（AUC）を同じ表で見る")
    print("=" * 78)
    d = json.loads(OUT2.read_text(encoding="utf-8"))
    pool = d["scored_all"]
    # 本番と同じ定義（recommend2.py）。**strong の免除は「あらすじの材料が無い」ときだけ**
    tier = lambda x: 0 if (x["both"] or (x.get("no_c") and x["strong"] >= 2)) else 1  # noqa: E731
    orders = {
        "3 段 (重なり → 効く一致 → 正規化)":
            (lambda x: (tier(x), -x["strong"], -(x["s"] or 0)),
             lambda x: (tier(x), x["strong"], x["s"])),
        "2 段 (効く一致 → 正規化)":
            (lambda x: (-x["strong"], -(x["s"] or 0)), lambda x: (x["strong"], x["s"])),
        "正規化スコアだけ": (lambda x: -(x["s"] or 0), lambda x: (x["s"],)),
        "名簿の点だけ": (lambda x: -x["b"], lambda x: (round(x["b"], 4),)),
        "生の和 b+c": (lambda x: -round(x["b"] + x["c"], 4),
                    lambda x: (round(x["b"] + x["c"], 4),)),
    }
    print(f"候補 {len(pool)} 件から上位 15 件を切り出したときの同点の具合\n")
    print(f"{'並べ方':36} {'段の数':>5} {'同点の中':>7} {'V48':>6}")
    for name, (k, t) in orders.items():
        top = sorted(pool, key=k)[:15]
        g = collections.Counter(t(x) for x in top)
        tied = sum(v for v in g.values() if v > 1)
        print(f"{name:36} {len(g):>5} {tied:>5}/15 {'合格' if tied < 7.5 else '不成立':>6}")
    print("\n**同点の数は母集団で動くので、この軸では決まらない。** 3 段と 2 段の差は"
          "母集団によって入れ替わる（118 件では 6 対 2、74 件では 5 対 6）。"
          "\n**どちらも V48 には合格する。1 段目を外す根拠は、同点ではなく当たり（②④）と"
          "層の境目の誤り（④）である。**\n**同点を実際に割っているのは 2 段目（効く一致）で、"
          "これを外すと同点は 12/15 に戻る。**")


if __name__ == "__main__":
    raise SystemExit(main())
