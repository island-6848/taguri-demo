#!/usr/bin/env python3
"""Upload posters fetched by tools/taguri/posters.py to R2, and list them in D1.

    python3 cloudflare/scripts/deliver_posters.py build --data data --out d1-posters
    npx wrangler d1 execute taguri-demo --remote --file d1-posters/posters-upload.sql
    python3 cloudflare/scripts/deliver_posters.py commit --data data --out d1-posters

起案者の指示（2026-10-13）「ポスターは R2 など別の置き場に移す（Worker にポスターを出す件と一緒に決める）」
(docs/knowledge: dec-posters-r2). The crawler's working data reached 2 GB, most of it
poster images kept in the state branch (q-crawler-state-size). Once a poster is
in R2:
- data/r2/posters.json lists it (stage_id -> file), so posters.py does not fetch
  it again and crawler_state.py leaves the local copy out of the state branch;
- the D1 table `poster` lists it, so the Worker draws it and serves /img/<file>.

`build` uploads up to --limit local files not yet listed, through the Cloudflare
REST API (PUT .../r2/buckets/<bucket>/objects/<key>, needs an API token with
"Workers R2 Storage: Edit"), and writes the SQL for the uploaded ones.
`commit` saves the list after the SQL went into D1. A token without R2 access,
or a bucket that does not exist, stops the upload with a message and changes
nothing (the step is not fatal: posters stay in the working data as before).

無料枠（起案者の指示「必ず無料の範囲内にして。絶対超えないで」、docs/free-tier-budget.md）:
R2 は無料枠を越えると請求が来る。入れる前に free_tier.py の控え（data/free_tier/usage.json）を見て、
保存の合計が CAPS["r2_bytes"]（8 GB）・今月の PUT が CAPS["r2_class_a_month"]（30 万回）・
今日の D1 の書き込みが残り（poster 表は 1 行 2 書き込み）を越えるものは入れない。PUT は送る前に数える
（失敗した PUT も数える）。1 回に入れるのは既定 2,000 枚。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from build_recommend_index import _inserts                         # noqa: E402
import free_tier as FT                                             # noqa: E402

IMG = Path("review") / "img"
MANIFEST = Path("r2") / "posters.json"
WRITES_PER_ROW = 2             # the poster row and its primary-key index entry
TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def load(data: Path) -> dict[str, str]:
    p = data / MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def put_object(account: str, token: str, bucket: str, key: str, body: bytes, ctype: str) -> None:
    url = (f"https://api.cloudflare.com/client/v4/accounts/{account}/r2/buckets/{bucket}/objects/"
           + urllib.parse.quote(key))
    req = urllib.request.Request(url, data=body, method="PUT",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=60) as r:
        r.read()


def build(data: Path, out: Path, *, bucket: str, limit: int, put=put_object) -> dict:
    account, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    done = load(data)
    files = sorted(f for f in (data / IMG).iterdir() if f.is_file()) if (data / IMG).exists() else []
    todo = [f for f in files if f.stem not in done and f.suffix.lower() in TYPES][:limit]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    got: dict[str, str] = {}
    stop = ""
    u = FT.load(data)
    d1_rows = FT.d1_left(data) // WRITES_PER_ROW
    try:
        for f in todo:
            size = f.stat().st_size
            if FT.r2_bytes(u) + size > FT.CAPS["r2_bytes"]:
                stop = f"R2 の保存が上限 {FT.CAPS['r2_bytes']:,} バイトに届くので止めた（無料枠 10 GB）"
                break
            if FT.r2_class_a(u) + 1 > FT.CAPS["r2_class_a_month"]:
                stop = f"今月の R2 の書き込みが上限 {FT.CAPS['r2_class_a_month']:,} 回に届くので止めた"
                break
            if len(got) + 1 > d1_rows:
                stop = "今日の D1 の書き込みの残りが無いので止めた（続きは明日）"
                break
            m = FT.month()
            u["r2"]["class_a"][m] = FT.r2_class_a(u) + 1       # 送る前に数える
            try:
                put(account, token, bucket, f.name, f.read_bytes(), TYPES[f.suffix.lower()])
            except urllib.error.HTTPError as e:
                # 401/403: the token has no R2 access; 404: the bucket does not exist.
                stop = f"R2 への書き込みを止めた（HTTP {e.code}）。鍵に R2 の権限があるか、バケット {bucket} があるかを確かめる"
                break
            except Exception as e:                                   # noqa: BLE001
                stop = f"R2 への書き込みを止めた（{type(e).__name__}）"
                break
            u["r2"]["sizes"][f.name] = size
            got[f.stem] = f.name
    finally:
        FT.save(data, u)
    FT.d1_spend(data, WRITES_PER_ROW * len(got))
    if got:
        sql = _inserts("poster", "stage_id,file", sorted(got.items()))
        (out / "posters-upload.sql").write_text(
            "\n".join(s.replace("INSERT INTO", "INSERT OR REPLACE INTO", 1) for s in sql) + "\n", encoding="utf-8")
    (out / "pending.json").write_text(json.dumps({**done, **got}, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return {"uploaded": len(got), "already": len(done), "left": len(files) - len(done) - len(got), "stopped": stop,
            "r2_bytes": FT.r2_bytes(u), "r2_class_a_month": FT.r2_class_a(u)}


def commit(data: Path, out: Path) -> None:
    (data / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out / "pending.json", data / MANIFEST)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["build", "commit"])
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--bucket", default=os.environ.get("TAGURI_POSTER_BUCKET", "taguri-posters"))
    ap.add_argument("--limit", type=int, default=2000)
    a = ap.parse_args()
    if a.action == "commit":
        commit(a.data, a.out)
        print("posters: delivered list saved")
        return 0
    print(json.dumps(build(a.data, a.out, bucket=a.bucket, limit=a.limit), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
