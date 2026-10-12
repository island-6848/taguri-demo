#!/usr/bin/env python3
"""公開版（デモ版・サービス版）をRender等のクラウドで動かすための入口（#000008・2026-08-29）。

    python3 tools/taguri/serve_cloud.py

`tools/taguri/run.py`（ローカル・EC2向け）とはあえて別ファイルにした。**run.py は
「利用者が1回実行して、閉じたら落ちる一時プロセス」を前提にしたコードで、これは
`127.0.0.1`固定・監視（`_watchdog`）・「終わる」ボタンでの終了と分かちがたく
結び付いている。** クラウドでは逆に「常時稼働し、誰でも公開URLから入れる」ことが
要件なので、前提から違う。1本のファイルに両方の条件分岐を持ち込むより、
**入口を分けて、それぞれの前提に素直な形にする**方を選んだ。

## この入口だけがすること

- `PORT`環境変数（Renderが起動時に渡す）を読み、`0.0.0.0`で待ち受ける
- `Server`を`public=True`で作る（`serve.py`参照。起動ごとの合言葉を迂回し、
  `/api/close`を無効化する）
- **どちらの版で動くかを `TAGURI_EDITION`（`demo` か `service`）で決める。** 既定は
  `demo`。デモ版とサービス版は**別のサービス（別の URL・別の保存先・別の合言葉）として
  立てる**前提で、1 つのプロセスが両方を兼ねることはない（docs/editions.md）
- **サービス版は永続の保存先（`TAGURI_STATE_DIR`）が無ければ起動しない。** 利用者の
  記録が再デプロイで消えるのを、黙って許さない
- ブラウザを開こうとしない（サーバ側に画面が無い）
- 監視（`_watchdog`）で自動終了しない（`public=True`だと自動的に無効になる）

## 呼ばないもの

`run.py`の9段（購入取り込み・評価待ち・材料取得・お気に入り検索・カレンダー取り込み・
推薦計算・ポスター取り込み・振り返り材料組み・画面を開く）は呼ばない。**デモの
体験データは、あらかじめEC2で1回だけ用意する**（#000008の作業ログ参照）。起動のたびに
外部サイトへ取得しに行く必要は無く、むしろ**リクルーターの操作をきっかけに外部サイトへの
取得やLLM呼び出しが無制限に走るのは避けたい**（費用・礼儀の両面で）。反応・評価・
お気に入りの登録に対しては、`serve.py`が本人の画面キャッシュを無効化し、
次の読み込みで本人の保存済みデータから計算する（外部通信は無い）。

利用者の SQLite と認証 pepper は `TAGURI_STATE_DIR` で公演カタログと分離できる。
この設定だけではホスト側の永続性は保証できないため、永続ディスクの設定と
再起動・再デプロイ後の確認が必要。未設定時にもカタログ交換で既存DBを削除しないが、
Render の一時ファイルシステムが失われたときの復元はできない。

## データは公開Gitリポジトリに同梱しない（#000008・2026-08-29に撤回）

**当初は`data/review/`をリポジトリに直接コミットしていたが、撤回した。** 起案者の
指摘 ──「今って再配布には当たらない？」。CoRichから取得した公演情報・ポスター画像を
Publicリポジトリに置くことは、[利用規約第6条](../../docs/000007-taguri-terms-of-use.md)
が禁じている「第三者への再配布」に当たる。特にポスター画像は各制作会社の著作物であり、
リスクが高い。

**代わりに、非公開のS3から起動時に取得する。** 「ゆくゆく本番システムとして公開する」
ことも見据え、この置き場所はデモ専用ではなく**利用者共通の公演カタログ**（決定事項2で
「全利用者で共有する」と決めた性質のデータ）の置き場として設計した。読み取りは
専用の読み取り専用IAMユーザー（`taguri-catalog-reader`、対象は
`stage-catalog/`prefixのみ）に絞ってある。

**`boto3`を使う。** このファイルだけの例外として、標準ライブラリのみという方針
（`tools/README.md`）から外れる。SigV4署名を標準ライブラリで手書きするより、
AWS公式のSDKを使うほうが確実で読みやすいと判断した。影響は`serve_cloud.py`という
クラウド専用の入口1本に閉じており、`tools/`本体の方針は変えない。
"""

from __future__ import annotations

import os
import shutil
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import taguri_state as STATE

S3_BUCKET = os.environ.get("STAGE_CATALOG_BUCKET", "nakaya-mao-private-play-recommendation2026")
S3_KEY = os.environ.get("STAGE_CATALOG_KEY", "stage-catalog/data.tar.gz")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")
# **動いている間も、カタログが新しくなったら入れ替える。** カタログは
# `publish_catalog.py` が定期的に作り直して S3 に載せる。起動時に 1 回読むだけだと、
# 常時稼働のサーバーは再起動するまで古いカタログのまま動き続ける。0 で止める
CATALOG_REFRESH_HOURS = float(os.environ.get("CATALOG_REFRESH_HOURS", "6") or 0)
_installed_etag: list[str | None] = [None]


def edition() -> str:
    """`TAGURI_EDITION` を読む。**知らない値では起動しない**（打ち間違いで別の版にならない）。"""
    value = (os.environ.get("TAGURI_EDITION", "") or "demo").strip().lower()
    if value not in ("demo", "service"):
        raise RuntimeError("TAGURI_EDITION must be 'demo' or 'service'")
    return value


