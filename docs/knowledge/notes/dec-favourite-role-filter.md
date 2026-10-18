---
id: dec-favourite-role-filter
type: decision
status: adopted
date: 2026-10-18
title: お気に入りの人は、任意で役職（出演・脚本・演出・作曲・音楽・振付・翻訳・原作、複数可）に絞れる。絞った名前は、その役職で欄に書かれた公演だけを一覧と推薦の種に使う
sources:
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/settings.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/recommend.js
  - web/app.js
  - web/theme.css
  - cloudflare/test/fav-roles.test.js
links:
  - answers: q-favourite-homonym
---
起案者の答え（2026-10-18）「Aで。ただし人って選んだあとに、細く指定したい場合のみ任意で選べるように。複数役職やる人もいるので。」

- 登録の欄で種類に「人」を選んだときだけ、「役職で絞る（任意）」の札が出る（CSS の :has。ほかの種類では出ない）。選ばなければ、これまでどおりどの役職でも当てる。複数選べる。
- 控えは app_setting の `declared_roles`（{名前: [札]}）。お気に入りの名前の控え（declared）の形は変えていない（古い Python 版・別のセッションのコードに影響しない）。足し直すと札を置き換え、札なしで足し直すか外すと絞りも消える。変わらないときは書かない。
- お気に入りの一覧（lists.wholePersonNames）: 絞った名前は、出演・スタッフ欄を名前ごとに切り分けて、選んだ役職で書かれているときだけ当てる。「作・演出」のような並びは、・／で切った 1 つずつでも当てる。欄を読めない公演では役職を確かめられないので外す。
- 推薦の種（recommend.seedsFromFavourites）: 絞った名前は、選んだ役職の索引だけを引く。おすすめの控え（rec_cache）は declared_roles が変わると作り直す。
- 札は「#人「加藤拓也」脚本・演出」のように、名前の後ろに選んだ役職を小さく添える。
- 無料枠: 登録のときに D1 の読み 1・書き 0〜1、一覧を出すときに読み 1 が増えるだけ。
