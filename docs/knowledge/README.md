# たぐり ナレッジグラフ

調べたこと・今後調べること・決めたことを 1 件ずつ記録し、つながりで管理する。
**このファイルと `graph.json` は `tools/knowledge/build_graph.py` が作る。手で直さない。**

## 書き足し方

1. `docs/knowledge/notes/<id>.md` を作る（形は `tools/knowledge/build_graph.py` の冒頭）
2. 調べたら `type: finding`。出典 URL を `sources` に、確かめた日を `date` に書く。一次情報（公式文書・実物の確認）で確かめたものだけ `confirmed`。ブログや推測は `unverified`
3. 分からないことは `type: question`（`open`）。答えが出たら答えの finding に `answers: <問いの id>` を書き、問いを `answered` にする
4. 古くなった事実は消さずに `outdated`、取り消した決定は `superseded` にして、新しい方から `supersedes` でつなぐ
5. 計画などの文書（`docs/*.md`）から項目を指すときは `〔id〕` と書く。無い id を指すと検査で失敗する
6. `python3 tools/knowledge/build_graph.py` で索引と図を作り直してからコミットする（CI が `--check` で確かめる）

つながりの種類: `supports`（根拠になる）、`contradicts`（食い違う）、`raises`（新たな問いを生む）、`answers`（答える）、`affects`（影響する）、`depends_on`（前提にする）、`supersedes`（置き換える）、`verifies`（検証項目）

## 図

形: 丸＝調べたこと、六角＝今後調べること、二重枠＝決めたこと、平行四辺形＝仕組みの部品。点線の枠は未確認・提案中。灰色は古い・回答済み・置き換え済み。

