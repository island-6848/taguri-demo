# たぐり サービス版 システムテスト手順書

| 項目 | 内容 |
|---|---|
| 版 | 第 1 版。2026-10-20 作成 |
| 元 | [システムテスト計画書](system-test-plan.md)（承認済み）・[システムテスト仕様書](system-test-spec.md)（ケース・担当・判定基準） |
| 決めたこと | 〔dec-system-test-design〕 |

仕様書のケースを、**どの条件のときに・どの順で・何を打って・何を見るか**まで書く。節の番号（P-xx）は仕様書の「手順」の列と同じ。
担当の記号は仕様書 2 のとおり（CL＝Claude、OW＝起案者、BT＝ベータ参加者）。

> **無料枠を越えない。** 本番（P）・別の D1（X）・taguri-crawler（CR）を触る節では、始める前と終わったあとに 0.2 と 0.5 の無料枠の確かめを必ず行う。
> 本番で流してよい量は 1 日に Workers 2,000 要求・D1 書き込み 2,000 行・読み出し 5 万行・R2 1,000 回まで（計画書 8）。R2 の上限の試験は本番で行わない〔dec-free-tier-only〕。

---

## 0. どの節にも共通すること

### 0.1 流してよい条件

次がすべてそろったときだけ始める。そろわないケースは「保留」にして、理由を記録する。

- 対象のコミットが決まっていて、そのコミットの CI（Check Cloudflare migration preview・Knowledge graph）が緑
- 本番・X・CR を触る節: 0.2 の無料枠の確かめで、どの項目も 8 割未満
- 本番を触る節: 人工の利用者だけを使う（仕様書 TD-02）。本物の利用者のアカウントに触らない
- 壊す・戻す試験: 本番の D1（`taguri-demo`）ではなく、別の D1（`taguri-st`）か手元で行う

### 0.2 始める前

1. 並行している作業を確かめる（CL）
   ```sh
   git fetch origin
   git log --oneline -10 origin/master
   git branch -r --sort=-committerdate | head
   ```
   方針の食い違いがあれば、ナレッジグラフに `question` を立て、起案者に伝える
2. 対象のコミットを記録に書く（`git rev-parse --short HEAD`。本番は `/api/health` の版）
3. 無料枠を見る（本番・X・CR を触る節）
   - OW: ブラウザで `https://app.taguri.workers.dev/api/health` を開き、`free_tier` の各値と上限を記録に写す
   - OW: taguri-crawler の最新の Catalog の実行の Summary にある「Free-tier check」の表を写す
   - どれかが 8 割以上なら、**その日の本番・X・CR の節は流さない**。起案者に知らせる（OW が見たなら、そのまま判断する）
4. 記録のファイルを作る（0.4 の形）

### 0.3 止める条件

流している途中で次のどれかが起きたら、その場で止め、記録に書き、起案者に知らせる。

- 仕様書 1.3 の「致命」に当たる不具合（記録が消えた・他人の記録が見えた・請求が出た・秘密が出た）
- 無料枠のどれかが 8 割を越えた、または数えられなくなった
- 手順に書いていない操作をしないと先へ進めない（手順を直してから流し直す）
- 本番で、人工の利用者以外の行に触れたおそれがある

### 0.4 記録の形

1 回の実施ごとに `docs/verification/system-test-<YYYY-MM-DD>-<節>.md` を作る（例: `system-test-2026-10-26-P03.md`）。

```markdown
# システムテスト P-03 通し検証（2026-10-26）

| 項目 | 内容 |
|---|---|
| 実施者 | CL |
| 対象 | master `abc1234` |
| 環境 | L（wrangler 4.x・Node 22.x・Chromium 1xx） |
| 無料枠（前） | ―（ローカルのみ） |
| 無料枠（後） | ― |

| ケース | 判定 | 証拠 | メモ |
|---|---|---|---|
| FN-01-01 | OK | `$E2E_OUT/01.png` | |
| FN-03-02 | NG | D1 の行（下） | issue #NNN |

## 不具合
- #NNN（重い）…

## 残したこと・分かったこと
```

