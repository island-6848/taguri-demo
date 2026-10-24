// ことばの雲（起案者の指示 2026-10-24「眺めるページにワードクラウドを表示したい。自分の過去の観た舞台のあらすじからつくる」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {clean, countWords, layout, panel, MIN_STAGES} from '../src/screens/words.js';
import {FIGS} from '../src/screens/figs.js';
import {setup, step, signIn} from './screens/harness.js';

const SYN = [
  '戦争で家族を失った青年が、故郷の京都へ帰る。運命に抗う青年の旅。',
  '京都の老舗で働く青年と、戦争の記憶を抱えた祖母の物語。',
  '運命の恋に落ちた二人。舞台は戦争前夜の上海（山田太郎）。',
  'ベートーヴェンの生涯を、生演奏とダンスで描く。運命の交響曲。',
  '孤独な少女が、ダンスに出会い、居場所を見つける。',
];

test('a word counts once per performance, names in brackets and stock words are dropped', () => {
  const words = countWords(SYN);
  const n = Object.fromEntries(words);
  assert.equal(n['運命'], 3);          // 1 本のあらすじに 2 回出ても 1
  assert.equal(n['戦争'], 3);
  assert.equal(n['京都'], 2);
  assert.equal(n['山田'], undefined);  // 括弧の中（役者の名前）は数えない
  assert.equal(n['物語'], undefined);  // どのあらすじにも出る言葉
  assert.equal(n['舞台'], undefined);
  assert.ok(words.every(([w]) => /^(?:[一-鿿々]+|[゠-ヿ]{3,})$/u.test(w)), '送り仮名のある語は入らない');
  assert.deepEqual(words[0], ['運命', 3]);
});

test('entities are decoded and urls removed before counting', () => {
  assert.equal(clean('A&amp;B https://x.example/a 本文（出演者）'), 'A&B   本文 ');
});

test('the layout never overlaps and stays inside the box', () => {
  const words = countWords(SYN);
  for (const W of [340, 720]) {
    const H = Math.round(W * (W < 500 ? 0.95 : 0.55)), P = layout(words, W, H);
    assert.ok(P.length >= Math.min(words.length, 10), `${W}: ${P.length} placed`);
    for (const p of P) assert.ok(p.x >= 0 && p.y >= 0 && p.x + p.w <= W && p.y + p.h <= H);
    for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) {
      const a = P[i], b = P[j];
      assert.ok(!(a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h), `${a.word} / ${b.word}`);
    }
    assert.equal(P[0].word, '運命');
  }
});

test('the panel: too few synopses says why instead of drawing', () => {
  const few = panel(SYN.slice(0, MIN_STAGES - 1), 12);
  assert.match(few, /あらすじを取れた公演がまだ 4 公演なので、雲を描いていません/);
  assert.doesNotMatch(few, /class="wcloud"/);
  const html = FIGS.words([], {syn: SYN, nSeen: 12}, 720);
  assert.match(html, /ことばの雲/);
  assert.match(html, /いちばん多いのは <b>「運命」の 3 公演<\/b>/);
  assert.match(html, /観た 12 公演のうち、あらすじを取れた 5 公演から作っています/);
  assert.match(html, /<text class="w0"[^>]*><title>運命：3 公演のあらすじに出てくる<\/title>運命<\/text>/);
});

test('眺める sends the synopses of the performances seen: hand-fixed first, then the catalogue, then past stages', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const ins = sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people,synopsis) VALUES(?,?,?,'2025-07-01','2025-08-30','劇場A','劇団甲','東京都','[]',?)");
    ins.run('900', '過去の芝居', '過去の芝居', '過去の公演のあらすじ');
    ins.run('901', '直した芝居', '直した芝居', '直す前のあらすじ');
    ins.run('902', '無い芝居', '無い芝居', '');
    sqlite.exec("INSERT INTO stage_override(stage_id,synopsis,updated_at) VALUES('901','手で直したあらすじ','2026-10-24')");
    for (const [title, sid] of [['過去の芝居', '900'], ['直した芝居', '901'], ['無い芝居', '902']]) {
      await step(env, a, {post: '/api/add_work', body: {title, date: '2025-08-20', stage_id: sid}});
    }
    const html = (await step(env, a, {get: '/api/screen/records'})).body.body_html;
    assert.match(html, /<div data-fig="words"><\/div>/);
    const src = JSON.parse(/<script id="figs-src" type="application\/json">([\s\S]*?)<\/script>/.exec(html)[1]);
    assert.deepEqual([...src.syn].sort(), ['手で直したあらすじ', '過去の公演のあらすじ']);
    assert.equal(src.nSeen, 3);
  } finally { sqlite.close(); }
});
