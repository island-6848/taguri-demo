---
id: dec-login-look-1018
type: decision
status: adopted
date: 2026-10-18
title: ログイン画面の色をログイン後（theme.css の明るい表示）にそろえ、復旧コードをメールの下に点線で置き、状態の文を押したボタンの直下に出す
sources:
  - cloudflare/public/login.html
  - cloudflare/public/auth.css
  - cloudflare/src/client/login.js
  - cloudflare/test/recovery-login.test.js
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: dec-about-on-login
---
起案者の指示（2026-10-18）6 つのうち、ログイン画面の見た目と文言の分。

- 色: ログインの前の頁（/login・/terms・/privacy・/oauth/calendar）は theme.css を読まないので、theme.css の明るい表示の色の値（地 #f2f2f3・紙 #fff・文字 #1d1d1f・差し色えんじ #9b2335 など）を auth.css に写した。上の帯はえんじの塗りをやめ、ログイン後の行き先の帯と同じ紙の地に濃い字（印だけ差し色）。暗い表示はログイン後と同じく style.css のまま。theme.css の色を変えたら auth.css も直す（コメントに書いた）。
- 復旧コードでログイン: 独立した札（auth-card）をやめ、ログインの欄の中、「メールでログイン」の下に 2px の点線を引いてその下に、メールと同じ「入力欄＋ボタン」の形で置く。削除（?purpose=delete）・結び付け（?link=1）の画面でも同じ場所。
- 状態の文: #status を 1 つのまま（aria-live も 1 つ）、押したボタン・欄の直下へ動かす（login.js say の第 3 引数）。パソコンの幅でボタンが横に並んでいるときは列の下。メールのリンクは入力欄の行の下、パスキーで作ったあとは復旧コードの札の中、削除は削除の札の中。
- 迷惑メール: 「メールでログイン」と「メールで始める」（登録するメールアドレス）の入力欄の下に、迷惑メールボックスを確認するよう書いた。
- 「Google」→「Googleアカウント」: 「Googleアカウントでログイン」「Googleアカウントで始める」など、ログインの方法を指すところ。パソコンの幅では「Googleアカウントで始める」が長くなり 3 つ並びがはみ出すので、Google を 1 行目いっぱい、メールとパスキーを 2 行目にした。
- 確かめ: e2e-walk に「ログイン画面と規約の見た目（PC・電話・暗い表示）」の段と、案内がボタンの直下に出るかの確認を足した（44 段すべて OK）。
