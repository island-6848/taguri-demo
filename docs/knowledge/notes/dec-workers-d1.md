---
id: dec-workers-d1
type: decision
status: adopted
date: 2026-10-13
title: 無料で起動を速くするため、Cloudflare Workers＋D1 で動かす
sources:
  - https://github.com/island-6848/taguri-demo/pull/5
links:
  - contradicts: dec-defer-workers
  - depends_on: workers-free-cpu-10ms
  - affects: comp-cf-worker
  - affects: q-direction
---
起案者が選んだ（「無料で起動時間早くするならどっち？」→ A）。Render 無料プランの休止からの起動待ちを無くすため。PR #5 の上で段階的に進める。
