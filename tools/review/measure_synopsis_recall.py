#!/usr/bin/env python3
"""あらすじ抽出の版を、検証 038 の正解データで前後比較する（V70）。

## なぜこの道具が要るのか

[検証 034](../../docs/verification/034-net-c-discrimination.md) は**適合率**を機械で測れるように
したが（抽出が渡した本文に実在するか）、**再現率は反例が無いので測れていなかった。**
[検証 038](../../docs/verification/038-rated-material.md) が渡した本文を 1 件ずつ読んで
**「その公演の物語が本文にあるのに抽出が空を返した 7 件」**を作ったので、ここで初めて測れる。

## 3 つの群で測る ── 再現率だけを見ると、取りすぎに気づけない

| 群 | 件数 | 正解 | 出どころ |
|---|---|---|---|
| **取りこぼし** | 7 | **空でない**（本文に物語がある） | `fail_cause="取りこぼし"` |
| **別公演を掴んだ** | 3 | **空**（当該公演の物語は本文に無い） | `wrong_join` があって抽出が非空 |
| **空が正しい** | 18 | **空**（材料なし 12・誤マッチ 6） | `fail_cause` が材料なし／誤マッチ |

**再現率を上げる変更は、同時に取りすぎを増やしうる。** 3 群を同じ実行で見ないと、
「7 件が取れた」と「別公演も取るようになった」を区別できない。

## 揺れも測る

検証 038 は「抽出は 1 回の実行の結果である」「『ダブル・トラブル』は 3 公演のうち 2 公演で取れて
1 公演だけ空 ── 材料の差ではなく抽出の揺れである」と書いている。**同じ条件を複数回まわし、
件数ではなく「何回中何回取れたか」で出す。**

    python3 tools/review/measure_synopsis_recall.py --repeat 1          # 下見
    python3 tools/review/measure_synopsis_recall.py --repeat 3
    python3 tools/review/measure_synopsis_recall.py --conditions c2/6,c4/1

**新しい取得は 1 回も発生しない**（キャッシュにあるページだけを読む）。
`data/credits/themes.jsonl` には書かない ── 確定した抽出を測定で上書きしないため。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits"))
import extract_theme_llm as E                                    # noqa: E402

TRUTH = ROOT / "docs" / "verification" / "data-038-rated-material.json"
OUT = ROOT / "docs" / "verification" / "data-042-synopsis-prompt.json"

# (群の名前, 正解は空でないか)
GROUPS = {"取りこぼし": True, "別公演を掴んだ": False, "空が正しい": False}


def ground_truth() -> dict[str, str]:
    """{作品のキー: 群の名前} を返す。"""
    rows = json.loads(TRUTH.read_text(encoding="utf-8"))
    g: dict[str, str] = {}
    for r in rows:
        if r.get("fail_cause") == "取りこぼし":
            g[r["key"]] = "取りこぼし"
        elif r.get("wrong_join") and r.get("synopsis"):
            g[r["key"]] = "別公演を掴んだ"
        elif r.get("fail_cause") in ("材料なし", "誤マッチ"):
            g[r["key"]] = "空が正しい"
    return g


def run_condition(items: list[dict], version: str, batch: int, jobs: int) -> dict[str, dict]:
    """1 条件を 1 回まわし、{キー: {"synopsis":…, "elements":…}} を返す。"""
    batches = [items[i:i + batch] for i in range(0, len(items), batch)]
    got: dict[str, dict] = {}

    def one(b: list[dict]) -> None:
        for g in E.ask(b, E.MODEL, version):
            if not isinstance(g, dict) or g.get("id") is None:
                continue
            got[str(g["id"])] = g

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(one, batches))

    out: dict[str, dict] = {}
    for r in items:
        g = got.get(str(r["id"]))
        if g is None:                       # 応答が返らなかった。**空とは区別する**
            out[r["id"]] = {"synopsis": None, "elements": []}
            continue
        syn = (g.get("synopsis") or "")[:400]
        els = [e.get("word") for e in (g.get("elements") or [])
               if isinstance(e, dict) and e.get("word")][:E.MAX_ELEMENTS.get(version, 5)]
        if syn and not E.verbatim(syn, r["text"]):      # 本文に無いものは製品と同じく落とす
            syn, els = "", []
        out[r["id"]] = {"synopsis": syn, "elements": els}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--conditions", default="c2/6,c3/6,c4/6,c4/1",
                    help="版/まとめて渡す件数 をカンマ区切りで")
    a = ap.parse_args()

    truth = ground_truth()
    rows = [r for r in E.targets("rated", fetch=False) if r["id"] in truth]
    rows = [r for r in rows if r["text"]]
    print(f"正解データ {len(truth)} 件のうち、本文が引けた {len(rows)} 件で測る")
    for name in GROUPS:
        n = sum(1 for r in rows if truth[r["id"]] == name)
        print(f"    {name}: {n} 件")
    conds = [(c.split("/")[0], int(c.split("/")[1])) for c in a.conditions.split(",")]

    # results[条件][キー] = [各回の synopsis]
    results: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    elements: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for version, batch in conds:
        label = f"{version}/{batch}"
        for i in range(a.repeat):
            print(f"■ 条件 {label} ── {i + 1}/{a.repeat} 回目", flush=True)
            got = run_condition(rows, version, batch, a.jobs)
            for k, v in got.items():
                results[label][k].append(v["synopsis"])
                elements[label][k].append(v["elements"])

    print("\n■ 群ごとの結果（分母は 件数 × 回数）")
    print(f"    {'条件':<8} {'取りこぼし→取れた':>18} {'別公演→空を保った':>18} {'空が正しい→空':>16}")
    for version, batch in conds:
        label = f"{version}/{batch}"
        cell = {}
        for name, want_text in GROUPS.items():
            ok = tot = 0
            for r in rows:
                if truth[r["id"]] != name:
                    continue
                for syn in results[label][r["id"]]:
                    if syn is None:                 # 応答なしは分母に入れない
                        continue
                    tot += 1
                    ok += 1 if bool(syn) == want_text else 0
            cell[name] = f"{ok}/{tot}" + (f" ({ok / tot * 100:.0f}%)" if tot else "")
        print(f"    {label:<8} {cell['取りこぼし']:>18} {cell['別公演を掴んだ']:>18} "
              f"{cell['空が正しい']:>16}")

    print("\n■ 1 件ずつ（取りこぼしの 7 件と、別公演を掴んだ 3 件）")
    for name in ("取りこぼし", "別公演を掴んだ"):
        print(f"  ── {name}")
        for r in rows:
            if truth[r["id"]] != name:
                continue
            line = f"     {r['title'][:30]:<32}"
            for version, batch in conds:
                got = results[f"{version}/{batch}"][r["id"]]
                # **判定の記号を使わない。** 群によって「空」が正解か外れかが逆になるので、
                # 取れたか空かだけを書く（取=非空／空=空／・=応答が返らなかった）。
                mark = "".join("・" if s is None else ("取" if s else "空") for s in got)
                line += f" {version}/{batch}:{mark}"
            print(line)

    OUT.write_text(json.dumps(
        {"conditions": [f"{v}/{b}" for v, b in conds], "repeat": a.repeat,
         "model": E.MODEL,
         "items": [{"key": r["id"], "title": r["title"], "group": truth[r["id"]],
                    "url": r["url"], "text_len": len(r["text"]),
                    "runs": {f"{v}/{b}": [{"synopsis": s, "elements": e} for s, e in
                                          zip(results[f'{v}/{b}'][r["id"]],
                                              elements[f'{v}/{b}'][r["id"]])]
                             for v, b in conds}}
                   for r in rows]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n1 件ずつの中身を {OUT.relative_to(ROOT)} に残した")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
