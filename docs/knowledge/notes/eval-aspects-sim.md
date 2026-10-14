---
id: eval-aspects-sim
type: finding
status: unverified
date: 2026-10-13
title: 作ったデータでは、気になった所を仮定どおりに付ける人には効き、でたらめに付ける人には害があり、裏の答え合わせはその害をあまり拾えない
sources:
  - cloudflare/test/reco-gate.test.js
links:
  - affects: impl-rating-aspects
  - depends_on: q-aspect-attribution-check
  - depends_on: dec-no-n1-evidence
---
作った利用者（出演 4 人・演出 1 人・料金の帯。評価は好きな出演者の数で決まり、高い公演の 7 割で「値段」を理由に 2 段下げる、各 200 人）。値段を付ける人では、6 件ずつの区切りで「使わない」版が勝ったのは 410、負けたのは 551（評価 60 件）で、使わない版に切り替わった人は 0。でたらめに付ける人では使わない版が 460 勝 348 敗と害が出るが、切り替わったのは 120 件でも 3.5%（区切りの差が小さい）。仮定どおりに動くことの確認であって、実際の観劇で良くなる証拠ではない（q-aspect-attribution-check）。観点ごとの評価と出演者の両方を持つ公開データは見つかっていない。
