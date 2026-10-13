---
id: impl-hidden-gate
type: finding
status: confirmed
date: 2026-10-13
title: 裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）
sources:
  - cloudflare/src/reco-gate.js
  - cloudflare/src/worker.js
  - cloudflare/test/reco-gate.test.js
links:
  - answers: q-hidden-gate
  - depends_on: impl-person-ordinal-v3
  - depends_on: lit-prequential
  - depends_on: lit-safe-improvement
  - affects: comp-recommender
---
予想点を保存する代わりに、推薦を計算するたびに本人の評価を付けた順に再生する（保存も送信もしない）。直近 120 件を 6 件ずつの区切りに分け、各区切りをそれより前の評価だけで採点し、区切りの中で本人が違う評価を付けた組（同じ段階どうし）を今の計算と別の計算のどちらが多く本人の順に並べたかで勝ち負けを付ける。区切りの勝ちが負けより十分に多い（片側の符号検定 z ≥ 1.96、決着した区切り 6 以上）ときだけその計算を使う。別の計算は役職のまとめごとの効かせ方: 公演の種類 2 倍（kinds_strong）、演出・脚本 2.5 倍（author_strong）。どちらも公開データでは決めきれなかった選択（eval-design-choices）。結果の variant は応答に入るが画面には出さない。Render の Python 版には入れていない。作った利用者での動き: eval-hidden-gate-sim。
