---
id: q-d1-user-writes-uncapped
type: question
status: open
date: 2026-10-18
title: Worker の D1 の書き込みの全体と、取得が書く前の D1 の大きさを数えるか
links:
  - depends_on: free-tier-audit-1018
  - affects: d1-free-limits
---
取得・管理画面・予行・定期実行の上限を足すと 1 日 約 9.35 万行（予行の無い日は 約 8.35 万行）で、利用者の操作に残るのは 約 6,500〜1.65 万行。利用者の書き込みには 1 人ずつの行の上限はあるが、1 日の全体の上限は無い。Worker の R2 の読み出しの数え（20 回に 1 回の書き込み）も、上限まで読む月は 1 日 約 5,000 行になる。越えるとその日の残りは D1 がエラーを返す（請求は無い）。取得は 19:17 UTC に動くので、利用者が先に使い切ると取得が入れられない。また取得の deliver_* は D1 の大きさを見ずに書く（Worker は 4 GB で止める）。案: Worker が meta.rows_written を間引いて usage に数え 8 割で増やす書き込みを止める。deliver_* の前に wrangler d1 info で大きさを読む。
