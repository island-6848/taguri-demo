---
id: dec-calendar-worker
type: decision
status: adopted
date: 2026-10-14
title: 公演カレンダーを Worker に移す（stage_calendar.panel・観劇日を追加するを JS に移し、Python と同じ HTML になることを確かめる）
sources:
  - cloudflare/src/screens/calendar.js
  - cloudflare/src/screens/calendar_js.js
  - cloudflare/test/calendar.test.js
  - cloudflare/test/screens/calendar_fixture.py
links:
  - depends_on: dec-reminder-worker
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の 2 段目の後半。
- stage_calendar の rows_of・月の格子（土日の影・今日の線・帯・行く日の半券）・種類と都道府県の絞り込み・12 か月より先の注・「観劇日を追加する」の窓（作品ごとにまとめた会場と入れてある日）を JS に移した。手で作った 9 件・券 5 枚で、絞り込み 4 通りと追加の窓・空のときの出力が Python と一字一句同じ（calendar.test.js）
- 格子のあとに Python が置く <script>（stage_calendar.JS）も scripts/write_icons.py で書き出してそのまま置く（innerHTML で入れるので動かないが、HTML を Python と同じに保つ）
- 並べる公演は興味あり・お気に入り・購入済みと同じ振り分け（lists.js の buckets）。公演の期間・会場は D1 の今の索引（rec_stage.entry）から
- メールの取り込みは持ち主専用なので、「カレンダーに表示できていないチケット」の知らせは出さない
