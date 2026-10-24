---
id: find-wikipedia-member-categories-1024
type: finding
status: confirmed
date: 2026-10-24
title: 日本語版 Wikipedia の分類から、宝塚歌劇団の在団・退団者 833 名と STARTO・旧ジャニーズの人 383 名の名前を集めた。手元の出演欄と合うのは 345 名と 166 名で、これからの公演の札は 宝塚 74→131 件・STARTO 26→66 件に増える
sources:
  - https://ja.wikipedia.org/wiki/Category:宝塚歌劇団
  - https://ja.wikipedia.org/wiki/Category:STARTO_ENTERTAINMENT所属者
  - https://ja.wikipedia.org/wiki/Category:過去のジャニーズ事務所所属者
  - tools/review/collect_affil_wikipedia.py
  - cloudflare/scripts/affil_members.json
links:
  - answers: q-affil-external-list
  - affects: dec-member-affil-tag
  - depends_on: find-takarazuka-starto-coverage-1024
---
起案者の答え「b,c でお願い」（2026-10-24）の b（Wikipedia）。c（公式サイト）は使えなかった〔find-starto-robots-no-claude-1024〕〔find-kageki-unreachable-1024〕。

**取り方**
- MediaWiki の API は、この環境の IP（共用）では 429 で断られた。Retry-After に従っても、1 時間に 61 回断られてほとんど進まなかった。
- 普通の分類のページ（HTML）は読めたので、3 秒おきに 209 の分類を読んだ。控えを書くので、途中から続けられる。
- 本文は読まず、使っていない。分類に載った記事名（人の名前）だけを抜き出した。
- 名前の形（漢字・かなで 2〜8 字）に合うものだけを残した。曲名・番組名の多くはここで落ちる。残っても、出演欄の名前と合わなければ効かない。
- Wikipedia の文章は CC BY-SA 4.0。出典は affil_members.json の source に書いた。

**分類**
- 宝塚: 「宝塚歌劇団N期生」（1〜112 期、記事のある人だけ）。在団と退団を分けない。
- STARTO: 「STARTO ENTERTAINMENT所属者」「過去のSTARTO ENTERTAINMENT所属者」「過去のジャニーズ事務所所属者」「ジャニーズJr.」「関西Jr.」と、グループの分類（今と過去のポップ・グループ、37 分類）。
  - 人ごとの分類（「坂本昌行」など、人物別のトピックス）は使わない。配偶者や出た番組が入るため。初めの集計では、朝海ひかる（宝塚 OG）と宮沢りえが STARTO に入っていた。

**結果（作業データ 2026-10-22 の過去 30,633 件・これから 4,766 件と照らした）**

| | Wikipedia の名前 | 出演欄と合った人 | 手元の一覧に無く、新しく入った人 | これからの公演の札 |
|---|---|---|---|---|
| 宝塚歌劇団 | 833 | 345 | 202 | 74 → 131 件 |
| STARTO | 383 | 166 | 107 | 26 → 66 件 |

- 新しく入った宝塚の人の例: 天海祐希・一路真輝・大地真央・柚希礼音・望海風斗・明日海りお。2021 年より前の退団者が入った。
- 新しく入った STARTO の人の例: 岡本健一・森田剛・堂本光一・草彅剛・風間俊介・生田斗真。

**分からないこと**
- 記事の無い人（下級生・Jr. の多く）は入らない。
- 同じ名前の別の人がいれば、間違って札が付く。数は確かめていない。
- TOKIO・嵐の分類は 3 段目にあり、たどっていない。ただし主な人は「過去の所属者」の分類に入っている。
