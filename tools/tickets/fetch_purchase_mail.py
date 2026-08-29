#!/usr/bin/env python3
"""購入確認メールを全期間から拾い、件名の書式ごとにまとめる。

## なぜ差出人で絞らないのか

[検証 004](../../docs/verification/004-purchase-mail.md) で、**発行元がチケット事業者に
集中していない**ことが実測で分かった。6 購入に対して発行元が 5 つあり、候補に並べた
事業者 12 社のうち当たったのは 1 社だけだった。劇場3主催の公演を劇場3から
買えば事業者は介在しない。**列挙では追いつかないので、件名の網で絞ってから中身を見る。**

## 3 段の 1 段目と 2 段目

    ① 件名の網（このスクリプト）      16,276 通  取りこぼし 0（正解 6/6 で実測）
    ② 購入確認かの判定（規則表）      ← --templates の出力を人が読んで作る
    ③ 公演名・日付・劇場の抽出        別スクリプト

**②を 1 通ずつではなく書式ごとに判定する。** 同じ発行元は同じ雛形でメールを出すので、
件名を正規化してまとめると数百種類に収まる。書式単位なら判断の根拠が残り、
あとから「この書式を購入確認とみなした」を検証できる。

## 出力

`data/tickets/headers.jsonl` に 1 通 1 行で置く。**リポジトリには入れない**（.gitignore 済み）。
観劇履歴は行動履歴であり嗜好の記録でもあるため、端末内にのみ置く方針に従う。

## 使い方

    python3 tools/tickets/fetch_purchase_mail.py --fetch       # 全件のヘッダを取る
    python3 tools/tickets/fetch_purchase_mail.py --templates   # 書式ごとにまとめて出す
"""

from __future__ import annotations

import argparse
import collections
import email.utils
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_ticket_mail import Gmail, _decode, _domain  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "tickets" / "headers.jsonl"

# 検証 004 で再現率 6/6 を確認した一次の網。**広めに取って取りこぼしを作らない。**
# 母数が増えても、②の判定は書式単位なので手間はほとんど変わらない。
NET_QUERY = (
    'subject:(購入 OR 申込 OR "申し込み" OR 注文 OR 予約 OR 決済 OR 引換 '
    'OR 発券 OR "抽選結果" OR 当選 OR 入金 OR 受取 OR 受付 OR チケット) '
    '-in:chats -from:me'
)


def normalize(subject: str) -> str:
    """件名を書式に潰す。公演名・数字・日付など 1 通ごとに変わる部分を伏せる。"""
    s = subject
    s = re.sub(r"[『「\"'“‘][^』」\"'”’]{1,60}[』」\"'”’]", "◯", s)
    s = re.sub(r"\d+", "#", s)
    s = re.sub(r"[A-Za-z]{4,}", "A", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:56]


def fetch(gm) -> None:
    ids = gm.ids(NET_QUERY, cap=60000)
    print(f"網にかかった: {len(ids)} 通。ヘッダを取得します…", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i in range(0, len(ids), 200):
            for r in gm.headers_many(ids[i:i + 200]):
                try:
                    dt = email.utils.parsedate_to_datetime(r["date"]).strftime("%Y-%m-%d")
                except Exception:
                    dt = ""
                f.write(json.dumps({
                    "date": dt,
                    "from": _domain(r["from"]),
                    "subject": r["subject"],
                }, ensure_ascii=False) + "\n")
                n += 1
            print(f"  {n}/{len(ids)}", end="\r", flush=True)
    print(f"\n{n} 通を {OUT} に書き出しました。")


def templates(min_count: int, since: str) -> None:
    if not OUT.exists():
        raise SystemExit(f"{OUT} がありません。先に --fetch を実行してください。")
    rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    if since:
        rows = [r for r in rows if r["date"] >= since]
    groups = collections.Counter((r["from"], normalize(r["subject"])) for r in rows)
    print(f"対象 {len(rows)} 通 / 書式 {len(groups)} 種類"
          f"{f'（{since} 以降）' if since else ''}")
    print(f"（{min_count} 通以上の書式のみ表示）")
    print("=" * 96)
    shown = 0
    for (dom, tpl), n in groups.most_common():
        if n < min_count:
            continue
        shown += n
        print(f"{n:>5}  {dom[:26]:<28} {tpl}")
    print("=" * 96)
    print(f"表示した書式で {shown} 通 / 全 {len(rows)} 通をカバー")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true", help="全期間のヘッダを取得する")
    ap.add_argument("--templates", action="store_true", help="件名を書式ごとにまとめる")
    ap.add_argument("--min-count", type=int, default=3, help="--templates で表示する下限")
    ap.add_argument("--since", default="", help="YYYY-MM-DD 以降に限る")
    a = ap.parse_args()
    if a.fetch:
        fetch(Gmail())
    elif a.templates:
        templates(a.min_count, a.since)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
