#!/usr/bin/env python3
"""取得処理の作業データ（data/）を、毎回まっさらな実行環境の間で引き継ぐ。

    python3 tools/taguri/crawler_state.py restore   # 始める前：前回の作業データを S3 から戻す
    python3 tools/taguri/crawler_state.py save      # 終わった後：作業データを S3 に置く

## なぜ要るのか

取得処理（`publish_catalog.py` → `run.py`）は、前回までの控えを引き継いで動く
（お気に入りの検索は 3 日、依頼の検索は 7 日控える。週 1 は「新しい公演と前回取れなかった分だけ」取る）。
GitHub Actions は毎回まっさらな機械で動くので、**前回の data/ を戻してから始め、終わったら置く。**
（docs/knowledge の crawler-state-between-runs・dec-crawler-gha-private）

## 置く場所

公開カタログ（`stage-catalog/data.tar.gz`、サーバーが読む）とは別の
`stage-catalog/crawler-state.tar.gz` に置く。公開カタログに入れない取得の控え
（依頼された題名の控えなど）も含むので、**バケットは非公開のまま**にする。
作業データがまだ無いとき（初回）は、公開カタログを種にして始める。

利用者の記録・認証・持ち主の購入の記録（`*.db`・`auth/`・`tickets/`・pepper）は、
戻すときも置くときも入れない。
"""
from __future__ import annotations

import argparse
import os
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
S3_BUCKET = os.environ.get("STAGE_CATALOG_BUCKET", "nakaya-mao-private-play-recommendation2026")
S3_KEY = os.environ.get("STAGE_CATALOG_KEY", "stage-catalog/data.tar.gz")
STATE_KEY = os.environ.get("CRAWLER_STATE_KEY", S3_KEY.rsplit("/", 1)[0] + "/crawler-state.tar.gz")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")


def keep(rel: str) -> bool:
    """作業データに入れてよいか。利用者・持ち主の記録と、ロック・一時ファイルは入れない。"""
    parts = rel.split("/")
    name = parts[-1]
    if parts[0] in ("auth", "tickets", "mail"):
        return False
    if any(t in name for t in (".db", ".sqlite", "pepper")):
        return False
    if name.endswith(".part") or name.startswith(".publish_catalog.lock"):
        return False
    return True


def pack(data: Path, archive: Path) -> int:
    n = 0
    with tarfile.open(archive, "w:gz") as tf:
        for path in sorted(data.rglob("*")):
            rel = path.relative_to(data).as_posix()
            if path.is_symlink() or not path.is_file() or not keep(rel):
                continue
            tf.add(path, arcname=rel, recursive=False)
            n += 1
    return n


def unpack(archive: Path, data: Path) -> int:
    """安全なものだけ戻す（絶対パス・`..`・リンク・特殊ファイル・記録は拒む）。"""
    n = 0
    data.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tf:
        for m in tf.getmembers():
            p = Path(m.name)
            if p.is_absolute() or ".." in p.parts or not (m.isfile() or m.isdir()):
                raise ValueError("unsafe archive")
            if m.isdir() or not keep(p.as_posix()):
                continue
            dest = data / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            src = tf.extractfile(m)
            if src is None:
                raise ValueError("invalid member")
            with src, dest.open("wb") as out:
                out.write(src.read())
            n += 1
    return n


def _s3():
    import boto3
    return boto3.client("s3", region_name=S3_REGION)


def _exists(s3, key: str) -> bool:
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except Exception:                                               # noqa: BLE001
        return False


def restore(s3=None) -> str:
    s3 = s3 or _s3()
    key = STATE_KEY if _exists(s3, STATE_KEY) else S3_KEY
    if not _exists(s3, key):
        print("作業データも公開カタログも無い。空から始める")
        return "empty"
    with tempfile.TemporaryDirectory() as work:
        archive = Path(work) / "state.tar.gz"
        s3.download_file(S3_BUCKET, key, str(archive))
        n = unpack(archive, DATA)
    which = "作業データ" if key == STATE_KEY else "公開カタログ（初回の種）"
    print(f"{which}から {n} ファイルを戻した")
    return "state" if key == STATE_KEY else "catalog"


def save(s3=None) -> int:
    s3 = s3 or _s3()
    with tempfile.TemporaryDirectory() as work:
        archive = Path(work) / "state.tar.gz"
        n = pack(DATA, archive)
        s3.upload_file(str(archive), S3_BUCKET, STATE_KEY)
    print(f"作業データ {n} ファイルを置いた")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("restore", "save"))
    a = ap.parse_args()
    try:
        restore() if a.action == "restore" else save()
    except Exception as e:                                          # noqa: BLE001
        # 例外の文には URL や鍵の一部が混じりうるので、種類だけを出す
        print(f"{a.action} に失敗した（{type(e).__name__}）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
