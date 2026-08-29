#!/usr/bin/env python3
"""母集団の掲載漏れを測る（V45）。

**当事者が通う劇場・製作会社の公式サイトに載っている公演**を正解データとし、
候補の母集団（CoRich・ステイジーズカレンダー）に載っているかを数える。

[検証 017](../../docs/verification/017-candidate-coverage.md) の反省を 2 つ入れてある。

1. **過去の履歴と未来の枠を比べない。** 正解データは「これから上演される公演」だけである
2. **収録期間の外を「掲載漏れ」と数えない。** カレンダーの収録期間（初日の列の範囲）より
   先の公演は「期間外」として別に数える

正解データは `data/stages/venue_upcoming.json`（公式サイトから目視で書き出したもの）。
規則で切り出すと別のものが混ざることが[検証 020](../../docs/verification/020-synopsis-extraction-quality.md)
で分かっているので、**取得は機械・書き出しは目視**にしている。

    python3 tools/stages/measure_venue_coverage.py
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRUTH = ROOT / "data" / "stages" / "venue_upcoming.json"
CORICH = ROOT / "data" / "review" / "candidates.jsonl"
SHEET = "1OtXzChuCUfy2AnyuRW5ZgnMbsKHUwlCEF9keTA0Gb8c"
CAL_URL = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid=0"

# 演劇として数える種別。企画の対象は演劇なので、コンサート・落語・お笑い・講座は分けて数える。
PLAY = ("演劇", "ミュージカル", "音楽劇")

PREFIX = re.compile(r"^(舞台|ミュージカル|音楽劇|劇団[^\s『「]*|演劇)[\s『「]*")
NOISE = re.compile(r"[『』「」【】\[\]（）()〜～ー・,、。\.\s!！?？:：/／-]+")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = PREFIX.sub("", s)
    s = NOISE.sub("", s)
    return s.lower()


def parse_date(s: str):
    s = (s or "").strip()
    for f in ("%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def load_corich() -> list[dict]:
    out = []
    for line in CORICH.open(encoding="utf-8"):
        d = json.loads(line)
        out.append(d)
    return out


def load_calendar():
    with urllib.request.urlopen(CAL_URL, timeout=60) as r:
        rows = list(csv.reader(io.StringIO(r.read().decode("utf-8"))))
    hdr = rows[1]
    col = {n: hdr.index(n) for n in ("都道府県", "劇場名", "公演団体名", "初日", "楽日")}
    data = [r for r in rows[2:] if r and r[0].strip().isdigit()]
    ent = []
    for r in data:
        ent.append({
            "theater": r[col["劇場名"]].strip(),
            "group": r[col["公演団体名"]].strip(),
            "start": parse_date(r[col["初日"]]),
            "end": parse_date(r[col["楽日"]]),
        })
    days = [e["start"] for e in ent if e["start"]]
    return ent, min(days), max(days)


def main() -> int:
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    shows = truth["公演"]
    corich = load_corich()
    cal, cal_lo, cal_hi = load_calendar()

    # 題名 → 候補（同じ作品の別会場があるので複数持つ）
    ctitles: dict[str, list[dict]] = {}
    for c in corich:
        k = norm(c.get("title") or "")
        if len(k) < 2:
            continue  # 題名が取れていない候補（"?"）は照合に使わない
        ctitles.setdefault(k, []).append(c)

    def venue_same(a: str, b: str) -> bool:
        a = unicodedata.normalize("NFKC", a or "")
        b = unicodedata.normalize("NFKC", b or "")
        if not a or not b:
            return False
        return a in b or b in a

    def find_corich(s, start, end):
        """完全一致を優先し、部分一致は劇場か期間が合うものだけ採る。"""
        key = norm(s["title"])
        cands = list(ctitles.get(key, []))
        if not cands:
            for k, lst in ctitles.items():
                if len(key) >= 4 and len(k) >= 4 and (key in k or k in key):
                    cands += lst
        if not cands:
            return None, None
        for c in cands:  # 劇場も期間も合う（当事者が行ける回）
            cs, ce = _period(c)
            if venue_same(c.get("theater", ""), s["venue"]) and cs and not (end < cs or start > ce):
                return c, "同じ会場・同じ時期"
        for c in cands:
            if venue_same(c.get("theater", ""), s["venue"]):
                return c, "同じ会場"
        for c in cands:
            cs, ce = _period(c)
            if cs and not (end < cs or start > ce):
                return c, "同じ時期・別の会場"
        return cands[0], "別の会場・別の時期（ツアーの他会場）"

    def _period(c):
        m = re.findall(r"(\d{4})/(\d{2})/(\d{2})", c.get("period", ""))
        if not m:
            return None, None
        d = [datetime.date(int(y), int(mo), int(da)) for y, mo, da in m]
        return min(d), max(d)

    print(f"正解データ {len(shows)} 件（{truth['取得日']} 時点・公式サイトから目視で書き出し）")
    print(f"CoRich 候補 {len(corich)} 件（題名が取れているもの {sum(len(v) for v in ctitles.values())} 件）"
          f" ／ カレンダー {len(cal)} 件（収録は初日 {cal_lo} 〜 {cal_hi}）\n")

    rows = []
    for s in shows:
        start, end = parse_date(s["start"]), parse_date(s["end"])
        hit_c, how = find_corich(s, start, end)
        hit_v = None
        for e in cal:
            if not e["start"] or not e["end"]:
                continue
            if venue_same(e["theater"], s["venue"]) and not (end < e["start"] or start > e["end"]):
                hit_v = e
                break
        # カレンダーと同じ弱い照合（会場と時期だけ）も出す ── 題名の列が無い相手と
        # 公平に比べるため。題名での照合より甘いので、両方を並べて読む。
        loose = any(venue_same(c.get("theater", ""), s["venue"])
                    and _period(c)[0] and not (end < _period(c)[0] or start > _period(c)[1])
                    for c in corich)
        rows.append({**s, "corich": hit_c is not None, "corich_loose": loose, "how": how,
                     "corich_title": (hit_c or {}).get("title"),
                     "corich_theater": (hit_c or {}).get("theater"),
                     "cal": hit_v is not None, "out": start > cal_hi})

    def show(sel, label):
        n = len(sel)
        if not n:
            return
        c = sum(1 for r in sel if r["corich"])
        cl = sum(1 for r in sel if r["corich_loose"])
        v = sum(1 for r in sel if r["cal"])
        b = sum(1 for r in sel if r["corich"] or r["cal"])
        print(f"{label}: {n} 件 ── CoRich 題名で {c}（{c/n:.0%}）／CoRich 会場と時期で {cl}（{cl/n:.0%}）"
              f"／カレンダー {v}（{v/n:.0%}）／どちらかに載る {b}（{b/n:.0%}）")

    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=120)  # 企画書 5 章「母集団は 4 か月先まで」
    inwin = [r for r in rows if not r["out"]]
    plays = [r for r in inwin if r["genre"] in PLAY]
    near = [r for r in rows if parse_date(r["start"]) <= horizon]
    nearplay = [r for r in near if r["genre"] in PLAY]
    print("## 全体")
    show(rows, "全 44 件")
    show(near, f"初日が 4 か月以内（〜{horizon}）")
    show(nearplay, "  うち演劇・ミュージカル・音楽劇")
    show(inwin, "カレンダーの収録期間内")
    show(plays, "  うち演劇・ミュージカル・音楽劇")
    print()

    print("## 劇場・製作会社ごと（収録期間内・演劇系のみ）")
    for src in dict.fromkeys(r["src"] for r in plays):
        show([r for r in plays if r["src"] == src], f"  {src}")
    print()

    print("## 照合の中身（目視で確かめる）")
    for r in rows:
        mark = "○" if r["corich"] else "×"
        extra = f' → {r["corich_title"]}／{r["corich_theater"]}（{r["how"]}）' if r["corich"] else ""
        print(f'  {mark} {r["title"]}（{r["venue"]}）{extra}')
    print()

    print("## どちらの母集団にも無い公演（掲載漏れの候補）")
    miss = [r for r in inwin if not r["corich"] and not r["cal"]]
    for r in miss:
        print(f"  ×  {r['title']}（{r['venue']} {r['start']}〜{r['end']}／{r['genre']}）")
    print(f"  ── {len(miss)} 件／収録期間内 {len(inwin)} 件")
    print()

    print("## 収録期間より先の公演（掲載漏れではない）")
    for r in rows:
        if r["out"]:
            print(f"  ・{r['title']}（{r['start']}〜／CoRich {'○' if r['corich'] else '×'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
