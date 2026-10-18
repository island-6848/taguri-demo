// 現行サービス版の主要操作を、本物の Worker（wrangler dev・ローカルの D1）と実ブラウザー（Chromium）で
// 最初から最後まで通す（issue #134）。本番には繋がない。
//
//   cd cloudflare && node test/e2e-walk.js            # 画面の写しは $E2E_OUT（既定 /tmp/taguri-e2e）
//
// - 毎回まっさらなローカル D1（一時フォルダ、--persist-to）に移行を当て、試験用の公演一覧
//   （test/screens/catalogue.py・recommend_fixture.py と、下の過去の公演）を入れてから始める
// - 登録はパスキー（Chromium の仮想認証器）。Google・メールのリンクは外の Firebase が要るので通さない
// - 失敗しても次の段に進み、最後に段ごとの OK / NG を表にする。NG が 1 つでもあれば終了コード 1
// - 時計は本物（Worker の env.CLOCK は wrangler の vars から渡せない）。公演の日付は今日（2026-10-18 前後）に合わせてある
//
// npm test には入れない: wrangler dev と Chromium を起動し、1 回に 1〜2 分かかる。
import {spawn, execFileSync} from 'node:child_process';
import {mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {chromium} from 'playwright';

const here = p => new URL(p, import.meta.url).pathname;
const CF = here('..');
const OUT = process.env.E2E_OUT || join(tmpdir(), 'taguri-e2e');
const PORT = Number(process.env.E2E_PORT || 8797);
const BASE = `http://localhost:${PORT}`;      // パスキーは IP では使えない（RP ID がドメインでないと断られる）
const CHROME = process.env.E2E_CHROMIUM || '/opt/pw-browsers/chromium';
const STATE = mkdtempSync(join(tmpdir(), 'taguri-e2e-d1-'));
mkdirSync(OUT, {recursive: true});
const env = {...process.env, WRANGLER_SEND_METRICS: 'false', CI: '1'};
const wrangler = (...args) => execFileSync('npx', ['wrangler', ...args], {cwd: CF, env, encoding: 'utf8', maxBuffer: 64 << 20, stdio: ['ignore', 'pipe', 'pipe']});
const sql = command => JSON.parse(wrangler('d1', 'execute', 'taguri-demo', '--local', '--persist-to', STATE, '--json', '--command', command))[0].results;

// ---------------------------------------------------------------- 試験用のデータ
const PAST = [
  // 3 会場のツアー（劇場ごとに stage_id が違う）と、1 会場だけの公演
  ['710001', '旅の芝居', '旅の芝居', '2025-07-01', '2025-07-10', '劇場A', '劇団甲', '東京都', '[["出演","俳優甲"]]'],
  ['710002', '旅の芝居', '旅の芝居', '2025-08-01', '2025-08-03', '劇場B', '劇団甲', '大阪府', '[["出演","俳優甲"]]'],
  ['710003', '旅の芝居', '旅の芝居', '2025-08-20', '2025-08-24', '劇場E', '劇団甲', '愛知県', '[["出演","俳優甲"]]'],
  ['710010', '冬の物語', '冬の物語', '2024-01-05', '2024-01-20', '劇場D', '劇団丙', '東京都', '[["出演","俳優乙"]]'],
];
// 開幕リマインド用: 今日（日本時間）から 3 日後に開く、一覧（catalogue）だけにある公演
const jst = (days = 0) => new Date(Date.now() + 9 * 3600e3 + days * 86400e3).toISOString().slice(0, 10);
const SOON = {id: '990001', title: '近く開く芝居', date: jst(3), end: jst(10), venue: '劇場F', group: '劇団丁', cast: '俳優丙'};
// 取り込みの試験用のファイル（中身は作り物）
const ICS = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//taguri e2e//JA',
  // 一致する予定。VALARM の SUMMARY（別の題）は予定の題名に使わない
  'BEGIN:VEVENT', 'UID:e2e-1', 'DTSTART;TZID=Asia/Tokyo:20240110T180000', 'SUMMARY:観劇『冬の物語』', 'LOCATION:劇場D, 東京都',
  'BEGIN:VALARM', 'ACTION:DISPLAY', 'SUMMARY:舞台ひとつめ', 'DESCRIPTION:リマインダー', 'TRIGGER:-PT1H', 'END:VALARM', 'END:VEVENT',
  // 取り消した予定（STATUS:CANCELLED）は出さない
  'BEGIN:VEVENT', 'UID:e2e-2', 'DTSTART;TZID=Asia/Tokyo:20250702T190000', 'SUMMARY:旅の芝居', 'STATUS:CANCELLED', 'END:VEVENT',
  // 公演でない予定
  'BEGIN:VEVENT', 'UID:e2e-3', 'DTSTART:20250910T010000Z', 'SUMMARY:歯医者', 'END:VEVENT',
  'END:VCALENDAR', ''].join('\r\n');
const eml = (id, subject, body) => ['From: =?UTF-8?B?' + Buffer.from('チケットぴあ').toString('base64') + '?= <info@pia.co.jp>', 'To: a@example.com',
  `Subject: =?UTF-8?B?${Buffer.from(subject).toString('base64')}?=`, `Message-ID: <${id}@e2e.example>`, 'Date: Mon, 01 Jan 2024 10:00:00 +0900',
  'MIME-Version: 1.0', 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: base64', '', Buffer.from(body).toString('base64'), ''].join('\r\n');
const EMLS = [
  ['e2e-new.eml', eml('n1', '【チケットぴあ】購入完了のお知らせ', '公演名：冬の物語\n公演日：2024/01/15(月)\n開演時刻：13:00\n会場名：劇場D\n')],
  // もう記録してある回（旅の芝居 8/2）。「記録済み」と出て選べないはず
  ['e2e-dup.eml', eml('n2', '【チケットぴあ】購入完了のお知らせ', '公演名：旅の芝居\n公演日：2025/08/02(土)\n会場名：劇場B\n')],
];
function seed() {
  wrangler('d1', 'migrations', 'apply', 'taguri-demo', '--local', '--persist-to', STATE);
  const cat = JSON.parse(execFileSync('python3', [here('./screens/catalogue.py'), '--sql'], {encoding: 'utf8', maxBuffer: 64 << 20}));
  const rec = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 << 20}));
  const q = v => "'" + String(v).replaceAll("'", "''") + "'";
  const past = PAST.map(r => `INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people) VALUES(${r.map(q).join(',')});`);
  const soon = `INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(${[SOON.id, SOON.title, SOON.date, SOON.venue, 'https://stage.example/990001',
    JSON.stringify({end_date: SOON.end, group: SOON.group, fields: {'出演': SOON.cast}})].map(q).join(',')});`;
  // おすすめのカードの見た目を確かめるため、舞台ひとつめ（101）に長いあらすじ・題材・料金（同じ額の幅を含む）・公演日時を
  // 手で直した分（stage_override）として重ねる（起案者の指示 2026-10-18 のカードの 7 点）
  const ov = `INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES(${['101',
    '海辺の町で小さな食堂を営む家族の物語。父が倒れ、都会に出ていた長女が十年ぶりに戻ってくる。閉めるか続けるかで揺れる家族の前に、'
    + '父が昔書き残した献立帳が見つかる。献立帳をたどるうちに、長女は町の人たちと父の知られざる過去に出会っていく。笑って泣ける再生の物語。',
    JSON.stringify(['家族', '再生', '食堂']),
    JSON.stringify({fields: {'料金（1枚あたり）': '12,000円 ～ 12,000円\n【発売日】2026/09/01\nS席：12,000円\nA席：8,000円〜8,000円\nU-25：6,000円',
      // 11/3 の 18:00 は貸切の回（暦に「(貸)18:00」。起案者の指示 2026-10-18）
      'タイムテーブル': '11月1日(日) 13:00\n11月2日(月) 19:00\n11月3日(火) 13:00/18:00貸切'}}),
    '2026-10-18T00:00:00Z'].map(q).join(',')});`;
  // あらすじのハッシュタグの公演の一覧と、料金の明細を出さないカード（会場ごとに料金が違う 2 会場のツアー）を確かめるため、
  // 劇場の無い舞台（106）に題材「家族」・料金・貸切の回のある公演日時を重ね、同じツアーの 2 つめの会場（107、料金が違う）を
  // 索引とカードに足す（起案者の指示 2026-10-18 の写し: 2 会場・2 つ目の会場の暦の上に料金）
  const ov106 = `INSERT INTO stage_override(stage_id,synopsis,themes,info,updated_at) VALUES(${['106',
    '小さな町の劇団を舞台に、解散を前にした家族のような仲間たちの最後の一週間を描く喜劇。',
    JSON.stringify(['家族', '喜劇']),
    JSON.stringify({venue: '劇場Y', pref: '東京都', fields: {'料金（1枚あたり）': '12,500円(全席指定・税込)',
      'タイムテーブル': '12月1日(火) 19:00\n12月2日(水) 13:00/17:00貸切\n12月3日(木) 13:00'}}),
    '2026-10-18T00:00:00Z'].map(q).join(',')});`;
  const tour107 = [
    `INSERT INTO rec_card(ver,stage_id,html,title,tour,start,end,pref,gnz,blob,ws,synz) SELECT ver,'107',replace(html,'data-stage="106"','data-stage="107"'),title,tour,'2026-12-10','2026-12-12','大阪府',gnz,blob,ws,synz FROM rec_card WHERE stage_id='106';`,
    `INSERT INTO rec_stage(ver,stage_id,title,tkey,grp,tour,gkey,start,end,credits,entry) SELECT ver,'107',title,tkey,grp,tour,gkey,'2026-12-10','2026-12-12',credits,`
      + `json_set(entry,'$.theater','劇場Z','$.pref','大阪府','$.period','2026/12/10~2026/12/12','$.fields',json(${q(JSON.stringify({'料金（1枚あたり）': '9,800円(全席指定・税込)', 'タイムテーブル': '12月10日(木) 18:00\n12月11日(金) (貸切)13:00/18:00\n12月12日(土) 13:00'}))})) FROM rec_stage WHERE stage_id='106';`];
  const file = join(STATE, 'seed.sql');
  writeFileSync(file, [...cat.sql, ...rec.sql, ...past, soon, ov, ov106, ...tour107, "INSERT INTO venue_pref(venue,pref) VALUES('劇場F','東京都');"].join('\n'));
  wrangler('d1', 'execute', 'taguri-demo', '--local', '--persist-to', STATE, '--file', file);
}

