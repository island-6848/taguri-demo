---
id: dec-merge-without-asking
type: decision
status: adopted
date: 2026-10-24
title: Claude が作った PR は、確かめが済んでいれば、起案者に聞かずに master へマージしてよい
sources:
  - docs/issues-workflow.md
---
起案者の指示（2026-10-24）「勝手にPRをmasterにマージしてよい」。issue の定期確認（docs/issues-workflow.md の「確認せずにマージする」）と同じ扱いを、ふだんの作業の PR にも広げる。

**マージしてよい条件**
- 手元の試験が通っている: cloudflare の node の試験、関わる Python の試験、`sync_public_ui.py --check`、`build_graph.py --check`。
- GitHub の CI の失敗が、この PR の変更によらないものだけ。例: 始まった秒に終わる「Workers Builds: app」。その場合は、PR に一度だけそう書いておく。
- マージの衝突が無い。

**変えないこと**
- 無料枠の決まり（CLAUDE.md）。使う量が増える変更は、数えてから入れる。
- 本番のデータを書き換える操作（D1・R2 への送信、大量の取得）は、別に起案者の確認を取る。
- マージのあとは、作業のブランチを master から作り直す（force push はしない）。
