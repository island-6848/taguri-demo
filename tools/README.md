# 調査ツール

タスク [#000001](../tasks/active/current/000001-customer-acquisition-system-requirements.md) の現地調査・SNS 調査に使うスクリプト群。

既存の `geo/` `instagram/` の各スクリプトは **Python 標準ライブラリのみ**で書いてあり、何も入れずに `python3 tools/...` で動く。この方針は今後も維持する（環境が変わっても壊れないため）。

## 実行環境

環境構築は [`setup_env.sh`](setup_env.sh) にまとめてある（冪等。何度実行してもよい）。

```bash
bash tools/setup_env.sh          # sudo 不要な部分
bash tools/setup_env.sh --deps   # 共有ライブラリも入れる（パスワードを聞かれる）
```

| 要素 | 状態 | 備考 |
|------|------|------|
| pip | **導入済み** 26.2.1 | `ensurepip` も `venv` も無かったため `get-pip.py` で直接導入。PEP 668 の保護があるため `--user --break-system-packages` で ~/.local に限定して入れている |
| Node.js / npm | **導入済み** v22.20.0 / 10.9.3 | 公式ビルド済み tarball を `~/.local/nodejs` に展開し、`~/.local/bin` に symlink（`npm` の shebang が PATH 上の `node` を要求するため symlink が必須） |
| sudo | **元から使える** | 未インストールだったのではなく、ユーザは `sudo` グループに属している。ただし**パスワード入力が必要なため非対話では実行できない**。sudo が要る操作はユーザ自身が実行する必要がある |
| Chromium（Playwright 同梱） | **ダウンロード済み** | `~/.cache/ms-playwright/` |
| Chromium の共有ライブラリ | **要 sudo** | Ubuntu 26.04 では大半が既に入っており、不足は `libnspr4` `libnss3` `libasound2t64` の 3 つのみ。`sudo apt-get install -y libnspr4 libnss3 libasound2t64` |
| instaloader | 導入済み 4.15.3 | Instagram 取得の代替手段。ただし結局ログインが必要 |

`playwright install-deps` は使わない。xvfb や各種フォントまで入れようとして、このリリースに存在しないパッケージで失敗するため、必要最小限を直接指定している。

**ヘッドレスブラウザが動けば、Instagram もストリートビューも API キー無しで取得できるようになる。** 上記 3 パッケージが入るまでは、下記の「認証・キーが必要」な制約が残る。

## 一覧

| スクリプト | 用途 | 認証 | 状態 |
|-----------|------|------|------|
| `geo/fetch_osm_context.py` | 周辺の道路・街灯・駐輪場・店舗を OpenStreetMap から取得 | 不要 | **動作確認済み** |
| `geo/fetch_kartaview.py` | KartaView の街路画像を取得 | 不要 | 動作するが**現地のカバレッジがほぼ無い** |
| `geo/fetch_google_streetview.py` | Google ストリートビュー画像を取得 | **API キー必須** | キー待ち |
| `instagram/fetch_posts.py` | 全投稿の画像とキャプションを取得 | **セッション Cookie または Graph API トークン必須** | 認証情報待ち |

取得した画像は `data/` 配下に保存され、Claude Code の Read ツールで画像として直接読める（視覚的に解析できる）。

## 画像取得の可否と、その理由

### 判明した根本的な制約

**「夜の見え方」はどの画像サービスでも取得できない。** Google ストリートビューも KartaView も撮影は原則として日中である。したがって「夜に黒板の看板がどう見えるか」「アーケードの先のギャラリーの窓が暗いか」は、**現地で夜間に撮影した写真でしか確認できない**。API キーを用意しても、この点は解決しない。

昼間の画像から判定できるのは、道幅・見通し・街灯ポールの有無・建物の外観・看板の設置位置といった、時間帯に依存しない要素に限られる。

### KartaView（キー不要・カバレッジ不足）

コミュニティ投稿のドライブレコーダー画像。API キーが不要なのが利点だが、**柴崎駅周辺は半径 600m でも画像が 1 枚しか存在せず、しかもそれは甲州街道上（2017 年 8 月撮影）**で、店舗のある裏道は写っていない。実行済みの結果は `data/streetview/jindaiyu-00.jpg`。

```bash
python3 tools/geo/fetch_kartaview.py --lat 35.654551 --lng 139.5662897 \
    --radius 150 --limit 14 --label jindaiyu --outdir data/streetview
```

### Google ストリートビュー（キー必須）

キー無しのリクエストは `REQUEST_DENIED`（実測）。キーの取得手順:

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「API とサービス」→ **Street View Static API** を有効化
3. 「認証情報」→ API キーを作成
4. **請求先アカウントの紐付けが必須**（無料枠を超えない範囲でも登録は必要）
5. キーには HTTP リファラ制限ではなく **API 制限（Street View Static API のみ）** をかけること

```bash
export GOOGLE_MAPS_API_KEY='...'
# 神代湯前から 4 方向
python3 tools/geo/fetch_google_streetview.py --lat 35.654551 --lng 139.5662897 \
    --label jindaiyu --headings 0,90,180,270 --outdir data/streetview
# 柴崎駅北口から
python3 tools/geo/fetch_google_streetview.py --lat 35.653971 --lng 139.566460 \
    --label station-north --headings 0,90,180,270 --outdir data/streetview
```

メタデータ（パノラマの有無と撮影年月）を先に確認してから画像を取得するので、存在しない座標に無駄な課金が発生しない。

### Instagram（認証必須）

匿名アクセスは 2026-08-17 時点で全経路が封じられていることを実測した。

| 試した方法 | 結果 |
|-----------|------|
| プロフィール HTML の直接取得 | HTTP 200 だが JS シェルのみ。投稿データ・画像 URL を含まない |
| `i.instagram.com/api/v1/users/web_profile_info/`（`X-IG-App-ID` 付き） | HTTP 400 |
| `?__a=1&__d=dis` | HTTP 201 / 本文 0 バイト |
| 投稿の `/embed/captioned/` | JS シェルが返り画像 URL なし |

したがって次のどちらかが必要。

**方法 1: セッション Cookie（手軽）**

ブラウザで Instagram にログインし、開発者ツールの Application → Cookies から `sessionid` の値をコピーする。

```bash
export IG_SESSIONID='...'   # 引数ではなく環境変数で渡す（引数はプロセス一覧に見える）
python3 tools/instagram/fetch_posts.py --user yorucafe_mayoi \
    --outdir data/instagram --max-posts 300
```

`sessionid` は**パスワードと同等の機密情報**である。ファイルにも Git にも残さないこと。作業後は Instagram の設定から「すべてのセッションからログアウト」で無効化できる。

**方法 2: Instagram Graph API（公式・恒久運用向け）**

規約上の正式な経路で、Cookie の共有が不要。ただし前提条件がある。

1. 対象アカウントがプロフェッショナル（ビジネスまたはクリエイター）であること
2. Facebook ページに紐づいていること
3. [Meta for Developers](https://developers.facebook.com/) でアプリを作成し、`instagram_basic` 権限のアクセストークンを発行すること

```bash
export IG_GRAPH_TOKEN='...'
python3 tools/instagram/fetch_posts.py --graph --ig-user-id <IG_USER_ID> \
    --outdir data/instagram
```

店舗アカウントを継続的に分析するなら方法 2 が望ましい。単発でメニュー画像を読むだけなら方法 1 で足りる。

## 出力先

| ディレクトリ | 内容 |
|------------|------|
| `data/streetview/` | 街路画像と `osm-context.json` |
| `data/instagram/posts.json` | 投稿メタデータ（キャプション・日時・いいね数） |
| `data/instagram/img/` | 投稿画像 |

`data/instagram/` は投稿画像を含み、著作権と容量の両面で Git に載せるべきではないため `.gitignore` で除外している。
