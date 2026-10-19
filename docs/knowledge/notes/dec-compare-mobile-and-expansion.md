---
id: dec-compare-mobile-and-expansion
type: decision
status: adopted
date: 2026-10-19
title: 比較表のスマホはみ出しを修正し、公演DBと本人の比較拡充案を整理する
sources:
  - cloudflare/src/screens/compare.js
  - tools/taguri/compare.py
  - web/style.css
  - cloudflare/test/compare-layout-browser.js
  - docs/compare-expansion-proposal.md
---
起案者の指定は、まずスマホのはみ出しを直した後、比較の充実案を検討すること。比較の6列表はカード内で横スクロールする。表のラベルと数値を残し、狭い画面に案内を表示する。共通CSSと配信コピー、Python側の同じパネルも同期する。

内容の追加はまだ行わない。比較対象は一般の観客の好みではなく、取得済み掲載公演の構成比である。期間・地域・作品の数え方・欠損・母数をそろえ、既存クレジット4軸と題材を優先候補とする。実装案・限界・未確認事項は提案書に記す。本番DBを読む処理・新しい外部取得・保存領域は増やさない。