```mermaid
flowchart LR
  n0("利用規約は公演情報を第三者へ再配布しないと約束している")
  n1("Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある")
  n2("Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える")
  n3[/"登録・復旧の試行回数の制限（auth.py）"/]
  n4[/"公演カタログの取得と配布（publish_catalog.py）"/]
  n5[/"取得の作法（polite_http.py）"/]
  n6[/"本人の書き出し（/export.json・/data.zip）"/]
  n7[/"画面（web/・config.js）"/]
  n8[/"公開版のサーバー（serve_cloud.py・serve.py）"/]
  n9[/"本人向けのおすすめ計算（user_recommender.py）"/]
  n10[/"利用者の保存先とバックアップ"/]
  n11[/"サービス版の VM（cloudflared・systemd）"/]
  n12("取得元の実際の robots.txt はまだ読めていない")
  n13("Pages と Render は別サイトなので、Cookie が別サイトの扱いになる")
  n14("D1 の無料枠は日ごとの読み書き上限（数値は未確認）")
  n15[["Cloudflare Workers への完全移行は今は見送る"]]
  n16[["デモ版は Render の無料プランのまま残す"]]
  n17[["デモ版とサービス版を分ける"]]
  n18[["独自ドメインを取り、画面と API を同じドメインの下に置く"]]
  n19[["取得はすべて polite_http を通す"]]
  n20[["サービス版を Render の有料サービスで立てる"]]
  n21[["サービス版は空から始め、デモの記録を移さない"]]
  n22[["サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く"]]
  n23("見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）")
  n24("LLM の呼び出しには月の上限がある（既定 300 回）")
  n25("Gmail の読み取りは制限付きの権限で、毎年の第三者の審査が要る")
  n26("test_digest と test_impressions は以前から失敗している")
  n27("Oracle Always Free は ARM の VM とディスクが無料。ただし放置判定で回収されうる")
  n28("GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている")
  n29("公開版の書き出しが他の利用者の記録まで渡していた（修正済み）")
  n30{{"検証中に自分だけを通す方法（Cloudflare Access の無料枠）"}}
  n31{{"CF-Connecting-IP をどう信頼するか"}}
  n32{{"Tunnel の公式の制限・料金・必要な設定"}}
  n33{{"将来の移行に向けた D1 と Python Workers の制限"}}
  n34{{"どのドメインをどこで取るか"}}
  n35{{"今の EC2 の種類・月額・無料期間"}}
  n36{{"無料で使える外形監視と通知"}}
  n37{{"バックアップをどこに、どう暗号化して、いつまで置くか"}}
  n38{{"Oracle の公式の無料枠・回収の条件・従量課金にした場合の扱い"}}
  n39{{"個人情報保護法で何が求められるか"}}
  n40{{"サーバーの Python を何版に揃えるか"}}
  n41{{"R2 の公式料金と、今の boto3 のコードで読み書きできるか"}}
  n42{{"Render の無料プランでサービス版を動かせるか"}}
  n43{{"Safari で Cookie が通るか（実機）"}}
  n44{{"取得元の利用規約・robots.txt・ポスター画像の権利"}}
  n45{{"サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか"}}
  n46{{"VM でおすすめが 3 秒以内に開くか"}}
  n47{{"Cloudflare の無料枠だけで、今のコードのまま動かせるか"}}
  n48("R2 は 10GB まで無料で、取り出しの通信料がかからない")
  n49("おすすめは開くたびに全候補を計算している")
  n50("Render の無料プランは永続ディスクを付けられない")
  n51("Render の無料プランは 15 分でスリープし、起動に約 1 分かかる")
  n52("Render の有料プランならスリープせずディスクも付く（単価は二次情報）")
  n53("Python の robotparser は小数の Crawl-delay を読めない")
  n54("サービス版の保存先の検査が Render を前提にしている")
  n55("バックアップの検査が Python 3.13 では 1 件失敗する")
  n56("サーバーは標準ライブラリの http.server と sqlite3 で書いてある")
  n57("試行回数の制限は接続元のアドレスで数えている")
  n58("Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで")
  n0 -- 新たな問いを生む --> n44
  n0 -- 影響する --> n4
  n1 -- 根拠になる --> n22
  n1 -- 根拠になる --> n18
  n1 -- 新たな問いを生む --> n32
  n2 -- 影響する --> n3
  n2 -- 新たな問いを生む --> n31
  n11 -- 前提にする --> n45
  n12 -- 新たな問いを生む --> n44
  n13 -- 根拠になる --> n18
  n13 -- 新たな問いを生む --> n43
  n13 -- 影響する --> n7
  n14 -- 新たな問いを生む --> n33
  n15 -- 影響する --> n9
  n16 -- 前提にする --> n17
  n17 -- 影響する --> n8
  n17 -- 影響する --> n7
  n18 -- 影響する --> n7
  n18 -- 前提にする --> n34
  n19 -- 影響する --> n5
  n21 -- 前提にする --> n17
  n22 -- 置き換える --> n20
  n22 -- 前提にする --> n18
  n22 -- 影響する --> n8
  n22 -- 影響する --> n3
  n22 -- 影響する --> n11
  n23 -- 影響する --> n9
  n24 -- 影響する --> n4
  n27 -- 新たな問いを生む --> n38
  n27 -- 根拠になる --> n22
  n28 -- 影響する --> n7
  n29 -- 影響する --> n6
  n30 -- 前提にする --> n22
  n33 -- 前提にする --> n15
  n37 -- 前提にする --> n41
  n41 -- 前提にする --> n45
  n43 -- 前提にする --> n18
  n45 -- 前提にする --> n38
  n45 -- 前提にする --> n35
  n46 -- 前提にする --> n45
  n48 -- 根拠になる --> n22
  n48 -- 新たな問いを生む --> n41
  n48 -- 影響する --> n4
  n49 -- 根拠になる --> n15
  n49 -- 影響する --> n9
  n49 -- 答える --> n47
  n50 -- 根拠になる --> n22
  n50 -- 答える --> n42
  n50 -- 影響する --> n10
  n51 -- 根拠になる --> n22
  n51 -- 根拠になる --> n16
  n52 -- 根拠になる --> n20
  n53 -- 影響する --> n5
  n54 -- 影響する --> n8
  n54 -- 影響する --> n11
  n55 -- 新たな問いを生む --> n40
  n55 -- 影響する --> n10
  n56 -- 根拠になる --> n15
  n56 -- 根拠になる --> n22
  n56 -- 答える --> n47
  n57 -- 影響する --> n3
  n57 -- 新たな問いを生む --> n31
  n58 -- 根拠になる --> n15
  n58 -- 答える --> n47
  class n0 finding_confirmed
  class n1 finding_unverified
  class n2 finding_unverified
  class n3 component_current
  class n4 component_current
  class n5 component_current
  class n6 component_current
  class n7 component_current
  class n8 component_current
  class n9 component_current
  class n10 component_current
  class n11 component_planned
  class n12 finding_unverified
  class n13 finding_confirmed
  class n14 finding_unverified
  class n15 decision_adopted
  class n16 decision_proposed
  class n17 decision_adopted
  class n18 decision_proposed
  class n19 decision_adopted
  class n20 decision_superseded
  class n21 decision_adopted
  class n22 decision_adopted
  class n23 finding_unverified
  class n24 finding_confirmed
  class n25 finding_confirmed
  class n26 finding_confirmed
  class n27 finding_unverified
  class n28 finding_confirmed
  class n29 finding_confirmed
  class n30 question_open
  class n31 question_open
  class n32 question_open
  class n33 question_open
  class n34 question_open
  class n35 question_open
  class n36 question_open
  class n37 question_open
  class n38 question_open
  class n39 question_open
  class n40 question_open
  class n41 question_open
  class n42 question_answered
  class n43 question_open
  class n44 question_open
  class n45 question_open
  class n46 question_open
  class n47 question_answered
  class n48 finding_unverified
  class n49 finding_confirmed
  class n50 finding_confirmed
  class n51 finding_confirmed
  class n52 finding_unverified
  class n53 finding_confirmed
  class n54 finding_confirmed
  class n55 finding_unverified
  class n56 finding_confirmed
  class n57 finding_confirmed
  class n58 finding_confirmed
  classDef finding_confirmed fill:#e6f4ea,stroke:#2e7d32
  classDef finding_unverified fill:#fff8e1,stroke:#b26a00,stroke-dasharray:4 3
  classDef finding_outdated fill:#eeeeee,stroke:#9e9e9e
  classDef question_open fill:#fdecea,stroke:#c62828
  classDef question_answered fill:#eeeeee,stroke:#9e9e9e
  classDef question_dropped fill:#eeeeee,stroke:#9e9e9e
  classDef decision_adopted fill:#e3f2fd,stroke:#1565c0
  classDef decision_proposed fill:#e3f2fd,stroke:#1565c0,stroke-dasharray:4 3
  classDef decision_superseded fill:#eeeeee,stroke:#9e9e9e
  classDef component_current fill:#f3e5f5,stroke:#6a1b9a
  classDef component_planned fill:#f3e5f5,stroke:#6a1b9a,stroke-dasharray:4 3
  classDef component_retired fill:#eeeeee,stroke:#9e9e9e
```

