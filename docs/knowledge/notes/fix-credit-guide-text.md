---
id: fix-credit-guide-text
type: finding
status: confirmed
date: 2026-10-18
title: 出演欄などに名前の代わりに書かれた案内の文（「スタッフ欄をご覧ください。」「詳細は公式サイトにて、https://…」など）を人名として読んでいた。カードの出演の行と推薦の索引（rec_people）の両方に入っていたので、案内の文と URL は名前として読まないようにした
sources:
  - tools/review/measure_nets.py
  - cloudflare/src/screens/credits.js
  - cloudflare/src/screens/cast.js
  - tools/review/render_recommend.py
  - cloudflare/test/credits.test.js
  - cloudflare/test/cast.test.js
  - tools/review/test_measure_nets.py
links:
  - affects: dec-credit-part-names
---
起案者の指示（2026-10-18）「出演 スタッフ欄をご覧ください。になってる箇所があるから直して。」

調べたこと（取得元のデータそのもの: 候補 4,812 件・過去の公演 17,802 件、2026-10-16 の写し）:
- 出演欄の全体が案内の文の公演: 「スタッフ欄をご覧ください。」23 件、「詳細は公式サイトにて、https://musical-za.co.jp/」18 件、「詳細は公式サイトにて」2、「下記に掲載」2、「comingsoon....」「ComingSoon」「comigsoon」「（後日発表）」「下記、参照」「下記説明欄を参照」「詳細不明」「スタッフ欄に記載」「日により出演者が異なります、詳細はタイムテーブル欄をご覧ください。」「公式サイト参照」各 1〜2 件。脚本・演出欄にも「下記スタッフ欄をご参照ください」「スタッフ欄をご覧下さい」などがある
- カード（render_recommend.cast_block / Worker の settings.castBlock）は欄を区切りで割っただけで並べるので「出演 スタッフ欄をご覧ください。」と出ていた
- 名簿（measure_nets.parse_credits。推薦の索引 build_recommend_index も同じ関数）も人名として読んでいた。「スタッフ欄をご覧ください。」が 23 公演の「出演者」になり、「詳細は公式サイトにて」「musical-za.co.jp」も人として入っていた。評価した公演にこの文があると、同じ文のある別の公演を「同じ人の公演」として推していたことになる

直したこと: 案内の語（ご覧・参照・詳細・公式サイト・ホームページ・掲載・記載・後日発表・発表予定・調整中・異なります・coming soon）と URL（http(s):// と英数字のドメイン）を名前として読まない（measure_nets.GUIDE / is_guide、Worker の credits.GUIDE / isGuide。カードの split_names / splitNames も同じ規則）。出演欄が案内の文だけなら、カードに出演の行を出さない。
- 「未定」は欄の全体が未定のときだけ（実データに「今井未定」という名前が 13 件ある）。ドメインは英数字のものだけ（「演劇ユニットG.com」は団体名）
- 実データで、この規則で落ちる語は 62 種 153 か所。名前として残すべきものが落ちるのは「ホームページ∶小野村崇」（役職の区切りが比の記号「∶」）の 1 件だけと見た
- 索引（rec_people・rec_credit）は次の取得で作り直され、差分で入れ替わる（deliver_catalogue は値の変わった行を送る）。入れ替わるまでのあいだ、Worker は理由の行で案内の文の「人」を出さない（screens/recommend.js reasonRows）が、点数にはまだ効く

分からないこと: 本番の D1 の索引が何日で入れ替わるか（書き込みの上限の中で少しずつ送る）。新しい型の案内の文が増えたら語を足す必要がある。
