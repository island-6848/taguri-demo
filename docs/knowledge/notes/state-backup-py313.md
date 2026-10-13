---
id: state-backup-py313
type: finding
status: unverified
date: 2026-10-13
title: バックアップの検査が Python 3.13 では 1 件失敗する
sources:
  - tools/taguri/test_state_backup.py
links:
  - raises: q-python-version
  - affects: comp-state-storage
---
手元（3.13）ではログの 1 行が JSON として読めず失敗する。CI（3.12）では通る。原因は追っていない。
