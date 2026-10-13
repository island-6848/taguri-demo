---
id: q-catalog-source
type: question
status: open
date: 2026-10-13
title: 今の公演カタログ（S3）は、いつ・どこで作られたものか
links:
  - depends_on: q-crawler-host
verifies:
  - S23
---
EC2 が無いので、毎日の更新は止まっているはず。カタログの日付（manifest.json）を確かめ、古ければ新しく作る場所を決める（q-crawler-host）。作業環境からは S3 に入れないので、起案者か Render のログで確かめる。