// ---------------------------------------------------------------- 段の記録
const results = [];
let page, ctx, browser, current = null;
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function shot(name) {
  try { await page.screenshot({path: join(OUT, `${String(results.length).padStart(2, '0')}-${name}.png`), fullPage: true}); } catch {}
}
async function step(name, fn, opt = {}) {
  current = {name, ok: true, notes: [], errors: [], allowFailed: !!opt.allowFailed};
  const t0 = Date.now();
  try { await fn(current); } catch (e) { current.ok = false; current.notes.push('例外: ' + String(e.message || e).split('\n')[0]); }
  // 段の中で起きた JavaScript のエラー・コンソールのエラー・素の SyntaxError の文字は NG にする
  try {
    const text = await page.locator('body').innerText({timeout: 2000});
    if (/SyntaxError|Unexpected token|is not valid JSON|\[object Object\]|undefined is not|TypeError/.test(text)) current.errors.push('画面に素のエラー文: ' + text.match(/.{0,40}(SyntaxError|Unexpected token|is not valid JSON|\[object Object\]|undefined is not|TypeError).{0,40}/)[0]);
  } catch {}
  if (current.errors.length) current.ok = false;
  await shot(name.replace(/[^\p{L}\p{N}]+/gu, '_').slice(0, 40));
  current.ms = Date.now() - t0;
  delete current.allowFailed;
  results.push(current);
  console.log(`${current.ok ? 'OK' : 'NG'}  ${name}${current.notes.length ? ' — ' + current.notes.join(' / ') : ''}${current.errors.length ? ' — ' + current.errors.join(' / ') : ''}`);
  current = null;
}
const check = (cond, msg) => { if (!cond) throw new Error(msg); };
const note = msg => current.notes.push(msg);
// 画面の読み込みが終わるまで待つ（#content の .tg-loading が消える）
async function settle() {
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.locator('#content .tg-loading').waitFor({state: 'detached', timeout: 15000}).catch(() => {});
}
async function go(path) { await page.goto(BASE + path); await settle(); }
const content = () => page.locator('#content').innerText();
// 調べるための控え（画面の文と HTML）
// 写しを PC と電話の幅で撮る（見出し・説明・空のときの案内を目で確かめるため）
async function shotsBoth(name) {
  await page.screenshot({path: join(OUT, `${name}-pc.png`), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  await sleep(300);
  await page.screenshot({path: join(OUT, `${name}-phone.png`), fullPage: true});
  await page.setViewportSize({width: 1280, height: 900});
  await sleep(200);
}

async function dump(name) {
  try { writeFileSync(join(OUT, `dump-${name}.txt`), await content()); writeFileSync(join(OUT, `dump-${name}.html`), await page.locator('#content').innerHTML()); } catch {}
}
async function saidOf(scope) { return (await scope.locator('.said').first().innerText().catch(() => '')).trim(); }
async function waitSaid(scope, re, timeout = 10000) {
  const t0 = Date.now();
  let last = '';
  while (Date.now() - t0 < timeout) {
    last = (await scope.locator('.said').allInnerTexts().catch(() => [])).join(' ');
    if (re.test(last)) return last;
    await sleep(150);
  }
  throw new Error(`「${re.source}」が出ない（出ていたのは「${last}」）`);
}
function watch(p, who) {
  // 失敗した要求は、どの URL かを段の控えに書く（コンソールの「Failed to load resource」には URL が無い）
  p.on('response', r => { if (r.status() >= 400 && r.url().startsWith(BASE)) (current?.notes || orphan).push(`[${who}] ${r.status()} ${r.request().method()} ${r.url().slice(BASE.length).split('?')[0]}`); });
  p.on('requestfailed', r => { if (r.url().startsWith(BASE)) (current?.notes || orphan).push(`[${who}] 届かなかった要求 ${r.request ? '' : ''}${r.method()} ${r.url().slice(BASE.length).split('?')[0]}`); });
  p.on('pageerror', e => { const m = `[${who}] ページのエラー: ${e.message}`; (current?.errors || orphan).push(m); });
  p.on('console', m => {
    if (m.type() !== 'error') return;
    const t = m.text();
    // 外へ出る要求（ポスターの無い画像・止めた要求）は除く
    if (/Failed to load resource|net::ERR_FAILED/.test(t) && current?.allowFailed) return;
    (current?.errors || orphan).push(`[${who}] コンソールのエラー: ${t.slice(0, 200)}`);
  });
}
const orphan = [];

async function newUser(who) {
  const c = await browser.newContext({viewport: {width: 1280, height: 900}, locale: 'ja-JP', timezoneId: 'Asia/Tokyo'});
  const p = await c.newPage();
  watch(p, who);
  const cdp = await c.newCDPSession(p);
  await cdp.send('WebAuthn.enable');
  const {authenticatorId} = await cdp.send('WebAuthn.addVirtualAuthenticator', {options: {protocol: 'ctap2', transport: 'internal', hasResidentKey: true, hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true}});
  return {ctx: c, page: p, cdp, authenticatorId};
}

// ---------------------------------------------------------------- 起動
console.log(`D1: ${STATE}\n画面の写し: ${OUT}`);
seed();
const server = spawn('npx', ['wrangler', 'dev', '--ip', '127.0.0.1', '--port', String(PORT), '--persist-to', STATE], {cwd: CF, detached: true, stdio: ['ignore', 'pipe', 'pipe'], env});
let logs = '';
for (const s of [server.stdout, server.stderr]) s.on('data', d => { logs = (logs + d.toString()).slice(-20000); });
const users = {};
try {
  let ready = false;
  for (let i = 0; i < 90 && !ready; i++) {
    if (server.exitCode !== null) throw new Error('wrangler dev が止まった: ' + logs);
    try { ready = (await fetch(`http://127.0.0.1:${PORT}/login`)).ok; } catch {}
    if (!ready) await sleep(1000);
  }
  if (!ready) throw new Error('wrangler dev が立ち上がらない: ' + logs);
  browser = await chromium.launch({executablePath: CHROME});
  const A = await newUser('A');
  ({page, ctx} = A);
  users.A = A;
  await walkA(A);
  const B = await newUser('B');
  ({page, ctx} = B);
  await walkB(A, B);
  ({page, ctx} = A);
  await deleteA(A, B);
} finally {
  if (browser) await browser.close().catch(() => {});
  try { process.kill(-server.pid, 'SIGTERM'); } catch {}
  await sleep(1500);
  try { process.kill(-server.pid, 'SIGKILL'); } catch {}
  writeFileSync(join(OUT, 'results.json'), JSON.stringify({base: BASE, results, orphan}, null, 1));
  writeFileSync(join(OUT, 'wrangler.log'), logs);
  if (!process.env.E2E_KEEP) rmSync(STATE, {recursive: true, force: true});
}
const ng = results.filter(r => !r.ok);
console.log(`\n${results.length - ng.length} / ${results.length} 段が OK${orphan.length ? `（段の外のエラー ${orphan.length} 件）` : ''}`);
process.exitCode = ng.length ? 1 : 0;

// ================================================================ 利用者 A の道のり
async function walkA(A) {
  let code = '';
  await step('新規登録（同意なしでは始まらない）', async () => {
    await go('/');
    check(page.url().endsWith('/login'), 'ログインしていないのに /login へ行かない: ' + page.url());
    await page.click('#passkey-signup');
    const s = await page.locator('#status').innerText();
    check(/同意して始める/.test(s), '同意なしで押したときの案内が出ない: ' + s);
    check(await page.evaluate(() => document.activeElement?.id) === 'agree', '同意のチェックに焦点が移らない');
    // 状態の文は押したボタンの直下に出る（起案者の指示 2026-10-18「…対応する各ボタンの下に文章が出るようにして。」）
    // （パソコンの幅ではボタンが横に並ぶので、その列のすぐ下）
    check(await page.evaluate(() => { const b = document.querySelector('#passkey-signup'); return [b.nextElementSibling?.id, b.parentElement.nextElementSibling?.id].includes('status'); }), '案内が押したボタンの下に出ない');
    // 電話の幅でも写す（新規登録の欄と、ボタンの下の案内）
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: join(OUT, 'signup-need-agree-phone.png'), fullPage: true});
    await page.setViewportSize({width: 1280, height: 900});
  });
  await step('新規登録（パスキー・復旧コード）', async () => {
    await page.check('#agree');
    await page.click('#passkey-signup');
    await page.locator('#passkey-recovery:not([hidden])').waitFor({timeout: 15000});
    code = (await page.locator('#recovery-code').innerText()).trim();
    check(/^[0-9a-f]{64}$/.test(code), '復旧コードの形が違う: ' + code);
    await shot('recovery-code');
    await page.click('#recovery-done');
    await page.waitForURL(BASE + '/');
    await settle();
    check(/今週のあなたへのおすすめ/.test(await content()), '登録後におすすめの画面が出ない');   // 見出しは 2026-10-18 から「今週のあなたへのおすすめ…」
  });
  A.code = code;
  A.uid = sql('SELECT id FROM users')[0]?.id;

  await step('改定した規約への同意（キーボードの焦点）', async () => {
    sql("UPDATE users SET terms_version='2026-10-01'");
    await go('/rate');
    const pop = page.locator('.agreepop-box');
    await pop.waitFor({timeout: 10000});
    check(await page.evaluate(() => document.activeElement?.classList.contains('agreepop-box')), '開いたときに窓へ焦点が移らない');
    const seen = [];
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab');
      seen.push(await page.evaluate(() => { const a = document.activeElement; return (a.closest('.agreepop-box') ? 'in:' : 'OUT:') + (a.textContent || a.type || a.tagName).trim().slice(0, 12); }));
    }
    check(seen.every(x => x.startsWith('in:')), 'Tab で窓の外へ出る: ' + seen.join(' | '));
    await page.keyboard.press('Shift+Tab');
    check(await page.evaluate(() => !!document.activeElement.closest('.agreepop-box')), 'Shift+Tab で窓の外へ出る');
    check(await page.evaluate(() => document.querySelector('#content').closest('[inert]') !== null), '後ろの画面が inert になっていない');
    check(await page.locator('.agreepop-ok').isDisabled(), 'チェック前から「同意して続ける」が押せる');
    await shot('terms-modal');
    // チェックをキーボードで（Space）入れて、ボタンを Enter で押す
    await page.locator('.agreepop-check input').focus();
    await page.keyboard.press('Space');
    await page.locator('.agreepop-ok').focus();
    await page.keyboard.press('Enter');
    await pop.waitFor({state: 'detached', timeout: 5000});
    await go('/rate');
    await sleep(500);
    check(await page.locator('.agreepop').count() === 0, '同意したのに、開き直すとまた出る');
    const row = sql('SELECT terms_version FROM users')[0];
    note('D1 の terms_version: ' + row.terms_version);
  });

  // 使い始めでおすすめが無いときは、ワンポイント（3 つの始め方）だけを出し、選び方・絞り込みは出さない（起案者 2026-10-18）
  await step('初めてのおすすめ: ワンポイントだけ（選び方・絞り込みは出さない）', async () => {
    await go('/recommend');
    const t = await content();
    check(/おすすめを出すためのワンポイント/.test(t), 'ワンポイントが無い');
    check(/過去の観劇記録を2件以上追加する/.test(t) && /開幕リマインド」で興味あり・なしを回答する/.test(t), '3 つの始め方が無い');
    check(!/おすすめの選び方|表示の絞り込み/.test(t), '選び方・絞り込みが出ている');
    await page.setViewportSize({width: 390, height: 844});
    await sleep(300);
    await page.screenshot({path: join(OUT, 'recommend-start-phone.png'), fullPage: true});
    await page.setViewportSize({width: 1280, height: 900});
    await sleep(200);
  });

  // 興味あり・購入済の公演が 0 件のときは、ワンポイントと同じ形の絵の付いた案内（起案者の指示 2026-10-18）
  await step('空の一覧: 興味あり・購入済の公演は絵の付いた案内（PC・電話の幅）', async () => {
    await go('/recommend/interest');
    let t = await content();
    check(/「興味あり」の公演/.test(t) && !/追いかけている/.test(t), '興味ありの見出しが違う');
    check(/「おすすめ」または「開幕リマインド」、「探す」で「興味あり」と回答してください。/.test(t), '興味ありの案内の文が違う');
    check(await page.locator('section.eguide svg.tip-art').count() === 1, '興味ありの案内に絵が無い');
    check(await page.locator('section.eguide a[href^="/recommend/reminder"]').count() === 1, '案内の「開幕リマインド」がリンクでない');
    await shotsBoth('interest-empty');
    await go('/tickets');
    t = await content();
    check(/購入済の公演/.test(t) && !/購入済み公演 ──/.test(t), '購入済の公演の見出しが違う');
    check(/で「購入済」と回答してください。/.test(t) && /「観劇記録を追加」で購入済の公演を追加してください。/.test(t), '購入済の案内の文が違う');
    check(await page.locator('section.eguide a[href^="/register"]').count() === 1, '案内の「観劇記録を追加」がリンクでない');
    await shotsBoth('tickets-empty');
  });

  await step('観劇記録を手で 1 件足す', async () => {
    await go('/register');
    const g = page.locator('.add-work');
    await page.fill('#w-title', '手で足した芝居');
    await page.fill('#w-date', '2026-09-20');
    await page.fill('#w-time', '19:00');
    await page.fill('#w-venue', '劇場Z');
    const reload = page.waitForEvent('load', {timeout: 15000});
    await g.locator('button[data-add-work]').click();
    await waitSaid(g, /登録しました/);
    await reload;
    await settle();
    await go('/rate/unrated');
    await dump('unrated-1');
    check(/手で足した芝居/.test(await content()), '未評価に出ない');
    const w = sql("SELECT title, first_date, time, venue FROM works WHERE title='手で足した芝居'");
    check(w.length === 1 && w[0].first_date === '2026-09-20' && w[0].time === '19:00' && w[0].venue === '劇場Z', 'D1 の行が違う: ' + JSON.stringify(w));
  });

  await step('探す → 過去の公演（ツアー）を「観た」で足す・別の日・同じ日の別の回', async () => {
    await go('/search?q=' + encodeURIComponent('旅の芝居'));
    const li = page.locator('.pastrow').first();
    await li.waitFor();
    await dump('search-past');
    await li.locator('[data-past=seen]').click();
    const form = li.locator('.past-seen');
    check(await form.isVisible(), '「観た」で欄が開かない');
    const add = async (date, time) => {
      await form.locator('input[name=date]').fill(date);
      await form.locator('input[name=date]').dispatchEvent('change');
      if (time) await form.locator('input[name=time]').fill(time);
      await form.locator('[data-past=seen-save]').click();
    };
    await add('2025-08-02', '');
    await waitSaid(li, /8\/2 を観劇記録に追加しました/);
    await add('2025-08-21', '13:00');
    await waitSaid(li, /8\/21 13:00 を観劇記録に追加しました/);
    await add('2025-08-21', '18:00');
    await waitSaid(li, /8\/21 18:00 を観劇記録に追加しました/);
    await add('2025-08-21', '18:00');
    const dup = await waitSaid(li, /できませんでした|もうある/);
    note('同じ日・同じ開演の 4 回目: 「' + dup + '」');
    await add('2025-07-15', '');
    note('ツアーの合間の日: 「' + (await saidOf(li)) + '」');
    const rows = sql("SELECT work_key, first_date, time, stage_id, venue FROM works WHERE title='旅の芝居' ORDER BY work_key");
    note('D1: ' + rows.map(r => `${r.first_date} ${r.time || '-'} ${r.stage_id} ${r.venue}`).join(' / '));
    check(rows.length === 3, '3 回分の記録にならない: ' + rows.length);
    check(rows.find(r => r.first_date === '2025-08-02')?.stage_id === '710002', '8/2 が劇場B（710002）に結び付かない');
    check(rows.filter(r => r.first_date === '2025-08-21').every(r => r.stage_id === '710003'), '8/21 が劇場E（710003）に結び付かない');
  }, {allowFailed: true});   // 4 回目は断られる（400）はずなので、その要求の失敗はコンソールに出てよい

  const KEY = '手で足した芝居#2026-09-20';
  const row = () => page.locator(`.rec-row:has([data-note="${KEY}"]), .wait:has([data-note="${KEY}"])`).first();
  await step('星で評価する（4 つ）', async () => {
    await go('/rate/unrated');
    const r = row();
    await r.locator('button.star[data-v="4/5"]').click();
    await waitSaid(r, /記録しました/);
    check((await r.locator('button.star.on').count()) === 4, '押した所まで星が付かない');
    await go('/rate');
    await dump('rate-1');
    check(/付けた 1 件/.test(await content()), '評価一覧に出ない');
    const v = sql(`SELECT verdict FROM works WHERE work_key='${KEY}'`)[0]?.verdict;
    check(v === '4/5', 'D1 の評価が違う: ' + v);
    check((await row().locator('button.star.on').count()) === 4, '開き直すと星が 4 つでない');
  });

  // 星の右端の ✕ と、詳細の 5 段階・項目を外す ✕（起案者の指示 2026-10-18「『評価しない』のボタンじゃなくて、星の右端に✕ボタンを
  // つけることでnullにできるようにして」「最低限5段階くらいほしい」「なかったときは✕で要素を消せるようにしてほしい」）
  await step('詳細を 5 段階で付け、無い項目を ✕ で外して戻す', async () => {
    await go('/rate');
    const r = row();
    const box = r.locator('details.asp');
    check(await box.isVisible(), '評価を付けた行に詳細が出ない');
    if (!(await box.evaluate(b => b.open))) await box.locator('summary').click();
    const asp = () => sql(`SELECT aspects FROM works WHERE work_key='${KEY}'`)[0]?.aspects;
    // 押して、/api/rate の返事を待ってから D1 を読む
    const act = async (fn, want, what) => {
      const res = page.waitForResponse(x => x.url().endsWith('/api/rate') && x.request().method() === 'POST', {timeout: 10000});
      await fn();
      check((await res).ok(), what + ': 保存に失敗した');
      const got = asp();
      check(got === want, `${what}: D1 の詳細が「${got}」`);
    };
    check((await box.locator('.aspsl').first().getAttribute('max')) === '2' && (await box.locator('.aspsl').first().getAttribute('min')) === '-2', 'つまみが 5 段階でない');
    await act(() => box.locator('.aspsl[data-a="acting"]').fill('2'), '++acting', '好き');
    check((await box.locator('.aspr[data-a="acting"] .aspv').innerText()) === '好き', '段階の言葉が出ない');
    await act(() => box.locator('.aspsl[data-a="price"]').fill('-1'), 'price,++acting', 'やや好みではない');
    await act(() => box.locator('button.aspx[data-na="music"]').click(), 'price,++acting,~music', '歌・音楽を外す');
    await act(() => box.locator('button.aspx[data-na="dance"]').click(), 'price,++acting,~music,~dance', 'ダンスを外す');
    check(!(await box.locator('.aspr[data-a="music"]').isVisible()), '外した項目が残っている');
    check(/好き: 演技・出演／やや好みではない: 値段/.test(await box.locator('.asps').innerText()), '要約が違う: ' + (await box.locator('.asps').innerText()));
    await r.screenshot({path: join(OUT, 'row-aspects-5.png')}).catch(() => {});
    // 電話の幅（375px）でも、項目名・つまみ・言葉・✕ が横にはみ出さない
    const wide = page.viewportSize();
    await page.setViewportSize({width: 375, height: 800});
    await sleep(300);
    await r.screenshot({path: join(OUT, 'row-aspects-5-phone.png')}).catch(() => {});
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    check(over <= 0, `電話の幅で横にはみ出す: ${over}px`);
    await page.setViewportSize(wide);
    await go('/rate');
    const box2 = row().locator('details.asp');
    if (!(await box2.evaluate(b => b.open))) await box2.locator('summary').click();
    check(!(await box2.locator('.aspr[data-a="dance"]').isVisible()), '開き直すと外した項目が戻っている');
    check((await box2.locator('.aspsl[data-a="acting"]').inputValue()) === '2', '開き直すと 好き が残っていない');
    await act(() => box2.locator('button.aspadd[data-add="dance"]').click(), 'price,++acting,~music', 'ダンスを戻す');
    check(await box2.locator('.aspr[data-a="dance"]').isVisible(), '戻した項目が出ない');
    note('D1: ' + asp());
  });

  await step('星の右端の ✕ で評価を消し、付け直す', async () => {
    await go('/rate');
    const r = row();
    const x = r.locator('button.gclr');
    check(await x.isVisible(), '評価を付けた行に ✕ が無い');
    check((await x.getAttribute('aria-label')) === '評価を消す(未評価に戻す)', '✕ に aria-label が無い');
    await r.locator('.rb').screenshot({path: join(OUT, 'row-stars-x.png')}).catch(() => {});
    await x.click();
    await waitSaid(r, /評価を消しました/);
    check((await r.locator('button.star.on').count()) === 0, '✕ で星が消えない');
    check(!(await x.isVisible()), '消したあとも ✕ が出ている');
    const v = sql(`SELECT verdict, aspects FROM works WHERE work_key='${KEY}'`)[0];
    check(v.verdict === null, 'D1 の評価が消えない: ' + v.verdict);
    check(v.aspects === 'price,++acting,~music', '評価を消すと詳細まで消えた: ' + v.aspects);
    await sleep(700);
    check(!(await r.locator('details.asp').isVisible()), '評価を消しても詳細が出ている');
    await go('/rate/unrated');
    check(await row().isVisible(), '消した記録が未評価に出ない');
    check(!(await row().locator('button.gclr').isVisible()), '未評価の行に ✕ が出ている');
    await row().locator('button.star[data-v="4/5"]').click();
    await waitSaid(row(), /記録しました/);
    check(await row().locator('button.gclr').isVisible(), '付け直しても ✕ が出ない');
    check(sql(`SELECT verdict FROM works WHERE work_key='${KEY}'`)[0]?.verdict === '4/5', '付け直した評価が D1 に無い');
  });

  await step('感想を書く → 開き直して残っている', async () => {
    await go('/rate');
    const r = row();
    await r.locator('[data-note-open]').first().click();
    // まだ書いていない記録でも、空の文の上でそのまま書く形（textarea は隠れたまま）
    const el = r.locator('.int[contenteditable]');
    await el.waitFor();
    await page.keyboard.type('最初に書いた感想。');
    await el.blur();
    await waitSaid(r, /感想を保存しました/);
    await go('/rate');
    check(/最初に書いた感想。/.test(await row().innerText()), '開き直すと感想が無い');
  });

  await step('感想を書き直す（その場で編集）・保存の失敗から送り直す', async () => {
    await go('/rate');
    const r = row();
    // 通信を止めてから書き直す
    await page.route('**/api/note', route => route.abort());
    await r.locator('[data-note-open]').first().click();
    const el = r.locator('.int[contenteditable]');
    await el.waitFor();
    await page.keyboard.press('End');
    await page.keyboard.type('書き足した。');
    await el.blur();
    const fail = await waitSaid(r, /できませんでした/);
    note('止めたとき: 「' + fail.trim() + '」');
    check(/書いた文は残しています/.test(fail), '書いた文が残ると言わない');
    check(/書き足した。/.test(await r.locator('.int').innerText()), '失敗で文が巻き戻った');
    await page.unroute('**/api/note');
    await sleep(700);   // 「書き終える」の直後 0.6 秒は、押しても書き始めない（editInPlace）
    // 書き直さずにもう一度開いて離れる → 送り直す（#83）
    await r.locator('[data-note-open]').first().click();
    await r.locator('.int[contenteditable]').waitFor();
    await r.locator('.int[contenteditable]').blur();
    await waitSaid(r, /感想を保存しました/);
    await go('/rate');
    check(/最初に書いた感想。書き足した。/.test(await row().innerText()), '送り直した感想が開き直すと無い: ' + (await row().innerText()).slice(0, 200));
    const n = sql(`SELECT note_impression FROM works WHERE work_key='${KEY}'`)[0]?.note_impression;
    check(n === '最初に書いた感想。書き足した。', 'D1 の感想が違う: ' + n);
  }, {allowFailed: true});

  await step('手で足す欄の候補（公演一覧）から選んで足す', async () => {
    for (const [q, title, sid, date] of [['終わった', '終わった舞台', '103', '2026-08-05'], ['一日だけ', '一日だけの<舞台> & "夜"', '104', '2026-09-05']]) {
      await go('/register');
      const g = page.locator('.add-work');
      await page.locator('#w-title').pressSequentially(q, {delay: 30});
      const pick = page.locator('#sug .sug-row.stage').filter({hasText: title}).locator('[data-pick]');
      await pick.waitFor({timeout: 10000});
      await pick.click();
      check(await page.inputValue('#w-title') === title, '候補の題名が欄に入らない: ' + await page.inputValue('#w-title'));
      check(await page.inputValue('#w-stage') === sid, '候補の公演 id が入らない');
      note(`${title}: 候補を選ぶと観た日「${await page.inputValue('#w-date')}」・劇場「${await page.inputValue('#w-venue')}」`);
      await page.fill('#w-date', date);
      const reload = page.waitForEvent('load', {timeout: 15000});
      await g.locator('button[data-add-work]').click();
      await waitSaid(g, /登録しました/);
      await reload;   // 材料を取り終えたら（waitJob）画面を読み込み直す
      await settle();
      const w = sql(`SELECT stage_id FROM works WHERE first_date='${date}'`);
      check(w.length === 1 && w[0].stage_id === sid, `${title} が公演 ${sid} に結び付かない: ` + JSON.stringify(w));
    }
  });

  await step('ほかの記録も評価する（おすすめの材料）', async () => {
    await go('/rate/unrated');
    for (const [t, v] of [['終わった舞台', '5/5'], ['一日だけ', '1/5']]) {
      const r = page.locator('.rec-row, .wait').filter({hasText: t}).first();
      await r.locator(`button.star[data-v="${v}"]`).click();
      await waitSaid(r, /記録しました/);
    }
    await go('/rate/unrated');
    for (const [i, v] of [[0, '5/5'], [1, '5/5'], [2, '4/5']]) {
      const r = page.locator('.rec-row, .wait').filter({hasText: '旅の芝居'}).nth(0);
      await r.locator(`button.star[data-v="${v}"]`).click();
      await waitSaid(r, /記録しました/);
      await go('/rate/unrated');
    }
    const n = sql("SELECT count(*) n FROM works WHERE verdict IS NOT NULL")[0].n;
    check(n === 6, '評価の数が 6 でない: ' + n);
  });

  // 起案者の指示 2026-10-18（おすすめのカードの 7 点）: 理由の作品名は 2 つまで・札は「人物」「形式」で Zen丸ゴシック、
  // 発売の札は値段帯のすぐ下、枠線 2px、同じ額の幅は 1 つの額、あらすじの続きは地の色なしで題材のハッシュタグ、日程と暦の間をあける
  await step('今週のおすすめ: カードの見た目（理由・発売の札・料金・あらすじのハッシュタグ・暦。PC・電話の幅）', async () => {
    await go('/');
    const card = page.locator('.ticket.recommend[data-stage="101"]');
    await card.waitFor({timeout: 10000});
    const nets = await card.locator('.rs .net').allInnerTexts();
    check(nets.length && nets.every(t => ['人物', '形式', '感想'].includes(t.trim())), '理由の札: ' + nets.join(','));
    const works = await card.locator('.rs .n').allInnerTexts();
    check(works.every(t => (t.match(/『/g) || []).length <= 2), '理由の作品名が 3 つ以上: ' + works.join(' / '));
    check(!works.some(t => /お気に入り・興味ありの公演から/.test(t)), '「（お気に入り・興味ありの公演から）」が残っている');
    check(works.length && works.every(t => /[(（].+[)）]/.test(t)), '括弧の説明の無い理由の行: ' + works.join(' / '));
    const font = await card.locator('.rs .net').first().evaluate(n => [getComputedStyle(n).fontFamily, getComputedStyle(n).fontWeight]);
    check(/Zen Maru Gothic/.test(font[0]) && font[1] === '700', '理由の札の字: ' + font.join(' '));
    const order = await card.locator('.main').evaluate(m => [...m.children].map(n => n.className.split(' ')[0]).join(','));
    check(/lprice,sale/.test(order), '発売の札が値段帯のすぐ下にない: ' + order);
    const bw = await card.evaluate(t => [t.querySelector('.sale .pill'), t.querySelector('.pcol .sitebtn, .sitelink')].filter(Boolean).map(n => getComputedStyle(n).borderTopWidth));
    check(bw[0] === '2px' && (bw.length < 2 || bw[1] === '2px'), '発売の札の枠線: ' + bw.join(','));
    const price = await card.locator('.lprice').innerText();
    check(!/12,000円\s*[~〜～]\s*12,000円/.test(price) && /12,000円/.test(price), '同じ額の幅が残っている: ' + price.replace(/\s+/g, ' '));
    // 金額だけの行（幅を 1 つにした「12,000円」）は、同じ額の券種つきの行（S席 12,000円）があれば出さない（起案者の指示 2026-10-18
    // 「『7,000円\n全席指定 7,000円』ってなってる公演があるけど『全席指定 7,000円』でよい」）
    const prow = (await card.locator('.lprice .lp-row').allInnerTexts()).map(t => t.replace(/\s+/g, ' ').trim());
    check(!prow.includes('12,000円') && prow.some(t => /S席 ?12,000円/.test(t)), '同じ額の行が 2 度出る: ' + prow.join(' / '));
    note('料金: ' + price.replace(/\s+/g, ' ') + ' / 並び: ' + order + ' / 枠線: ' + bw.join(','));
    // 写しの間だけ、使い方の案内（.tgt-root）を隠す（カードに重なるため。押さないので次の段には響かない）
    const hideTour = on => page.evaluate(v => document.querySelectorAll('.tgt-root').forEach(n => { n.style.visibility = v ? 'hidden' : ''; }), on);
    await hideTour(true);
    await page.setViewportSize({width: 390, height: 844});
    await card.scrollIntoViewIfNeeded();
    await card.screenshot({path: join(OUT, 'card-recommend-phone-closed.png')}).catch(() => {});
    // 開く: 料金の詳細・あらすじの続き。日程の暦は会場が 1 つなら開いている
    await card.locator('details.lprice > summary').click().catch(() => {});
    await card.locator('details.lsynmore > summary').click();
    const tags = await card.locator('.lsynmore .lsyntag').allInnerTexts();
    check(tags.join(' ') === '#家族 #再生 #食堂', 'あらすじのハッシュタグ: ' + tags.join(' '));
    const bg = await card.locator('details.lsynmore').evaluate(n => getComputedStyle(n).backgroundColor);
    check(bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent', '開いたあらすじに地の色: ' + bg);
    const gap = await card.evaluate(t => { const b = t.querySelector('.tourfull.v2 details[open] > .tf-body'); return b ? getComputedStyle(b).marginTop : 'なし'; });
    check(gap === '6px', '日程と暦の間: ' + gap);
    note('ハッシュタグ: ' + tags.join(' ') + ' / 暦の上: ' + gap);
    await card.screenshot({path: join(OUT, 'card-recommend-phone-open.png')}).catch(() => {});
    await page.setViewportSize({width: 1280, height: 900});
    await card.scrollIntoViewIfNeeded();
    await card.screenshot({path: join(OUT, 'card-recommend-pc-open.png')}).catch(() => {});
    await hideTour(false);
  });

  // 起案者の指示 2026-10-18: あらすじのハッシュタグ → その題材の公演の一覧／暦の貸切は「(貸)17:00」で升の中で折り返さない／
  // 値段と発売の札は本文の列（料金の明細の無いカードも）・札の ↗ は折り返さない／ヘルプはカードの枠の外の右上に小さく
  await step('あらすじのハッシュタグ → 題材の公演の一覧（2 会場で料金の明細の無いカード・暦の貸切・右上のヘルプ。PC・電話の幅）', async () => {
    await go('/');
    const card = page.locator('.ticket.recommend[data-stage="101"]');
    await card.waitFor({timeout: 10000});
    const kas = await card.locator('.ttb .tm.kas').allInnerTexts();
    check(kas.map(t => t.trim()).join(',') === '(貸)18:00', '暦の貸切の回: ' + kas.join(','));
    // ヘルプ（？）は枠の外の右上の角: 右端・上端が枠の外に出て、見た目は 24px ほど、押せる広さは 44px
    const helpAt = () => card.evaluate(t => {
      const a = t.getBoundingClientRect(), btn = t.querySelector(':scope > .fixq .fixq-open');
      if (!btn) return null;
      const b = btn.getBoundingClientRect(), hit = getComputedStyle(btn, '::after');
      return {right: Math.round(b.right - a.right), top: Math.round(b.top - a.top), w: Math.round(b.width), hit: hit.width};
    });
    const hp = await helpAt();
    check(hp && hp.right > 0 && hp.top < 0 && hp.w <= 26 && hp.hit === '44px', 'ヘルプの位置: ' + JSON.stringify(hp));
    note('ヘルプ: ' + JSON.stringify(hp));
    const hideTour = on => page.evaluate(v => document.querySelectorAll('.tgt-root').forEach(n => { n.style.visibility = v ? 'hidden' : ''; }), on);
    // カードの写しは、枠の外のヘルプが入るように周りを 16px 広げて撮る
    const around = async (loc, path) => { await loc.scrollIntoViewIfNeeded(); const b = await loc.boundingBox(); if (b) await page.screenshot({path, clip: {x: Math.max(0, b.x - 16), y: Math.max(0, b.y - 16), width: b.width + 32, height: b.height + 24}}).catch(() => {}); };
    await card.locator('details.lsynmore > summary').click();
    const link = card.locator('.lsynmore a.lsyntag', {hasText: '#家族'});
    check(await link.count() === 1, 'ハッシュタグがリンクになっていない');
    await link.click();
    await page.waitForURL(/\/recommend\/tag\?w=/, {timeout: 10000});
    await settle();
    check(/#家族\s*の公演/.test(await content()), '題材の公演の画面が出ない: ' + (await content()).slice(0, 80));
    const sids = await page.locator('#content article.ticket').evaluateAll(as => as.map(a => a.dataset.stage));
    check(sids.includes('101') && sids.includes('106') && !sids.includes('107'), '一覧の公演: ' + sids.join(','));
    note('#家族 の一覧: ' + sids.join(','));
    // 2 会場で料金の違うカード（料金の明細なし）: 値段の 1 行と発売の札は本文の列に、札はその下に。ポスターの下の列には無い
    const c = page.locator('#content .ticket[data-stage="106"]');
    const order = await c.locator('.main').evaluate(m => [...m.children].map(n => n.className.split(' ')[0]).join(','));
    check(/lprice,sale/.test(order), '値段と発売の札の並び: ' + order);
    check(await c.locator('.pcol .sale, .pcol .lprice, .pcol .yen').count() === 0, '値段・発売の札がポスターの下の列に残る');
    const yen = (await c.locator('.main > .lprice.lyen').innerText()).trim();
    check(/12,500円|9,800円/.test(yen), '値段の行: ' + yen);
    check(await c.locator('.tourfull .tf-row').count() === 2, '日程の会場が 2 つでない');
    note('106 の並び: ' + order + ' / 値段: ' + yen.replace(/\s+/g, ' '));
    // 「ほか 1 会場」を押すと、ほかの会場（劇場Z・12/10〜12/12）が開く。日程の行に「詳細」の字は無い（起案者の指示 2026-10-18）
    const more = c.locator('.meta .mvmore');
    check(await more.count() === 1 && !(await c.locator('.meta .mvlist').isVisible()), '「ほか n 会場」の押し口が無いか、最初から開いている');
    await more.click();
    const mv = (await c.locator('.meta .mvlist').innerText()).replace(/\s+/g, ' ').trim();
    check(/劇場Z/.test(mv) && /12\/10〜12\/12/.test(mv) && !/劇場Y/.test(mv), 'ほかの会場の一覧: ' + mv);
    check(await more.getAttribute('aria-expanded') === 'true', 'aria-expanded が true にならない');
    check(await c.locator('.tf-more').count() === 0 && !/詳細/.test(await c.locator('.tourfull').innerText()), '日程の行に「詳細」が残る');
    // 料金はどこでも同じ箇条書き（.pblock .plist li）。表（.ptb）は使わない
    check(await c.locator('.ptb').count() === 0 && await c.locator('.tf-price .plist li').count() >= 1 && await c.locator('.main > .lprice .plist li').count() === 1, '料金が箇条書きでない');
    note('ほかの会場: ' + mv);
    const lines = el => el.evaluate(n => { const r = n.getClientRects(); return [r.length, Math.round(n.getBoundingClientRect().height), parseFloat(getComputedStyle(n).lineHeight) || 0]; });
    await hideTour(true);
    for (const [w, h, tag] of [[1280, 900, 'pc'], [390, 844, 'phone']]) {
      await page.setViewportSize({width: w, height: h});
      // 発売の札（「発売日不明 ↗」など）は 1 行
      const pl = await lines(c.locator('.sale .pill').first());
      check(pl[0] === 1, `${tag}: 発売の札が折り返す: ` + pl.join(','));
      // 貸切の回は升の中で 1 行（はみ出さない）
      const cells = await c.locator('.ttb .tm.kas').evaluateAll(ns => ns.map(n => { const td = n.closest('td'); return {t: n.textContent, rects: n.getClientRects().length, w: Math.round(n.scrollWidth), cw: Math.round(td.clientWidth)}; }));
      check(cells.length && cells.every(x => x.rects === 1 && x.w <= x.cw), `${tag}: 暦の貸切の回: ` + JSON.stringify(cells));
      note(`${tag}: 貸切の升 ` + cells.map(x => `${x.t} ${x.w}/${x.cw}px`).join(' '));
      // 料金の箇条書きの各行は 1 行（券種・金額が折り返さない）。おすすめのカード（101）の明細も同じ形
      const pls = await page.locator('#content .plist li:visible').evaluateAll(ns => ns.map(n => { const lh = parseFloat(getComputedStyle(n).lineHeight) || 19; return {t: n.textContent.trim(), one: n.getBoundingClientRect().height < lh * 1.6}; }));
      check(pls.length && pls.every(x => x.one), `${tag}: 料金の行が折り返す: ` + JSON.stringify(pls.filter(x => !x.one)));
      await page.screenshot({path: join(OUT, `tag-list-${tag}.png`), fullPage: true}).catch(() => {});
      await around(c, join(OUT, `card-tag-tour-${tag}.png`));
    }
    await page.setViewportSize({width: 1280, height: 900});
    await go('/');
    await hideTour(true);   // 開き直すと使い方の案内がまた出るので、写しの間だけ隠し直す
    await around(page.locator('.ticket.recommend[data-stage="101"]'), join(OUT, 'card-recommend-help-pc.png'));
    await page.setViewportSize({width: 390, height: 844});
    await around(page.locator('.ticket.recommend[data-stage="101"]'), join(OUT, 'card-recommend-help-phone.png'));
    await page.setViewportSize({width: 1280, height: 900});
    await hideTour(false);
  });

  await step('今週のおすすめ: 興味なし → 押し直して興味あり', async () => {
    await go('/');
    const card = page.locator('.ticket.recommend[data-stage="101"]');
    await card.waitFor({timeout: 10000});
    note('理由: ' + (await card.locator('.rs').allInnerTexts()).map(t => t.replace(/\s+/g, ' ').trim()).join(' / '));
    await card.locator('button[data-v="nointerest"]').click();
    await waitSaid(card, /記録しました/);
    check(await card.locator('.nn').isVisible(), '興味なしのあとに「見送った理由」の欄が出ない');
    await card.locator('button[data-v="interest"]').click();
    await waitSaid(card, /記録しました/);
    const r = sql("SELECT stage_id, interest, owned, source FROM reaction");
    note('D1 reactions: ' + JSON.stringify(r));
    await go('/recommend/interest');
    check(/舞台ひとつめ/.test(await content()), '興味ありの一覧に出ない');
    // 興味ありのカードの見た目（PC・電話の幅）。発売の札は値段帯のすぐ下（起案者の指示 2026-10-18）
    const ic = page.locator('.ticket.interest[data-stage="101"]');
    check(/lprice,sale/.test(await ic.locator('.main').evaluate(m => [...m.children].map(n => n.className.split(' ')[0]).join(','))), '興味ありのカードで発売の札が値段帯の下にない');
    const hide = on => page.evaluate(v => document.querySelectorAll('.tgt-root').forEach(n => { n.style.visibility = v ? 'hidden' : ''; }), on);
    await hide(true);
    await ic.screenshot({path: join(OUT, 'card-interest-pc.png')}).catch(() => {});
    await page.setViewportSize({width: 390, height: 844});
    await ic.screenshot({path: join(OUT, 'card-interest-phone.png')}).catch(() => {});
    await page.setViewportSize({width: 1280, height: 900});
    await hide(false);
    await go('/');
    check(await page.locator('.ticket.recommend[data-stage="101"]').count() === 0, '答えた公演がおすすめに残る');
  });

  await step('お気に入り: 名前を足す・外す', async () => {
    await go('/recommend/favourites');
    const g = page.locator('.fav-add');
    for (const [kind, name] of [['人', '俳優乙'], ['団体', '劇団ナシ']]) {
      // 欄は畳んだ「登録した名前」の中。足したあと読み込み直しても開いたまま（#names）
      if (!(await page.locator('details#names').getAttribute('open') !== null)) await page.locator('details#names > summary').click();
      await page.selectOption('#fav-kind', kind);
      await page.fill('#fav-name', name);
      const reload = page.waitForEvent('load', {timeout: 15000});
      await g.locator('button[data-fav="add"]').click();
      await waitSaid(g, /登録しました/);
      await reload; await settle();
    }
    await dump('favourites-2');
    const t = await content();
    check(/俳優乙/.test(t) && /劇団ナシ/.test(t), '足した名前が出ない');
    check(/舞台ふたつめ/.test(t), '俳優乙の公演（舞台ふたつめ）がお気に入りに出ない');
    check(await page.locator('details#names').getAttribute('open') !== null, '足したあと「要素を登録」が畳まれる');
    // 見出し・説明・札の形・並べ替えの位置（起案者の指示 2026-10-18）
    check(/^お気に入り$/.test((await page.locator('h1').first().innerText()).trim()), 'お気に入りの見出しが「お気に入り」だけでない');
    check(/お気に入りに追加することで情報の追跡ができます。/.test(t) && !/観ると決めたら、公式サイトで券を買って|すべてを表示しています/.test(t), 'お気に入りの説明の文が違う');
    check((await page.locator('details#names .tag[data-name="俳優乙"] .tgn').innerText()).trim() === '#人「俳優乙」', '札が「#人「俳優乙」」の形でない');
    check(/要素を登録/.test(await page.locator('details#names > summary').innerText()), '箱の名前が「要素を登録」でない');
    const below = await page.evaluate(() => {
      const nav = document.querySelector('nav.idx[aria-label="月で切り替える"]'), f = document.querySelector('form.sortf');
      return Boolean(nav && f && (nav.compareDocumentPosition(f) & Node.DOCUMENT_POSITION_FOLLOWING));
    });
    check(below, '並べ替えが月のタブより下にない');
    await shotsBoth('favourites');
    const tag = page.locator('.tag[data-name="劇団ナシ"]');
    const reload = page.waitForEvent('load', {timeout: 15000});
    await tag.locator('button[data-fav="remove"]').click();
    await reload; await settle();
    check(!/劇団ナシ/.test(await content()), '外した名前が残る');
    const f = JSON.parse(sql("SELECT value FROM app_setting WHERE key='declared'")[0]?.value || '{}');
    note('D1 app_setting.declared: ' + JSON.stringify(f));
    check(JSON.stringify(f['人']) === '["俳優乙"]' && !(f['団体'] || []).length, 'D1 のお気に入りが違う');
    // おすすめの理由の文（起案者の指摘 2026-10-18「堂本光一と登録したら『好きな諸鍛冶裕太と同じ公演に関わる人)』と出た」）。
    // 登録していない人を「好きな」と書かない。カッコは開きと閉じがそろう（全角のまま書き、halfwidth.js が半角にする）
    await go('/');
    await dump('home-after-favourite');
    const why = (await page.locator('li.rs').allInnerTexts().catch(() => [])).map(t => t.replace(/\s+/g, ' ').replace(/✕/g, '').trim());
    note('おすすめの理由: ' + why.join(' / '));
    check(!why.some(t => /好きな/.test(t) && !/好きな俳優乙/.test(t)), '登録していない人が「好きな」と出る');
    check(why.every(t => (t.match(/[(（]/g) || []).length === (t.match(/[)）]/g) || []).length), '理由のカッコの数が合わない');
    const first = page.locator('.ticket.recommend').first();
    if (await first.count()) await first.screenshot({path: join(OUT, 'reasons-after-favourite.png')}).catch(() => {});
  });

  await step('開幕リマインド: 近く開く公演に興味あり', async () => {
    await go('/recommend/reminder');
    await dump('reminder');
    // 開く日ごとに畳んである（details.dgday）。開いて、その行の三択を押す
    const day = page.locator('details.dgday').filter({has: page.locator(`[data-stage="${SOON.id}"]`)});
    await day.locator('> summary').click();
    const card = page.locator(`li.dgli[data-stage="${SOON.id}"]`);
    await card.locator('button[data-v="interest"]').click();
    await waitSaid(card, /記録しました/);
    const r = sql(`SELECT interest, source FROM reaction WHERE stage_id='${SOON.id}'`);
    note('D1: ' + JSON.stringify(r));
    check(r[0]?.interest === 1, 'D1 に興味ありが無い');
    await go('/recommend/interest');
    await dump('interest');
    const t = await content();
    check(/近く開く芝居/.test(t), '興味ありの一覧に出ない');
    note('一覧の「どこから」: ' + ((t.match(/開幕リマインド[^\n]{0,20}/) || ['（開幕リマインドの文字なし）'])[0]));
  });

  // 答えた行は「回答を直す」だけ、押すと三択（興味ありを含む）が出る。パソコンと電話の幅の写しも撮る
  await step('開幕リマインド: 答えた行は「回答を直す」だけ（パソコン・電話の幅）', async () => {
    await go('/recommend/reminder');
    for (const d of await page.locator('details.dgday:not([open]) > summary').all()) await d.click();
    const card = page.locator(`li.dgli[data-stage="${SOON.id}"]`);
    check(await card.locator('button[data-btns-open]').isVisible(), '「回答を直す」が無い');
    await page.screenshot({path: join(OUT, 'reminder-pc.png'), fullPage: true});
    // 見出し・前置きの 1 文・件数の 1 行（週のタブの下）・「直近の観劇予定」の枠なし（起案者の指示 2026-10-18）
    const rt = await content();
    check(/開幕リマインドでは、おすすめやお気に入りにかかわらず、今週・来週開幕予定の公演を全件掲載しています。/.test(rt) && !/見逃していませんか|直近の観劇予定|好みに関係なく/.test(rt), '開幕リマインドの文が違う');
    check(/に開幕する公演 ︰ \d+ 件/.test(rt), '「〇〜〇に開幕する公演 ︰ N 件」の形でない');
    check(await page.evaluate(() => document.querySelector('nav.idx[aria-label="週で切り替える"]')?.nextElementSibling?.classList.contains('rcount')), '件数の 1 行が週のタブの下にない');
    check(!(await card.locator('button[data-v="interest"]').isVisible()), '押す前から三択が見えている');
    await card.locator('button[data-btns-open]').click();
    check(await card.locator('button[data-v="interest"]').isVisible(), '押しても興味ありが出ない');
    check(!(await card.locator('button[data-btns-open]').isVisible()), '押したあとも「回答を直す」が残る');
    await page.setViewportSize({width: 390, height: 844});
    await sleep(300);
    await page.screenshot({path: join(OUT, 'reminder-phone.png'), fullPage: true});
    await page.setViewportSize({width: 1280, height: 900});
  });

  await step('購入済みにする（探すから）', async () => {
    await go('/search?q=' + encodeURIComponent('舞台ふたつめ'));
    const card = page.locator('.ticket[data-stage="102"]').first();
    await card.waitFor();
    await card.locator('button[data-v="owned"]').click();
    const said = await waitSaid(card, /記録しました|購入済/);
    note('押したあと: 「' + said.trim() + '」');
    check(await card.isVisible(), '購入済みを押したらカードが消えた（2026-10-18 からは残す決まり）');
    const r = sql("SELECT owned FROM reaction WHERE stage_id='102'");
    check(r[0]?.owned === 1, 'D1 に購入済みが無い: ' + JSON.stringify(r));
    await go('/tickets');
    await dump('tickets');
    check(/舞台ふたつめ/.test(await content()), '購入済み公演に出ない');
  });

  await step('公演カレンダー: 行く日を 2 つ入れて、1 つを「この日時を削除」', async () => {
    const addDate = async (date, time) => {
      await go('/calendar');
      await page.locator('button.addtk').click();
      const dlg = page.locator('dialog#tkdlg');
      await dlg.waitFor();
      await dlg.locator('.tkd-work').selectOption('102');
      await dlg.locator('.tkd-date').fill(date);
      if (time) await dlg.locator('.tkd-time').fill(time);
      const reload = page.waitForEvent('load', {timeout: 15000});
      await dlg.locator('[data-dlg-add]').click();
      await waitSaid(dlg, /記録しました/);
      await reload; await settle();
    };
    await addDate('2026-10-19', '14:00');
    await addDate('2026-10-20', '18:30');
    await dump('calendar-2');
    let t = sql("SELECT date, time FROM ticket WHERE stage_id='102' ORDER BY date");
    check(t.length === 2, 'D1 の行く日が 2 つでない: ' + JSON.stringify(t));
    await page.locator('button.addtk').click();
    const dlg = page.locator('dialog#tkdlg');
    await dlg.locator('.tkd-work').selectOption('102');
    const li = dlg.locator('.tkinfo:not([hidden]) .tklist li');
    check(await li.count() === 2, '入れてある日が 2 つ並ばない: ' + await li.count());
    const reload = page.waitForEvent('load', {timeout: 15000});
    await li.first().locator('button[data-del]').click();
    const said = await waitSaid(dlg, /削除しました/);
    note('削除のあと: 「' + said.trim() + '」');
    await reload; await settle();
    t = sql("SELECT date, time FROM ticket WHERE stage_id='102'");
    check(t.length === 1 && t[0].date === '2026-10-20' && t[0].time === '18:30', 'D1 に残った行く日が違う: ' + JSON.stringify(t));
    check(sql("SELECT owned FROM reaction WHERE stage_id='102'")[0]?.owned === 1, '行く日を消したら購入済みまで消えた');
    // 開幕リマインドの「直近の観劇予定」の枠は外した（起案者の指示 2026-10-18）。残った行く日は購入済の公演の画面で確かめる
    await go('/recommend/reminder');
    check(!/直近の観劇予定/.test(await content()), '開幕リマインドに「直近の観劇予定」の枠が残っている');
    await go('/tickets');
    const plan = await page.locator('article.ticket[data-stage="102"] .mytix').first().innerText();
    note('購入済の公演の行く日: ' + plan.replace(/\s+/g, ' ').slice(0, 160));
    check(/10\/20|10月20日/.test(plan) && !/10\/19|10月19日/.test(plan), '購入済の公演の行く日が残った日（10/20）だけになっていない');
  });

  await step('観察: 行く日が過ぎた券（昨日）は評価待ちになるか', async () => {
    await go('/calendar');
    await page.locator('button.addtk').click();
    const dlg = page.locator('dialog#tkdlg');
    await dlg.locator('.tkd-work').selectOption('102');
    await dlg.locator('.tkd-date').fill(jst(-1));
    const reload = page.waitForEvent('load', {timeout: 15000});
    await dlg.locator('[data-dlg-add]').click();
    await waitSaid(dlg, /記録しました|できませんでした/);
    await reload.catch(() => {}); await settle();
    for (const p of ['/', '/rate/unrated', '/records/works']) {
      await go(p);
      await dump('after-ticket' + p.replace(/\W+/g, '_'));
      note(`${p}: 舞台ふたつめ ${/舞台ふたつめ/.test(await content()) ? 'あり' : 'なし'}`);
    }
  });

  await step('設定: 観に行ける場所（東京都・大阪府）', async () => {
    await go('/settings');
    const card = page.locator('#pref-setting');
    await page.locator('details:has(#pref-setting) > summary').click();   // 「観に行ける場所を決めておく」は畳んである
    for (const p of ['東京都', '大阪府']) await card.locator(`input[name=pref][value="${p}"]`).check();
    const reload = page.waitForEvent('load', {timeout: 15000});
    await card.locator('button[data-set-pref]').click();
    await waitSaid(card, /保存しました/);
    await reload; await settle();
    const t = await content();
    note('設定の見出し: ' + (t.match(/いまは[^\n]*/) || [''])[0]);
    check(/東京都/.test(t) && /大阪府/.test(t), '開き直すと場所が出ない');
    await go('/recommend/reminder');
    note('開幕リマインドの絞り込み: ' + ((await content()).match(/場所\n[^\n]*/) || [''])[0].replace('\n', ' '));
  });

  await step('今週のおすすめ: 効かせ方のつまみ（保存して開き直す・初めの設定に戻す）', async () => {
    await go('/');
    await page.locator('button.ftab[data-for="wbox"]').click();
    const sl = page.locator('.wsl[data-weight="cast"]');
    await sl.waitFor();
    // 保存していない人のつまみは群ごとの初めの設定を指す（起案者の指示 2026-10-18「出演者、作品の内容︰少し強く／
    // 制作・宣伝、その他の役職︰あまり効かせない／それ以外はふつう」、dec-weight-defaults）
    const initial = Object.fromEntries(await page.locator('.wsl').evaluateAll(ns => ns.map(n => [n.dataset.weight, n.value])));
    note('効かせ方の初めの位置: ' + JSON.stringify(initial));
    check(JSON.stringify(initial) === JSON.stringify({cast: '3', author: '2', craft: '2', stage: '2', produce: '1', other: '1', theme: '3'}),
      'つまみの初めの位置が群ごとの既定でない');
    await page.locator('#weights').screenshot({path: join(OUT, 'weights-default.png')}).catch(() => {});
    await sl.fill('4');
    await sleep(800);
    check((await page.locator('.wrow[data-grp="cast"] .wv').innerText()).includes('とても強く'), 'つまみの札が変わらない');
    await go('/');
    const v = await page.locator('.wsl[data-weight="cast"]').inputValue();
    check(v === '4', '開き直すとつまみが戻る: ' + v);
    note('D1 rank_weight: ' + JSON.stringify(sql('SELECT * FROM rank_weight')));
    await page.locator('button.ftab[data-for="wbox"]').click();
    const reload = page.waitForEvent('load', {timeout: 15000});
    await page.locator('button[data-wreset]').click();
    await reload; await settle();
    // 「すべて初めの設定に戻す」は群ごとの既定へ（出演者は「少し強く」= 3。前は全部「ふつう」= 2 だった）
    check(await page.locator('.wsl[data-weight="cast"]').inputValue() === '3', '「すべて初めの設定に戻す」で戻らない');
    check(await page.locator('.wsl[data-weight="produce"]').inputValue() === '1', '「すべて初めの設定に戻す」で制作・宣伝が既定に戻らない');
  });

  await step('取り込み: iCal ファイル（取り消した予定・VALARM を含む）', async () => {
    const f = join(OUT, 'e2e-calendar.ics');
    writeFileSync(f, ICS);
    await go('/register');
    await page.locator('details.imx-alt > summary').click();
    await page.setInputFiles('#imx-ics', f);
    const box = page.locator('.imx-found');
    await box.locator('.imx-list li').first().waitFor({timeout: 15000});
    const items = await box.locator('.imx-list li').allInnerTexts();
    note('一覧: ' + items.map(t => t.replace(/\s+/g, ' ').trim()).join(' / '));
    note('見出し: ' + (await box.locator('.imx-head').innerText().catch(() => '')).trim());
    check(items.length === 1 && /冬の物語/.test(items[0]), '一致したのが冬の物語 1 件だけでない');
    check(!items.some(t => /旅の芝居|舞台ひとつめ|歯医者/.test(t)), '取り消した予定・VALARM の題・公演でない予定が出た');
    if (await box.locator('[data-imx-all]').isEnabled()) await box.locator('[data-imx-all]').click();   // 未登録は初めから選んである
    await box.locator('[data-imx-add]').click();
    await waitSaid(page.locator('[data-import]'), /1 件を記録に足しました|記録に足しました/, 15000).catch(async () => note('said: ' + await page.locator('[data-import] .said').first().innerText()));
    const w = sql("SELECT first_date, time, stage_id, venue FROM works WHERE title='冬の物語'");
    note('D1: ' + JSON.stringify(w));
    check(w.length === 1 && w[0].first_date === '2024-01-10' && w[0].time === '18:00', 'D1 の行が違う');
  });

  await step('取り込み: 購入確認メール（.eml 2 通、1 通は記録済み）', async () => {
    const files = EMLS.map(([name, text]) => { const f = join(OUT, name); writeFileSync(f, text); return f; });
    await go('/register');
    await page.locator('details.imx-src').filter({hasText: '購入確認メールから'}).locator('> summary').click();
    await page.setInputFiles('#imx-eml', files);
    const box = page.locator('.imx-found');
    await box.locator('.imx-list li').first().waitFor({timeout: 15000});
    const items = await box.locator('.imx-list li').allInnerTexts();
    note('一覧: ' + items.map(t => t.replace(/\s+/g, ' ').trim()).join(' / '));
    check(items.length === 2, '2 件出ない');
    const dup = box.locator('.imx-list li').filter({hasText: '旅の芝居'});
    check(await dup.locator('input[type=checkbox]').isDisabled(), '記録済みの回が選べる');
    if (await box.locator('[data-imx-all]').isEnabled()) await box.locator('[data-imx-all]').click();   // 未登録は初めから選んである
    await box.locator('[data-imx-add]').click();
    await sleep(1500);
    note('said: ' + (await page.locator('[data-import] .said').first().innerText()).trim());
    const w = sql("SELECT first_date, time FROM works WHERE title='冬の物語' ORDER BY first_date");
    check(w.length === 2 && w[1].first_date === '2024-01-15' && w[1].time === '13:00', 'メールの回が足されない: ' + JSON.stringify(w));
    check(sql("SELECT count(*) n FROM works WHERE title='旅の芝居'")[0].n === 3, '記録済みの回が二重に足された');
  });

  await step('内部リンクを Ctrl+クリックすると新しいタブで開く', async () => {
    await go('/rate');
    const link = page.locator('nav a[href="/records/works"], .side a[href="/records/works"]').first();
    const [tab] = await Promise.all([ctx.waitForEvent('page', {timeout: 5000}), link.click({modifiers: ['Control']})]);
    await tab.waitForLoadState();
    note('新しいタブ: ' + tab.url().slice(BASE.length));
    check(tab.url().startsWith(BASE + '/records/works'), '新しいタブの行き先が違う');
    check(page.url() === BASE + '/rate', '元のタブが移動した: ' + page.url());
    await tab.close();
    // ふつうのクリックは同じタブの中で移る
    await link.click();
    await page.waitForURL(BASE + '/records/works');
  });

  await step('書き出す（taguri-export.json）', async () => {
    await go('/settings');
    await page.locator('details:has(a.dl) > summary').click();
    const [dl] = await Promise.all([page.waitForEvent('download'), page.locator('a.dl').click()]);
    const path = join(OUT, 'taguri-export-A.json');
    await dl.saveAs(path);
    const data = JSON.parse(readFileSync(path, 'utf8'));
    const text = JSON.stringify(data);
    note('鍵: ' + Object.keys(data).join(','));
    for (const want of ['手で足した芝居', '最初に書いた感想。書き足した。', '4/5', '旅の芝居', '冬の物語', '俳優乙'])
      check(text.includes(want), `書き出しに「${want}」が無い`);
    check(!text.includes(A.code), '書き出しに復旧コードが入っている');
  });

  // 画面に出る全角のカッコは半角にそろえる（起案者の指示 2026-10-18、web/halfwidth.js）。本人の感想・メモは除く
  await step('全角のカッコが画面に残らない（主な画面）', async () => {
    for (const path of ['/recommend', '/recommend/reminder', '/rate', '/records/works', '/tickets', '/settings', '/account']) {
      await go(path);
      const left = await page.evaluate(() => {
        const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), out = [];
        for (let n = w.nextNode(); n; n = w.nextNode()) {
          if (/[（）]/.test(n.nodeValue) && !n.parentElement.closest('script,style,code,pre,textarea,input,.int,.wnt,.nnv')) out.push(n.nodeValue.trim().slice(0, 30));
        }
        return out;
      });
      check(!left.length, `${path} に全角のカッコ: ${left.slice(0, 3).join(' / ')}`);
    }
  });

  await step('ログアウト → 開くとログインの画面', async () => {
    await go('/account');
    await page.locator('button[data-account-logout]:not([data-account-logout="all"])').click();
    await page.waitForURL(/\/login/);
    await go('/rate');
    check(page.url().includes('/login'), 'ログアウト後に記録の画面が開く: ' + page.url());
    const r = await page.request.get(BASE + '/api/screen/rate');
    check(r.status() === 401, 'ログアウト後に API が ' + r.status());
  });

  // ログイン画面・規約の見た目（起案者の指示 2026-10-18: 色をログイン後にそろえる・復旧コードはメールの下に点線で・
  // 迷惑メールの案内・「Googleアカウント」・「プライバシーポリシー」）。PC と電話の幅、暗い表示も写す
  await step('ログイン画面と規約の見た目（PC・電話・暗い表示）', async () => {
    await go('/login');
    const bg = await page.evaluate(() => [getComputedStyle(document.body).backgroundColor, getComputedStyle(document.querySelector('.auth-top')).backgroundColor]);
    check(bg[0] === 'rgb(242, 242, 243)' && bg[1] === 'rgb(255, 255, 255)', 'ログイン後の色（地 #f2f2f3・帯 #fff）でない: ' + bg.join(' / '));
    check(/Googleアカウントでログイン/.test(await page.locator('#google').innerText()), '「Googleアカウントでログイン」でない');
    check(/迷惑メールボックス/.test(await page.locator('#email-form').innerText()), 'メールの欄の下に迷惑メールの案内が無い');
    check(await page.evaluate(() => !!document.querySelector('#login #email-form ~ #recovery-login')), '復旧コードの欄がメールの欄の下（ログインの欄の中）に無い');
    check(/プライバシーポリシー/.test(await page.locator('#signup').innerText()), '同意の文が「プライバシーポリシー」でない');
    await page.screenshot({path: join(OUT, 'login-pc.png'), fullPage: true});
    await page.setViewportSize({width: 390, height: 844});
    await page.screenshot({path: join(OUT, 'login-phone.png'), fullPage: true});
    await page.emulateMedia({colorScheme: 'dark'});
    await page.screenshot({path: join(OUT, 'login-phone-dark.png'), fullPage: true});
    await page.emulateMedia({colorScheme: 'light'});
    for (const p of ['terms', 'privacy']) {
      await go('/' + p);
      check(/第 1 条/.test(await page.locator('article').innerText()), `/${p} が条の形でない`);
      await page.screenshot({path: join(OUT, `${p}-phone.png`), fullPage: false});
    }
    await page.setViewportSize({width: 1280, height: 900});
    for (const p of ['terms', 'privacy']) { await go('/' + p); await page.screenshot({path: join(OUT, `${p}-pc.png`), fullPage: false}); }
    check(/プライバシーポリシー/.test(await page.title()), '/privacy の題が「プライバシーポリシー」でない');
  });

  await step('もう一度ログイン（パスキー）', async () => {
    await go('/login');
    await page.click('#passkey-login');
    await page.waitForURL(BASE + '/', {timeout: 15000});
    await go('/rate?v=' + encodeURIComponent('4/5'));
    const t = await content();
    check(/手で足した芝居/.test(t) && /最初に書いた感想。書き足した。/.test(t), 'ログインし直すと記録・感想が無い');
  });

  // 起案者の指摘 2026-10-18「どのアイコン画像選んでも選べない」（CSP が blob: を許していなかった）・「観た回数」・「お気に入りが常に 0 件」
  await step('アカウント: アイコン画像を選べて、観た回数とお気に入りの数が出る', async () => {
    await go('/account');
    const png = await page.screenshot({clip: {x: 0, y: 0, width: 120, height: 90}});
    await page.locator('input[data-account-avatar]').setInputFiles({name: 'icon.png', mimeType: 'image/png', buffer: png});
    const said = await waitSaid(page.locator('.acpic'), /保存しました|読めませんでした|使えません/);
    note('アイコン: 「' + said + '」');
    check(/保存しました/.test(said) && await page.locator('.acav img').count() === 1, 'アイコン画像を選んでも出ない');
    const t = await content();
    note((t.match(/\d+\s*観た回数/) || ['観た回数なし'])[0].replace(/\s+/g, ' ') + '・' + (t.match(/\d+\s*お気に入り/) || ['お気に入りなし'])[0].replace(/\s+/g, ' '));
    check(/観た回数/.test(t), '観た回数が無い');
    await shotsBoth('account-stats');
  });

  await step('復旧コードでログイン', async () => {
    await go('/account');
    await page.locator('button[data-account-logout]:not([data-account-logout="all"])').click();
    await page.waitForURL(/\/login/);
    await settle();
    const form = page.locator('#recovery-login');
    check(await form.isVisible(), 'ログイン画面に復旧コードの欄が無い（削除・結び付けの画面にしか無い）');
    // 違うコードは断られる
    await page.fill('#recovery-input', '0'.repeat(64));
    await form.locator('button').click();
    await page.locator('#status.bad').waitFor({timeout: 5000});
    check(await page.evaluate(() => !!document.querySelector('#recovery-login label + #status')), '断られた文が復旧コードの欄の下に出ない');
    note('違うコード: 「' + (await page.locator('#status').innerText()).trim() + '」');
    await page.fill('#recovery-input', A.code);
    await form.locator('button').click();
    await page.waitForURL(BASE + '/', {timeout: 10000});
    await go('/rate?v=' + encodeURIComponent('4/5'));
    check(/手で足した芝居/.test(await content()), '復旧コードで戻れない');
  }, {allowFailed: true});

  await step('アカウントの画面のリンク（別のページへ行くもの）', async () => {
    const seen = [];
    for (const [href, want] of [['/migration-data/#passkeys', /パスキー/], ['/login?link=1&next=%2Faccount', /結び付け/]]) {
      await go('/account');
      await page.locator(`a[href="${href}"]`).click();
      await page.waitForLoadState('networkidle');
      const t = await page.locator('body').innerText();
      seen.push(`${href} → ${page.url().slice(BASE.length)}`);
      check(!/このページはありません/.test(t) && want.test(t), `${href} が開けない（「見つかりません」）`);
      if (href.startsWith('/migration-data')) note('/migration-data/ の「観劇記録」: ' + ((t.match(/観劇記録\n+(\d+件)/) || [, '?'])[1]) + '（日記帳には ' + sql(`SELECT count(*) n FROM works WHERE user_id='${A.uid}'`)[0].n + ' 件）');
    }
    await go('/settings');
    await page.locator('details:has(a[href="/terms"]) > summary').first().click().catch(() => {});
    const terms = page.locator('#content a[href="/terms"]').first();
    if (await terms.count()) {
      await terms.click();
      await page.waitForLoadState('networkidle');
      seen.push('/terms → ' + page.url().slice(BASE.length));
      check(!/このページはありません/.test(await page.locator('body').innerText()), '設定の利用規約へのリンクが開けない');
    }
    note(seen.join(' / '));
  });

  // 残りの画面も開いて、エラーが出ないことだけを確かめる
  for (const p of ['/records', '/records/chronicle', '/records/trace', '/records/works', '/rate/notes', '/tickets', '/settings', '/account', '/search']) {
    await step('開く ' + p, async () => { await go(p); check((await content()).trim().length > 0, '中身が空'); check(!/このページはありません|読み込めませんでした/.test(await content()), '画面が出ない'); });
  }

  // 日記帳のコラージュの見た目（起案者の指示 2026-10-18）: 日付は yyyy/mm/dd(曜日)、テープの中心がポスターの上辺に重なる、
  // テープの柄が行ごとに違う、感想の欄に地の色。パソコンと電話の幅（390px）の両方で確かめ、写しを残す
  await step('日記帳の見た目（日付・テープ・感想の欄、パソコンと電話の幅）', async () => {
    for (const [w, h, name] of [[1280, 900, 'works-pc.png'], [390, 844, 'works-phone.png']]) {
      await page.setViewportSize({width: w, height: h});
      await go('/records/works');
      const rows = await page.evaluate(() => [...document.querySelectorAll('[data-route="/records/works"] .idxsheet>.rec-row')].map(r => {
        const pin = r.querySelector('.pin'), po = pin.firstElementChild, pr = pin.getBoundingClientRect();
        const t = getComputedStyle(pin, '::before'), pcs = getComputedStyle(po);
        const tapeMid = pr.top + parseFloat(t.top) + parseFloat(t.height) / 2;
        // ポスターの上辺（傾ける前）: 枠の上端。傾きは小さいので、外接の箱の上端から上の縁の太さまでの間に入る
        const top = pin.getBoundingClientRect().top + parseFloat(getComputedStyle(pin).paddingTop);
        return {date: r.querySelector('.dt')?.textContent || '', gap: Math.abs(tapeMid - top),
          // テープは形そのものを行ごとに替える（同日「テープは柄だけでなく形自体（うねうね、四角、丸シールなど）も何種類かほしい」）
          tape: [t.width, t.height, t.borderRadius, t.clipPath, t.maskImage || t.webkitMaskImage].join('|'),
          inb: getComputedStyle(r.querySelector('.inr>.inb') || r).backgroundColor, poster: pcs.borderTopWidth,
          wide: document.documentElement.scrollWidth};
      }));
      check(rows.length >= 2, '日記帳の行が足りない');
      for (const r of rows) {
        check(/^\d{4}\/\d{2}\/\d{2}\([月火水木金土日]\)$/.test(r.date) || /上演日が/.test(r.date), `日付の形が違う: ${r.date}`);
        check(r.gap <= 1.5, `テープの中心がポスターの上辺から ${r.gap.toFixed(1)}px ずれている`);
        check(!/rgba\(0, 0, 0, 0\)|transparent/.test(r.inb), '感想の欄に地の色が無い');
        check(r.wide <= w, `横にはみ出す（${r.wide}px）`);
      }
      check(new Set(rows.slice(0, 4).map(r => r.tape)).size === Math.min(4, rows.length), 'テープの形が行ごとに替わらない');
      await page.screenshot({path: join(OUT, name), fullPage: true});
      note(`${w}px: ${rows.map(r => r.date).join(' / ')}`);
    }
    await page.setViewportSize({width: 1280, height: 900});
  });
}

