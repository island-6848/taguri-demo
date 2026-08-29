#!/usr/bin/env python3
"""「興味あり」と答えた公演を実際に観たと仮定して、次の推薦がどれだけ変わるかを測る。

## 検証 028 との違い ── 測る信号が 1 つ手前ではなく 1 つ先である

[検証 028](../../docs/verification/028-purchase-effect-on-next-week.md) は**購入**を注入して
「束は動くが中身は動かない」を出した。動くのは ◎ が付いてからで、そこは 1 件しか測っていない。
**ここで測るのは「何件か観た」の側である** ── 観劇は名簿（網 B）と要素の持ち上がり（網 C）と
基準線（r_base）の 3 つを同時に動かすので、**どれがどれだけ動かしているかを分ける。**

## 観劇は 3 つを動かす。分けて測る

| 動くもの | 何が変わるか | 分け方 |
|---|---|---|
| **基準線 r_base**（全体の ◎ 率） | 全候補のスコアが一斉に動く。**順位は変わりにくい** | クレジットを空にした行を入れる |
| **名簿（網 B）** | 観た公演の作り手が他の候補に居れば、その候補が上がる | 行にクレジットを入れる |
| **要素の持ち上がり（網 C）** | 観た公演のあらすじの要素が持ち上がる | あらすじの要素を学習側へ回す |

**網 C まで動かすのがこの版の要点である。** 検証 028 の D は名簿だけを動かしていたが、
観たのなら**その公演のあらすじも学習側に入る**（`themes.jsonl` の candidate 側の行を
rated 側の鍵で読ませる）。

## 本物の DB には 1 行も書かない

反応（`reaction`）は観劇では変わらないので**複製すらしない。** `--no-snapshot` で
`presented` にも入れない。読むだけである。

## 測る 4 つ

1. **1 件ずつ 16 通り** ── 1 本観るとどれだけ動くか。**公演によって桁が違う**ので幅で見る
2. **累積（近い順に k 件）** ── 件数を増やすと動き方が飽和するか
3. **評価の別（k=8）** ── 全部 ◎ / 実測どおり（◎ 38%）/ 1 件も ◎ が付かなかった場合
4. **分解（k=8）** ── 物差しだけ / ＋名簿 / ＋要素

    python3 tools/review/simulate_watch.py            # 人物名を出さない（既定）
    python3 tools/review/simulate_watch.py --names    # 理由の人物名も出す
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_nets as M                       # noqa: E402
import net_c as C                              # noqa: E402
import recommend2 as R                         # noqa: E402

TOP = 15            # 推薦枠の件数（比較はこの 15 件で行う）
WIDE = 400          # 全順位を書き出させるための --top（スコアが正の候補は 138 件）


# ---------------------------------------------------------------- 1 回の推薦

def run(work: Path, tag: str, *, extra_rated=(), extra_themes=()) -> dict:
    """評価済みに行を足して推薦を出し、結果を読んで返す。

    `extra_themes` は (作品の鍵, 要素の行) の列。**rated 側の鍵で入れる** ── 網 C の学習は
    `themes[("rated", key)]` しか見ないので、候補側の行のままでは持ち上がりに入らない。
    """
    out = work / f"{tag}.json"
    orig_rated, orig_themes = M.load_rated, C.load_themes
    if extra_rated:
        M.load_rated = lambda: orig_rated() + list(extra_rated)          # noqa: B023
    if extra_themes:
        C.load_themes = lambda: {**orig_themes(),                        # noqa: B023
                                 **{("rated", k): v for k, v in extra_themes}}
    try:
        sys.argv = ["recommend2", "--no-snapshot", "--top", str(WIDE), "--out", str(out)]
        R.main()
    finally:
        M.load_rated, C.load_themes = orig_rated, orig_themes
    return json.loads(out.read_text(encoding="utf-8"))


def watched_row(c: dict, verdict: str) -> dict:
    """観たと仮定した 1 件を、評価済みの行の形にする。"""
    return {"key": f"SIM-{c['stage_id']}", "title": c["title"], "date": "2026-09-01",
            "verdict": verdict, "times": 1,
            "people": sorted(set(M.parse_credits(c["fields"]))), "venues": []}


def arms(track: list[dict], verdicts: list[str], themes: dict, *,
         people: bool = True, net_c: bool = True):
    """観た k 件から、注入する (評価済みの行, 要素の行) を作る。"""
    rows, ths = [], []
    for c, v in zip(track, verdicts):
        r = watched_row(c, v)
        if not people:
            r["people"] = []
        rows.append(r)
        th = themes.get(("candidate", str(c["stage_id"])))
        if net_c and th:
            ths.append((r["key"], th))
    return rows, ths


# ---------------------------------------------------------------- 差の測り方

def spearman(a: dict, b: dict) -> float:
    """両方でスコアが付いた候補について、順位の相関。**入れ替わりの量を 1 つの数にする。**"""
    ks = [k for k in a if k in b]
    if len(ks) < 3:
        return float("nan")
    ra = {k: i for i, k in enumerate(sorted(ks, key=lambda k: -a[k]))}
    rb = {k: i for i, k in enumerate(sorted(ks, key=lambda k: -b[k]))}
    n = len(ks)
    d2 = sum((ra[k] - rb[k]) ** 2 for k in ks)
    return 1 - 6 * d2 / (n * (n * n - 1))


def scores(d: dict) -> dict[str, float]:
    return {c["title"]: c["total"] for c in d["recommend"]}


def measure(A: dict, B: dict) -> dict:
    """A（現状）と B（観たあと）の差。**推薦枠 15 件と、全順位の両方で見る。**"""
    ta = [c["title"] for c in A["recommend"][:TOP]]
    tb = [c["title"] for c in B["recommend"][:TOP]]
    sa, sb = scores(A), scores(B)
    common = [k for k in sa if k in sb]
    return {
        "in": [t for t in tb if t not in ta],
        "out": [t for t in ta if t not in tb],
        "swap": len(set(tb) - set(ta)),
        "rank": sum(1 for x, y in zip(ta, tb) if x != y),
        "moved": sum(1 for k in common if abs(sa[k] - sb[k]) > 1e-9),
        "common": len(common),
        "rho": spearman(sa, sb),
        "top1": B["recommend"][0]["total"] if B["recommend"] else 0.0,
        "n_scored": B["n_scored"],
        "nb": sum(1 for c in B["recommend"] if c["b"] > 0),
        "base": B["base"],
        "tracking": len(B["tracking"]),
        # **入った公演のうち、理由が内容の要素だけのもの。** 検証 026 で網 C 単独の 7 件は
        # 興味あり 0 件だった ── **入替が多くても、この型で埋まっているなら質は上がらない。**
        "in_c_only": sum(1 for c in B["recommend"][:TOP]
                         if c["title"] in [t for t in tb if t not in ta] and c["b"] == 0),
        # **推薦枠のうち、理由が内容の要素だけの件数。** 観る前から 13/15 がこの型である
        "c_only": sum(1 for c in B["recommend"][:TOP] if c["b"] == 0),
        # 同点の割合。上位が 1 語の lift で決まっていると同点が並ぶ
        "ties": TOP - len({round(c["total"], 4) for c in B["recommend"][:TOP]}),
    }


def line(tag: str, m: dict, ref: dict | None = None) -> str:
    d_top = "" if ref is None else f"（{ref['top1']:+.4f} → {m['top1'] - ref['top1']:+.4f}）"
    return (f"{tag:34s} 入替 {m['swap']:2d}/15(うち網C単独 {m['in_c_only']:2d})  "
            f"順位変動 {m['rank']:2d}/15  スコアが動いた {m['moved']:3d}/{m['common']:3d}  "
            f"ρ={m['rho']:+.3f}  最上位 {m['top1']:.4f}{d_top}  "
            f"網Bが理由 {m['nb']:3d}/{m['n_scored']:3d}  枠内の網C単独 {m['c_only']:2d}/15  同点 {m['ties']:2d}/15  "
            f"基準線 {m['base']:.4f}  追跡枠 {m['tracking']:2d}")


# ---------------------------------------------------------------- 本体

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # **網 C の重みを外から差せるようにする。** 並行して[検証 034](../../docs/verification/034-net-c-discrimination.md)
    # が「網 C は判別に効かない（AUC 0.551、B に足して上がった回 0/40）」を出しており、
    # **重みを 0 にするか 1 にするかで観劇の効き方が桁で変わる。** 両方を測れないと
    # 「どの程度変わるか」に一意の答えが出ない。
    ap.add_argument("--wc", type=float, default=None,
                    help="網 C の重み（既定は recommend2.py の W_C）。0 にすると網 B だけで並べる")
    ap.add_argument("--names", action="store_true",
                    help="理由の人物名も出す（推定した括りなので既定では出さない。検証 031）")
    a = ap.parse_args()
    if a.wc is not None:
        R.W_C = a.wc
    print(f"網 C の重み W_C = {R.W_C}")
    themes = C.load_themes()

    with tempfile.TemporaryDirectory(prefix="sim-watch-") as tmp:
        work = Path(tmp)
        A = run(work, "A")
        track = A["tracking"]
        base_roster = M.build_roster(M.load_rated(), lambda v: 1.0 if v == "◎" else 0.0)
        print("\n===== 現状 =====")
        print(f"推薦枠 {len(A['recommend'][:TOP])}／追いかけている {len(track)}／"
              f"スコアが正の候補 {A['n_scored']}／最上位 "
              f"{A['recommend'][0]['total']:.4f}／基準線 {A['base']:.4f}／名簿 {len(base_roster)} 件")
        rated0 = M.load_rated()
        with_th = [r for r in rated0 if themes.get(("rated", r["key"]))]
        lift0 = C.build_lift(rated0, themes, lambda v: 1.0 if v == "◎" else 0.0)
        print(f"網 C の学習側: 要素が取れている評価済み {len(with_th)} 作品"
              f"（うち ◎ {sum(1 for r in with_th if r['verdict'] == '◎')}）／語 {len(lift0)} 語")
        print("  持ち上がりの上位: "
              + "・".join(f"{w}{v:+.4f}" for w, v in sorted(lift0.items(), key=lambda x: -x[1])[:5]))

        # --- ① 1 件ずつ ---------------------------------------------------
        print("\n===== ① 1 本だけ観たと仮定する（◎ を付けた）=====")
        print("公演ごとに、そのクレジットが他の候補に何件現れるかを添える"
              " ── **重なりが無ければ順位は動かない**")
        cp = {str(c["stage_id"]): set(M.parse_credits(c["fields"]))
              for c in map(json.loads, filter(str.strip,
                                              (R.CAND).read_text(encoding="utf-8").split("\n")))}
        singles = []
        for i, c in enumerate(track):
            rows, ths = arms([c], ["◎"], themes)
            m = measure(A, run(work, f"s{i}", extra_rated=rows, extra_themes=ths))
            rb, _ = arms([c], ["◎"], themes, net_c=False)
            mb = measure(A, run(work, f"sb{i}", extra_rated=rb))
            ppl = set(M.parse_credits(c["fields"]))
            new = {p for p in ppl if p not in base_roster}
            ov = sum(1 for sid, ps in cp.items() if sid != str(c["stage_id"]) and ps & new)
            singles.append((c, m, mb, len(new), ov))
            print(f"  {i + 1:2d} {c['title'][:22]:24s} 新しい人{len(new):3d} 重なる候補{ov:4d} "
                  f"要素{'有' if themes.get(('candidate', str(c['stage_id']))) else '無'} → "
                  f"入替 名簿だけ {mb['swap']:2d}/15・要素も {m['swap']:2d}/15  "
                  f"最上位 {m['top1']:.4f}")

        sw = sorted(x[1]["swap"] for x in singles)
        swb = sorted(x[2]["swap"] for x in singles)
        print(f"\n  入替の分布（名簿だけ）: 最小 {swb[0]}／中央 {swb[len(swb) // 2]}／最大 {swb[-1]}"
              f"／0 件が {sum(1 for x in swb if x == 0)}/{len(swb)} 本")
        print(f"  入替の分布（要素も）  : 最小 {sw[0]}／中央 {sw[len(sw) // 2]}／最大 {sw[-1]}"
              f"／0 件が {sum(1 for x in sw if x == 0)}/{len(sw)} 本")

        # --- ② 累積 -------------------------------------------------------
        print("\n===== ② 近い順に k 件観たと仮定する（すべて ◎）=====")
        for k in (1, 2, 3, 5, 8, len(track)):
            rows, ths = arms(track[:k], ["◎"] * k, themes)
            m = measure(A, run(work, f"k{k}", extra_rated=rows, extra_themes=ths))
            print(line(f"k={k:2d} すべて ◎", m, None))

        # --- ③ 評価の別 ---------------------------------------------------
        K = 8
        print(f"\n===== ③ 同じ {K} 件でも、付けた評価で変わるか =====")
        # **実測どおりは ◎ 38%**（評価済み 90 作品のうち 34 件。1 件おきではなく 8 件に 3 件）
        real = ["◎" if i % 8 in (0, 3, 6) else "○" for i in range(K)]
        for name, vs in (("すべて ◎", ["◎"] * K),
                         (f"実測どおり ◎{sum(1 for v in real if v == '◎')}/{K}", real),
                         ("1 件も ◎ が付かない（全部 ○）", ["○"] * K)):
            rows, ths = arms(track[:K], vs, themes)
            m = measure(A, run(work, f"v{name[:4]}", extra_rated=rows, extra_themes=ths))
            print(line(name, m))

        # --- ④ 分解 -------------------------------------------------------
        print(f"\n===== ④ 何が動かしているのか（{K} 件・実測どおりの評価）=====")
        prev = None
        for name, kw in (("物差しだけ（クレジットも要素も入れない）",
                          dict(people=False, net_c=False)),
                         ("＋名簿（網 B）", dict(people=True, net_c=False)),
                         ("＋要素（網 C）", dict(people=True, net_c=True))):
            rows, ths = arms(track[:K], real, themes, **kw)
            B = run(work, f"d{name[:3]}", extra_rated=rows, extra_themes=ths)
            m = measure(A, B)
            print(line(name, m))
            if name.startswith("＋要素"):
                prev = B
        if prev:
            rows, ths = arms(track[:K], real, themes)
            lift1 = C.build_lift(rated0 + rows, {**themes, **{("rated", k): v for k, v in ths}},
                                 lambda v: 1.0 if v == "◎" else 0.0)
            print("\n  持ち上がりの上位（観たあと）: "
                  + "・".join(f"{w}{v:+.4f}" for w, v in sorted(lift1.items(),
                                                               key=lambda x: -x[1])[:5]))
            print(f"  語数 {len(lift0)} → {len(lift1)}／"
                  f"上位 5 語の顔ぶれが変わった数 "
                  f"{len({w for w, _ in sorted(lift1.items(), key=lambda x: -x[1])[:5]} - {w for w, _ in sorted(lift0.items(), key=lambda x: -x[1])[:5]})}/5")
            m = measure(A, prev)
            print(f"\n  推薦枠に入った: {m['in']}")
            print(f"  推薦枠から出た: {m['out']}")
            if a.names:
                for c in prev["recommend"][:TOP]:
                    print(f"    {c['total']:.4f} {c['title'][:30]:32s} "
                          f"B={c['b']} {[(p[1], p[2], p[3]) for p in c['why_b'][:3]]}")
            else:
                for c in prev["recommend"][:TOP]:
                    print(f"    {c['total']:.4f} {c['title'][:30]:32s} "
                          f"B={c['b']} 理由の役職={[p[1] for p in c['why_b'][:3]]}"
                          f" 要素={len(c['why_c'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
