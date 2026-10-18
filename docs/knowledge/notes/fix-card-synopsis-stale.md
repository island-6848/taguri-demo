---
id: fix-card-synopsis-stale
type: finding
status: unverified
date: 2026-10-17
title: 読み取り済みのあらすじが画面に出ないのは、カード（rec_card）が古い版のまま残るため。一覧（catalogue）には先に届くので、画面に出すときに一覧の本文で埋める
sources:
  - cloudflare/src/screens/override.js
  - cloudflare/src/screens/cards.js
  - cloudflare/scripts/deliver_catalogue.py
  - tools/admin/admin.py
  - cloudflare/test/override.test.js
links:
  - depends_on: dec-synopsis-reader-claude
  - depends_on: dec-recommend-worker-cards
---
起案者の質問（2026-10-17）「すでにあらすじが取れている公演なのに、各画面（お気に入りやおすすめ、興味ありなど）に実際の文章が表示されていないのはなぜ？」。

- **カードと一覧で、届き方が違う。** あらすじはどちらも、本文に実在するか確かめた themes.jsonl から来る。
  - 一覧（catalogue）の行は、変わった行だけを毎日先に入れる。
  - カード（rec_card）は、これからの公演の全部を 1 つの版として作り直す（1 公演あたり 2〜4 行の書き込み）。その日の書き込みの枠に入らないと、丸ごと見送る（`deliver_catalogue.py` の "skipped: … would exceed the budget"）。
  - そのため、あとから読み取ったあらすじは一覧にだけ届き、カードは「あらすじを取れませんでした」のまま残ることがある。
  - 管理画面（`tools/admin/admin.py stage`）は、カードに本文が無いと一覧の本文を出すので、「取れている」ように見える。
- **本番の D1 は読めていない。** 本番でカードを見送った日があったかは確かめていない（取得側の作業の記録は別の非公開リポジトリにある）。上の説明は、コードの作りから導いたもの。
- **直し方。** `cardTemplates` で、カードに本文（`<p class="txt">`）が無く、手で入れたあらすじも無い公演について、一覧の metadata.synopsis を読む。あれば、あらすじの枠をその本文に差し替える。
  - 題材のタグと、内容を直す入れ口は残す。
  - D1 の読み取りは、1 画面で 1 回（90 件ごと）増える。書き込みは増えない。
  - metadata の JSON は Worker で解かず、D1 の json_extract であらすじだけを取り出す（2026-10-18。無料枠の CPU 10ms の対策）。
- **まだ直していないこと。** カードの作り直しが枠に入らない日が続くと、日付・料金などのほかの欄も古いままになる。差分だけを入れる形にするのは別の作業。
