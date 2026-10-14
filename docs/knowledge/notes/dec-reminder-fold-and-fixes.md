---
id: dec-reminder-fold-and-fixes
type: decision
status: adopted
date: 2026-10-14
title: 開幕リマインドを題名で折りたたみ、開くと会期・出演・あらすじを出す。カードの無い公演の答えを失わない。設定では全都道府県を選べる。「記録しました」は帯の下
sources:
  - cloudflare/src/screens/reminder.js
  - cloudflare/src/screens/fallback.js
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/settings.js
  - cloudflare/src/screens/prefs.js
  - web/theme.css
  - cloudflare/test/lists-screen.test.js
---
起案者の指摘（2026-10-14・スマホのサービス版）：
- 「地方選ぶ機能が使えなくなってる」：設定の都道府県は、その人のおすすめに入っている県だけを出していたので、記録の少ない人・索引が古い日には 1 つも出なかった。設定では 47 都道府県と 8 地方を常に出す（既定を決める場所なので、いま公演があるかに関わらない）
- 「開幕リマインドで『興味あり』押して、そのまま開いても 0 件になる」：開幕リマインドは索引に無い公演を公演一覧（catalogue）から補って出すが、興味あり・お気に入り・持っている公演の振り分け（lists.buckets）と一覧のカードは、作り置きのカード（rec_card）がある公演しか見ていなかった。答えが保存されても「興味あり」に出ず、開幕リマインドでは未回答のままに見えた。カードの無い公演は catalogue・rec_stage から振り分け用の情報と簡単なカードを作る（fallback.js）
- 「開幕リマインドのとこも、タイトルで折りたたんで、開いたら同じようにあらすじとか出演者とか出るように」：行を details にし、開くと作り置きのカードから会期・料金・販売・出演・あらすじ（修正の欄は除く）を、カードの無い公演は catalogue の出演・あらすじを出す。答えのボタンは畳んだまま押せる
- 「このおすすめの日程」はおすすめのカードの言い方で、開幕リマインドでは「この行の会場」にする（ツアーのほかの会場と並べたときの、この行の会場の印）
- 「記録しましたは横に出すより下で出したほうがいい」：カードの外の答えの帯でも、カードの中と同じく帯の下の行に出す（web/theme.css、デモ版も同じ）
