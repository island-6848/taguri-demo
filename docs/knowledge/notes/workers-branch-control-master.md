---
id: workers-branch-control-master
type: finding
status: unverified
date: 2026-10-14
title: 起案者が Workers Builds を master だけ組み立てるようにした
links:
  - affects: workers-preview-build-log
---
起案者の報告（2026-10-14「masterだけにしてる」）。画面は見ていない。これで master 以外のブランチの組み立て（wrangler preview で失敗していたもの）は走らなくなり、コミットの ✗ も出なくなるはず。次に作業ブランチへ押したとき、check-runs に Workers Builds が出ないかで確かめる。
