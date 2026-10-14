---
id: reco-plan-unmerged
type: finding
status: confirmed
date: 2026-10-13
title: 推薦の計算を改善する計画書はあるが、master に入っておらず内容が一部古い
sources:
  - https://github.com/island-6848/taguri-demo/blob/docs/personalized-recommendation-plan/docs/personalized-recommendation-plan.md
links:
  - affects: comp-recommender
  - raises: q-reco-eval-harness
---
docs/personalized-recommendation-plan.md（ブランチ docs/personalized-recommendation-plan、352 行）。本人の人物実績＋感想の観点＋あらすじの意味的な近さ（SBERT）を足し合わせる案を最初の比較候補にし、P0〜P3 の段階、検証 V01〜V25・Q01〜Q12（主指標は時系列で分けた NDCG@10、学習曲線は独立作品 5/10/20/40 件）、比べる構成 B0〜B6 を決めている。古い master から分かれたため、§2 の現状表は、その後に master で入った本人の評価の反映・由来の列・接触ログと合わない。再現・実利用での比較はすべて未実施。
