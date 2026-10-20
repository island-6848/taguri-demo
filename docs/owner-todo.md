# 起案者のやることリスト

起案者にしかできないこと（アカウント・お金・鍵・実機・決めること）の一覧です。Claude が作業の中で見つけたら足し、済んだら「済み」に移します。
くわしい理由や経緯は、各項目の〔 〕の中の名前（`docs/knowledge/notes/` の同じ名前のファイル）にあります。最終更新 2026-10-20。

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

## 決めること

- [ ] [システムテスト計画書](system-test-plan.md)を認めるか: 日程、本番で流す試験の 1 日の量、対象の OS・ブラウザ、戻すまでの時間（4 時間）の目標〔dec-system-test-plan〕
- [ ] 公開リポジトリの過去の履歴に残る観劇記録・第三者の連絡先を、履歴から消すか〔q-pii-git-history〕
- [ ] 「眺める」に足す図を選ぶ〔q-records-viz〕
- [ ] 下書きの PR #9・#12（`cloudflare-d1-preview` 向け）を続けるか閉じるか

## 済み

- 2026-10-20 ストアの登録料は起案者が負担すると決めた〔dec-app-release-costs〕
- 2026-10-13 取得用の非公開リポジトリ taguri-crawler を作り、Claude の GitHub アプリを許可した〔q-crawler-repo〕