- 証拠の画像・出力は、個人の情報が無いことを確かめてから置く。人工の利用者の復旧コード・Cookie は記録に書かない
- NG は GitHub の issue を作り、重さ（致命・重い・軽い）を付け、記録に番号を書く
- 分かったことはナレッジグラフ（`docs/knowledge/notes/`）に `finding`、残った問いは `question` として足し、`python3 tools/knowledge/build_graph.py` を流す

### 0.5 終わったあと

1. 本番を触った節: 人工の利用者をアカウントの画面から削除する（P-08 の 8）。Firebase の利用者一覧から消えたかも見る
2. X を触った節: `npx wrangler d1 delete taguri-st`（OW）。消す前に、戻した中身を手元に残していないか確かめる（残すなら暗号化して手元だけ）
3. 手元に平文の控え（`*.sql`）を出した節: `rm -rf "$W"`
4. 0.2 の 3 と同じ無料枠の確かめをもう一度行い、記録に写す
5. 記録をコミットする（CL）。起案者が流した節は、起案者が結果を Claude に渡し、Claude が記録に起こす

---

## P-01 ローカルの環境を作る（CL）

```sh
cd cloudflare
node --version            # 22 以上（node:sqlite を使う）
python3 --version         # 3.12 以上
npm ci --no-audit --no-fund
npx wrangler --version    # 4.x
ls /opt/pw-browsers/chromium   # Playwright の Chromium（playwright install はしない）
```

まっさらな手元の D1:

```sh
export ST_D1=$(mktemp -d)                         # 毎回新しく
npx wrangler d1 migrations apply taguri-demo --local --persist-to "$ST_D1"
npx wrangler dev --ip 127.0.0.1 --port 8787 --persist-to "$ST_D1"   # 別の端末で起動したままにする
```

設定を変えて起動するとき（P-05・P-15）: `--var ALLOW_REGISTRATION:false` や `--var ORIGINAL_UI_BRIDGE:false` を足す。

**確かめ:** `curl -s http://127.0.0.1:8787/api/health` が `"ok":true` を返す。

## P-02 自動の試験一式（CL・毎回）

対象: FN-02-06・FN-08-02・FN-10-03・FN-11-01〜02・FN-12-01・AV-06-01・PF-05-01・OM-02-01〜03・OM-04-01・OM-07-01・SC-02-01〜02・SC-03-01・SC-05-01・SC-09-01

```sh
cd cloudflare
npm audit --omit=dev --audit-level=high          # SC-09-01
npm test                                         # Worker の試験（128 本）
python3 -m unittest discover -s test -p 'test_*.py'
npx wrangler deploy --dry-run --outdir "$(mktemp -d)"
npx wrangler d1 migrations apply taguri-demo --local
node test/runtime-smoke.js
cd ..
for t in tools/taguri/test_*.py; do python3 "$t" || echo "NG: $t"; done
python3 tools/knowledge/build_graph.py --check
```

ケースごとの見どころ:

| ケース | 見る試験 | OK の条件 |
|---|---|---|
| FN-02-06・SC-02-02 | `passkey.test.js` | すべて ok |
| FN-10-03 | `account-delete.test.js` | すべて ok |
| FN-11-01〜02 | `fixrequest.test.js` | すべて ok |
| AV-06-01 | `trouble.test.js` | すべて ok |
| PF-05-01・SC-05-01 | `rate-limit.test.js` | すべて ok |
| OM-02-01〜03 | `migrations-keep-records.test.js`・`test_delivery_keeps_records.py`・`redeploy-keeps-records.test.js` | すべて ok |
| OM-04-01 | `test_free_tier.py` | すべて ok |
| OM-07-01 | `cleanup.test.js` | すべて ok |
| SC-03-01 | `export.test.js` | すべて ok |
| FN-12-01 | CI の一致試験 | 緑 |

