---
id: q-e2e-register-rework
type: question
status: open
date: 2026-10-19
title: 観劇記録の追加の画面を作り替えた PR #219・#220 のあと、e2e-walk の 13 段が落ちる。だれが e2e を新しい画面に合わせるか
sources:
  - cloudflare/test/e2e-walk.js
  - https://github.com/island-6848/taguri-demo/pull/219
  - https://github.com/island-6848/taguri-demo/pull/220
links:
  - depends_on: dec-sale-label-1019
---
手を入れていない origin/master（6cf2f19）で e2e-walk を流すと 54 段のうち 41 段だけが OK（2026-10-19）。最初の NG は「観劇記録を手で 1 件足す」で、e2e は「登録しました」を待つが画面は「保存しました。」と出す。以後、記録が無いため評価・おすすめ・取り込みの段が続けて落ちる（取り込みは details.imx-src が 2 つに増えた）。#219・#220 は codex/ のブランチで、e2e は直していない。直すのは e2e の側（新しい画面の文言と並び）と思われるが、作り替えた側の意図を確かめてから。
