---
id: dec-register-dialog-shared-controls
type: decision
status: adopted
date: 2026-10-19
title: 詳細検索のボタンと入力欄は他ページの共通スタイルを使う
sources:
  - web/style.css
  - cloudflare/src/screens/register-dialog.js
  - cloudflare/test/register-dialog-browser.js
links:
  - affects: fix-register-empty-dialog
---
起案者の指示：「ポップアップのデザイン（ボタンとか）を他ページと同じにして」。

詳細検索だけのボタンと入力欄の装飾をやめ、登録・設定などのページで使う共通セレクタに含める。ボタンは丸い枠線、入力欄は薄い背景と8pxの角丸、ラベルは共通のfld/flにする。閉じる・検索する・候補選択のボタンは同じ規則で描く。ダイアログの枠と余白もカードと揃え、フォーカス表示と既存の無効状態を保つ。

検索・日程条件・連続保存の処理は変えない。配信用CSSを同期する。既存のブラウザ検証を拡張し、PC・スマホでポップアップと通常ページのボタンのフォント・枠線・色・角丸・余白、入力欄の見た目が同じであることを計算済みスタイルで比較する。

外部取得・問い合わせ・保存項目・定期実行は増やさない。