// ================================================================ 利用者 B（別の履歴）と分離
async function walkB(A, B) {
  await step('利用者 B を登録（同じブラウザーの別の窓）', async () => {
    await go('/login');
    await page.check('#agree');
    await page.click('#passkey-signup');
    await page.locator('#passkey-recovery:not([hidden])').waitFor({timeout: 15000});
    B.code = (await page.locator('#recovery-code').innerText()).trim();
    check(B.code !== A.code, '復旧コードが A と同じ');
    await page.click('#recovery-done');
    await page.waitForURL(BASE + '/');
    B.uid = sql(`SELECT id FROM users WHERE id<>'${A.uid}'`)[0]?.id;
    check(B.uid && B.uid !== A.uid, 'B のアカウントが別にできない');
  });
  await step('B には A の記録・評価・感想・お気に入り・興味あり・券が見えない', async () => {
    const leaks = [];
    for (const p of ['/rate', '/rate/unrated', '/rate/notes', '/records/works', '/recommend/interest', '/recommend/favourites', '/tickets', '/calendar', '/recommend/reminder', '/account', '/search?q=' + encodeURIComponent('旅の芝居')]) {
      await go(p);
      const t = await content();
      for (const w of ['手で足した芝居', '最初に書いた感想', '冬の物語', '俳優乙', '近く開く芝居', '舞台ふたつめ'])
        if (t.includes(w) && !(p.startsWith('/search') || p === '/recommend/reminder') ) leaks.push(`${p}: ${w}`);
      // 開幕リマインドの「直近の観劇予定」（A の行く日が出うる枠）は 2026-10-18 に外した。行く日は /tickets で見ている
      if (p.startsWith('/search') && await page.locator('.pastrow .past-done, [data-past=missed][disabled]').count()) leaks.push('search: A の「観た」');
    }
    check(!leaks.length, '見えた: ' + leaks.join(' / '));
    const ex = await page.request.get(BASE + '/export.json');
    const text = await ex.text();
    check(ex.status() === 200 && !/手で足した芝居|冬の物語|俳優乙/.test(text), 'B の書き出しに A の記録が入る');
  });
  await step('B は A の記録を名指ししても書き換えられない', async () => {
    const KEY = '手で足した芝居#2026-09-20';
    const tries = [['/api/note', {work_key: KEY, note_impression: 'Bが書いた'}], ['/api/rate', {work_key: KEY, verdict: '1/5'}], ['/api/drop_work', {work_key: KEY}]];
    const got = [];
    for (const [path, body] of tries) {
      const r = await page.request.post(BASE + path, {data: body, headers: {origin: BASE}});
      got.push(`${path} ${r.status()}`);
    }
    note(got.join(' / '));
    check(got.every(g => / 4\d\d$/.test(g)), 'B の書き込みが通った');
    const w = sql(`SELECT verdict, note_impression FROM works WHERE user_id='${A.uid}' AND work_key='${KEY}'`)[0];
    check(w?.verdict === '4/5' && w?.note_impression === '最初に書いた感想。書き足した。', 'A の記録が変わった: ' + JSON.stringify(w));
  });
  await step('B が自分の記録を足す（A には見えない）', async () => {
    await go('/register');
    await page.fill('#w-title', 'Bだけの芝居');
    await page.fill('#w-date', '2026-10-01');
    const reload = page.waitForEvent('load', {timeout: 15000});
    await page.locator('.add-work button[data-add-work]').click();
    await waitSaid(page.locator('.add-work'), /登録しました/);
    await reload; await settle();
    const ap = A.page;
    await ap.goto(BASE + '/rate/unrated'); await ap.waitForLoadState('networkidle');
    check(!/Bだけの芝居/.test(await ap.locator('#content').innerText()), 'A に B の記録が見える');
  });

  // お気に入りを登録しただけでもおすすめが出る（起案者の問い 2026-10-18「お気に入りに登録するとおすすめが出る、って
  // 書いてあるのに、何もでないときがある」、fix-fav-only-no-reco）。B は評価も興味ありも無い。名前は空白入りで登録する
  // （前は索引の「作家丁」と当たらず 0 件だった）。理由には登録した名前を書く（「好きな○○」と登録していない人を書かない）
  await step('B: お気に入り（作家 丁）だけでおすすめが出て、理由に登録した名前が出る', async () => {
    await go('/recommend/favourites');
    if (!(await page.locator('details#names').getAttribute('open') !== null)) await page.locator('details#names > summary').click();
    await page.selectOption('#fav-kind', '人');
    await page.fill('#fav-name', '作家 丁');
    const reload = page.waitForEvent('load', {timeout: 15000});
    await page.locator('.fav-add button[data-fav="add"]').click();
    await waitSaid(page.locator('.fav-add'), /登録しました/);
    await reload; await settle();
    await go('/');
    await dump('b-home-favourite-only');
    const card = page.locator('.ticket.recommend[data-stage="101"]');
    check(await card.count() === 1, 'お気に入りだけでおすすめ（舞台ひとつめ）が出ない');
    const why = (await card.locator('li.rs').allInnerTexts().catch(() => [])).map(t => t.replace(/\s+/g, ' ').replace(/✕/g, '').trim());
    note('おすすめの理由: ' + why.join(' / '));
    // 理由の形は「登録した名前 その作品での役職『作品名』この人の役職」（起案者の指示 2026-10-18、fix-fav-reason-roles）
    check(why.some(t => /[(（]作家 丁 脚本『舞台ふたつめ』出演[)）]/.test(t)), '理由に登録した名前・役職・作品（作家 丁 脚本『舞台ふたつめ』出演）が出ない');
    // 括弧の説明の無い行は出さない（起案者の問い 2026-10-18「括弧でおすすめ理由がついてないもの…」、fix-reason-no-paren）
    check(why.every(t => /[(（].+[)）]/.test(t)), '括弧の説明の無い理由の行: ' + why.join(' / '));
    check(!why.some(t => /好きな/.test(t)), '登録していない人が「好きな」と出る');
    check(why.every(t => (t.match(/[(（]/g) || []).length === (t.match(/[)）]/g) || []).length), '理由のカッコの数が合わない');
    await card.screenshot({path: join(OUT, 'reasons-favourite-only.png')}).catch(() => {});
  });
}

