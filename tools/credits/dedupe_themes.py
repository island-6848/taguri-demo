#!/usr/bin/env python3
"""`themes.jsonl` の重なった行を落とし、公演 1 件を 1 行にする。

## なぜ重なったのか

`extract_theme_llm.py` は結果を**追記**する。抽出をやり直すと、同じ公演について
**古い行と新しい行が両方残る。** 読む側は `(side, id)` で辞書に入れ直していて
**後の行が前の行を上書きする**ので、これまで害が出ていなかった。

**害が出るのは、版で絞って読むときである。** `net_c_axes.py` は
「版を 1 つに絞って読む（混ざった状態で測ると再現しない）」という作りで、
**古い版の行が残っていると、上書きされたはずの古い抽出がそのまま標本になる。**

そこで**保存の側で 1 件 1 行にする。** 落とすのは、同じ `(side, id)` の**古い行だけ**である。

    python3 tools/credits/dedupe_themes.py --dry-run    # 何を落とすかだけ見る
    python3 tools/credits/dedupe_themes.py

**控えを残す。** `data/credits/` は git の追跡外（行動履歴なので端末内にのみ置く）で、
**履歴から戻せない。** 書き換える前に `themes.jsonl.bak` を置く。
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEMES = ROOT / "data" / "credits" / "themes.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="書き換えず、落とす行を数えるだけ")
    ap.add_argument("--drop-stale-candidates", action="store_true",
                    help="いまの候補一覧に無い公演の行も落とす（下の説明を読むこと）")
    ap.add_argument("--accept-empty-newer", action="store_true",
                    help="新しい行が空でも古い行を落とす。**空が正しいと確かめた場合だけ使う**")
    a = ap.parse_args()

    rows = [json.loads(l) for l in THEMES.read_text(encoding="utf-8").split("\n") if l.strip()]

    # **後の行を残す。** 読む側（`net_c.py`）が既に「後の行が前の行を上書きする」と
    # 決めているので、**保存の側で同じ規則を使う** ── 掃除で結果が変わらないようにする。
    keep_at: dict[tuple[str, str], int] = {}
    for i, r in enumerate(rows):
        keep_at[(r["side"], str(r["id"]))] = i
    keep = set(keep_at.values())

    # **いまの候補一覧に無い行を落とす（任意）。**
    # 候補一覧は毎週作り直すので、**初日が過ぎた公演は一覧から外れる。** その行は
    # 抽出のやり直しの対象にならないので、古い版のまま残り続ける。**消費する側が無い。**
    # 落とすと、その公演が一覧に戻ったときに取り直しが 1 回発生するが、
    # **ページはキャッシュにあるので取り直せる。**
    #
    # **落とす理由は「古いから」ではない。** `--recheck` の事故
    # （[検証 042](../../docs/verification/042-synopsis-prompt.md)）で
    # **「本文に無い」という誤った理由が書かれた行が、この中に 92 件ある。**
    # 残すと、抽出の失敗として数えられる。**測っていない失敗を数字にしないために落とす。**
    if a.drop_stale_candidates:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import extract_theme_llm as E
        live = {str(r["id"]) for r in E.targets("candidate", fetch=False)}
        stale = {i for i, r in enumerate(rows)
                 if r["side"] == "candidate" and str(r["id"]) not in live}
        print(f"いまの候補一覧に無い行: {len(stale)} 件（一覧は {len(live)} 件）")
        keep -= stale

    dropped = [r for i, r in enumerate(rows) if i not in keep]
    print(f"行 {len(rows)} → {len(keep)}（落とす {len(dropped)} 行）")
    if dropped:
        c = collections.Counter(
            (r["side"], r.get("prompt_version"), bool(r["synopsis"]), r.get("reason", ""))
            for r in dropped)
        print("  落とす行の内訳（側／版／あらすじの有無／理由）:")
        for k in sorted(c, key=str):
            print(f"    {k} {c[k]} 件")

    # **落とすことであらすじが消える公演が無いことを確かめる。** 古い行にあらすじがあって
    # 新しい行が空なら、掃除が抽出結果を減らす。**その場合は落とさずに報告して止める。**
    loss = []
    for (side, sid), i in keep_at.items():
        if i not in keep:                   # 落とすと決めた行は検査しない
            continue
        newer = rows[i]
        for j, r in enumerate(rows):
            if j != i and r["side"] == side and str(r["id"]) == sid \
                    and r["synopsis"] and not newer["synopsis"]:
                loss.append((side, sid, newer["title"]))
                break
    if loss:
        print(f"\n■ 掃除であらすじが消える公演が {len(loss)} 件ある。")
        for side, sid, title in loss[:10]:
            print(f"    {side} {sid} {title[:40]}")
        if not a.accept_empty_newer:
            print("  古い行のほうにあらすじがある。どちらを採るかを決めてから掃除する。")
            print("  **空が正しいと確かめたなら --accept-empty-newer を付ける。**")
            return 1
        # **空が正しい場合がある。** c3 以降は題名を渡すので、
        # **本文にその公演の物語が無く、別公演の物語しか無い行は空になるのが正しい**
        # （[検証 042](../../docs/verification/042-synopsis-prompt.md) が
        # 『流浪樹』『CAMPだGO!』『俺たちのBANG!!!』の 3 件で、題名を渡すと
        # 9 回すべて空になることを測っている）。**古い行のあらすじは別公演のものである。**
        # 止める作りは事故を防ぐためのもので、確かめた場合の道も残す。
        print("  --accept-empty-newer が付いているので、新しい行（空）を採る。")

    if a.dry_run:
        print("\n--dry-run なので書き換えていない。")
        return 0

    bak = THEMES.with_suffix(".jsonl.bak")
    bak.write_text(THEMES.read_text(encoding="utf-8"), encoding="utf-8")
    THEMES.write_text(
        "\n".join(json.dumps(rows[i], ensure_ascii=False) for i in sorted(keep)) + "\n",
        encoding="utf-8")
    print(f"\n書き換えた。控えは {bak.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
