---
id: q-native-cutover
type: question
status: open
date: 2026-10-13
title: Worker の画面への切り替えを、日記帳など 4 画面だけ先にするか、全画面がそろってから一度にするか
links:
  - depends_on: native-cutover-map
---
計画書は「全画面を移してから一度だけ切り替える」。4 画面だけ先にすると、その 4 画面は D1 の新しい記録（最初は空）、ほかの画面は Render の記録を見る（native-cutover-map）。
起案者に決めてもらうこと:
1. 4 画面を先に切り替えるか、計画どおり段 2〜4（おすすめ・予定・眺める・探す・設定・登録など）を移してからにするか
2. 「アカウント・記録」の画面（/migration-data/）で入れた records を works に移すか（変換を作るか、捨てるか）
3. Render の記録・見本は移らないことを、利用者にどう伝えるか（移さないこと自体は決めてある）
4. ポスターを Worker で出すか（q-worker-posters）
5. ~~無料枠の CPU 10ms を超えたら有料（Workers Paid）にするか~~ → 有料にはしない（dec-free-tier-only）。超えるなら、その画面は移さず Render のままにする
6. Render をいつ止めるか、デモ版をどうするか（q-demo-trial-design）
どちらの場合も先に要ること（進める）: 本番の D1 に一覧が入ったことを /api/health と rec_meta で確かめる → suggest（結び付ける公演の候補）を Worker に移す → 本物の量で CPU 時間・D1 の行数を測る → 別の Worker（wrangler の env）で NATIVE_UI=all を通しで試す。切り替えは wrangler.jsonc の vars に NATIVE_UI を書いて master に入れる（戻すときはその変更を戻す。D1 に書かれた分は残る）。
