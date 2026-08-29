#!/usr/bin/env python3
"""「他人には作れない知識」という主張を、代替できる知識と並べて測る。

企画書は網 D（評価語の変換表）を「自分の中にしかなく、他人には作れない」知識として
中核に置いていたが、材料が無いことが分かった（検証 029）。**D 抜きでこの主張が立つかを、
「代わりに使える知識で同じだけ当たってしまわないか」で測る。**

比べる相手は 3 種類ある。

  ① 既製の公開指標 ── クチコミ件数・平均★・上演日数。**誰でも取れる。**
  ② 本人が言えること ── 申告した団体・人・作品。**聞けば分かる。**
  ③ 履歴の素朴な集計 ── 同じ作品を何回観たか。**評価を付けなくても分かる。**

**主張が立つのは、名簿（網 B）がこの 3 つのどれよりも当たり、かつ申告を除いても残るときだけである。**

    python3 tools/review/measure_own_knowledge.py
"""
from __future__ import annotations

import collections
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M                                     # noqa: E402
import measure_net_d as D                                    # noqa: E402
from recommend import DECLARED, EXPLAINED_BY                  # noqa: E402

CREDITS = ROOT / "data" / "credits" / "credits.jsonl"


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").lower()


# **申告から自明に導ける名前も除く。** 「劇団1（特に作り手24）」と申告していれば、
# メンバー 4 名は本人が言える名前である。除かないと残差が甘くなる。
DECLARED_PEOPLE = [nz(x) for x in DECLARED["人"]] + [
    nz(x) for x in ["作り手26", "作り手18", "作り手27", "作り手24"]]


def is_declared(person: str) -> bool:
    p = nz(person)
    return any(d and d in p for d in DECLARED_PEOPLE)


def explained(title: str) -> bool:
    t = nz(title)
    return any(nz(x) in t for x in EXPLAINED_BY)


def run_days(rows: list[dict], by_key: dict) -> dict[str, int]:
    """作品ごとの上演日数（期間の表記から）。"""
    out = {}
    for r in rows:
        f = (by_key.get(r["key"]) or {}).get("fields") or {}
        m = re.match(r"(\d{4})/(\d{2})/(\d{2}).*?～\s*(\d{4})/(\d{2})/(\d{2})", f.get("期間", "") or "")
        if m:
            a = datetime.date(*map(int, m.group(1, 2, 3)))
            b = datetime.date(*map(int, m.group(4, 5, 6)))
            out[r["key"]] = (b - a).days + 1
    return out


def show(label: str, pairs: list[tuple[float, bool]]) -> None:
    a = M.auc(pairs)
    n = len(pairs)
    pos = sum(1 for _, y in pairs if y)
    print(f"  {label:38s} AUC {('---' if a is None else format(a, '.3f'))}"
          f"　（n={n}、◎ {pos} 件）")


def main() -> int:
    rated = M.load_rated()
    pages = D.read_pages()
    # 作品 → クレジット行（期間・クチコミの突き合わせ用）
    by_key, sids = {}, {}
    for line in CREDITS.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        c = json.loads(line)
        by_key[(c.get("date"), c.get("mail_title"))] = c
    # load_rated は key に日付を持たないので、題名と日付で引き直す
    ck = {}
    for r in rated:
        for (d, t), c in by_key.items():
            if d == r["date"] and nz(t)[:12] == nz(r["title"])[:12]:
                ck[r["key"]] = c
                if c.get("stage_id"):
                    sids[r["key"]] = c["stage_id"]
                break
    days = run_days(rated, ck)
    is_top = lambda v: v == "◎"                              # noqa: E731

    print(f"評価済み {len(rated)} 作品（◎ {sum(1 for r in rated if is_top(r['verdict']))} 件）")

    print("\n① 既製の公開指標 ── 誰でも取れる")
    show("クチコミ件数（CoRich）",
         [(pages[sids[r["key"]]][0], is_top(r["verdict"]))
          for r in rated if sids.get(r["key"]) in pages])
    show("平均★（クチコミ 1 件以上）",
         [(pages[sids[r["key"]]][1], is_top(r["verdict"]))
          for r in rated if sids.get(r["key"]) in pages and pages[sids[r["key"]]][0] >= 1])
    show("上演日数（長期公演ほど上）",
         [(days[r["key"]], is_top(r["verdict"])) for r in rated if r["key"] in days])

    print("\n② 本人が言えること ── 聞けば分かる")
    show("申告に当たるか（団体・人・作品）",
         [(float(explained(r["title"])), is_top(r["verdict"])) for r in rated])

    print("\n③ 履歴の素朴な集計 ── 評価を付けなくても分かる")
    show("同じ作品を観た回数", [(r["times"], is_top(r["verdict"])) for r in rated])

    print("\n④ 網 B（作り手の名簿）── 評価と突き合わせて初めて作れる")
    a, _ = M.leave_one_out(rated, is_top, by_role=True)
    show("名簿ぜんぶ", [(0, False)] if a is None else
         M.leave_one_out(rated, is_top, by_role=True)[1])

    # 申告した名前を名簿から外す
    stripped = [dict(r, people=[(ro, p) for ro, p in r["people"] if not is_declared(p)])
                for r in rated]
    show("申告した名前を除いた名簿",
         M.leave_one_out(stripped, is_top, by_role=True)[1])

    # 申告で説明できない作品だけを当てる（名簿は全作品から作る）
    sub = [r for r in rated if not explained(r["title"])]
    print(f"\n⑤ 申告で説明できない作品だけを当てる（{len(sub)} 作品）")
    show("名簿ぜんぶ", M.leave_one_out(sub, is_top, by_role=True)[1])
    show("申告した名前を除いた名簿",
         M.leave_one_out([dict(r, people=[(ro, p) for ro, p in r["people"]
                                          if not is_declared(p)]) for r in sub],
                         is_top, by_role=True)[1])
    # ---- 同じ標本で並べる。**標本が違う AUC を比べてはいけない。**
    reach = [r for r in rated if sids.get(r["key"]) in pages]
    cnt = {r["key"]: pages[sids[r["key"]]][0] for r in reach}
    print(f"\n⑥ 同じ標本で並べる ── クチコミ件数が取れた {len(reach)} 作品")
    show("クチコミ件数", [(cnt[r["key"]], is_top(r["verdict"])) for r in reach])
    _, pairs = M.leave_one_out(rated, is_top, by_role=True)
    keyed = {r["key"]: p for r, p in zip(rated, pairs)}
    show("名簿（同じ 作品だけ採点）", [keyed[r["key"]] for r in reach])

    print("\n⑦ 人気で層に割る ── 名簿の当たりが人気の言い換えでないかを見る")
    for label, cond in (("クチコミ 0 件の作品", lambda k: cnt[k] == 0),
                        ("クチコミ 1 件以上の作品", lambda k: cnt[k] >= 1)):
        show(f"名簿 / {label}", [keyed[r["key"]] for r in reach if cond(r["key"])])

    print("\n※ ④⑤⑥⑦ は 1 件を伏せて残りから名簿を作り、その 1 件を当てる（leave-one-out）")
    print("※ 候補側ではクチコミ件数は使えない ── 818 件の 98.4% が 0 件で、並べられない（検証 029）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
