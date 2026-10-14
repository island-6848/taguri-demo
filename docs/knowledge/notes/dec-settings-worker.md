---
id: dec-settings-worker
type: decision
status: adopted
date: 2026-10-14
title: 設定・はじめる・公演情報の登録を Worker に移す（Render に依っていた所は本番の形に置き換える）
sources:
  - cloudflare/src/screens/settings.js
  - cloudflare/src/screens/prefs.js
  - cloudflare/src/screens/cast.js
  - cloudflare/test/lists-screen.test.js
  - cloudflare/test/cast.test.js
links:
  - depends_on: dec-native-cutover-now
  - affects: comp-native-screens
---
起案者の指示（2026-10-14）「残りの画面も順に移して」の 3 段目。見た目と文は app._settings_body / _start_body / _register_body のまま。変えたのは Render に依っていた所だけ:
- 設定の「アカウント」の札（Render の復旧コード・別端末のコード）→ 本番のアカウントの画面（/account）への案内
- 設定の「観に行ける場所」（pref_setting）→ app_setting の pref_filter に保存し、今の絞り込み（recommend_prefs）にも当てる。おすすめ・開幕リマインドは、絞り込みを選んでいなければこれを使う（serve.get_prefs と同じ）。地方でまとめて選ぶ札も出す（地図は輪郭が D1 に無いので出さない）
- 書き出す（/export.json）→ Worker が D1 から、その人の行だけを Python と同じ鍵で返す
- はじめるの 2 段目（run.py --fetch の案内）→ 毎日の取得で届いた件数を言う
- 登録の①（メールの取り込み）は持ち主専用のまま。「観ればよかった」（missed）は、その場で外を調べず、D1 の今の索引と過去の公演から題名の鍵で当てて、出演者・作り手を出す（Python は外を調べる。公開版は次の更新で探す依頼にしていた）。Python の missed_rows が利用者で絞っていなかった点は、Worker では本人の分だけにした
- 出演者の並び（cast_block・split_names）を JS に移し、Python と同じ HTML になることを cast.test.js で確かめる
