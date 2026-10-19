---
id: dec-register-optional-date-parts
type: decision
status: adopted
date: 2026-10-19
title: 上演日程は年・月・日を常時表示し、任意入力された項目だけで検索する
sources:
  - cloudflare/src/screens/register-dialog.js
  - cloudflare/src/screens/schedule-filter.js
  - cloudflare/src/screens/settings.js
  - web/app.js
  - cloudflare/test/schedule-filter.test.js
  - cloudflare/test/register-detail.test.js
  - cloudflare/test/register-dialog-browser.js
links:
  - affects: dec-register-run-precision
---
起案者の指示：「細かさの指定、年と月と日の入力欄はデフォルトで出して、任意入力にして、入力されたものだけで調べるようにして（なので指定の細かさのプルダウンは消して）」。

- 指定の細かさのプルダウンを撤去し、年・月・日の数値入力欄を最初から表示する。すべて空欄で開始し、すべて任意とする。空欄はAPIへ送らない。
- 入力された年・月・日をすべて満たす日が、上演期間の中にあれば一致とする。月だけ・日だけ・年と日だけを含む8通りの組み合わせに対応する。全部空欄なら日程で絞らない。
- 年指定が無い月日は年を問わない。日だけなら月も問わない。2月29日はうるう年だけに一致し、2月30日や2025年2月29日など不正な指定は拒否する。検索条件を観劇日には転記しない。
- 古い画面をキャッシュした端末向けに、以前のprecision・完全日付パラメータは互換のため受け付ける。新画面からprecisionは送らない。
- 題名索引と候補数の上限は維持。年があればSQLの期間条件にも使い、日だけ・年なしの条件は上限内の候補に対して最大9年×12か月の計算で照合する。新しい取得・問い合わせ・保存項目・定期実行は増やさない。

検証：関連テスト13件。任意の8通り、空欄、日だけ・年と日のDB検索、年越し、閏年、不正値、入力した項目だけ送ること、観劇日に転記しないことを含む。PC・スマホのブラウザ試験も、最初から3欄が見え、月だけで検索できることを確認する内容へ更新した。