**判定:** どれか 1 本でも落ちたら NG。前から落ちていると分かっている試験（〔legacy-test-failures〕）は、記録に名前を書き、今回の変更で新しく落ちたものと分ける。
**CI でも同じ:** push すると `cloudflare-preview-check.yml` が同じものを流す。手元と CI の両方の結果を記録に書く。

## P-03 通し検証（CL）

対象: FN-01-01〜03・FN-02-01〜03・FN-03・FN-04・FN-05-01〜03・FN-06・FN-07-01〜02・FN-08-01・FN-08-03・FN-09・FN-10-01〜02・MG-04-01・SC-01

条件: P-01 ができていること（`e2e-walk.js` は自分で wrangler dev とまっさらな D1 を起動するので、P-01 の wrangler dev は止めておく）。

```sh
cd cloudflare
export E2E_OUT=$(mktemp -d)/e2e        # 画面の写しの置き場所
node test/e2e-walk.js 2>&1 | tee "$E2E_OUT.log"
```

1. 最後に出る段ごとの OK／NG の表を記録に写し、段を仕様書のケースに当てる（仕様書 6.1 の「元」の列の e2e #）
2. 終了コードが 0 でなければ、NG の段の写しとログを見る
3. 次の 3 つは `e2e-walk.js` に無いので、同じ wrangler dev とブラウザで手で確かめる
   - **FN-08-03:** 開発者ツールの通信の記録で、人の流れ・相関図の画面が `/figs/` を読み、Worker の画面の応答に図が入っていない
   - **MG-04-01:** 段 22 で書き出した `taguri-export.json` を、新しく作った利用者 C で取り込み、C の記録の件数が説明どおりで、B の行が無い
   - **FN-05-03:** 効かせ方を「出演者を強く」にして、出演者の一致する公演が上がる
4. 1 回に 1〜2 分。NG を直したら全段を流し直す（段は前の段の状態を使うので、途中からは流さない）

## P-04 見た目（CL）

対象: FN-12-02・EN-04-01・EN-05-02

```sh
cd cloudflare
python3 scripts/visual_fixtures.py /tmp/taguri-visual-fixtures.json
node test/visual-check.js          # 写しと差の画像は /tmp/taguri-visual
```

- **FN-12-02:** 1280 と 390 の幅で、元の画面との差が `visual-check.js` の閾値以内。差の画像を記録に添える
- **EN-04-01:** `visual-check.js` の幅に 360 が無ければ足してから流す。全画面で横のスクロールが出ない（`document.documentElement.scrollWidth <= 360`）
- **EN-05-02:** P-01 の wrangler dev で、ログインした状態でおすすめを 2 回開き、開発者ツールの通信の記録で 2 回目の要求の数が 1 回目より少ない。数を記録する

## P-05 無料枠の上限に当てる（CL・ローカルだけ）

対象: FN-01-05・AV-05-01〜03・PF-05-02

**本番では流さない。** R2 の上限（AV-05-02）は越えると請求されるので、特に本番では試さない。

1. 試験で確かめる（P-02 の中にもある）
   ```sh
   cd cloudflare
   node --test --test-isolation=none test/free-tier-d1.test.js test/rate-limit.test.js test/limit-upsert.test.js
   ```
   - AV-05-01: D1 の大きさが 4 GB に達した状態で、足す操作が日本語の案内で断られ、外す・消す・ログアウト・削除は通る
   - AV-05-02: R2 の今月の読み出しが上限に達した状態で、ポスターを読まずに画面が出る
