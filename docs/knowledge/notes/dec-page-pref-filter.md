---
id: dec-page-pref-filter
type: decision
status: adopted
date: 2026-10-17
title: ページで選んだ県の絞り込みは、そのページの中だけで効かせる（保存するのは設定の県だけ）
sources:
  - cloudflare/src/screens/prefs.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/reminder.js
  - web/app.js
  - cloudflare/test/lists-screen.test.js
  - cloudflare/test/recommend-screen.test.js
links:
  - affects: dec-settings-worker
  - affects: dec-reminder-worker
---
起案者「絞り込んだ都道府県は、そのページ内でのみ維持されるように。全部の共通の絞り込みは設定で保存しているので」（2026-10-17）。
- それまで: おすすめ・開幕リマインドで県を選ぶと app_setting の recommend_prefs に保存し、おすすめ・開幕リマインド・開幕の帯（ticker）・入れ替えの 1 枚のどれにも、次に開いたときにも効いていた（Python の serve.get_prefs / set_prefs と同じ作り）
- いま: prefs.prefsFor は、URL に ?f=1&pref=… があればその県、無ければ設定の県（pref_filter）。保存はしない。読み込み直し・戻るでは URL に残るので、そのページの中では続く
- ページの中の移動にも持ち回す: 開幕リマインドの週の札（prefQs）、おすすめの「おすすめに出てこない公演を探す」の欄（prefHidden）、答えた後の入れ替えの 1 枚（web/app.js pagePrefs が URL の県を /api/react の fill_only に送る）
- 設定で県を保存しても recommend_prefs には書かない。古い recommend_prefs の行は読まない（残っていても効かない）
- 無料枠: 絞り込むたびの D1 の書き込み（1 回 1 行）が無くなるので、使う量は減る
- Python の serve.py（ローカルのデモ）は元のまま保存する作り。本番は Worker
