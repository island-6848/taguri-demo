---
id: dec-share-links
type: decision
status: adopted
date: 2026-10-21
title: 共有リンク（/s/<token>）。公演 1 件のカードか、観劇記録の一覧・眺める・お気に入り・観劇史年表を、リンクを知る人だけにログインなしで見せる。評価・感想・名前は共有するときに選び、既定は出さない。検索エンジンには載せず、いつでも取り消せる
sources:
  - cloudflare/src/share.js
  - cloudflare/migrations/0044.sql
  - cloudflare/src/worker.js
  - web/app.js
  - web/theme.css
  - cloudflare/public/privacy.html
  - cloudflare/test/share.test.js
  - cloudflare/test/e2e-walk.js
links:
  - affects: comp-public-server
---
起案者の指示（2026-10-21）「共有できるようにしたい。公演単体か、または指定のページをパブリックで公開するか選べるように」。起案者の答え（同日）:
- 公開できるもの: 観劇記録の一覧・眺める・お気に入りの一覧・観劇の年表と評価の一覧・「この公演を購入しました！」「興味ありにしました！」など公演単体のカード
- 評価・感想: 公開するときに選ぶ
- 範囲: リンクを知る人だけ（推測できない URL・検索エンジンに載せない・取り消せる）
- 名前（表示名・アイコン）: 公開するときに選ぶ

**作り**
- **表 share（migrations/0044）**
  - 列: token（22 文字・128 ビット）・user_id・kind・target（公演）・label（購入しました・興味あり・観ました）・評価・感想・名前を出すか・作った時刻。
  - 1 人 100 件まで。アカウントを消すと一緒に消える（ON DELETE CASCADE、cleanup の SCREEN_TABLES）。
  - 記録には数えない（記録の無いアカウントの片付けは、共有リンクだけ残っていても消す）。
- **公開ページ（share.publicShare）**
  - gate より先に `/s/<token>` を返す。ログインした人の画面（screens/）はそのまま使わない。出すものを 1 つずつ選んで組む。
  - 記録も読むだけの問い合わせで集める（loadWorks・recordsBase は取り消した記録を消す・自動で結び付けるなど、書き込みを伴う）。
  - 眺める・年表の部品（年輪・時間割・制覇マップ・年表）は使い回す。ただし publicHtml で、内部の道・ボタン・フォーム・スクリプト・data- の印を外す。
  - user_id・記録の鍵・内部の道は出さない（試験が確かめる）。
- **見出しとヘッダー**
  - `noindex,nofollow,noarchive` を meta と X-Robots-Tag の両方に付ける。
  - CSP は `script-src 'none'`。Referrer-Policy は no-referrer。
  - リンクのカード（OGP）は、共有ごとの題を付ける（例「この公演を観ました！『…』」）。公演のカードでは、その公演のポスターを `/s/<token>/poster` で出す（R2 の読み出しの上限は同じ r2ReadAllowed）。
- **控えと取り消し**
  - 公開ページは毎回、いまの記録から作る。控え（Cache-Control と caches.default）は 60 秒。
  - 取り消し（/api/share revoke）は行を消し、その場所の控えも消す。ほかの場所の控えは、最長 60 秒で切れる。
- **押し口**
  - 興味あり・購入済のカード（lists.js。build_cards.compose の形は変えない）、眺める・年表・お気に入りの見出しの下に「共有」がある。
  - 日記帳は、HTML を Python 版と同じ形に保つ試験（screens.test.js）があるので、app.js の fixupShare が「このページを共有」と各行の「共有（観ました）」を足す。行は記録の鍵で送り、公演に結び付いていない記録はサーバーが断る。
  - 小窓（app.js openShare）で、評価・感想・表示名とアイコンを選んでからリンクを作る。コピーと、端末の共有（navigator.share）ができる。
  - 設定の「共有中のリンク」で一覧し、取り消す。
- **プライバシーポリシー**: 第 5 条に、共有リンクの扱いを追記した。改めての同意（TERMS_VERSION）を求めるかは起案者が決める（owner-todo）。

**無料枠**
- 書き込みは、リンクを作る・取り消すときに 1 行ずつ。
- 公開ページを開くと、D1 は共有の行・記録・除外・まとめの数行〜記録の数ぶんを読む。眺めるは図の部品ぶん多い。
- 控え 60 秒と、接続元ごとの回数制限（rate-limit.js の any、10 秒に 120 回）で、同じリンクが大量に開かれても読み出しが増えすぎないようにした。
- 大量に広まった場合の読み出しは測っていない。

**確かめたこと**
- cloudflare の試験 543 件（share.test.js 7 件を含む）。
- e2e-walk の「共有リンク」の段（日記帳の行から作る → ログインしていない窓で開く → 取り消すと 404。電話の幅）。
