#!/usr/bin/env python3
"""CoRich のクチコミが「公演あたり」と「人あたり」でどれだけ集まるかを実測する。

企画（#000005 / 手繰り）の前提「公演から情報を集めると足りないが、人から集めると
足りる」を、2 件の実例ではなく分布で示すために作った。標本の取り方に偏りがあるので、
その偏りが結論にどう効くかまで出力する。

## 標本の取り方

新着クチコミ一覧（`/watch/done`）から N ページ分を取り、そこに現れた
**公演**と**投稿者**をそれぞれ母集団の標本として扱う。

- **公演側は上振れする。** クチコミが 1 件も付いていない公演は一覧に現れないので、
  標本には「最低 1 件はある公演」しか入らない。**それでも少ないなら、結論は強まる**
- **投稿者側も上振れする。** 最近投稿した人ほど選ばれやすく、投稿数の多い人ほど
  最近投稿している確率が高い（長さバイアス）。**ただし本システムがたどるのは
  まさに「活動している観劇者」なので、この標本は用途と一致している**

## 使い方

    python3 tools/corich/sample_density.py --pages 5
    python3 tools/corich/sample_density.py --pages 5 --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://stage.corich.jp"
UA = "Mozilla/5.0 (compatible; kangeki-study/1.0; personal research)"
CACHE = Path.home() / ".cache" / "corich-sample"
DELAY = 1.1   # 秒。1 リクエスト/秒を超えない


def get(path: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", path).strip("_")[:120] + ".html")
    if key.exists():
        return key.read_text(encoding="utf-8", errors="replace")
    time.sleep(DELAY)
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            html = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        html = f"<!--HTTP {e.code}-->"
    except Exception as e:                      # noqa: BLE001
        html = f"<!--ERR {e}-->"
    key.write_text(html, encoding="utf-8")
    return html


def collect(pages: int) -> tuple[list[str], list[str]]:
    stages, users = [], []
    for p in range(1, pages + 1):
        html = get(f"/watch/done?page={p}&sort=create")
        stages += re.findall(r'/stage/(\d+)/done', html) + re.findall(r'href="/stage/(\d+)"', html)
        users += re.findall(r'/user/(\d+)', html)
        print(f"  一覧 {p}/{pages} 取得", file=sys.stderr, flush=True)
    return sorted(set(stages)), sorted(set(users))


def stage_review_count(sid: str) -> int | None:
    """公演ページのクチコミ件数。取れなければ None。"""
    html = get(f"/stage/{sid}/done")
    m = re.search(r'(\d+)\s*件中', html)
    if m:
        return int(m.group(1))
    if "まだクチコミはありません" in html or "クチコミはありません" in html:
        return 0
    # 「観てきた！ N人」表記を予備で見る
    m = re.search(r'観てきた[！!]\s*</?[^>]*>?\s*(\d+)\s*人', html)
    return int(m.group(1)) if m else None


def user_review_count(uid: str) -> int | None:
    """利用者の観てきた!件数。取れなければ None。"""
    html = get(f"/user/{uid}")
    m = re.search(r'/user/\d+/done_watch[^>]*>[^<]*?(\d+)', html)
    if m:
        return int(m.group(1))
    m = re.search(r'観てきた[！!][^\d]{0,40}(\d+)', html)
    return int(m.group(1)) if m else None


def describe(name: str, xs: list[int]) -> dict:
    xs = sorted(xs)
    q = statistics.quantiles(xs, n=4) if len(xs) >= 4 else [float("nan")] * 3
    d = {
        "対象": name, "標本数": len(xs),
        "中央値": statistics.median(xs) if xs else None,
        "平均": round(statistics.fmean(xs), 1) if xs else None,
        "第1四分位": q[0], "第3四分位": q[2],
        "最小": xs[0] if xs else None, "最大": xs[-1] if xs else None,
    }
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=5, help="新着一覧から取るページ数（1 ページ 20 件）")
    ap.add_argument("--limit", type=int, default=120, help="公演・利用者それぞれの上限")
    ap.add_argument("--json", help="結果を JSON で書き出す")
    a = ap.parse_args()

    print("■ 新着クチコミ一覧から標本を集めます", file=sys.stderr)
    stages, users = collect(a.pages)
    stages, users = stages[:a.limit], users[:a.limit]
    print(f"  公演 {len(stages)} 件 / 投稿者 {len(users)} 人", file=sys.stderr)

    print("■ 公演ごとのクチコミ件数", file=sys.stderr)
    sc = []
    for i, sid in enumerate(stages, 1):
        n = stage_review_count(sid)
        if n is not None:
            sc.append(n)
        if i % 20 == 0:
            print(f"  {i}/{len(stages)}", file=sys.stderr, flush=True)

    print("■ 投稿者ごとの観てきた!件数", file=sys.stderr)
    uc = []
    for i, uid in enumerate(users, 1):
        n = user_review_count(uid)
        if n is not None:
            uc.append(n)
        if i % 20 == 0:
            print(f"  {i}/{len(users)}", file=sys.stderr, flush=True)

    res = {
        "公演あたりのクチコミ件数": describe("公演", sc),
        "投稿者あたりの観てきた件数": describe("投稿者", uc),
        "公演の件数分布": {str(k): sc.count(k) for k in sorted(set(sc))[:12]},
        "投稿者が100件以上の割合": round(sum(1 for x in uc if x >= 100) / len(uc), 3) if uc else None,
        "投稿者が500件以上の割合": round(sum(1 for x in uc if x >= 500) / len(uc), 3) if uc else None,
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
