#!/usr/bin/env python3
"""網 D（評価語の変換表）に材料があるかを、端末内のキャッシュだけで測る。

企画書 4 章の網 D は「他人のクチコミの語を自分の基準に読み替える」網である。
成立の前提は 2 つあり、どちらも件数の問題として測れる。

  D1（適用側）判定したい公演に、読めるクチコミが付いているか
  D2（学習側）変換表を作れるだけのクチコミが、評価済みの公演に付いているか
  D3（代替）  既製の集合知（クチコミの平均★）で ◎ を当てられてしまわないか

**新しく取得はしない。** すでに端末内にある CoRich の公演ページ
（`data/credits/pages/`、2026-08-20 取得）と、候補一覧・評価をそのまま数える。
取得時点が「推薦を出した時点」なので、適用側の件数はそのまま実運用の値になる。

    python3 tools/review/measure_net_d.py
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import rate_performances as R          # noqa: E402
from measure_nets import auc           # noqa: E402

PAGES = ROOT / "data" / "credits" / "pages"
CREDITS = ROOT / "data" / "credits" / "credits.jsonl"
CANDIDATES = ROOT / "data" / "review" / "candidates.jsonl"
GRADES = ["◎", "○", "△", "×"]

# 公演ページの「観てきた！」欄。件数と平均満足度がこの順で並ぶ。
_MITEKITA = re.compile(
    r'id="mitekita">.*?<span class="count">(\d+)<span>人</span>'
    r'.*?<span class="rate">([\d.]+)</span>', re.S)
_SID = re.compile(r"stage_(\d+)\.html$")


def read_pages() -> dict[str, tuple[int, float, datetime.date]]:
    """公演ページから（クチコミ件数, 平均★, 取得日）を読む。"""
    out = {}
    for f in PAGES.glob("https___stage_corich_jp_stage_*.html"):
        m0 = _SID.search(f.name)
        if not m0:
            continue
        m = _MITEKITA.search(f.read_text(encoding="utf-8", errors="replace"))
        if not m:
            continue
        out[m0.group(1)] = (int(m.group(1)), float(m.group(2)),
                            datetime.date.fromtimestamp(os.path.getmtime(f)))
    return out


def rated_works() -> list[dict]:
    """評価済みの作品に、CoRich の公演 ID を付けて返す。"""
    by_key = {}
    for line in CREDITS.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            c = json.loads(line)
            by_key[(c.get("date"), c.get("mail_title"))] = c
    purchases = R.load_purchases()
    con = R.connect()
    state = R.State("measure_d", con, purchases)
    saved = R.read_works(con)
    out = []
    for w in state.works:
        row = saved.get(w["work_key"]) or {}
        if row.get("verdict") not in GRADES:
            continue
        sids = set()
        for s in w["shows"]:
            p = state.by_uid[s["uid"]]
            c = by_key.get((p.get("date"), p.get("title")))
            if c and c.get("stage_id"):
                sids.add(c["stage_id"])
        out.append({"title": w["title_display"], "verdict": row["verdict"],
                    "sids": sorted(sids)})
    con.close()
    return out


def bucket(start: datetime.date, fetched: datetime.date) -> str:
    d = (fetched - start).days
    return "未開幕" if d < 0 else "0-2 日" if d <= 2 else "3-7 日" if d <= 7 else "8 日以上"


def main() -> int:
    pages = read_pages()
    print(f"公演ページ {len(pages)} 件（端末内のキャッシュ、取得日 "
          f"{min(v[2] for v in pages.values())}〜{max(v[2] for v in pages.values())}）\n")

    # ---- D1 適用側 ── 推薦を出した時点の候補に、クチコミが付いているか
    cands = [json.loads(l) for l in CANDIDATES.read_text(encoding="utf-8").split("\n")
             if l.strip()]
    have = [c for c in cands if c.get("stage_id") in pages]
    n1 = [c for c in have if pages[c["stage_id"]][0] >= 1]
    n3 = [c for c in have if pages[c["stage_id"]][0] >= 3]
    print(f"D1 候補 {len(have)} 件 → クチコミ 1 件以上 {len(n1)} 件 "
          f"({len(n1)/len(have):.1%})／3 件以上 {len(n3)} 件 ({len(n3)/len(have):.1%})")

    tot, h1, h3 = collections.Counter(), collections.Counter(), collections.Counter()
    for c in have:
        m = re.match(r"(\d{4})/(\d{2})/(\d{2})", c.get("period", "") or "")
        if not m:
            continue
        k = bucket(datetime.date(*map(int, m.group(1, 2, 3))), pages[c["stage_id"]][2])
        tot[k] += 1
        h1[k] += pages[c["stage_id"]][0] >= 1
        h3[k] += pages[c["stage_id"]][0] >= 3
    print("   初日からの経過日（取得時点）ごとの内訳")
    for k in ["未開幕", "0-2 日", "3-7 日", "8 日以上"]:
        if tot[k]:
            print(f"     {k:6s} {h1[k]:3d}/{tot[k]:3d} = {h1[k]/tot[k]:5.1%}"
                  f"　（3 件以上 {h3[k]}/{tot[k]}）")

    # ---- D2 学習側 ── 変換表の材料
    rated = rated_works()
    reached = [r for r in rated if r["sids"]]
    uniq = {s: pages[s] for r in reached for s in r["sids"] if s in pages}
    print(f"\nD2 評価済み {len(rated)} 作品 → 公演ページに到達 {len(reached)} 作品"
          f"（ユニークなページ {len(uniq)}）")
    print(f"   クチコミ 1 件以上 {sum(1 for v in uniq.values() if v[0] >= 1)} ページ"
          f"／3 件以上 {sum(1 for v in uniq.values() if v[0] >= 3)} ページ"
          f"／総数 {sum(v[0] for v in uniq.values())} 件")

    # ---- D3 代替 ── 平均★で ◎ を当てられるか
    rows = []
    for r in reached:
        vals = [pages[s] for s in r["sids"] if s in pages]
        if vals:
            top = max(vals, key=lambda v: v[0])
            rows.append((r["verdict"], top[0], top[1]))
    for th in (1, 3):
        sub = [x for x in rows if x[1] >= th]
        a = auc([(x[2], x[0] == "◎") for x in sub])
        print(f"\nD3 クチコミ {th} 件以上の {len(sub)} 作品"
              f"（{dict(collections.Counter(x[0] for x in sub))}）")
        print(f"   平均★で ◎ を当てる AUC {a if a is None else round(a, 3)}")
        print(f"   ★の分布 {dict(sorted(collections.Counter(x[2] for x in sub).items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
