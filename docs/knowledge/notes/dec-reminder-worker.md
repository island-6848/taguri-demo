---
id: dec-reminder-worker
type: decision
status: adopted
date: 2026-10-14
title: 開幕リマインドを Worker に移す（digest.panel を JS に移し、同じ入力で Python と同じ HTML になることを確かめる）
sources:
  - cloudflare/src/screens/reminder.js
  - cloudflare/src/screens/icons.js
  - cloudflare/scripts/write_icons.py
  - cloudflare/migrations/0019.sql
  - cloudflare/test/reminder.test.js
  - cloudflare/test/screens/reminder_fixture.py
links:
  - depends_on: dec-lists-worker
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の 2 段目の前半。
- digest.panel（今週・来週の耳、日ごとに畳む、同じ地方のツアーを 1 行に、取得元の違う二重登録を 1 本に、未回答だけ三択、直近の観劇予定）と render_recommend.schedule_html・run_range を JS に移した。手で作った 11 公演（ツアー・二重登録・答え済み・券）で、県 4 通り × 週 2 通りなど 9 通りの出力が digest.panel と一字一句同じ（reminder.test.js）
- 候補は D1 の今の索引（rec_stage。取得が digest.all_candidates から作る）で、今日から 14 日のうちに初日が来るもの（migration 0019 で初日の索引を足した）。答えの状態は興味あり・お気に入り・購入済みと同じ振り分け（lists.js の buckets）
- 県の絞り込みはおすすめと共有（app_setting の recommend_prefs）。地図はまだ
- アイコンは tools/taguri/icons.py から scripts/write_icons.py で src/screens/icons.js に書き出し、icons.test.js がずれを見張る
無料枠: 画面を開くたびに、2 週間ぶんの初日の公演（索引で数百行まで）と、答え・券・お気に入りの照合（lists.js と同じ）を読む。