2. 新規登録の止め（FN-01-05）
   ```sh
   npx wrangler dev --ip 127.0.0.1 --port 8787 --persist-to "$ST_D1" --var ALLOW_REGISTRATION:false
   curl -s -X POST http://127.0.0.1:8787/api/register -H 'Origin: http://127.0.0.1:8787' -H 'Content-Type: application/json' -d '{"agree":"<今の規約の版>"}' -w '\n%{http_code}\n'
   ```
   503 と「新規登録を一時停止しています。」。前に作った利用者の Cookie では画面が開く
3. 人数の上限（AV-05-03・PF-05-02）: 手元の D1 に 300 人を入れ（`node scripts/st_seed_users.mjs --users 300 --records 0 --out /tmp/st-seed.sql` → `npx wrangler d1 execute taguri-demo --local --persist-to "$ST_D1" --file /tmp/st-seed.sql`）、301 人目の登録が断られる。同じ日に 30 人を作ったあとの 31 人目、同じ住所（`CF-Connecting-IP` を固定）から 4 人目も断られる
4. 記録に、断られたときの状態コードと案内の文を写す

## P-06 性能（OW／CL）

対象: PF-01・PF-02・PF-03-02・PF-04-01

1. **実カタログでの CPU（PF-01、CR、OW）:** 実カタログの索引はこの作業環境に無い。taguri-crawler の Catalog のジョブで索引を作ったあと、同じ場所で流す
   ```sh
   node cloudflare/scripts/measure_worker.mjs --index d1-out/index.sql --sizes 0,5,20,50,100,300
   node cloudflare/scripts/measure_worker_replay.mjs --index d1-out/index.sql --sizes 0,20,50 --rep 15 --notes 0.5   # D1 を通らない CPU だけ
   node cloudflare/scripts/st_measure_screens.mjs --index d1-out/index.sql --sizes 0,20,200,300 --rep 9 | tail -1   # 主な画面（PF-01-02）
   ```
   出力の表（記録の件数ごとの CPU の真ん中の値・いちばん遅い値・D1 の行数）を Claude に渡す。Claude が記録に起こし、10 ミリ秒の基準と 8 ミリ秒の注意のラインで判定する
2. **D1 の行数（PF-02-01、CL）:** 1 の行数から、300 人 × 1 日 20 画面の読み込みを表で計算し、500 万行の半分以下か見る
3. **索引の入れ替え（PF-02-02、OW）:** Catalog の Free-tier check の表で、その日の書き込みが 8 万行の中
4. **300 人の伸び（PF-04-01、CL）:** 公演の id を書き出し（`npx wrangler d1 execute taguri-demo --local --persist-to "$ST_D1" --json --command "SELECT id FROM catalogue" | python3 -c 'import json,sys; print("\n".join(r["id"] for r in json.load(sys.stdin)[0]["results"]))' > /tmp/st-stages.txt`）、`node scripts/st_seed_users.mjs --users 300 --records 200 --stages /tmp/st-stages.txt --out /tmp/st-seed.sql` を入れ（60,300 行。D1 で約 14 MB）、TD-01 の索引で 1 と同じ測りをする。D1 の大きさ（`wrangler d1 execute … --command "PRAGMA page_count"` × ページの大きさ）から、300 人の大きさを推計して表にする
5. **速さ（PF-03-02、CL）:** P-01 の wrangler dev で、主な画面を 20 回ずつ `curl -w '%{time_total}'` で開き、95% の値が 1 秒以内

## P-07 安全（CL・一部 OW）

対象: SC-04・SC-06・SC-07・SC-08・SC-10・SC-11・EN-05-01

1. **入れた文字（SC-04-01）:** `node --test test/st-escape.test.js`（`npm test` にも入っている）。ブラウザでも、TD-05 を感想に入れた利用者で全画面を開き、警告の窓が 1 度も出ない・コンソールに CSP の違反以外のエラーが無い
2. **ヘッダ（SC-04-02・SC-11-01・EN-05-01）:** `node --test test/st-headers.test.js`（`npm test` にも入っている）。手でも:
   ```sh
   for p in / /login /privacy /terms /export.json /api/health /.well-known/assetlinks.json; do echo "== $p"; curl -sI "http://127.0.0.1:8787$p" | grep -iE 'content-security|x-content-type|cache-control|strict-transport'; done
   ```
   本番の分（SC-11-01 の P）は OW が同じコマンドを本番の URL で流し、出力を渡す（6 要求）
