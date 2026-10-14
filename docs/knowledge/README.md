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
  n0("記録と公演ページの自動の結び付けは、いまは持ち主の手元でしか動かない")
  n1("AWS の無料枠は 2025 年 7 月 15 日以降の新しい口座ではクレジット制（最大 200 ドル・6 か月）")
  n2("AWS は公開 IPv4 アドレス 1 つにつき 1 時間 0.005 ドル（月 3.6 ドルほど）かかる")
  n3("カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした")
  n4("最初の毎日の Catalog は D1 に入れる段で落ちた。題名の中の U+2028 を splitlines が行の区切りにしたため（直した）")
  n5("利用規約は公演情報を第三者へ再配布しないと約束している")
  n6("Cloudflare Access は 50 人まで無料（古い公式資料）")
  n7("Cloudflare には R2 の使いすぎを止める仕組みが無い。予算の通知（Budget alerts）は知らせるだけ")
  n8("この作業環境からは Cloudflare・Firebase の公式文書や外部サイトが読めない")
  n9("Cloudflare Registrar では .jp を取れない。DNS だけ Cloudflare に置くことはできる")
  n10("Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある")
  n11("Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える")
  n12("Claude の GitHub アプリは taguri-crawler にまだ入っていない")
  n13(".com の卸値は 2026 年 11 月 1 日から年 10.97 ドルに上がる")
  n14[/"登録・復旧の試行回数の制限（auth.py）"/]
  n15[/"公演カタログの取得と配布（publish_catalog.py）"/]
  n16[/"Cloudflare Worker（cloudflare/src/worker.js）"/]
  n17[/"取得の作法（polite_http.py）"/]
  n18[/"Cloudflare D1（taguri-demo データベース）"/]
  n19[/"本人の書き出し（/export.json・/data.zip）"/]
  n20[/"ログイン：Firebase Authentication（Google・メールリンク）"/]
  n21[/"画面（web/・config.js）"/]
  n22[/"元の画面の Worker 版（cloudflare/src/screens/）"/]
  n23[/"ログイン：パスキー（Google を使わない人向け）"/]
  n24[/"公開版のサーバー（serve_cloud.py・serve.py）"/]
  n25[/"推薦の索引の作成（build_recommend_index.py）"/]
  n26[/"本人向けのおすすめ計算（user_recommender.py）"/]
  n27[/"利用者の保存先とバックアップ"/]
  n28[/"サービス版の VM（cloudflared・systemd）"/]
  n29("CoRich の公演ページの表にはプレイガイド（券の販売先）の欄が無い。名前が料金の欄の文に 1 割ほど出るだけ")
  n30("CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している")
  n31("取得元の実際の robots.txt はまだ読めていない")
  n32("CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）")
  n33("CoRich のサイトマップには、すべての公演ページ（/stage/<id>）が更新日つきで載っている")
  n34("取得の Actions は毎日の更新が 1 回 約 9 分。過去の公演を 1 日 6,000 枚読むと月 3,600 分を越え、無料の 2,000 分に収まらない")
  n35("取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）")
  n36("Pages と Render は別サイトなので、Cookie が別サイトの扱いになる")
  n37("D1 の無料プランは 1 つのデータベースが 500MB まで（二次情報）")
  n38("D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB")
  n39("D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）")
  n40("D1 は 1 つの問い合わせに 100 個までの値しか渡せず、1 文は 100 KB まで")
  n41("D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）")
  n42[["アカウント削除は「削除」の入力と直近 10 分以内のログインを求める"]]
  n43[["過去の公演の一覧（2019 年以降）を毎日 6,000 枚ずつ作り、記録を自動で結び付ける"]]
  n44[["GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む"]]
  n45[["取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）"]]
  n46[["取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる"]]
  n47[["Cloudflare Workers への完全移行は今は見送る（見直し中）"]]
  n48[["デモ版は Render の無料プランのまま残す"]]
  n49[["デモ版は、触れるがデータを持たないお試し版にする"]]
  n50[["いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる"]]
  n51[["既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない"]]
  n52[["デモ版とサービス版を分ける"]]
  n53[["会員ログインは Firebase Authentication にする"]]
  n54[["たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる"]]
  n55[["推薦の理由に本人の感想（「あなたの言葉」）を引かない ── デモ版もサービス版も"]]
  n56[["読み込み画面 ── 幕と歩くピクトグラムをやめ、毛糸玉が転がって糸をたぐる形にする"]]
  n57[["画面の移行は wip-screens-port で進め、段ごとに試験が通ってから master に入れる"]]
  n58[["画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る"]]
  n59[["持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない"]]
  n60[["Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない"]]
  n61[["運営者名は @return1_end（X）にする"]]
  n62[["独自ドメインを取り、画面と API を同じドメインの下に置く"]]
  n63[["「すでに持っている」を押した公演は購入済み公演にだけ出し、終わったら未評価に出す。前に開いてから終わった未評価があれば、おすすめを開いたときに知らせる"]]
  n64[["Google を使いたくない人のために、パスキーを新しく作る"]]
  n65[["スマホの見出し ── 4 つの大メニューを均等割りで常に出し、子メニューはすだれで出す"]]
  n66[["取得はすべて polite_http を通す"]]
  n67[["ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す"]]
  n68[["評価の詳細は任意で隠しておき、項目ごとに「良かった／気になった」を付けられる。詳しく記録するか、あっさり付けるかは人が選ぶ"]]
  n69[["おすすめの人物の理由には、本数ではなく具体的な作品名（と付けた印）を書く"]]
  n70[["推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない"]]
  n71[["推薦の改善は、先に測る仕組みを作ってから計算を変える"]]
  n72[["おすすめ（人物得点）は索引をバッチで作り、Worker で計算する"]]
  n73[["推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）"]]
  n74[["「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）"]]
  n75[["おすすめの券の見直し（2026-10-14 の 10 項目）── 回答の帯は右寄せ・興味なしはグレー・書き込み中・説明はインフォへ・もう追いかけない束をやめる・名前の札・絵記号・期間の表記・ツアーの日程・発売の札から券の案内へ"]]
  n76[["評価一覧などの記録の 1 件をおすすめの 1 枚と同じ形にし、感想はその文の上で書き直す"]]
  n77[["Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）"]]
  n78[["サービス版を Render の有料サービスで立てる"]]
  n79[["1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる"]]
  n80[["記録を公演に結び付ける検索には、公開カタログの公演だけを出す"]]
  n81[["サービス版は空から始め、デモの記録を移さない"]]
  n82[["ログインしていない人に見せるのは「ログイン」と「たぐりとは」だけ"]]
  n83[["公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ"]]
  n84[["見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）"]]
  n85[["料金の欄から最安〜最高の金額を読み、おすすめの券に出して、上限の金額で絞り込めるようにする"]]
  n86[["評価の段階は利用者が選べる。初期設定は 5 段階、最小 2 段階・最大 11 段階"]]
  n87[["評価の分布を発散型の帯にし、判子から評価を選び直す。＋は登録の 3 つの入口を開く"]]
  n88[["サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く"]]
  n89[["無料で起動を速くするため、Cloudflare Workers＋D1 で動かす"]]
  n90("見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）")
  n91[["パソコンの見た目の案（左の行き先の帯に 14 項目を組で並べ、本文は 920px 幅、半券にポスターの列）"]]
  n92[/"見た目の調整室（起案者が色・文字・ボタン・配置・文言を決めて保存し、Claude が読み取って実際の画面に反映する）"/]
  n93("東京の t4g.micro は 1 時間 0.0108 ドル（月 8 ドルほど）、t3.micro は 0.0136 ドル")
  n94("作ったデータでは、気になった所を仮定どおりに付ける人には効き、でたらめに付ける人には害があり、裏の答え合わせはその害をあまり拾えない")
  n95("推薦の計算の細部（数字への直し方・平均か合計か・割り引き・足す人数）はほぼ差が無く、効くのはジャンルの好みと監督の重みを上げること")
  n96("作品そのものの評判（他の人の平均）は、人物の手がかりよりずっと強い（AUC 0.79 対 0.57）")
  n97("公開の映画評価データ（実在の 500 人）では、今の推薦は当てずっぽうに近い（AUC 0.50〜0.53）")
  n98("全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる")
  n99("答え合わせの問題を固定しても、使うほど当たりは上がる（今の計算で 63%、graded で 74% の人）。ただし水準は低い")
  n100("役職（出演・監督）の重みを人ごとに学んでも、この条件では良くならなかった")
  n101("評価の段階を粗くしても当たりは少し下がるだけで、途中で段階を変えた人は「同じ段階どうしで比べる」のがよい")
  n102("お気に入りを仮の評価にすると、評価0件のときだけ当たりが上がる（+0.014〜0.015）。すぐ薄めれば後で下がらない")
  n103("本人のジャンルの好みを足すと、人物だけより当たりが上がり、使うほどの伸びも大きくなる（映画の公開データ）")
  n104("裏の答え合わせは「組を数える」「前の作品と比べる」とでたらめな人でも切り替わる。区切りごとに数えると誤りは 3% 以下")
  n105("組み合わせの重みを公開データの別の人で学んで固定すると少し上がる（+0.006）。人ごとに学び直すのと小さな MLP は効かない")
  n106("最初に評価してもらう過去作を、これから並べる候補に多い人物・ジャンルから選ぶと、同じ件数で当たりが上がる（楽観的な条件）")
  n107("水準を大きく上げたのは「作り手・ジャンルの世間の評判」だけで、それは使っても上がらない")
  n108("Firebase の Web 用 API キーは秘密ではない（使える範囲は承認済みドメインとキーの制限で絞る）")
  n109("◎○△× の 4 段階が適切だという直接の証拠は無い（「残す」は手間と既存の評価を理由にした判断）")
  n110("起案者が Cloudflare の Budget alerts を作り、Workers の Free を確かめた。GitHub には支払い方法を登録していない")
  n111("LLM の呼び出しには月の上限がある（既定 300 回）")
  n112("舞台のジャンル分けは、チケット販売サイト・業界の白書・助成制度・演劇史の区分がそれぞれ独自に持っていて、共通の公式の分け方は無い")
  n113("GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた")
  n114("Actions の無料の分は毎月 0 に戻り、月払いの支払いの上限は既定で 0 ドル（越えると止まる）")
  n115("非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料")
  n116("公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる")
  n117("この作業環境の GitHub 連携では、新しいリポジトリを作れない")
  n118("実行中の GitHub Actions のジョブのログは API で取れない（404）。進み具合は手順の状態でしか見えない")
  n119("GitHub Actions の定期実行は遅れたり、混雑時に飛ばされたりする")
  n120("公開リポジトリでは GitHub Actions の標準の実行環境が無料。ただし 60 日動きが無いと定期実行が止まる")
  n121("Gmail の読み取りは制限付きの権限で、毎年の第三者の審査が要る")
  n122("評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）")
  n123("裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）")
  n124("最初の評価で聞く過去作の一覧を出す API を作った（お気に入りの公演 → 今後の候補を一番多く覆う公演）")
  n125("推薦の計算を person-graded-v2 に変えた（Python 版と Worker 版の両方、同じ結果になることをテストで確認）")
  n126("推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）")
  n127("評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）")
  n128("Worker の推薦でもツアー公演を 1 枠にまとめ、ほかの会場を付けて出すようにした（+tour1）")
  n129(".jp は年 4,000 円前後（税の扱い・年額かは未確認）")
  n130("test_digest と test_impressions は以前から失敗している")
  n131("評定（◎○△×）の分布は、0 を中心に左右へ分ける積み上げ棒がよい ── 可視化の論文から")
  n132("当てる精度だけを上げると、役に立つ推薦から外れることがある（McNee ほか 2006・Ferrari Dacrema ほか 2019）")
  n133("順位を直接学ぶ「組で比べる」学習（BPR）は、AUC を最大にするのと同じ形（Rendle ほか 2009）")
  n134("新作向けの深層学習の推薦（DropoutNet・CB2CF・two-tower・言語モデル）は、対象分野の協調データか外部への送信が要り、たぐりの方針にそのままは合わない")
  n135("「好み」と「評価の付け方の癖」を分けて扱うと精度が上がり、順位だけを使うと情報を捨てすぎる（Jin・Si・Zhai 2003）")
  n136("選べるようにしても、多くの人は最初に決められた選択肢のままにする（既定の効果、Johnson & Goldstein 2003）")
  n137("推薦が利用者の行動を変え、その行動で次の推薦を学ぶ「輪」で、推薦は偏りやすくなる（Chaney・Stewart・Engelhardt 2018）")
  n138("映画のジャンルを使った推薦の研究は、主に「新しい利用者・新作の立ち上がり」のために使われている")
  n139("利用者ごとの好みを、全体の事前分布から少しずつ個人に寄せる学習は確立した方法（Zhang & Koren 2007）")
  n140("観る前の反応（興味あり・購入）は「好みの信号」だが確からしさが違うので、重みを変えて扱う（Hu・Koren・Volinsky 2008）")
  n141("評価が付いていないこと自体が情報になり、付いた評価だけで学ぶ・測ると偏る（Steck 2010）")
  n142("総合評価に加えて観点ごとの評価を使う推薦（多基準推薦）は、1 つの評価だけより精度が上がったと報告されている（Adomavicius & Kwon 2007 ほか）")
  n143("低い評価は、とくにデータが少ないときに推薦の役に立つ（Negative ratings play a positive role in information filtering）")
  n144("評価を等間隔の数ではなく順序として扱う研究（OrdRec）と、少ない件数を割り引く「damping」は推薦の定番")
  n145("舞台芸術の推薦の先行例は少なく、主に劇場側の販売データでの協調フィルタリング")
  n146("届いた順に「予想してから答え合わせ」する評価（prequential）は、変わり続ける推薦の評価に使われている（Vinagre ほか 2014）")
  n147("「値段に見合うか（知覚価値）」は品質と支払う犠牲の釣り合いで決まり、推薦でも価格を別に扱う研究がある（Zeithaml 1988・Zheng ほか 2020）")
  n148("同じ人が同じ作品を付け直しても評価はぶれる（Amatriain ほか 2009）")
  n149("評価の段階は「付ける手間」と「推薦に使える情報量」の引き換えで、粗い段階は速いが情報が少ない（Sparling & Sen 2011・Kluver ほか 2012）")
  n150("評価の付け方の癖は文化や個人で違い、日本や中国の回答者は真ん中を選びやすく、米国は端を選びやすい（Chen・Lee・Stevenson 1995、Harzing 2006）")
  n151("新しい方式は「前より悪くないと高い確信で言えるときだけ」採る、という考え方がある（Thomas ほか 2015）")
  n152("評価の段階を途中で変えたときの扱い：直接の研究は少なく、段階どうしを決まった式で写すのは最善ではないとされる")
  n153("評価の段階数の研究では 2〜4 段階は信頼性・妥当性が低く、7 段階前後がよいとされる。ただし多ければ良いとも限らない")
  n154("内容ベースの推薦で、本人の初期の好みを評価が増えるたびに修正する方法がある（Billsus & Pazzani）")
  n155("推薦では、利用者ごとの評価の甘さ辛さ（user bias）を差し引いて扱うのが定番（Koren 2008 ほか）")
  n156("利用者に評価の段階を選ばせる案は研究で提案されており、選ばれる段階は評価する物や経験で変わる（Cena・Vernero ほか）")
  n157("観点ごとの評価がある公開データ（Yahoo! Movies：物語・演技・演出・映像＋総合）が研究で使われている")
  n158("Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない")
  n159("段 1（記録と評価）の画面 4 枚と書き込み 11 種が、Python と同じ応答を返すようになった")
  n160("段 1 の作りかけを受け取った。読み込めない原因は py.js の正規表現に入った生の行区切り文字だった")
  n161("日記帳などを Worker の画面に切り替えるための今の状態（NATIVE_UI）")
  n162("AWS はもう使っていない")
  n163("EC2 は無い")
  n164("商用でも無料の日本語書体（SIL OFL）と、自分のサイトで配るときの重さ")
  n165("Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる")
  n166("GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている")
  n167("パスキーはドメインに結び付くので、ドメインを変えると使えなくなる")
  n168("本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている")
  n169("本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）")
  n170("公開版の書き出しが他の利用者の記録まで渡していた（修正済み）")
  n171("Python の画面は一時保存先・固定日付・通信なしで、テストの中から動かせる")
  n172("別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている")
  n173{{"観点（値段・脚本・演出など）ごとに下げる相手を変える案を、どう確かめるか"}}
  n174{{"評価の画面に「気になった所」（任意・複数選択）のボタンを付けるか"}}
  n175{{"古い記録を自動で結び付けるための「過去の公演の一覧」を、CoRich のページを読んで作ってよいか"}}
  n176{{"今の公演カタログ（S3）は、いつ・どこで作られたものか"}}
  n177{{"取得したカタログを Cloudflare 版（D1）にどう届けるか"}}
  n178{{"Worker の /api/catalogue は 1,000 件までしか返さない。これからの公演がそれより多いときどうするか"}}
  n179{{"移行ブランチの Python 版はカタログをコードの束に同梱する。D1 に毎日入れる作りとどう揃えるか"}}
  n180{{"検証中に自分だけを通す方法（Cloudflare Access の無料枠）"}}
  n181{{"CF-Connecting-IP をどう信頼するか"}}
  n182{{"Tunnel の公式の制限・料金・必要な設定"}}
  n183{{"問い合わせ用のメールアドレス"}}
  n184{{"CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか"}}
  n185{{"CoRich のサイトマップから、これからの公演を見つけられるか"}}
  n186{{"一度読んだ公演ページの更新（出演者の追加など）をどう拾い直すか"}}
  n187{{"公演情報の取得処理をどこで動かすか"}}
  n188{{"取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定"}}
  n189{{"取得の作業データ（state ブランチ）が 2 GB になった。ポスターと公演ページの HTML の控えをどうするか"}}
  n190{{"D1 のバックアップと復元をどうするか"}}
  n191{{"Python Workers の CPU の制限と成熟度"}}
  n192{{"Render を止めたあと、デモ版（見本の記録で試す版）をどうするか"}}
  n193{{"データを持たないお試し版をどう作るか"}}
  n194{{"たぐりの見た目をどの方向に変えるか（A 幕と半券・B 観劇ノート・C 客電が落ちる）"}}
  n195{{"サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか"}}
  n196{{"どのドメインをどこで取るか"}}
  n197{{"今の EC2 の種類・口座の作成日・月額"}}
  n198{{"最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）"}}
  n199{{"Firebase Authentication の無料枠の正確な範囲（メールリンク・利用者数）"}}
  n200{{"Firebase の API キーに制限（Web サイト・使う API）を掛けたか"}}
  n201{{"アカウント削除で Firebase 側の利用者も本当に消えているか"}}
  n202{{"登録して最初の 1 回目の評価だけ、これから並ぶ公演に関係する過去作から聞く形にするか（起案者の案）"}}
  n203{{"起案者のアカウントの設定で、無料枠を越えても請求されないようになっているか"}}
  n204{{"新しい要素を安全に入れる「裏の答え合わせ」をどう作るか（起案者が良いと判断）"}}
  n205{{"Worker の依存とログイン画面の組み立てを再現できるようにするか（lockfile）"}}
  n206{{"メールリンクのログインで、メールアドレスを端末に残してよいか"}}
  n207{{"移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）"}}
  n208{{"画面の移行の続き（段 1〜5）をどのセッションが受け持つか"}}
  n209{{"無料で使える外形監視と通知"}}
  n210{{"CoRich の検索を使えないとき、お気に入りの登録名や探してほしい題名で公演をどう探すか"}}
  n211{{"Worker の画面への切り替えを、日記帳など 4 画面だけ先にするか、全画面がそろってから一度にするか"}}
  n212{{"D1 のバックアップを、Time Travel の期間より長くどこに残すか"}}
  n213{{"Oracle の公式の無料枠と回収の条件"}}
  n214{{"Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか"}}
  n215{{"元の画面の Content-Security-Policy を強められるか"}}
  n216{{"パスキーは実機（iPhone・Android・Mac・Windows）で登録・ログインできるか"}}
  n217{{"昔の公演を、公開情報だけで探せるようにするにはどうするか"}}
  n218{{"起案者が「UI が素敵」と挙げた plainwalk はどのサイトか"}}
  n219{{"好きな作品のポスターから色を取り出して画面を染めるには、何が要るか"}}
  n220{{"推薦側の PR #13（person-graded-v2・評価の段階・評価の「詳細」8 項目）を入れるか。入れるなら「詳細」の画面をこちらで作るか"}}
  n221{{"個人情報保護法で何が求められるか"}}
  n222{{"本番に deploy するブランチをどれにするか（PR のブランチのままにしない）"}}
  n223{{"公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか"}}
  n224{{"サーバーの Python を何版に揃えるか"}}
  n225{{"R2 の公式料金と、今の boto3 のコードで読み書きできるか"}}
  n226{{"ポスターが R2 の上限 8 GB に近づいたら、どれを消すか"}}
  n227{{"ログイン・登録・検索の回数制限を Worker でどう掛けるか"}}
  n228{{"総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか"}}
  n229{{"◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか"}}
  n230{{"実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか"}}
  n231{{"推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）"}}
  n232{{"「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）"}}
  n233{{"その人の記録だけで、計算方式の良し悪しをどう確かめるか（振り返りでの検証）"}}
  n234{{"Render の無料プランでサービス版を動かせるか"}}
  n235{{"Render のデモ版は、起動し直すと動かなくなるのではないか"}}
  n236{{"Safari で Cookie が通るか（実機）"}}
  n237{{"取得元の利用規約・robots.txt・ポスター画像の権利"}}
  n238{{"あらすじの読み取りを誰が担うか（Claude の定期実行・Gemini API・当面読まない）"}}
  n239{{"あらすじを Claude の定期実行で読むと、1 日にどれだけ読め、起案者の使用枠をどれだけ使うか"}}
  n240{{"観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか"}}
  n241{{"評価の段階を利用者自身に選んでもらうか（起案者の案）"}}
  n242{{"サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか"}}
  n243{{"VM でおすすめが 3 秒以内に開くか"}}
  n244{{"調整室で選んだ書体（Zen Old Mincho など）を、外部から読み込まずに全員の画面で出すには"}}
  n245{{"Cloudflare 版でポスターをどこに置いて出すか"}}
  n246{{"無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか"}}
  n247{{"移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか"}}
  n248{{"Cloudflare の無料枠だけで、今のコードのまま動かせるか"}}
  n249("R2 の無料枠は保存 10 GB・Class A 月 100 万回・Class B 月 1,000 万回で、越えた分は請求される（取り出しの通信料は無料）")
  n250("R2 は 10GB まで無料で、取り出しの通信料がかからない")
  n251("観劇の評価は内容だけでなく、値段に見合うか・構成・演出などが混ざって 1 つの記号になる")
  n252("今の推薦（person-feedback-v1）の精度は、公開版の利用者では測っていない")
  n253("今の計算は「その人の◎の割合」を差し引くので、◎が珍しい人の◎ほど強く効き、◎ばかりの人の◎はほとんど効かない")
  n254("おすすめは開くたびに全候補を計算している")
  n255("推薦の良し悪しを測る仕組みが足りない（利用者ごとの時系列評価・正解データ・提示と結果の結び付け）")
  n256("Worker の推薦は Python（person-feedback-v1）と同じ結果を出す")
  n257("過去の改善の実験結果（持ち主 1 人の評価での AUC）は、判断の根拠に使わない")
  n258("推薦の計算を改善する計画書はあるが、master に入っておらず内容が一部古い")
  n259("推薦の計算 person-graded-v2 は、D1 の索引の作り（表と行）を変えない")
  n260("Render の無料プランは永続ディスクを付けられない")
  n261("Render の無料プランは 15 分でスリープし、起動に約 1 分かかる")
  n262("Render の有料プランならスリープせずディスクも付く（単価は二次情報）")
  n263("Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている")
  n264("元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）")
  n265("Python の robotparser は小数の Crawl-delay を読めない")
  n266("1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）")
  n267("サービス版の保存先の検査が Render を前提にしている")
  n268("シンプルなデザインは「削る」ことではなく、要るものを一つに絞って際立たせ、押せる手がかりは残すこと")
  n269("サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た")
  n270("舞台の仕事の分担：演出家が作品全体の芸術面の責任者で、舞台監督は現場の進行、制作・プロデューサーは予算と運営（値段を決める側）")
  n271("バックアップの検査が Python 3.13 では 1 件失敗する")
  n272("サーバーは標準ライブラリの http.server と sqlite3 で書いてある")
  n273("あらすじの読み取りは Gemini API。以前の claude CLI 呼び出しは起案者の判断でやめている")
  n274("舞台の公演に業界共通の公式のジャンル分けは見つからない。近いものは日本劇作家協会「戯曲デジタルアーカイブ」のジャンル（戯曲向け）")
  n275("持ち主の過去の検証では、あらすじのテーマ語は作品間で重なりにくく、一般的な語（家族・恋愛・コメディ・友情）に偏っていた")
  n276("試行回数の制限は接続元のアドレスで数えている")
  n277("題字の書体の候補（明朝と本文ゴシックの間）── どれも SIL OFL")
  n278("題名の正規化（title_key）は JS でも Python と同じにできる")
  n279("画面の△の説明「あまり合わなかった」は、起案者の考える△（まあ良いが気になる所がある）と食い違う")
  n280("note・Notion のような白基調の記録サイトの見た目（白い紙面・真っ黒でない文字・差し色 1 つ・広い余白）")
  n281("本番の Worker の /api/health は、Render への橋渡しに取られて 404 になっていた（直した）")
  n282("Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）")
  n283("push するたびに Workers Builds が D1 の migration を当ててから deploy する")
  n284("Workers Builds（GitHub からの自動配信）は無料プランで月 3,000 分・同時 1 本・1 回 20 分まで")
  n285("コミットの ✗ は Workers Builds が cloudflare/ の無い master を組もうとして失敗していたため")
  n286("Workers の Cache API は *.workers.dev では何もしない（独自ドメインでだけ効く）")
  n287("Workers の定期実行は、無料プランだと 1 回あたり CPU 10 ミリ秒・外部への要求 50 回まで")
  n288("別の作業で、Workers＋D1 の版が workers.dev で動き始めている")
  n289("Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで")
  n290("Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる")
  n291("Workers の静的ファイルへの要求は無料・無制限で、要求数の上限に数えない")
  n0 -- 新たな問いを生む --> n175
  n0 -- 影響する --> n217
  n1 -- 影響する --> n197
  n2 -- 影響する --> n197
  n3 -- 影響する --> n176
  n3 -- 影響する --> n209
  n4 -- 影響する --> n46
  n4 -- 影響する --> n269
  n5 -- 新たな問いを生む --> n237
  n5 -- 影響する --> n15
  n6 -- 影響する --> n180
  n7 -- 根拠になる --> n54
  n7 -- 新たな問いを生む --> n203
  n9 -- 影響する --> n196
  n10 -- 根拠になる --> n88
  n10 -- 根拠になる --> n62
  n10 -- 新たな問いを生む --> n182
  n11 -- 影響する --> n14
  n11 -- 新たな問いを生む --> n181
  n12 -- 影響する --> n188
  n13 -- 影響する --> n196
  n18 -- 影響する --> n27
  n22 -- 影響する --> n24
  n22 -- 影響する --> n21
  n25 -- 前提にする --> n15
  n25 -- 影響する --> n26
  n28 -- 前提にする --> n242
  n29 -- 根拠になる --> n75
  n30 -- 影響する --> n237
  n30 -- 置き換える --> n31
  n31 -- 新たな問いを生む --> n237
  n32 -- 答える --> n184
  n32 -- 影響する --> n45
  n33 -- 答える --> n185
  n33 -- 影響する --> n45
  n34 -- 根拠になる --> n54
  n34 -- 影響する --> n43
  n34 -- 影響する --> n115
  n35 -- 影響する --> n187
  n36 -- 根拠になる --> n62
  n36 -- 新たな問いを生む --> n236
  n36 -- 影響する --> n21
  n37 -- 影響する --> n266
  n38 -- 影響する --> n191
  n38 -- 影響する --> n195
  n39 -- 答える --> n191
  n39 -- 新たな問いを生む --> n230
  n39 -- 根拠になる --> n38
  n40 -- 影響する --> n25
  n41 -- 影響する --> n212
  n41 -- 影響する --> n288
  n42 -- 影響する --> n18
  n42 -- 新たな問いを生む --> n201
  n43 -- 答える --> n175
  n43 -- 前提にする --> n0
  n44 -- 前提にする --> n32
  n44 -- 前提にする --> n33
  n44 -- 影響する --> n45
  n45 -- 答える --> n187
  n45 -- 前提にする --> n115
  n45 -- 前提にする --> n116
  n45 -- 前提にする --> n35
  n46 -- 答える --> n177
  n46 -- 前提にする --> n45
  n46 -- 前提にする --> n83
  n46 -- 前提にする --> n89
  n46 -- 新たな問いを生む --> n178
  n46 -- 新たな問いを生む --> n179
  n47 -- 影響する --> n26
  n47 -- 前提にする --> n195
  n48 -- 前提にする --> n52
  n49 -- 答える --> n192
  n49 -- 影響する --> n52
  n49 -- 置き換える --> n48
  n50 -- 前提にする --> n51
  n50 -- 前提にする --> n92
  n50 -- 影響する --> n84
  n51 -- 答える --> n194
  n51 -- 前提にする --> n84
  n51 -- 前提にする --> n268
  n52 -- 影響する --> n24
  n52 -- 影響する --> n21
  n53 -- 影響する --> n20
  n53 -- 新たな問いを生む --> n200
  n53 -- 新たな問いを生む --> n199
  n54 -- 置き換える --> n79
  n54 -- 前提にする --> n249
  n54 -- 前提にする --> n114
  n54 -- 前提にする --> n38
  n54 -- 前提にする --> n289
  n54 -- 影響する --> n43
  n54 -- 影響する --> n67
  n54 -- 影響する --> n211
  n54 -- 新たな問いを生む --> n203
  n54 -- 新たな問いを生む --> n226
  n55 -- 影響する --> n74
  n56 -- 影響する --> n50
  n57 -- 答える --> n207
  n57 -- 前提にする --> n169
  n57 -- 前提にする --> n58
  n58 -- 答える --> n208
  n58 -- 前提にする --> n77
  n58 -- 影響する --> n158
  n59 -- 影響する --> n257
  n59 -- 影響する --> n231
  n59 -- 影響する --> n26
  n60 -- 根拠になる --> n81
  n60 -- 前提にする --> n260
  n62 -- 影響する --> n21
  n62 -- 前提にする --> n196
  n64 -- 影響する --> n23
  n64 -- 新たな問いを生む --> n216
  n65 -- 影響する --> n50
  n65 -- 前提にする --> n277
  n66 -- 影響する --> n17
  n67 -- 答える --> n189
  n67 -- 答える --> n245
  n68 -- 影響する --> n127
  n68 -- 前提にする --> n142
  n68 -- 影響する --> n26
  n70 -- 前提にする --> n98
  n70 -- 置き換える --> n71
  n70 -- 影響する --> n26
  n70 -- 影響する --> n228
  n71 -- 前提にする --> n231
  n71 -- 根拠になる --> n258
  n72 -- 置き換える --> n254
  n72 -- 前提にする --> n256
  n72 -- 影響する --> n26
  n73 -- 影響する --> n231
  n73 -- 影響する --> n71
  n73 -- 影響する --> n26
  n73 -- 新たな問いを生む --> n233
  n74 -- 影響する --> n50
  n74 -- 前提にする --> n65
  n74 -- 新たな問いを生む --> n245
  n75 -- 前提にする --> n29
  n75 -- 影響する --> n74
  n76 -- 影響する --> n50
  n76 -- 前提にする --> n74
  n77 -- 食い違う --> n47
  n77 -- 食い違う --> n88
  n77 -- 前提にする --> n264
  n77 -- 影響する --> n22
  n77 -- 影響する --> n24
  n77 -- 影響する --> n195
  n79 -- 影響する --> n195
  n79 -- 前提にする --> n230
  n79 -- 前提にする --> n187
  n80 -- 新たな問いを生む --> n217
  n81 -- 前提にする --> n52
  n82 -- 影響する --> n16
  n83 -- 答える --> n238
  n83 -- 前提にする --> n273
  n83 -- 前提にする --> n45
  n83 -- 影響する --> n177
  n83 -- 新たな問いを生む --> n239
  n84 -- 影響する --> n194
  n84 -- 新たな問いを生む --> n219
  n86 -- 答える --> n241
  n86 -- 影響する --> n26
  n86 -- 影響する --> n229
  n87 -- 前提にする --> n131
  n87 -- 影響する --> n76
  n88 -- 置き換える --> n78
  n88 -- 前提にする --> n62
  n88 -- 影響する --> n24
  n88 -- 影響する --> n14
  n88 -- 影響する --> n28
  n89 -- 答える --> n195
  n89 -- 置き換える --> n47
  n89 -- 置き換える --> n88
  n89 -- 食い違う --> n47
  n89 -- 前提にする --> n289
  n89 -- 影響する --> n16
  n89 -- 影響する --> n195
  n90 -- 影響する --> n26
  n91 -- 前提にする --> n50
  n92 -- 前提にする --> n51
  n92 -- 影響する --> n84
  n93 -- 影響する --> n197
  n94 -- 影響する --> n127
  n94 -- 前提にする --> n173
  n94 -- 前提にする --> n59
  n95 -- 影響する --> n26
  n95 -- 根拠になる --> n103
  n96 -- 新たな問いを生む --> n223
  n97 -- 影響する --> n26
  n97 -- 答える --> n232
  n98 -- 根拠になる --> n229
  n98 -- 根拠になる --> n135
  n98 -- 根拠になる --> n143
  n98 -- 影響する --> n26
  n99 -- 根拠になる --> n70
  n99 -- 新たな問いを生む --> n223
  n100 -- 影響する --> n232
  n101 -- 根拠になる --> n86
  n101 -- 影響する --> n26
  n102 -- 前提にする --> n154
  n102 -- 前提にする --> n59
  n102 -- 影響する --> n26
  n103 -- 影響する --> n26
  n103 -- 新たな問いを生む --> n240
  n104 -- 根拠になる --> n123
  n104 -- 前提にする --> n59
  n105 -- 根拠になる --> n139
  n105 -- 影響する --> n26
  n106 -- 影響する --> n26
  n107 -- 影響する --> n223
  n108 -- 新たな問いを生む --> n200
  n109 -- 影響する --> n229
  n110 -- 答える --> n203
  n110 -- 根拠になる --> n54
  n111 -- 影響する --> n15
  n112 -- 影響する --> n240
  n113 -- 影響する --> n188
  n113 -- 新たな問いを生む --> n184
  n113 -- 影響する --> n66
  n114 -- 根拠になる --> n115
  n114 -- 根拠になる --> n54
  n115 -- 影響する --> n187
  n116 -- 影響する --> n187
  n116 -- 影響する --> n5
  n117 -- 影響する --> n45
  n117 -- 新たな問いを生む --> n188
  n118 -- 影響する --> n45
  n119 -- 影響する --> n187
  n120 -- 新たな問いを生む --> n187
  n122 -- 答える --> n198
  n122 -- 前提にする --> n102
  n122 -- 前提にする --> n126
  n122 -- 影響する --> n26
  n123 -- 答える --> n204
  n123 -- 前提にする --> n126
  n123 -- 前提にする --> n146
  n123 -- 前提にする --> n151
  n123 -- 影響する --> n26
  n124 -- 答える --> n202
  n124 -- 前提にする --> n106
  n124 -- 前提にする --> n122
  n124 -- 影響する --> n26
  n125 -- 前提にする --> n70
  n125 -- 影響する --> n26
  n126 -- 前提にする --> n95
  n126 -- 影響する --> n26
  n126 -- 答える --> n240
  n127 -- 答える --> n228
  n127 -- 前提にする --> n68
  n127 -- 前提にする --> n270
  n127 -- 前提にする --> n251
  n127 -- 前提にする --> n123
  n127 -- 影響する --> n26
  n128 -- 影響する --> n26
  n129 -- 影響する --> n196
  n131 -- 根拠になる --> n87
  n132 -- 根拠になる --> n232
  n133 -- 根拠になる --> n232
  n134 -- 影響する --> n26
  n135 -- 根拠になる --> n229
  n135 -- 食い違う --> n253
  n136 -- 影響する --> n241
  n137 -- 影響する --> n198
  n137 -- 根拠になる --> n141
  n138 -- 根拠になる --> n240
  n138 -- 根拠になる --> n198
  n139 -- 根拠になる --> n232
  n139 -- 食い違う --> n73
  n140 -- 根拠になる --> n232
  n141 -- 食い違う --> n232
  n142 -- 根拠になる --> n228
  n143 -- 根拠になる --> n229
  n144 -- 影響する --> n229
  n144 -- 根拠になる --> n95
  n145 -- 影響する --> n232
  n146 -- 根拠になる --> n232
  n147 -- 根拠になる --> n228
  n148 -- 影響する --> n229
  n149 -- 影響する --> n229
  n150 -- 影響する --> n229
  n151 -- 根拠になる --> n232
  n152 -- 影響する --> n241
  n153 -- 食い違う --> n229
  n154 -- 根拠になる --> n232
  n155 -- 影響する --> n229
  n156 -- 根拠になる --> n241
  n157 -- 影響する --> n173
  n158 -- 影響する --> n77
  n158 -- 新たな問いを生む --> n208
  n158 -- 新たな問いを生む --> n207
  n159 -- 影響する --> n77
  n159 -- 前提にする --> n57
  n160 -- 答える --> n207
  n160 -- 影響する --> n158
  n161 -- 新たな問いを生む --> n211
  n162 -- 影響する --> n45
  n162 -- 新たな問いを生む --> n235
  n162 -- 新たな問いを生む --> n177
  n162 -- 影響する --> n176
  n163 -- 答える --> n197
  n163 -- 新たな問いを生む --> n176
  n163 -- 影響する --> n187
  n163 -- 影響する --> n230
  n163 -- 影響する --> n77
  n163 -- 影響する --> n15
  n164 -- 答える --> n244
  n165 -- 答える --> n213
  n165 -- 新たな問いを生む --> n214
  n165 -- 根拠になる --> n88
  n166 -- 影響する --> n21
  n167 -- 影響する --> n196
  n167 -- 根拠になる --> n62
  n168 -- 新たな問いを生む --> n222
  n169 -- 答える --> n222
  n169 -- 置き換える --> n168
  n169 -- 影響する --> n207
  n170 -- 影響する --> n19
  n171 -- 根拠になる --> n77
  n172 -- 影響する --> n195
  n172 -- 新たな問いを生む --> n191
  n173 -- 前提にする --> n228
  n173 -- 前提にする --> n73
  n174 -- 前提にする --> n259
  n174 -- 影響する --> n159
  n175 -- 前提にする --> n0
  n175 -- 影響する --> n217
  n176 -- 前提にする --> n187
  n177 -- 前提にする --> n230
  n177 -- 前提にする --> n162
  n178 -- 前提にする --> n46
  n178 -- 前提にする --> n230
  n179 -- 前提にする --> n46
  n179 -- 前提にする --> n58
  n180 -- 前提にする --> n88
  n183 -- 前提にする --> n61
  n184 -- 前提にする --> n113
  n184 -- 影響する --> n237
  n185 -- 前提にする --> n30
  n186 -- 前提にする --> n44
  n187 -- 前提にする --> n197
  n188 -- 前提にする --> n45
  n189 -- 前提にする --> n269
  n190 -- 影響する --> n18
  n190 -- 前提にする --> n212
  n192 -- 前提にする --> n77
  n192 -- 影響する --> n52
  n193 -- 前提にする --> n49
  n194 -- 影響する --> n77
  n195 -- 前提にする --> n230
  n195 -- 前提にする --> n242
  n196 -- 前提にする --> n195
  n198 -- 前提にする --> n154
  n198 -- 前提にする --> n204
  n198 -- 影響する --> n26
  n202 -- 前提にする --> n106
  n202 -- 前提にする --> n198
  n202 -- 影響する --> n26
  n203 -- 影響する --> n54
  n204 -- 前提にする --> n73
  n204 -- 影響する --> n26
  n205 -- 影響する --> n16
  n206 -- 影響する --> n20
  n207 -- 前提にする --> n222
  n207 -- 影響する --> n158
  n208 -- 前提にする --> n77
  n210 -- 前提にする --> n44
  n211 -- 前提にする --> n161
  n212 -- 前提にする --> n225
  n215 -- 影響する --> n22
  n217 -- 前提にする --> n66
  n217 -- 前提にする --> n5
  n218 -- 影響する --> n51
  n219 -- 前提にする --> n84
  n220 -- 影響する --> n69
  n223 -- 前提にする --> n5
  n223 -- 前提にする --> n66
  n223 -- 影響する --> n26
  n225 -- 前提にする --> n242
  n226 -- 影響する --> n67
  n226 -- 影響する --> n54
  n227 -- 前提にする --> n14
  n227 -- 影響する --> n16
  n228 -- 前提にする --> n229
  n228 -- 影響する --> n232
  n229 -- 前提にする --> n279
  n229 -- 影響する --> n232
  n230 -- 前提にする --> n197
  n231 -- 前提にする --> n73
  n231 -- 前提にする --> n59
  n231 -- 前提にする --> n230
  n231 -- 影響する --> n26
  n232 -- 前提にする --> n73
  n232 -- 影響する --> n26
  n233 -- 前提にする --> n73
  n233 -- 影響する --> n26
  n235 -- 前提にする --> n162
  n235 -- 影響する --> n193
  n236 -- 前提にする --> n62
  n238 -- 前提にする --> n273
  n238 -- 前提にする --> n45
  n239 -- 前提にする --> n83
  n240 -- 影響する --> n26
  n241 -- 前提にする --> n229
  n242 -- 前提にする --> n214
  n242 -- 前提にする --> n197
  n242 -- 前提にする --> n195
  n243 -- 前提にする --> n242
  n244 -- 前提にする --> n92
  n245 -- 前提にする --> n74
  n246 -- 前提にする --> n247
  n246 -- 前提にする --> n230
  n247 -- 前提にする --> n289
  n247 -- 影響する --> n22
  n249 -- 検証項目 --> n250
  n249 -- 根拠になる --> n54
  n249 -- 影響する --> n67
  n250 -- 根拠になる --> n88
  n250 -- 新たな問いを生む --> n225
  n250 -- 影響する --> n15
  n251 -- 新たな問いを生む --> n228
  n251 -- 影響する --> n26
  n252 -- 影響する --> n26
  n252 -- 新たな問いを生む --> n231
  n253 -- 影響する --> n229
  n253 -- 影響する --> n26
  n254 -- 根拠になる --> n47
  n254 -- 影響する --> n26
  n254 -- 答える --> n248
  n255 -- 新たな問いを生む --> n231
  n256 -- 影響する --> n26
  n257 -- 影響する --> n26
  n258 -- 影響する --> n26
  n258 -- 新たな問いを生む --> n231
  n259 -- 影響する --> n46
  n260 -- 根拠になる --> n88
  n260 -- 答える --> n234
  n260 -- 影響する --> n27
  n261 -- 根拠になる --> n88
  n261 -- 根拠になる --> n48
  n262 -- 根拠になる --> n78
  n263 -- 新たな問いを生む --> n195
  n263 -- 根拠になる --> n77
  n264 -- 影響する --> n24
  n265 -- 影響する --> n17
  n266 -- 根拠になる --> n79
  n266 -- 影響する --> n195
  n266 -- 前提にする --> n230
  n267 -- 影響する --> n24
  n267 -- 影響する --> n28
  n268 -- 影響する --> n84
  n269 -- 検証項目 --> n44
  n269 -- 影響する --> n178
  n269 -- 新たな問いを生む --> n189
  n270 -- 影響する --> n228
  n271 -- 新たな問いを生む --> n224
  n271 -- 影響する --> n27
  n272 -- 根拠になる --> n47
  n272 -- 根拠になる --> n88
  n272 -- 答える --> n248
  n273 -- 影響する --> n238
  n274 -- 影響する --> n240
  n275 -- 影響する --> n240
  n276 -- 影響する --> n14
  n276 -- 新たな問いを生む --> n181
  n277 -- 根拠になる --> n164
  n277 -- 影響する --> n50
  n279 -- 新たな問いを生む --> n229
  n279 -- 影響する --> n26
  n280 -- 影響する --> n51
  n281 -- 影響する --> n3
  n281 -- 根拠になる --> n54
  n282 -- 食い違う --> n47
  n282 -- 新たな問いを生む --> n230
  n282 -- 影響する --> n195
  n283 -- 影響する --> n18
  n284 -- 根拠になる --> n54
  n285 -- 影響する --> n16
  n286 -- 影響する --> n54
  n287 -- 影響する --> n187
  n288 -- 食い違う --> n47
  n288 -- 影響する --> n195
  n288 -- 影響する --> n26
  n289 -- 根拠になる --> n47
  n289 -- 答える --> n248
  n290 -- 根拠になる --> n79
  n290 -- 影響する --> n195
  n291 -- 影響する --> n266
  class n0 finding_confirmed
  class n1 finding_confirmed
  class n2 finding_confirmed
  class n3 finding_confirmed
  class n4 finding_confirmed
  class n5 finding_confirmed
  class n6 finding_unverified
  class n7 finding_confirmed
  class n8 finding_confirmed
  class n9 finding_unverified
  class n10 finding_unverified
  class n11 finding_unverified
  class n12 finding_outdated
  class n13 finding_confirmed
  class n14 component_current
  class n15 component_current
  class n16 component_current
  class n17 component_current
  class n18 component_current
  class n19 component_current
  class n20 component_current
  class n21 component_current
  class n22 component_planned
  class n23 component_current
  class n24 component_current
  class n25 component_current
  class n26 component_current
  class n27 component_current
  class n28 component_retired
  class n29 finding_confirmed
  class n30 finding_confirmed
  class n31 finding_outdated
  class n32 finding_confirmed
  class n33 finding_confirmed
  class n34 finding_confirmed
  class n35 finding_confirmed
  class n36 finding_confirmed
  class n37 finding_unverified
  class n38 finding_confirmed
  class n39 finding_unverified
  class n40 finding_unverified
  class n41 finding_confirmed
  class n42 decision_adopted
  class n43 decision_adopted
  class n44 decision_adopted
  class n45 decision_adopted
  class n46 decision_adopted
  class n47 decision_superseded
  class n48 decision_superseded
  class n49 decision_adopted
  class n50 decision_adopted
  class n51 decision_adopted
  class n52 decision_adopted
  class n53 decision_adopted
  class n54 decision_adopted
  class n55 decision_adopted
  class n56 decision_adopted
  class n57 decision_adopted
  class n58 decision_adopted
  class n59 decision_adopted
  class n60 decision_adopted
  class n61 decision_adopted
  class n62 decision_proposed
  class n63 decision_adopted
  class n64 decision_adopted
  class n65 decision_adopted
  class n66 decision_adopted
  class n67 decision_adopted
  class n68 decision_adopted
  class n69 decision_adopted
  class n70 decision_adopted
  class n71 decision_superseded
  class n72 decision_adopted
  class n73 decision_adopted
  class n74 decision_adopted
  class n75 decision_adopted
  class n76 decision_adopted
  class n77 decision_adopted
  class n78 decision_superseded
  class n79 decision_superseded
  class n80 decision_adopted
  class n81 decision_adopted
  class n82 decision_adopted
  class n83 decision_adopted
  class n84 decision_proposed
  class n85 decision_adopted
  class n86 decision_adopted
  class n87 decision_adopted
  class n88 decision_superseded
  class n89 decision_adopted
  class n90 finding_unverified
  class n91 decision_proposed
  class n92 component_retired
  class n93 finding_unverified
  class n94 finding_unverified
  class n95 finding_confirmed
  class n96 finding_confirmed
  class n97 finding_confirmed
  class n98 finding_confirmed
  class n99 finding_confirmed
  class n100 finding_confirmed
  class n101 finding_confirmed
  class n102 finding_confirmed
  class n103 finding_confirmed
  class n104 finding_unverified
  class n105 finding_confirmed
  class n106 finding_confirmed
  class n107 finding_confirmed
  class n108 finding_unverified
  class n109 finding_confirmed
  class n110 finding_unverified
  class n111 finding_confirmed
  class n112 finding_unverified
  class n113 finding_confirmed
  class n114 finding_confirmed
  class n115 finding_confirmed
  class n116 finding_unverified
  class n117 finding_confirmed
  class n118 finding_confirmed
  class n119 finding_unverified
  class n120 finding_confirmed
  class n121 finding_confirmed
  class n122 finding_confirmed
  class n123 finding_confirmed
  class n124 finding_confirmed
  class n125 finding_confirmed
  class n126 finding_confirmed
  class n127 finding_confirmed
  class n128 finding_confirmed
  class n129 finding_unverified
  class n130 finding_confirmed
  class n131 finding_unverified
  class n132 finding_confirmed
  class n133 finding_confirmed
  class n134 finding_unverified
  class n135 finding_confirmed
  class n136 finding_unverified
  class n137 finding_confirmed
  class n138 finding_unverified
  class n139 finding_confirmed
  class n140 finding_confirmed
  class n141 finding_confirmed
  class n142 finding_confirmed
  class n143 finding_unverified
  class n144 finding_unverified
  class n145 finding_unverified
  class n146 finding_confirmed
  class n147 finding_confirmed
  class n148 finding_unverified
  class n149 finding_confirmed
  class n150 finding_confirmed
  class n151 finding_confirmed
  class n152 finding_confirmed
  class n153 finding_confirmed
  class n154 finding_confirmed
  class n155 finding_unverified
  class n156 finding_confirmed
  class n157 finding_unverified
  class n158 finding_confirmed
  class n159 finding_confirmed
  class n160 finding_confirmed
  class n161 finding_confirmed
  class n162 finding_confirmed
  class n163 finding_confirmed
  class n164 finding_confirmed
  class n165 finding_confirmed
  class n166 finding_confirmed
  class n167 finding_confirmed
  class n168 finding_outdated
  class n169 finding_confirmed
  class n170 finding_confirmed
  class n171 finding_confirmed
  class n172 finding_confirmed
  class n173 question_open
  class n174 question_open
  class n175 question_answered
  class n176 question_open
  class n177 question_open
  class n178 question_open
  class n179 question_open
  class n180 question_dropped
  class n181 question_dropped
  class n182 question_dropped
  class n183 question_open
  class n184 question_answered
  class n185 question_answered
  class n186 question_open
  class n187 question_answered
  class n188 question_open
  class n189 question_answered
  class n190 question_open
  class n191 question_open
  class n192 question_answered
  class n193 question_open
  class n194 question_answered
  class n195 question_answered
  class n196 question_open
  class n197 question_answered
  class n198 question_answered
  class n199 question_open
  class n200 question_open
  class n201 question_open
  class n202 question_answered
  class n203 question_answered
  class n204 question_open
  class n205 question_open
  class n206 question_open
  class n207 question_answered
  class n208 question_answered
  class n209 question_open
  class n210 question_open
  class n211 question_open
  class n212 question_open
  class n213 question_answered
  class n214 question_dropped
  class n215 question_open
  class n216 question_open
  class n217 question_open
  class n218 question_open
  class n219 question_open
  class n220 question_open
  class n221 question_open
  class n222 question_answered
  class n223 question_open
  class n224 question_open
  class n225 question_dropped
  class n226 question_open
  class n227 question_open
  class n228 question_answered
  class n229 question_open
  class n230 question_open
  class n231 question_open
  class n232 question_open
  class n233 question_open
  class n234 question_answered
  class n235 question_open
  class n236 question_open
  class n237 question_open
  class n238 question_answered
  class n239 question_open
  class n240 question_open
  class n241 question_answered
  class n242 question_dropped
  class n243 question_dropped
  class n244 question_answered
  class n245 question_answered
  class n246 question_dropped
  class n247 question_open
  class n248 question_answered
  class n249 finding_confirmed
  class n250 finding_unverified
  class n251 finding_confirmed
  class n252 finding_confirmed
  class n253 finding_confirmed
  class n254 finding_confirmed
  class n255 finding_confirmed
  class n256 finding_confirmed
  class n257 finding_unverified
  class n258 finding_confirmed
  class n259 finding_confirmed
  class n260 finding_confirmed
  class n261 finding_confirmed
  class n262 finding_unverified
  class n263 finding_confirmed
  class n264 finding_confirmed
  class n265 finding_confirmed
  class n266 finding_unverified
  class n267 finding_confirmed
  class n268 finding_unverified
  class n269 finding_confirmed
  class n270 finding_unverified
  class n271 finding_unverified
  class n272 finding_confirmed
  class n273 finding_confirmed
  class n274 finding_unverified
  class n275 finding_unverified
  class n276 finding_confirmed
  class n277 finding_confirmed
  class n278 finding_confirmed
  class n279 finding_confirmed
  class n280 finding_unverified
  class n281 finding_confirmed
  class n282 finding_unverified
  class n283 finding_confirmed
  class n284 finding_confirmed
  class n285 finding_confirmed
  class n286 finding_confirmed
  class n287 finding_confirmed
  class n288 finding_confirmed
  class n289 finding_confirmed
  class n290 finding_confirmed
  class n291 finding_confirmed
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

