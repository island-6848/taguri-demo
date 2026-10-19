---
id: dec-people-network-on-trace
type: decision
status: adopted
date: 2026-10-19
title: 一緒に出てくる人のネットワーク図はたどるの冒頭へ移す
sources:
  - cloudflare/src/screens/records.js
links:
  - affects: dec-overview-without-venue-ranking
---
起案者の指定「『眺める』の一緒に出てくる人の繋がり、のネットワーク図を『たどる』ページの冒頭に入れて」。たどるの見出しと記録件数の直後、名前を選ぶ説明・既存のたどる機能より前に置く。眺めるからは相関図の置き場所を削除する。既存のfigs-srcとdata-fig方式でブラウザに描画させるため、描画・選択機能は共通処理をそのまま使う。recordsBaseが既に読む本人のratedデータを使い、追加のDB・外部問い合わせや保存は増やさない。眺めるの劇場欄を削除したため、たどるの説明に残っていた劇場への案内も調整する。
