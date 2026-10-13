---
id: workers-free-cpu-10ms
type: finding
status: confirmed
date: 2026-10-13
title: Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで
sources:
  - https://developers.cloudflare.com/workers/platform/pricing/
links:
  - supports: dec-defer-workers
  - answers: q-workers-free-viable
---
上限は毎日 0 時（UTC）に戻る。超えるとその種類の処理が失敗する。（公式ページの記述を検索結果の引用で確かめた。作業環境の通信制限でページを直接は開けていない）
