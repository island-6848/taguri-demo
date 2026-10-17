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
