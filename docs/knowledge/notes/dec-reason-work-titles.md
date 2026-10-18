---
id: dec-reason-work-titles
type: decision
status: superseded
date: 2026-10-14
title: おすすめの人物の理由には、本数ではなく具体的な作品名（と付けた印）を書く
sources:
  - tools/review/measure_nets.py
  - tools/review/recommend2.py
  - tools/review/user_recommender.py
  - tools/review/render_recommend.py
  - tools/review/test_reason_works.py
---
起案者の指示（2026-10-14）「『（◎ を付けた・気になった作品での実績・履歴 1 本）』じゃなくて、具体的に（『作品A』『作品B』など）って書いてほしい」。
`measure_nets.person_titles` が、名簿と同じ材料（評価を付けた記録と、興味ありを押した公演）から (役職, 人物) → [(作品名, 印)] を作り、`recommend2`・`user_recommender` が `why_b_works`（"役職\t人物" → 作品の並び）として候補に持たせる。画面は「（『作品A』◎・『作品B』○・『作品C』興味あり ほか 2 本）」と 3 本まで書く。並びは ◎ → ○ → △ → × → 興味あり、同じ印の中は新しい観劇日から。作品名が引けない人（観ればよかったから来た人・古い出力）は「（履歴 N 本）」のまま。
本数だけを書いていたのは「1 本の偶然と 8 本の好みを同じ顔で読ませない」ためだった。作品名と印を並べればその役目も果たせる。人の作品名は本人の記録なので、本人の画面にだけ出る（公開のカタログ・D1 には入らない ── convert_catalogue.public_candidate は許した欄しか写さない）。
2026-10-14 追記: 起案者の指示「理由に作品名を書くとき、◯とかの評価は不要。作品名だけでよい」で、印を付けずに「（『作品A』・『作品B』 ほか N 本）」にした。並びは ◎ を付けた作品が先のまま。
