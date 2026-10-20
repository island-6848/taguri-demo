---
id: dec-system-test-plan
type: decision
status: proposed
date: 2026-10-20
title: 一般公開の前のシステムテストは、IPA の非機能要件の 6 観点に S01〜S35 を並べ直して行い、負荷・壊す試験はローカルと別の D1 だけ、本番は 1 日の使う量を決めた少しの確かめだけにする（起案者の承認待ち）
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/docs/system-test-plan.md
links:
  - depends_on: dec-free-tier-only
  - depends_on: dec-workers-d1
  - depends_on: e2e-walk-1018
  - depends_on: records-survive-1018
  - depends_on: dec-d1-backup
  - depends_on: dec-service-watch
  - affects: q-workers-cpu-real
  - affects: q-d1-migration-failure
  - affects: q-passkey-real-devices
---
計画書は `docs/system-test-plan.md`。決めたい中身:

- 観点: 機能要件（FN-01〜13、通し検証の段に結ぶ）と、IPA の非機能要件の大項目（可用性 AV・性能拡張性 PF・運用保守性 OM・移行性 MG・セキュリティ SC・システム環境エコロジー EN）。今ある S01〜S35 は各項目の「元」として結び、同じことを二度試験しない
- 「システム環境・エコロジー」の設置場所（温湿度・耐震・電圧）は、自前の機械が無いので対象外。動作環境（端末・ブラウザ・TWA）と、無駄な要求・計算・取得を減らすこと（＝無料枠を守ること）に読み替える
- 可用性は、無料枠に SLA が無いので「止まったら 1 時間以内に気付き、Time Travel（7 日）と毎日の控えで戻せる」を基準にする。RTO 4 時間は案
- 無料枠: 負荷・限界の試験は本番で行わない。本番の試験は 1 日に Workers 2,000 要求・D1 書き込み 2,000 行・読み出し 5 万行・R2 1,000 回まで。R2 の上限の試験はローカルだけ。試験の前後に `/api/health` の `free_tier` を見て、8 割を越えたら止める
- 日程（目安）: 準備 10/21〜、ローカル・CI 10/26〜、本番・別の D1 11/5〜、切り替え 11/10〜、ベータ 11/17〜12/14、判定 12/15 ごろ。画面の移行の終わり〔q-migration-owner〕に左右される

分かっていないこと: 起案者がこの日程・量・対象の動作環境・RTO を認めるか。承認されたら `adopted` にする。