// ================================================================ アカウントの削除（A）
async function deleteA(A, B) {
  let cookie = '';
  await step('アカウントの削除（復旧コードで本人確認 →「削除」）', async () => {
    cookie = (await ctx.cookies(BASE)).map(c => `${c.name}=${c.value}`).join('; ');
    await go('/account');
    await page.locator('a[href="/login?purpose=delete"]').click();
    await page.waitForURL(/purpose=delete/);
    await settle();
    check(await page.locator('#delete-intro').isVisible(), '削除の説明が出ない');
    await page.fill('#recovery-input', A.code);
    await page.locator('#recovery-login button').click();
    await page.locator('#delete-confirm:not([hidden])').waitFor({timeout: 10000});
    await page.fill('#delete-word', '削除');
    await page.locator('#delete-confirm button').click();
    await page.locator('#delete-done:not([hidden])').waitFor({timeout: 10000});
    note('終わり: 「' + (await page.locator('#status').innerText()).trim() + '」');
    const left = [];
    for (const t of ['users', 'sessions', 'works', 'reaction', 'ticket', 'app_setting', 'rank_weight', 'passkeys']) {
      const col = t === 'users' ? 'id' : 'user_id';
      const n = sql(`SELECT count(*) n FROM ${t} WHERE ${col}='${A.uid}'`)[0].n;
      if (n) left.push(`${t} ${n}`);
    }
    check(!left.length, 'A の行が残る: ' + left.join(', '));
    { const bn = sql(`SELECT count(*) n FROM works WHERE user_id='${B.uid}'`)[0].n; check(bn === 1, 'B の記録まで消えた（B の works ' + bn + ' 件）'); }
    const old = await fetch(BASE + '/api/screen/rate', {headers: {cookie}});
    check(old.status === 401, '前のセッションで ' + old.status);
    const rec = await fetch(BASE + '/migration-api/recover', {method: 'POST', headers: {origin: BASE, 'content-type': 'application/json'}, body: JSON.stringify({code: A.code})});
    check(rec.status === 401, '消したあとも復旧コードで ' + rec.status);
  }, {allowFailed: true});
  await step('消したアカウントのパスキーではログインできない', async () => {
    await go('/login');
    await page.click('#passkey-login');
    await page.locator('#status.bad').waitFor({timeout: 10000});
    note('「' + (await page.locator('#status').innerText()).trim() + '」');
    check(page.url().includes('/login'), 'ログインできてしまう');
  }, {allowFailed: true});
}
