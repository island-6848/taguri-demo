---
id: peer-past-name-index
type: finding
status: unverified
date: 2026-10-16
title: 別のセッションが、過去の公演の「名前 → 公演」の索引を R2（taguri-posters の pastidx/v1/<xx>.json、256 個に分割）に置く段を取得に足す PR を出した（起案者の許可待ち）
links:
  - affects: dec-free-tier-only
---
相手のセッション（評価・画面側）の知らせ（2026-10-16 00:29 UTC）による。起案者の選択（案 A）。taguri-crawler の PR（ブランチ claude/past-name-index）で catalog.yml の「Deliver the new past stages to D1」の後に段を足し、taguri-demo の PR #32 の cloudflare/scripts/deliver_past_index.py が data/past/stages.jsonl の全行から名前（出演・作り手・団体）→ 公演の索引を作り、FNV-1a % 256 で分けて変わったものだけ PUT する。控えは data/r2/pastidx.json（SHA-256）。R2 の保存と Class A は free_tier.py の控えに足す。失敗しても先へ進み、script が無ければ何もしない。お気に入りのハッシュタグの画面が 1 回読むだけで過去の公演を出す。
- R2 は越えると請求される（dec-free-tier-only）。ファイル 256 個・変わったものだけなので Class A は 1 日最大 256 回、保存は数 MB の見込み（私の見積もり、PR の中身は読んでいない）
- catalog.yml を触るときは、この段を残す
