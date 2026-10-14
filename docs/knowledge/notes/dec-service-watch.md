---
id: dec-service-watch
type: decision
status: adopted
date: 2026-10-14
title: サービス版の見張りは公開リポジトリの GitHub Actions で 1 時間ごと（動いているか）と毎日（カタログの日付）。失敗の通知は GitHub のメール
sources:
  - tools/taguri/check_service.py
  - tools/taguri/test_check_service.py
  - .github/workflows/service-watch.yml
  - .github/workflows/catalog-age.yml
links:
  - answers: q-monitoring
  - supports: dec-free-tier-only
  - depends_on: catalog-age-check
---
- 1 時間ごと（service-watch.yml）: `/api/health`（D1 を読む）・`/about`・`/login` が 200 で 10 秒より速いか、無料枠の数え（R2 の読み出し）が 8 割未満か。一度だけの通信の失敗では鳴らさない（30 秒おいて 3 回まで）
- 毎日（catalog-age.yml）: カタログの日付の上限を 3 日から 1 日にした。取得が 2 日続けて止まると 2 日目の朝に鳴る（S23「2 日以内に気付ける」）
- 費用: taguri-demo は公開のリポジトリなので Actions の分は無料。D1・R2 の無料枠の 8 割の見張りは取得の側（free_tier.py check）が毎日している
- 通知: 失敗した実行は GitHub がリポジトリの持ち主にメールで知らせる（定期実行の通知は、その cron を最後に変えた人に届く）
- 起案者がすること: リポジトリの変数 TAGURI_HEALTH_URL を入れる（入れるまで定期実行は動かない）。master に入ったあと、手動の実行で url に存在しない URL を入れて、メールが届くことを確かめる（S22 の「わざと鳴らす」）
- 見ていないもの: Worker のエラー率（無料で取れる通知が無い。画面のエラーは health と画面の 200 で代わりに見る）