3. **ログの目印（SC-06-01）:** `node test/st-log-marker.js`（30 秒ほど。全部 OK なら終了コード 0）。手で確かめるときは、wrangler dev の出力をファイルに残しながら、TD-04 の目印を感想・お気に入り名・修正依頼に入れ、ログイン・ログアウト・復旧コードでのログインをする。終わったら
   ```sh
   grep -c "STMARK-" wrangler.log          # 0 であること
   grep -c "<その回の復旧コード>" wrangler.log   # 0
   grep -ci "cookie:" wrangler.log         # 0
   ```
4. **本番のログ（SC-06-02、OW）:** `npx wrangler tail app --format json > tail.json` を流したまま、人工の利用者 A で 3 と同じ操作をし、同じ `grep` をする。`tail.json` は終わったら消す
5. **追える記録（SC-07-01）:** 3 のログから、ログインの失敗・削除・上限の発動の行を抜き出し、何が起きたかが分かり、中身が無いことを見る
6. **持ち主専用（SC-08-01）:** `node --test test/st-owner-only.test.js`（`npm test` にも入っている）
7. **秘密（SC-10-01）:** GitHub の秘密の検査をリポジトリ全体に流す（CL）。Firebase の API キーに制限が掛かっていることは OW が Google Cloud のコンソールで見る

## P-08 本番のスモーク（OW、手順と記録の下書きは CL）

対象: FN-01-04・FN-02-04〜05・FN-05-04・FN-07-03・FN-10-04〜05・FN-11-03・OM-02-04・SC-02-03・SC-05-02・MG-06-01

条件: 0.1・0.2 がそろっていること。1 回の実施は 1 時間以内、Workers の要求はおよそ 300 以内に収める（画面 1 枚でポスターを含めて約 20 要求）。

1. ふだん使わないブラウザのプロフィール（または秘密のウィンドウ）で `https://app.taguri.workers.dev/` を開く
2. **FN-01-04:** 同意して、パスキーで新規登録。復旧コードは記録に書かず、終わるまで手元に控える。おすすめ・記録・興味ありが空であることを写す。これが利用者 A
3. **OM-02-04（前半）:** A で記録を 3 件つけ、1 件に ◎、感想に `ST-<日付>-A` と書く。件数と中身を写す
4. **FN-05-04:** ◎ を付けた記録の出演者の公演が、次のおすすめに理由付きで出るか見る（出なければ、その人の公演が一覧に無いだけでないかを Claude と確かめる）
5. **FN-02-04・FN-02-05:** ログアウトし、試験用の Google アカウントでログイン（利用者 A2）。ログアウトし、メールのリンクでログイン（A3）。リンクをもう一度開いて使えないことを見る
6. **SC-02-03:** 別のブラウザで、A の Cookie を持たずに ログインが要る画面（トップの `/` と `/export.json`）を開き、ログインの画面に回されることを見る
7. **FN-07-03・FN-11-03（任意）:** A で Google カレンダーに 1 件書き出して消す。修正依頼を 1 件送り、Gmail に知らせが届くことを見る
8. **FN-10-04・FN-10-05:** アカウントの画面で、Time Travel に 7 日残ることが書いてあるのを写し、A・A2・A3 を削除する。Firebase のコンソールの利用者一覧に A2・A3 が残っていないことを見る
9. **OM-02-04（後半）:** 3 の前に、記録を残したままの人工の利用者 B を別に作っておき、次の配備と次の朝の配送のあとに開き、件数と中身が同じことを写してから B を削除する
10. **SC-05-02（任意）:** 家の回線で、違う復旧コードでのログインを 11 回して断られたあと、携帯の回線からはふつうにログインできる
11. **MG-06-01（CL）:** アカウントの画面から行く Render 版の案内を読み、移らないことと書き出し方が書いてあるか

