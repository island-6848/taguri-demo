---
id: fix-account-diary-owned-1018
type: finding
status: confirmed
date: 2026-10-18
title: アカウントの「お気に入り」がいつも 0 件だったのは古い表（favourites）だけを数えていたため。アイコン画像が選べなかったのは CSP が blob: を許していなかったため。購入済みは行く日の 0 時に消え、開演まではどこにも出なかった
sources:
  - cloudflare/src/screens/account.js
  - public/_headers
  - web/app.js
  - cloudflare/src/screens/lists.js
  - cloudflare/test/account-stats.test.js
  - cloudflare/test/lists-screen.test.js
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: dec-favourite-role-filter
---
起案者の指示・問い（2026-10-18）「購入済み公演は、観に行く日の公演開始時間過ぎてから未評価に移して」「『これまでの記録』に…『観た回数』のカウントも出して。同箇所で『お気に入り』が常に0件なのなぜ？」「どのアイコン画像選んでも選べないのどうにかして」「日記帳ページ、出演者が3行以上になりそうなら折りたたんでほかN名表記で構わない」「スマホで見るとnullにする✕が改行されてるから、★と同じ列に収めて」。

分かったこと（コードと実行結果で確かめた）:
- お気に入りの数: アカウントの画面は古い表 favourites だけを数えていた。いまのお気に入りは本人の設定（app_setting の declared）に入るので、いつも 0 件だった。lists.loadDeclared（両方を合わせる）で数えるようにした。
- アイコン画像: 画面は選んだ画像を URL.createObjectURL の blob: URL で読んでいたが、サイトの CSP（public/_headers の img-src 'self' data:）が blob: を許していないので、どの画像も読み込みに失敗して「この画像は読めませんでした」になっていた。CSP は緩めず、FileReader で data: URL にして読むようにした。e2e で画像を選んで「アイコンを保存しました」と出ることを確かめた。
- 購入済みの公演: 購入済の一覧からは行く日（または千穐楽）の 0 時に消え、未評価には開演の時刻を過ぎてから入る（行く日の券）か 0 時に入る（券の無いとき）作りで、その日の開演まではどちらにも出なかった。lists.startPassed（行く日が今日より前、または今日で開演の時刻を過ぎた。時刻が分からない回は次の日）に揃えた。

足したもの:
- 観た回数: 作品でまとめず、記録の times と、まとめた別の回の記録（merged）を足した数。
- 日記帳の出演: 出したあとに測り、3 行を越えるなら 3 行に収まる人まで出して「ほか N 名」で開く（app.js foldCastLines）。試験用の公演は出演が短いので、e2e では折りたたまれる場面は通していない。
- 電話の幅（420px 以下）の評価の行: 星を 25px にし、✕ を星のすぐ後ろ、「★4」をその下の行にした。e2e の電話の写しで同じ列に収まるのを見た。
