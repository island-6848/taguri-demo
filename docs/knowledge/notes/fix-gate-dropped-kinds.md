---
id: fix-gate-dropped-kinds
type: decision
status: adopted
date: 2026-10-18
title: 裏の答え合わせの点（reco-gate.stageScore）も、本番の点（scoreFromIndex）と同じく、使わなくなった種類（#値段・#会場・原作「原作もの」）を数えない。答え合わせを表示の計算とそろえる残り（本人の倍率・お気に入り・興味あり・1 段広げる）は測ってから（#115）
sources:
  - https://github.com/island-6848/taguri-demo/issues/115
  - cloudflare/src/reco-gate.js
  - cloudflare/test/reco-gate.test.js
links:
  - affects: impl-hidden-gate
  - raises: q-gate-matches-shown-ranking
---
issue #115（2026-10-18）: chooseVariant の答え合わせは personValues(過去) と自前の stageScore で採点し、stageScore は本番で外した #値段・#会場（DROPPED_AXES）も数えていた（issue の例で #値段だけの値 1 → 点 1）。
- 直したこと（小さな直し）: stageScore で droppedKind の種類を飛ばす。試験の人工利用者（「高い公演で値段に不満を付ける」人）は、値段の不満そのものは当てられなくなり、「詳細を使う」ほうの勝ち越しが 1.15 倍から 1 倍強に縮んだので、試験の閾値を「負けより勝ちが多い」に直した（詳細を使い続けることは全 60 通りで変わらない）
- 画面の控えは screen-v28
- 残り（測ってから決める、〔q-gate-matches-shown-ranking〕）: 本人の効かせ方の倍率・お気に入り・興味あり・1 段広げる・表示の選別を、答え合わせに入れるか