0.5 の無料枠の確かめを行い、写しと結果を Claude に渡す。

## P-09 Time Travel の戻し（OW、手順と時間の記録の下書きは CL）

対象: AV-03-01・AV-07-01・OM-06-01

Time Travel は戻す先を選べず、その D1 自身が戻る。だから本番の `taguri-demo` では試さず、試験用の `taguri-st` で行う。

```sh
cd cloudflare
npx wrangler d1 create taguri-st
npx wrangler d1 migrations apply taguri-st --remote
# A・B の記録（各 5 行ほど）を入れる。SQL は Claude が用意する（st-seed-ab.sql）
npx wrangler d1 execute taguri-st --remote --yes --file st-seed-ab.sql
npx wrangler d1 execute taguri-st --remote --command "SELECT user_id, COUNT(*) FROM works GROUP BY user_id"   # 前の件数
date -Iseconds                                    # この時刻を控える（T0）
# 数分待ってから、A の記録を 2 行消し、B の評価を書き換える
npx wrangler d1 execute taguri-st --remote --command "<Claude が用意する変更の SQL>"
npx wrangler d1 time-travel info taguri-st --timestamp=<T0>          # 印（bookmark）
time npx wrangler d1 time-travel restore taguri-st --bookmark=<印>   # かかった時間を測る
npx wrangler d1 execute taguri-st --remote --command "SELECT user_id, COUNT(*) FROM works GROUP BY user_id"   # 前と同じか
```

**OK の条件:** 最後の件数と中身が T0 のときと同じ。かかった時間を記録に書く。書き込みは 100 行以内（1 日の 10 万行の枠を本番と分け合うため）。
**AV-07-01:** P-10 と合わせ、「カタログの巻き戻し → D1 の戻し → 削除のやり直し（〔q-restore-redelete〕）」を順に通し、始めから終わりまでの時間が 4 時間以内か見る。
終わったら 0.5 の 2（`taguri-st` を消す）。

## P-10 控えから戻す（OW）

対象: AV-04-01〜02・OM-05-01・MG-05-01・OM-06-01

1. **AV-04-01:** taguri-crawler の Actions で「Restore drill」を手動で動かす。月初（Actions の分が戻ったあと）に流す。`free_tier.py plan --mode drill` が止めたら「保留」にし、翌月の初めに回す（10/19 に一度止められた）
2. **AV-04-02・MG-05-01:** [控えと戻し方](backup-restore.md) の「7 日より前に戻す」を、`taguri-restored` の代わりに `taguri-st` で行う。控えの表の数・行の数（Restore drill の出力にある）と、入れたあとの `SELECT COUNT(*)` が一致する。続けて、手元の `wrangler dev` をその D1 に向け（`--remote` は使わず、`wrangler.jsonc` の写しを手元で書き換える）、全画面が開くことを見る。**`wrangler.jsonc` の書き換えはコミットしない**
3. **OM-05-01:** 7 日続けて `npx wrangler r2 object list taguri-backup --prefix backup/d1/` を見て（または Catalog の実行の「Back up the user records」）、毎日 1 つ増え、30 日より古いものが無い
4. 平文の控えは 0.5 の 3 で消す

## P-11 見張りを鳴らす（CL・OW）

対象: AV-01・AV-02・PF-03-01・OM-04-02・EN-06-01

