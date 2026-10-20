---
id: f-corich-title-parts
type: finding
status: confirmed
date: 2026-10-20
title: CoRich の公演ページの見出しは 冠名（p.crown）→ タイトル（h1.name）→ サブタイトル（p.subTitle）。<title> にはタイトルしか入らず、控えの 6,000 件で冠名は 4,092 件・サブタイトルは 969 件にあった
sources:
  - https://github.com/island-6848/taguri-crawler/tree/state/credits/pages
  - https://github.com/island-6848/taguri-demo/blob/master/tools/credits/fetch_credits.py
links:
  - affects: dec-title-crown-subtitle
---
起案者の指摘（2026-10-20）「CoRich の公演タイトル、冠名→タイトル→サブタイトルで入力欄があるんだけど、今タイトルの部分しか拾えてないものがある」。

- 取得の控え（taguri-crawler の state ブランチ credits/pages、公演ページ 6,000 件）を読んだ。見出しは `<div class="mainTitle">` の中に `<p class="crown">`・`<h1 class="name">`（電話の幅の方は `<div class="name">`）・`<p class="subTitle">`。空の欄も要素は出る
- 冠名がある 4,092 件のうち <title> に冠名がある 14 件、サブタイトルがある 969 件のうち 7 件。題名を <title> から取っていた（fetch_credits.parse_stage・fetch_candidates.stage_row・fetch_past_stages.row_from_html）ので、ほぼ全部で落ちていた
- 冠名の例: 「喜劇結社バキュン！ズ第６回公演」「創立45周年記念」「舞台」「2019年6月公演」。サブタイトルの例: 「～再び死ぬ～(再演)」

分からなかったこと: 検索の一覧（/stage/search の `<p class="stage">`）に冠名が入るか（控えに一覧のページが無く、この環境から CoRich に届かない）。本番は一覧の検索を止めてサイトマップから公演ページを読むので、題名は公演ページから取れる。
