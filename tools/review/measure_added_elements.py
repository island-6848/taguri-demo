#!/usr/bin/env python3
"""要素の上限を上げ、あらすじが空でも要素を取ると、**何個増えて、増えた分は正しいか**（V71）。

## なぜこの道具が要るのか

[検証 045](../../docs/verification/045-theme-precision.md) は**いまの抽出**の適合率を 98% と測ったが、
測ったのは**上限 5 個・あらすじがある行**だけである。次の 2 つは測っていない。

| 変える点 | 増える見込み | 測っていないこと |
|---|---|---|
| **要素の上限を 5 → 8**（版 c5） | 要素がちょうど 5 個の行は 230/714（32%）。上限で切られている | **6 個目以降が正しいか** |
| **あらすじが空でも要素を取る**（版 c6） | 候補側で空の 344 件のうち、筋書きの無い催し 42%・内容の説明はある 12% | **物語の無いページから作った要素が正しいか** |

**件数だけを増やすのは意味がない。** 網 C を足すとスコアの付く候補が 29 件 → 136 件になる
（[検証 033](../../docs/verification/033-net-c-on-candidates.md)）ので、**増えた分が誤っていれば
そのまま外れが増える。** そこで増分と適合率を同じ標本で測る。

## 測り方 ── 2 つの群に、同じ本文で 3 つの版を当てる

| 群 | 標本の取り方 | 見るもの |
|---|---|---|
| **上限で切られた行** | いまの抽出で要素がちょうど 5 個の候補 | c5 で 6 個目以降が出るか、それが正しいか |
| **あらすじが空の行** | いまの抽出で `synopsis` が空・`reason` も空の候補 | c6 で要素が出るか、それが正しいか |

**両方の群に 3 版すべてを当てる。** 片方だけに当てると、**c6 が上限の効果を、c5 が空の行の効果を
持っていないこと**を確かめられない。あわせて **c6 が既にあるあらすじを壊していないか**（群 1 で
あらすじが空に転じないか）も同じ実行で見る。

**新しい取得は 1 回も発生しない**（キャッシュにあるページだけを読む）。
`data/credits/themes.jsonl` には書かない ── 確定した抽出を測定で上書きしないためである。

**1 回の実行の結果である。** 抽出には実行ごとの揺れがある（[検証 042](../../docs/verification/042-synopsis-prompt.md)）ので、
増分の件数は幅を持って読む。適合率は「出た要素が正しいか」なので揺れの影響は小さい。

    python3 tools/review/measure_added_elements.py --n 25
    python3 tools/review/measure_added_elements.py --judged docs/verification/data-048-added-elements.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits"))
import extract_theme_llm as E                                    # noqa: E402

THEMES = ROOT / "data" / "credits" / "themes.jsonl"
OUT = ROOT / "docs" / "verification" / "data-048-added-elements.json"

GROUPS = ("上限で切られた行", "あらすじが空の行")


def sample(n: int, seed: int) -> dict[str, list[str]]:
    """{群: [id]} を返す。**本文が再現できる行だけを母数にする。**"""
    rows = [json.loads(l) for l in THEMES.read_text(encoding="utf-8").split("\n") if l.strip()]
    cand = [r for r in rows if r["side"] == "candidate"]
    bodies = {t["id"]: t for t in E.targets("candidate", fetch=False) if t["text"]}
    capped = sorted({r["id"] for r in cand if len(r.get("elements") or []) >= 5
                     and r["id"] in bodies})
    empty = sorted({r["id"] for r in cand if not r["synopsis"] and not r.get("reason")
                    and r["id"] in bodies})
    rnd = random.Random(seed)
    print(f"母数 ── 上限で切られた行 {len(capped)} 件／あらすじが空の行 {len(empty)} 件"
          f"（どちらも本文が再現できるものだけ）")
    return {GROUPS[0]: rnd.sample(capped, min(n, len(capped))),
            GROUPS[1]: rnd.sample(empty, min(n, len(empty)))}


def run(items: list[dict], version: str, batch: int, jobs: int) -> dict[str, dict]:
    """1 版を 1 回まわす。**製品と同じ後始末をする**（本文に無いあらすじは落とす）。"""
    batches = [items[i:i + batch] for i in range(0, len(items), batch)]
    got: dict[str, dict] = {}

    def one(b: list[dict]) -> None:
        for g in E.ask(b, E.MODEL, version):
            if isinstance(g, dict) and g.get("id") is not None:
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
        els = [{"kind": e.get("kind", ""), "word": e["word"]}
               for e in (g.get("elements") or [])
               if isinstance(e, dict) and e.get("word")][:E.MAX_ELEMENTS.get(version, 5)]
        if syn and not E.verbatim(syn, r["text"]):
            syn, els = "", []
        out[r["id"]] = {"synopsis": syn, "elements": els}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=25, help="群ごとの標本の行数")
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--versions", default="c4,c5,c6")
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--body-limit", type=int, default=3200, help="判定票に残す本文の長さ")
    ap.add_argument("--judged", type=Path, help="判定済みの票を集計する")
    a = ap.parse_args()

    if a.judged:
        return report(a.judged)

    picked = sample(a.n, a.seed)
    bodies = {t["id"]: t for t in E.targets("candidate", fetch=False)}
    ids = [i for g in GROUPS for i in picked[g]]
    items = [bodies[i] for i in ids]
    versions = a.versions.split(",")

    runs: dict[str, dict[str, dict]] = {}
    for v in versions:
        print(f"■ 版 {v} ── {len(items)} 件（{a.batch} 件ずつ・{a.jobs} 並列）", flush=True)
        runs[v] = run(items, v, a.batch, a.jobs)

    base = versions[0]
    out = {"seed": a.seed, "n": a.n, "versions": versions, "model": E.MODEL, "rows": []}
    for g in GROUPS:
        for sid in picked[g]:
            t = bodies[sid]
            had = {e["word"] for e in runs[base][sid]["elements"]}
            row = {"群": g, "id": sid, "title": t["title"], "url": t["url"],
                   "本文の長さ": len(t["text"]), "runs": {}}
            for v in versions:
                r = runs[v][sid]
                row["runs"][v] = {
                    "synopsis": r["synopsis"],
                    "elements": [{
                        "kind": e["kind"], "word": e["word"], "位置": i,
                        # **増えた分だけを判定する。** 版をまたいで同じ語は
                        # 検証 045 が測った 98% の中身なので、ここで測り直さない
                        "増えた分": v != base and e["word"] not in had,
                        "語が本文にある": e["word"] in t["text"],
                        "判定": None,       # 正／誤／判定不能
                        "誤りの型": None,   # 別公演／本文に無い／宣伝文／粒度／上演形態
                    } for i, e in enumerate(r["elements"], 1)],
                }
            row["body"] = t["text"][:a.body_limit]
            out["rows"].append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    summarize(out)
    print(f"\n判定票を {OUT.relative_to(ROOT)} に書いた（増えた要素の「判定」を埋めてから --judged）")
    return 0


def summarize(d: dict) -> None:
    """**判定の前に、増分だけを出す。** 正しいかはまだ言えない。"""
    base = d["versions"][0]
    print(f"\n■ 増分（判定前・分母は行）")
    for g in GROUPS:
        rows = [r for r in d["rows"] if r["群"] == g]
        if not rows:
            continue
        print(f"  ── {g}（{len(rows)} 行）")
        for v in d["versions"]:
            els = sum(len(r["runs"][v]["elements"]) for r in rows)
            add = sum(1 for r in rows for e in r["runs"][v]["elements"] if e["増えた分"])
            syn = sum(1 for r in rows if r["runs"][v]["synopsis"])
            has = sum(1 for r in rows if r["runs"][v]["elements"])
            print(f"     {v}: 要素 {els:>3} 個（1 行あたり {els/len(rows):.1f}）／"
                  f"{base} に無い語 {add:>3} 個／要素が付いた行 {has:>2}／あらすじが取れた行 {syn:>2}")


def report(path: Path) -> int:
    """**判定が入っている要素だけを数える。**

    群によって判定した範囲が違うので、分母を勝手に広げない ──
    群 1 は「6 個目以降」（1〜5 個目は検証 045 が測った範囲と重なる）、
    群 2 は「c6 で増えた要素すべて」である。範囲は判定票の `判定の規準` に書いてある。
    """
    d = json.loads(path.read_text(encoding="utf-8"))
    summarize(d)
    print("\n■ 適合率（判定が入っている要素だけ・分母から判定不能を外す）")
    for g in GROUPS:
        rows = [r for r in d["rows"] if r["群"] == g]
        for v in d["versions"]:
            els = [e for r in rows for e in r["runs"][v]["elements"] if e["判定"]]
            if not els:
                continue
            ok = [e for e in els if e["判定"] == "正"]
            ng = [e for e in els if e["判定"] == "誤"]
            unk = [e for e in els if e["判定"] == "判定不能"]
            deep = sum(1 for e in els if e.get("位置", 0) >= 6)
            den = len(ok) + len(ng)
            line = f"  {g} / {v}: 判定 {len(els)} 個（うち 6 個目以降 {deep}）・判定不能 {len(unk)}"
            if den:
                line += f" → **適合率 {len(ok)}/{den} = {len(ok)/den:.1%}**"
            print(line)
            for e in ng:
                print(f"      誤: {e['kind']}「{e['word']}」── {e['誤りの型']}")
    print("\n■ あらすじを壊していないか（群 1 であらすじが空に転じた行）")
    for v in d["versions"]:
        lost = [r for r in d["rows"] if r["群"] == GROUPS[0]
                and r["runs"][d["versions"][0]]["synopsis"] and not r["runs"][v]["synopsis"]]
        print(f"  {v}: {len(lost)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
