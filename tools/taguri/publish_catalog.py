#!/usr/bin/env python3
"""公演カタログを取り直して、公開サーバーが読む S3 に載せ直す（定期実行用）。

    python3 tools/taguri/publish_catalog.py --mode daily     # 毎日：一覧・お気に入り・カレンダー
    python3 tools/taguri/publish_catalog.py --mode weekly    # 週 1：候補とクレジット・あらすじも取り直す
    python3 tools/taguri/publish_catalog.py --no-update --dry-run   # 取らずに、まとめて検査だけ

## なぜ要るのか

公開サーバー（`serve_cloud.py`）は、公演カタログを**自分では取りに行かない**。訪問者の
操作で外部サイトへの取得や LLM が走らないようにするためで、カタログは事前に作って
非公開の S3 に置き、起動時に読むだけである。**ところが、作り直す仕組みが無かった**
（最初に 1 回、手で作ったきり）。そのままでは新しく発表された公演が出ず、終わった公演が
増えていく ──「初報から初日までに気づかせる」という目的に直接響く。

## すること

1. 取り直す（`run.py --no-open`。週 1 のときは `--fetch` も付ける）。取得はすべて
   `tools/lib/polite_http.py` を通るので、名乗り・robots.txt・間隔の作法が守られる
2. 公開してよいファイルだけを tar.gz にまとめる（下の「載せないもの」）
3. **壊れたカタログを載せない検査**をする ── これから観られる候補が少なすぎる・前回より
   大きく減った・載せてはいけないファイルが混じった、のどれかなら載せずに止まる
4. 今の S3 のカタログを `history/` に控えてから、新しいものを載せる（戻せるように）。
   控えは新しい順に `KEEP_HISTORY` 個まで残す
5. 件数と sha256 を書いた `manifest.json` も載せる。サーバーはカタログの ETag を見て、
   変わっていれば入れ替える（`serve_cloud.py` の定期確認）

## 載せないもの

**訪問者に出さない・外に出さないと決めているもの**は、カタログに入れない。

| 載せない | 理由 |
|---|---|
| `auth/`・`*.db`・pepper | 認証と利用者の記録。カタログとは保存先を分けている（`taguri_state.py`） |
| `tickets/` | 購入確認メールから読み取った、持ち主の購入の記録 |
| `lookback.*`・`chronicle.json`・`people_read.json`・`waiting.json`・`recommend.html` | 持ち主の観劇履歴から作った分析。訪問者には出さない（`app._is_owner`） |
| `declared.json`・`declined.json` | 持ち主のお気に入り・出さない語 |
| 取得の控え（`official_fail.json`・`requests_cache.json`・`*.part` など） | 取得する側だけが使う。`requests_cache.json` には利用者が頼んだ題名が入る |

## 実行する場所と権限

持ち主の記録がある手元のサーバー（EC2）で動かす。`run.py` が持ち主の評価から共通の
順位（`recommend2.json`）を作るためである。S3 へ書くには `stage-catalog/` への
書き込み権限を持つ資格情報が要る（サーバーが使う読み取り専用の `taguri-catalog-reader`
とは別にする）。定期実行の設定は `tools/taguri/deploy/` を参照。

`boto3` を使う（`serve_cloud.py` と同じ例外。S3 の署名を標準ライブラリで手書きしない）。
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
S3_BUCKET = os.environ.get("STAGE_CATALOG_BUCKET", "nakaya-mao-private-play-recommendation2026")
S3_KEY = os.environ.get("STAGE_CATALOG_KEY", "stage-catalog/data.tar.gz")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")
KEEP_HISTORY = 8
MIN_UPCOMING = 100             # これより少なければ取得が壊れたとみなして載せない
MIN_RATIO = 0.5                # 前回のこの割合を下回ったら載せない（--force で越える）

EXCLUDE_DIRS = {"auth", "tickets", "mail"}
EXCLUDE_GLOBS = ["*.db", "*.db-wal", "*.db-shm", "*.db-journal", "*.sqlite*", "*pepper*",
                 "*.part", "*.tmp", ".*"]
EXCLUDE_FILES = {"review/lookback.json", "review/lookback.html", "review/chronicle.json",
                 "review/people_read.json", "review/waiting.json", "review/recommend.html",
                 "review/declared.json", "review/declined.json", "credits/official_fail.json",
                 "review/requests_cache.json"}


def log(msg: str) -> None:
    print(f"[publish_catalog] {msg}", flush=True)


def excluded(rel: str) -> bool:
    parts = rel.split("/")
    if parts[0] in EXCLUDE_DIRS or rel in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(parts[-1], g) for g in EXCLUDE_GLOBS)


def update(mode: str, today: str) -> None:
    """`run.py` で取り直す。**途中の段が失敗しても続ける**（run.py の各段は required=False）。"""
    cmd = [sys.executable, str(ROOT / "tools" / "taguri" / "run.py"), "--no-open", "--today", today]
    if mode == "weekly":
        cmd.append("--fetch")
    log("取り直す: " + " ".join(cmd[1:]))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"run.py が {r.returncode} で終わった。カタログは載せない")


def count_upcoming(today: str) -> dict:
    """候補・カレンダー・お気に入りの、楽日が今日以降の件数。"""
    sys.path.insert(0, str(ROOT / "tools" / "review"))
    import recommend2 as RC                                         # noqa: E402
    t = datetime.date.fromisoformat(today)
    out = {}
    for name in ("candidates", "calendar", "favourites"):
        f = DATA / "review" / f"{name}.jsonl"
        n = 0
        if f.exists():
            for line in f.read_text(encoding="utf-8").split("\n"):
                if not line.strip():
                    continue
                end = RC.period_end(json.loads(line).get("period") or "")
                if end and end >= t:
                    n += 1
        out[name] = n
    return out


def build(archive: Path) -> dict:
    """公開してよいファイルだけをまとめる。**シンボリックリンクと特殊ファイルは入れない**
    （サーバー側の `_install_catalog` もそれを拒む）。"""
    n_files = 0
    with tarfile.open(archive, "w:gz") as tf:
        for path in sorted(DATA.rglob("*")):
            rel = path.relative_to(DATA).as_posix()
            if path.is_symlink() or excluded(rel):
                continue
            if path.is_dir():
                continue
            if not path.is_file():
                continue
            tf.add(path, arcname=rel, recursive=False)
            n_files += 1
    return {"files": n_files}


def verify(archive: Path) -> None:
    """まとめたものを読み直して、載せてはいけないものが無いか確かめる。"""
    with tarfile.open(archive) as tf:
        names = []
        for m in tf.getmembers():
            p = Path(m.name)
            if p.is_absolute() or ".." in p.parts or not (m.isfile() or m.isdir()):
                raise SystemExit(f"危ないエントリが入っている: {m.name}")
            if excluded(p.as_posix()):
                raise SystemExit(f"載せないはずのファイルが入っている: {m.name}")
            names.append(m.name)
    if "review/candidates.jsonl" not in names:
        raise SystemExit("review/candidates.jsonl が無い。カタログは載せない")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_key() -> str:
    return S3_KEY.rsplit("/", 1)[0] + "/manifest.json"


def previous_manifest(s3) -> dict:
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=manifest_key())
        return json.loads(obj["Body"].read())
    except Exception:                                               # noqa: BLE001
        return {}


def upload(s3, archive: Path, manifest: dict) -> None:
    prefix = S3_KEY.rsplit("/", 1)[0] + "/history/"
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=S3_KEY)
        s3.copy_object(Bucket=S3_BUCKET, Key=f"{prefix}data-{stamp}.tar.gz",
                       CopySource={"Bucket": S3_BUCKET, "Key": S3_KEY})
        log(f"前のカタログを控えた: {prefix}data-{stamp}.tar.gz")
    except Exception as e:                                          # noqa: BLE001
        log(f"前のカタログは控えなかった（{type(e).__name__}）")
    s3.upload_file(str(archive), S3_BUCKET, S3_KEY,
                   ExtraArgs={"ContentType": "application/gzip"})
    s3.put_object(Bucket=S3_BUCKET, Key=manifest_key(),
                  Body=json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8"),
                  ContentType="application/json")
    # 控えは新しい順に KEEP_HISTORY 個まで
    hist = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix).get("Contents") or []
    for old in sorted(hist, key=lambda o: o["Key"], reverse=True)[KEEP_HISTORY:]:
        s3.delete_object(Bucket=S3_BUCKET, Key=old["Key"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("daily", "weekly"), default="daily")
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--no-update", action="store_true", help="取り直さず、今の data/ をまとめるだけ")
    ap.add_argument("--dry-run", action="store_true", help="S3 に載せない（まとめて検査するだけ）")
    ap.add_argument("--out", type=Path, help="まとめた tar.gz をこの場所にも残す")
    ap.add_argument("--force", action="store_true", help="前回より大きく減っていても載せる")
    ap.add_argument("--data-dir", type=Path, help="まとめる元（既定は data/。試験用）")
    a = ap.parse_args()
    global DATA
    if a.data_dir:
        DATA = a.data_dir.resolve()

    DATA.mkdir(exist_ok=True)
    # **同時に 2 本走らせない**（毎日と週 1 が重なったとき・手で走らせたとき）
    with open(DATA / ".publish_catalog.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log("別の実行が走っているので止める")
            return 1
        return _run(a)


def _run(a) -> int:
    if not a.no_update:
        update(a.mode, a.today)
    counts = count_upcoming(a.today)
    log("これから観られる件数: " + "・".join(f"{k} {v}" for k, v in counts.items()))
    if counts["candidates"] < MIN_UPCOMING:
        log(f"候補が {counts['candidates']} 件しかない（{MIN_UPCOMING} 件未満）。取得が壊れているとみなし、載せない")
        return 1

    with tempfile.TemporaryDirectory(prefix=".catalog-build-", dir=ROOT) as work:
        archive = Path(work) / "data.tar.gz"
        info = build(archive)
        verify(archive)
        manifest = {"built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                    "mode": a.mode, "today": a.today, "upcoming": counts, "files": info["files"],
                    "bytes": archive.stat().st_size, "sha256": sha256(archive)}
        try:
            manifest["commit"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                                capture_output=True, text=True).stdout.strip()
        except OSError:
            pass
        log(f"まとめた: {info['files']} ファイル・{manifest['bytes'] / 1e6:.1f} MB")
        if a.out:
            a.out.write_bytes(archive.read_bytes())
            log(f"控え: {a.out}")
        if a.dry_run:
            log("--dry-run なので S3 には載せない")
            print(json.dumps(manifest, ensure_ascii=False, indent=1))
            return 0
        import boto3
        s3 = boto3.client("s3", region_name=S3_REGION)
        prev = previous_manifest(s3)
        prev_n = ((prev.get("upcoming") or {}).get("candidates")) or 0
        if prev_n and counts["candidates"] < prev_n * MIN_RATIO and not a.force:
            log(f"候補が前回の {prev_n} 件から {counts['candidates']} 件に減った。"
                "取得の失敗を疑って載せない（確かめたうえで --force）")
            return 1
        upload(s3, archive, manifest)
        log(f"載せた: s3://{S3_BUCKET}/{S3_KEY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
