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
  n0("AWS の無料枠は 2025 年 7 月 15 日以降の新しい口座ではクレジット制（最大 200 ドル・6 か月）")
  n1("AWS は公開 IPv4 アドレス 1 つにつき 1 時間 0.005 ドル（月 3.6 ドルほど）かかる")
  n2("カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした")
  n3("利用規約は公演情報を第三者へ再配布しないと約束している")
  n4("Cloudflare Access は 50 人まで無料（古い公式資料）")
  n5("この作業環境からは Cloudflare・Firebase の公式文書や外部サイトが読めない")
  n6("Cloudflare Registrar では .jp を取れない。DNS だけ Cloudflare に置くことはできる")
  n7("Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある")
  n8("Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える")
  n9("Claude の GitHub アプリは taguri-crawler にまだ入っていない")
  n10(".com の卸値は 2026 年 11 月 1 日から年 10.97 ドルに上がる")
  n11[/"登録・復旧の試行回数の制限（auth.py）"/]
  n12[/"公演カタログの取得と配布（publish_catalog.py）"/]
  n13[/"Cloudflare Worker（cloudflare/src/worker.js）"/]
  n14[/"取得の作法（polite_http.py）"/]
  n15[/"Cloudflare D1（taguri-demo データベース）"/]
  n16[/"本人の書き出し（/export.json・/data.zip）"/]
  n17[/"ログイン：Firebase Authentication（Google・メールリンク）"/]
  n18[/"画面（web/・config.js）"/]
  n19[/"元の画面の Worker 版（cloudflare/src/screens/）"/]
  n20[/"ログイン：パスキー（Google を使わない人向け）"/]
  n21[/"公開版のサーバー（serve_cloud.py・serve.py）"/]
  n22[/"推薦の索引の作成（build_recommend_index.py）"/]
  n23[/"本人向けのおすすめ計算（user_recommender.py）"/]
  n24[/"利用者の保存先とバックアップ"/]
  n25[/"サービス版の VM（cloudflared・systemd）"/]
  n26("CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している")
  n27("取得元の実際の robots.txt はまだ読めていない")
  n28("CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）")
  n29("取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）")
  n30("Pages と Render は別サイトなので、Cookie が別サイトの扱いになる")
  n31("D1 の無料プランは 1 つのデータベースが 500MB まで（二次情報）")
  n32("D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB")
  n33("D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）")
  n34("D1 は 1 つの問い合わせに 100 個までの値しか渡せず、1 文は 100 KB まで")
  n35("D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）")
  n36[["アカウント削除は「削除」の入力と直近 10 分以内のログインを求める"]]
  n37[["取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）"]]
  n38[["Cloudflare Workers への完全移行は今は見送る（見直し中）"]]
  n39[["デモ版は Render の無料プランのまま残す"]]
  n40[["デモ版は、触れるがデータを持たないお試し版にする"]]
  n41[["デモ版とサービス版を分ける"]]
  n42[["会員ログインは Firebase Authentication にする"]]
  n43[["画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る"]]
  n44[["Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない"]]
  n45[["運営者名は @return1_end（X）にする"]]
  n46[["独自ドメインを取り、画面と API を同じドメインの下に置く"]]
  n47[["Google を使いたくない人のために、パスキーを新しく作る"]]
  n48[["取得はすべて polite_http を通す"]]
  n49[["おすすめ（人物得点）は索引をバッチで作り、Worker で計算する"]]
  n50[["Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）"]]
  n51[["サービス版を Render の有料サービスで立てる"]]
  n52[["1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる"]]
  n53[["記録を公演に結び付ける検索には、公開カタログの公演だけを出す"]]
  n54[["サービス版は空から始め、デモの記録を移さない"]]
  n55[["ログインしていない人に見せるのは「ログイン」と「たぐりとは」だけ"]]
  n56[["サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く"]]
  n57[["無料で起動を速くするため、Cloudflare Workers＋D1 で動かす"]]
  n58("見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）")
  n59("東京の t4g.micro は 1 時間 0.0108 ドル（月 8 ドルほど）、t3.micro は 0.0136 ドル")
  n60("Firebase の Web 用 API キーは秘密ではない（使える範囲は承認済みドメインとキーの制限で絞る）")
  n61("LLM の呼び出しには月の上限がある（既定 300 回）")
  n62("GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた")
  n63("非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料")
  n64("公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる")
  n65("この作業環境の GitHub 連携では、新しいリポジトリを作れない")
  n66("GitHub Actions の定期実行は遅れたり、混雑時に飛ばされたりする")
  n67("公開リポジトリでは GitHub Actions の標準の実行環境が無料。ただし 60 日動きが無いと定期実行が止まる")
  n68("Gmail の読み取りは制限付きの権限で、毎年の第三者の審査が要る")
  n69(".jp は年 4,000 円前後（税の扱い・年額かは未確認）")
  n70("test_digest と test_impressions は以前から失敗している")
  n71("Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない")
  n72("AWS はもう使っていない")
  n73("EC2 は無い")
  n74("Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる")
  n75("GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている")
  n76("パスキーはドメインに結び付くので、ドメインを変えると使えなくなる")
  n77("本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている")
  n78("本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）")
  n79("公開版の書き出しが他の利用者の記録まで渡していた（修正済み）")
  n80("Python の画面は一時保存先・固定日付・通信なしで、テストの中から動かせる")
  n81("別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている")
  n82{{"今の公演カタログ（S3）は、いつ・どこで作られたものか"}}
  n83{{"取得したカタログを Cloudflare 版（D1）にどう届けるか"}}
  n84{{"検証中に自分だけを通す方法（Cloudflare Access の無料枠）"}}
  n85{{"CF-Connecting-IP をどう信頼するか"}}
  n86{{"Tunnel の公式の制限・料金・必要な設定"}}
  n87{{"問い合わせ用のメールアドレス"}}
  n88{{"CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか"}}
  n89{{"CoRich のサイトマップから、これからの公演を見つけられるか"}}
  n90{{"公演情報の取得処理をどこで動かすか"}}
  n91{{"取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定"}}
  n92{{"D1 のバックアップと復元をどうするか"}}
  n93{{"Python Workers の CPU の制限と成熟度"}}
  n94{{"Render を止めたあと、デモ版（見本の記録で試す版）をどうするか"}}
  n95{{"データを持たないお試し版をどう作るか"}}
  n96{{"サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか"}}
  n97{{"どのドメインをどこで取るか"}}
  n98{{"今の EC2 の種類・口座の作成日・月額"}}
  n99{{"Firebase Authentication の無料枠の正確な範囲（メールリンク・利用者数）"}}
  n100{{"Firebase の API キーに制限（Web サイト・使う API）を掛けたか"}}
  n101{{"アカウント削除で Firebase 側の利用者も本当に消えているか"}}
  n102{{"Worker の依存とログイン画面の組み立てを再現できるようにするか（lockfile）"}}
  n103{{"メールリンクのログインで、メールアドレスを端末に残してよいか"}}
  n104{{"移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）"}}
  n105{{"画面の移行の続き（段 1〜5）をどのセッションが受け持つか"}}
  n106{{"無料で使える外形監視と通知"}}
  n107{{"D1 のバックアップを、Time Travel の期間より長くどこに残すか"}}
  n108{{"Oracle の公式の無料枠と回収の条件"}}
  n109{{"Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか"}}
  n110{{"元の画面の Content-Security-Policy を強められるか"}}
  n111{{"パスキーは実機（iPhone・Android・Mac・Windows）で登録・ログインできるか"}}
  n112{{"昔の公演を、公開情報だけで探せるようにするにはどうするか"}}
  n113{{"個人情報保護法で何が求められるか"}}
  n114{{"本番に deploy するブランチをどれにするか（PR のブランチのままにしない）"}}
  n115{{"サーバーの Python を何版に揃えるか"}}
  n116{{"R2 の公式料金と、今の boto3 のコードで読み書きできるか"}}
  n117{{"ログイン・登録・検索の回数制限を Worker でどう掛けるか"}}
  n118{{"実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか"}}
  n119{{"Render の無料プランでサービス版を動かせるか"}}
  n120{{"Render のデモ版は、起動し直すと動かなくなるのではないか"}}
  n121{{"Safari で Cookie が通るか（実機）"}}
  n122{{"取得元の利用規約・robots.txt・ポスター画像の権利"}}
  n123{{"サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか"}}
  n124{{"VM でおすすめが 3 秒以内に開くか"}}
  n125{{"無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか"}}
  n126{{"移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか"}}
  n127{{"Cloudflare の無料枠だけで、今のコードのまま動かせるか"}}
  n128("R2 は 10GB まで無料で、取り出しの通信料がかからない")
  n129("おすすめは開くたびに全候補を計算している")
  n130("Worker の推薦は Python（person-feedback-v1）と同じ結果を出す")
  n131("Render の無料プランは永続ディスクを付けられない")
  n132("Render の無料プランは 15 分でスリープし、起動に約 1 分かかる")
  n133("Render の有料プランならスリープせずディスクも付く（単価は二次情報）")
  n134("Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている")
  n135("元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）")
  n136("Python の robotparser は小数の Crawl-delay を読めない")
  n137("1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）")
  n138("サービス版の保存先の検査が Render を前提にしている")
  n139("バックアップの検査が Python 3.13 では 1 件失敗する")
  n140("サーバーは標準ライブラリの http.server と sqlite3 で書いてある")
  n141("試行回数の制限は接続元のアドレスで数えている")
  n142("題名の正規化（title_key）は JS でも Python と同じにできる")
  n143("Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）")
  n144("push するたびに Workers Builds が D1 の migration を当ててから deploy する")
  n145("コミットの ✗ は Workers Builds が cloudflare/ の無い master を組もうとして失敗していたため")
  n146("Workers の定期実行は、無料プランだと 1 回あたり CPU 10 ミリ秒・外部への要求 50 回まで")
  n147("別の作業で、Workers＋D1 の版が workers.dev で動き始めている")
  n148("Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで")
  n149("Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる")
  n150("Workers の静的ファイルへの要求は無料・無制限で、要求数の上限に数えない")
  n0 -- 影響する --> n98
  n1 -- 影響する --> n98
  n2 -- 影響する --> n82
  n2 -- 影響する --> n106
  n3 -- 新たな問いを生む --> n122
  n3 -- 影響する --> n12
  n4 -- 影響する --> n84
  n6 -- 影響する --> n97
  n7 -- 根拠になる --> n56
  n7 -- 根拠になる --> n46
  n7 -- 新たな問いを生む --> n86
  n8 -- 影響する --> n11
  n8 -- 新たな問いを生む --> n85
  n9 -- 影響する --> n91
  n10 -- 影響する --> n97
  n15 -- 影響する --> n24
  n19 -- 影響する --> n21
  n19 -- 影響する --> n18
  n22 -- 前提にする --> n12
  n22 -- 影響する --> n23
  n25 -- 前提にする --> n123
  n26 -- 影響する --> n122
  n26 -- 置き換える --> n27
  n27 -- 新たな問いを生む --> n122
  n28 -- 答える --> n88
  n28 -- 影響する --> n37
  n29 -- 影響する --> n90
  n30 -- 根拠になる --> n46
  n30 -- 新たな問いを生む --> n121
  n30 -- 影響する --> n18
  n31 -- 影響する --> n137
  n32 -- 影響する --> n93
  n32 -- 影響する --> n96
  n33 -- 答える --> n93
  n33 -- 新たな問いを生む --> n118
  n33 -- 根拠になる --> n32
  n34 -- 影響する --> n22
  n35 -- 影響する --> n107
  n35 -- 影響する --> n147
  n36 -- 影響する --> n15
  n36 -- 新たな問いを生む --> n101
  n37 -- 答える --> n90
  n37 -- 前提にする --> n63
  n37 -- 前提にする --> n64
  n37 -- 前提にする --> n29
  n38 -- 影響する --> n23
  n38 -- 前提にする --> n96
  n39 -- 前提にする --> n41
  n40 -- 答える --> n94
  n40 -- 影響する --> n41
  n40 -- 置き換える --> n39
  n41 -- 影響する --> n21
  n41 -- 影響する --> n18
  n42 -- 影響する --> n17
  n42 -- 新たな問いを生む --> n100
  n42 -- 新たな問いを生む --> n99
  n43 -- 答える --> n105
  n43 -- 前提にする --> n50
  n43 -- 影響する --> n71
  n44 -- 根拠になる --> n54
  n44 -- 前提にする --> n131
  n46 -- 影響する --> n18
  n46 -- 前提にする --> n97
  n47 -- 影響する --> n20
  n47 -- 新たな問いを生む --> n111
  n48 -- 影響する --> n14
  n49 -- 置き換える --> n129
  n49 -- 前提にする --> n130
  n49 -- 影響する --> n23
  n50 -- 食い違う --> n38
  n50 -- 食い違う --> n56
  n50 -- 前提にする --> n135
  n50 -- 影響する --> n19
  n50 -- 影響する --> n21
  n50 -- 影響する --> n96
  n52 -- 影響する --> n96
  n52 -- 前提にする --> n118
  n52 -- 前提にする --> n90
  n53 -- 新たな問いを生む --> n112
  n54 -- 前提にする --> n41
  n55 -- 影響する --> n13
  n56 -- 置き換える --> n51
  n56 -- 前提にする --> n46
  n56 -- 影響する --> n21
  n56 -- 影響する --> n11
  n56 -- 影響する --> n25
  n57 -- 答える --> n96
  n57 -- 置き換える --> n38
  n57 -- 置き換える --> n56
  n57 -- 食い違う --> n38
  n57 -- 前提にする --> n148
  n57 -- 影響する --> n13
  n57 -- 影響する --> n96
  n58 -- 影響する --> n23
  n59 -- 影響する --> n98
  n60 -- 新たな問いを生む --> n100
  n61 -- 影響する --> n12
  n62 -- 影響する --> n91
  n62 -- 新たな問いを生む --> n88
  n62 -- 影響する --> n48
  n63 -- 影響する --> n90
  n64 -- 影響する --> n90
  n64 -- 影響する --> n3
  n65 -- 影響する --> n37
  n65 -- 新たな問いを生む --> n91
  n66 -- 影響する --> n90
  n67 -- 新たな問いを生む --> n90
  n69 -- 影響する --> n97
  n71 -- 影響する --> n50
  n71 -- 新たな問いを生む --> n105
  n71 -- 新たな問いを生む --> n104
  n72 -- 影響する --> n37
  n72 -- 新たな問いを生む --> n120
  n72 -- 新たな問いを生む --> n83
  n72 -- 影響する --> n82
  n73 -- 答える --> n98
  n73 -- 新たな問いを生む --> n82
  n73 -- 影響する --> n90
  n73 -- 影響する --> n118
  n73 -- 影響する --> n50
  n73 -- 影響する --> n12
  n74 -- 答える --> n108
  n74 -- 新たな問いを生む --> n109
  n74 -- 根拠になる --> n56
  n75 -- 影響する --> n18
  n76 -- 影響する --> n97
  n76 -- 根拠になる --> n46
  n77 -- 新たな問いを生む --> n114
  n78 -- 答える --> n114
  n78 -- 置き換える --> n77
  n78 -- 影響する --> n104
  n79 -- 影響する --> n16
  n80 -- 根拠になる --> n50
  n81 -- 影響する --> n96
  n81 -- 新たな問いを生む --> n93
  n82 -- 前提にする --> n90
  n83 -- 前提にする --> n118
  n83 -- 前提にする --> n72
  n84 -- 前提にする --> n56
  n87 -- 前提にする --> n45
  n88 -- 前提にする --> n62
  n88 -- 影響する --> n122
  n89 -- 前提にする --> n26
  n90 -- 前提にする --> n98
  n91 -- 前提にする --> n37
  n92 -- 影響する --> n15
  n92 -- 前提にする --> n107
  n94 -- 前提にする --> n50
  n94 -- 影響する --> n41
  n95 -- 前提にする --> n40
  n96 -- 前提にする --> n118
  n96 -- 前提にする --> n123
  n97 -- 前提にする --> n96
  n102 -- 影響する --> n13
  n103 -- 影響する --> n17
  n104 -- 前提にする --> n114
  n104 -- 影響する --> n71
  n105 -- 前提にする --> n50
  n107 -- 前提にする --> n116
  n110 -- 影響する --> n19
  n112 -- 前提にする --> n48
  n112 -- 前提にする --> n3
  n116 -- 前提にする --> n123
  n117 -- 前提にする --> n11
  n117 -- 影響する --> n13
  n118 -- 前提にする --> n98
  n120 -- 前提にする --> n72
  n120 -- 影響する --> n95
  n121 -- 前提にする --> n46
  n123 -- 前提にする --> n109
  n123 -- 前提にする --> n98
  n123 -- 前提にする --> n96
  n124 -- 前提にする --> n123
  n125 -- 前提にする --> n126
  n125 -- 前提にする --> n118
  n126 -- 前提にする --> n148
  n126 -- 影響する --> n19
  n128 -- 根拠になる --> n56
  n128 -- 新たな問いを生む --> n116
  n128 -- 影響する --> n12
  n129 -- 根拠になる --> n38
  n129 -- 影響する --> n23
  n129 -- 答える --> n127
  n130 -- 影響する --> n23
  n131 -- 根拠になる --> n56
  n131 -- 答える --> n119
  n131 -- 影響する --> n24
  n132 -- 根拠になる --> n56
  n132 -- 根拠になる --> n39
  n133 -- 根拠になる --> n51
  n134 -- 新たな問いを生む --> n96
  n134 -- 根拠になる --> n50
  n135 -- 影響する --> n21
  n136 -- 影響する --> n14
  n137 -- 根拠になる --> n52
  n137 -- 影響する --> n96
  n137 -- 前提にする --> n118
  n138 -- 影響する --> n21
  n138 -- 影響する --> n25
  n139 -- 新たな問いを生む --> n115
  n139 -- 影響する --> n24
  n140 -- 根拠になる --> n38
  n140 -- 根拠になる --> n56
  n140 -- 答える --> n127
  n141 -- 影響する --> n11
  n141 -- 新たな問いを生む --> n85
  n143 -- 食い違う --> n38
  n143 -- 新たな問いを生む --> n118
  n143 -- 影響する --> n96
  n144 -- 影響する --> n15
  n145 -- 影響する --> n13
  n146 -- 影響する --> n90
  n147 -- 食い違う --> n38
  n147 -- 影響する --> n96
  n147 -- 影響する --> n23
  n148 -- 根拠になる --> n38
  n148 -- 答える --> n127
  n149 -- 根拠になる --> n52
  n149 -- 影響する --> n96
  n150 -- 影響する --> n137
  class n0 finding_confirmed
  class n1 finding_confirmed
  class n2 finding_confirmed
  class n3 finding_confirmed
  class n4 finding_unverified
  class n5 finding_confirmed
  class n6 finding_unverified
  class n7 finding_unverified
  class n8 finding_unverified
  class n9 finding_outdated
  class n10 finding_confirmed
  class n11 component_current
  class n12 component_current
  class n13 component_current
  class n14 component_current
  class n15 component_current
  class n16 component_current
  class n17 component_current
  class n18 component_current
  class n19 component_planned
  class n20 component_current
  class n21 component_current
  class n22 component_current
  class n23 component_current
  class n24 component_current
  class n25 component_retired
  class n26 finding_confirmed
  class n27 finding_outdated
  class n28 finding_confirmed
  class n29 finding_confirmed
  class n30 finding_confirmed
  class n31 finding_unverified
  class n32 finding_confirmed
  class n33 finding_unverified
  class n34 finding_unverified
  class n35 finding_confirmed
  class n36 decision_adopted
  class n37 decision_adopted
  class n38 decision_superseded
  class n39 decision_superseded
  class n40 decision_adopted
  class n41 decision_adopted
  class n42 decision_adopted
  class n43 decision_adopted
  class n44 decision_adopted
  class n45 decision_adopted
  class n46 decision_proposed
  class n47 decision_adopted
  class n48 decision_adopted
  class n49 decision_adopted
  class n50 decision_adopted
  class n51 decision_superseded
  class n52 decision_adopted
  class n53 decision_adopted
  class n54 decision_adopted
  class n55 decision_adopted
  class n56 decision_superseded
  class n57 decision_adopted
  class n58 finding_unverified
  class n59 finding_unverified
  class n60 finding_unverified
  class n61 finding_confirmed
  class n62 finding_confirmed
  class n63 finding_confirmed
  class n64 finding_unverified
  class n65 finding_confirmed
  class n66 finding_unverified
  class n67 finding_confirmed
  class n68 finding_confirmed
  class n69 finding_unverified
  class n70 finding_confirmed
  class n71 finding_confirmed
  class n72 finding_confirmed
  class n73 finding_confirmed
  class n74 finding_confirmed
  class n75 finding_confirmed
  class n76 finding_confirmed
  class n77 finding_outdated
  class n78 finding_confirmed
  class n79 finding_confirmed
  class n80 finding_confirmed
  class n81 finding_confirmed
  class n82 question_open
  class n83 question_open
  class n84 question_dropped
  class n85 question_dropped
  class n86 question_dropped
  class n87 question_open
  class n88 question_answered
  class n89 question_open
  class n90 question_answered
  class n91 question_open
  class n92 question_open
  class n93 question_open
  class n94 question_answered
  class n95 question_open
  class n96 question_answered
  class n97 question_open
  class n98 question_answered
  class n99 question_open
  class n100 question_open
  class n101 question_open
  class n102 question_open
  class n103 question_open
  class n104 question_open
  class n105 question_answered
  class n106 question_open
  class n107 question_open
  class n108 question_answered
  class n109 question_dropped
  class n110 question_open
  class n111 question_open
  class n112 question_open
  class n113 question_open
  class n114 question_answered
  class n115 question_open
  class n116 question_dropped
  class n117 question_open
  class n118 question_open
  class n119 question_answered
  class n120 question_open
  class n121 question_open
  class n122 question_open
  class n123 question_dropped
  class n124 question_dropped
  class n125 question_dropped
  class n126 question_open
  class n127 question_answered
  class n128 finding_unverified
  class n129 finding_confirmed
  class n130 finding_confirmed
  class n131 finding_confirmed
  class n132 finding_confirmed
  class n133 finding_unverified
  class n134 finding_confirmed
  class n135 finding_confirmed
  class n136 finding_confirmed
  class n137 finding_unverified
  class n138 finding_confirmed
  class n139 finding_unverified
  class n140 finding_confirmed
  class n141 finding_confirmed
  class n142 finding_confirmed
  class n143 finding_unverified
  class n144 finding_confirmed
  class n145 finding_confirmed
  class n146 finding_confirmed
  class n147 finding_confirmed
  class n148 finding_confirmed
  class n149 finding_confirmed
  class n150 finding_confirmed
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

