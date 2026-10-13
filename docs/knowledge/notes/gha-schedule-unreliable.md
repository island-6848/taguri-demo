---
id: gha-schedule-unreliable
type: finding
status: unverified
date: 2026-10-13
title: GitHub Actions の定期実行は遅れたり、混雑時に飛ばされたりする
sources:
  - https://upptime.js.org/blog/2021/01/22/github-actions-schedule-not-working/
  - https://itime.day/articles/github-actions-cron-delays
links:
  - affects: q-crawler-host
verifies:
  - S23
---
毎時 0 分付近は混み、数分〜30 分以上遅れることがある。まれに実行されない日もあるという報告がある。対策は、0 分を避ける・手動でも起動できるようにする・飛ばされたら気付ける監視を置くこと。
