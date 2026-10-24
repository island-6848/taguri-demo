---
id: q-miss-saigon-cast
type: question
status: answered
date: 2026-10-24
title: ミス・サイゴンの出演者を、起案者が渡した一覧に差し替える（管理画面で起案者が入れる）
sources:
  - docs/owner/miss-saigon-cast.txt
  - tools/admin/admin.py
  - cloudflare/src/screens/override.js
links:
  - depends_on: impl-admin-tool
---
起案者の指示（2026-10-24）「ミス・サイゴンの出演者だけ以下に変更して」（エンジニア・キム・クリス・ジョン・エレン・トゥイ・ジジ・タムと、役名の無い 40 人）。

- 入れ方: 管理画面（tools/admin、admin.save）の「出演」の欄に入れると、stage_override.info.fields["出演"] に入り、Worker がカードと公演の詳細に重ねて出す（override.mergeInfo）。取得し直しても消えない
- 入れる文: docs/owner/miss-saigon-cast.txt。1 役 1 行で「役名：名前、名前」。役名の無い 40 人は、役名を付けずに最後の 1 行に並べる（はじめ「アンサンブル」と名付けたが、起案者の指示 2026-10-24「『アンサンブル：』不要」で外した）。credits.parseCredits で読むと 60 人の名前になり、役名は名前に混ざらない（確かめた）
- まだやっていない理由: Claude のセッションから本番の D1 を読む・書く操作は、許可の設定で止められた（2026-10-24）。どの公演（stage_id）が当たるかも見られていない。起案者が管理画面で入れるか、Claude に本番の D1 を扱う許可を出す
- 分からないこと: 推薦の材料（索引の出演者、rec_credit）は手入れの出演を使わない。おすすめの理由に出る名前は、次の取得で元の出演のままになる
