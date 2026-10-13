---
id: q-crawler-repo
type: question
status: open
date: 2026-10-13
title: 取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定
links:
  - depends_on: dec-crawler-gha-private
verifies:
  - S23
  - S24
---
起案者が非公開リポジトリ island-6848/taguri-crawler を作り、秘密（S3 の書き込み用の鍵・バケット名・Gemini の鍵）を入れる。中身（.github/workflows/catalog.yml）は公開リポジトリの tools/taguri/deploy/github-actions/ に用意した。
実際に GitHub Actions の上で取得が最後まで通るか（所要時間・取得元に断られないか・GitHub の共有アドレスからの接続でよいか）は未確認。
2026-10-13、起案者がリポジトリを作った。秘密は要らなくなった（作業データは state ブランチ、GITHUB_TOKEN だけで足りる）。Claude の GitHub アプリの対象に足してもらえば、中身を入れられる（claude-app-repo-access）。
2026-10-13 13:03 UTC、Claude の GitHub アプリの許可が済み、taguri-crawler の main にワークフローを入れて、初回（weekly）を手動で起動した（https://github.com/island-6848/taguri-crawler/actions/runs/38402020387）。
