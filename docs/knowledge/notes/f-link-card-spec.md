---
id: f-link-card-spec
type: finding
status: unverified
date: 2026-10-19
title: X のカード（summary_large_image）の画像は 2:1 前後・5MB まで、X のタグが無ければ OGP を使う（公式は未確認）
sources:
  - https://soona.co/image-resizer/twitter-spec-guide
  - https://kb.theseoframework.com/kb/twitter-cards-and-x-sharing/
  - https://frontendchecklist.io/rules/seo/twitter-cards
links:
  - affects: dec-link-card
---
分かったこと（検索で出た第三者の解説。X と ogp.me の公式ページは、この環境から名前を引けず開けなかった）:
- `twitter:card` を `summary_large_image` にすると大きな画像のカード。`twitter:*` が無い項目は `og:*` を使う
- 画像は最小 300×157・最大 4096×4096・5MB まで、JPG・PNG・WEBP・GIF。比は 2:1 とする解説と、1200×630（約 1.91:1）や 1200×675 を勧める解説がある。比が違うと中央で切られるという
- og:image は絶対 URL にするのが通例

分からないこと: X のクローラーがリダイレクト（302）を何回たどるか、robots.txt の扱い、カードを何日控えておくか。公式の文書で確かめていない。たぐりは、たどらないクローラーでも出るよう、その場で 200 を返す形にした。
