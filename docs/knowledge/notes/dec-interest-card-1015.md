---
id: dec-interest-card-1015
type: decision
status: adopted
date: 2026-10-15
title: 興味ありのカード: 「くわしく」を理由の上に、開幕リマインドから足した公演は「開幕リマインドからの追加」とだけ書く、本人が書いた文は明朝
sources:
  - web/app.js
  - web/theme.css
  - cloudflare/src/screens/cards.js
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/recommend.js
links:
  - affects: comp-frontend
---
起案者の指示（2026-10-15）は次の 3 つ。
- 「「くわしく」は「おすすめ理由」の上にして」
- 「「おすすめ理由」は初期登録で開幕リマインドから追加したものは、おすすめ理由という欄ではなく、「開幕リマインドからの追加」だけ書いて」
- 「なぜ気になったか？や感想など、ユーザーが自分で入力したものはちょっとフォント変えて」

作りは次のとおり。
- 「くわしく」の位置（app.js の compactTickets）: 理由の見出しの直前に置く。おすすめ・興味あり・購入済みのカードすべてで同じ。
- 押した画面を記録する:
  - 画面（app.js）が `/api/react` に from（reminder・search・favourites）を送り、reaction.source に入れる。from が無ければこれまでどおり 'screen'。ツアーのほかの会場には `_tour` を付ける。
  - 理由やメモだけを書いたときは source を書き換えない（ON CONFLICT の CASE）。
- 興味ありの一覧（lists.interestScreen）: 最新の興味ありが reminder なら、理由の見出しと一覧の代わりに「開幕リマインドからの追加」とだけ書く（cards.compose の origin）。探すから足したものは「探すからの追加」。
- この記録はこの変更から始まる。それより前に足した興味ありは source が 'screen' で見分けられないため、これまでどおりの理由の欄のまま。
- 本人が書いた文（.wnt・.int・.nnv と、その入れ口の textarea）は、--mincho（明朝）にした。
