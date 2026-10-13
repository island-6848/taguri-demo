---
id: cf-registrar-no-jp
type: finding
status: unverified
date: 2026-10-13
title: Cloudflare Registrar では .jp を取れない。DNS だけ Cloudflare に置くことはできる
sources:
  - https://dev.classmethod.jp/articles/cloudflare-registrar-transfer/
  - https://www.issoh.co.jp/tech/details/17851/
links:
  - affects: q-domain
verifies:
  - S04
---
日本語の解説記事が一致してそう書いている。.jp は国内の登録事業者で取り、ネームサーバーを Cloudflare に向ければ Tunnel は使える。Cloudflare Registrar を使うと DNS は Cloudflare 固定になる。