1. **AV-01-01（CL）:** Actions → Service watch → Run workflow。`url` に `https://app.taguri.workers.dev/api/health-st-not-found` を入れる。実行が失敗すること。OW は GitHub から通知のメールが届いたかを見る
2. **AV-01-02（CL）:** `url` を空のまま（変数 `TAGURI_HEALTH_URL`）か、本番の `/api/health` で実行し、成功すること
3. **AV-02-01（CL）:** Actions → Catalog age → Run workflow。`max_days` に `-1` を入れる（カタログが今日の日付でも「0 日前 > -1」で失敗する）。失敗し、通知が届くこと
4. **PF-03-01（CL）:** Service watch の直近 7 日の実行の一覧で、失敗が無い（あれば、その実行のログで遅さか止まりかを見る）
5. **OM-04-02・EN-06-01（OW）:** taguri-crawler の最新の Catalog の Summary の Free-tier check の表と、取得のログの要求の間隔を Claude に渡す。全項目が 8 割未満、同じ取得元への間隔が 1 秒以上、robots.txt で禁止されたパスが無い

公開リポジトリの Actions は無料。1〜3 は 1 回ずつ（3 分ほど）しか流さない。

## P-12 本番の出し方（OW・CL）

対象: OM-01

1. **OM-01-01（OW）:** Cloudflare のダッシュボード → Workers → taguri → Settings → Builds で、本番の組み立て元が `master` で、作業ブランチの組み立てが本番に出ない設定であることを写す（〔q-branch-builds-fail〕も合わせて見る）
2. **OM-01-02:** CL が作業ブランチに、画面には出ない小さな変更（試験の記録のコミットでよい）を push する。OW は、push の前と 10 分後に `/api/health` の版と画面を見て、変わっていないことを写す

## P-13 migration の失敗（OW、SQL は CL）

対象: OM-03-01

1. P-09 と同じく `taguri-st` を作り、今の migration を全部当て、A・B の記録を入れる
2. Claude が用意する「前半は正しく、途中で失敗する」migration（例: 表を足す → 無い列を参照して失敗）を、`taguri-st` のときだけ使う別のフォルダに置いて当てる
   ```sh
   npx wrangler d1 execute taguri-st --remote --file st-broken-migration.sql
   npx wrangler d1 execute taguri-st --remote --command "SELECT name FROM sqlite_master WHERE type='table'"
   ```
3. 前半で足した表が残ったか（巻き戻ったか）、A・B の行が変わっていないかを写す
4. 結果を Claude に渡す。Claude が〔q-d1-migration-failure〕に答えの finding を書き、[控えと戻し方](backup-restore.md) に戻し方を足す
5. 0.5 の 2

## P-14 実機（OW）

対象: FN-13・EN-01〜04（EN-04-01 を除く）

本番の人工の利用者で行う（1 台あたり 1 人。終わったら削除）。1 台につき次の表を埋めて Claude に渡す。

| 操作 | OK／NG | メモ |
|---|---|---|
| 新規登録（パスキー） | | |
| 復旧コードを控える・復旧コードでログイン | | |
| 記録を 1 件足す・評価・感想 | | |
| おすすめを開く・興味あり | | |
| ログアウト・パスキーでログイン | | |
| アカウントの削除 | | |
| 文字を大きくした設定で暦の「(貸)17:00」（EN-04-02） | | |

- 端末: iPhone（Safari）・Android（Chrome とアプリ）・Mac・Windows（Chrome・Edge・Firefox・Safari のうち持っているもの）。持っていないものは保留
- **FN-13-01:** アプリを入れ直してから起動し、上の URL と ✕ の帯が出ないことを写す
- **EN-03-01:** iPhone の Safari で 1 人だけ削除せずに残し、7 日後に開いてログインが保たれているかを見てから削除する
- 1 台あたり Workers の要求はおよそ 200

## P-15 切り替え（CL・OW）

対象: MG-02・MG-03

