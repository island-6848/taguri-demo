---
id: peer-synopsis-routine
type: finding
status: unverified
date: 2026-10-15
title: 別のセッションが、あらすじを読む定期実行（毎日 06:07 UTC・40 件、trig_01Y7a7jwMQpEgcCiTdkwwVaK）を作った。Catalog の state の書き戻しは毎回 force push なので、両方の時刻が重ならないことが前提
links:
  - affects: q-synopsis-routine-quota
---
相手のセッション（評価・画面側）の知らせ（2026-10-15 23:19 UTC）による。起案者の指示「あらすじを読む定期実行も作って」。fire ごとに新しいセッションで、Catalog が実行中なら見送り、state ブランチから credits/synopsis_queue.jsonl・synopsis_prompt.txt・themes.jsonl だけを取り、extract_theme_llm.py で 40 件読み、2 つのファイルだけを通常の push で戻す（拒まれたら見送り、force はしない）。待ちが無い日は何もしない（いまは queue が無く themes.jsonl は 0 バイト）。
- 注意（私の見立て）: Catalog の最後の段は state を 1 コミットに作り直して `git push -f` する（catalog.yml）。Catalog は始めに state を取り出すので、06:07 の定期実行が Catalog の前に push した分は残る。Catalog の実行中（ふだん 22:18〜01:15 UTC ごろ）に push されると、最後の force push で消える。定期実行は Catalog の実行中を見送るので、ふつうは重ならない
- 定期実行の中身・権限は自分では確かめていない
