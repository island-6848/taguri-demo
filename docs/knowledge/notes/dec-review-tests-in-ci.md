---
id: dec-review-tests-in-ci
type: decision
status: adopted
date: 2026-10-16
title: test_measure_nets・test_interest_roster・test_rate_performances を CI（recommendation-loop）で動かす。持ち主のデータが無いときは作った材料で試し、要るファイルが無い検査は名前を出して飛ばす
sources:
  - .github/workflows/recommendation-loop.yml
  - tools/review/test_rate_performances.py
  - tools/review/fixtures/performances.jsonl
links:
  - depends_on: review-tests-stale-1016
  - depends_on: github-actions-public-free
---
起案者の依頼（2026-10-16）「CI で動いているか確かめて、動いていなければ足して」。3 つとも、どのワークフローにも入っていなかった。そのため落ちていても気づかなかった。

- recommendation-loop.yml の「Person reasons name the works」の後に 3 段足した。tools/review/** を変えたときに動く
- test_rate_performances は `data/tickets/performances.jsonl` が無ければ `tools/review/fixtures/performances.jsonl`（8 回・仮の題名と劇場。同じ期間に 2 回・翌年の再演・セット券・これからの公演を含む）を読む。館の座標・区の境界・推薦の控え・クレジットの控え・メールの本文が要る検査は「-- 飛ばした」と理由を出して数えない。持ち主の端末では今までどおり本物の控えで全部試す
- 費用: 3 つ合わせて手元で 3 秒ほど。taguri-demo は公開リポジトリなので Actions は無料（github-actions-public-free）。無料枠の数え直しは要らない
