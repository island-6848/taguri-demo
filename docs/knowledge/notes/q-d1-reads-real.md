---
id: q-d1-reads-real
type: question
status: open
date: 2026-10-14
title: 本番で 1 人・1 日あたり D1 を何行読んでいるか（利用者 300 人の上限の前提）
links:
  - affects: dec-account-cap-counted
---
上限 300 人は「よく使う人 1 人が 1 日 3.5 万行読む・3 人に 1 人が毎日使う」という見積もりから出した。D1 は meta.rows_read を返すので、Worker で日ごとに足して（書き込みが増えないよう、r2Gate と同じく間引いて数える）/api/health に出せば実測できる。実測が出たら上限を見直す。