## 今後調べること（28 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md) | 未着手 | 2026-10-13 | S23 | 前提にする → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした](notes/catalog-age-check.md) が影響する<br>[AWS はもう使っていない](notes/no-aws.md) が影響する<br>[EC2 は無い](notes/no-ec2.md) が新たな問いを生む |
| [取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md) | 未着手 | 2026-10-13 | S21, S23 | 前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>前提にする → [AWS はもう使っていない](notes/no-aws.md)<br>[AWS はもう使っていない](notes/no-aws.md) が新たな問いを生む |
| [問い合わせ用のメールアドレス](notes/q-contact-email.md) | 未着手 | 2026-10-13 | S10, S25 | 前提にする → [運営者名は @return1_end（X）にする](notes/dec-operator-name.md) |
| [CoRich のサイトマップから、これからの公演を見つけられるか](notes/q-corich-sitemap.md) | 未着手 | 2026-10-13 | S24 | 前提にする → [CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している](notes/corich-robots-sitemap-only.md) |
| [取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md) | 未着手 | 2026-10-13 | S23, S24 | 前提にする → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>[Claude の GitHub アプリは taguri-crawler にまだ入っていない](notes/claude-app-repo-access.md) が影響する<br>[GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) が影響する<br>[この作業環境の GitHub 連携では、新しいリポジトリを作れない](notes/gha-repo-create-forbidden.md) が新たな問いを生む |
| [D1 のバックアップと復元をどうするか](notes/q-d1-backup.md) | 未着手 | 2026-10-13 | ─ | 影響する → [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md)<br>前提にする → [D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md) |
| [Python Workers の CPU の制限と成熟度](notes/q-d1-python-workers.md) | 未着手 | 2026-10-13 | ─ | [D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md) が影響する<br>[D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）](notes/d1-free-write-limit.md) が答える<br>[別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている](notes/python-workers-migration-state.md) が新たな問いを生む |
| [データを持たないお試し版をどう作るか](notes/q-demo-trial-design.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md)<br>[Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md) が影響する |
| [どのドメインをどこで取るか](notes/q-domain.md) | 未着手 | 2026-10-13 | S04 | 前提にする → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[Cloudflare Registrar では .jp を取れない。DNS だけ Cloudflare に置くことはできる](notes/cf-registrar-no-jp.md) が影響する<br>[.com の卸値は 2026 年 11 月 1 日から年 10.97 ドルに上がる](notes/com-wholesale-2026.md) が影響する<br>[独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) が前提にする<br>[.jp は年 4,000 円前後（税の扱い・年額かは未確認）](notes/jp-domain-price.md) が影響する<br>[パスキーはドメインに結び付くので、ドメインを変えると使えなくなる](notes/passkey-rpid-domain.md) が影響する |
| [Firebase Authentication の無料枠の正確な範囲（メールリンク・利用者数）](notes/q-firebase-free-tier.md) | 未着手 | 2026-10-13 | ─ | [会員ログインは Firebase Authentication にする](notes/dec-firebase-auth.md) が新たな問いを生む |
| [Firebase の API キーに制限（Web サイト・使う API）を掛けたか](notes/q-firebase-key-restriction.md) | 未着手 | 2026-10-13 | ─ | [会員ログインは Firebase Authentication にする](notes/dec-firebase-auth.md) が新たな問いを生む<br>[Firebase の Web 用 API キーは秘密ではない（使える範囲は承認済みドメインとキーの制限で絞る）](notes/firebase-apikey-public.md) が新たな問いを生む |
| [アカウント削除で Firebase 側の利用者も本当に消えているか](notes/q-firebase-user-deletion.md) | 未着手 | 2026-10-13 | ─ | [アカウント削除は「削除」の入力と直近 10 分以内のログインを求める](notes/dec-account-deletion.md) が新たな問いを生む |
| [Worker の依存とログイン画面の組み立てを再現できるようにするか（lockfile）](notes/q-lockfile-reproducible.md) | 未着手 | 2026-10-13 | ─ | 影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [メールリンクのログインで、メールアドレスを端末に残してよいか](notes/q-login-email-storage.md) | 未着手 | 2026-10-13 | ─ | 影響する → [ログイン：Firebase Authentication（Google・メールリンク）](notes/comp-firebase-login.md) |
| [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md) | 未着手 | 2026-10-13 | S33 | 前提にする → [本番に deploy するブランチをどれにするか（PR のブランチのままにしない）](notes/q-production-branch.md)<br>影響する → [Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md)<br>[Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) が新たな問いを生む<br>[本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md) が影響する |
| [無料で使える外形監視と通知](notes/q-monitoring.md) | 未着手 | 2026-10-13 | S22, S23 | [カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした](notes/catalog-age-check.md) が影響する |
| [D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md) | 未着手 | 2026-10-13 | S07, S10 | 前提にする → [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md)<br>[D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）](notes/d1-time-travel.md) が影響する<br>[D1 のバックアップと復元をどうするか](notes/q-d1-backup.md) が前提にする |
| [元の画面の Content-Security-Policy を強められるか](notes/q-original-ui-csp.md) | 未着手 | 2026-10-13 | ─ | 影響する → [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md) |
| [パスキーは実機（iPhone・Android・Mac・Windows）で登録・ログインできるか](notes/q-passkey-real-devices.md) | 未着手 | 2026-10-13 | ─ | [Google を使いたくない人のために、パスキーを新しく作る](notes/dec-passkeys.md) が新たな問いを生む |
| [昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [取得はすべて polite_http を通す](notes/dec-polite-crawling.md)<br>前提にする → [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md)<br>[記録を公演に結び付ける検索には、公開カタログの公演だけを出す](notes/dec-search-public-only.md) が新たな問いを生む |
| [個人情報保護法で何が求められるか](notes/q-privacy-law.md) | 未着手 | 2026-10-13 | S10, S25 | ─ |
| [サーバーの Python を何版に揃えるか](notes/q-python-version.md) | 未着手 | 2026-10-13 | S07 | [バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) が新たな問いを生む |
| [ログイン・登録・検索の回数制限を Worker でどう掛けるか](notes/q-rate-limiting.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md) | 未着手 | 2026-10-13 | S20, S21 | 前提にする → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>[D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）](notes/d1-free-write-limit.md) が新たな問いを生む<br>[1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) が前提にする<br>[EC2 は無い](notes/no-ec2.md) が影響する<br>[取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md) が前提にする<br>[サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) が前提にする<br>[無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか](notes/q-workers-cpu-overrun.md) が前提にする<br>[1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) が前提にする<br>[Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) が新たな問いを生む |
| [Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [AWS はもう使っていない](notes/no-aws.md)<br>影響する → [データを持たないお試し版をどう作るか](notes/q-demo-trial-design.md)<br>[AWS はもう使っていない](notes/no-aws.md) が新たな問いを生む |
| [Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md) | 未着手 | 2026-10-13 | S04, S19 | 前提にする → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>[Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が新たな問いを生む |
| [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md) | 未着手 | 2026-10-13 | S11, S24 | [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) が新たな問いを生む<br>[CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している](notes/corich-robots-sitemap-only.md) が影響する<br>[取得元の実際の robots.txt はまだ読めていない](notes/corich-robots-unchecked.md) が新たな問いを生む<br>[CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md) が影響する |
| [移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか](notes/q-workers-cpu-real.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md)<br>影響する → [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md)<br>[無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか](notes/q-workers-cpu-overrun.md) が前提にする |

## 決めたこと（22 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [デモ版とサービス版を分ける](notes/dec-edition-split.md) | 採用 | 2026-10-12 | S01, S09 | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [画面（web/・config.js）](notes/comp-frontend.md)<br>[デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) が前提にする<br>[デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) が影響する<br>[サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md) が前提にする<br>[Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md) が影響する |
| [取得はすべて polite_http を通す](notes/dec-polite-crawling.md) | 採用 | 2026-10-12 | S15, S24 | 影響する → [取得の作法（polite_http.py）](notes/comp-crawler.md)<br>[GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) が影響する<br>[昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) が前提にする |
| [サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md) | 採用 | 2026-10-12 | S01 | 前提にする → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>[Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない](notes/dec-no-render-data-migration.md) が根拠になる |
| [アカウント削除は「削除」の入力と直近 10 分以内のログインを求める](notes/dec-account-deletion.md) | 採用 | 2026-10-13 | ─ | 影響する → [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md)<br>新たな問いを生む → [アカウント削除で Firebase 側の利用者も本当に消えているか](notes/q-firebase-user-deletion.md) |
| [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) | 採用 | 2026-10-13 | S23, S24 | 答える → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>前提にする → [非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md)<br>前提にする → [公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md)<br>前提にする → [取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）](notes/crawler-state-between-runs.md)<br>[CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）](notes/corich-search-waf-403.md) が影響する<br>[この作業環境の GitHub 連携では、新しいリポジトリを作れない](notes/gha-repo-create-forbidden.md) が影響する<br>[AWS はもう使っていない](notes/no-aws.md) が影響する<br>[取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md) が前提にする |
| [デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) | 採用 | 2026-10-13 | ─ | 答える → [Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md)<br>影響する → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>置き換える → [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md)<br>[データを持たないお試し版をどう作るか](notes/q-demo-trial-design.md) が前提にする |
| [会員ログインは Firebase Authentication にする](notes/dec-firebase-auth.md) | 採用 | 2026-10-13 | ─ | 影響する → [ログイン：Firebase Authentication（Google・メールリンク）](notes/comp-firebase-login.md)<br>新たな問いを生む → [Firebase の API キーに制限（Web サイト・使う API）を掛けたか](notes/q-firebase-key-restriction.md)<br>新たな問いを生む → [Firebase Authentication の無料枠の正確な範囲（メールリンク・利用者数）](notes/q-firebase-free-tier.md) |
| [画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) | 採用 | 2026-10-13 | ─ | 答える → [画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md)<br>前提にする → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>影響する → [Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) |
| [Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない](notes/dec-no-render-data-migration.md) | 採用 | 2026-10-13 | ─ | 根拠になる → [サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md)<br>前提にする → [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) |
| [運営者名は @return1_end（X）にする](notes/dec-operator-name.md) | 採用 | 2026-10-13 | ─ | [問い合わせ用のメールアドレス](notes/q-contact-email.md) が前提にする |
| [Google を使いたくない人のために、パスキーを新しく作る](notes/dec-passkeys.md) | 採用 | 2026-10-13 | ─ | 影響する → [ログイン：パスキー（Google を使わない人向け）](notes/comp-passkeys.md)<br>新たな問いを生む → [パスキーは実機（iPhone・Android・Mac・Windows）で登録・ログインできるか](notes/q-passkey-real-devices.md) |
| [おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) | 採用 | 2026-10-13 | ─ | 置き換える → [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md)<br>前提にする → [Worker の推薦は Python（person-feedback-v1）と同じ結果を出す](notes/reco-js-parity.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) | 採用 | 2026-10-13 | ─ | 食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>食い違う → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>前提にする → [元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）](notes/render-ui-server-rendered.md)<br>影響する → [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md)<br>影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) が前提にする<br>[Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) が影響する<br>[EC2 は無い](notes/no-ec2.md) が影響する<br>[Python の画面は一時保存先・固定日付・通信なしで、テストの中から動かせる](notes/python-screens-harness.md) が根拠になる<br>[Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md) が前提にする<br>[画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md) が前提にする<br>[Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている](notes/render-two-identities.md) が根拠になる |
| [1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) | 採用 | 2026-10-13 | S12 | 影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>前提にする → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) が根拠になる<br>[Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる](notes/workers-paid-plan.md) が根拠になる |
| [記録を公演に結び付ける検索には、公開カタログの公演だけを出す](notes/dec-search-public-only.md) | 採用 | 2026-10-13 | ─ | 新たな問いを生む → [昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) |
| [ログインしていない人に見せるのは「ログイン」と「たぐりとは」だけ](notes/dec-signed-out-gate.md) | 採用 | 2026-10-13 | ─ | 影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) | 採用 | 2026-10-13 | ─ | 答える → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>置き換える → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>置き換える → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>前提にする → [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md)<br>影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) |
| [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) | 提案 | 2026-10-13 | S04, S09 | 影響する → [画面（web/・config.js）](notes/comp-frontend.md)<br>前提にする → [どのドメインをどこで取るか](notes/q-domain.md)<br>[Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が根拠になる<br>[Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が根拠になる<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が前提にする<br>[パスキーはドメインに結び付くので、ドメインを変えると使えなくなる](notes/passkey-rpid-domain.md) が根拠になる<br>[Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md) が前提にする |
| [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md) | 置き換え済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>前提にする → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が食い違う<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が置き換える<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が食い違う<br>[おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が根拠になる<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が根拠になる<br>[Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) が食い違う<br>[別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) が食い違う<br>[Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) が根拠になる |
| [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) | 置き換え済み | 2026-10-13 | ─ | 前提にする → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>[デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) が置き換える<br>[Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) が根拠になる |
| [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md) | 置き換え済み | 2026-10-13 | ─ | [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が置き換える<br>[Render の有料プランならスリープせずディスクも付く（単価は二次情報）](notes/render-paid-disk-cost.md) が根拠になる |
| [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) | 置き換え済み | 2026-10-13 | S02, S13, S22 | 置き換える → [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md)<br>前提にする → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>影響する → [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md)<br>[Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が根拠になる<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が食い違う<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が置き換える<br>[Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) が根拠になる<br>[検証中に自分だけを通す方法（Cloudflare Access の無料枠）](notes/q-cf-access.md) が前提にする<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が根拠になる<br>[Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が根拠になる<br>[Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) が根拠になる<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が根拠になる |

## 調べたこと（68 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [Gmail の読み取りは制限付きの権限で、毎年の第三者の審査が要る](notes/gmail-restricted-scope.md) | 確認済み | 2026-08-28 | ─ | ─ |
| [test_digest と test_impressions は以前から失敗している](notes/legacy-test-failures.md) | 確認済み | 2026-10-12 | ─ | ─ |
| [GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている](notes/pages-404-fallback.md) | 確認済み | 2026-10-12 | S09 | 影響する → [画面（web/・config.js）](notes/comp-frontend.md) |
| [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) | 確認済み | 2026-10-12 | S20 | 根拠になる → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md)<br>[おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) が置き換える |
| [Python の robotparser は小数の Crawl-delay を読めない](notes/robotparser-decimal-delay.md) | 確認済み | 2026-10-12 | ─ | 影響する → [取得の作法（polite_http.py）](notes/comp-crawler.md) |
| [AWS の無料枠は 2025 年 7 月 15 日以降の新しい口座ではクレジット制（最大 200 ドル・6 か月）](notes/aws-free-plan-2025.md) | 確認済み | 2026-10-13 | S12 | 影響する → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md) |
| [AWS は公開 IPv4 アドレス 1 つにつき 1 時間 0.005 ドル（月 3.6 ドルほど）かかる](notes/aws-ipv4-charge.md) | 確認済み | 2026-10-13 | S12 | 影響する → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md) |
| [カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした](notes/catalog-age-check.md) | 確認済み | 2026-10-13 | S23 | 影響する → [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md)<br>影響する → [無料で使える外形監視と通知](notes/q-monitoring.md) |
| [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) | 確認済み | 2026-10-13 | S11 | 新たな問いを生む → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md)<br>[公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md) が影響する<br>[昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) が前提にする |
| [この作業環境からは Cloudflare・Firebase の公式文書や外部サイトが読めない](notes/cf-docs-blocked-here.md) | 確認済み | 2026-10-13 | ─ | ─ |
| [.com の卸値は 2026 年 11 月 1 日から年 10.97 ドルに上がる](notes/com-wholesale-2026.md) | 確認済み | 2026-10-13 | ─ | 影響する → [どのドメインをどこで取るか](notes/q-domain.md) |
| [CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している](notes/corich-robots-sitemap-only.md) | 確認済み | 2026-10-13 | S24 | 影響する → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>置き換える → [取得元の実際の robots.txt はまだ読めていない](notes/corich-robots-unchecked.md)<br>[CoRich のサイトマップから、これからの公演を見つけられるか](notes/q-corich-sitemap.md) が前提にする |
| [CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）](notes/corich-search-waf-403.md) | 確認済み | 2026-10-13 | S24 | 答える → [CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md)<br>影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) |
| [取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）](notes/crawler-state-between-runs.md) | 確認済み | 2026-10-13 | ─ | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が前提にする |
| [Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) | 確認済み | 2026-10-13 | S04 | 根拠になる → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>新たな問いを生む → [Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md)<br>影響する → [画面（web/・config.js）](notes/comp-frontend.md) |
| [D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md) | 確認済み | 2026-10-13 | S20, S21 | 影響する → [Python Workers の CPU の制限と成熟度](notes/q-d1-python-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）](notes/d1-free-write-limit.md) が根拠になる |
| [D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）](notes/d1-time-travel.md) | 確認済み | 2026-10-13 | S07, S10 | 影響する → [D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md)<br>影響する → [別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) |
| [LLM の呼び出しには月の上限がある（既定 300 回）](notes/gemini-budget-cap.md) | 確認済み | 2026-10-13 | S27 | 影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) | 確認済み | 2026-10-13 | S24 | 影響する → [取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md)<br>新たな問いを生む → [CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md)<br>影響する → [取得はすべて polite_http を通す](notes/dec-polite-crawling.md)<br>[CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md) が前提にする |
| [非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md) | 確認済み | 2026-10-13 | S12 | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が前提にする |
| [この作業環境の GitHub 連携では、新しいリポジトリを作れない](notes/gha-repo-create-forbidden.md) | 確認済み | 2026-10-13 | ─ | 影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>新たな問いを生む → [取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md) |
| [公開リポジトリでは GitHub Actions の標準の実行環境が無料。ただし 60 日動きが無いと定期実行が止まる](notes/github-actions-public-free.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) |
| [Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) | 確認済み | 2026-10-13 | ─ | 影響する → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>新たな問いを生む → [画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md)<br>新たな問いを生む → [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md)<br>[画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) が影響する<br>[移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md) が影響する |
| [AWS はもう使っていない](notes/no-aws.md) | 確認済み | 2026-10-13 | ─ | 影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>新たな問いを生む → [Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md)<br>新たな問いを生む → [取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md)<br>影響する → [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md)<br>[取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md) が前提にする<br>[Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md) が前提にする |
| [EC2 は無い](notes/no-ec2.md) | 確認済み | 2026-10-13 | S23 | 答える → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>新たな問いを生む → [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md)<br>影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>影響する → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>影響する → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) | 確認済み | 2026-10-13 | S12, S29 | 答える → [Oracle の公式の無料枠と回収の条件](notes/q-oracle-official.md)<br>新たな問いを生む → [Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか](notes/q-oracle-payg.md)<br>根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) |
| [パスキーはドメインに結び付くので、ドメインを変えると使えなくなる](notes/passkey-rpid-domain.md) | 確認済み | 2026-10-13 | S04 | 影響する → [どのドメインをどこで取るか](notes/q-domain.md)<br>根拠になる → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) |
| [本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md) | 確認済み | 2026-10-13 | S33 | 答える → [本番に deploy するブランチをどれにするか（PR のブランチのままにしない）](notes/q-production-branch.md)<br>置き換える → [本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている](notes/pr-branch-is-production.md)<br>影響する → [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md) |
| [公開版の書き出しが他の利用者の記録まで渡していた（修正済み）](notes/public-export-leak.md) | 確認済み | 2026-10-13 | S03 | 影響する → [本人の書き出し（/export.json・/data.zip）](notes/comp-export.md) |
| [Python の画面は一時保存先・固定日付・通信なしで、テストの中から動かせる](notes/python-screens-harness.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) |
| [別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている](notes/python-workers-migration-state.md) | 確認済み | 2026-10-13 | ─ | 影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>新たな問いを生む → [Python Workers の CPU の制限と成熟度](notes/q-d1-python-workers.md) |
| [Worker の推薦は Python（person-feedback-v1）と同じ結果を出す](notes/reco-js-parity.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) が前提にする |
| [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) | 確認済み | 2026-10-13 | S02 | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>答える → [Render の無料プランでサービス版を動かせるか](notes/q-render-free-viable.md)<br>影響する → [利用者の保存先とバックアップ](notes/comp-state-storage.md)<br>[Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない](notes/dec-no-render-data-migration.md) が前提にする |
| [Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>根拠になる → [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) |
| [Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている](notes/render-two-identities.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>根拠になる → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) |
| [元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）](notes/render-ui-server-rendered.md) | 確認済み | 2026-10-13 | ─ | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が前提にする |
| [サービス版の保存先の検査が Render を前提にしている](notes/serve-cloud-render-guard.md) | 確認済み | 2026-10-13 | S02 | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) |
| [サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) |
| [試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) | 確認済み | 2026-10-13 | S13 | 影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>新たな問いを生む → [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) |
| [題名の正規化（title_key）は JS でも Python と同じにできる](notes/title-key-parity.md) | 確認済み | 2026-10-13 | ─ | ─ |
| [push するたびに Workers Builds が D1 の migration を当ててから deploy する](notes/workers-builds-applies-migrations.md) | 確認済み | 2026-10-13 | ─ | 影響する → [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md) |
| [コミットの ✗ は Workers Builds が cloudflare/ の無い master を組もうとして失敗していたため](notes/workers-builds-master-fail.md) | 確認済み | 2026-10-13 | ─ | 影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [Workers の定期実行は、無料プランだと 1 回あたり CPU 10 ミリ秒・外部への要求 50 回まで](notes/workers-cron-free-limits.md) | 確認済み | 2026-10-13 | S23 | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) |
| [別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) | 確認済み | 2026-10-13 | S10, S20 | 食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）](notes/d1-time-travel.md) が影響する |
| [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md)<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が前提にする<br>[移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか](notes/q-workers-cpu-real.md) が前提にする |
| [Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる](notes/workers-paid-plan.md) | 確認済み | 2026-10-13 | S12 | 根拠になる → [1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) |
| [Workers の静的ファイルへの要求は無料・無制限で、要求数の上限に数えない](notes/workers-static-assets-free.md) | 確認済み | 2026-10-13 | S20 | 影響する → [1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) |
| [取得元の実際の robots.txt はまだ読めていない](notes/corich-robots-unchecked.md) | 古い | 2026-10-12 | S24 | 新たな問いを生む → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>[CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している](notes/corich-robots-sitemap-only.md) が置き換える |
| [Claude の GitHub アプリは taguri-crawler にまだ入っていない](notes/claude-app-repo-access.md) | 古い | 2026-10-13 | ─ | 影響する → [取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md) |
| [本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている](notes/pr-branch-is-production.md) | 古い | 2026-10-13 | ─ | 新たな問いを生む → [本番に deploy するブランチをどれにするか（PR のブランチのままにしない）](notes/q-production-branch.md)<br>[本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md) が置き換える |
| [見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）](notes/demo-seed-link-rate.md) | 未確認 | 2026-10-12 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [Cloudflare Access は 50 人まで無料（古い公式資料）](notes/cf-access-free-50.md) | 未確認 | 2026-10-13 | S30 | 影響する → [検証中に自分だけを通す方法（Cloudflare Access の無料枠）](notes/q-cf-access.md) |
| [Cloudflare Registrar では .jp を取れない。DNS だけ Cloudflare に置くことはできる](notes/cf-registrar-no-jp.md) | 未確認 | 2026-10-13 | S04 | 影響する → [どのドメインをどこで取るか](notes/q-domain.md) |
| [Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>根拠になる → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>新たな問いを生む → [Tunnel の公式の制限・料金・必要な設定](notes/q-cf-tunnel-official.md) |
| [Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える](notes/cf-tunnel-origin-localhost.md) | 未確認 | 2026-10-13 | S13 | 影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>新たな問いを生む → [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) |
| [D1 の無料プランは 1 つのデータベースが 500MB まで（二次情報）](notes/d1-free-db-size.md) | 未確認 | 2026-10-13 | S21 | 影響する → [1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) |
| [D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）](notes/d1-free-write-limit.md) | 未確認 | 2026-10-13 | ─ | 答える → [Python Workers の CPU の制限と成熟度](notes/q-d1-python-workers.md)<br>新たな問いを生む → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>根拠になる → [D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md) |
| [D1 は 1 つの問い合わせに 100 個までの値しか渡せず、1 文は 100 KB まで](notes/d1-query-limits.md) | 未確認 | 2026-10-13 | ─ | 影響する → [推薦の索引の作成（build_recommend_index.py）](notes/comp-rec-index.md) |
| [東京の t4g.micro は 1 時間 0.0108 ドル（月 8 ドルほど）、t3.micro は 0.0136 ドル](notes/ec2-tokyo-price.md) | 未確認 | 2026-10-13 | S12 | 影響する → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md) |
| [Firebase の Web 用 API キーは秘密ではない（使える範囲は承認済みドメインとキーの制限で絞る）](notes/firebase-apikey-public.md) | 未確認 | 2026-10-13 | ─ | 新たな問いを生む → [Firebase の API キーに制限（Web サイト・使う API）を掛けたか](notes/q-firebase-key-restriction.md) |
| [公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md) | 未確認 | 2026-10-13 | ─ | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>影響する → [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md)<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が前提にする |
| [GitHub Actions の定期実行は遅れたり、混雑時に飛ばされたりする](notes/gha-schedule-unreliable.md) | 未確認 | 2026-10-13 | S23 | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) |
| [.jp は年 4,000 円前後（税の扱い・年額かは未確認）](notes/jp-domain-price.md) | 未確認 | 2026-10-13 | ─ | 影響する → [どのドメインをどこで取るか](notes/q-domain.md) |
| [R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>新たな問いを生む → [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [Render の有料プランならスリープせずディスクも付く（単価は二次情報）](notes/render-paid-disk-cost.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md) |
| [1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) | 未確認 | 2026-10-13 | S20, S21 | 根拠になる → [1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>[D1 の無料プランは 1 つのデータベースが 500MB まで（二次情報）](notes/d1-free-db-size.md) が影響する<br>[Workers の静的ファイルへの要求は無料・無制限で、要求数の上限に数えない](notes/workers-static-assets-free.md) が影響する |
| [バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) | 未確認 | 2026-10-13 | ─ | 新たな問いを生む → [サーバーの Python を何版に揃えるか](notes/q-python-version.md)<br>影響する → [利用者の保存先とバックアップ](notes/comp-state-storage.md) |
| [Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) | 未確認 | 2026-10-13 | S20 | 食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>新たな問いを生む → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) |

## 仕組みの部品（15 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [取得の作法（polite_http.py）](notes/comp-crawler.md) | 現行 | 2026-10-12 | ─ | [取得はすべて polite_http を通す](notes/dec-polite-crawling.md) が影響する<br>[Python の robotparser は小数の Crawl-delay を読めない](notes/robotparser-decimal-delay.md) が影響する |
| [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) | 現行 | 2026-10-12 | ─ | [推薦の索引の作成（build_recommend_index.py）](notes/comp-rec-index.md) が影響する<br>[Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md) が影響する<br>[おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) が影響する<br>[見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）](notes/demo-seed-link-rate.md) が影響する<br>[おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が影響する<br>[Worker の推薦は Python（person-feedback-v1）と同じ結果を出す](notes/reco-js-parity.md) が影響する<br>[別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) が影響する |
| [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md) | 現行 | 2026-10-13 | ─ | [Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える](notes/cf-tunnel-origin-localhost.md) が影響する<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が影響する<br>[ログイン・登録・検索の回数制限を Worker でどう掛けるか](notes/q-rate-limiting.md) が前提にする<br>[試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) が影響する |
| [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) | 現行 | 2026-10-13 | ─ | [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) が影響する<br>[推薦の索引の作成（build_recommend_index.py）](notes/comp-rec-index.md) が前提にする<br>[LLM の呼び出しには月の上限がある（既定 300 回）](notes/gemini-budget-cap.md) が影響する<br>[EC2 は無い](notes/no-ec2.md) が影響する<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が影響する |
| [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) | 現行 | 2026-10-13 | ─ | [ログインしていない人に見せるのは「ログイン」と「たぐりとは」だけ](notes/dec-signed-out-gate.md) が影響する<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が影響する<br>[Worker の依存とログイン画面の組み立てを再現できるようにするか（lockfile）](notes/q-lockfile-reproducible.md) が影響する<br>[ログイン・登録・検索の回数制限を Worker でどう掛けるか](notes/q-rate-limiting.md) が影響する<br>[コミットの ✗ は Workers Builds が cloudflare/ の無い master を組もうとして失敗していたため](notes/workers-builds-master-fail.md) が影響する |
| [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md) | 現行 | 2026-10-13 | ─ | 影響する → [利用者の保存先とバックアップ](notes/comp-state-storage.md)<br>[アカウント削除は「削除」の入力と直近 10 分以内のログインを求める](notes/dec-account-deletion.md) が影響する<br>[D1 のバックアップと復元をどうするか](notes/q-d1-backup.md) が影響する<br>[push するたびに Workers Builds が D1 の migration を当ててから deploy する](notes/workers-builds-applies-migrations.md) が影響する |
| [本人の書き出し（/export.json・/data.zip）](notes/comp-export.md) | 現行 | 2026-10-13 | ─ | [公開版の書き出しが他の利用者の記録まで渡していた（修正済み）](notes/public-export-leak.md) が影響する |
| [ログイン：Firebase Authentication（Google・メールリンク）](notes/comp-firebase-login.md) | 現行 | 2026-10-13 | ─ | [会員ログインは Firebase Authentication にする](notes/dec-firebase-auth.md) が影響する<br>[メールリンクのログインで、メールアドレスを端末に残してよいか](notes/q-login-email-storage.md) が影響する |
| [画面（web/・config.js）](notes/comp-frontend.md) | 現行 | 2026-10-13 | ─ | [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md) が影響する<br>[Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が影響する<br>[デモ版とサービス版を分ける](notes/dec-edition-split.md) が影響する<br>[独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) が影響する<br>[GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている](notes/pages-404-fallback.md) が影響する |
| [ログイン：パスキー（Google を使わない人向け）](notes/comp-passkeys.md) | 現行 | 2026-10-13 | ─ | [Google を使いたくない人のために、パスキーを新しく作る](notes/dec-passkeys.md) が影響する |
| [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md) | 現行 | 2026-10-13 | ─ | [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md) が影響する<br>[デモ版とサービス版を分ける](notes/dec-edition-split.md) が影響する<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が影響する<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が影響する<br>[元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）](notes/render-ui-server-rendered.md) が影響する<br>[サービス版の保存先の検査が Render を前提にしている](notes/serve-cloud-render-guard.md) が影響する |
| [推薦の索引の作成（build_recommend_index.py）](notes/comp-rec-index.md) | 現行 | 2026-10-13 | ─ | 前提にする → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[D1 は 1 つの問い合わせに 100 個までの値しか渡せず、1 文は 100 KB まで](notes/d1-query-limits.md) が影響する |
| [利用者の保存先とバックアップ](notes/comp-state-storage.md) | 現行 | 2026-10-13 | ─ | [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md) が影響する<br>[Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が影響する<br>[バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) が影響する |
| [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md) | 予定 | 2026-10-13 | ─ | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [画面（web/・config.js）](notes/comp-frontend.md)<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が影響する<br>[元の画面の Content-Security-Policy を強められるか](notes/q-original-ui-csp.md) が影響する<br>[移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか](notes/q-workers-cpu-real.md) が影響する |
| [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) | 廃止 | 2026-10-13 | ─ | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md)<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が影響する<br>[サービス版の保存先の検査が Render を前提にしている](notes/serve-cloud-render-guard.md) が影響する |

## 答えの出た問い・取り下げた問い（18 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md) | 回答済み | 2026-10-13 | S11, S24 | 前提にする → [GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md)<br>影響する → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>[CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）](notes/corich-search-waf-403.md) が答える<br>[GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) が新たな問いを生む |
| [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) | 回答済み | 2026-10-13 | S23, S24 | 前提にする → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>[取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）](notes/crawler-state-between-runs.md) が影響する<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が答える<br>[1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) が前提にする<br>[非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md) が影響する<br>[公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md) が影響する<br>[GitHub Actions の定期実行は遅れたり、混雑時に飛ばされたりする](notes/gha-schedule-unreliable.md) が影響する<br>[公開リポジトリでは GitHub Actions の標準の実行環境が無料。ただし 60 日動きが無いと定期実行が止まる](notes/github-actions-public-free.md) が新たな問いを生む<br>[EC2 は無い](notes/no-ec2.md) が影響する<br>[今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md) が前提にする<br>[Workers の定期実行は、無料プランだと 1 回あたり CPU 10 ミリ秒・外部への要求 50 回まで](notes/workers-cron-free-limits.md) が影響する |
| [Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>影響する → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>[デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) が答える |
| [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) | 回答済み | 2026-10-13 | S12 | 前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md)<br>[D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md) が影響する<br>[Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md) が前提にする<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が影響する<br>[1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) が影響する<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が答える<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が影響する<br>[別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている](notes/python-workers-migration-state.md) が影響する<br>[どのドメインをどこで取るか](notes/q-domain.md) が前提にする<br>[サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする<br>[Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている](notes/render-two-identities.md) が新たな問いを生む<br>[1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) が影響する<br>[Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) が影響する<br>[別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) が影響する<br>[Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる](notes/workers-paid-plan.md) が影響する |
| [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md) | 回答済み | 2026-10-13 | S12 | [AWS の無料枠は 2025 年 7 月 15 日以降の新しい口座ではクレジット制（最大 200 ドル・6 か月）](notes/aws-free-plan-2025.md) が影響する<br>[AWS は公開 IPv4 アドレス 1 つにつき 1 時間 0.005 ドル（月 3.6 ドルほど）かかる](notes/aws-ipv4-charge.md) が影響する<br>[東京の t4g.micro は 1 時間 0.0108 ドル（月 8 ドルほど）、t3.micro は 0.0136 ドル](notes/ec2-tokyo-price.md) が影響する<br>[EC2 は無い](notes/no-ec2.md) が答える<br>[公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) が前提にする<br>[実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md) が前提にする<br>[サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする |
| [画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>[画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) が答える<br>[Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) が新たな問いを生む |
| [Oracle の公式の無料枠と回収の条件](notes/q-oracle-official.md) | 回答済み | 2026-10-13 | ─ | [Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) が答える |
| [本番に deploy するブランチをどれにするか（PR のブランチのままにしない）](notes/q-production-branch.md) | 回答済み | 2026-10-13 | ─ | [本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている](notes/pr-branch-is-production.md) が新たな問いを生む<br>[本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md) が答える<br>[移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md) が前提にする |
| [Render の無料プランでサービス版を動かせるか](notes/q-render-free-viable.md) | 回答済み | 2026-10-13 | ─ | [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が答える |
| [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) | 回答済み | 2026-10-13 | ─ | [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が答える<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が答える<br>[Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) が答える |
| [検証中に自分だけを通す方法（Cloudflare Access の無料枠）](notes/q-cf-access.md) | 取り下げ | 2026-10-13 | S30 | 前提にする → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>[Cloudflare Access は 50 人まで無料（古い公式資料）](notes/cf-access-free-50.md) が影響する |
| [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) | 取り下げ | 2026-10-13 | S13 | [Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える](notes/cf-tunnel-origin-localhost.md) が新たな問いを生む<br>[試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) が新たな問いを生む |
| [Tunnel の公式の制限・料金・必要な設定](notes/q-cf-tunnel-official.md) | 取り下げ | 2026-10-13 | S22 | [Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が新たな問いを生む |
| [Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか](notes/q-oracle-payg.md) | 取り下げ | 2026-10-13 | S29 | [Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) が新たな問いを生む<br>[サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする |
| [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md) | 取り下げ | 2026-10-13 | ─ | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md)<br>[D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md) が前提にする<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が新たな問いを生む |
| [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) | 取り下げ | 2026-10-13 | S12 | 前提にする → [Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか](notes/q-oracle-payg.md)<br>前提にする → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>前提にする → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) が前提にする<br>[サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) が前提にする<br>[R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md) が前提にする<br>[VM でおすすめが 3 秒以内に開くか](notes/q-vm-performance.md) が前提にする |
| [VM でおすすめが 3 秒以内に開くか](notes/q-vm-performance.md) | 取り下げ | 2026-10-13 | S20 | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) |
| [無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか](notes/q-workers-cpu-overrun.md) | 取り下げ | 2026-10-13 | S20 | 前提にする → [移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか](notes/q-workers-cpu-real.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md) |
