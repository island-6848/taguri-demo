---
id: dec-entity-pages
type: decision
status: adopted
date: 2026-10-19
title: おすすめ理由の太字から、人物・形式ごとのページへ飛べるようにする
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/screens/entity.js
links:
  - affects: comp-cf-worker
---
起案者の依頼（2026-10-19）「おすすめ理由になってる項目の黒太字押したら、各個別ページに飛ぶようにして」。

- 人物の理由（出演・演出など）の太字は `/recommend/person?n=名前&r=役割` へ。ページには、たぐりにある今後の公演（5 件ずつページ送り）、過去の公演（検索と同じ `pastHits`）、自分の観劇記録のうちその名前を含むものを出す
- 形式の理由（原作・ジャンルなど）の太字は `/recommend/kind?a=#軸&w=語` へ。今後の公演を出す
- 経歴・プロフィールは**取得も保存もしない**。Wikipedia と Google の検索へのリンクを置くだけ。自動で要約を取ると新しい外部サービスになり、無料枠と「越えたらどうなるか」を確かめる必要があるうえ、同姓同名を取り違えるおそれがあるため。取るかどうかは起案者が決める
- 無料枠: 新しい保存・定期実行はない。ページを開いたときに D1 を読むだけ（rec_credit・rec_stage・過去公演の検索と同じ量）
