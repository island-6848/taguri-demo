# システムテスト 準備の段（2026-10-20・ローカル）

[手順書](../system-test-procedure.md) の準備の段で書いた試験と道具を、初めて流した記録。〔dec-system-test-design〕

| 項目 | 内容 |
|---|---|
| 実施者 | CL |
| 対象 | ブランチ `ccr-02edfa98-8mo8xj`（`ce22fb6` に、この記録のコミットで足した試験と道具） |
| 環境 | L（Node 22.22.0・wrangler 4・手元の D1）。CI は Node 24 |
| 無料枠（前・後） | ―（ローカルだけ。本番・Cloudflare には触れていない） |

| ケース | 判定 | 証拠 | メモ |
|---|---|---|---|
| SC-04-01 | OK | `node --test test/st-escape.test.js` | 21 画面すべて 200 で開き、TD-05 はエスケープされて出る。検索の語・人の名前の引数も同じ |
| SC-04-02（ログインの画面） | OK | `st-headers.test.js` | ログインの画面は inline のスクリプトを許さない。元の画面の CSP は 'unsafe-inline'・'unsafe-eval' のまま（分かっている穴〔q-original-ui-csp〕。今より広げないことだけを見る） |
| SC-11-01（L の分） | OK | `st-headers.test.js` | 本番の分（P）は未実施 |
| EN-05-01 | OK | `st-headers.test.js` | ポスターは `private, max-age=604800, immutable` |
| SC-08-01 | OK | `st-owner-only.test.js` | 中継あり・なしの両方で 503 で断り、外への要求 0 件。画面に入口が無い |
| SC-06-01 | OK | `node test/st-log-marker.js` | 目印・復旧コード・セッションの値・Cookie の見出しが、wrangler dev の出力（約 10 KB）に 0 件。要求の行がすべてログにあることも確かめた |
| PF-01-02 | 保留 | `st_measure_screens.mjs --fixture` | 本番の判定は実カタログ（CR）で流してから。手元では records が評価 200〜300 件で 10 ミリ秒の前後〔st-screens-cpu-local-1020〕 |

`npm test` 全体（536 本）は、足した 3 本を含めて通った。

## 分かったこと

- **records の画面の CPU が、評価の多い人で 10 ミリ秒の前後になる。** 手元の値で、本物の機械とは違う。実カタログで測り直すまで PF-01-02 は保留〔st-screens-cpu-local-1020〕
- 作り物の 300 人 × 200 記録（60,300 行）は、手元の D1 で約 14 MB（3,506 ページ）。D1 の 4 GB の上限に対して 0.4%
- 初めの版の `st-log-marker.js` は「ログに要求が届いているか」を `logs.length > 500` で見ていて、ログが wrangler の起動の文だけでも通ってしまった。要求の行を名指しで探すように直した
