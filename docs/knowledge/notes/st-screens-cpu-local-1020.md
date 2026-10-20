---
id: st-screens-cpu-local-1020
type: finding
status: confirmed
date: 2026-10-20
title: 手元で測ると、「記録を見返す」（records）の画面は評価 200〜300 件で CPU が 10 ミリ秒の前後になる（ほかの主な画面は 5 ミリ秒以下）
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/scripts/st_measure_screens.mjs
  - https://github.com/island-6848/taguri-demo/blob/master/docs/verification/system-test-2026-10-20-prep.md
links:
  - affects: q-workers-cpu-real
  - supports: dec-system-test-design
---
システムテスト PF-01-02 の道具 `st_measure_screens.mjs` を作り、手元（このコンテナ、Node 22）の作り物の公演一覧（`--fixture`、6 公演）で 11 画面を測った。画面を Worker の入口から開き、プロセスの CPU から SQLite の中の CPU を引いた値。

分かったこと（リポジトリのコードと実行結果）:
- 評価 0・20 件では、どの画面も真ん中の値が 2.4 ミリ秒以下
- 評価 200 件: records が 7.1〜12.3 ミリ秒（2 回測って揺れた）、works・rate が 3.8 ミリ秒前後、ほかは 2.6 ミリ秒以下
- 評価 300 件: records 11.0（いちばん遅い回 21.7）、chronicle 9.3、works 4.2 ミリ秒
- 最初の 1 回（作り置きを作る回）は rate が 22 ミリ秒になることがある（V8 の最初の組み立てを含む）

分からないこと: Workers の本物の機械での値（こことは別の機械）。実カタログの索引（公演数千）では、推薦の載る画面がもっと重い見込み。測り直しは手順書 P-06 の 1（taguri-crawler で、起案者が流す）。records が実機でも 10 ミリ秒を越えるなら、図と同じくブラウザで組むか、件数で区切る必要がある。
