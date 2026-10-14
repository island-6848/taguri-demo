---
id: corich-no-playguide-field
type: finding
status: confirmed
date: 2026-10-14
title: CoRich の公演ページの表にはプレイガイド（券の販売先）の欄が無い。名前が料金の欄の文に 1 割ほど出るだけ
sources:
  - https://github.com/island-6848/taguri-crawler/tree/state
links:
  - supports: dec-recommend-ui-1014
---
取得の作業データ（taguri-crawler の state ブランチの review/candidates.jsonl、2026-10-14 に読んだ。これからの公演 1,353 件の表）を数えた。欄の名前は 期間・劇場・出演・演出・料金（1枚あたり）・公式／劇場サイト・タイムテーブル・その他注意事項・スタッフ など。券の販売先の欄は無い。「ぴあ」「ローソンチケット」「イープラス」「カンフェティ」「teket」などの名前は、料金の欄（80 件）・スタッフ・その他注意事項に文として出るだけで、販売先の URL は料金の欄に stage.parco.jp が 9 件ある程度。各公演のプレイガイドのページへ直接つなぐには、公式サイトを読みに行く必要がある（取得の量と相手のサイトへの負担が増えるので、今はしない）。
