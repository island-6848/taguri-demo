---
id: dec-d1-remote-permission
type: decision
status: adopted
date: 2026-10-24
title: Claude のクラウドのセッションに、本番の D1 への wrangler d1 execute（taguri-demo --remote）だけを許可する（.claude/settings.json の permissions.allow）
sources:
  - .claude/settings.json
links:
  - affects: q-miss-saigon-cast
---
起案者の指示（2026-10-24）「このルールを足して」。ミス・サイゴンの出演の差し替え（q-miss-saigon-cast）で、本番の D1 を読む操作が Auto のモードの自動の判定で止められたため。

- 足したルール: `Bash(npx wrangler d1 execute taguri-demo --remote:*)`。本番の D1 を読む・書くのは、このコマンドだけ
- 許可しないもの: デプロイ（wrangler deploy）・R2・ほかの D1・本番のほかの操作。今までどおり、そのつど止まる
- 効くのは、このファイルが master に入ってから始めたセッション（クラウドのセッションは始まるときにリポジトリの .claude/settings.json を読む）。足したセッションに効くかは確かめていない
- 使い方の約束: 書く前に、何を・どの行に書くかを起案者に伝えて、よいと言われてから書く。読むのは調べものとしてそのまま行う
- 無料枠: D1 の読み書きは無料枠（1 日 500 万行の読み出し・10 万行の書き込み）に数えられる。行を絞って引く（全部の行をなめる問い合わせをしない）
