---
id: q-crawl-in-session
type: question
status: open
date: 2026-10-22
title: GitHub Actions でしている取得（特に過去の公演の補完・ポスター・本文の長い実行）を、Claude Code のクラウドのセッションで代わりに動かすか
sources:
  - https://code.claude.com/docs/en/cloud-environments#network-access
links:
  - depends_on: find-catalog-stopped-1022
---
起案者（2026-10-22）「actionsでやってることをこのセッションで代替できる？」

**確かめたこと（このセッションの実行結果）**
- このセッションの環境のネットワークの決まりで、stage.corich.jp と api.cloudflare.com への接続が断られる（プロキシが CONNECT に 403）。npm の取得はできる。
- Cloudflare の鍵（CLOUDFLARE_API_TOKEN・CLOUDFLARE_ACCOUNT_ID）は、このセッションに無い。GitHub の secrets にあるだけ。
- taguri-crawler のリポジトリ（state ブランチを含む）は、このセッションから読み書きできる。

**動かすのに要るもの**
- 環境のネットワーク許可: stage.corich.jp、api.cloudflare.com、R2 の接続先。公式サイトからクレジットを取る段は取得先が多いので、広い許可が要る。
- 環境変数として Cloudflare の鍵を置く。
- Actions と同時に動かさない（state と無料枠の控え data/free_tier/usage.json を取り合う）。

**無料枠**
- Actions の分は使わない。D1 の書き込み・R2 は同じスクリプトの守り（free_tier.py）がそのまま効く。state を戻してから動かし、終わったら書き戻すことが条件。
- セッションは起案者の Claude の利用量を使う。有料のサービスは足さない。

**案**
- 毎日の更新は Actions のまま（定時・自動・ログが残る）にする。
- 枠を食っていた長い手動の実行（過去の公演・ポスター・本文）だけを、許可を足したセッションで動かす。
