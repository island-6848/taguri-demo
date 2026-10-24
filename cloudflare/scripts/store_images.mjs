// Google Play の掲載用の画像（フィーチャーグラフィック 1024×500・電話のスクリーンショット 1080×1920）を作る（impl-android-twa）。
// スクリーンショットは本物の画面（Worker と web/ の画面）を、テストのデータを架空の題名・人名・劇場に置き換えて写す。
// 実在の公演・人・ポスターは使わない（権利のため）。ポスターは「now printing」の札のまま。
//   node scripts/store_images.mjs ../docs/store/images
import http from 'node:http';
import {readFileSync, existsSync, statSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {join} from 'node:path';
import {chromium} from 'playwright';
import worker from '../src/worker.js';
import {setup, signIn, step} from '../test/screens/harness.js';

const OUT = process.argv[2] || '../docs/store/images';
const PORT = 8791;
const FIXTURE = JSON.parse(execFileSync('python3', ['test/screens/recommend_fixture.py'], {encoding: 'utf8', maxBuffer: 64 << 20}));
// テストの仮の名前 → 架空の名前（どの公演でも同じ人。おすすめの理由がつながるように）
const NAMES = [['舞台ひとつめ', '海辺の図書館'], ['舞台ふたつめ', '灯台守の娘'], ['終わった舞台', '春の終わりの停車場'], ['一日だけの舞台', '一夜かぎりの朗読会'],
  ['劇場の無い舞台', '路地裏の音楽会'], ['俳優甲', '青木 遥'], ['俳優乙', '森下 透'], ['演出家丙', '佐伯 千尋'], ['作家丁', '柚木 一誠'],
  ['劇団甲', '劇団あさぎり'], ['劇団乙', 'ことのは座'], ['劇場A', 'みなと劇場'], ['劇場B', '川沿いシアター'], ["劇場 ''C''", '北口ホール'], ["劇場 'C'", '北口ホール'], ['料金を取れませんでした', '全席指定 4,800円']];
const rename = s => NAMES.reduce((t, [a, b]) => t.split(a).join(b), s);
// 「海辺の図書館」を元に、日付と題名・劇場・あらすじを変えた架空の公演を足す
const MORE = [
  ['月曜日の亡霊', 'こもれび小劇場', '11/6', '11/16', '取り壊しの決まった古い劇場に、毎週月曜日だけ現れる幽霊がいる。最後の公演の夜、幽霊は台本の続きを書いてほしいと頼みにくる。'],
  ['さよなら、ガラスの街', '北口ホール', '11/12', '11/23', '町じゅうの窓がガラス細工でできた街。ひびの入った窓を直す職人の姉妹が、街を出るか残るかを決める一週間の物語。'],
  ['ひかりの庭で', '川沿いシアター', '11/20', '11/30', '老人ホームの小さな庭で、入居者たちが一度きりの芝居を作る。忘れかけた台詞と、忘れられない思い出が交差するヒューマンドラマ。'],
  ['真夜中のピクニック', 'みなと劇場', '11/27', '12/7', '終電を逃した見知らぬ五人が、閉店後の遊園地で朝を待つ。軽やかな会話劇の奥に、それぞれが言えなかった言葉が隠れている。'],
  ['雨音のワルツ', 'こもれび小劇場', '12/4', '12/14', '雨の日だけ開く小さなダンスホール。そこで出会った二人が、言葉の代わりにステップで想いを伝えようとするミュージカル。'],
];
const SYN0 = '海辺の町の小さな図書館に、閉館の知らせが届く。最後の一週間、本を返しに来る人々の思い出が、少しずつ館長の過去をほどいていく。';

const {env, sqlite} = setup();
for (const s of FIXTURE.sql) sqlite.exec(rename(s));
const synBlock = (sid, text) => `<div class="syn" data-stage="${sid}"><p class="txt">${text}</p><span class="src">［出典: 公演ページ］</span><button class="mrb" data-more="1">続きを読む</button></div>`;
const fixCard = (html, sid, text) => html.replace(/<div class="syn no"[\s\S]*?<\/details><\/div>/, synBlock(sid, text));
for (const r of sqlite.prepare("SELECT ver, html FROM rec_card WHERE stage_id='101'").all())
  sqlite.prepare("UPDATE rec_card SET html=? WHERE ver=? AND stage_id='101'").run(fixCard(r.html, '101', SYN0), r.ver);
const iso = md => { const [m, d] = md.split('/').map(Number); return `2026-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`; };
MORE.forEach(([title, venue, from, to, syn], i) => {
  const sid = String(201 + i);
  const days = Math.round((Date.parse(iso(to)) - Date.parse(iso(from))) / 864e5) + 1;
  const swap = v => typeof v !== 'string' ? v : v.split('101').join(sid).split('海辺の図書館').join(title).split('みなと劇場').join(venue)
    .split('2026-11-01').join(iso(from)).split('2026-11-10').join(iso(to)).split('2026/11/01').join(iso(from).replaceAll('-', '/'))
    .split('2026/11/10').join(iso(to).replaceAll('-', '/')).split('11/1〜11/10').join(`${from}〜${to}`).split('<b>11/1</b>').join(`<b>${from}</b>`)
    .split('10 日間').join(`${days} 日間`).split('c2ff6bec7691d022').join('tour' + sid);
  for (const t of ['rec_stage', 'rec_credit', 'rec_card', 'rec_people']) {
    const cols = sqlite.prepare(`PRAGMA table_info(${t})`).all().map(c => c.name);
    if (!cols.includes('stage_id')) continue;
    for (const r of sqlite.prepare(`SELECT * FROM ${t} WHERE stage_id='101'`).all()) {
      const v = Object.fromEntries(Object.entries(r).map(([k, x]) => [k, swap(x)]));
      if (t === 'rec_card') v.html = v.html.replace(/<div class="syn"[\s\S]*?<\/button><\/div>/, synBlock(sid, syn));
      sqlite.prepare(`INSERT OR IGNORE INTO ${t}(${cols.join(',')}) VALUES(${cols.map(() => '?').join(',')})`).run(...cols.map(c => v[c]));
    }
  }
});
const types = {js: 'text/javascript', css: 'text/css', html: 'text/html', png: 'image/png', svg: 'image/svg+xml', webmanifest: 'application/manifest+json', woff2: 'font/woff2'};
env.ASSETS = {fetch: async req => {
  let p = new URL(req.url).pathname; if (p === '/' || !/\.[a-z0-9]+$/.test(p)) p = '/index.html';
  const f = 'public' + p;
  if (!existsSync(f) || statSync(f).isDirectory()) return new Response('nf', {status: 404});
  return new Response(readFileSync(f), {headers: {'content-type': types[p.split('.').pop()] || 'application/octet-stream'}});
}};
const a = await signIn(env);
await step(env, a, {post: '/api/terms', body: {}}).catch(() => null);
const rate = async (title, date, verdict, sid) => {
  const key = (await step(env, a, {post: '/api/add_work', body: {title, date}})).body.work_key;
  if (sid) await step(env, a, {post: '/api/link_stage', body: {work_key: key, stage_id: sid}});
  await step(env, a, {post: '/api/rate', body: {work_key: key, verdict}});
};
await rate('春の終わりの停車場', '2026-08-05', '5/5', '103');
await rate('一夜かぎりの朗読会', '2026-09-05', '2/5', '104');
for (const [t, d, v] of [['星を数える夜', '2026-07-12', '5/5'], ['とおい親戚', '2026-06-21', '4/5'], ['紙ひこうきの約束', '2026-05-30', '4/5'],
  ['冬の窓辺', '2026-03-14', '3/5'], ['あの日の合唱', '2026-02-08', '5/5'], ['ふたりの台所', '2025-12-20', '4/5']]) await rate(t, d, v);
await step(env, a, {post: '/api/react', body: {stage_id: '203', value: 'interest', nofill: true, note: 'ポスターの色がきれいだった'}});
await step(env, a, {post: '/api/react', body: {stage_id: '205', value: 'interest', nofill: true}});

const srv = http.createServer(async (req, res) => {
  const chunks = []; for await (const c of req) chunks.push(c);
  const r = await worker.fetch(new Request(`http://127.0.0.1:${PORT}` + req.url, {method: req.method, headers: req.headers, body: ['GET', 'HEAD'].includes(req.method) ? undefined : Buffer.concat(chunks)}), env);
  res.writeHead(r.status, Object.fromEntries(r.headers)); res.end(Buffer.from(await r.arrayBuffer()));
}).listen(PORT);
const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
// 電話: 360×640 の 3 倍 = 1080×1920（Play の 9:16）
const ctx = await b.newContext({viewport: {width: 360, height: 640}, deviceScaleFactor: 3, isMobile: true, hasTouch: true, colorScheme: 'light'});
const [name, value] = a.split('=');
await ctx.addCookies([{name, value, url: `http://127.0.0.1:${PORT}`}]);
// 初めて開いたときの案内（tour.js）は出さない
await ctx.addInitScript(() => {
  try { localStorage.setItem('taguri_tour_done_v1', '1'); } catch { /* なくても写せる */ }
  // 右下の「使い方」のボタンも写さない
  document.addEventListener('DOMContentLoaded', () => {
    const st = document.createElement('style'); st.textContent = '.tgt-fab{display:none!important}'; document.head.appendChild(st);
  });
});
const page = await ctx.newPage();
async function shot(path, file, at) {
  await page.goto(`http://127.0.0.1:${PORT}${path}`);
  await page.waitForSelector('#content h1', {timeout: 15000});
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(600);
  // at: 写し始める要素（セレクター）か、上からの位置（px）
  if (at) await page.evaluate(sel => { const el = typeof sel === 'number' ? null : document.querySelector(sel);
    window.scrollTo(0, el ? el.getBoundingClientRect().top + window.scrollY - 8 : Number(sel)); }, at);
  await page.waitForTimeout(300);
  await page.screenshot({path: join(OUT, file)});
  console.log('wrote', file);
}
await shot('/recommend', 'screen-1-recommend.png', null);
await shot('/recommend', 'screen-2-reasons.png', '.ticket.recommend');
await shot('/recommend/interest', 'screen-3-interest.png', '.ticket');
await shot('/rate', 'screen-4-rate.png', null);
await shot('/records/works', 'screen-5-diary.png', 436);
await b.close(); srv.close(); sqlite.close();

// フィーチャーグラフィック（1024×500）: リンクのカード（public/assets/og.png、1200×630）を縮め、左右を同じ地の色で埋める。
// Play は上下左右の端を切ることがあるので、文字は中央に収める
{
  const og = readFileSync('public/assets/og.png').toString('base64');
  const b2 = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  const p = await b2.newPage({viewport: {width: 1024, height: 500}});
  await p.setContent(`<body style="margin:0;width:1024px;height:500px;background:#f2f2f2;display:flex;align-items:center;justify-content:center">`
    + `<img src="data:image/png;base64,${og}" style="height:500px"></body>`);
  const bg = await p.evaluate(async () => { const i = document.querySelector('img'); await i.decode();
    const c = document.createElement('canvas'); c.width = 4; c.height = 4; const x = c.getContext('2d'); x.drawImage(i, 0, 0);
    const [r, g, bl] = x.getImageData(1, 1, 1, 1).data; return `rgb(${r},${g},${bl})`; });
  await p.evaluate(c => { document.body.style.background = c; }, bg);
  await p.screenshot({path: join(OUT, 'feature-graphic-1024x500.png')});
  await b2.close();
  console.log('wrote feature-graphic-1024x500.png');
}
