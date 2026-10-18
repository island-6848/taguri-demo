---
id: fix-interest-tour-copies
type: decision
status: adopted
date: 2026-10-18
title: ツアーのほかの会場へ写した答え（reaction.source が '…_tour'）は、好みの手がかり（興味あり・興味なしの種）にも、手元の答え合わせ（replay_eval の logged）にも数えない。会場ごとの行は、答えた公演を外すため・一覧のために残す（#110）
sources:
  - https://github.com/island-6848/taguri-demo/issues/110
  - cloudflare/src/screens/recommend.js
  - tools/review/replay_eval.py
  - cloudflare/test/recommend-screen.test.js
links:
  - affects: impl-interest-split
  - affects: impl-replay-eval
---
issue #110（2026-10-18）: reactAction は押した答えをツアーのほかの会場（siblings、最大 40）へ source='…_tour' で写す。interestSeeds は公演ごとの最新の答えを全部種にしていたので、1 回の興味ありが会場の数だけの重さになり（issue の例で人物の値 0.197949 → 0.866025）、MAX_SEED_STAGES（60）も写しで埋まった。
- 直したこと: interestSeeds は、公演ごとの最新の答えが写し（'_tour'）なら種にしない（興味あり・行けない・興味なしとも）。最新の答えで決めるので、写しのあとにその会場を本人が直接押し直した答えは 1 件として数える。answered（おすすめから外す）・興味ありの一覧は会場ごとの行をそのまま使う
- 手元の答え合わせ（tools/review/replay_eval.py の logged）も、写しの行を正例・負例に数えていたので外した
- 残り: 写しではなく本人が同じ公演の別の会場を別々に押した場合は、まだ 2 件になる（公演の束 rec_stage.tour でまとめるには、種の公演の束を読む 1 回の読み出しが要る）。評価（works）は公演 1 つに 1 行で、写しは無い
- 画面の控えは screen-v24
