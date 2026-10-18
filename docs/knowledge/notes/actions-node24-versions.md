---
id: actions-node24-versions
type: finding
status: confirmed
date: 2026-10-18
title: GitHub の公式アクションで Node.js 24 で動く版は checkout@v5・setup-node@v5・setup-python@v6・upload-artifact@v6・deploy-pages@v5・configure-pages@v6。upload-pages-artifact は v5 から中で upload-artifact@v7 を使う
sources:
  - https://raw.githubusercontent.com/actions/checkout/v5/action.yml
  - https://raw.githubusercontent.com/actions/setup-node/v5/action.yml
  - https://raw.githubusercontent.com/actions/setup-python/v6/action.yml
  - https://raw.githubusercontent.com/actions/upload-artifact/v6/action.yml
  - https://raw.githubusercontent.com/actions/deploy-pages/v5/action.yml
  - https://raw.githubusercontent.com/actions/configure-pages/v6/action.yml
  - https://raw.githubusercontent.com/actions/upload-pages-artifact/v5/action.yml
links:
  - affects: q-review-1015
---
各アクションの action.yml の `runs.using` を直接読んだ（2026-10-18）。node24: checkout@v5、setup-node@v5、setup-python@v6、upload-artifact@v6、deploy-pages@v5、configure-pages@v6。
node20 のまま: deploy-pages@v4、configure-pages@v5、upload-artifact@v4（v5 は既定が node20 という報告あり。v5 は読んでいない）。
upload-pages-artifact は composite で、v3・v4 は中で upload-artifact@v4（node20）、v5 は upload-artifact@v7 を使う。
taguri-demo の .github/workflows と雛形（tools/taguri/deploy/github-actions）をこの版に上げた（#71）。taguri-crawler は別のセッションが PR #6 で上げ済み。
GitHub 社のランナーが node24 を既定にする日付（2026-03-04 の予定）は検索結果の引用で見ただけ。
