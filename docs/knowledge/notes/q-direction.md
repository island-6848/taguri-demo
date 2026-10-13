---
id: q-direction
type: question
status: answered
date: 2026-10-13
title: サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか
links:
  - depends_on: q-real-catalog-stats
  - depends_on: q-vm-host-choice
verifies:
  - S12
---
この作業では VM＋Cloudflare に決めたが（dec-vm-cloudflare）、別の作業で Workers＋D1 の版がかなり進んでいる（workers-d1-preview-state・python-workers-migration-state）。2 つを並行して進めると、削除・認証・推薦などを二重に作り、検証も二重になる。起案者が 1 つに寄せる。判断の材料: 費用（VM は回収・課金の心配、Workers は無料枠に収まるか q-real-catalog-stats）、残りの作業量、運用の手間（VM は OS の更新とバックアップ、Workers はほぼ不要）、Render を止められる時期。
答え: Workers＋D1 に寄せる（dec-workers-d1・dec-render-full-migration）。
