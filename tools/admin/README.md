# たぐりの管理画面（このパソコンだけで開く）

## 開き方（初めて）
1. このパソコンにリポジトリを取ってくる（`git clone https://github.com/island-6848/taguri-demo.git`、すでにあれば `git pull`）
2. Python 3 と Node.js（https://nodejs.org）を入れる
3. `cd taguri-demo/cloudflare && npx wrangler login`（ブラウザで Cloudflare にログイン。1 回だけ）
4. 開く
   - Mac: Finder で `tools/admin/open-admin.command` をダブルクリック（またはターミナルで `python3 tools/admin/serve_admin.py`）
   - Windows: `tools\admin\open-admin.bat` をダブルクリック（または `py tools\admin\serve_admin.py`）
5. ブラウザが開きます。開かなければ、黒い画面に出た `http://127.0.0.1:8770/?t=…` を開いてください

- このパソコンの中だけで開きます（127.0.0.1）。鍵は `data/admin/token` に控え、起動し直しても URL は変わらないのでブックマークできます。動いているあいだだけ開けます（止めるには窓を閉じるか Ctrl-C）
- `admin.html` を直接ダブルクリックしても動きません（上の 4 で開きます）
- このクラウドのセッションの中で動かしても、お手元のブラウザからは届きません（お手元のパソコンで動かします）
- できること: 公演を探す／ポスターを入れる（縮めて R2 へ）／あらすじ・題材・詳細（会場・期間・料金・タイムテーブル・出演など）を直す／手で直した分を消して取得した内容に戻す
- 直した内容は本番の D1（`stage_override`・`poster`・`admin_log`）と、手元の `data/admin/log.jsonl` に書きます。カードは取得のたびに作り直されますが、手で直した分は Worker が画面に出すときに重ねるので消えません
- あらすじを入れて題材を空にすると、題材の読み取りを `data/admin/llm_queue.jsonl` に積みます
  - 「Claude で題材を読み取る」: このパソコンの Claude Code（`claude -p`）が読みます。`ANTHROPIC_API_KEY` は渡しません（渡すと従量課金の API になるため）
  - Claude Code のセッションでは「読み取り待ちを片付けて」と頼むと、`.claude/skills/taguri-admin-queue` の手順で片付けます

## 要るもの
- `cd cloudflare && npx wrangler login`（D1 を読み書きするため）
- ポスターを入れるとき: 環境変数 `CLOUDFLARE_ACCOUNT_ID` と `CLOUDFLARE_API_TOKEN`（R2 の書き込み権限）、Pillow
- 鍵は GitHub やチャットに貼らないでください

## 無料枠
書く前に数えます（`cloudflare/scripts/free_tier.py` の `CAPS`: 管理画面の D1 の書き込み 1 日 1,000 行・ポスター 1 か月 300 枚、取得と共通の D1・R2 の上限）。届くと書かずに止めます。控えは `data/admin/free_tier/usage.json`。
