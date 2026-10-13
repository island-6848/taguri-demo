---
id: dec-render-full-migration
type: decision
status: adopted
date: 2026-10-13
title: Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/docs/render-migration-plan.md
links:
  - contradicts: dec-defer-workers
  - contradicts: dec-vm-cloudflare
  - depends_on: render-ui-server-rendered
  - affects: comp-native-screens
  - affects: comp-public-server
  - affects: q-direction
---
起案者の指示（「render いらないなら完璧に移行してもよい」）。画面は Python と同じ HTML を出すように 1 枚ずつ JS に移し、全部そろってから本番で切り替える。持ち主専用の機能（メール取り込み・Gemini）は EC2 に残す。
2026-10-13、EC2 は無いと分かった（no-ec2）。持ち主専用の機能は、持ち主のパソコンの run.py に残すのが自然。