## 今後調べること（16 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [検証中に自分だけを通す方法（Cloudflare Access の無料枠）](notes/q-cf-access.md) | 未着手 | 2026-10-13 | S30 | 前提にする → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) |
| [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) | 未着手 | 2026-10-13 | S13 | [Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える](notes/cf-tunnel-origin-localhost.md) が新たな問いを生む<br>[試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) が新たな問いを生む |
| [Tunnel の公式の制限・料金・必要な設定](notes/q-cf-tunnel-official.md) | 未着手 | 2026-10-13 | S22 | [Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が新たな問いを生む |
| [将来の移行に向けた D1 と Python Workers の制限](notes/q-d1-python-workers.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [Cloudflare Workers への完全移行は今は見送る](notes/dec-defer-workers.md)<br>[D1 の無料枠は日ごとの読み書き上限（数値は未確認）](notes/d1-free-limits.md) が新たな問いを生む |
| [どのドメインをどこで取るか](notes/q-domain.md) | 未着手 | 2026-10-13 | S04 | [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) が前提にする |
| [今の EC2 の種類・月額・無料期間](notes/q-ec2-cost.md) | 未着手 | 2026-10-13 | S12 | [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする |
| [無料で使える外形監視と通知](notes/q-monitoring.md) | 未着手 | 2026-10-13 | S22, S23 | ─ |
| [バックアップをどこに、どう暗号化して、いつまで置くか](notes/q-offsite-backup.md) | 未着手 | 2026-10-13 | S07, S10 | 前提にする → [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md) |
| [Oracle の公式の無料枠・回収の条件・従量課金にした場合の扱い](notes/q-oracle-official.md) | 未着手 | 2026-10-13 | S12 | [Oracle Always Free は ARM の VM とディスクが無料。ただし放置判定で回収されうる](notes/oracle-always-free.md) が新たな問いを生む<br>[サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする |
| [個人情報保護法で何が求められるか](notes/q-privacy-law.md) | 未着手 | 2026-10-13 | S10, S25 | ─ |
| [サーバーの Python を何版に揃えるか](notes/q-python-version.md) | 未着手 | 2026-10-13 | S07 | [バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) が新たな問いを生む |
| [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md)<br>[バックアップをどこに、どう暗号化して、いつまで置くか](notes/q-offsite-backup.md) が前提にする<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が新たな問いを生む |
| [Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md) | 未着手 | 2026-10-13 | S04, S19 | 前提にする → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>[Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が新たな問いを生む |
| [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md) | 未着手 | 2026-10-13 | S11, S24 | [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) が新たな問いを生む<br>[取得元の実際の robots.txt はまだ読めていない](notes/corich-robots-unchecked.md) が新たな問いを生む |
| [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) | 未着手 | 2026-10-13 | S12 | 前提にする → [Oracle の公式の無料枠・回収の条件・従量課金にした場合の扱い](notes/q-oracle-official.md)<br>前提にする → [今の EC2 の種類・月額・無料期間](notes/q-ec2-cost.md)<br>[サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) が前提にする<br>[R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md) が前提にする<br>[VM でおすすめが 3 秒以内に開くか](notes/q-vm-performance.md) が前提にする |
| [VM でおすすめが 3 秒以内に開くか](notes/q-vm-performance.md) | 未着手 | 2026-10-13 | S20 | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) |

## 決めたこと（8 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [デモ版とサービス版を分ける](notes/dec-edition-split.md) | 採用 | 2026-10-12 | S01, S09 | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [画面（web/・config.js）](notes/comp-frontend.md)<br>[デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) が前提にする<br>[サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md) が前提にする |
| [取得はすべて polite_http を通す](notes/dec-polite-crawling.md) | 採用 | 2026-10-12 | S15, S24 | 影響する → [取得の作法（polite_http.py）](notes/comp-crawler.md) |
| [サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md) | 採用 | 2026-10-12 | S01 | 前提にする → [デモ版とサービス版を分ける](notes/dec-edition-split.md) |
| [Cloudflare Workers への完全移行は今は見送る](notes/dec-defer-workers.md) | 採用 | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[将来の移行に向けた D1 と Python Workers の制限](notes/q-d1-python-workers.md) が前提にする<br>[おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が根拠になる<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が根拠になる<br>[Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) が根拠になる |
| [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) | 採用 | 2026-10-13 | S02, S13, S22 | 置き換える → [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md)<br>前提にする → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>影響する → [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md)<br>[Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が根拠になる<br>[Oracle Always Free は ARM の VM とディスクが無料。ただし放置判定で回収されうる](notes/oracle-always-free.md) が根拠になる<br>[検証中に自分だけを通す方法（Cloudflare Access の無料枠）](notes/q-cf-access.md) が前提にする<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が根拠になる<br>[Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が根拠になる<br>[Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) が根拠になる<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が根拠になる |
| [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) | 提案 | 2026-10-13 | ─ | 前提にする → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>[Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) が根拠になる |
| [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) | 提案 | 2026-10-13 | S04, S09 | 影響する → [画面（web/・config.js）](notes/comp-frontend.md)<br>前提にする → [どのドメインをどこで取るか](notes/q-domain.md)<br>[Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が根拠になる<br>[Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が根拠になる<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が前提にする<br>[Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md) が前提にする |
| [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md) | 置き換え済み | 2026-10-13 | ─ | [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が置き換える<br>[Render の有料プランならスリープせずディスクも付く（単価は二次情報）](notes/render-paid-disk-cost.md) が根拠になる |

## 調べたこと（24 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [Gmail の読み取りは制限付きの権限で、毎年の第三者の審査が要る](notes/gmail-restricted-scope.md) | 確認済み | 2026-08-28 | ─ | ─ |
| [test_digest と test_impressions は以前から失敗している](notes/legacy-test-failures.md) | 確認済み | 2026-10-12 | ─ | ─ |
| [GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている](notes/pages-404-fallback.md) | 確認済み | 2026-10-12 | S09 | 影響する → [画面（web/・config.js）](notes/comp-frontend.md) |
| [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) | 確認済み | 2026-10-12 | S20 | 根拠になる → [Cloudflare Workers への完全移行は今は見送る](notes/dec-defer-workers.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) |
| [Python の robotparser は小数の Crawl-delay を読めない](notes/robotparser-decimal-delay.md) | 確認済み | 2026-10-12 | ─ | 影響する → [取得の作法（polite_http.py）](notes/comp-crawler.md) |
| [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) | 確認済み | 2026-10-13 | S11 | 新たな問いを生む → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) | 確認済み | 2026-10-13 | S04 | 根拠になる → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>新たな問いを生む → [Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md)<br>影響する → [画面（web/・config.js）](notes/comp-frontend.md) |
| [LLM の呼び出しには月の上限がある（既定 300 回）](notes/gemini-budget-cap.md) | 確認済み | 2026-10-13 | S27 | 影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [公開版の書き出しが他の利用者の記録まで渡していた（修正済み）](notes/public-export-leak.md) | 確認済み | 2026-10-13 | S03 | 影響する → [本人の書き出し（/export.json・/data.zip）](notes/comp-export.md) |
| [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) | 確認済み | 2026-10-13 | S02 | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>答える → [Render の無料プランでサービス版を動かせるか](notes/q-render-free-viable.md)<br>影響する → [利用者の保存先とバックアップ](notes/comp-state-storage.md) |
| [Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>根拠になる → [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) |
| [サービス版の保存先の検査が Render を前提にしている](notes/serve-cloud-render-guard.md) | 確認済み | 2026-10-13 | S02 | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) |
| [サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Cloudflare Workers への完全移行は今は見送る](notes/dec-defer-workers.md)<br>根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) |
| [試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) | 確認済み | 2026-10-13 | S13 | 影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>新たな問いを生む → [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) |
| [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Cloudflare Workers への完全移行は今は見送る](notes/dec-defer-workers.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) |
| [取得元の実際の robots.txt はまだ読めていない](notes/corich-robots-unchecked.md) | 未確認 | 2026-10-12 | S24 | 新たな問いを生む → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md) |
| [見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）](notes/demo-seed-link-rate.md) | 未確認 | 2026-10-12 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>根拠になる → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>新たな問いを生む → [Tunnel の公式の制限・料金・必要な設定](notes/q-cf-tunnel-official.md) |
| [Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える](notes/cf-tunnel-origin-localhost.md) | 未確認 | 2026-10-13 | S13 | 影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>新たな問いを生む → [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) |
| [D1 の無料枠は日ごとの読み書き上限（数値は未確認）](notes/d1-free-limits.md) | 未確認 | 2026-10-13 | ─ | 新たな問いを生む → [将来の移行に向けた D1 と Python Workers の制限](notes/q-d1-python-workers.md) |
| [Oracle Always Free は ARM の VM とディスクが無料。ただし放置判定で回収されうる](notes/oracle-always-free.md) | 未確認 | 2026-10-13 | ─ | 新たな問いを生む → [Oracle の公式の無料枠・回収の条件・従量課金にした場合の扱い](notes/q-oracle-official.md)<br>根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) |
| [R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>新たな問いを生む → [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [Render の有料プランならスリープせずディスクも付く（単価は二次情報）](notes/render-paid-disk-cost.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md) |
| [バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) | 未確認 | 2026-10-13 | ─ | 新たな問いを生む → [サーバーの Python を何版に揃えるか](notes/q-python-version.md)<br>影響する → [利用者の保存先とバックアップ](notes/comp-state-storage.md) |

## 仕組みの部品（9 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [取得の作法（polite_http.py）](notes/comp-crawler.md) | 現行 | 2026-10-12 | ─ | [取得はすべて polite_http を通す](notes/dec-polite-crawling.md) が影響する<br>[Python の robotparser は小数の Crawl-delay を読めない](notes/robotparser-decimal-delay.md) が影響する |
| [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) | 現行 | 2026-10-12 | ─ | [Cloudflare Workers への完全移行は今は見送る](notes/dec-defer-workers.md) が影響する<br>[見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）](notes/demo-seed-link-rate.md) が影響する<br>[おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が影響する |
| [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md) | 現行 | 2026-10-13 | ─ | [Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える](notes/cf-tunnel-origin-localhost.md) が影響する<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が影響する<br>[試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) が影響する |
| [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) | 現行 | 2026-10-13 | ─ | [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) が影響する<br>[LLM の呼び出しには月の上限がある（既定 300 回）](notes/gemini-budget-cap.md) が影響する<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が影響する |
| [本人の書き出し（/export.json・/data.zip）](notes/comp-export.md) | 現行 | 2026-10-13 | ─ | [公開版の書き出しが他の利用者の記録まで渡していた（修正済み）](notes/public-export-leak.md) が影響する |
| [画面（web/・config.js）](notes/comp-frontend.md) | 現行 | 2026-10-13 | ─ | [Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が影響する<br>[デモ版とサービス版を分ける](notes/dec-edition-split.md) が影響する<br>[独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) が影響する<br>[GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている](notes/pages-404-fallback.md) が影響する |
| [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md) | 現行 | 2026-10-13 | ─ | [デモ版とサービス版を分ける](notes/dec-edition-split.md) が影響する<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が影響する<br>[サービス版の保存先の検査が Render を前提にしている](notes/serve-cloud-render-guard.md) が影響する |
| [利用者の保存先とバックアップ](notes/comp-state-storage.md) | 現行 | 2026-10-13 | ─ | [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が影響する<br>[バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) が影響する |
| [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) | 予定 | 2026-10-13 | ─ | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md)<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が影響する<br>[サービス版の保存先の検査が Render を前提にしている](notes/serve-cloud-render-guard.md) が影響する |

## 答えの出た問い・取り下げた問い（2 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [Render の無料プランでサービス版を動かせるか](notes/q-render-free-viable.md) | 回答済み | 2026-10-13 | ─ | [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が答える |
| [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) | 回答済み | 2026-10-13 | ─ | [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が答える<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が答える<br>[Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) が答える |
