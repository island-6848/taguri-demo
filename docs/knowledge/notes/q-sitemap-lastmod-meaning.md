---
id: q-sitemap-lastmod-meaning
type: question
status: open
date: 2026-10-21
title: CoRich のサイトマップの lastmod は、出演者の追加・日程の変更など公演ページの中身が変わったときに進むか。進まないなら、持っている公演の変更の確認（優先度 3）を別の方法で補う
sources:
  - tools/review/fetch_candidates.py
links:
  - raises: dec-crawl-tiers
  - affects: corich-sitemap-stage-ids
---
dec-crawl-tiers は、lastmod が前回より新しいこれからの公演だけを読み直す。corich-sitemap-stage-ids の時点（10-13）では、「lastmod が公演の更新を表すか」は未確認のまま。
- 確かめ方: 取り直しのログの「更新日が変わったこれからの公演 N 件」と、読み直した公演のクレジットが実際に変わった件数を、1〜2 週間ぶん比べる
- 進まないと分かったら: 週 1 の取り直しで、これからの公演のうち初日が近いものだけを読み直す、などを考える
