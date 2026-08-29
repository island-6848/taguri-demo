# ストリートビューを Claude Code から見られるようにする

## なぜ必要か

Google マップの Web 版はパノラマを JavaScript + WebGL で描画する。`WebFetch` や `curl` は
HTML を取るだけなので、あの環境では**画像が一切見えない**。タスク #000001 で
「ストリートビュー未取得」となったのはこれが理由。

解決策は 2 つある。**方法 A を推奨**（追加インストールが要らず、この環境でそのまま動く）。

| | 方法 A: Street View Static API | 方法 B: ヘッドレスブラウザ |
|---|---|---|
| 仕組み | HTTP で JPEG が直接返る | Chromium で描画して撮る |
| 追加インストール | **なし**（Python 標準ライブラリのみ） | Chromium + Playwright（`sudo` 必須・約 500MB） |
| 必要なもの | API キー（課金アカウント紐付けが必須） | なし |
| 費用 | 月 10,000 枚まで無料。超過分 $7.00/1,000 枚 | 無料 |
| 撮れるもの | 任意の座標・方位・画角の静止画 | 地図 UI ごとの画面全体 |
| 安定性 | 高い（公式 API・仕様が固定） | 低い（UI 変更や同意ダイアログで壊れる） |

---

## 方法 A: Street View Static API（推奨）

### 1. API キーを取る

Google Cloud Console で以下を行う。所要 5 分程度。

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成（既存でもよい）
2. **課金を有効化**する。Google Maps Platform は無料枠の利用でも課金アカウントの
   紐付けが必須（[公式](https://developers.google.com/maps/documentation/streetview/usage-and-billing)）
3. 「API とサービス」→「ライブラリ」で **Street View Static API** を検索して有効化
4. 「API とサービス」→「認証情報」→「認証情報を作成」→「API キー」
5. 作成したキーを編集し、**API の制限**で「Street View Static API」のみに絞る
   （キーが漏れても他の API を使われないようにする）
6. アプリケーションの制限は、サーバーから叩くので「なし」または IP 制限にする。
   **HTTP リファラ制限にすると curl から使えなくなる**ので注意

無料枠と単価（2026-08 時点、[料金表](https://developers.google.com/maps/billing-and-pricing/pricing)）:

- `Static Street View` … **月 10,000 呼び出しまで無料**、以降 $7.00 / 1,000 枚
- `Street View Metadata` … **無制限に無料**。だから `sv.py` は必ず先に
  メタデータで存在確認してから画像を取る（無駄な課金を出さないため）

### 2. キーを置く

```bash
mkdir -p ~/.config/streetview
echo 'ここにキー' > ~/.config/streetview/api_key
chmod 600 ~/.config/streetview/api_key
```

環境変数 `GOOGLE_MAPS_API_KEY` でも読む。`sv.py` はキーを標準出力・
`manifest.json`・エラーメッセージのいずれにも書き出さない（伏字にする）。

### 3. 疎通確認

```bash
./sv.py check
```

`OK: Street View Static API に到達し、メタデータを取得できました。` と出れば完了。

### 4. 使う

```bash
# 撮影されているか・いつ撮影されたかを確認（無料）
./sv.py meta "35.6512,139.5545"

# 4 方向を撮る
./sv.py shot "35.6512,139.5545" --heading 0,90,180,270

# 8 方位を一括で撮る（周囲の見え方をまとめて把握したいとき）
./sv.py around "35.6512,139.5545"

# 道路上の A 地点から建物 B を見た画像。方位角を自動計算する
./sv.py look-at 35.6512,139.5545 35.6514,139.5547

# 望遠で看板を寄って見る（fov を小さくする）
./sv.py shot "35.6512,139.5545" --heading 45 --fov 30

# 建物の上を見る / 足元を見る
./sv.py shot "35.6512,139.5545" --heading 45 --pitch 20
```

画像は既定で `./sv-out/<ラベル>/h045_p+00_f090.jpg` の形で保存され、
同じディレクトリに `manifest.json`（pano_id・撮影年月・実際の座標・著作権）が出る。
Claude Code はこの JPEG を `Read` すれば**画像として見られる**。

### 押さえておくべき制約

- `--size` の上限は **640x640**。それ以上は課金区分が変わるため既定のまま使う
- ストリートビューは**撮影時点の記録**。`meta` の `date` を必ず確認する。
  数年前の画像で現在の看板や外観を判断すると誤る
- **夜間の画像は基本的に存在しない**。Google の撮影はほぼ日中。
  タスク #000001 の「夜どう見えるか」は、この API では原理的に確認できない。
  昼の画像で分かるのは、建物の形・入口の位置・看板の位置と大きさ・
  アーケードの奥行き・通りからの見通しまで
- 路地や私道は撮影されていないことが多い。`ZERO_RESULTS` なら `--radius` を
  広げて最寄りの道路上のパノラマを拾う

---

## 方法 B: ヘッドレスブラウザ（キーを使いたくない場合）

`sudo` が必要なので**利用者自身が実行する**。Claude Code のプロンプトで
`! ` を先頭に付ければこのセッション内で実行でき、出力もそのまま共有される。

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv
python3 -m venv ~/.venv/sv && ~/.venv/sv/bin/pip install playwright
sudo ~/.venv/sv/bin/playwright install-deps chromium
~/.venv/sv/bin/playwright install chromium
```

その後:

```bash
~/.venv/sv/bin/python browser_shot.py 35.6512,139.5545 --heading 45 --out shot.png
```

方法 A と違い、地図 UI・道路名・周辺の店名ラベルも一緒に写るので
「地図として周辺を把握したい」ときはこちらが向く。ただし Google の UI 変更や
同意ダイアログで壊れやすく、自動アクセスは Google の利用規約上の制限も受ける。
継続的に使うなら方法 A にすること。

---

## 方法 C: 公式 API もブラウザも使えない場合

- [Mapillary](https://www.mapillary.com/)（無料 API トークンで街路画像を取得可能。
  ただし日本の住宅街の路地は投稿が少なく、カバーされていない可能性が高い）
- 現地写真を店主に撮ってもらう。**夜間の見え方はこれが唯一の確実な手段**で、
  タスク #000001 の入口離脱仮説の検証には結局これが必要になる
