---
id: dec-fav-only-reco
type: decision
status: adopted
date: 2026-10-18
title: お気に入りだけでもおすすめが出るようにする: 名前は空白を詰めても引く、一覧に出る公演も種にする、広げる元は本人が評価・興味ありにした公演の人だけ、お気に入りから来た人の理由には登録した名前を書く
sources:
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/lists.js
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/test/fav-reco.test.js
  - cloudflare/test/recommend-screen.test.js
links:
  - depends_on: fix-fav-only-no-reco
  - depends_on: fav-reason-two-step
  - depends_on: impl-favourite-seed
  - affects: dec-spread-and-partners
---
起案者の指示（2026-10-18）: 案内のとおりに「お気に入りを登録しただけでもおすすめが出る」ように直す。理由の文は登録した名前（例: 堂本光一）を書く。原因は〔fix-fav-only-no-reco〕〔fav-reason-two-step〕。

決めたこと（版 screen-v33 で控え rec_cache を作り直す）:
- **名前の書き方:** 種を引くとき、登録した名前に加えて NFKC で空白を詰めた形（recommend.personKey、build_recommend_index.person_key）でも索引を引く。理由に出さない本人（skip）にも両方を入れる
- **一覧に出る公演も種にする:** お気に入りの一覧に出る公演（lists.nameHits の hits）のうち、まだ種に無いものを足す（screens/recommend.hitSeeds）。種の上限 MAX_SEED_STAGES（60）は前と同じなので、読む行の上限は変わらない（索引 rec_people から人を読み、無い公演だけ出演欄から読む。控えが古いときだけ動く）。本人の名前は空白を詰めた形で比べて理由から外す
- **1 段だけ広げる元:** 本人が評価した公演・興味ありを押した公演にいる人に限る。お気に入りの公演の共演者は、それ自体がお気に入りの名前から 1 段広げた人なので、そこから広げない（2 段先にしない）
- **理由の文:** 評価の履歴が無く、お気に入りの公演にいたことで上がった人は「（お気に入りの{登録した名前}と同じ公演に関わる人：『その公演の題名』）」と書く（screens/recommend.favOrigins・reasonRows）。同じ人が何人ものお気に入りの公演にいれば、いっしょの公演が多い名前。劇団・作品・題材で登録したときも登録した名前（d1Access.stagesMatching が当たった語を labels で返す。列を足すだけで行は増えない。PR #210 の語彙表で広げた言葉（exact）で当たった公演も、理由には登録した題材の語を書く。exact の問い合わせは DISTINCT を (stage_id, 言葉) にしたので、1 公演が広げた言葉の 2 つ以上に当たるときだけ行が少し増える）
- **案内の文（TIPS）は変えない。** 直したあとは「共演者や題材などが推薦に反映されます」のとおりに動く。ただし共演者などの別の公演が、まだ始まっていないものに無いと 0 件のまま（〔q-fav-reco-running-shows〕）

無料枠: D1 の読み取りは控えが古いときだけ。種の公演の数の上限（60）は前と同じで、足したのは一覧に出る公演の人の行（rec_people、多くて 60 公演ぶん）と、索引に人が無い公演だけの出演欄。書き込みは増えない。

試験: fav-reco（7 件）。recommend-screen の「お気に入りの共演者の理由」の期待を新しい文に変えた（理由をコメントに書いた）。e2e-walk に「B: お気に入り（作家 丁）だけで…」を足した。Python の参照（user_recommender）には 1 段広げる計算が無いので、広げる元の変更は Worker だけ。
