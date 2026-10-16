#!/usr/bin/env python3
"""Put the name index of the past stages into R2 (pastidx/v1/<shard>.json).

    python3 cloudflare/scripts/deliver_past_index.py --data data

起案者の指示（2026-10-15）「ハッシュタグ絞り込みで、過去の公演は…自動的に表示して」「明日じゃ困る。
すぐ表示できるための方法考えて」→ 案 A（docs/knowledge: dec-past-name-index）。

お気に入りのハッシュタグの画面は、名前（人・団体）から過去の公演（2019 年以降）を引く。D1 の
past_stage を毎回全部読むと 1 回で最大 2 万行になり、無料枠（1 日 500 万行）では回数を絞るしかない。
そこで、毎日の取得のときに「名前 → 公演」の対応表を作り、名前の FNV-1a で 256 個に分けて R2 に置く。
画面は名前の 1 個だけを読む（R2 の読み出し 1 回、D1 は読まない）。

- 元は data/past/stages.jsonl の全行（D1 に入れ終えたかどうかに関係なく、取れた公演はすべて）。
- 名前は出演・作り手（measure_nets.parse_credits）と団体。正規化は Worker の lists.nz と同じ
  （NFKC・半角と全角の空白を除く・小文字）。2 文字未満の名前は入れない。
- 1 個のファイル: {"v":1, "stages": {stage_id: [title, tkey, start, end, venue, group]}, "names": {name: [stage_id, ...]}}。
- 中身が前回（data/r2/pastidx.json に SHA-256 を控える）と同じファイルは送らない。
- 無料枠: R2 は越えると請求が来るので、送る前に free_tier.py の控えで保存の合計と今月の書き込み回数を
  確かめ、越えるなら止める（deliver_posters.py と同じ）。ふだんは 1 日 256 回まで。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(HERE))

import free_tier as FT                                             # noqa: E402
from deliver_past import people_of                                 # noqa: E402
import deliver_posters as DP                                       # noqa: E402
import measure_nets as M                                           # noqa: E402

SHARDS = 256
PREFIX = "pastidx/v1/"
ROWS = Path("past") / "stages.jsonl"
MANIFEST = Path("r2") / "pastidx.json"


def nz(s) -> str:
    """lists.nz in the Worker: NFKC, no half/full-width spaces, lower case."""
    return unicodedata.normalize("NFKC", str(s or "")).replace(" ", "").replace("　", "").lower()


def shard_of(name: str) -> int:
    """FNV-1a (32 bit) of the UTF-8 bytes, modulo SHARDS. lists.pastShard in the Worker is the same."""
    h = 0x811C9DC5
    for b in name.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h % SHARDS


def shards(data: Path) -> dict[int, dict]:
    text = (data / ROWS).read_text(encoding="utf-8") if (data / ROWS).exists() else ""
    out: dict[int, dict] = {}
    for line in text.split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        sid, title = str(r.get("stage_id") or ""), r.get("title") or ""
        if not sid or not title:
            continue
        names = {nz(p) for _, p in people_of(r.get("fields") or {})}
        if r.get("group"):
            names.add(nz(r["group"]))
        row = [title, M.R.title_key(title), r.get("start") or "", r.get("end") or "", r.get("theater") or "", r.get("group") or ""]
        for n in names:
            if len(n) < 2:
                continue
            s = out.setdefault(shard_of(n), {"v": 1, "stages": {}, "names": {}})
            s["stages"][sid] = row
            ids = s["names"].setdefault(n, [])
            if sid not in ids:
                ids.append(sid)
    return out


def body_of(shard: dict) -> bytes:
    return json.dumps(shard, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def deliver(data: Path, *, bucket: str, put=DP.put_object) -> dict:
    account, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    prev = json.loads((data / MANIFEST).read_text(encoding="utf-8")) if (data / MANIFEST).exists() else {}
    built = shards(data)
    u = FT.load(data)
    sent, stop = 0, ""
    done = dict(prev)
    for k in sorted(built):
        body = body_of(built[k])
        digest = hashlib.sha256(body).hexdigest()
        key = f"{PREFIX}{k:02x}.json"
        if prev.get(key) == digest:
            continue
        grow = len(body) - int(u["r2"]["sizes"].get(key, 0))
        if FT.r2_bytes(u) + max(0, grow) > FT.CAPS["r2_bytes"]:
            stop = f"R2 の保存が上限 {FT.CAPS['r2_bytes']:,} バイトに届くので止めた（無料枠 10 GB）"
            break
        if FT.r2_class_a(u) + 1 > FT.CAPS["r2_class_a_month"]:
            stop = f"今月の R2 の書き込みが上限 {FT.CAPS['r2_class_a_month']:,} 回に届くので止めた"
            break
        u["r2"]["class_a"][FT.month()] = FT.r2_class_a(u) + 1        # 送る前に数える
        try:
            put(account, token, bucket, key, body, "application/json")
        except urllib.error.HTTPError as e:
            stop = f"R2 への書き込みを止めた（HTTP {e.code}）。鍵に R2 の権限があるか、バケット {bucket} があるかを確かめる"
            break
        except Exception as e:                                       # noqa: BLE001
            stop = f"R2 への書き込みを止めた（{type(e).__name__}）"
            break
        u["r2"]["sizes"][key] = len(body)
        done[key] = digest
        sent += 1
    FT.save(data, u)
    (data / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (data / MANIFEST).write_text(json.dumps(done, sort_keys=True), encoding="utf-8")
    return {"shards": len(built), "sent": sent, "names": sum(len(s["names"]) for s in built.values()),
            "bytes": sum(len(body_of(s)) for s in built.values()), "stopped": stop}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--bucket", default=os.environ.get("TAGURI_POSTER_BUCKET", "taguri-posters"))
    a = ap.parse_args()
    print(json.dumps(deliver(a.data, bucket=a.bucket), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
