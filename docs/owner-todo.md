# 起案者のやることリスト

起案者にしかできないこと（アカウント・お金・鍵・実機・決めること）の一覧です。Claude が作業の中で見つけたら足し、済んだら「済み」に移します。
くわしい理由や経緯は、各項目の〔 〕の中の名前（`docs/knowledge/notes/` の同じ名前のファイル）にあります。最終更新 2026-10-21。

費用が掛かるのは、ストアの登録料（Google Play 1 回 25 米ドル・Apple 年 99 米ドル）だけです〔dec-app-release-costs〕。それ以外は無料枠の中で進めます。

## いますぐ（Android アプリの上の URL と ✕ の帯を消す）

- [ ] **アップロード鍵を GitHub の Secrets に入れる**（Claude が渡した `github-secrets.txt` の 4 つの値。Settings → Secrets and variables → Actions）〔dec-twa-fixed-signing〕
- [ ] **`taguri-upload.jks` と合言葉を、手元の安全な場所に保管する**（なくすと Play で鍵を替える手続きが要る）
- [ ] Actions → Android → Run workflow で組み直し、前のアプリを消してから新しい APK を入れ直す。帯が消えたか Claude に知らせる

## Google Play に出すまで（手順は [android-release.md](android-release.md)）

- [ ] **アプリの番号（パッケージ名）を決める。** いまは仮に `jp.taguri.app`。Play に一度上げると変えられない
- [ ] Google Play Console の開発者アカウントを作る（25 米ドル・本人確認）。個人か組織かを決める〔plan-app-release〕
- [ ] 個人のアカウントなら、非公開テストに入ってくれる人を **12 人以上**集める（14 日続けて参加が要る）〔f-store-review-rules〕
- [ ] Play Console に AAB を上げ、「アプリ署名鍵」の SHA-256 を Claude に知らせる（サイトに足すと、Play から入れたアプリでも帯が消える）
- [ ] 掲載情報を入れる: 文面は [store/google-play-listing.md](store/google-play-listing.md)、画像は `docs/store/images/`〔impl-store-images〕。データセーフティ・コンテンツのレーティングに答える
- [ ] 問い合わせ用のメールアドレスを作る（規約・削除依頼の窓口に載せる）〔q-contact-email〕

## 実機で確かめること

- [ ] パスキーを iPhone・Android で登録・ログインできるか〔q-passkey-real-devices〕
- [ ] iPhone の Safari でログインが保たれるか（Cookie）〔q-safari-cookies〕
- [ ] 暦の貸切の回「(貸)17:00」が升からはみ出さないか〔q-ttb-kas-phone-fonts〕

## 管理画面で確かめること

- [ ] Firebase の API キーに制限（Web サイト・使う API）を掛ける（Google Cloud コンソール）〔q-firebase-key-restriction〕
- [ ] アカウントを消したあと、Firebase の利用者一覧に残っていないかを見る〔q-firebase-user-deletion〕
- [ ] Cloudflare のダッシュボードで Workers Builds の月の分（無料 3,000 分）を見る〔q-workers-builds-minutes〕
- [ ] Workers Builds が「master だけ組み立てる」設定のままか見る。2026-10-20 も作業ブランチ（PR #238・#239）の組み立てが毎回 ✗ になっている。ログは Builds の記録にだけ出る〔q-branch-builds-fail〕

## 取得（taguri-crawler）を新しい形にする（2026-10-21〔dec-crawl-tiers〕）

- [ ] taguri-demo の PR #243（D1 の読み出しを減らす）と、取得の優先順位の PR をマージする（Claude はレビュー無しのマージができない）。順番は taguri-demo が先、taguri-crawler があと
- [ ] Cloudflare の鍵（CLOUDFLARE_API_TOKEN）に、D1 の分析を読む権限（Account Analytics: Read）があるか見る。無いと、点検の表の D1 の読み出しが「読めなかった」になる〔f-wrangler-d1-info-reads〕

## 決めること
- [ ] 共有リンクの追記（プライバシーポリシー第 5 条）の文面を確かめ、改めての同意（TERMS_VERSION を上げて全員に同意を求める）が要るかを決める。いまは「本人が自ら作るときだけ公開する」ので、版は上げていない〔dec-share-links〕

- [ ] 公開リポジトリの過去の履歴に残る観劇記録・第三者の連絡先を、履歴から消すか〔q-pii-git-history〕
- [ ] 「眺める」に足す図を選ぶ〔q-records-viz〕
- [ ] 下書きの PR #9・#12（`cloudflare-d1-preview` 向け）を続けるか閉じるか
- [ ] 「次の更新で探してもらう」依頼を処理する段を作るか（issue #101）。今は依頼を受け付けるだけで、だれも探していない。案: 毎日の取得が新しく読んだ公演と、頼まれた題名を手元で照らし、画面に「見つかった・まだ」を出す（通信なし・Actions 数秒・D1 の書き込み 1 日 最大 200 行）〔q-search-request-crawl〕

## 済み

- 2026-10-24 定期実行の環境のセットアップスクリプトを空にした（許可の設定の書き方の 2 行が入っていて、あらすじの読み取りが 10-20 ごろから毎回失敗していた）〔f-past-synopsis-progress-1024〕

- 2026-10-20 ストアの登録料は起案者が負担すると決めた〔dec-app-release-costs〕
- 2026-10-13 取得用の非公開リポジトリ taguri-crawler を作り、Claude の GitHub アプリを許可した〔q-crawler-repo〕
