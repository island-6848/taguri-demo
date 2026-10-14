---
id: dec-d1-backup
type: decision
status: adopted
date: 2026-10-14
title: D1 の控えは Time Travel（7 日）に加え、利用者の記録の表を毎日書き出し、gpg で暗号化して R2 に 30 日置く。月に 1 回、新しい D1 に戻す予行を自動で流す
sources:
  - cloudflare/scripts/backup_d1.py
  - cloudflare/test/test_backup_d1.py
  - tools/taguri/deploy/github-actions/catalog.yml
  - tools/taguri/deploy/github-actions/restore-drill.yml
  - docs/backup-restore.md
links:
  - answers: q-d1-backup
  - answers: q-offsite-backup
  - depends_on: d1-time-travel
  - supports: dec-free-tier-only
---
- 書き出すのは利用者の記録の表だけ。毎日作り直せる表とセッションを外す「除く一覧」の形にし、新しい表は自動で控えに入るようにした（入れ忘れで記録が漏れないように）
- 置く前に、書き出した SQL を手元の SQLite に読み込み、表ごとの行数を D1 と比べる。減っていれば置かない
- 暗号化は gpg の合言葉（AES-256）。合言葉は起案者が作って taguri-crawler の secret に入れ、別の場所にも控える。R2 には暗号化したものだけ。置き場所はポスターと同じ入れ物の backup/d1/（新しい入れ物を作る権限や手順を増やさないため。Worker の /img/ は「/」を含む名前を出さない）
- 動かす場所は非公開の taguri-crawler（ログに行数が出るため、公開の taguri-demo では動かさない）。毎日の取得のジョブの終わりに 1 回。R2 の保存量と書き込み回数は free_tier.py の数えに足す
- 予行（restore-drill.yml）: 毎月 1 回、いちばん新しい控えを開いて新しい D1 に入れ、行数を比べてから消す。本番の D1 には書かない
- 残る問題: 消した人の記録は控えに最大 30 日（Time Travel に 7 日）残る。戻したときに、その後に消した人が戻ってしまう〔q-restore-redelete〕
