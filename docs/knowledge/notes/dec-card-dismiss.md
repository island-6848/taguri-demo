---
id: dec-card-dismiss
type: decision
status: adopted
date: 2026-10-18
title: カードの右上の ✕「候補から消す」: ふつうは reaction.interest=3（どの一覧・おすすめからも外すだけ）、興味ありの画面で押したら 4（外して、興味あり 1 公演と同じ重さの負の手がかり）
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/lists.js
  - cloudflare/src/screens/reminder.js
  - cloudflare/src/screens/search.js
  - cloudflare/src/screens/tagged.js
  - cloudflare/test/dismiss.test.js
links:
  - depends_on: impl-interest-split
---
起案者の指示（2026-10-18）「ヘルプマークやっぱりカード内の右下角において。逆に今ヘルプマークがあるとこには取り消しの✕をつけて。たとえばお気に入りとか、これいらんなってときがある。その時候補から消したい。興味の画面でバツを押された場合は、興味なしか視界にも入れたくないから結構マイナスと判断できる。」

決めたこと:
- /api/react に value `dismiss`（interest=3）と `dismiss_strong`（interest=4）を足した。新しい列・移行は要らない（reaction.interest の値を足しただけ。D1 の書き込みは、ほかの答えと同じ 1 回の batch）。
- 3・4 とも、答えた公演としておすすめから外れる（answered）。興味あり・お気に入り・開幕リマインドの一覧にも出さない（lists.reactionsOf の others に dismissed として入れ、reminder.weekRows で飛ばす）。検索とハッシュタグの一覧では「候補から消しました」と出す（自分で探したときは見つかる）。
- 3（おすすめ・お気に入りなどで押した ✕）は好みの手がかりにしない。「この公演はいらない」だけで、そこに出ている人が嫌いとは限らないため。
- 4（興味ありの画面で押した ✕）は、興味あり 1 公演と同じ重さ（REJECT_W = 1）を向きだけ逆にして、その公演の人・種類に割る（recommend.personValues の disliked のうち strong）。好きと分かっている人へ多めに配る割り方は使わない（好きな人ほど強く下げることになるため）。ふつうの興味なし（0）は、これまでどおり興味ありとの比べにだけ使う。
- 重さ 1 は見積もりで、本番のデータでは確かめていない。
- 購入済の公演のカードには ✕ を出さない（持っている券なので）。画面の側は web/app.js。
