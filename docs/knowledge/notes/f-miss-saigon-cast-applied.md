---
id: f-miss-saigon-cast-applied
type: finding
status: confirmed
date: 2026-10-24
title: ミス・サイゴンのツアー 5 会場（484535〜484539）の出演を、起案者の一覧に差し替えた（本番の D1 の stage_override、管理画面と同じ形）
sources:
  - docs/owner/miss-saigon-cast.txt
  - tools/admin/admin.py
links:
  - answers: q-miss-saigon-cast
  - depends_on: dec-d1-remote-permission
---
起案者の指示（2026-10-24）「ミス・サイゴンの出演者だけ以下に変更して」。本番の D1 を扱う許可（dec-d1-remote-permission）を足したあとに行った。

- 当たった公演（索引の今の版、題名から「・」を除いて「ミスサイゴン」を含むもの）: 484535 東急シアターオーブ（2026-10-16〜11-29）、484536 梅田芸術劇場メインホール（12-05〜12-17）、484537 福岡市民ホール（12-24〜12-27）、484538 アクトシティ浜松（2027-01-08〜01-11）、484539 札幌文化芸術劇場 hitaru（01-17〜01-24）。どれも手入れは無かった
- 書いたもの: 各公演の stage_override に info = {"fields": {"出演": docs/owner/miss-saigon-cast.txt の文}}（管理画面の admin.save・_clean_info と同じ形）。あらすじ・題材は触っていない。admin_log に 1 公演 1 行の変更の記録（by: Claude）。合わせて 10 文・D1 の書き込み 20 行
- 確かめたこと: 書いたあと読み直し、5 公演とも出演の欄が文と一字一句同じ
- 手元の管理画面の記録のファイル（data の admin log・無料枠の台帳）には、このセッションからは書いていない（手元のファイルが無いため）。D1 の admin_log には残っている
- 推薦の材料（索引の出演者）は元のまま。おすすめの理由に出る名前は、取得したデータの出演から出る