1. **MG-02-01（CL、切り替えの前）:** `npx wrangler dev … --var ORIGINAL_UI_BRIDGE:false` で全画面を開き、wrangler の出力に Render（`onrender.com`）への要求が 1 つも無い。どの画面も「いま新しい仕組みに移しています」で止まらない
2. **MG-03-01（OW、前）:** 本番で人工の利用者 D を作り、記録を 3 件つけて写す
3. 段 5 の切り替えを行う（[サービス化の進め方](service-roadmap.md) の 4。別の作業）
4. **MG-03-01（OW、後）:** D で開き、件数と中身が同じ
5. **MG-02-02（OW）:** 切り替えから 7 日、`wrangler tail` を 1 日 10 分ずつ流し、`onrender.com` への要求が 0 件。7 日たったら D を削除
6. 切り替えのあと、P-02・P-03・P-04 を流し直す（回帰）

## P-16 ベータ（OW・BT、まとめは CL）

対象: BT-01〜04・EN-07-01

1. 5〜10 人を招く（Play の非公開テストの 12 人と一緒に集めてよい）。招く前に、記録が試験であること・消えるおそれがあること・問い合わせ先を伝える
2. **BT-01:** うち 3 人以上は、起案者が横で見る（説明をしない）。おすすめに 1 件反応するまでに迷った所を書く
3. **BT-02:** 1 人に 10 件を手で入れてもらい、時間を測る
4. **BT-03:** 毎週 1 回、全員に「記録が消えた・他人の記録が見えたことがあったか」を聞き、問い合わせと合わせて記録する。1 件でもあれば致命として 0.3 で止める
5. **EN-07-01・BT-04:** 毎週、`/api/health` の `free_tier` と Free-tier check の表を写し、1 人 1 日あたりの要求・D1 の読み書き・Actions の分と、2 週目にも開いた人の割合を Claude が表にする。300 人に伸ばしたときの推計が無料枠の半分を越えたら、起案者に知らせる
6. 4 週間が終わったら、Claude が判定の案（仕様書 1.4 の全体の合格ライン）を書き、起案者が判定する

---

## 付録 A. 段ごとの流す順

| 計画書の段 | 流す節 | 担当 |
|---|---|---|
| 0. 準備（10/21〜） | P-01、書き足す試験（仕様書 4）を書いて P-02 に入れる | CL |
| 1. ローカル・CI（10/26〜） | P-02 → P-03 → P-04 → P-05 → P-07（ローカルの分）→ P-06 の 4・5 | CL |
| 2. 本番・別の D1（11/5〜） | P-11 → P-12 → P-08 → P-07 の 2・4 → P-09 → P-13 → P-10（11/1 以降）→ P-06 の 1〜3 | OW・CL |
| 3. 実機（10/26〜、並行） | P-14 | OW |
| 4. 切り替え（11/10〜） | P-15 → P-02・P-03・P-04（回帰） | CL・OW |
| 5. ベータ（11/17〜12/14） | P-16、毎日 P-11 の 4・5 を見る | OW・BT・CL |
| 6. 判定（12/15 ごろ） | 記録をまとめ、仕様書 1.4 で判定 | CL（案）・OW（判定） |

## 付録 B. 本番で使う量の見積もり

| 節 | 回数 | Workers の要求 | D1 の書き込み |
|---|---|---:|---:|
| P-08 | 1〜2 回 | 約 300 × 2 | 約 100 × 2 |
| P-07 の 2・4 | 1 回 | 約 100 | 約 30 |
| P-11 | 1 回 | 約 20 | 0 |
| P-12 | 1 回 | 約 10 | 0 |
| P-14 | 端末 6 台 | 約 200 × 6 | 約 50 × 6 |
| P-15 | 1 回＋7 日 | 約 100 | 約 30 |

いちばん多い日（P-14 を 1 日にまとめた日）でも Workers 約 1,200 要求・D1 の書き込み約 300 行で、計画書 8 の 1 日の目安（2,000 要求・2,000 行）に収まる。P-09・P-10・P-13 の `taguri-st` への書き込みは 1 回 100 行以内（P-10 の控えの読み込みは控えの行数、今は約 4,700 行。Restore drill の 1 万行の上限の中）。
