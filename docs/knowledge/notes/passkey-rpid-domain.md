---
id: passkey-rpid-domain
type: finding
status: confirmed
date: 2026-10-13
title: パスキーはドメインに結び付くので、ドメインを変えると使えなくなる
sources:
  - https://github.com/island-6848/taguri-demo/blob/cloudflare-d1-preview/cloudflare/README.md
links:
  - affects: q-domain
  - supports: dec-own-domain
verifies:
  - S04
---
Workers 版のパスキーの RP ID はアクセスされたホスト名。workers.dev で始めて後から独自ドメインに移ると、利用者は復旧コードか Google でログインし直してパスキーを足し直す必要がある。
