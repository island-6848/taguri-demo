---
id: dec-records-notes-trim-1024
type: decision
status: adopted
date: 2026-10-24
title: 眺めるの劇場制覇マップの下の注（数えている劇場の決め方）と、観劇の時間割の上の説明の文を消す。時間割の「時刻なし」の列は、時刻の分からない回が無ければ出さない
sources:
  - cloudflare/src/screens/conquest.js
  - cloudflare/src/screens/timetable.js
  - cloudflare/test/timetable.test.js
  - cloudflare/test/conquest.test.js
links:
  - affects: dec-storyline-title-scroll
---
起案者の指示（2026-10-24）: 劇場制覇マップの「その県の劇場として数えているのは、たぐりが集めた公演…に 2 回以上出てきた会場です。…」を削除。観劇の時間割の「観た回を曜日と開演の時刻…で数えています。いちばん多いのは…。開演時刻が分かるのは…」を削除。「時刻なしの列は1件もなければ非表示」。

- 劇場制覇マップ: 下の注の段落を消した。数え方（venue_census の 2 回以上の会場、ホールは分ける、数に無い劇場に行けば足す）はコードの冒頭のコメントと前の決定に残る
- 観劇の時間割: 上の説明の段落を消した。いちばん多い曜日・時間帯の計算もやめた（出す所が無くなったため）。列の見出しの title（「15 時より前」など）は残るので、押さえれば区切りは分かる
- 時刻なしの列: 時刻の分からない回が 1 回も無ければ、見出し・各行の升を出さない。各行の「計」は前のまま全部の回を足す（時刻なしが無いので同じ数）。表の読み上げの説明も、出している列だけを並べる
- 試験: timetable.test.js（説明の文が無い・時刻なしの列が有るときと無いとき）、conquest.test.js（注の文が無い）。npm test が通る
