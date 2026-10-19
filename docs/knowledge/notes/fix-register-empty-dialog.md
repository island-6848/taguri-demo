---
id: fix-register-empty-dialog
type: finding
status: confirmed
date: 2026-10-19
title: 詳細検索のフォームを画面HTMLに含め、開いた実画面をブラウザで検証する
sources:
  - cloudflare/src/screens/register-dialog.js
  - cloudflare/src/screens/settings.js
  - web/app.js
  - cloudflare/test/register-dialog-markup.test.js
  - cloudflare/test/register-dialog-browser.js
  - cloudflare/test/visual-check.js
links:
  - affects: dec-register-run-precision
---
起案者の報告：「詳細検索の中身作成して」→確認への回答「ポップアップの中身が空になっている」。

従来のフォームはweb/app.jsがクリック時にHTML文字列から生成していた。既存のブラウザ比較チェックは、同じPython製の画面を双方に差し込んで比べるため、このサービス版のポップアップを実際に開く試験ではなかった。以前のフロントエンドの試験も、モックの入力欄を渡して検索処理を試すだけで、実DOMの表示は確認していなかった。

フォームの全項目（公演名・団体名・劇場・上演日程の粒度と年月日）を、registerScreenが返す閉じたdialogに含めるように変更した。JavaScriptは既存のフォームへ動きを結び、開閉する。閉じた後も要素を残し、再度開いたときに送信ハンドラーを重複して結ばない。既存のdata-open-dialogによる開く動作も使えるようにした。

HTMLに項目が揃うことを検査し、CIのブラウザ検証にサービス版の実際のregisterScreenを読み込む通しテストを追加。PC1280px・スマホ390pxで開いた入力欄の可視性、月指定の検索、候補の選択、再表示、Escapeとフォーカス復帰を確認し、スクリーンショットを成果物に残す。ブラウザ試験では合成データとモックAPIを使い、本番のアカウントには書き込まない。

実際に空になっている本番ブラウザのDOMや配信中のJSは、この作業環境からは取得できず、空表示の正確な発生条件は未確定。再発を検出できる実DOMの試験を追加する。外部取得・定期実行・保存項目の追加はない。
