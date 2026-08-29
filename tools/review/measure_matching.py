#!/usr/bin/env python3
"""名寄せと上演日時の精度を測る（V15・V16・V38）。

  V38  購入確認メールから取った上演日時が正しいか
       ── 正解は**本文**にある。開演・開場・公演日の近くにある日付を正解とし、
          購入・入金・引取・発売の近くは捨てる
  V16  同じ作品が同じ作品として束ねられているか
       ── 題名が似ている作品の組を機械的に挙げ、別の作品に分かれていないかを見る
  V15  同じ人物が同じ人物として束ねられているか
       ── クレジットの人名で、正規化すると一致する組を挙げる

    python3 tools/review/measure_matching.py

**どれも取得はしない。** 端末内のファイルだけを読む。
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M  # noqa: E402
import rate_performances as R  # noqa: E402

BODIES = ROOT / "data" / "tickets" / "bodies"
SRC = ROOT / "data" / "tickets" / "performances.jsonl"

_DATE = re.compile(r"(\d{4})[/年\-.](\d{1,2})[/月\-.](\d{1,2})")
# 「上演日」を指す語と、指さない語。**引取・発売・入金は上演日ではない。**
NEAR = ("開演", "開場", "公演日", "上演", "観劇日", "ご来場", "来場日")
AWAY = ("申込", "購入", "入金", "決済", "発売", "受付", "予約日", "注文", "支払",
        "期限", "締切", "引取", "引き取り", "発券", "引換", "配信")


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def mail_date(r: dict) -> str:
    try:
        return parsedate_to_datetime(r["mail_date"]).date().isoformat()
    except Exception:
        return ""


def body_truth(uid: str) -> tuple[str | None, str]:
    """本文から上演日を探す。(日付, 根拠の抜粋) を返す。決められなければ (None, "")。

    **日付の直後に「開演」「開場」があれば、それで決める。** 周りに「支払」「受取」が
    あっても関係ない ── 実データでは「2025/11/8(土) 18:30開場 19:00開演」の下に
    受取方法の案内が続いており、減点で打ち消して**本物の上演日を捨てていた。**
    """
    p = BODIES / f"{uid}.txt"
    if not p.exists():
        return None, ""
    text = norm(p.read_text(encoding="utf-8", errors="replace"))
    best = None
    for m in _DATE.finditer(text):
        d = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        tail = text[m.end():m.end() + 25]
        w = text[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")
        if any(k in tail for k in ("開演", "開場")):
            score = 10          # 直後に開演・開場 ── これで決める
        else:
            score = sum(2 for k in NEAR if k in w) - sum(3 for k in AWAY if k in w)
        if score > 0 and (best is None or score > best[0]):
            best = (score, d, w[:76])
    return (best[1], best[2]) if best else (None, "")


def v38() -> None:
    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").split("\n") if l.strip()]
    dated = [r for r in rows if r.get("date")]
    agree, bad, nojudge = 0, [], 0
    for r in dated:
        t, why = body_truth(r["uid"])
        if t is None:
            nojudge += 1
            continue
        if t == r["date"]:
            agree += 1
        else:
            bad.append((r["uid"], r["date"], t, mail_date(r), norm(r.get("title"))[:24], why))
    n = agree + len(bad)
    print("■ V38 上演日時の精度 ── 正解は本文（開演・開場・公演日の近くの日付）")
    print(f"    日付つき {len(dated)} 件 / 本文から上演日を特定できた {n} 件"
          f" / 決められなかった {nojudge} 件")
    print(f"    一致 {agree} 件（{agree / n * 100:.1f}%）  食い違い {len(bad)} 件")
    print(f"    → 閾値 9 割に対して **{'成立' if agree / n >= 0.9 else '不成立'}**")
    if bad:
        print("    食い違った件（すべて）:")
        for uid, d, t, md, title, why in bad:
            flag = "  ← 記録が受信日と同じ" if d == md else ""
            print(f"      uid={uid} 記録={d} 本文={t}{flag}  {title}")
            print(f"          根拠: {why}")
    print()


def v16(state: R.State) -> None:
    """同じ作品が別の作品に分かれていないか。題名の近さで候補の組を挙げる。"""
    works = state.works
    core = {}
    for w in works:
        t = re.sub(r"[『』「」【】〈〉\[\]（）()・,，.。\s\-−–—~〜/／:：!！?？'\"“”’]", "", norm(w["title"])).lower()
        core[w["work_key"]] = t
    pairs = []
    keys = list(core)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            x, y = core[a], core[b]
            if len(x) < 3 or len(y) < 3:
                continue
            short, long_ = (x, y) if len(x) <= len(y) else (y, x)
            if short in long_ and len(short) >= 4:
                pairs.append((a, b, short, long_))
    by_key = {w["work_key"]: w for w in works}
    print("■ V16 作品の束ね方 ── 題名の一方が他方に含まれる組（同じ作品の可能性）")
    print(f"    作品 {len(works)} 件から候補の組 {len(pairs)} 件")
    for a, b, _, _ in pairs:
        wa, wb = by_key[a], by_key[b]
        same_run = (wa["first_date"] and wb["first_date"]
                    and abs(int(wa["first_date"][:4]) - int(wb["first_date"][:4])) <= 0)
        print(f"      {'★同年' if same_run else '  別年/不明'}  "
              f"{wa['first_date'] or '日付不明':<11} {wa['title_display'][:30]:<32}"
              f" ／ {wb['first_date'] or '日付不明':<11} {wb['title_display'][:30]}")
    print()


def v15(rated: list[dict]) -> None:
    """同じ人物が別人として数えられていないか。正規化で一致する組を挙げる。"""
    people = collections.Counter()
    for r in rated:
        for role, p in r["people"]:
            people[p] += 1
    def key(p: str) -> str:
        return re.sub(r"[\s　・･.,、。]", "", norm(p)).lower()
    groups = collections.defaultdict(set)
    for p in people:
        groups[key(p)].add(p)
    dups = {k: v for k, v in groups.items() if len(v) > 1}
    print("■ V15 人物名の名寄せ ── 記号と空白を落とすと一致する組")
    print(f"    ユニークな人名 {len(people)} / 一致する組 {len(dups)} 件")
    for k, v in sorted(dups.items())[:20]:
        print("      " + " ／ ".join(f"{x}({people[x]})" for x in sorted(v)))
    # 姓名の区切りだけが違う組は、名寄せしないと別人として数えられる
    n_dup_names = sum(len(v) - 1 for v in dups.values())
    print(f"    → 名寄せしないと {n_dup_names} 人ぶん余分に数える"
          f"（ユニーク人名の {n_dup_names / len(people) * 100:.1f}%）")
    print()


def main() -> int:
    argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    v38()
    pur = R.load_purchases()
    con = R.connect()
    state = R.State("measure", con, pur)
    v16(state)
    v15(M.load_rated())
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
