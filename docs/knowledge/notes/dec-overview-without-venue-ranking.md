---
id: dec-overview-without-venue-ranking
type: decision
status: adopted
date: 2026-10-19
title: 眺めるのよく行く劇場欄を削除する
sources:
  - cloudflare/src/screens/records.js
---
起案者の指定「『眺める』のよく行く劇場の欄消して」。recordsScreenのvenuePanelの呼び出しと未使用importを削除する。アカウント画面の劇場ランキングや観劇記録のデータには変更を加えない。新たな取得や保存は増えない。
