---
id: q-catalogue-python-snapshot-vs-d1
type: question
status: open
date: 2026-10-13
title: 移行ブランチの Python 版はカタログをコードの束に同梱する。D1 に毎日入れる作りとどう揃えるか
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-complete-migration/cloudflare/python/README.md
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-complete-migration/cloudflare/scripts/build_public_snapshot.py
links:
  - depends_on: dec-d1-catalogue-delivery
  - depends_on: dec-migration-owner-push
---
cloudflare-complete-migration ブランチ（別セッション、2026-10-13）の Python Workers 版は、承認済みの公開カタログを build_public_snapshot.py で作り、デプロイの束に同梱する（D1 には個人の記録だけを置く）。この作りだと、カタログを新しくするたびにデプロイが要る。
本番（master）の JS の Worker は catalogue 表を D1 から読むので、dec-d1-catalogue-delivery はそちらに合わせた。画面の移行を引き継ぐ（wip-screens-port を受け取る）ときに、画面がカタログを D1 から読むようにするかを決める。
