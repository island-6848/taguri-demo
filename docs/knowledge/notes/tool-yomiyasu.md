---
id: tool-yomiyasu
type: decision
status: adopted
date: 2026-10-17
title: サイトの文章を yomiyasu（日本語の推敲スキル）で書き直す。スキルは .claude/skills/yomiyasu に入れた
sources:
  - https://github.com/nanaism/yomiyasu
  - .claude/skills/yomiyasu/SKILL.md
  - .claude/skills/yomiyasu/UPSTREAM
---
起案者「https://github.com/nanaism/yomiyasu これを使ってサイトの全部の文章を書き直して」（2026-10-17）。規約・プライバシーの説明も含める（起案者の回答）。
- yomiyasu: AI が書いた日本語の不自然な比喩・曖昧な主述・過剰な装飾を、意味を変えずに直す Claude 用のスキル（MIT ライセンス）。書き直したあと scripts/yomiyasu_check.py で、数値・否定・主語と目的語の入れ替えなどが変わっていないかを検査する（リポジトリの README と SKILL.md による。取得元そのものなので confirmed 扱い）
- 入れ方: skills/yomiyasu を .claude/skills/yomiyasu にそのまま写した（取り込んだ版は UPSTREAM）。検査の記録 .yomiyasu/ は .gitignore
- 書き直しの約束: 画面に出る文だけを直す（コメント・識別子・取得した文を読み分けるための語は変えない）。画面ごとの Python の写し（テストで HTML を比べている所）も同じに直す。規約は文言を直したら terms.js の TERMS_VERSION を上げる

追記（2026-10-18）: 書き直しを終えた。7 つに分けて並行で直し（画面の共通部分 app.js 15 か所／今週のおすすめ・カード・開幕リマインド・制覇マップ 36／興味あり・お気に入り・購入済み・探す・公演カレンダー 36／評価・日記帳 25／眺める・使い方の案内 28／ログイン・アカウント・設定・取り込み 34／規約・プライバシーの説明〔impl-terms-reagree〕）、どれも yomiyasu_check の verify を通し、全テスト（JS 241・Python）を通して master に入れた。自然な文は直していない（スキルの決まり）。
- 画面名・ボタン名・起案者が決めた言葉は残した。「回答ありがとうございました」の下のワンポイントは、起案者の指定（「１、過去の記録を追加する・・・」）どおり、やることを先頭に置く形（太字の見出し＋「：」）に戻した
- 残したこと・分かったこと:
  - 「A ── B」の見出し（「眺める ── 図で見る」など）は、サイト全体でそろえて決めることなので、多くはそのまま
  - テストで比べていない画面の Python の写し（tools/taguri/app.py・serve.py の一部。ローカルのデモ版）は古い文言のまま残っている所がある
  - tools/review/render_recommend.py の直し（カードのあらすじが取れないときの文など）は、取得の側がカードを作り直したあとに本番に出る
  - 評価・日記帳の画面の文が、実際の画面とずれている所が 2 つ見つかった〔q-rate-diary-copy-mismatch〕
