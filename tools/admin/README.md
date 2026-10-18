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
    - あらすじは外のサイト由来のこともあるので、`claude -p` は**文を受け取って題材の JSON を返すだけ**にしています（issue #130）。道具は全部外し（`--tools ""`。ファイル・コマンド・外への通信の道具は名前でも断る）、MCP は読まず（`--strict-mcp-config`）、リポジトリの外の空の一時ディレクトリで動かします。環境変数は、claude が動くのに要るもの（PATH・HOME・プロキシ・Windows の基本の変数など。`admin.py` の `CLAUDE_ENV_KEEP`）だけを渡し、`CLOUDFLARE_API_TOKEN` などの本番の鍵は渡しません
    - ログインはいつもの Claude Code のもの（サブスクリプション）をそのまま使います。設定し直しは要りません
    - 「claude が古く、道具を外す引数を知らない」と出たら `claude update` で新しくしてください（守りを外しては動かしません）
    - 返ってきた答えは、積んだ読み取りにある公演の分だけ、語の長さと数を確かめてから書きます
  - Claude Code のセッションでは「読み取り待ちを片付けて」と頼むと、`.claude/skills/taguri-admin-queue` の手順で片付けます
    - このときはセッションの Claude が道具を持っているので、あらすじの中の指示には従わないよう手順に書いてあります

## 要るもの
- `cd cloudflare && npx wrangler login`（D1 を読み書きするため）
- wrangler は `cloudflare/package-lock.json` の版を使います（issue #131）。`cd cloudflare && npm ci` をしてあればその wrangler を、無ければその版を名指しで `npx` が取ってきます（その時いちばん新しい版は取りません）。lockfile が変わったら `npm ci` をし直すと、取り込みを待たずに動きます
- ポスターを入れるとき: 環境変数 `CLOUDFLARE_ACCOUNT_ID` と `CLOUDFLARE_API_TOKEN`（R2 の書き込み権限）、Pillow
- 鍵は GitHub やチャットに貼らないでください

## 無料枠
書く前に数えます（`cloudflare/scripts/free_tier.py` の `CAPS`: 管理画面の D1 の書き込み 1 日 1,000 行・ポスター 1 か月 300 枚、取得と共通の D1・R2 の上限）。届くと書かずに止めます。控えは `data/admin/free_tier/usage.json`。

## 公演修正依頼（利用者から）
- 本番のカードの下の「公演情報の誤りを知らせる」から届きます（1 人 1 日 5 件まで）。D1 の `fix_request` に入り、起案者にメールが届きます
- 管理画面の左の「公演修正依頼」に未対応の依頼が並びます（開いているあいだは 5 分ごとに読み直し、題名に件数が出ます）。押すと、その公演の編集が依頼の文と一緒に開きます。直して保存したら「直した」、直さないなら「見送る」（控えは利用者には出ません）。どちらも記録に残ります

### メールの設定（1 回だけ・無料）
独自ドメインを使わない約束なので、起案者の Gmail から自分宛てに送ります。
1. Google アカウントで 2 段階認証を有効にし、「アプリ パスワード」を 1 つ作る（https://myaccount.google.com/apppasswords）
2. Cloudflare のダッシュボード → Workers & Pages → app → 設定 → 変数とシークレット で、種類「シークレット」として次を足す
   - `SMTP_USER`: Gmail のアドレス
   - `SMTP_PASS`: 1 で作ったアプリ パスワード（16 文字）
   - `NOTIFY_TO`: 届け先（省略すると SMTP_USER）
3. 次の配信から届きます。設定が無いあいだも依頼は保存され、管理画面で見られます
- パスワードはチャットや GitHub に貼らないでください。メールは 1 日 30 通まで（`free-tier.js` の `FIX_MAILS_PER_DAY`）で、越えた日の依頼は保存だけします
