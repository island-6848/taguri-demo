---
id: dec-app-release-costs
type: decision
status: adopted
date: 2026-10-20
title: アプリをストアに出す登録料（Apple 年 99 米ドル・Google Play 1 回 25 米ドル）は起案者が負担する。ほかは無料枠のまま
sources:
  - docs/free-tier-budget.md
  - CLAUDE.md
links:
  - answers: q-app-direction
  - depends_on: f-app-store-fees
  - affects: dec-free-tier-only
---
起案者の指示（2026-10-20）「本格的に配信リリースするときの経費は負担する。アプリにしたい。」

- 無料の約束（dec-free-tier-only）の例外は、ストアに出すための登録料だけ。払うのは起案者
- サーバー・保存・定期実行・通知の送信は今までどおり無料枠の中。独自ドメイン・有料のビルドサービス・有料プランなどは、起案者がはっきり指示するまで使わない・勧めない
- 進め方の計画は〔plan-app-release〕
