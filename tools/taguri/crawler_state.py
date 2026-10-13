#!/usr/bin/env python3
"""取得処理の作業データ（data/）を、毎回まっさらな実行環境の間で引き継ぐ。

    python3 tools/taguri/crawler_state.py restore --from state/   # 始める前：前回の作業データを戻す
    python3 tools/taguri/crawler_state.py save --to state/        # 終わった後：作業データを書き出す

## なぜ要るのか

取得処理（`publish_catalog.py` → `run.py`）は、前回までの控えを引き継いで動く
（お気に入りの検索は 3 日、依頼の検索は 7 日控える。週 1 は「新しい公演と前回取れなかった分だけ」取る）。
GitHub Actions は毎回まっさらな機械で動くので、**前回の data/ を戻してから始め、終わったら書き出す。**
（docs/knowledge の crawler-state-between-runs・dec-crawler-gha-private）

## 置く場所

**AWS は使っていない**（no-aws）。作業データは、取得処理を動かす非公開リポジトリ
（`island-6848/taguri-crawler`）の `state` ブランチに、ファイルのまま置く（ワークフローが
取り出し・書き戻しをする。このスクリプトは、そのディレクトリと data/ の間で写すだけ）。
非公開なので、公開カタログに入れない取得の控え（依頼された題名の控えなど）も置いてよい。

利用者の記録・認証・持ち主の購入の記録（`*.db`・`auth/`・`tickets/`・`mail/`・pepper）は、
戻すときも書き出すときも入れない。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SKIP_DIRS = {".git", ".github"}


def keep(rel: str) -> bool:
    """作業データに入れてよいか。利用者・持ち主の記録と、ロック・一時ファイルは入れない。"""
    parts = rel.split("/")
    name = parts[-1]
    if parts[0] in ("auth", "tickets", "mail") or parts[0] in SKIP_DIRS:
        return False
    if any(t in name for t in (".db", ".sqlite", "pepper")):
        return False
    if name.endswith(".part") or name.startswith(".publish_catalog.lock"):
        return False
    return True


def _files(base: Path):
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base).as_posix()
        if path.is_symlink() or not path.is_file() or not keep(rel):
            continue
        yield rel, path


def copy_tree(src: Path, dst: Path) -> int:
    """src の入れてよいファイルを dst に写す。**リンクは辿らない・dst の外には書かない。**"""
    dst.mkdir(parents=True, exist_ok=True)
    root = dst.resolve()
    n = 0
    for rel, path in _files(src):
        out = (dst / rel).resolve()
        if root not in out.parents:
            raise ValueError("unsafe path")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        n += 1
    return n


def clear(dst: Path) -> None:
    """書き出す前に、前回の作業データを消す（消えた公演の控えを残さない）。`.git` は残す。"""
    if not dst.exists():
        return
    for child in dst.iterdir():
        if child.name in SKIP_DIRS:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def restore(src: Path) -> int:
    if not src.is_dir():
        print("前回の作業データが無い。空から始める（初回は週 1 の取り直しで始めること）")
        return 0
    n = copy_tree(src, DATA)
    print(f"作業データ {n} ファイルを戻した")
    return n


def save(dst: Path) -> int:
    clear(dst)
    n = copy_tree(DATA, dst)
    print(f"作業データ {n} ファイルを書き出した")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True)
    r = sub.add_parser("restore")
    r.add_argument("--from", dest="src", type=Path, required=True)
    s = sub.add_parser("save")
    s.add_argument("--to", dest="dst", type=Path, required=True)
    a = ap.parse_args()
    try:
        restore(a.src) if a.action == "restore" else save(a.dst)
    except Exception as e:                                          # noqa: BLE001
        print(f"{a.action} に失敗した（{type(e).__name__}）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
