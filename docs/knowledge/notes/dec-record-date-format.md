---
id: dec-record-date-format
type: decision
status: adopted
date: 2026-10-24
title: 利用者の記録の日付は、どの画面も「2026.10.13(水) 13:00」の形にする（時刻は分かるときだけ）
sources:
  - cloudflare/src/screens/row.js
  - cloudflare/src/screens/cards.js
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/settings.js
  - cloudflare/src/screens/trace.js
  - cloudflare/src/screens/people.js
  - tools/taguri/charts.py
links:
  - supersedes: dec-diary-collage
---
起案者の指示（2026-10-24）「全ページ共通でユーザが追加した公演記録の日付の表記、2026.10.13(水) 13:00表記を採用して」。

- 形を 1 か所（row.recDate、Python は charts.rec_date）にまとめ、記録の日付を出すところを全部これにした: 日記帳・評価一覧・未評価・探すの行、まとめた回の一覧、購入済の「行く日」、感想の評価待ち、行かなかった公演、観た公演をつなぐ糸、人のつながりの時間の軸
- 10-18 の「yyyy/mm/dd(曜日)」（日記帳・評価一覧・探す）と、ほかの画面の「2026年10月13日」「11月3日」を撤回して 1 つにそろえた
- 行の開演の時刻は、会場の横の「13:00 開演」をやめて日付の後ろに書く（同じ時刻を 2 度書かないため）
- 公演の会期・カレンダーの升・開幕リマインドなど、公演そのものの日程（利用者の記録ではないもの）は変えていない
