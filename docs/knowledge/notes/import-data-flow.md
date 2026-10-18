---
id: import-data-flow
type: finding
status: confirmed
date: 2026-10-18
title: 取り込みの読み方ごとに、端末で読むもの・サーバーを通るもの・保存するものが違う。非公開アドレスはサーバーを通る（#91）
sources:
  - cloudflare/src/client/import.js
  - cloudflare/src/client/calendar-callback.js
  - cloudflare/src/screens/import.js
  - cloudflare/src/screens/settings.js
links:
  - affects: dec-import-calendar-mail
---
issue #91（master b8fb7c7 の見直し, 2026-10-18）: 登録画面の①が冒頭で「読み取りはこの端末の中だけ」「カレンダーやメールの中身はたぐりに送りません」と書いていたが、非公開アドレスの道ではアドレスを /api/calendar_ics に送り、Worker（fetchCalendar）がカレンダー全体を取ってきて返している。コードで確かめた流れ:
- Google の許可（API）: 許可の鍵はアドレスの #access_token で戻り、calendar-callback.js がブラウザから Google を直接読む。予定は sessionStorage で登録画面に渡す。鍵も予定もたぐりに送らない
- .ics ファイル・メール（貼る・.eml）: この端末の中だけで読む
- 非公開アドレス: アドレスがたぐりのサーバーを通り、サーバーがカレンダー全体を取ってきて端末に返す。保存はしない（Cloudflare 側のアクセスの記録にアドレスが残るかは確かめていない）
- どの道でも、照合のために題名の候補と日付を /api/import_match に送る（保存しない）。保存するのは /api/import_works で選んだ公演の題名・日付・開演時刻・劇場だけ

画面の説明を道ごとに書き直し、アドレスの欄の横に「サーバーを通ります（保存はしません）」と置いた。「保存しない」と「送らない」を分けて書く。
