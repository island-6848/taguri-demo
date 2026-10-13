---
id: workers-static-assets-free
type: finding
status: confirmed
date: 2026-10-13
title: Workers の静的ファイルへの要求は無料・無制限で、要求数の上限に数えない
sources:
  - https://developers.cloudflare.com/workers/static-assets/billing-and-limitations
  - https://developers.cloudflare.com/workers/platform/pricing/
links:
  - affects: scale-1000-estimate
verifies:
  - S20
---
Worker のコードを動かす要求だけが数えられる。ただし `run_worker_first` で Worker を先に通す道は、無料枠を超えると静的ファイルにも落ちず 429 になる。Workers 版は `run_worker_first` を `/*` にして CSS・JS などだけを外している（ログインの関所のため）ので、画面の HTML は Worker の要求として数える。（公式ページの記述を検索結果の引用で確かめた。作業環境の通信制限でページを直接は開けていない）
