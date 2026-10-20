---
id: dec-ikeba-yokatta
type: decision
status: adopted
date: 2026-10-20
title: 「観ればよかった」を「行けばよかった」にし、興味ありのまま購入済みにならずに終わった公演は自動で入れる。「行けない」のボタンはやめる
sources:
  - cloudflare/src/screens/settings.js
  - cloudflare/src/screens/cards.js
  - cloudflare/src/screens/search.js
  - web/app.js
  - cloudflare/test/cantgo.test.js
links:
  - affects: comp-cf-worker
---
起案者の指示（2026-10-20）「行けばよかった登録できるところを整えたい。あと『行かない』は不要。興味ありにしたけど購入済みにならなかったら自動的に行けばよかった扱いにすれば良い」。置き場所は「今の場所のまま中身だけ整える」（観劇記録を追加の畳んだ欄）を起案者が選んだ。

- 名前を「行けばよかった」にした（観劇記録を追加の欄・探すの過去の公演のボタンと文言）。保存先の表（missed）と API（/api/missed）は前のまま
- 自動で入る分（settings.autoMissed）: 興味あり（interest=1、前に押した行けない=2 も）で、購入済み（owned=1）でなく、公演の終わりの日が今日より前のもの。観た記録に結び付いた公演・同じ題名の観た記録・自分で登録した題名は除く。ツアーは題名と団体で 1 行。**保存はせず、開くたびに答えから数える**（D1 の書き込みは増えない。読み取りは答えの表と、その公演の索引・一覧の行）
- 一覧は題名 1 行ずつ（自動の分は会場・終わりの日と「興味ありのまま終わった」、自分で足した分は登録日）。自分で足した分の「どこで漏れたか」・演者・あらすじは「くわしく」に畳んだ
- 興味ありの一覧の「行けない」のボタンを外した（cards.interestButtons）。前に押した「行けない」の答え（interest=2）は残り、その公演では押し直せるよう出す。API の cantgo は前の画面のために受け付けたまま
