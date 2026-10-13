---
id: comp-state-storage
type: component
status: current
date: 2026-10-13
title: 利用者の保存先とバックアップ
sources:
  - tools/lib/taguri_state.py
  - tools/taguri/state_backup.py
  - docs/demo-state-storage.md
---
`TAGURI_STATE_DIR` に認証・記録・推薦露出の DB を置く。停止中に一組で退避・復元する（state_backup.py）。
