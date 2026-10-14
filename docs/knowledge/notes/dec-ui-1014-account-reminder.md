---
id: dec-ui-1014-account-reminder
type: decision
status: adopted
date: 2026-10-14
title: おすすめの初期画面にワンポイントを出す・「アカウント・記録」のリンクを外す・アカウントにアイコン画像・開幕リマインドを 1 公演 1 枠に・出演欄の括弧の注記で名前が割れるのを直す
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/worker.js
  - cloudflare/src/screens/account.js
  - cloudflare/src/screens/index.js
  - web/app.js
  - web/theme.css
  - cloudflare/test/account-avatar.test.js
  - cloudflare/test/recommend-screen.test.js
links:
  - depends_on: new-user-reco-threshold
  - depends_on: dec-account-cap-counted
---
起案者の指示（2026-10-14、スマホの画面写真 2 枚つき）。
- おすすめが 1 件も出ないとき（県で絞っていないとき）、「おすすめを出すためのワンポイント」を出す。技術の言葉を使わず、(1) 観た公演を 2 本以上、◎ だけでなく ○△× も混ぜて評価、(2) 題名と観た日を正しく入れる・日記帳で結び付いていない記録は公演を選ぶ、(3) 好きな俳優・劇団・作品をお気に入りに、(4) 目安 10 本、を書いた（条件の根拠は new-user-reco-threshold）
- 「アカウント・記録」は、移行の途中で Worker がメニューに差し込んでいた、古い /migration-data/ のページへのリンク（HTMLRewriter）。新しい「アカウント」があるので外した。スマホでは検索窓と同じ行に並んでいたので、外した分だけ検索窓が広がる（.side .search は flex:1）。/migration-data/ のページ自体はパスキーの設定のために残す。ログインの画面の削除の説明は「設定」の「書き出す」を指すように直した
- アイコン画像: ブラウザで真ん中を正方形に切り抜き 160×160 の WebP（書けない端末は JPEG）にして、本人の設定（app_setting 'avatar'）に data: URL で置く。サーバーは 60,000 文字まで、先頭のバイトが WebP・JPEG・PNG のものだけ受ける（SVG は受けない）。アカウントの保存だけ本文の上限を 64KB にした。試しの 1 枚は 1,887 文字。300 人でも最大 18MB で、D1 の無料枠に響かない
- 開幕リマインド: 題名で畳んだ 1 公演（.dgfold）を角丸の枠にし、題名・開いた中身・三択ボタンを同じ枠に入れた。題名の下の線は、日付の見出しの書式（.dgday summary）が題名の行にも掛かっていたのが原因だった
- ミス・サイゴンの「桐山照史（以上」「交互出演）」: お気に入りに足す名前は、画面側が出演欄を「、」で切っていた。括弧の中の注記（「（以上、交互出演）」）を先に外してから切るようにした（web/app.js splitCast）
