#!/usr/bin/env python3
"""「次の更新で探してほしい」と頼まれた題名を、CoRich で探して手元の控えに加える。

    python3 tools/taguri/fetch_requests.py

## なぜ要るのか ── 探しても見つからない公演

公開版は、訪問者の操作で外部サイトを検索しない（取得の量を利用者数に比例させない・
取得先への礼儀・`serve_cloud.py`）。そのため**手元のカタログに無い公演は、「探す」でも
「手で足す」でも、いくら探しても出てこなかった。** 「観ればよかった」を登録しても、
その場では演者もあらすじも調べられない。

そこで、見つからなかった題名を本人の依頼として公開サーバーに控え（`/api/search_request`。
「観ればよかった」は登録と同時に自動で控える）、**この処理が毎日の更新でまとめて探す。**
見つかった公演は `picked.jsonl`（探して拾った公演の控え）に入り、カタログに載って、
翌日から「探す」と「手で足す」の候補に出る。

## 取りすぎない

- 依頼は公開サーバーの `/api/catalog/search-requests` から、利用者 ID なしで読む
  （合言葉は `TAGURI_NAMES_TOKEN`。お気に入りの登録名と同じ口・同じ合言葉）
- **1 回に探すのは `MAX_REQUESTS` 件まで。** 依頼した人の多い題名から、控えの古い順に回す
- **同じ題名は `RETRY_DAYS` 日のあいだ探し直さない**（見つからなかった題名も控える）
- 1 つの題名につき候補は `PER_QUERY` 件まで。取得はすべて `polite_http` を通る
  （名乗り・robots.txt・1.1 秒に 1 回・断られたら引く）
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in ("tools/lib", "tools/taguri", "tools/review", "tools/credits"):
    sys.path.insert(0, str(ROOT / _p))
import polite_http as PH                                            # noqa: E402

REQUESTS_URL = os.environ.get("TAGURI_REQUESTS_URL", "")
TOKEN = os.environ.get("TAGURI_NAMES_TOKEN", "")
CACHE = ROOT / "data" / "review" / "requests_cache.json"
MAX_REQUESTS = 60
RETRY_DAYS = 7
PER_QUERY = 6


def requests_url() -> str:
    """依頼を読む URL。未設定なら、お気に入りの登録名の口と同じサーバーから作る。"""
    if REQUESTS_URL:
        return REQUESTS_URL
    names = os.environ.get("TAGURI_NAMES_URL", "")
    return names.replace("/favourite-names", "/search-requests") if names.endswith("/favourite-names") else ""


def load_requests() -> list[dict]:
    url = requests_url()
    if not (url and TOKEN):
        print("  依頼を読む先（TAGURI_NAMES_URL・TAGURI_NAMES_TOKEN）が未設定なので飛ばす")
        return []
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": PH.UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:                                          # noqa: BLE001
        print(f"  依頼を読めなかった（{type(e).__name__}）。今回は飛ばす")
        return []
    out = []
    for x in data.get("requests") or []:
        q = x.get("query")
        if isinstance(q, str) and 2 <= len(q.strip()) <= 60:
            out.append({"query": q.strip(), "users": int(x.get("users") or 1)})
    return out


def load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:                                               # noqa: BLE001
        return {}


def save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".part")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    tmp.replace(CACHE)


def choose(reqs: list[dict], cache: dict, today: datetime.date, limit: int) -> list[str]:
    """探す題名を選ぶ。**最近探した題名は飛ばし**、残りを控えの古い順・依頼の多い順に。"""
    import rate_performances as R
    fresh_cut = (today - datetime.timedelta(days=RETRY_DAYS)).isoformat()
    todo = []
    for r in reqs:
        ent = cache.get(R.title_key(r["query"]))
        if ent and ent.get("at", "") > fresh_cut:
            continue
        todo.append((ent.get("at", "") if ent else "", -r["users"], r["query"]))
    return [q for _, _, q in sorted(todo)[:limit]]


def known_ids() -> set[str]:
    out = set()
    for name in ("picked", "candidates", "calendar", "favourites"):
        f = ROOT / "data" / "review" / f"{name}.jsonl"
        if f.exists():
            out |= {str(json.loads(l).get("stage_id")) for l in
                    f.read_text(encoding="utf-8").split("\n") if l.strip()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--max", type=int, default=MAX_REQUESTS, help="1 回に探す題名の上限")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)

    import rate_performances as R
    import stage_search as SS
    reqs = load_requests()
    if not reqs:
        return 0
    cache = load_cache()
    queries = choose(reqs, cache, today, a.max)
    print(f"  依頼 {len(reqs)} 件のうち {len(queries)} 件を探す（上限 {a.max}・{RETRY_DAYS} 日以内に探した題名は飛ばす）")
    have = known_ids()
    added = 0
    for q in queries:
        r = SS.search_full(q, limit=PER_QUERY)
        new = [row for row in r["rows"] if row.get("stage_id") and str(row["stage_id"]) not in have]
        if new:
            with SS.PICKED.open("a", encoding="utf-8") as f:
                for row in new:
                    row["source"] = "頼まれて探した"
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    have.add(str(row["stage_id"]))
            added += len(new)
        # **見つからなかった題名も控える**（毎日同じ題名を探し直さない）。失敗した回は控えない
        if not r.get("error"):
            cache[R.title_key(q)] = {"at": today.isoformat(), "found": len(r["rows"]), "added": len(new)}
    save_cache(cache)
    print(f"  手元の控えに {added} 件を加えた（picked.jsonl）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
