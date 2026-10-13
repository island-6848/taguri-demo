---
id: render-free-spin-down
type: finding
status: confirmed
date: 2026-10-13
title: Render の無料プランは 15 分でスリープし、起動に約 1 分かかる
sources:
  - https://render.com/docs/free
  - https://render.com/docs/faq
links:
  - supports: dec-vm-cloudflare
  - supports: dec-demo-stays-render-free
---
受け取りが 15 分無いと止まり、次の要求で約 1 分かけて起きる。月 750 時間の無料枠を使い切ると月末まで止まる。
