---
id: impl-hashtag-list
type: decision
status: adopted
date: 2026-10-18
title: あらすじのハッシュタグを押すと、その題材の付いたこれから観られる公演の一覧（/recommend/tag）へ。1 回開くごとの D1 の読み取りは 2,000 行ほど
sources:
  - cloudflare/src/screens/tagged.js
  - cloudflare/test/tagged.test.js
  - web/app.js
  - cloudflare/test/e2e-walk.js
  - cloudflare/migrations/0018.sql
links:
  - depends_on: dec-recommend-worker-cards
  - depends_on: d1-free-limits
  - affects: q-d1-reads-real
  - affects: dec-rec-card-1018-layout
---
起案者の指示（2026-10-18）「あらすじのハッシュタグ押したらそれがついてる公演一覧が出るようにして。」

決めたこと:
- カードのあらすじの下のハッシュタグ（app.js leadSynopsis の .lsyntag）を、`/recommend/tag?w=語` へのリンクにした。画面の名前は `tagged`（Worker だけが答える。cloudflare/src/screens/tagged.js）。デモ版（Render）にはこの画面が無いので、デモでは押せない札のまま
- 既存の画面に乗せなかった理由: 探す（/search）は題名・団体・人・劇場にも当たり、「その語が付いている公演」より広い。お気に入りの名前の画面（/recommend/favourites?n=）は登録した名前だけを引く作りで、別の担当が名前の当たり（lists.js）を直している最中。なので新しい画面を足した
- どこから引くか（リポジトリのコードで確かめた）: カードの札は作り置きのカード（rec_card）のあらすじの枠の題材（build_cards.py の `c["themes"]`＝themes.jsonl の elements の word。数の上限なし）と、管理者が手で入れた題材（stage_override.themes。入っていればカードの札はそちらに差し替わる）。rec_card には同じ題材を recommend2.nz でそろえて 1 行 1 語にした列 `ws` がある（migration 0018）。索引の #題材（rec_credit）は 1 公演 6 語まで・2 文字以上（build_recommend_index.theme_words）でカードの札と食い違うので使わない
- 当たりの決め方: `ws` の 1 行がその語（nz でそろえる）と完全に同じ公演。語の一部では当たらない（「家」で「家族」は出ない）。手で入れた題材がある公演は、手で入れた方で決め直す
- 並べ方: 公演ごとに 1 枚（同じ tour の会場は 1 枚の日程に入れる。代表は、語の付いた会場のうち初日の早いもの）。上演日の近い順、1 ページ 20 件（TAG_SHOW）。カードは探すの結果と同じ形（「ヒットした箇所：題材 #語」、興味あり・興味なし・購入済を押せる。興味ありと答えた公演は興味ありのカード、答えた公演は答えを 1 行添える）。画面の見た目はおすすめと同じ「くわしく」なしの形（app.js compactTickets の tagPage）。ここで押した興味ありは「探すからの追加」として残す（app.js の from。screens/recommend.js の reactAction は別の担当が直しているので触っていない）

無料枠（D1 の読み取り、1 日 500 万行〔d1-free-limits〕）。1 回開くごと:
- rec_card のいまの版のうち終わっていない行を 1 回なめる: いまは約 1,350 行（これからの公演の数。`ws` に索引は無いので行数ぶん読む）。ツアーのほかの会場も同じ 1 回で拾う（tour の列を一緒に返す）
- stage_override: 手で直した公演の行だけ（上限 500 行、TAG_OVERRIDE_ROWS）
- 出すカード 20 件ぶん: rec_card（stage_id で引く）・poster・stage_override・catalogue（あらすじの穴埋め）・rec_stage と catalogue（日程）で、1 件あたり数行
- 本人の答え（reaction、本人の行だけ）
合わせて 2,000 行ほど。探すで言葉を 1 回引く（rec_stage 約 4,800 行と rec_card を突き合わせ、catalogue の 1 年分も読む）より軽い。ただし 300 人が全員 1 日 10 回開くと 600 万行になり 1 日 500 万行を越える（D1 は越えるとその日はエラーで、請求はされない）。よく使う人の見積もり（1 人 1 日 3.5 万行〔dec-account-cap-counted〕）の中に入る量として扱い、〔q-d1-reads-real〕の実測で確かめる。重いと分かったら、索引の #題材（rec_credit、索引を引くだけで当たった行しか読まない）を先に引く形に変える（ただしカードの札と食い違う分が出る）。当たった会場は 300 件（TAG_ROWS）で打ち切る。rec_card をなめる問い合わせが 1 回だけであることは tagged.test.js で確かめている

分からないこと: 本番の rec_card の行数は 2026-10-14 の取得の数（これからの公演 1,353 件）からの見積もりで、今日の本番の行数は見ていない。D1 が返す rows_read（meta）を実際に読んで確かめてはいない。
