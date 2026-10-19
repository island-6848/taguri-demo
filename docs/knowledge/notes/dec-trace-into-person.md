---
id: dec-trace-into-person
type: decision
status: adopted
date: 2026-10-19
title: 「たどる」の画面を外し、糸の図だけを人物のページに載せる（名前の一覧・人のネットワーク図はやめる）
sources:
  - cloudflare/src/screens/trace.js
  - cloudflare/src/screens/entity.js
  - web/app.js
links:
  - answers: q-trace-into-person
  - depends_on: dec-entity-pages-keep
  - affects: comp-cf-worker
---
起案者の指示（2026-10-19）「名前の一覧もネットワーク図もいらない。糸で繋がってる図だけ各人物の個人ページに入れてくれればok」。

- 人物のページ（/recommend/person）に「観た公演をつなぐ糸」を出す。評価した記録のうち、上演日のある 2 公演以上にその名前があるときだけ（trace.personThread。線の引き方・垂れる名前の選び方は前の「たどる」と同じ）
- 垂れた名前を押すと、その人の人物のページへ移る。たどってきた道（via）の表示はやめた
- 「たどる」の画面（records.traceScreen）・名前の一覧・人のネットワーク図はやめた。メニューから外し、前のアドレス /records/trace は、name があればその人の人物のページ、無ければ「眺める」へ移す（web/app.js の loadScreen）
- Python の trace.body と比べるテスト（trace.test.js・trace_fixture.py）は外した。代わりに Worker のテストで人物のページの糸を確かめる
- 無料枠: 人物のページを開くたびに、本人の評価した記録の出演者（peopleByKey）と劇場を読む。「たどる」を開いたときと同じ量で、新しい保存・定期実行はない