## 今後調べること（45 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [観点（値段・脚本・演出など）ごとに下げる相手を変える案を、どう確かめるか](notes/q-aspect-attribution-check.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md)<br>前提にする → [推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md)<br>[作ったデータでは、気になった所を仮定どおりに付ける人には効き、でたらめに付ける人には害があり、裏の答え合わせはその害をあまり拾えない](notes/eval-aspects-sim.md) が前提にする<br>[観点ごとの評価がある公開データ（Yahoo! Movies：物語・演技・演出・映像＋総合）が研究で使われている](notes/lit-yahoo-multicriteria.md) が影響する |
| [評価の画面に「気になった所」（任意・複数選択）のボタンを付けるか](notes/q-aspects-ui.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [推薦の計算 person-graded-v2 は、D1 の索引の作り（表と行）を変えない](notes/reco-v2-index-compatible.md)<br>影響する → [段 1（記録と評価）の画面 4 枚と書き込み 11 種が、Python と同じ応答を返すようになった](notes/migration-stage1-parity.md) |
| [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md) | 未着手 | 2026-10-13 | S23 | 前提にする → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした](notes/catalog-age-check.md) が影響する<br>[AWS はもう使っていない](notes/no-aws.md) が影響する<br>[EC2 は無い](notes/no-ec2.md) が新たな問いを生む |
| [取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md) | 未着手 | 2026-10-13 | S21, S23 | 前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>前提にする → [AWS はもう使っていない](notes/no-aws.md)<br>[取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md) が答える<br>[公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md) が影響する<br>[AWS はもう使っていない](notes/no-aws.md) が新たな問いを生む |
| [Worker の /api/catalogue は 1,000 件までしか返さない。これからの公演がそれより多いときどうするか](notes/q-catalogue-api-limit.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>[取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md) が新たな問いを生む<br>[サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た](notes/sitemap-first-run.md) が影響する |
| [移行ブランチの Python 版はカタログをコードの束に同梱する。D1 に毎日入れる作りとどう揃えるか](notes/q-catalogue-python-snapshot-vs-d1.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md)<br>前提にする → [画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md)<br>[取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md) が新たな問いを生む |
| [問い合わせ用のメールアドレス](notes/q-contact-email.md) | 未着手 | 2026-10-13 | S10, S25 | 前提にする → [運営者名は @return1_end（X）にする](notes/dec-operator-name.md) |
| [一度読んだ公演ページの更新（出演者の追加など）をどう拾い直すか](notes/q-corich-updates-after-first-read.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む](notes/dec-corich-sitemap.md) |
| [取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md) | 未着手 | 2026-10-13 | S23, S24 | 前提にする → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>[Claude の GitHub アプリは taguri-crawler にまだ入っていない](notes/claude-app-repo-access.md) が影響する<br>[GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) が影響する<br>[この作業環境の GitHub 連携では、新しいリポジトリを作れない](notes/gha-repo-create-forbidden.md) が新たな問いを生む |
| [D1 のバックアップと復元をどうするか](notes/q-d1-backup.md) | 未着手 | 2026-10-13 | ─ | 影響する → [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md)<br>前提にする → [D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md) |
| [Python Workers の CPU の制限と成熟度](notes/q-d1-python-workers.md) | 未着手 | 2026-10-13 | ─ | [D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md) が影響する<br>[D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）](notes/d1-free-write-limit.md) が答える<br>[別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている](notes/python-workers-migration-state.md) が新たな問いを生む |
| [データを持たないお試し版をどう作るか](notes/q-demo-trial-design.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md)<br>[Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md) が影響する |
| [どのドメインをどこで取るか](notes/q-domain.md) | 未着手 | 2026-10-13 | S04 | 前提にする → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[Cloudflare Registrar では .jp を取れない。DNS だけ Cloudflare に置くことはできる](notes/cf-registrar-no-jp.md) が影響する<br>[.com の卸値は 2026 年 11 月 1 日から年 10.97 ドルに上がる](notes/com-wholesale-2026.md) が影響する<br>[独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) が前提にする<br>[.jp は年 4,000 円前後（税の扱い・年額かは未確認）](notes/jp-domain-price.md) が影響する<br>[パスキーはドメインに結び付くので、ドメインを変えると使えなくなる](notes/passkey-rpid-domain.md) が影響する |
| [Firebase Authentication の無料枠の正確な範囲（メールリンク・利用者数）](notes/q-firebase-free-tier.md) | 未着手 | 2026-10-13 | ─ | [会員ログインは Firebase Authentication にする](notes/dec-firebase-auth.md) が新たな問いを生む |
| [Firebase の API キーに制限（Web サイト・使う API）を掛けたか](notes/q-firebase-key-restriction.md) | 未着手 | 2026-10-13 | ─ | [会員ログインは Firebase Authentication にする](notes/dec-firebase-auth.md) が新たな問いを生む<br>[Firebase の Web 用 API キーは秘密ではない（使える範囲は承認済みドメインとキーの制限で絞る）](notes/firebase-apikey-public.md) が新たな問いを生む |
| [アカウント削除で Firebase 側の利用者も本当に消えているか](notes/q-firebase-user-deletion.md) | 未着手 | 2026-10-13 | ─ | [アカウント削除は「削除」の入力と直近 10 分以内のログインを求める](notes/dec-account-deletion.md) が新たな問いを生む |
| [新しい要素を安全に入れる「裏の答え合わせ」をどう作るか（起案者が良いと判断）](notes/q-hidden-gate.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md) が答える<br>[最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md) が前提にする |
| [Worker の依存とログイン画面の組み立てを再現できるようにするか（lockfile）](notes/q-lockfile-reproducible.md) | 未着手 | 2026-10-13 | ─ | 影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [メールリンクのログインで、メールアドレスを端末に残してよいか](notes/q-login-email-storage.md) | 未着手 | 2026-10-13 | ─ | 影響する → [ログイン：Firebase Authentication（Google・メールリンク）](notes/comp-firebase-login.md) |
| [無料で使える外形監視と通知](notes/q-monitoring.md) | 未着手 | 2026-10-13 | S22, S23 | [カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした](notes/catalog-age-check.md) が影響する |
| [CoRich の検索を使えないとき、お気に入りの登録名や探してほしい題名で公演をどう探すか](notes/q-name-search-without-corich-search.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む](notes/dec-corich-sitemap.md) |
| [Worker の画面への切り替えを、日記帳など 4 画面だけ先にするか、全画面がそろってから一度にするか](notes/q-native-cutover.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [日記帳などを Worker の画面に切り替えるための今の状態（NATIVE_UI）](notes/native-cutover-map.md)<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が影響する<br>[日記帳などを Worker の画面に切り替えるための今の状態（NATIVE_UI）](notes/native-cutover-map.md) が新たな問いを生む |
| [D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md) | 未着手 | 2026-10-13 | S07, S10 | 前提にする → [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md)<br>[D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）](notes/d1-time-travel.md) が影響する<br>[D1 のバックアップと復元をどうするか](notes/q-d1-backup.md) が前提にする |
| [元の画面の Content-Security-Policy を強められるか](notes/q-original-ui-csp.md) | 未着手 | 2026-10-13 | ─ | 影響する → [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md) |
| [パスキーは実機（iPhone・Android・Mac・Windows）で登録・ログインできるか](notes/q-passkey-real-devices.md) | 未着手 | 2026-10-13 | ─ | [Google を使いたくない人のために、パスキーを新しく作る](notes/dec-passkeys.md) が新たな問いを生む |
| [昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [取得はすべて polite_http を通す](notes/dec-polite-crawling.md)<br>前提にする → [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md)<br>[記録と公演ページの自動の結び付けは、いまは持ち主の手元でしか動かない](notes/auto-link-current-state.md) が影響する<br>[記録を公演に結び付ける検索には、公開カタログの公演だけを出す](notes/dec-search-public-only.md) が新たな問いを生む<br>[古い記録を自動で結び付けるための「過去の公演の一覧」を、CoRich のページを読んで作ってよいか](notes/q-auto-link-past.md) が影響する |
| [起案者が「UI が素敵」と挙げた plainwalk はどのサイトか](notes/q-plainwalk-ui.md) | 未着手 | 2026-10-13 | ─ | 影響する → [既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md) |
| [好きな作品のポスターから色を取り出して画面を染めるには、何が要るか](notes/q-poster-palette.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md)<br>[見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md) が新たな問いを生む |
| [個人情報保護法で何が求められるか](notes/q-privacy-law.md) | 未着手 | 2026-10-13 | S10, S25 | ─ |
| [公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか](notes/q-public-reputation-signal.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md)<br>前提にする → [取得はすべて polite_http を通す](notes/dec-polite-crawling.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[作品そのものの評判（他の人の平均）は、人物の手がかりよりずっと強い（AUC 0.79 対 0.57）](notes/eval-douban-consensus-strong.md) が新たな問いを生む<br>[答え合わせの問題を固定しても、使うほど当たりは上がる（今の計算で 63%、graded で 74% の人）。ただし水準は低い](notes/eval-douban-learning-curve.md) が新たな問いを生む<br>[水準を大きく上げたのは「作り手・ジャンルの世間の評判」だけで、それは使っても上がらない](notes/eval-reputation-signals.md) が影響する |
| [サーバーの Python を何版に揃えるか](notes/q-python-version.md) | 未着手 | 2026-10-13 | S07 | [バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) が新たな問いを生む |
| [ポスターが R2 の上限 8 GB に近づいたら、どれを消すか](notes/q-r2-poster-growth.md) | 未着手 | 2026-10-13 | ─ | 影響する → [ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す](notes/dec-posters-r2.md)<br>影響する → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md)<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が新たな問いを生む |
| [ログイン・登録・検索の回数制限を Worker でどう掛けるか](notes/q-rate-limiting.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [画面の△の説明「あまり合わなかった」は、起案者の考える△（まあ良いが気になる所がある）と食い違う](notes/triangle-label-mismatch.md)<br>影響する → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md)<br>[評価の段階は利用者が選べる。初期設定は 5 段階、最小 2 段階・最大 11 段階](notes/dec-user-scale-range.md) が影響する<br>[全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる](notes/eval-douban-graded-better.md) が根拠になる<br>[◎○△× の 4 段階が適切だという直接の証拠は無い（「残す」は手間と既存の評価を理由にした判断）](notes/four-level-unsupported.md) が影響する<br>[「好み」と「評価の付け方の癖」を分けて扱うと精度が上がり、順位だけを使うと情報を捨てすぎる（Jin・Si・Zhai 2003）](notes/lit-decoupled-rating.md) が根拠になる<br>[低い評価は、とくにデータが少ないときに推薦の役に立つ（Negative ratings play a positive role in information filtering）](notes/lit-negative-ratings.md) が根拠になる<br>[評価を等間隔の数ではなく順序として扱う研究（OrdRec）と、少ない件数を割り引く「damping」は推薦の定番](notes/lit-ordinal-damping.md) が影響する<br>[同じ人が同じ作品を付け直しても評価はぶれる（Amatriain ほか 2009）](notes/lit-rating-noise.md) が影響する<br>[評価の段階は「付ける手間」と「推薦に使える情報量」の引き換えで、粗い段階は速いが情報が少ない（Sparling & Sen 2011・Kluver ほか 2012）](notes/lit-rating-scale-granularity.md) が影響する<br>[評価の付け方の癖は文化や個人で違い、日本や中国の回答者は真ん中を選びやすく、米国は端を選びやすい（Chen・Lee・Stevenson 1995、Harzing 2006）](notes/lit-response-style-culture.md) が影響する<br>[評価の段階数の研究では 2〜4 段階は信頼性・妥当性が低く、7 段階前後がよいとされる。ただし多ければ良いとも限らない](notes/lit-scale-points.md) が食い違う<br>[推薦では、利用者ごとの評価の甘さ辛さ（user bias）を差し引いて扱うのが定番（Koren 2008 ほか）](notes/lit-user-bias.md) が影響する<br>[総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md) が前提にする<br>[評価の段階を利用者自身に選んでもらうか（起案者の案）](notes/q-user-chosen-scale.md) が前提にする<br>[今の計算は「その人の◎の割合」を差し引くので、◎が珍しい人の◎ほど強く効き、◎ばかりの人の◎はほとんど効かない](notes/reco-base-rate-relative.md) が影響する<br>[画面の△の説明「あまり合わなかった」は、起案者の考える△（まあ良いが気になる所がある）と食い違う](notes/triangle-label-mismatch.md) が新たな問いを生む |
| [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md) | 未着手 | 2026-10-13 | S20, S21 | 前提にする → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>[D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）](notes/d1-free-write-limit.md) が新たな問いを生む<br>[1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) が前提にする<br>[EC2 は無い](notes/no-ec2.md) が影響する<br>[取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md) が前提にする<br>[Worker の /api/catalogue は 1,000 件までしか返さない。これからの公演がそれより多いときどうするか](notes/q-catalogue-api-limit.md) が前提にする<br>[サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) が前提にする<br>[推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md) が前提にする<br>[無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか](notes/q-workers-cpu-overrun.md) が前提にする<br>[1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) が前提にする<br>[Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) が新たな問いを生む |
| [推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md)<br>前提にする → [持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md) が影響する<br>[推薦の改善は、先に測る仕組みを作ってから計算を変える](notes/dec-reco-measure-first.md) が前提にする<br>[推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md) が影響する<br>[今の推薦（person-feedback-v1）の精度は、公開版の利用者では測っていない](notes/reco-accuracy-unverified.md) が新たな問いを生む<br>[推薦の良し悪しを測る仕組みが足りない（利用者ごとの時系列評価・正解データ・提示と結果の結び付け）](notes/reco-eval-gaps.md) が新たな問いを生む<br>[推薦の計算を改善する計画書はあるが、master に入っておらず内容が一部古い](notes/reco-plan-unmerged.md) が新たな問いを生む |
| [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[公開の映画評価データ（実在の 500 人）では、今の推薦は当てずっぽうに近い（AUC 0.50〜0.53）](notes/eval-douban-current-weak.md) が答える<br>[役職（出演・監督）の重みを人ごとに学んでも、この条件では良くならなかった](notes/eval-douban-role-learning-no-gain.md) が影響する<br>[当てる精度だけを上げると、役に立つ推薦から外れることがある（McNee ほか 2006・Ferrari Dacrema ほか 2019）](notes/lit-beyond-accuracy.md) が根拠になる<br>[順位を直接学ぶ「組で比べる」学習（BPR）は、AUC を最大にするのと同じ形（Rendle ほか 2009）](notes/lit-bpr-pairwise.md) が根拠になる<br>[利用者ごとの好みを、全体の事前分布から少しずつ個人に寄せる学習は確立した方法（Zhang & Koren 2007）](notes/lit-hierarchical-user-model.md) が根拠になる<br>[観る前の反応（興味あり・購入）は「好みの信号」だが確からしさが違うので、重みを変えて扱う（Hu・Koren・Volinsky 2008）](notes/lit-implicit-confidence.md) が根拠になる<br>[評価が付いていないこと自体が情報になり、付いた評価だけで学ぶ・測ると偏る（Steck 2010）](notes/lit-mnar.md) が食い違う<br>[舞台芸術の推薦の先行例は少なく、主に劇場側の販売データでの協調フィルタリング](notes/lit-performing-arts.md) が影響する<br>[届いた順に「予想してから答え合わせ」する評価（prequential）は、変わり続ける推薦の評価に使われている（Vinagre ほか 2014）](notes/lit-prequential.md) が根拠になる<br>[新しい方式は「前より悪くないと高い確信で言えるときだけ」採る、という考え方がある（Thomas ほか 2015）](notes/lit-safe-improvement.md) が根拠になる<br>[内容ベースの推薦で、本人の初期の好みを評価が増えるたびに修正する方法がある（Billsus & Pazzani）](notes/lit-syskill-webert-prior.md) が根拠になる<br>[総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md) が影響する<br>[◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) が影響する |
| [その人の記録だけで、計算方式の良し悪しをどう確かめるか（振り返りでの検証）](notes/q-reco-personal-backtest.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md) が新たな問いを生む |
| [Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [AWS はもう使っていない](notes/no-aws.md)<br>影響する → [データを持たないお試し版をどう作るか](notes/q-demo-trial-design.md)<br>[AWS はもう使っていない](notes/no-aws.md) が新たな問いを生む |
| [Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md) | 未着手 | 2026-10-13 | S04, S19 | 前提にする → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>[Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が新たな問いを生む |
| [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md) | 未着手 | 2026-10-13 | S11, S24 | [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) が新たな問いを生む<br>[CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している](notes/corich-robots-sitemap-only.md) が影響する<br>[取得元の実際の robots.txt はまだ読めていない](notes/corich-robots-unchecked.md) が新たな問いを生む<br>[CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md) が影響する |
| [あらすじを Claude の定期実行で読むと、1 日にどれだけ読め、起案者の使用枠をどれだけ使うか](notes/q-synopsis-routine-quota.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md)<br>[公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md) が新たな問いを生む |
| [観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md) | 未着手 | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[本人のジャンルの好みを足すと、人物だけより当たりが上がり、使うほどの伸びも大きくなる（映画の公開データ）](notes/eval-genre-preference.md) が新たな問いを生む<br>[舞台のジャンル分けは、チケット販売サイト・業界の白書・助成制度・演劇史の区分がそれぞれ独自に持っていて、共通の公式の分け方は無い](notes/genre-schemes-found.md) が影響する<br>[推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）](notes/impl-person-ordinal-v3.md) が答える<br>[映画のジャンルを使った推薦の研究は、主に「新しい利用者・新作の立ち上がり」のために使われている](notes/lit-genre-reco.md) が根拠になる<br>[舞台の公演に業界共通の公式のジャンル分けは見つからない。近いものは日本劇作家協会「戯曲デジタルアーカイブ」のジャンル（戯曲向け）](notes/theatre-genre-sources.md) が影響する<br>[持ち主の過去の検証では、あらすじのテーマ語は作品間で重なりにくく、一般的な語（家族・恋愛・コメディ・友情）に偏っていた](notes/theme-words-sparse-past.md) が影響する |
| [移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか](notes/q-workers-cpu-real.md) | 未着手 | 2026-10-13 | ─ | 前提にする → [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md)<br>影響する → [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md)<br>[無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか](notes/q-workers-cpu-overrun.md) が前提にする |
| [推薦側の PR #13（person-graded-v2・評価の段階・評価の「詳細」8 項目）を入れるか。入れるなら「詳細」の画面をこちらで作るか](notes/q-pr13-aspects-screen.md) | 未着手 | 2026-10-14 | ─ | 影響する → [おすすめの人物の理由には、本数ではなく具体的な作品名（と付けた印）を書く](notes/dec-reason-work-titles.md) |

## 決めたこと（49 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [デモ版とサービス版を分ける](notes/dec-edition-split.md) | 採用 | 2026-10-12 | S01, S09 | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [画面（web/・config.js）](notes/comp-frontend.md)<br>[デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) が前提にする<br>[デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) が影響する<br>[サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md) が前提にする<br>[Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md) が影響する |
| [取得はすべて polite_http を通す](notes/dec-polite-crawling.md) | 採用 | 2026-10-12 | S15, S24 | 影響する → [取得の作法（polite_http.py）](notes/comp-crawler.md)<br>[GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) が影響する<br>[昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) が前提にする<br>[公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか](notes/q-public-reputation-signal.md) が前提にする |
| [サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md) | 採用 | 2026-10-12 | S01 | 前提にする → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>[Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない](notes/dec-no-render-data-migration.md) が根拠になる |
| [アカウント削除は「削除」の入力と直近 10 分以内のログインを求める](notes/dec-account-deletion.md) | 採用 | 2026-10-13 | ─ | 影響する → [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md)<br>新たな問いを生む → [アカウント削除で Firebase 側の利用者も本当に消えているか](notes/q-firebase-user-deletion.md) |
| [過去の公演の一覧（2019 年以降）を毎日 6,000 枚ずつ作り、記録を自動で結び付ける](notes/dec-auto-link-past.md) | 採用 | 2026-10-13 | ─ | 答える → [古い記録を自動で結び付けるための「過去の公演の一覧」を、CoRich のページを読んで作ってよいか](notes/q-auto-link-past.md)<br>前提にする → [記録と公演ページの自動の結び付けは、いまは持ち主の手元でしか動かない](notes/auto-link-current-state.md)<br>[取得の Actions は毎日の更新が 1 回 約 9 分。過去の公演を 1 日 6,000 枚読むと月 3,600 分を越え、無料の 2,000 分に収まらない](notes/crawler-actions-minutes.md) が影響する<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が影響する |
| [GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む](notes/dec-corich-sitemap.md) | 採用 | 2026-10-13 | S24 | 前提にする → [CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）](notes/corich-search-waf-403.md)<br>前提にする → [CoRich のサイトマップには、すべての公演ページ（/stage/<id>）が更新日つきで載っている](notes/corich-sitemap-stage-ids.md)<br>影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>[一度読んだ公演ページの更新（出演者の追加など）をどう拾い直すか](notes/q-corich-updates-after-first-read.md) が前提にする<br>[CoRich の検索を使えないとき、お気に入りの登録名や探してほしい題名で公演をどう探すか](notes/q-name-search-without-corich-search.md) が前提にする<br>[サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た](notes/sitemap-first-run.md) が検証項目 |
| [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) | 採用 | 2026-10-13 | S23, S24 | 答える → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>前提にする → [非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md)<br>前提にする → [公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md)<br>前提にする → [取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）](notes/crawler-state-between-runs.md)<br>[CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）](notes/corich-search-waf-403.md) が影響する<br>[CoRich のサイトマップには、すべての公演ページ（/stage/<id>）が更新日つきで載っている](notes/corich-sitemap-stage-ids.md) が影響する<br>[GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む](notes/dec-corich-sitemap.md) が影響する<br>[取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md) が前提にする<br>[公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md) が前提にする<br>[この作業環境の GitHub 連携では、新しいリポジトリを作れない](notes/gha-repo-create-forbidden.md) が影響する<br>[実行中の GitHub Actions のジョブのログは API で取れない（404）。進み具合は手順の状態でしか見えない](notes/gha-running-job-logs-404.md) が影響する<br>[AWS はもう使っていない](notes/no-aws.md) が影響する<br>[取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md) が前提にする<br>[あらすじの読み取りを誰が担うか（Claude の定期実行・Gemini API・当面読まない）](notes/q-synopsis-reader.md) が前提にする |
| [取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md) | 採用 | 2026-10-13 | S21, S23 | 答える → [取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md)<br>前提にする → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>前提にする → [公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md)<br>前提にする → [無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md)<br>新たな問いを生む → [Worker の /api/catalogue は 1,000 件までしか返さない。これからの公演がそれより多いときどうするか](notes/q-catalogue-api-limit.md)<br>新たな問いを生む → [移行ブランチの Python 版はカタログをコードの束に同梱する。D1 に毎日入れる作りとどう揃えるか](notes/q-catalogue-python-snapshot-vs-d1.md)<br>[最初の毎日の Catalog は D1 に入れる段で落ちた。題名の中の U+2028 を splitlines が行の区切りにしたため（直した）](notes/catalog-daily-splitlines.md) が影響する<br>[Worker の /api/catalogue は 1,000 件までしか返さない。これからの公演がそれより多いときどうするか](notes/q-catalogue-api-limit.md) が前提にする<br>[移行ブランチの Python 版はカタログをコードの束に同梱する。D1 に毎日入れる作りとどう揃えるか](notes/q-catalogue-python-snapshot-vs-d1.md) が前提にする<br>[推薦の計算 person-graded-v2 は、D1 の索引の作り（表と行）を変えない](notes/reco-v2-index-compatible.md) が影響する |
| [デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) | 採用 | 2026-10-13 | ─ | 答える → [Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md)<br>影響する → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>置き換える → [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md)<br>[データを持たないお試し版をどう作るか](notes/q-demo-trial-design.md) が前提にする |
| [いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md) | 採用 | 2026-10-13 | ─ | 前提にする → [既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md)<br>前提にする → [見た目の調整室（起案者が色・文字・ボタン・配置・文言を決めて保存し、Claude が読み取って実際の画面に反映する）](notes/design-studio.md)<br>影響する → [見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md)<br>[読み込み画面 ── 幕と歩くピクトグラムをやめ、毛糸玉が転がって糸をたぐる形にする](notes/dec-loading-yarn.md) が影響する<br>[スマホの見出し ── 4 つの大メニューを均等割りで常に出し、子メニューはすだれで出す](notes/dec-phone-nav-four.md) が影響する<br>[「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md) が影響する<br>[評価一覧などの記録の 1 件をおすすめの 1 枚と同じ形にし、感想はその文の上で書き直す](notes/dec-record-row-card.md) が影響する<br>[パソコンの見た目の案（左の行き先の帯に 14 項目を組で並べ、本文は 920px 幅、半券にポスターの列）](notes/design-desktop.md) が前提にする<br>[題字の書体の候補（明朝と本文ゴシックの間）── どれも SIL OFL](notes/title-font-candidates.md) が影響する |
| [既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md) | 採用 | 2026-10-13 | ─ | 答える → [たぐりの見た目をどの方向に変えるか（A 幕と半券・B 観劇ノート・C 客電が落ちる）](notes/q-design-direction.md)<br>前提にする → [見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md)<br>前提にする → [シンプルなデザインは「削る」ことではなく、要るものを一つに絞って際立たせ、押せる手がかりは残すこと](notes/simple-design-principles.md)<br>[いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md) が前提にする<br>[見た目の調整室（起案者が色・文字・ボタン・配置・文言を決めて保存し、Claude が読み取って実際の画面に反映する）](notes/design-studio.md) が前提にする<br>[起案者が「UI が素敵」と挙げた plainwalk はどのサイトか](notes/q-plainwalk-ui.md) が影響する<br>[note・Notion のような白基調の記録サイトの見た目（白い紙面・真っ黒でない文字・差し色 1 つ・広い余白）](notes/white-record-sites.md) が影響する |
| [会員ログインは Firebase Authentication にする](notes/dec-firebase-auth.md) | 採用 | 2026-10-13 | ─ | 影響する → [ログイン：Firebase Authentication（Google・メールリンク）](notes/comp-firebase-login.md)<br>新たな問いを生む → [Firebase の API キーに制限（Web サイト・使う API）を掛けたか](notes/q-firebase-key-restriction.md)<br>新たな問いを生む → [Firebase Authentication の無料枠の正確な範囲（メールリンク・利用者数）](notes/q-firebase-free-tier.md) |
| [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) | 採用 | 2026-10-13 | ─ | 置き換える → [1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md)<br>前提にする → [R2 の無料枠は保存 10 GB・Class A 月 100 万回・Class B 月 1,000 万回で、越えた分は請求される（取り出しの通信料は無料）](notes/r2-free-tier-billed.md)<br>前提にする → [Actions の無料の分は毎月 0 に戻り、月払いの支払いの上限は既定で 0 ドル（越えると止まる）](notes/gha-minutes-reset-budget.md)<br>前提にする → [D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md)<br>前提にする → [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md)<br>影響する → [過去の公演の一覧（2019 年以降）を毎日 6,000 枚ずつ作り、記録を自動で結び付ける](notes/dec-auto-link-past.md)<br>影響する → [ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す](notes/dec-posters-r2.md)<br>影響する → [Worker の画面への切り替えを、日記帳など 4 画面だけ先にするか、全画面がそろってから一度にするか](notes/q-native-cutover.md)<br>新たな問いを生む → [起案者のアカウントの設定で、無料枠を越えても請求されないようになっているか](notes/q-free-tier-account-settings.md)<br>新たな問いを生む → [ポスターが R2 の上限 8 GB に近づいたら、どれを消すか](notes/q-r2-poster-growth.md)<br>[Cloudflare には R2 の使いすぎを止める仕組みが無い。予算の通知（Budget alerts）は知らせるだけ](notes/cf-budget-alerts-not-cap.md) が根拠になる<br>[取得の Actions は毎日の更新が 1 回 約 9 分。過去の公演を 1 日 6,000 枚読むと月 3,600 分を越え、無料の 2,000 分に収まらない](notes/crawler-actions-minutes.md) が根拠になる<br>[起案者が Cloudflare の Budget alerts を作り、Workers の Free を確かめた。GitHub には支払い方法を登録していない](notes/free-tier-account-settings-done.md) が根拠になる<br>[Actions の無料の分は毎月 0 に戻り、月払いの支払いの上限は既定で 0 ドル（越えると止まる）](notes/gha-minutes-reset-budget.md) が根拠になる<br>[起案者のアカウントの設定で、無料枠を越えても請求されないようになっているか](notes/q-free-tier-account-settings.md) が影響する<br>[ポスターが R2 の上限 8 GB に近づいたら、どれを消すか](notes/q-r2-poster-growth.md) が影響する<br>[R2 の無料枠は保存 10 GB・Class A 月 100 万回・Class B 月 1,000 万回で、越えた分は請求される（取り出しの通信料は無料）](notes/r2-free-tier-billed.md) が根拠になる<br>[本番の Worker の /api/health は、Render への橋渡しに取られて 404 になっていた（直した）](notes/worker-health-bridged-404.md) が根拠になる<br>[Workers Builds（GitHub からの自動配信）は無料プランで月 3,000 分・同時 1 本・1 回 20 分まで](notes/workers-builds-free-3000.md) が根拠になる<br>[Workers の Cache API は *.workers.dev では何もしない（独自ドメインでだけ効く）](notes/workers-cache-api-workers-dev.md) が影響する |
| [推薦の理由に本人の感想（「あなたの言葉」）を引かない ── デモ版もサービス版も](notes/dec-hide-own-words.md) | 採用 | 2026-10-13 | ─ | 影響する → [「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md) |
| [読み込み画面 ── 幕と歩くピクトグラムをやめ、毛糸玉が転がって糸をたぐる形にする](notes/dec-loading-yarn.md) | 採用 | 2026-10-13 | ─ | 影響する → [いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md) |
| [画面の移行は wip-screens-port で進め、段ごとに試験が通ってから master に入れる](notes/dec-migration-branch-wip.md) | 採用 | 2026-10-13 | ─ | 答える → [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md)<br>前提にする → [本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md)<br>前提にする → [画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md)<br>[段 1（記録と評価）の画面 4 枚と書き込み 11 種が、Python と同じ応答を返すようになった](notes/migration-stage1-parity.md) が前提にする |
| [画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) | 採用 | 2026-10-13 | ─ | 答える → [画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md)<br>前提にする → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>影響する → [Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md)<br>[画面の移行は wip-screens-port で進め、段ごとに試験が通ってから master に入れる](notes/dec-migration-branch-wip.md) が前提にする<br>[移行ブランチの Python 版はカタログをコードの束に同梱する。D1 に毎日入れる作りとどう揃えるか](notes/q-catalogue-python-snapshot-vs-d1.md) が前提にする |
| [持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md) | 採用 | 2026-10-13 | ─ | 影響する → [過去の改善の実験結果（持ち主 1 人の評価での AUC）は、判断の根拠に使わない](notes/reco-past-auc.md)<br>影響する → [推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[作ったデータでは、気になった所を仮定どおりに付ける人には効き、でたらめに付ける人には害があり、裏の答え合わせはその害をあまり拾えない](notes/eval-aspects-sim.md) が前提にする<br>[お気に入りを仮の評価にすると、評価0件のときだけ当たりが上がる（+0.014〜0.015）。すぐ薄めれば後で下がらない](notes/eval-favourite-seed.md) が前提にする<br>[裏の答え合わせは「組を数える」「前の作品と比べる」とでたらめな人でも切り替わる。区切りごとに数えると誤りは 3% 以下](notes/eval-hidden-gate-sim.md) が前提にする<br>[推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md) が前提にする |
| [Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない](notes/dec-no-render-data-migration.md) | 採用 | 2026-10-13 | ─ | 根拠になる → [サービス版は空から始め、デモの記録を移さない](notes/dec-service-starts-empty.md)<br>前提にする → [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) |
| [運営者名は @return1_end（X）にする](notes/dec-operator-name.md) | 採用 | 2026-10-13 | ─ | [問い合わせ用のメールアドレス](notes/q-contact-email.md) が前提にする |
| [Google を使いたくない人のために、パスキーを新しく作る](notes/dec-passkeys.md) | 採用 | 2026-10-13 | ─ | 影響する → [ログイン：パスキー（Google を使わない人向け）](notes/comp-passkeys.md)<br>新たな問いを生む → [パスキーは実機（iPhone・Android・Mac・Windows）で登録・ログインできるか](notes/q-passkey-real-devices.md) |
| [スマホの見出し ── 4 つの大メニューを均等割りで常に出し、子メニューはすだれで出す](notes/dec-phone-nav-four.md) | 採用 | 2026-10-13 | ─ | 影響する → [いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md)<br>前提にする → [題字の書体の候補（明朝と本文ゴシックの間）── どれも SIL OFL](notes/title-font-candidates.md)<br>[「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md) が前提にする |
| [ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す](notes/dec-posters-r2.md) | 採用 | 2026-10-13 | ─ | 答える → [取得の作業データ（state ブランチ）が 2 GB になった。ポスターと公演ページの HTML の控えをどうするか](notes/q-crawler-state-size.md)<br>答える → [Cloudflare 版でポスターをどこに置いて出すか](notes/q-worker-posters.md)<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が影響する<br>[ポスターが R2 の上限 8 GB に近づいたら、どれを消すか](notes/q-r2-poster-growth.md) が影響する<br>[R2 の無料枠は保存 10 GB・Class A 月 100 万回・Class B 月 1,000 万回で、越えた分は請求される（取り出しの通信料は無料）](notes/r2-free-tier-billed.md) が影響する |
| [推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない](notes/dec-reco-graded.md) | 採用 | 2026-10-13 | ─ | 前提にする → [全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる](notes/eval-douban-graded-better.md)<br>置き換える → [推薦の改善は、先に測る仕組みを作ってから計算を変える](notes/dec-reco-measure-first.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>影響する → [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md)<br>[答え合わせの問題を固定しても、使うほど当たりは上がる（今の計算で 63%、graded で 74% の人）。ただし水準は低い](notes/eval-douban-learning-curve.md) が根拠になる<br>[推薦の計算を person-graded-v2 に変えた（Python 版と Worker 版の両方、同じ結果になることをテストで確認）](notes/impl-person-graded-v2.md) が前提にする |
| [おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) | 採用 | 2026-10-13 | ─ | 置き換える → [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md)<br>前提にする → [Worker の推薦は Python（person-feedback-v1）と同じ結果を出す](notes/reco-js-parity.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md) | 採用 | 2026-10-13 | ─ | 影響する → [推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md)<br>影響する → [推薦の改善は、先に測る仕組みを作ってから計算を変える](notes/dec-reco-measure-first.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>新たな問いを生む → [その人の記録だけで、計算方式の良し悪しをどう確かめるか（振り返りでの検証）](notes/q-reco-personal-backtest.md)<br>[利用者ごとの好みを、全体の事前分布から少しずつ個人に寄せる学習は確立した方法（Zhang & Koren 2007）](notes/lit-hierarchical-user-model.md) が食い違う<br>[観点（値段・脚本・演出など）ごとに下げる相手を変える案を、どう確かめるか](notes/q-aspect-attribution-check.md) が前提にする<br>[新しい要素を安全に入れる「裏の答え合わせ」をどう作るか（起案者が良いと判断）](notes/q-hidden-gate.md) が前提にする<br>[推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md) が前提にする<br>[「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) が前提にする<br>[その人の記録だけで、計算方式の良し悪しをどう確かめるか（振り返りでの検証）](notes/q-reco-personal-backtest.md) が前提にする |
| [「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md) | 採用 | 2026-10-13 | ─ | 影響する → [いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md)<br>前提にする → [スマホの見出し ── 4 つの大メニューを均等割りで常に出し、子メニューはすだれで出す](notes/dec-phone-nav-four.md)<br>新たな問いを生む → [Cloudflare 版でポスターをどこに置いて出すか](notes/q-worker-posters.md)<br>[推薦の理由に本人の感想（「あなたの言葉」）を引かない ── デモ版もサービス版も](notes/dec-hide-own-words.md) が影響する<br>[おすすめの券の見直し（2026-10-14 の 10 項目）── 回答の帯は右寄せ・興味なしはグレー・書き込み中・説明はインフォへ・もう追いかけない束をやめる・名前の札・絵記号・期間の表記・ツアーの日程・発売の札から券の案内へ](notes/dec-recommend-ui-1014.md) が影響する<br>[評価一覧などの記録の 1 件をおすすめの 1 枚と同じ形にし、感想はその文の上で書き直す](notes/dec-record-row-card.md) が前提にする<br>[Cloudflare 版でポスターをどこに置いて出すか](notes/q-worker-posters.md) が前提にする |
| [評価一覧などの記録の 1 件をおすすめの 1 枚と同じ形にし、感想はその文の上で書き直す](notes/dec-record-row-card.md) | 採用 | 2026-10-13 | ─ | 影響する → [いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md)<br>前提にする → [「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md)<br>[評価の分布を発散型の帯にし、判子から評価を選び直す。＋は登録の 3 つの入口を開く](notes/dec-verdict-diverging.md) が影響する |
| [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) | 採用 | 2026-10-13 | ─ | 食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>食い違う → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>前提にする → [元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）](notes/render-ui-server-rendered.md)<br>影響する → [元の画面の Worker 版（cloudflare/src/screens/）](notes/comp-native-screens.md)<br>影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) が前提にする<br>[Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) が影響する<br>[段 1（記録と評価）の画面 4 枚と書き込み 11 種が、Python と同じ応答を返すようになった](notes/migration-stage1-parity.md) が影響する<br>[EC2 は無い](notes/no-ec2.md) が影響する<br>[Python の画面は一時保存先・固定日付・通信なしで、テストの中から動かせる](notes/python-screens-harness.md) が根拠になる<br>[Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md) が前提にする<br>[たぐりの見た目をどの方向に変えるか（A 幕と半券・B 観劇ノート・C 客電が落ちる）](notes/q-design-direction.md) が影響する<br>[画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md) が前提にする<br>[Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている](notes/render-two-identities.md) が根拠になる |
| [記録を公演に結び付ける検索には、公開カタログの公演だけを出す](notes/dec-search-public-only.md) | 採用 | 2026-10-13 | ─ | 新たな問いを生む → [昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) |
| [ログインしていない人に見せるのは「ログイン」と「たぐりとは」だけ](notes/dec-signed-out-gate.md) | 採用 | 2026-10-13 | ─ | 影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md) | 採用 | 2026-10-13 | ─ | 答える → [あらすじの読み取りを誰が担うか（Claude の定期実行・Gemini API・当面読まない）](notes/q-synopsis-reader.md)<br>前提にする → [あらすじの読み取りは Gemini API。以前の claude CLI 呼び出しは起案者の判断でやめている](notes/synopsis-llm-history.md)<br>前提にする → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>影響する → [取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md)<br>新たな問いを生む → [あらすじを Claude の定期実行で読むと、1 日にどれだけ読め、起案者の使用枠をどれだけ使うか](notes/q-synopsis-routine-quota.md)<br>[取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md) が前提にする<br>[あらすじを Claude の定期実行で読むと、1 日にどれだけ読め、起案者の使用枠をどれだけ使うか](notes/q-synopsis-routine-quota.md) が前提にする |
| [評価の段階は利用者が選べる。初期設定は 5 段階、最小 2 段階・最大 11 段階](notes/dec-user-scale-range.md) | 採用 | 2026-10-13 | ─ | 答える → [評価の段階を利用者自身に選んでもらうか（起案者の案）](notes/q-user-chosen-scale.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>[評価の段階を粗くしても当たりは少し下がるだけで、途中で段階を変えた人は「同じ段階どうしで比べる」のがよい](notes/eval-douban-scales.md) が根拠になる |
| [評価の分布を発散型の帯にし、判子から評価を選び直す。＋は登録の 3 つの入口を開く](notes/dec-verdict-diverging.md) | 採用 | 2026-10-13 | ─ | 前提にする → [評定（◎○△×）の分布は、0 を中心に左右へ分ける積み上げ棒がよい ── 可視化の論文から](notes/likert-diverging-bars.md)<br>影響する → [評価一覧などの記録の 1 件をおすすめの 1 枚と同じ形にし、感想はその文の上で書き直す](notes/dec-record-row-card.md)<br>[評定（◎○△×）の分布は、0 を中心に左右へ分ける積み上げ棒がよい ── 可視化の論文から](notes/likert-diverging-bars.md) が根拠になる |
| [無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) | 採用 | 2026-10-13 | ─ | 答える → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>置き換える → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>置き換える → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>前提にする → [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md)<br>影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md) が前提にする |
| [「すでに持っている」を押した公演は購入済み公演にだけ出し、終わったら未評価に出す。前に開いてから終わった未評価があれば、おすすめを開いたときに知らせる](notes/dec-owned-only-owned-list.md) | 採用 | 2026-10-14 | ─ | ─ |
| [評価の詳細は任意で隠しておき、項目ごとに「良かった／気になった」を付けられる。詳しく記録するか、あっさり付けるかは人が選ぶ](notes/dec-rating-detail-mode.md) | 採用 | 2026-10-14 | ─ | 影響する → [評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md)<br>前提にする → [総合評価に加えて観点ごとの評価を使う推薦（多基準推薦）は、1 つの評価だけより精度が上がったと報告されている（Adomavicius & Kwon 2007 ほか）](notes/lit-multi-criteria.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md) が前提にする |
| [おすすめの人物の理由には、本数ではなく具体的な作品名（と付けた印）を書く](notes/dec-reason-work-titles.md) | 採用 | 2026-10-14 | ─ | [推薦側の PR #13（person-graded-v2・評価の段階・評価の「詳細」8 項目）を入れるか。入れるなら「詳細」の画面をこちらで作るか](notes/q-pr13-aspects-screen.md) が影響する |
| [おすすめの券の見直し（2026-10-14 の 10 項目）── 回答の帯は右寄せ・興味なしはグレー・書き込み中・説明はインフォへ・もう追いかけない束をやめる・名前の札・絵記号・期間の表記・ツアーの日程・発売の札から券の案内へ](notes/dec-recommend-ui-1014.md) | 採用 | 2026-10-14 | ─ | 前提にする → [CoRich の公演ページの表にはプレイガイド（券の販売先）の欄が無い。名前が料金の欄の文に 1 割ほど出るだけ](notes/corich-no-playguide-field.md)<br>影響する → [「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md)<br>[CoRich の公演ページの表にはプレイガイド（券の販売先）の欄が無い。名前が料金の欄の文に 1 割ほど出るだけ](notes/corich-no-playguide-field.md) が根拠になる |
| [料金の欄から最安〜最高の金額を読み、おすすめの券に出して、上限の金額で絞り込めるようにする](notes/dec-ticket-price-filter.md) | 採用 | 2026-10-14 | ─ | ─ |
| [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) | 提案 | 2026-10-13 | S04, S09 | 影響する → [画面（web/・config.js）](notes/comp-frontend.md)<br>前提にする → [どのドメインをどこで取るか](notes/q-domain.md)<br>[Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が根拠になる<br>[Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) が根拠になる<br>[サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が前提にする<br>[パスキーはドメインに結び付くので、ドメインを変えると使えなくなる](notes/passkey-rpid-domain.md) が根拠になる<br>[Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md) が前提にする |
| [見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md) | 提案 | 2026-10-13 | ─ | 影響する → [たぐりの見た目をどの方向に変えるか（A 幕と半券・B 観劇ノート・C 客電が落ちる）](notes/q-design-direction.md)<br>新たな問いを生む → [好きな作品のポスターから色を取り出して画面を染めるには、何が要るか](notes/q-poster-palette.md)<br>[いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md) が影響する<br>[既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md) が前提にする<br>[見た目の調整室（起案者が色・文字・ボタン・配置・文言を決めて保存し、Claude が読み取って実際の画面に反映する）](notes/design-studio.md) が影響する<br>[好きな作品のポスターから色を取り出して画面を染めるには、何が要るか](notes/q-poster-palette.md) が前提にする<br>[シンプルなデザインは「削る」ことではなく、要るものを一つに絞って際立たせ、押せる手がかりは残すこと](notes/simple-design-principles.md) が影響する |
| [パソコンの見た目の案（左の行き先の帯に 14 項目を組で並べ、本文は 920px 幅、半券にポスターの列）](notes/design-desktop.md) | 提案 | 2026-10-13 | ─ | 前提にする → [いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md) |
| [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md) | 置き換え済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>前提にする → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が食い違う<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が置き換える<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が食い違う<br>[おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が根拠になる<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が根拠になる<br>[Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) が食い違う<br>[別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) が食い違う<br>[Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) が根拠になる |
| [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) | 置き換え済み | 2026-10-13 | ─ | 前提にする → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>[デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) が置き換える<br>[Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) が根拠になる |
| [推薦の改善は、先に測る仕組みを作ってから計算を変える](notes/dec-reco-measure-first.md) | 置き換え済み | 2026-10-13 | ─ | 前提にする → [推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md)<br>根拠になる → [推薦の計算を改善する計画書はあるが、master に入っておらず内容が一部古い](notes/reco-plan-unmerged.md)<br>[推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない](notes/dec-reco-graded.md) が置き換える<br>[推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md) が影響する |
| [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md) | 置き換え済み | 2026-10-13 | ─ | [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) が置き換える<br>[Render の有料プランならスリープせずディスクも付く（単価は二次情報）](notes/render-paid-disk-cost.md) が根拠になる |
| [1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) | 置き換え済み | 2026-10-13 | S12 | 影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>前提にする → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が置き換える<br>[1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) が根拠になる<br>[Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる](notes/workers-paid-plan.md) が根拠になる |
| [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) | 置き換え済み | 2026-10-13 | S02, S13, S22 | 置き換える → [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md)<br>前提にする → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>影響する → [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md)<br>[Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が根拠になる<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が食い違う<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が置き換える<br>[Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) が根拠になる<br>[検証中に自分だけを通す方法（Cloudflare Access の無料枠）](notes/q-cf-access.md) が前提にする<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が根拠になる<br>[Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が根拠になる<br>[Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) が根拠になる<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が根拠になる |

## 調べたこと（151 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [Gmail の読み取りは制限付きの権限で、毎年の第三者の審査が要る](notes/gmail-restricted-scope.md) | 確認済み | 2026-08-28 | ─ | ─ |
| [test_digest と test_impressions は以前から失敗している](notes/legacy-test-failures.md) | 確認済み | 2026-10-12 | ─ | ─ |
| [GitHub Pages は知らない道に 404.html を返し、画面はそれで深い道を開いている](notes/pages-404-fallback.md) | 確認済み | 2026-10-12 | S09 | 影響する → [画面（web/・config.js）](notes/comp-frontend.md) |
| [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) | 確認済み | 2026-10-12 | S20 | 根拠になる → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md)<br>[おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) が置き換える |
| [Python の robotparser は小数の Crawl-delay を読めない](notes/robotparser-decimal-delay.md) | 確認済み | 2026-10-12 | ─ | 影響する → [取得の作法（polite_http.py）](notes/comp-crawler.md) |
| [記録と公演ページの自動の結び付けは、いまは持ち主の手元でしか動かない](notes/auto-link-current-state.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [古い記録を自動で結び付けるための「過去の公演の一覧」を、CoRich のページを読んで作ってよいか](notes/q-auto-link-past.md)<br>影響する → [昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md)<br>[過去の公演の一覧（2019 年以降）を毎日 6,000 枚ずつ作り、記録を自動で結び付ける](notes/dec-auto-link-past.md) が前提にする<br>[古い記録を自動で結び付けるための「過去の公演の一覧」を、CoRich のページを読んで作ってよいか](notes/q-auto-link-past.md) が前提にする |
| [AWS の無料枠は 2025 年 7 月 15 日以降の新しい口座ではクレジット制（最大 200 ドル・6 か月）](notes/aws-free-plan-2025.md) | 確認済み | 2026-10-13 | S12 | 影響する → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md) |
| [AWS は公開 IPv4 アドレス 1 つにつき 1 時間 0.005 ドル（月 3.6 ドルほど）かかる](notes/aws-ipv4-charge.md) | 確認済み | 2026-10-13 | S12 | 影響する → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md) |
| [カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした](notes/catalog-age-check.md) | 確認済み | 2026-10-13 | S23 | 影響する → [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md)<br>影響する → [無料で使える外形監視と通知](notes/q-monitoring.md)<br>[本番の Worker の /api/health は、Render への橋渡しに取られて 404 になっていた（直した）](notes/worker-health-bridged-404.md) が影響する |
| [最初の毎日の Catalog は D1 に入れる段で落ちた。題名の中の U+2028 を splitlines が行の区切りにしたため（直した）](notes/catalog-daily-splitlines.md) | 確認済み | 2026-10-13 | ─ | 影響する → [取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md)<br>影響する → [サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た](notes/sitemap-first-run.md) |
| [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md) | 確認済み | 2026-10-13 | S11 | 新たな問いを生む → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md)<br>[公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md) が影響する<br>[昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md) が前提にする<br>[公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか](notes/q-public-reputation-signal.md) が前提にする |
| [Cloudflare には R2 の使いすぎを止める仕組みが無い。予算の通知（Budget alerts）は知らせるだけ](notes/cf-budget-alerts-not-cap.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md)<br>新たな問いを生む → [起案者のアカウントの設定で、無料枠を越えても請求されないようになっているか](notes/q-free-tier-account-settings.md) |
| [この作業環境からは Cloudflare・Firebase の公式文書や外部サイトが読めない](notes/cf-docs-blocked-here.md) | 確認済み | 2026-10-13 | ─ | ─ |
| [.com の卸値は 2026 年 11 月 1 日から年 10.97 ドルに上がる](notes/com-wholesale-2026.md) | 確認済み | 2026-10-13 | ─ | 影響する → [どのドメインをどこで取るか](notes/q-domain.md) |
| [CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している](notes/corich-robots-sitemap-only.md) | 確認済み | 2026-10-13 | S24 | 影響する → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>置き換える → [取得元の実際の robots.txt はまだ読めていない](notes/corich-robots-unchecked.md)<br>[CoRich のサイトマップから、これからの公演を見つけられるか](notes/q-corich-sitemap.md) が前提にする |
| [CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）](notes/corich-search-waf-403.md) | 確認済み | 2026-10-13 | S24 | 答える → [CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md)<br>影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>[GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む](notes/dec-corich-sitemap.md) が前提にする |
| [CoRich のサイトマップには、すべての公演ページ（/stage/<id>）が更新日つきで載っている](notes/corich-sitemap-stage-ids.md) | 確認済み | 2026-10-13 | S24 | 答える → [CoRich のサイトマップから、これからの公演を見つけられるか](notes/q-corich-sitemap.md)<br>影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>[GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む](notes/dec-corich-sitemap.md) が前提にする |
| [取得の Actions は毎日の更新が 1 回 約 9 分。過去の公演を 1 日 6,000 枚読むと月 3,600 分を越え、無料の 2,000 分に収まらない](notes/crawler-actions-minutes.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md)<br>影響する → [過去の公演の一覧（2019 年以降）を毎日 6,000 枚ずつ作り、記録を自動で結び付ける](notes/dec-auto-link-past.md)<br>影響する → [非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md) |
| [取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）](notes/crawler-state-between-runs.md) | 確認済み | 2026-10-13 | ─ | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が前提にする |
| [Pages と Render は別サイトなので、Cookie が別サイトの扱いになる](notes/cross-origin-cookies.md) | 確認済み | 2026-10-13 | S04 | 根拠になる → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md)<br>新たな問いを生む → [Safari で Cookie が通るか（実機）](notes/q-safari-cookies.md)<br>影響する → [画面（web/・config.js）](notes/comp-frontend.md) |
| [D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md) | 確認済み | 2026-10-13 | S20, S21 | 影響する → [Python Workers の CPU の制限と成熟度](notes/q-d1-python-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[D1 の無料枠は 1 日 10 万行の書き込み・500 万行の読み込み（記憶による数値）](notes/d1-free-write-limit.md) が根拠になる<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が前提にする |
| [D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）](notes/d1-time-travel.md) | 確認済み | 2026-10-13 | S07, S10 | 影響する → [D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md)<br>影響する → [別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) |
| [推薦の計算の細部（数字への直し方・平均か合計か・割り引き・足す人数）はほぼ差が無く、効くのはジャンルの好みと監督の重みを上げること](notes/eval-design-choices.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>根拠になる → [本人のジャンルの好みを足すと、人物だけより当たりが上がり、使うほどの伸びも大きくなる（映画の公開データ）](notes/eval-genre-preference.md)<br>[推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）](notes/impl-person-ordinal-v3.md) が前提にする<br>[評価を等間隔の数ではなく順序として扱う研究（OrdRec）と、少ない件数を割り引く「damping」は推薦の定番](notes/lit-ordinal-damping.md) が根拠になる |
| [作品そのものの評判（他の人の平均）は、人物の手がかりよりずっと強い（AUC 0.79 対 0.57）](notes/eval-douban-consensus-strong.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか](notes/q-public-reputation-signal.md) |
| [公開の映画評価データ（実在の 500 人）では、今の推薦は当てずっぽうに近い（AUC 0.50〜0.53）](notes/eval-douban-current-weak.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>答える → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) |
| [全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる](notes/eval-douban-graded-better.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>根拠になる → [「好み」と「評価の付け方の癖」を分けて扱うと精度が上がり、順位だけを使うと情報を捨てすぎる（Jin・Si・Zhai 2003）](notes/lit-decoupled-rating.md)<br>根拠になる → [低い評価は、とくにデータが少ないときに推薦の役に立つ（Negative ratings play a positive role in information filtering）](notes/lit-negative-ratings.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない](notes/dec-reco-graded.md) が前提にする |
| [答え合わせの問題を固定しても、使うほど当たりは上がる（今の計算で 63%、graded で 74% の人）。ただし水準は低い](notes/eval-douban-learning-curve.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない](notes/dec-reco-graded.md)<br>新たな問いを生む → [公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか](notes/q-public-reputation-signal.md) |
| [役職（出演・監督）の重みを人ごとに学んでも、この条件では良くならなかった](notes/eval-douban-role-learning-no-gain.md) | 確認済み | 2026-10-13 | ─ | 影響する → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) |
| [評価の段階を粗くしても当たりは少し下がるだけで、途中で段階を変えた人は「同じ段階どうしで比べる」のがよい](notes/eval-douban-scales.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [評価の段階は利用者が選べる。初期設定は 5 段階、最小 2 段階・最大 11 段階](notes/dec-user-scale-range.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [お気に入りを仮の評価にすると、評価0件のときだけ当たりが上がる（+0.014〜0.015）。すぐ薄めれば後で下がらない](notes/eval-favourite-seed.md) | 確認済み | 2026-10-13 | ─ | 前提にする → [内容ベースの推薦で、本人の初期の好みを評価が増えるたびに修正する方法がある（Billsus & Pazzani）](notes/lit-syskill-webert-prior.md)<br>前提にする → [持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）](notes/impl-favourite-seed.md) が前提にする |
| [本人のジャンルの好みを足すと、人物だけより当たりが上がり、使うほどの伸びも大きくなる（映画の公開データ）](notes/eval-genre-preference.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>新たな問いを生む → [観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md)<br>[推薦の計算の細部（数字への直し方・平均か合計か・割り引き・足す人数）はほぼ差が無く、効くのはジャンルの好みと監督の重みを上げること](notes/eval-design-choices.md) が根拠になる |
| [組み合わせの重みを公開データの別の人で学んで固定すると少し上がる（+0.006）。人ごとに学び直すのと小さな MLP は効かない](notes/eval-meta-learned-weights.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [利用者ごとの好みを、全体の事前分布から少しずつ個人に寄せる学習は確立した方法（Zhang & Koren 2007）](notes/lit-hierarchical-user-model.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [最初に評価してもらう過去作を、これから並べる候補に多い人物・ジャンルから選ぶと、同じ件数で当たりが上がる（楽観的な条件）](notes/eval-onboarding-selection.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[最初の評価で聞く過去作の一覧を出す API を作った（お気に入りの公演 → 今後の候補を一番多く覆う公演）](notes/impl-onboarding-list.md) が前提にする<br>[登録して最初の 1 回目の評価だけ、これから並ぶ公演に関係する過去作から聞く形にするか（起案者の案）](notes/q-first-rating-onboarding.md) が前提にする |
| [水準を大きく上げたのは「作り手・ジャンルの世間の評判」だけで、それは使っても上がらない](notes/eval-reputation-signals.md) | 確認済み | 2026-10-13 | ─ | 影響する → [公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか](notes/q-public-reputation-signal.md) |
| [◎○△× の 4 段階が適切だという直接の証拠は無い（「残す」は手間と既存の評価を理由にした判断）](notes/four-level-unsupported.md) | 確認済み | 2026-10-13 | ─ | 影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) |
| [LLM の呼び出しには月の上限がある（既定 300 回）](notes/gemini-budget-cap.md) | 確認済み | 2026-10-13 | S27 | 影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) | 確認済み | 2026-10-13 | S24 | 影響する → [取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md)<br>新たな問いを生む → [CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md)<br>影響する → [取得はすべて polite_http を通す](notes/dec-polite-crawling.md)<br>[CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md) が前提にする |
| [Actions の無料の分は毎月 0 に戻り、月払いの支払いの上限は既定で 0 ドル（越えると止まる）](notes/gha-minutes-reset-budget.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md)<br>根拠になる → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md)<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が前提にする |
| [非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md) | 確認済み | 2026-10-13 | S12 | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>[取得の Actions は毎日の更新が 1 回 約 9 分。過去の公演を 1 日 6,000 枚読むと月 3,600 分を越え、無料の 2,000 分に収まらない](notes/crawler-actions-minutes.md) が影響する<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が前提にする<br>[Actions の無料の分は毎月 0 に戻り、月払いの支払いの上限は既定で 0 ドル（越えると止まる）](notes/gha-minutes-reset-budget.md) が根拠になる |
| [この作業環境の GitHub 連携では、新しいリポジトリを作れない](notes/gha-repo-create-forbidden.md) | 確認済み | 2026-10-13 | ─ | 影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>新たな問いを生む → [取得処理用の非公開リポジトリ（taguri-crawler）と、その秘密の設定](notes/q-crawler-repo.md) |
| [実行中の GitHub Actions のジョブのログは API で取れない（404）。進み具合は手順の状態でしか見えない](notes/gha-running-job-logs-404.md) | 確認済み | 2026-10-13 | ─ | 影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) |
| [公開リポジトリでは GitHub Actions の標準の実行環境が無料。ただし 60 日動きが無いと定期実行が止まる](notes/github-actions-public-free.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) |
| [評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）](notes/impl-favourite-seed.md) | 確認済み | 2026-10-13 | ─ | 答える → [最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md)<br>前提にする → [お気に入りを仮の評価にすると、評価0件のときだけ当たりが上がる（+0.014〜0.015）。すぐ薄めれば後で下がらない](notes/eval-favourite-seed.md)<br>前提にする → [推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）](notes/impl-person-ordinal-v3.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[最初の評価で聞く過去作の一覧を出す API を作った（お気に入りの公演 → 今後の候補を一番多く覆う公演）](notes/impl-onboarding-list.md) が前提にする |
| [裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md) | 確認済み | 2026-10-13 | ─ | 答える → [新しい要素を安全に入れる「裏の答え合わせ」をどう作るか（起案者が良いと判断）](notes/q-hidden-gate.md)<br>前提にする → [推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）](notes/impl-person-ordinal-v3.md)<br>前提にする → [届いた順に「予想してから答え合わせ」する評価（prequential）は、変わり続ける推薦の評価に使われている（Vinagre ほか 2014）](notes/lit-prequential.md)<br>前提にする → [新しい方式は「前より悪くないと高い確信で言えるときだけ」採る、という考え方がある（Thomas ほか 2015）](notes/lit-safe-improvement.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[裏の答え合わせは「組を数える」「前の作品と比べる」とでたらめな人でも切り替わる。区切りごとに数えると誤りは 3% 以下](notes/eval-hidden-gate-sim.md) が根拠になる<br>[評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md) が前提にする |
| [最初の評価で聞く過去作の一覧を出す API を作った（お気に入りの公演 → 今後の候補を一番多く覆う公演）](notes/impl-onboarding-list.md) | 確認済み | 2026-10-13 | ─ | 答える → [登録して最初の 1 回目の評価だけ、これから並ぶ公演に関係する過去作から聞く形にするか（起案者の案）](notes/q-first-rating-onboarding.md)<br>前提にする → [最初に評価してもらう過去作を、これから並べる候補に多い人物・ジャンルから選ぶと、同じ件数で当たりが上がる（楽観的な条件）](notes/eval-onboarding-selection.md)<br>前提にする → [評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）](notes/impl-favourite-seed.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [推薦の計算を person-graded-v2 に変えた（Python 版と Worker 版の両方、同じ結果になることをテストで確認）](notes/impl-person-graded-v2.md) | 確認済み | 2026-10-13 | ─ | 前提にする → [推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない](notes/dec-reco-graded.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）](notes/impl-person-ordinal-v3.md) | 確認済み | 2026-10-13 | ─ | 前提にする → [推薦の計算の細部（数字への直し方・平均か合計か・割り引き・足す人数）はほぼ差が無く、効くのはジャンルの好みと監督の重みを上げること](notes/eval-design-choices.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>答える → [観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md)<br>[評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）](notes/impl-favourite-seed.md) が前提にする<br>[裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md) が前提にする |
| [評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md) | 確認済み | 2026-10-13 | ─ | 答える → [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md)<br>前提にする → [評価の詳細は任意で隠しておき、項目ごとに「良かった／気になった」を付けられる。詳しく記録するか、あっさり付けるかは人が選ぶ](notes/dec-rating-detail-mode.md)<br>前提にする → [舞台の仕事の分担：演出家が作品全体の芸術面の責任者で、舞台監督は現場の進行、制作・プロデューサーは予算と運営（値段を決める側）](notes/stage-roles.md)<br>前提にする → [観劇の評価は内容だけでなく、値段に見合うか・構成・演出などが混ざって 1 つの記号になる](notes/rating-mixes-aspects.md)<br>前提にする → [裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[評価の詳細は任意で隠しておき、項目ごとに「良かった／気になった」を付けられる。詳しく記録するか、あっさり付けるかは人が選ぶ](notes/dec-rating-detail-mode.md) が影響する<br>[作ったデータでは、気になった所を仮定どおりに付ける人には効き、でたらめに付ける人には害があり、裏の答え合わせはその害をあまり拾えない](notes/eval-aspects-sim.md) が影響する |
| [当てる精度だけを上げると、役に立つ推薦から外れることがある（McNee ほか 2006・Ferrari Dacrema ほか 2019）](notes/lit-beyond-accuracy.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) |
| [順位を直接学ぶ「組で比べる」学習（BPR）は、AUC を最大にするのと同じ形（Rendle ほか 2009）](notes/lit-bpr-pairwise.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) |
| [「好み」と「評価の付け方の癖」を分けて扱うと精度が上がり、順位だけを使うと情報を捨てすぎる（Jin・Si・Zhai 2003）](notes/lit-decoupled-rating.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>食い違う → [今の計算は「その人の◎の割合」を差し引くので、◎が珍しい人の◎ほど強く効き、◎ばかりの人の◎はほとんど効かない](notes/reco-base-rate-relative.md)<br>[全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる](notes/eval-douban-graded-better.md) が根拠になる |
| [推薦が利用者の行動を変え、その行動で次の推薦を学ぶ「輪」で、推薦は偏りやすくなる（Chaney・Stewart・Engelhardt 2018）](notes/lit-feedback-loop.md) | 確認済み | 2026-10-13 | ─ | 影響する → [最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md)<br>根拠になる → [評価が付いていないこと自体が情報になり、付いた評価だけで学ぶ・測ると偏る（Steck 2010）](notes/lit-mnar.md) |
| [利用者ごとの好みを、全体の事前分布から少しずつ個人に寄せる学習は確立した方法（Zhang & Koren 2007）](notes/lit-hierarchical-user-model.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md)<br>食い違う → [推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md)<br>[組み合わせの重みを公開データの別の人で学んで固定すると少し上がる（+0.006）。人ごとに学び直すのと小さな MLP は効かない](notes/eval-meta-learned-weights.md) が根拠になる |
| [観る前の反応（興味あり・購入）は「好みの信号」だが確からしさが違うので、重みを変えて扱う（Hu・Koren・Volinsky 2008）](notes/lit-implicit-confidence.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) |
| [評価が付いていないこと自体が情報になり、付いた評価だけで学ぶ・測ると偏る（Steck 2010）](notes/lit-mnar.md) | 確認済み | 2026-10-13 | ─ | 食い違う → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md)<br>[推薦が利用者の行動を変え、その行動で次の推薦を学ぶ「輪」で、推薦は偏りやすくなる（Chaney・Stewart・Engelhardt 2018）](notes/lit-feedback-loop.md) が根拠になる |
| [総合評価に加えて観点ごとの評価を使う推薦（多基準推薦）は、1 つの評価だけより精度が上がったと報告されている（Adomavicius & Kwon 2007 ほか）](notes/lit-multi-criteria.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md)<br>[評価の詳細は任意で隠しておき、項目ごとに「良かった／気になった」を付けられる。詳しく記録するか、あっさり付けるかは人が選ぶ](notes/dec-rating-detail-mode.md) が前提にする |
| [届いた順に「予想してから答え合わせ」する評価（prequential）は、変わり続ける推薦の評価に使われている（Vinagre ほか 2014）](notes/lit-prequential.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md)<br>[裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md) が前提にする |
| [「値段に見合うか（知覚価値）」は品質と支払う犠牲の釣り合いで決まり、推薦でも価格を別に扱う研究がある（Zeithaml 1988・Zheng ほか 2020）](notes/lit-price-value.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md) |
| [評価の段階は「付ける手間」と「推薦に使える情報量」の引き換えで、粗い段階は速いが情報が少ない（Sparling & Sen 2011・Kluver ほか 2012）](notes/lit-rating-scale-granularity.md) | 確認済み | 2026-10-13 | ─ | 影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) |
| [評価の付け方の癖は文化や個人で違い、日本や中国の回答者は真ん中を選びやすく、米国は端を選びやすい（Chen・Lee・Stevenson 1995、Harzing 2006）](notes/lit-response-style-culture.md) | 確認済み | 2026-10-13 | ─ | 影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) |
| [新しい方式は「前より悪くないと高い確信で言えるときだけ」採る、という考え方がある（Thomas ほか 2015）](notes/lit-safe-improvement.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md)<br>[裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md) が前提にする |
| [評価の段階を途中で変えたときの扱い：直接の研究は少なく、段階どうしを決まった式で写すのは最善ではないとされる](notes/lit-scale-change.md) | 確認済み | 2026-10-13 | ─ | 影響する → [評価の段階を利用者自身に選んでもらうか（起案者の案）](notes/q-user-chosen-scale.md) |
| [評価の段階数の研究では 2〜4 段階は信頼性・妥当性が低く、7 段階前後がよいとされる。ただし多ければ良いとも限らない](notes/lit-scale-points.md) | 確認済み | 2026-10-13 | ─ | 食い違う → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) |
| [内容ベースの推薦で、本人の初期の好みを評価が増えるたびに修正する方法がある（Billsus & Pazzani）](notes/lit-syskill-webert-prior.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md)<br>[お気に入りを仮の評価にすると、評価0件のときだけ当たりが上がる（+0.014〜0.015）。すぐ薄めれば後で下がらない](notes/eval-favourite-seed.md) が前提にする<br>[最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md) が前提にする |
| [利用者に評価の段階を選ばせる案は研究で提案されており、選ばれる段階は評価する物や経験で変わる（Cena・Vernero ほか）](notes/lit-user-chosen-scale.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [評価の段階を利用者自身に選んでもらうか（起案者の案）](notes/q-user-chosen-scale.md) |
| [Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) | 確認済み | 2026-10-13 | ─ | 影響する → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>新たな問いを生む → [画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md)<br>新たな問いを生む → [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md)<br>[画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) が影響する<br>[段 1 の作りかけを受け取った。読み込めない原因は py.js の正規表現に入った生の行区切り文字だった](notes/migration-wip-received.md) が影響する<br>[移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md) が影響する |
| [段 1（記録と評価）の画面 4 枚と書き込み 11 種が、Python と同じ応答を返すようになった](notes/migration-stage1-parity.md) | 確認済み | 2026-10-13 | S34 | 影響する → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>前提にする → [画面の移行は wip-screens-port で進め、段ごとに試験が通ってから master に入れる](notes/dec-migration-branch-wip.md)<br>[評価の画面に「気になった所」（任意・複数選択）のボタンを付けるか](notes/q-aspects-ui.md) が影響する |
| [段 1 の作りかけを受け取った。読み込めない原因は py.js の正規表現に入った生の行区切り文字だった](notes/migration-wip-received.md) | 確認済み | 2026-10-13 | ─ | 答える → [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md)<br>影響する → [Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) |
| [日記帳などを Worker の画面に切り替えるための今の状態（NATIVE_UI）](notes/native-cutover-map.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [Worker の画面への切り替えを、日記帳など 4 画面だけ先にするか、全画面がそろってから一度にするか](notes/q-native-cutover.md)<br>[Worker の画面への切り替えを、日記帳など 4 画面だけ先にするか、全画面がそろってから一度にするか](notes/q-native-cutover.md) が前提にする |
| [AWS はもう使っていない](notes/no-aws.md) | 確認済み | 2026-10-13 | ─ | 影響する → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>新たな問いを生む → [Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md)<br>新たな問いを生む → [取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md)<br>影響する → [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md)<br>[取得したカタログを Cloudflare 版（D1）にどう届けるか](notes/q-catalog-to-worker.md) が前提にする<br>[Render のデモ版は、起動し直すと動かなくなるのではないか](notes/q-render-s3-dependency.md) が前提にする |
| [EC2 は無い](notes/no-ec2.md) | 確認済み | 2026-10-13 | S23 | 答える → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>新たな問いを生む → [今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md)<br>影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>影響する → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>影響する → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md) |
| [商用でも無料の日本語書体（SIL OFL）と、自分のサイトで配るときの重さ](notes/ofl-japanese-fonts.md) | 確認済み | 2026-10-13 | ─ | 答える → [調整室で選んだ書体（Zen Old Mincho など）を、外部から読み込まずに全員の画面で出すには](notes/q-webfont-local.md)<br>[題字の書体の候補（明朝と本文ゴシックの間）── どれも SIL OFL](notes/title-font-candidates.md) が根拠になる |
| [Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) | 確認済み | 2026-10-13 | S12, S29 | 答える → [Oracle の公式の無料枠と回収の条件](notes/q-oracle-official.md)<br>新たな問いを生む → [Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか](notes/q-oracle-payg.md)<br>根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md) |
| [パスキーはドメインに結び付くので、ドメインを変えると使えなくなる](notes/passkey-rpid-domain.md) | 確認済み | 2026-10-13 | S04 | 影響する → [どのドメインをどこで取るか](notes/q-domain.md)<br>根拠になる → [独自ドメインを取り、画面と API を同じドメインの下に置く](notes/dec-own-domain.md) |
| [本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md) | 確認済み | 2026-10-13 | S33 | 答える → [本番に deploy するブランチをどれにするか（PR のブランチのままにしない）](notes/q-production-branch.md)<br>置き換える → [本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている](notes/pr-branch-is-production.md)<br>影響する → [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md)<br>[画面の移行は wip-screens-port で進め、段ごとに試験が通ってから master に入れる](notes/dec-migration-branch-wip.md) が前提にする |
| [公開版の書き出しが他の利用者の記録まで渡していた（修正済み）](notes/public-export-leak.md) | 確認済み | 2026-10-13 | S03 | 影響する → [本人の書き出し（/export.json・/data.zip）](notes/comp-export.md) |
| [Python の画面は一時保存先・固定日付・通信なしで、テストの中から動かせる](notes/python-screens-harness.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) |
| [別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている](notes/python-workers-migration-state.md) | 確認済み | 2026-10-13 | ─ | 影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>新たな問いを生む → [Python Workers の CPU の制限と成熟度](notes/q-d1-python-workers.md) |
| [R2 の無料枠は保存 10 GB・Class A 月 100 万回・Class B 月 1,000 万回で、越えた分は請求される（取り出しの通信料は無料）](notes/r2-free-tier-billed.md) | 確認済み | 2026-10-13 | ─ | 検証項目 → [R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md)<br>根拠になる → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md)<br>影響する → [ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す](notes/dec-posters-r2.md)<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が前提にする |
| [観劇の評価は内容だけでなく、値段に見合うか・構成・演出などが混ざって 1 つの記号になる](notes/rating-mixes-aspects.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md) が前提にする |
| [今の推薦（person-feedback-v1）の精度は、公開版の利用者では測っていない](notes/reco-accuracy-unverified.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>新たな問いを生む → [推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md) |
| [今の計算は「その人の◎の割合」を差し引くので、◎が珍しい人の◎ほど強く効き、◎ばかりの人の◎はほとんど効かない](notes/reco-base-rate-relative.md) | 確認済み | 2026-10-13 | ─ | 影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[「好み」と「評価の付け方の癖」を分けて扱うと精度が上がり、順位だけを使うと情報を捨てすぎる（Jin・Si・Zhai 2003）](notes/lit-decoupled-rating.md) が食い違う |
| [推薦の良し悪しを測る仕組みが足りない（利用者ごとの時系列評価・正解データ・提示と結果の結び付け）](notes/reco-eval-gaps.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md) |
| [Worker の推薦は Python（person-feedback-v1）と同じ結果を出す](notes/reco-js-parity.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) が前提にする |
| [推薦の計算を改善する計画書はあるが、master に入っておらず内容が一部古い](notes/reco-plan-unmerged.md) | 確認済み | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>新たな問いを生む → [推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md)<br>[推薦の改善は、先に測る仕組みを作ってから計算を変える](notes/dec-reco-measure-first.md) が根拠になる |
| [推薦の計算 person-graded-v2 は、D1 の索引の作り（表と行）を変えない](notes/reco-v2-index-compatible.md) | 確認済み | 2026-10-13 | ─ | 影響する → [取得処理のあとに、変わった公演の行だけを wrangler で本番の D1 に入れる](notes/dec-d1-catalogue-delivery.md)<br>[評価の画面に「気になった所」（任意・複数選択）のボタンを付けるか](notes/q-aspects-ui.md) が前提にする |
| [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) | 確認済み | 2026-10-13 | S02 | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>答える → [Render の無料プランでサービス版を動かせるか](notes/q-render-free-viable.md)<br>影響する → [利用者の保存先とバックアップ](notes/comp-state-storage.md)<br>[Render の他人の記録も、持ち主の EC2 の記録も、新しいアカウントには移さない](notes/dec-no-render-data-migration.md) が前提にする |
| [Render の無料プランは 15 分でスリープし、起動に約 1 分かかる](notes/render-free-spin-down.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>根拠になる → [デモ版は Render の無料プランのまま残す](notes/dec-demo-stays-render-free.md) |
| [Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている](notes/render-two-identities.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>根拠になる → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) |
| [元の画面は Python が HTML を組んで JSON で返している（約 2.5 万行）](notes/render-ui-server-rendered.md) | 確認済み | 2026-10-13 | ─ | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が前提にする |
| [サービス版の保存先の検査が Render を前提にしている](notes/serve-cloud-render-guard.md) | 確認済み | 2026-10-13 | S02 | 影響する → [公開版のサーバー（serve_cloud.py・serve.py）](notes/comp-public-server.md)<br>影響する → [サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) |
| [サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た](notes/sitemap-first-run.md) | 確認済み | 2026-10-13 | ─ | 検証項目 → [GitHub Actions では CoRich の検索を使わず、サイトマップで新しい公演を見つけて公演ページを読む](notes/dec-corich-sitemap.md)<br>影響する → [Worker の /api/catalogue は 1,000 件までしか返さない。これからの公演がそれより多いときどうするか](notes/q-catalogue-api-limit.md)<br>新たな問いを生む → [取得の作業データ（state ブランチ）が 2 GB になった。ポスターと公演ページの HTML の控えをどうするか](notes/q-crawler-state-size.md)<br>[最初の毎日の Catalog は D1 に入れる段で落ちた。題名の中の U+2028 を splitlines が行の区切りにしたため（直した）](notes/catalog-daily-splitlines.md) が影響する<br>[取得の作業データ（state ブランチ）が 2 GB になった。ポスターと公演ページの HTML の控えをどうするか](notes/q-crawler-state-size.md) が前提にする |
| [サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) |
| [あらすじの読み取りは Gemini API。以前の claude CLI 呼び出しは起案者の判断でやめている](notes/synopsis-llm-history.md) | 確認済み | 2026-10-13 | ─ | 影響する → [あらすじの読み取りを誰が担うか（Claude の定期実行・Gemini API・当面読まない）](notes/q-synopsis-reader.md)<br>[公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md) が前提にする<br>[あらすじの読み取りを誰が担うか（Claude の定期実行・Gemini API・当面読まない）](notes/q-synopsis-reader.md) が前提にする |
| [試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) | 確認済み | 2026-10-13 | S13 | 影響する → [登録・復旧の試行回数の制限（auth.py）](notes/comp-auth-throttle.md)<br>新たな問いを生む → [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) |
| [題字の書体の候補（明朝と本文ゴシックの間）── どれも SIL OFL](notes/title-font-candidates.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [商用でも無料の日本語書体（SIL OFL）と、自分のサイトで配るときの重さ](notes/ofl-japanese-fonts.md)<br>影響する → [いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md)<br>[スマホの見出し ── 4 つの大メニューを均等割りで常に出し、子メニューはすだれで出す](notes/dec-phone-nav-four.md) が前提にする |
| [題名の正規化（title_key）は JS でも Python と同じにできる](notes/title-key-parity.md) | 確認済み | 2026-10-13 | ─ | ─ |
| [画面の△の説明「あまり合わなかった」は、起案者の考える△（まあ良いが気になる所がある）と食い違う](notes/triangle-label-mismatch.md) | 確認済み | 2026-10-13 | ─ | 新たな問いを生む → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) が前提にする |
| [本番の Worker の /api/health は、Render への橋渡しに取られて 404 になっていた（直した）](notes/worker-health-bridged-404.md) | 確認済み | 2026-10-13 | ─ | 影響する → [カタログの日付は、公開の /api/health と毎日の GitHub Actions で確かめられるようにした](notes/catalog-age-check.md)<br>根拠になる → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) |
| [push するたびに Workers Builds が D1 の migration を当ててから deploy する](notes/workers-builds-applies-migrations.md) | 確認済み | 2026-10-13 | ─ | 影響する → [Cloudflare D1（taguri-demo データベース）](notes/comp-d1.md) |
| [Workers Builds（GitHub からの自動配信）は無料プランで月 3,000 分・同時 1 本・1 回 20 分まで](notes/workers-builds-free-3000.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) |
| [コミットの ✗ は Workers Builds が cloudflare/ の無い master を組もうとして失敗していたため](notes/workers-builds-master-fail.md) | 確認済み | 2026-10-13 | ─ | 影響する → [Cloudflare Worker（cloudflare/src/worker.js）](notes/comp-cf-worker.md) |
| [Workers の Cache API は *.workers.dev では何もしない（独自ドメインでだけ効く）](notes/workers-cache-api-workers-dev.md) | 確認済み | 2026-10-13 | ─ | 影響する → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) |
| [Workers の定期実行は、無料プランだと 1 回あたり CPU 10 ミリ秒・外部への要求 50 回まで](notes/workers-cron-free-limits.md) | 確認済み | 2026-10-13 | S23 | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) |
| [別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) | 確認済み | 2026-10-13 | S10, S20 | 食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[D1 は無料プランで 7 日前、有料プランで 30 日前まで戻せる（Time Travel）](notes/d1-time-travel.md) が影響する |
| [Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) | 確認済み | 2026-10-13 | ─ | 根拠になる → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>答える → [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md)<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が前提にする<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が前提にする<br>[移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか](notes/q-workers-cpu-real.md) が前提にする |
| [Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる](notes/workers-paid-plan.md) | 確認済み | 2026-10-13 | S12 | 根拠になる → [1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) |
| [Workers の静的ファイルへの要求は無料・無制限で、要求数の上限に数えない](notes/workers-static-assets-free.md) | 確認済み | 2026-10-13 | S20 | 影響する → [1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) |
| [CoRich の公演ページの表にはプレイガイド（券の販売先）の欄が無い。名前が料金の欄の文に 1 割ほど出るだけ](notes/corich-no-playguide-field.md) | 確認済み | 2026-10-14 | ─ | 根拠になる → [おすすめの券の見直し（2026-10-14 の 10 項目）── 回答の帯は右寄せ・興味なしはグレー・書き込み中・説明はインフォへ・もう追いかけない束をやめる・名前の札・絵記号・期間の表記・ツアーの日程・発売の札から券の案内へ](notes/dec-recommend-ui-1014.md)<br>[おすすめの券の見直し（2026-10-14 の 10 項目）── 回答の帯は右寄せ・興味なしはグレー・書き込み中・説明はインフォへ・もう追いかけない束をやめる・名前の札・絵記号・期間の表記・ツアーの日程・発売の札から券の案内へ](notes/dec-recommend-ui-1014.md) が前提にする |
| [Worker の推薦でもツアー公演を 1 枠にまとめ、ほかの会場を付けて出すようにした（+tour1）](notes/impl-tour-slots.md) | 確認済み | 2026-10-14 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
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
| [作ったデータでは、気になった所を仮定どおりに付ける人には効き、でたらめに付ける人には害があり、裏の答え合わせはその害をあまり拾えない](notes/eval-aspects-sim.md) | 未確認 | 2026-10-13 | ─ | 影響する → [評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md)<br>前提にする → [観点（値段・脚本・演出など）ごとに下げる相手を変える案を、どう確かめるか](notes/q-aspect-attribution-check.md)<br>前提にする → [持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md) |
| [裏の答え合わせは「組を数える」「前の作品と比べる」とでたらめな人でも切り替わる。区切りごとに数えると誤りは 3% 以下](notes/eval-hidden-gate-sim.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md)<br>前提にする → [持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md) |
| [Firebase の Web 用 API キーは秘密ではない（使える範囲は承認済みドメインとキーの制限で絞る）](notes/firebase-apikey-public.md) | 未確認 | 2026-10-13 | ─ | 新たな問いを生む → [Firebase の API キーに制限（Web サイト・使う API）を掛けたか](notes/q-firebase-key-restriction.md) |
| [舞台のジャンル分けは、チケット販売サイト・業界の白書・助成制度・演劇史の区分がそれぞれ独自に持っていて、共通の公式の分け方は無い](notes/genre-schemes-found.md) | 未確認 | 2026-10-13 | ─ | 影響する → [観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md) |
| [公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md) | 未確認 | 2026-10-13 | ─ | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md)<br>影響する → [利用規約は公演情報を第三者へ再配布しないと約束している](notes/catalog-terms-no-redistribution.md)<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が前提にする |
| [GitHub Actions の定期実行は遅れたり、混雑時に飛ばされたりする](notes/gha-schedule-unreliable.md) | 未確認 | 2026-10-13 | S23 | 影響する → [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) |
| [.jp は年 4,000 円前後（税の扱い・年額かは未確認）](notes/jp-domain-price.md) | 未確認 | 2026-10-13 | ─ | 影響する → [どのドメインをどこで取るか](notes/q-domain.md) |
| [評定（◎○△×）の分布は、0 を中心に左右へ分ける積み上げ棒がよい ── 可視化の論文から](notes/likert-diverging-bars.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [評価の分布を発散型の帯にし、判子から評価を選び直す。＋は登録の 3 つの入口を開く](notes/dec-verdict-diverging.md)<br>[評価の分布を発散型の帯にし、判子から評価を選び直す。＋は登録の 3 つの入口を開く](notes/dec-verdict-diverging.md) が前提にする |
| [新作向けの深層学習の推薦（DropoutNet・CB2CF・two-tower・言語モデル）は、対象分野の協調データか外部への送信が要り、たぐりの方針にそのままは合わない](notes/lit-cold-start-dl.md) | 未確認 | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) |
| [選べるようにしても、多くの人は最初に決められた選択肢のままにする（既定の効果、Johnson & Goldstein 2003）](notes/lit-default-effect.md) | 未確認 | 2026-10-13 | ─ | 影響する → [評価の段階を利用者自身に選んでもらうか（起案者の案）](notes/q-user-chosen-scale.md) |
| [映画のジャンルを使った推薦の研究は、主に「新しい利用者・新作の立ち上がり」のために使われている](notes/lit-genre-reco.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md)<br>根拠になる → [最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md) |
| [低い評価は、とくにデータが少ないときに推薦の役に立つ（Negative ratings play a positive role in information filtering）](notes/lit-negative-ratings.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>[全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる](notes/eval-douban-graded-better.md) が根拠になる |
| [評価を等間隔の数ではなく順序として扱う研究（OrdRec）と、少ない件数を割り引く「damping」は推薦の定番](notes/lit-ordinal-damping.md) | 未確認 | 2026-10-13 | ─ | 影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>根拠になる → [推薦の計算の細部（数字への直し方・平均か合計か・割り引き・足す人数）はほぼ差が無く、効くのはジャンルの好みと監督の重みを上げること](notes/eval-design-choices.md) |
| [舞台芸術の推薦の先行例は少なく、主に劇場側の販売データでの協調フィルタリング](notes/lit-performing-arts.md) | 未確認 | 2026-10-13 | ─ | 影響する → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) |
| [同じ人が同じ作品を付け直しても評価はぶれる（Amatriain ほか 2009）](notes/lit-rating-noise.md) | 未確認 | 2026-10-13 | ─ | 影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) |
| [推薦では、利用者ごとの評価の甘さ辛さ（user bias）を差し引いて扱うのが定番（Koren 2008 ほか）](notes/lit-user-bias.md) | 未確認 | 2026-10-13 | ─ | 影響する → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md) |
| [観点ごとの評価がある公開データ（Yahoo! Movies：物語・演技・演出・映像＋総合）が研究で使われている](notes/lit-yahoo-multicriteria.md) | 未確認 | 2026-10-13 | ─ | 影響する → [観点（値段・脚本・演出など）ごとに下げる相手を変える案を、どう確かめるか](notes/q-aspect-attribution-check.md) |
| [R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>新たな問いを生む → [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md)<br>影響する → [公演カタログの取得と配布（publish_catalog.py）](notes/comp-catalog-pipeline.md)<br>[R2 の無料枠は保存 10 GB・Class A 月 100 万回・Class B 月 1,000 万回で、越えた分は請求される（取り出しの通信料は無料）](notes/r2-free-tier-billed.md) が検証項目 |
| [過去の改善の実験結果（持ち主 1 人の評価での AUC）は、判断の根拠に使わない](notes/reco-past-auc.md) | 未確認 | 2026-10-13 | ─ | 影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md) が影響する |
| [Render の有料プランならスリープせずディスクも付く（単価は二次情報）](notes/render-paid-disk-cost.md) | 未確認 | 2026-10-13 | ─ | 根拠になる → [サービス版を Render の有料サービスで立てる](notes/dec-render-service-beta.md) |
| [1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) | 未確認 | 2026-10-13 | S20, S21 | 根拠になる → [1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>[D1 の無料プランは 1 つのデータベースが 500MB まで（二次情報）](notes/d1-free-db-size.md) が影響する<br>[Workers の静的ファイルへの要求は無料・無制限で、要求数の上限に数えない](notes/workers-static-assets-free.md) が影響する |
| [シンプルなデザインは「削る」ことではなく、要るものを一つに絞って際立たせ、押せる手がかりは残すこと](notes/simple-design-principles.md) | 未確認 | 2026-10-13 | ─ | 影響する → [見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md)<br>[既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md) が前提にする |
| [舞台の仕事の分担：演出家が作品全体の芸術面の責任者で、舞台監督は現場の進行、制作・プロデューサーは予算と運営（値段を決める側）](notes/stage-roles.md) | 未確認 | 2026-10-13 | ─ | 影響する → [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md)<br>[評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md) が前提にする |
| [バックアップの検査が Python 3.13 では 1 件失敗する](notes/state-backup-py313.md) | 未確認 | 2026-10-13 | ─ | 新たな問いを生む → [サーバーの Python を何版に揃えるか](notes/q-python-version.md)<br>影響する → [利用者の保存先とバックアップ](notes/comp-state-storage.md) |
| [舞台の公演に業界共通の公式のジャンル分けは見つからない。近いものは日本劇作家協会「戯曲デジタルアーカイブ」のジャンル（戯曲向け）](notes/theatre-genre-sources.md) | 未確認 | 2026-10-13 | ─ | 影響する → [観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md) |
| [持ち主の過去の検証では、あらすじのテーマ語は作品間で重なりにくく、一般的な語（家族・恋愛・コメディ・友情）に偏っていた](notes/theme-words-sparse-past.md) | 未確認 | 2026-10-13 | ─ | 影響する → [観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md) |
| [note・Notion のような白基調の記録サイトの見た目（白い紙面・真っ黒でない文字・差し色 1 つ・広い余白）](notes/white-record-sites.md) | 未確認 | 2026-10-13 | ─ | 影響する → [既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md) |
| [Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) | 未確認 | 2026-10-13 | S20 | 食い違う → [Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md)<br>新たな問いを生む → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>影響する → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) |
| [起案者が Cloudflare の Budget alerts を作り、Workers の Free を確かめた。GitHub には支払い方法を登録していない](notes/free-tier-account-settings-done.md) | 未確認 | 2026-10-14 | ─ | 答える → [起案者のアカウントの設定で、無料枠を越えても請求されないようになっているか](notes/q-free-tier-account-settings.md)<br>根拠になる → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) |

## 仕組みの部品（16 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [取得の作法（polite_http.py）](notes/comp-crawler.md) | 現行 | 2026-10-12 | ─ | [取得はすべて polite_http を通す](notes/dec-polite-crawling.md) が影響する<br>[Python の robotparser は小数の Crawl-delay を読めない](notes/robotparser-decimal-delay.md) が影響する |
| [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md) | 現行 | 2026-10-12 | ─ | [推薦の索引の作成（build_recommend_index.py）](notes/comp-rec-index.md) が影響する<br>[Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md) が影響する<br>[持ち主 1 人（n=1）の実験結果は、推薦の改善の根拠にしない](notes/dec-no-n1-evidence.md) が影響する<br>[評価の詳細は任意で隠しておき、項目ごとに「良かった／気になった」を付けられる。詳しく記録するか、あっさり付けるかは人が選ぶ](notes/dec-rating-detail-mode.md) が影響する<br>[推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない](notes/dec-reco-graded.md) が影響する<br>[おすすめ（人物得点）は索引をバッチで作り、Worker で計算する](notes/dec-reco-on-worker.md) が影響する<br>[推薦の改善は、利用者ごとに「その人にとって良くなったか」だけを確かめる（記録を集めない）](notes/dec-reco-per-user-eval.md) が影響する<br>[評価の段階は利用者が選べる。初期設定は 5 段階、最小 2 段階・最大 11 段階](notes/dec-user-scale-range.md) が影響する<br>[見本の記録のうち推薦の材料になるのは 6 割ほど（見積もり）](notes/demo-seed-link-rate.md) が影響する<br>[推薦の計算の細部（数字への直し方・平均か合計か・割り引き・足す人数）はほぼ差が無く、効くのはジャンルの好みと監督の重みを上げること](notes/eval-design-choices.md) が影響する<br>[公開の映画評価データ（実在の 500 人）では、今の推薦は当てずっぽうに近い（AUC 0.50〜0.53）](notes/eval-douban-current-weak.md) が影響する<br>[全部の段階をその人基準（いつもより高いか低いか）で使うと、62〜82% の人で今の推薦より良く、使うほど差が広がる](notes/eval-douban-graded-better.md) が影響する<br>[評価の段階を粗くしても当たりは少し下がるだけで、途中で段階を変えた人は「同じ段階どうしで比べる」のがよい](notes/eval-douban-scales.md) が影響する<br>[お気に入りを仮の評価にすると、評価0件のときだけ当たりが上がる（+0.014〜0.015）。すぐ薄めれば後で下がらない](notes/eval-favourite-seed.md) が影響する<br>[本人のジャンルの好みを足すと、人物だけより当たりが上がり、使うほどの伸びも大きくなる（映画の公開データ）](notes/eval-genre-preference.md) が影響する<br>[組み合わせの重みを公開データの別の人で学んで固定すると少し上がる（+0.006）。人ごとに学び直すのと小さな MLP は効かない](notes/eval-meta-learned-weights.md) が影響する<br>[最初に評価してもらう過去作を、これから並べる候補に多い人物・ジャンルから選ぶと、同じ件数で当たりが上がる（楽観的な条件）](notes/eval-onboarding-selection.md) が影響する<br>[評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）](notes/impl-favourite-seed.md) が影響する<br>[裏の答え合わせを Worker に入れた（本人の記録を時間順に再生して、別の計算が確かに勝ったときだけ使う）](notes/impl-hidden-gate.md) が影響する<br>[最初の評価で聞く過去作の一覧を出す API を作った（お気に入りの公演 → 今後の候補を一番多く覆う公演）](notes/impl-onboarding-list.md) が影響する<br>[推薦の計算を person-graded-v2 に変えた（Python 版と Worker 版の両方、同じ結果になることをテストで確認）](notes/impl-person-graded-v2.md) が影響する<br>[推薦の計算を person-ordinal-v3 に変えた（評価を順序として読み、公演の種類の好みを足す）](notes/impl-person-ordinal-v3.md) が影響する<br>[評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md) が影響する<br>[Worker の推薦でもツアー公演を 1 枠にまとめ、ほかの会場を付けて出すようにした（+tour1）](notes/impl-tour-slots.md) が影響する<br>[新作向けの深層学習の推薦（DropoutNet・CB2CF・two-tower・言語モデル）は、対象分野の協調データか外部への送信が要り、たぐりの方針にそのままは合わない](notes/lit-cold-start-dl.md) が影響する<br>[最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md) が影響する<br>[登録して最初の 1 回目の評価だけ、これから並ぶ公演に関係する過去作から聞く形にするか（起案者の案）](notes/q-first-rating-onboarding.md) が影響する<br>[新しい要素を安全に入れる「裏の答え合わせ」をどう作るか（起案者が良いと判断）](notes/q-hidden-gate.md) が影響する<br>[公開の評判（取得元の公開の評価・クチコミ）を推薦に使えるか](notes/q-public-reputation-signal.md) が影響する<br>[推薦の改善を判断するための評価の仕組みをどう作るか（何のデータで・どの指標で）](notes/q-reco-eval-harness.md) が影響する<br>[「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md) が影響する<br>[その人の記録だけで、計算方式の良し悪しをどう確かめるか（振り返りでの検証）](notes/q-reco-personal-backtest.md) が影響する<br>[観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか](notes/q-theme-preference.md) が影響する<br>[観劇の評価は内容だけでなく、値段に見合うか・構成・演出などが混ざって 1 つの記号になる](notes/rating-mixes-aspects.md) が影響する<br>[今の推薦（person-feedback-v1）の精度は、公開版の利用者では測っていない](notes/reco-accuracy-unverified.md) が影響する<br>[今の計算は「その人の◎の割合」を差し引くので、◎が珍しい人の◎ほど強く効き、◎ばかりの人の◎はほとんど効かない](notes/reco-base-rate-relative.md) が影響する<br>[おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が影響する<br>[Worker の推薦は Python（person-feedback-v1）と同じ結果を出す](notes/reco-js-parity.md) が影響する<br>[過去の改善の実験結果（持ち主 1 人の評価での AUC）は、判断の根拠に使わない](notes/reco-past-auc.md) が影響する<br>[推薦の計算を改善する計画書はあるが、master に入っておらず内容が一部古い](notes/reco-plan-unmerged.md) が影響する<br>[画面の△の説明「あまり合わなかった」は、起案者の考える△（まあ良いが気になる所がある）と食い違う](notes/triangle-label-mismatch.md) が影響する<br>[別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) が影響する |
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
| [見た目の調整室（起案者が色・文字・ボタン・配置・文言を決めて保存し、Claude が読み取って実際の画面に反映する）](notes/design-studio.md) | 廃止 | 2026-10-13 | ─ | 前提にする → [既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md)<br>影響する → [見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md)<br>[いまの見た目（たぐる糸・あたたかい灰の地・1 行の回答の帯・判子）を採用し、調整室は一旦閉じる](notes/dec-design-adopted.md) が前提にする<br>[調整室で選んだ書体（Zen Old Mincho など）を、外部から読み込まずに全員の画面で出すには](notes/q-webfont-local.md) が前提にする |

## 答えの出た問い・取り下げた問い（31 件）

| 項目 | 状態 | 日付 | 検証項目 | つながり |
| --- | --- | --- | --- | --- |
| [古い記録を自動で結び付けるための「過去の公演の一覧」を、CoRich のページを読んで作ってよいか](notes/q-auto-link-past.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [記録と公演ページの自動の結び付けは、いまは持ち主の手元でしか動かない](notes/auto-link-current-state.md)<br>影響する → [昔の公演を、公開情報だけで探せるようにするにはどうするか](notes/q-past-stage-catalogue.md)<br>[記録と公演ページの自動の結び付けは、いまは持ち主の手元でしか動かない](notes/auto-link-current-state.md) が新たな問いを生む<br>[過去の公演の一覧（2019 年以降）を毎日 6,000 枚ずつ作り、記録を自動で結び付ける](notes/dec-auto-link-past.md) が答える |
| [CoRich の検索ページが断る理由と、代わりに公演一覧をどこから取るか](notes/q-corich-search-refusal.md) | 回答済み | 2026-10-13 | S11, S24 | 前提にする → [GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md)<br>影響する → [取得元の利用規約・robots.txt・ポスター画像の権利](notes/q-source-terms.md)<br>[CoRich の検索ページは、サーバー手前のロードバランサーが 403 で断っている（公演ページは 200）](notes/corich-search-waf-403.md) が答える<br>[GitHub Actions からは CoRich の公演一覧の検索（/stage/search）が 403 で断られた](notes/gha-first-run-corich-search-403.md) が新たな問いを生む |
| [CoRich のサイトマップから、これからの公演を見つけられるか](notes/q-corich-sitemap.md) | 回答済み | 2026-10-13 | S24 | 前提にする → [CoRich の robots.txt は禁止を書いておらず、サイトマップを 2 つ示している](notes/corich-robots-sitemap-only.md)<br>[CoRich のサイトマップには、すべての公演ページ（/stage/<id>）が更新日つきで載っている](notes/corich-sitemap-stage-ids.md) が答える |
| [公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) | 回答済み | 2026-10-13 | S23, S24 | 前提にする → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>[取得処理は前回までの控えを引き継いで動く（毎回まっさらでは動かない）](notes/crawler-state-between-runs.md) が影響する<br>[取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md) が答える<br>[1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) が前提にする<br>[非公開リポジトリの GitHub Actions は、無料アカウントで月 2,000 分まで無料](notes/gha-private-free-minutes.md) が影響する<br>[公開リポジトリの Actions の実行ログは誰でも読める。成果物はログインした人が取れる](notes/gha-public-logs.md) が影響する<br>[GitHub Actions の定期実行は遅れたり、混雑時に飛ばされたりする](notes/gha-schedule-unreliable.md) が影響する<br>[公開リポジトリでは GitHub Actions の標準の実行環境が無料。ただし 60 日動きが無いと定期実行が止まる](notes/github-actions-public-free.md) が新たな問いを生む<br>[EC2 は無い](notes/no-ec2.md) が影響する<br>[今の公演カタログ（S3）は、いつ・どこで作られたものか](notes/q-catalog-source.md) が前提にする<br>[Workers の定期実行は、無料プランだと 1 回あたり CPU 10 ミリ秒・外部への要求 50 回まで](notes/workers-cron-free-limits.md) が影響する |
| [取得の作業データ（state ブランチ）が 2 GB になった。ポスターと公演ページの HTML の控えをどうするか](notes/q-crawler-state-size.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た](notes/sitemap-first-run.md)<br>[ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す](notes/dec-posters-r2.md) が答える<br>[サイトマップ版の初回の Catalog（6,000 枚）は成功し、これからの公演 1,353 件・終わった公演 3,460 件を得た](notes/sitemap-first-run.md) が新たな問いを生む |
| [Render を止めたあと、デモ版（見本の記録で試す版）をどうするか](notes/q-demo-after-render.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>影響する → [デモ版とサービス版を分ける](notes/dec-edition-split.md)<br>[デモ版は、触れるがデータを持たないお試し版にする](notes/dec-demo-trial-no-data.md) が答える |
| [たぐりの見た目をどの方向に変えるか（A 幕と半券・B 観劇ノート・C 客電が落ちる）](notes/q-design-direction.md) | 回答済み | 2026-10-13 | ─ | 影響する → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>[既定の見た目は「たぐる糸」に半券を合わせたものにし、A（幕と半券）はやめる。カード型のレイアウトは使わない](notes/dec-design-default-ito.md) が答える<br>[見た目は 1 つに決めず、いくつかの型から利用者が選べるようにする（ポスターの色で染める型も含む）](notes/dec-theme-user-choice.md) が影響する |
| [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) | 回答済み | 2026-10-13 | S12 | 前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md)<br>前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md)<br>[D1 の無料枠は 1 日に読み 500 万行・書き 10 万行、保存 5GB](notes/d1-free-limits.md) が影響する<br>[Cloudflare Workers への完全移行は今は見送る（見直し中）](notes/dec-defer-workers.md) が前提にする<br>[Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md) が影響する<br>[1000 人規模を見込むなら Workers＋D1 に寄せ、上限に近づいたら月 5 ドルの有料プランに上げる](notes/dec-scale-workers.md) が影響する<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が答える<br>[無料で起動を速くするため、Cloudflare Workers＋D1 で動かす](notes/dec-workers-d1.md) が影響する<br>[別の作業で、元の画面の Python を Python Workers で動かす移行版も作られている](notes/python-workers-migration-state.md) が影響する<br>[どのドメインをどこで取るか](notes/q-domain.md) が前提にする<br>[サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする<br>[Render の利用者（tg_session）とログインしたアカウント（D1）は別人として扱われている](notes/render-two-identities.md) が新たな問いを生む<br>[1000 人で使うと、Workers の無料枠は推薦の計算（CPU）と D1 の読み行数で足りなくなりそう（見積もり）](notes/scale-1000-estimate.md) が影響する<br>[Worker での推薦計算は 1 回 10〜12 ミリ秒、重い想定で 39 ミリ秒（見積もり）](notes/worker-reco-cpu-estimate.md) が影響する<br>[別の作業で、Workers＋D1 の版が workers.dev で動き始めている](notes/workers-d1-preview-state.md) が影響する<br>[Workers の有料プランは月 5 ドルで、要求 1000 万回・CPU 3000 万ミリ秒・D1 の読み 250 億行が含まれる](notes/workers-paid-plan.md) が影響する |
| [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md) | 回答済み | 2026-10-13 | S12 | [AWS の無料枠は 2025 年 7 月 15 日以降の新しい口座ではクレジット制（最大 200 ドル・6 か月）](notes/aws-free-plan-2025.md) が影響する<br>[AWS は公開 IPv4 アドレス 1 つにつき 1 時間 0.005 ドル（月 3.6 ドルほど）かかる](notes/aws-ipv4-charge.md) が影響する<br>[東京の t4g.micro は 1 時間 0.0108 ドル（月 8 ドルほど）、t3.micro は 0.0136 ドル](notes/ec2-tokyo-price.md) が影響する<br>[EC2 は無い](notes/no-ec2.md) が答える<br>[公演情報の取得処理をどこで動かすか](notes/q-crawler-host.md) が前提にする<br>[実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md) が前提にする<br>[サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする |
| [最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [内容ベースの推薦で、本人の初期の好みを評価が増えるたびに修正する方法がある（Billsus & Pazzani）](notes/lit-syskill-webert-prior.md)<br>前提にする → [新しい要素を安全に入れる「裏の答え合わせ」をどう作るか（起案者が良いと判断）](notes/q-hidden-gate.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[評価が無いうちの推薦をお気に入りから作るようにした（person-ordinal-v3+fav1、Worker）](notes/impl-favourite-seed.md) が答える<br>[推薦が利用者の行動を変え、その行動で次の推薦を学ぶ「輪」で、推薦は偏りやすくなる（Chaney・Stewart・Engelhardt 2018）](notes/lit-feedback-loop.md) が影響する<br>[映画のジャンルを使った推薦の研究は、主に「新しい利用者・新作の立ち上がり」のために使われている](notes/lit-genre-reco.md) が根拠になる<br>[登録して最初の 1 回目の評価だけ、これから並ぶ公演に関係する過去作から聞く形にするか（起案者の案）](notes/q-first-rating-onboarding.md) が前提にする |
| [登録して最初の 1 回目の評価だけ、これから並ぶ公演に関係する過去作から聞く形にするか（起案者の案）](notes/q-first-rating-onboarding.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [最初に評価してもらう過去作を、これから並べる候補に多い人物・ジャンルから選ぶと、同じ件数で当たりが上がる（楽観的な条件）](notes/eval-onboarding-selection.md)<br>前提にする → [最初に入れる「お気に入り」から、評価が付く前の推薦を作るか（起案者の案）](notes/q-favourites-seed.md)<br>影響する → [本人向けのおすすめ計算（user_recommender.py）](notes/comp-recommender.md)<br>[最初の評価で聞く過去作の一覧を出す API を作った（お気に入りの公演 → 今後の候補を一番多く覆う公演）](notes/impl-onboarding-list.md) が答える |
| [起案者のアカウントの設定で、無料枠を越えても請求されないようになっているか](notes/q-free-tier-account-settings.md) | 回答済み | 2026-10-13 | ─ | 影響する → [たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md)<br>[Cloudflare には R2 の使いすぎを止める仕組みが無い。予算の通知（Budget alerts）は知らせるだけ](notes/cf-budget-alerts-not-cap.md) が新たな問いを生む<br>[たぐりは無料枠の中だけで動かす。上限は無料枠より低く取り、越えそうなら使う前に止めて知らせる](notes/dec-free-tier-only.md) が新たな問いを生む<br>[起案者が Cloudflare の Budget alerts を作り、Workers の Free を確かめた。GitHub には支払い方法を登録していない](notes/free-tier-account-settings-done.md) が答える |
| [移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md) | 回答済み | 2026-10-13 | S33 | 前提にする → [本番に deploy するブランチをどれにするか（PR のブランチのままにしない）](notes/q-production-branch.md)<br>影響する → [Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md)<br>[画面の移行は wip-screens-port で進め、段ごとに試験が通ってから master に入れる](notes/dec-migration-branch-wip.md) が答える<br>[Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) が新たな問いを生む<br>[段 1 の作りかけを受け取った。読み込めない原因は py.js の正規表現に入った生の行区切り文字だった](notes/migration-wip-received.md) が答える<br>[本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md) が影響する |
| [画面の移行の続き（段 1〜5）をどのセッションが受け持つか](notes/q-migration-owner.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [Render をやめ、元の画面を Worker に移す（見た目はそのまま・最後に一度だけ切り替え）](notes/dec-render-full-migration.md)<br>[画面の移行（段 1〜5）は Push セッションが引き継ぎ、途中のコードも受け取る](notes/dec-migration-owner-push.md) が答える<br>[Render からの画面移行は段 0 まで済み、段 1 の途中は別セッションの手元にしかない](notes/migration-handover-stage0.md) が新たな問いを生む |
| [Oracle の公式の無料枠と回収の条件](notes/q-oracle-official.md) | 回答済み | 2026-10-13 | ─ | [Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) が答える |
| [本番に deploy するブランチをどれにするか（PR のブランチのままにしない）](notes/q-production-branch.md) | 回答済み | 2026-10-13 | ─ | [本番の Worker は PR のブランチ（cloudflare-d1-preview）から自動で deploy されている](notes/pr-branch-is-production.md) が新たな問いを生む<br>[本番の Worker の公開元を master に切り替えた（PR #5 は master にマージ済み）](notes/production-branch-master.md) が答える<br>[移行の作業をどのブランチで進めるか（cloudflare-d1-preview は push すると本番に出る）](notes/q-migration-branch.md) が前提にする |
| [総合の評価のほかに、何が良く何が悪かったか（内容・構成・演出・出演・値段・会場）をどう取るか](notes/q-rating-aspects.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>影響する → [「使うほど精度が上がる」推薦をどう作るか（何を好きとし、何を精度の向上とするか）](notes/q-reco-learning-design.md)<br>[推薦は「全部の段階を、その人基準（いつもより高いか低いか）で使う」形に変える。役職の重みの学習は入れない](notes/dec-reco-graded.md) が影響する<br>[評価の詳細（項目ごとの良かった／気になった）を記録に付けられるようにし、評価を項目に応じた役職に効かせるようにした（+asp1）](notes/impl-rating-aspects.md) が答える<br>[総合評価に加えて観点ごとの評価を使う推薦（多基準推薦）は、1 つの評価だけより精度が上がったと報告されている（Adomavicius & Kwon 2007 ほか）](notes/lit-multi-criteria.md) が根拠になる<br>[「値段に見合うか（知覚価値）」は品質と支払う犠牲の釣り合いで決まり、推薦でも価格を別に扱う研究がある（Zeithaml 1988・Zheng ほか 2020）](notes/lit-price-value.md) が根拠になる<br>[観点（値段・脚本・演出など）ごとに下げる相手を変える案を、どう確かめるか](notes/q-aspect-attribution-check.md) が前提にする<br>[観劇の評価は内容だけでなく、値段に見合うか・構成・演出などが混ざって 1 つの記号になる](notes/rating-mixes-aspects.md) が新たな問いを生む<br>[舞台の仕事の分担：演出家が作品全体の芸術面の責任者で、舞台監督は現場の進行、制作・プロデューサーは予算と運営（値段を決める側）](notes/stage-roles.md) が影響する |
| [Render の無料プランでサービス版を動かせるか](notes/q-render-free-viable.md) | 回答済み | 2026-10-13 | ─ | [Render の無料プランは永続ディスクを付けられない](notes/render-free-no-disk.md) が答える |
| [あらすじの読み取りを誰が担うか（Claude の定期実行・Gemini API・当面読まない）](notes/q-synopsis-reader.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [あらすじの読み取りは Gemini API。以前の claude CLI 呼び出しは起案者の判断でやめている](notes/synopsis-llm-history.md)<br>前提にする → [取得処理は、非公開の別リポジトリの GitHub Actions で動かす（勧め）](notes/dec-crawler-gha-private.md)<br>[公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ](notes/dec-synopsis-reader-claude.md) が答える<br>[あらすじの読み取りは Gemini API。以前の claude CLI 呼び出しは起案者の判断でやめている](notes/synopsis-llm-history.md) が影響する |
| [評価の段階を利用者自身に選んでもらうか（起案者の案）](notes/q-user-chosen-scale.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [◎○△× の 4 段階は適切か。△をどう読み、どう推薦に使うか](notes/q-rating-scale.md)<br>[評価の段階は利用者が選べる。初期設定は 5 段階、最小 2 段階・最大 11 段階](notes/dec-user-scale-range.md) が答える<br>[選べるようにしても、多くの人は最初に決められた選択肢のままにする（既定の効果、Johnson & Goldstein 2003）](notes/lit-default-effect.md) が影響する<br>[評価の段階を途中で変えたときの扱い：直接の研究は少なく、段階どうしを決まった式で写すのは最善ではないとされる](notes/lit-scale-change.md) が影響する<br>[利用者に評価の段階を選ばせる案は研究で提案されており、選ばれる段階は評価する物や経験で変わる（Cena・Vernero ほか）](notes/lit-user-chosen-scale.md) が根拠になる |
| [調整室で選んだ書体（Zen Old Mincho など）を、外部から読み込まずに全員の画面で出すには](notes/q-webfont-local.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [見た目の調整室（起案者が色・文字・ボタン・配置・文言を決めて保存し、Claude が読み取って実際の画面に反映する）](notes/design-studio.md)<br>[商用でも無料の日本語書体（SIL OFL）と、自分のサイトで配るときの重さ](notes/ofl-japanese-fonts.md) が答える |
| [Cloudflare 版でポスターをどこに置いて出すか](notes/q-worker-posters.md) | 回答済み | 2026-10-13 | ─ | 前提にする → [「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md)<br>[ポスターは R2 に置き、Worker の画面にも出す。R2 に入れた分は取得の作業データから外す](notes/dec-posters-r2.md) が答える<br>[「今週のおすすめ」── ポスターを切り取り線の左に置き、1 件を詰めて、くわしくは畳む（本番に反映）](notes/dec-recommend-compact-poster.md) が新たな問いを生む |
| [Cloudflare の無料枠だけで、今のコードのまま動かせるか](notes/q-workers-free-viable.md) | 回答済み | 2026-10-13 | ─ | [おすすめは開くたびに全候補を計算している](notes/reco-computed-per-request.md) が答える<br>[サーバーは標準ライブラリの http.server と sqlite3 で書いてある](notes/stdlib-server-sqlite.md) が答える<br>[Workers の無料プランは 1 要求あたり CPU 10 ミリ秒・1 日 10 万要求まで](notes/workers-free-cpu-10ms.md) が答える |
| [検証中に自分だけを通す方法（Cloudflare Access の無料枠）](notes/q-cf-access.md) | 取り下げ | 2026-10-13 | S30 | 前提にする → [サービス版は常時稼働の VM で動かし、前段に Cloudflare を置く](notes/dec-vm-cloudflare.md)<br>[Cloudflare Access は 50 人まで無料（古い公式資料）](notes/cf-access-free-50.md) が影響する |
| [CF-Connecting-IP をどう信頼するか](notes/q-cf-connecting-ip-trust.md) | 取り下げ | 2026-10-13 | S13 | [Tunnel の後ろのサーバーからは、すべての接続元が自分自身に見える](notes/cf-tunnel-origin-localhost.md) が新たな問いを生む<br>[試行回数の制限は接続元のアドレスで数えている](notes/throttle-keyed-by-client-address.md) が新たな問いを生む |
| [Tunnel の公式の制限・料金・必要な設定](notes/q-cf-tunnel-official.md) | 取り下げ | 2026-10-13 | S22 | [Cloudflare Tunnel は無料で使え、ドメインを Cloudflare の DNS に置く必要がある](notes/cf-tunnel-free.md) が新たな問いを生む |
| [Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか](notes/q-oracle-payg.md) | 取り下げ | 2026-10-13 | S29 | [Oracle Always Free の ARM は 2 OCPU・12GB まで。使用が少ないと回収されうる](notes/oracle-always-free.md) が新たな問いを生む<br>[サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) が前提にする |
| [R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md) | 取り下げ | 2026-10-13 | ─ | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md)<br>[D1 のバックアップを、Time Travel の期間より長くどこに残すか](notes/q-offsite-backup.md) が前提にする<br>[R2 は 10GB まで無料で、取り出しの通信料がかからない](notes/r2-free-tier.md) が新たな問いを生む |
| [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) | 取り下げ | 2026-10-13 | S12 | 前提にする → [Oracle を従量課金の契約にすると、無料枠と回収の扱いは変わるか](notes/q-oracle-payg.md)<br>前提にする → [今の EC2 の種類・口座の作成日・月額](notes/q-ec2-cost.md)<br>前提にする → [サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md)<br>[サービス版の VM（cloudflared・systemd）](notes/comp-vm-host.md) が前提にする<br>[サービス版の基盤を「VM＋Cloudflare の前段」と「Workers＋D1」のどちらに寄せるか](notes/q-direction.md) が前提にする<br>[R2 の公式料金と、今の boto3 のコードで読み書きできるか](notes/q-r2-boto3.md) が前提にする<br>[VM でおすすめが 3 秒以内に開くか](notes/q-vm-performance.md) が前提にする |
| [VM でおすすめが 3 秒以内に開くか](notes/q-vm-performance.md) | 取り下げ | 2026-10-13 | S20 | 前提にする → [サービス版の VM は Oracle Always Free と今の EC2 のどちらにするか](notes/q-vm-host-choice.md) |
| [無料プランで CPU 10 ミリ秒を超えると、実際にはどうなるか](notes/q-workers-cpu-overrun.md) | 取り下げ | 2026-10-13 | S20 | 前提にする → [移した画面は Workers 無料枠の CPU 10 ミリ秒に収まるか](notes/q-workers-cpu-real.md)<br>前提にする → [実カタログで、推薦の索引の行数と Worker の CPU 時間がどうなるか](notes/q-real-catalog-stats.md) |
