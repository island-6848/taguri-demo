#!/usr/bin/env python3
"""就活向けデモをRender等のクラウドで動かすための入口（#000008・2026-08-29）。

    python3 tools/taguri/serve_cloud.py

`tools/taguri/run.py`（ローカル・EC2向け）とはあえて別ファイルにした。**run.py は
「利用者が1回実行して、閉じたら落ちる一時プロセス」を前提にしたコードで、これは
`127.0.0.1`固定・監視（`_watchdog`）・「終わる」ボタンでの終了と分かちがたく
結び付いている。** クラウドでは逆に「常時稼働し、誰でも公開URLから入れる」ことが
要件なので、前提から違う。1本のファイルに両方の条件分岐を持ち込むより、
**入口を分けて、それぞれの前提に素直な形にする**方を選んだ。

## この入口だけがすること

- `PORT`環境変数（Renderが起動時に渡す）を読み、`0.0.0.0`で待ち受ける
- `Server`を`demo_mode=True`で作る（`serve.py`参照。起動ごとの合言葉を迂回し、
  `/api/close`を無効化する）
- ブラウザを開こうとしない（サーバ側に画面が無い）
- 監視（`_watchdog`）で自動終了しない（`demo_mode=True`だと自動的に無効になる）

## 呼ばないもの

`run.py`の9段（購入取り込み・評価待ち・材料取得・お気に入り検索・カレンダー取り込み・
推薦計算・ポスター取り込み・振り返り材料組み・画面を開く）は呼ばない。**デモの
体験データは、あらかじめEC2で1回だけ用意する**（#000008の作業ログ参照）。起動のたびに
外部サイトへ取得しに行く必要は無く、むしろ**リクルーターの操作をきっかけに外部サイトへの
取得やLLM呼び出しが無制限に走るのは避けたい**（費用・礼儀の両面で）。反応・評価・
お気に入りの登録に対しては、`serve.py`が既存のとおり`recommend2.py`を都度呼んで
並べ直す（外部通信は無い、recommend2.pyは公開情報を集計するだけ）。

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
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))

S3_BUCKET = os.environ.get("STAGE_CATALOG_BUCKET", "nakaya-mao-private-play-recommendation2026")
S3_KEY = os.environ.get("STAGE_CATALOG_KEY", "stage-catalog/data.tar.gz")
S3_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")


def _fetch_catalog() -> None:
    """非公開S3から公演カタログを取得し、`data/`に展開する。

    **`data/review/candidates.jsonl`が無いときだけ取得する。** Renderは再デプロイの
    たびにディスクを作り直すので、毎回の起動で必ず走るが、**同じ内容を毎回S3から
    落とすだけで、CoRichへは一切アクセスしない**（外部への取得はEC2側で事前に
    済ませてある）。
    """
    marker = ROOT / "data" / "review" / "candidates.jsonl"
    if marker.exists():
        print("公演カタログはすでにある（取得済み）", flush=True)
        return
    try:
        import boto3
    except ImportError:
        print("boto3が無いため公演カタログを取得できない。"
              "Build Commandに`pip install boto3`が要る。", flush=True)
        return
    print(f"公演カタログをS3から取得中 ── s3://{S3_BUCKET}/{S3_KEY}", flush=True)
    s3 = boto3.client("s3", region_name=S3_REGION)
    archive = ROOT / "_stage_catalog.tar.gz"
    s3.download_file(S3_BUCKET, S3_KEY, str(archive))
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tf:
        tf.extractall(ROOT / "data")            # noqa: S202 自分でS3に置いた信頼できる中身
    archive.unlink()
    print("公演カタログの取得が完了", flush=True)


import serve as S                                                  # noqa: E402


def main() -> int:
    _fetch_catalog()
    port = int(os.environ.get("PORT", "8000"))
    srv = S.Server("demo", port, bind_host="0.0.0.0", demo_mode=True)
    print(f"デモサーバ起動 ── 0.0.0.0:{port}（demo_mode）", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
