---
id: dec-free-tier-audit-fixes-1018
type: decision
status: adopted
date: 2026-10-18
title: 共通の数えを見ずに使っていた 6 か所に上限を足す（修正依頼の片付け・ポスターのやり直し・控えの入れ物の確かめ・予行の D1 と Actions・管理画面の R2 の保存・state を取り出せないとき）
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/docs/free-tier-audit-2026-10-18.md
links:
  - depends_on: free-tier-audit-1018
  - supports: dec-free-tier-only
  - affects: dec-fix-request-retention
  - affects: dec-d1-backup
  - affects: impl-admin-tool
  - raises: q-crawler-template-sync-1018
---
issue #139 の点検（free-tier-audit-1018）で見つかった穴のうち、小さく安全に直せるものを直した。上限を緩めたものは無く、3 つ足した。

- 修正依頼の片付け（purgeFixRequests）: 本文・行それぞれ 1 回 500 件まで（`free-tier.js` の `FIX_PURGE_PER_RUN`）。最悪の日の書き込みが 約 8,000 行から 約 2,000 行に下がる。残りは次の日
- ポスターのやり直し（deliver_posters.py）: やり直しの 1 回ごとに Class A の上限を見る
- 控え（backup_d1.py）: 入れ物の確かめ（作る・lifecycle の PUT を Class A 2、GET を Class B 1）を送る前に数え、上限の手前なら控えを作らない
- 戻す予行（backup_d1.py drill）: 新しい D1 への書き込みの見込み（行 ×（1＋索引の数））が `CAPS["drill_d1_writes"]`（1 万行）を越えたら D1 に入れず、手元の SQLite で開けて数が合うかだけを確かめる（警告を出す）。Actions も `free_tier.py plan --mode drill` で 20 分が残るときだけ（雛形 restore-drill.yml）
- 管理画面（tools/admin）: R2 の保存に `CAPS["admin_r2_bytes"]`（0.5 GB）。控えが取得と別なので、足して 8.5 GB に収める
- 取得のジョブ（雛形 catalog.yml）: state ブランチがあるのに取り出せない・有無が分からないときは、初回として続けずに止める

雛形の 2 つは本番の taguri-crawler に写すまで効かない（q-crawler-template-sync-1018）。
