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
import time
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


# ---- 画質を落としてから入れる（起案者の指示 2026-10-14「ポスターはちょっと画質落としてから入れて。
# 過去の公演はちょっと粗めでもよい」）。画面のポスターは幅 84〜104 px（高精細の画面で 2〜3 倍）なので、
# これからの公演は幅 360 px、終わった公演は幅 240 px の WebP にする。Pillow が無ければ元のまま入れる
UPCOMING = {"width": 360, "quality": 72}
ENDED = {"width": 240, "quality": 55}


def encode(body: bytes, *, coarse: bool) -> tuple[bytes, str, str] | None:
    """(縮めた中身, 拡張子, Content-Type)。Pillow が無い・読めない画像は None（元のまま入れる）。"""
    try:
        from PIL import Image
        import io
    except ImportError:
        return None
    spec = ENDED if coarse else UPCOMING
    try:
        with Image.open(io.BytesIO(body)) as im:
            im = im.convert("RGB")
            if im.width > spec["width"]:
                im = im.resize((spec["width"], round(im.height * spec["width"] / im.width)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=spec["quality"], method=6)
        return buf.getvalue(), ".webp", "image/webp"
    except Exception:                                                # noqa: BLE001
        return None


def ended_ids(data: Path, today: str) -> set[str]:
    """会期が終わった公演の stage_id（手元の一覧 candidates.jsonl と過去の公演 past/stages.jsonl から）。"""
    import re
    out: set[str] = set()
    for rel in (Path("review") / "candidates.jsonl", Path("past") / "stages.jsonl"):
        f = data / rel
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            end = r.get("end") or ""
            if not end:
                ds = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", r.get("period") or "")
                end = f"{ds[-1][0]}-{int(ds[-1][1]):02d}-{int(ds[-1][2]):02d}" if ds else ""
            if end and end < today:
                out.add(str(r.get("stage_id") or ""))
    out.discard("")
    return out


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


def _obj_url(account: str, bucket: str, key: str) -> str:
    return (f"https://api.cloudflare.com/client/v4/accounts/{account}/r2/buckets/{bucket}/objects/"
            + urllib.parse.quote(key))


def get_object(account: str, token: str, bucket: str, key: str) -> bytes:
    req = urllib.request.Request(_obj_url(account, bucket, key), headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def delete_object(account: str, token: str, bucket: str, key: str) -> None:
    req = urllib.request.Request(_obj_url(account, bucket, key), method="DELETE",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        r.read()


# R2 の一時的な失敗（5xx・接続の切れ）は待ってやり直す。Catalog #12（2026-10-18）は HTTP 500 が 1 回出ただけで、
# その日の残り 1,800 枚ほどをまるごと見送っていた。4xx（鍵の権限・入れ物が無い）はやり直さずに止める
RETRY_WAITS = (2, 8)


def _transient(e: Exception) -> bool:
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500
    return isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError))


def build(data: Path, out: Path, *, bucket: str, limit: int, put=put_object,
          get=get_object, delete=delete_object, reshrink: int = 0, sleep=time.sleep) -> dict:
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
    import datetime as _dt
    ended = ended_ids(data, (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=9)).date().isoformat())
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
            body, key, ctype = f.read_bytes(), f.name, TYPES[f.suffix.lower()]
            small = encode(body, coarse=f.stem in ended)
            if small and len(small[0]) < len(body):
                body, key, ctype = small[0], f.stem + small[1], small[2]
            size = len(body)
            if FT.r2_bytes(u) + size > FT.CAPS["r2_bytes"]:
                stop = f"R2 の保存が上限 {FT.CAPS['r2_bytes']:,} バイトに届くので止めた（無料枠 10 GB）"
                break
            m = FT.month()
            failure = None
            for wait in (*RETRY_WAITS, None):
                u["r2"]["class_a"][m] = FT.r2_class_a(u) + 1   # 送る前に数える（やり直しも 1 回ずつ数え、少なく数えない）
                try:
                    put(account, token, bucket, key, body, ctype)
                    failure = None
                    break
                except Exception as e:                               # noqa: BLE001
                    failure = e
                    if wait is None or not _transient(e):
                        break
                    sleep(wait)
            if isinstance(failure, urllib.error.HTTPError):
                # 401/403: the token has no R2 access; 404: the bucket does not exist; 5xx: R2 kept failing.
                stop = f"R2 への書き込みを止めた（HTTP {failure.code}）。鍵に R2 の権限があるか、バケット {bucket} があるかを確かめる"
                break
            if failure is not None:
                stop = f"R2 への書き込みを止めた（{type(failure).__name__}）"
                break
            u["r2"]["sizes"][key] = size
            got[f.stem] = key
        # **すでに R2 にある大きいままのポスターを縮め直す**（2026-10-14 までに入れた 2,000 枚は、取得の
        # 機械に Pillow が無くて縮んでいなかった）。1 回に `reshrink` 枚まで: 取り出し（Class B）→ 縮める →
        # 新しい名前で入れる（Class A）→ 古いものを消す（無料の操作）。上限の手前で止まるのは上と同じ
        n_re = 0
        if not stop:
            for stem, old_key in sorted(done.items()):
                if n_re >= reshrink:
                    break
                if old_key.endswith(".webp") or stem in got:
                    continue
                if FT.r2_class_a(u) + 1 > FT.CAPS["r2_class_a_month"] or len(got) + 1 > d1_rows:
                    break
                if FT.r2_class_b(u) + 1 > FT.CAPS["r2_class_b_month"] // 10:
                    break
                m = FT.month()
                u["r2"].setdefault("class_b", {})[m] = FT.r2_class_b(u) + 1
                try:
                    body = get(account, token, bucket, old_key)
                except Exception as e:                               # noqa: BLE001
                    stop = f"R2 から読めなかったので縮め直しを止めた（{type(e).__name__}）"
                    break
                small = encode(body, coarse=stem in ended)
                if not small or len(small[0]) >= len(body):
                    continue
                new_key = stem + small[1]
                u["r2"]["class_a"][m] = FT.r2_class_a(u) + 1
                try:
                    put(account, token, bucket, new_key, small[0], small[2])
                except Exception as e:                               # noqa: BLE001
                    stop = f"縮め直したポスターを入れられなかった（{type(e).__name__}）"
                    break
                u["r2"]["sizes"][new_key] = len(small[0])
                got[stem] = new_key
                try:
                    delete(account, token, bucket, old_key)
                    u["r2"]["sizes"].pop(old_key, None)
                except Exception:                                    # noqa: BLE001
                    pass       # 消せなかった古いものは保存の数えに残す（少なく数えない）
                n_re += 1
    finally:
        FT.save(data, u)
    FT.d1_spend(data, WRITES_PER_ROW * len(got))
    if got:
        sql = _inserts("poster", "stage_id,file", sorted(got.items()))
        (out / "posters-upload.sql").write_text(
            "\n".join(s.replace("INSERT INTO", "INSERT OR REPLACE INTO", 1) for s in sql) + "\n", encoding="utf-8")
    (out / "pending.json").write_text(json.dumps({**done, **got}, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return {"uploaded": len(got) - n_re, "reshrunk": n_re, "already": len(done),
            # 残り: 手元にあって、まだ R2 に入っていないもの（入れ終えたものは作業データから外れるので、files から引かない）
            "left": sum(1 for f in files if f.suffix.lower() in TYPES and f.stem not in done and f.stem not in got), "stopped": stop,
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
    ap.add_argument("--reshrink", type=int, default=500, help="R2 にある大きいままのポスターを 1 回に縮め直す枚数")
    a = ap.parse_args()
    if a.action == "commit":
        commit(a.data, a.out)
        print("posters: delivered list saved")
        return 0
    print(json.dumps(build(a.data, a.out, bucket=a.bucket, limit=a.limit, reshrink=a.reshrink), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
