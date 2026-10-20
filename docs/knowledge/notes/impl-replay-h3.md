---
id: impl-replay-h3
type: decision
status: adopted
date: 2026-10-20
title: H3（観る前の点と観たあとの評価の Kendall τ）を replay_eval の h3 と Replay の Summary に足した。観なかった公演は負例にせず、欠測と選んで観た偏りを並べて出す（#114）
sources:
  - https://github.com/island-6848/taguri-demo/issues/114
  - tools/review/replay_eval.py
  - cloudflare/scripts/replay_job.py
  - cloudflare/test/test_replay_eval.py
  - docs/research/real-data-eval-plan.md
links:
  - answers: q-replay-h3-satisfaction
  - affects: impl-replay-eval
---
起案者「issuesまだ47個あるから古い順に対応してください」（2026-10-20）。

- **使い方。** `python3 tools/review/replay_eval.py backup.sql h3 [--owner U]`。Actions の Replay の Summary にも「観る前の点と、観たあとの評価（H3・#114）」として出る。
- **観る前の点。** 答えたときに記録した点（reaction.score。0029 から）を使う。
  - 再生で日 t の点を計算し直す方法は取らなかった。観た公演は終わった公演なので、今日の索引にはもう無いことが多く、計算し直せない。
  - 同じ公演に何回も答えたときは、観た日（works.first_date）より前の答えのうち、いちばん後のもの。観た日以降の答えは、観たことを知っている点なので使わない。
  - ツアーのほかの会場へ写した答え（source が _tour）は数えない（#110 と同じ）。
- **観たあとの評価。** works.verdict を ◎3・○2・△1・×0 にする。「まだ判断できない」と評価の無い記録は入れない。観なかった公演（記録の無い答え）は満足の負例にしない。
- **数え方。** 利用者ごとに Kendall の τ-b（同順位を補正）。結べた公演が 3 件未満の人は数えない。τ の中央値と、τ > 0 と τ < 0 の人数の符号検定。持ち主は別に出す。
- **並べて出す欠測と偏り。**
  - 評価のうち、公演につながっていない数、観る前の点が無い数。
  - 結べた公演のうち、観る前に興味あり・購入済と答えていた割合。満足を測れるのは、観ると決めた公演だけという偏りを示す。
- **H1 とは別に報告する。** H1 は興味（答え）、H3 は満足（評価）。推薦の計算は変えていない。D1 には何も足していない。
- **分からないこと。** 件数は少ない見込み（計画 §9）。点（score）の目盛りは版（ver）で変わるが、τ は 1 人の中の並びだけを見るので、同じ人の中で版が混ざる影響は確かめていない。
