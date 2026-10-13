---
id: scale-1000-estimate
type: finding
status: unverified
date: 2026-10-13
title: 1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/README.md
links:
  - supports: dec-scale-workers
  - affects: q-direction
  - depends_on: q-real-catalog-stats
verifies:
  - S20
  - S21
---
前提（推測）: 1 日に開く人 250 人、1 人 20 要求、評価などで推薦を計算し直すのが 1 人 1 日 3 回、1 回の計算で読むのは 5,400〜30,000 行。要求は 1 日 5,000 回ほど（全員が毎日 40 要求でも 4 万回）で、無料の 10 万回に収まる。推薦の計算は 1 回 10〜39 ミリ秒の見積もりで、無料の 10 ミリ秒を超えうる。D1 の読みは推薦だけで 1 日 400 万〜2000 万行になりうり、無料の 500 万行を超えうる。書き込みは、毎日の索引の入れ替えの行数次第（未測定）。有料プラン（月 5 ドル）ならどれも十分に収まる。VM（2 OCPU・12GB）なら 1000 人でも処理は足りる見込み。実カタログでの測定（q-real-catalog-stats）で確かめる。
