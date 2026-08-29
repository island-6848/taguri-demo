#!/usr/bin/env python3
"""当事者が通う劇場での候補公演だけを取り、名簿との一致率を測る（V30b の切り分け）。

[検証 017](../../docs/verification/017-candidate-coverage.md) で、**無作為に抜いた候補
60 件では網 B の強さが 0 になるものが 95%** だった。その原因が
**母集団の偏り**（候補のうち当事者が通う劇場の公演は 5.5% しかない）なのか、
**名簿と候補の人的な重なりが薄いこと**なのかを分けるために、
**当事者が通う劇場の公演だけ**を取って同じ測り方をする。

    python3 tools/credits/fetch_home_venues.py --run
    python3 tools/credits/fetch_home_venues.py --report

取得は 1 リクエスト/秒以下（`fetch_upcoming_credits.py` の `get` を再利用する）。
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import fetch_upcoming_credits as U  # noqa: E402
import measure_nets as M  # noqa: E402

OUT = ROOT / "data" / "credits" / "home_venues.jsonl"

# 当事者が実際に観た首都圏の劇場（評価済み 91 作品の劇場から、首都圏で営業中のもの）。
# **休館中の帝国劇場と、圏外（関西・九州）は入れない** ── どちらもカレンダーに
# 載らない理由が別にあり、混ぜると測りたいことが測れない（検証 017 の反省）。
HOME = ("劇場3", "吉祥寺シアター", "本多劇場", "日生劇場", "シアタークリエ",
        "明治座", "三越劇場", "劇場2", "東京芸術劇場",
        "紀伊國屋", "下北沢", "座・高円寺", "劇団4")


def pick(today: str) -> list[dict]:
    rows = U.load(datetime.date.fromisoformat(today))
    return [r for r in rows if any(h in r["venue"] for h in HOME)]


def run(today: str) -> None:
    rows = pick(today)
    print(f"当事者が通う劇場での候補 {len(rows)} 件を取ります（1 リクエスト/秒以下）…",
          flush=True)
    out = []
    for n, r in enumerate(rows, 1):
        html, err = U.get(r["url"])
        got = U.roles_in(U.to_text(html)) if html else {}
        out.append({**r, "error": err, "roles": got,
                    "text_len": len(U.to_text(html)) if html else 0})
        print(f"  {n}/{len(rows)}", end="\r", flush=True)
    OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out),
                   encoding="utf-8")
    print()
    report()


def people_of(r: dict) -> list[tuple[str, str]]:
    out = []
    for role, txt in (r.get("roles") or {}).items():
        for n in M._names(txt):
            out.append((M.canon_role(role), n))
    return sorted(set(out))


def measure(rows: list[dict], label: str) -> None:
    rated = [r for r in M.load_rated() if r["people"]]
    pos = (lambda v: v == "◎")
    roster = M.build_roster(rated, pos)
    base = sum(1 for r in rated if pos(r["verdict"])) / len(rated)
    t = collections.Counter()
    scored = []
    for r in rows:
        ppl = people_of(r)
        hit = [k for k in ppl if roster.get(k, (0, 0))[0] > 0]
        s = M.score({"people": ppl}, roster, base, by_role=True)
        scored.append((r, ppl, hit, s))
        if not ppl:
            t["① クレジットが取れない"] += 1
        elif not hit:
            t["② 取れたが名簿に 1 人も一致しない"] += 1
        elif s <= 0:
            t["③ 一致したが寄与が正にならない"] += 1
        else:
            t["④ 網 B で順位が付く"] += 1
    n = len(rows)
    print(f"■ {label}（{n} 件）")
    for k in sorted(t):
        print(f"    {k:<28} {t[k]:>3}  {t[k] / n * 100:>3.0f}%")
    print(f"    網 B で順位が付く: {t['④ 網 B で順位が付く']}/{n} = "
          f"{t['④ 網 B で順位が付く'] / n * 100:.0f}%")
    for r, ppl, hit, s in sorted(scored, key=lambda x: -x[3])[:8]:
        if s <= 0:
            break
        print(f"      寄与 {s:.3f}  {r['venue'][:20]:<22} {r['troupe'][:22]:<24}"
              f" 一致 {len(hit)}/{len(ppl)} 人")
    print()


def report() -> None:
    if not OUT.exists():
        raise SystemExit(f"{OUT} がありません。--run を先に実行してください。")
    home = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    up = ROOT / "data" / "credits" / "upcoming.jsonl"
    rand = [json.loads(l) for l in up.read_text(encoding="utf-8").split("\n") if l.strip()]
    measure(rand, "無作為に等間隔で抜いた候補（比較のため）")
    measure(home, "当事者が通う劇場での候補")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--today", default="2026-08-20")
    a = ap.parse_args()
    if a.run:
        run(a.today)
    elif a.report:
        report()
    else:
        rows = pick(a.today)
        print(f"当事者が通う劇場での候補 {len(rows)} 件（--run で取得）")
        for k, v in collections.Counter(r["venue"] for r in rows).most_common(14):
            print(f"   {v:>3}  {k[:34]}")


if __name__ == "__main__":
    main()
