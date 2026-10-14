---
id: dec-ui-1014-drop-calendar-editor
type: decision
status: adopted
date: 2026-10-14
title: 取り消した記録は 30 日で自動で消す・公演カレンダーに一覧だけにある購入済み公演も出す・画面の控えを他のタブと戻る操作でも捨てる・「記録を直す」欄を言い換えてメールのボタンを外す
sources:
  - cloudflare/src/screens/works.js
  - cloudflare/src/screens/diary.js
  - cloudflare/src/screens/settings.js
  - cloudflare/src/screens/calendar.js
  - cloudflare/src/screens/row.js
  - web/app.js
  - cloudflare/test/drop-expiry.test.js
  - cloudflare/test/lists-screen.test.js
  - cloudflare/test/screens.test.js
links:
  - depends_on: dec-reminder-catalogue-fill
---
起案者の指示（2026-10-14、未評価の画面写真つき）。
- 取り消した記録: 取り消し（excluded の `work:<key>`）から 30 日（`DROP_KEEP_DAYS`）たっても戻さなかったら、記録を読むとき（`loadWorks` の最初、1 回の要求で 1 度）に works・hand_credits・merges・印をまとめて消す。設定の「いますぐ消す」（purge_work）は待たずにその場で消す（前の版の `purged:` の印も同じく消す）。D1 の量は減る方向なので無料枠には響かない。Python 版（持ち主の手元用）は印を付けるだけのままなので、比べる試し（scenarios.json）から purge の 3 手を外し、drop-expiry.test.js で確かめる
- 公演カレンダーに何も出ない: カレンダーが今の取得分（rec_stage）しか見ておらず、一覧（catalogue）にだけ残る購入済み公演を落としていた。リマインドと同じ `fallback.stageInfo` を使うようにした
- 取り消したのに開き直すと復活: サーバーは正しく外していた（未評価に出ない）。原因はブラウザ側の控え。`location.reload` のあとブラウザの戻る・進むの控え（bfcache）から古いページが出ること、別のタブが 45 秒の画面の控えを持ち続けること。`pageshow`（persisted）で画面を読み直し、書き換えたら localStorage で他のタブにも控えを捨てさせる（`markMutated`）
- 「公演詳細を直す」欄: 「記録を直す」に改め、観た日・劇場を先に、「おすすめに出る公演と結び付ける」を「観た公演」「公演一覧から探す」「つながりを外す」と言い換えた。「メール本文を見る」「自動の結び付けを外す」のボタンは外した。メールは保存していない（取り込みはブラウザの中で読み、題名・日付・劇場だけを送る）。Python 版は欄の形が違うので、比べる試しでは欄を印に置き換える
- 未評価の評価ボタンの左寄せ: スマホ幅・PC 幅の描画ではすでに左に寄っていた。どの部分のことか起案者に確かめる