def check_service_storage(ed: str) -> None:
    """サービス版は、利用者の保存先がカタログと別の永続ディレクトリに無ければ止める。"""
    if ed == "service" and STATE.state_dir() is None:
        raise RuntimeError("service edition requires TAGURI_STATE_DIR on a persistent disk")


def _install_catalog(archive: Path) -> None:
    """Validate in staging, retain legacy mutable state, then swap directories.

    Tar links, traversal and special files are rejected. Catalog archives are
    never a source of visitor databases or authentication secrets.
    """
    with tempfile.TemporaryDirectory(prefix=".catalog-", dir=ROOT) as work:
        work = Path(work)
        new = work / "new"
        new.mkdir()
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                path = Path(member.name)
                if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                    raise ValueError("unsafe catalog archive")
                # Older snapshots may include a demo owner's DB. Never import it.
                if (path.parts and path.parts[0] == "auth") or any(
                        token in path.name for token in (".db", ".sqlite", "pepper")):
                    continue
                dest = new / path
                if member.isdir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    source = tf.extractfile(member)
                    if source is None:
                        raise ValueError("invalid catalog member")
                    with source, dest.open("wb") as output:
                        shutil.copyfileobj(source, output)
        if not (new / "review" / "candidates.jsonl").is_file():
            raise ValueError("catalog lacks candidates")
        current = ROOT / "data"
        # Compatibility when no external persistent directory is configured.
        # This protects refreshes, not host filesystem loss on redeployment.
        for relative in ("auth", "review/ratings.db", "review/ratings.db-wal",
                         "review/ratings.db-shm", "review/ratings.db-journal", "review/declared.json"):
            source = current / relative
            dest = new / relative
            if source.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, dest)
        backup = work / "old"
        if current.exists():
            current.rename(backup)
        try:
            new.rename(current)
        except BaseException:
            if backup.exists():
                backup.rename(current)
            raise


def _fetch_catalog() -> None:
    """Fetch only catalog data; user storage is never replaced by the archive."""
    try:
        import boto3
        s3 = boto3.client("s3", region_name=S3_REGION)
        etag = _remote_etag(s3)
        with tempfile.TemporaryDirectory(prefix=".catalog-download-", dir=ROOT) as work:
            archive = Path(work) / "catalog.tar.gz"
            s3.download_file(S3_BUCKET, S3_KEY, str(archive))
            _install_catalog(archive)
        _installed_etag[0] = etag
        STATE.event("catalog_refresh")
    except Exception:
        STATE.event("catalog_refresh", outcome="failed")
        raise RuntimeError("catalog refresh failed; existing state retained") from None


def _remote_etag(s3) -> str | None:
    try:
        return s3.head_object(Bucket=S3_BUCKET, Key=S3_KEY).get("ETag")
    except Exception:                                               # noqa: BLE001
        return None


def _refresh_loop(srv) -> None:
    """カタログの ETag を定期的に見て、変わっていれば入れ替える。

    **利用者の保存先がカタログと別の場所にあるときだけ入れ替える**（`TAGURI_STATE_DIR`）。
    未設定のときは利用者の SQLite が `data/review/` にあり、`data/` ごと入れ替えると
    **開いている DB の実体を、動いたまま一時ディレクトリへ移して消してしまう。**
    その場合は入れ替えず、次の再起動（起動時の取得）に任せる。
    入れ替えに失敗しても、今のカタログで動き続ける（`_install_catalog` は途中で失敗すると
    元に戻す）。
    """
    import boto3
    s3 = boto3.client("s3", region_name=S3_REGION)
    while True:
        time.sleep(CATALOG_REFRESH_HOURS * 3600)
        if STATE.state_dir() is None:
            continue
        etag = _remote_etag(s3)
        if not etag or etag == _installed_etag[0]:
            continue
        try:
            _fetch_catalog()
        except RuntimeError:
            continue
        # 公演の索引と、訪問者ごとの画面の控えを捨てる（古いカタログで作った分）
        S.APP.reset_caches()
        srv.screen_cache.clear()


import serve as S                                                  # noqa: E402


def main() -> int:
    ed = edition()
    check_service_storage(ed)
    STATE.prepare_storage()
    _fetch_catalog()
    port = int(os.environ.get("PORT", "8000"))
    # **GitHub Pages移行（#000009）。** `CORS_ORIGIN`にGitHub Pagesの配信元
    # （例 `https://island-6848.github.io`）を設定すると、そこからのクロス
    # オリジン`fetch`（`/api/screen/*`等）を許可する。未設定なら今までどおり
    # CORSヘッダを出さない（同一オリジンの旧UIだけがRenderに残る前提）。
    cors_origin = os.environ.get("CORS_ORIGIN", "")
    try:
        srv = S.Server(ed, port, bind_host="0.0.0.0", public=True, edition=ed,
                       cors_origin=cors_origin)
    except Exception:
        STATE.event("server_start", outcome="failed")
        raise RuntimeError("server startup failed; check storage and service configuration") from None
    STATE.event("server_start")
    if CATALOG_REFRESH_HOURS > 0:
        threading.Thread(target=_refresh_loop, args=(srv,), daemon=True,
                         name="catalog-refresh").start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        STATE.event("server_stop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

