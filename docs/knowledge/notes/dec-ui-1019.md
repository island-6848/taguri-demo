---
id: dec-ui-1019
type: decision
status: adopted
date: 2026-10-19
title: 2026-10-19 の画面の変更: 過去の公演も題名の頭の語（舞台・ミュージカル…）の後ろで引く、同じ作品の記録を自動でまとめる、表示名はえんぴつで直す、探すのカードをほかと同じ形に、アカウントの小窓、戻る・歯車・文字の形を外す、設定の 2 つを折りたたみに、帯は「今週のおすすめ」、ログインの画面のロゴ、お気に入りが無いときの案内
sources:
  - cloudflare/src/stage-search.js
  - cloudflare/src/screens/suggest.js
  - cloudflare/src/screens/search.js
  - cloudflare/src/screens/diary.js
  - cloudflare/src/screens/rate.js
  - cloudflare/src/screens/records.js
  - cloudflare/src/screens/account.js
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/guide.js
  - cloudflare/public/login.html
  - cloudflare/public/auth.css
  - web/app.js
  - web/theme.css
  - web/index.html
  - web/404.html
  - cloudflare/test/title-leads.test.js
  - cloudflare/test/auto-merge.test.js
  - cloudflare/test/ui-1019.test.js
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: q-e2e-register-rework
---
起案者の指示（2026-10-19）と決めたこと:

1. 「『銀河鉄道の父』を探そうとしたら『舞台 銀河鉄道の父』で登録されてるらしくて参照できなかった」: 過去の公演（past_stage）は題名の先頭一致（tkey の索引）でしか引けない。途中の語まで当てると打つたびに全部の行を読む（D1 の読み取りの無料枠）ので、打った言葉の頭に「舞台」「ミュージカル」「人形劇」「朗読劇」「音楽劇」「オペラ」など 19 語（取得データで題名の頭に多かった語）を付けた形も、同じ索引の範囲で引く（stage-search.titlePrefixes。観劇記録の追加の候補と「探す」の両方）。打った言葉の頭にこの語があれば外した形でも引く。これからの公演は前から 2 文字ずつの索引で途中の語も当たる。
2. 「観劇記録の中でも回は違っても同じ作品なら同じ作品のツリーとして統合する作業を自動でやって」: diary.autoMerge。題名の鍵が同じで、団体が同じか片方に無い・劇場が同じ・同じ公演・同じツアー、のどれかなら同じ作品として、いちばん早い日の記録に手でまとめるのと同じ印（merges）を書く。評価が違う記録どうし・感想を書いた記録どうしはまとめない（片方が隠れるため）。本人が「まとめを外す」をした記録は excluded の nomerge:<鍵> を付け、まとめ直さない。日記帳・評価・眺めるの画面を開いたときに動く。
3. 表示名は名前の右のえんぴつで直す欄を開く。保存すると閉じる。
4. 「探す」のカードは、おすすめ・興味あり・お気に入り・ハッシュタグの一覧と同じ形（「くわしく」の折りたたみ無し）。「ヒットした箇所」はおすすめ理由と同じ所に同じ見た目で置く。
5. アカウントのアイコン（電話の幅は右上、パソコンの幅は帯の「アカウント」）で小窓を開く: アカウント・設定・ログアウト（この端末で）。歯車と帯の「設定」は外した（デモ版は歯車のまま）。
6. 全ページの「← 戻る」を外した（web/index.html・404.html。古い Python 版は触っていない）。
7. 設定の「文字の形」を外し、前に「規定の文字」を選んだ端末も決まりの文字に戻す。「評価の詳細の出し方」「カードに出す名前」はほかと同じ折りたたみ（details.card）。
8. 帯とすだれの名前は「今週のおすすめ」。画面の見出しは「今週のあなたへのおすすめ」のまま。
9. ログインの画面のロゴを、帯と同じ新しいロゴの横組み（tgl-row）にした。
10. お気に入りに名前が 1 件も無いときは、名前の欄の下にイラスト付きの案内「お気に入りに登録されている要素がありません。」を出し、年月の絞り込み（すべて）・並べ替え・一覧は出さない。

確かめたこと: 単体の試験（JS・Python）はすべて通る。e2e は、master にある観劇記録の追加の画面の作り替え（#219〜）で 13 段が落ちる〔q-e2e-register-rework〕。加えて「効かせ方のつまみ」の段は、手を入れていない今の master（69a342a）でも落ちる（おすすめが 0 件でつまみの札が出ない）。この作業で足した段（題名の検索・探すのカード・アカウントのアイコンと表示名・アカウントの小窓・戻る無し・設定の折りたたみ・帯の名前）は通り、写し（電話・PC・ログイン）を見た。自動でまとめる流れは単体の試験だけで、e2e の段は無い。
