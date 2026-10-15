---
id: impl-cast-seen
type: decision
status: adopted
date: 2026-10-15
title: 記録ごとに「観た回の出演者」を選べるようにした（Wキャスト・休演で出ていなかった人を外すと、推薦はその人をその記録の材料にしない）
sources:
  - cloudflare/migrations/0023.sql
  - cloudflare/src/screens/diary.js
  - cloudflare/src/screens/row.js
  - cloudflare/src/screens/recommend.js
  - web/app.js
  - cloudflare/test/cast-seen.test.js
links:
  - affects: q-theatre-differences
  - affects: impl-person-ordinal-v3
---
起案者の指示（2026-10-15）「Wキャストの出演者を選べるようにして」。docs/recommendation-concerns.md 3 章 B（同じ作品でも観た回で別物）への最初の手当て。
- works.cast_off（migrations/0023、JSON の名前の並び、空は全員を観た）。POST /api/cast_seen: {work_key} で公演の出演者（rec_people、無ければ past_stage の「出演」）といま外している人を返し、{work_key, off} で保存する。公演の出演者に無い名前・全員を外す・他人の記録は 400。保存で rec_cache を捨てる（updated_at は裏の答え合わせが評価の時刻に使うので動かさない）。観た公演のつながりを変えると空に戻す
- 記録を直す欄に「観た回の出演者」。押すと出演者のチェックが並び、外して保存する（出演者は押したときにだけ読む。画面を開くたびの読み込みは増えない）
- 推薦（screens/recommend.js ratedWorks）は、外した人を「出演」としてその記録の人物から除く
- まだのこと: 出演欄の書き方から Wキャストの組を見分けて先に示すこと、観た日の出演予定（キャストスケジュール）から自動で選ぶこと（取得のきまりの確認が要る）、眺める（人物の図）にも反映すること、旧い /migration-api の推薦
- 無料枠: 列 1 つ（1 記録あたり最大 200 名の名前）、押したときに D1 を 2〜3 行読むだけ
