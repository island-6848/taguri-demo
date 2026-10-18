---
id: impl-lockfile-repro
type: finding
status: confirmed
date: 2026-10-18
title: cloudflare に package-lock.json を入れ、CI を npm ci・配信の束の作り直しの一致・npm audit にした。本番の鍵で動く wrangler も lockfile の版にそろえた
sources:
  - https://github.com/island-6848/taguri-demo/issues/131
  - cloudflare/package-lock.json
  - cloudflare/package.json
  - .github/workflows/cloudflare-preview-check.yml
  - cloudflare/scripts/wrangler_pin.py
  - tools/taguri/deploy/github-actions/catalog.yml
  - docs/cloudflare-security-review.md
links:
  - depends_on: sec-audit-1017
---
issue #131（〔sec-audit-1017〕より前の点検の S4・T2）。

## したこと
- `cloudflare/package-lock.json` をコミットした（2026-10-18 に npm 10.9 で新しく入れて作った。wrangler 4.151.1・esbuild 0.28.2・firebase 13.0.0）。束を作る esbuild を devDependencies に版を固定して足した（前は wrangler の部品として入っていたものを使っていた）。
- **新しく入れた部品で `npm run build:login` をやり直すと、`public/vendor/` の 5 つの束と LEGAL.txt が 1 バイトも違わなかった**（この作業で確かめた）。手元の古い node_modules（別の @firebase/util）で作ると LEGAL.txt の並びが変わる。だから lockfile が要る。
- CI（`cloudflare-preview-check.yml`、プルリクエストのとき）：
  - `npm install` を `npm ci` にした。setup-node の npm の控え（cache）を lockfile で使う。
  - 束を作り直し、`git diff --exit-code -- public/vendor` で一致を確かめる。
  - `npm audit --omit=dev --audit-level=high`（利用者の画面と Worker に入る部品）で止める。2026-10-18 は 0 件。
  - 開発だけの部品まで含めた `npm audit` は、警告を出すだけ。2026-10-18 は high が 4 件で、すべて firebase の Firestore が使う `@grpc/grpc-js`（Node のサーバー側の部品）。ログインの束（Auth だけ）には入らない。直すには firebase の版を変える必要があり、今回はしていない。
- 本番の鍵で動く wrangler：`tools/admin/admin.py` と `cloudflare/scripts/backup_d1.py` は `wrangler_pin.wrangler_cmd()` を使う。`cloudflare/node_modules` に lockfile と同じ版があればそれを（`--no-install`）、無ければ lockfile の版を名指しで取る。`catalog.yml`（雛形）も `npx --yes wrangler@<lockfile の版>` にした。

## 使う量（Actions の分）
- 足した段は、束の作り直し（1 秒ほど）・`git diff`・`npm audit` 2 回（数秒ずつ）。合わせて 1 回 0.1〜0.2 分ほど増える見積もり。`npm ci` は控えから入れるので、前の `npm install`（毎回版を解決していた）より速くなる見込みで、差し引きはほぼ 0。このワークフローは公開リポジトリのプルリクエストのときだけ動く（公開リポジトリの GitHub の標準のランナーは無料）。
- `catalog.yml` は `npm ci` をせず、版を読む 1 段（`node -p`、1 秒足らず）だけ。非公開リポジトリの 1,500 分の上限には、ほぼ影響しない。

## まだのこと
- `npx --yes wrangler@<版>` で取るときは、wrangler 自身の版は固定されるが、wrangler の部品の版は npx が決める。部品まで固定するには、取得のジョブでも `npm ci` が要る（毎日 30 秒ほど増える）。今はしていない。
- `catalog.yml` は雛形なので、非公開リポジトリ（taguri-crawler）の写しを起案者が差し替える必要がある。
- Cloudflare の Workers Builds が lockfile を見て `npm ci` 相当で入れるかは、公式の文書で確かめていない（unverified）。
