// ことばの雲（起案者の指示 2026-10-24「眺めるページにワードクラウドを表示したい。自分の過去の観た舞台のあらすじからつくる」、
// 同じ日に「ワードクラウドはあらすじ抽出でタグに出ている単語リストから構成してほしい」）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {countTags, layout, panel, MIN_STAGES} from '../src/screens/words.js';
import {FIGS} from '../src/screens/figs.js';
import {setup, step, signIn} from './screens/harness.js';

const TAGS = [
  ['戦争', '家族', '運命', '京都'],
  ['京都', '戦争', '記憶', '祖母'],
  ['運命', '恋', '戦争', '運命'],
  ['ベートーヴェン', '運命', 'ダンス'],
  ['孤独', 'ダンス', '居場所'],
];

test('a tag counts once per performance, in the form it was written', () => {
  const words = countTags(TAGS);
  const n = Object.fromEntries(words);
  assert.equal(n['運命'], 3);          // 1 公演に 2 度あっても 1
  assert.equal(n['戦争'], 3);
  assert.equal(n['京都'], 2);
  assert.equal(n['ダンス'], 2);
  assert.equal(n['ベートーヴェン'], 1);   // 2 公演以上の語が 12 語に満たないので、1 公演の語も残す
  assert.deepEqual(words.slice(0, 2), [['運命', 3], ['戦争', 3]]);   // 同数は五十音順
  // 2 公演以上の語が 12 語以上あれば、1 公演だけの語は外す
  const many = Array.from({length: 13}, (_, i) => `語${i}`);
  assert.equal(Object.fromEntries(countTags([[...many, '一度だけ'], many]))['一度だけ'], undefined);
});

test('the layout never overlaps and stays inside the box', () => {
  const words = countTags(TAGS);
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

test('the panel: too few performances with tags says why instead of drawing', () => {
  const few = panel(TAGS.slice(0, MIN_STAGES - 1), 12);
  assert.match(few, /あらすじのタグがある公演がまだ 4 公演なので、雲を描いていません/);
  assert.doesNotMatch(few, /class="wcloud"/);
  const html = FIGS.words([], {tags: TAGS, nSeen: 12}, 720);
  assert.match(html, /ことばの雲 ── 観た舞台のタグから/);
  assert.match(html, /いちばん多いのは <b>「運命」の 3 公演<\/b>/);
  assert.match(html, /観た 12 公演のうち、あらすじのタグがある 5 公演から作っています/);
  assert.match(html, /<text class="w0"[^>]*><title>#運命：3 公演に付いている<\/title>運命<\/text>/);
});

test('眺める sends the tags of the performances seen: hand-entered first, then the card, then past stages', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const ins = sqlite.prepare("INSERT INTO past_stage(stage_id,title,tkey,start,end,venue,grp,pref,people,synopsis) VALUES(?,?,?,'2025-07-01','2025-08-30','劇場A','劇団甲','東京都',?,'')");
    ins.run('900', '過去の芝居', '過去の芝居', JSON.stringify([['出演', '俳優甲'], ['#題材', '戦争'], ['#題材', '家族'], ['#題材', '戦争']]));
    ins.run('901', '直した芝居', '直した芝居', JSON.stringify([['#題材', '直す前']]));
    ins.run('902', '無い芝居', '無い芝居', JSON.stringify([['出演', '俳優乙']]));
    ins.run('903', 'カードの芝居', 'カードの芝居', JSON.stringify([['#題材', '索引の語']]));
    ins.run('904', '題材なしの芝居', '題材なしの芝居', JSON.stringify([['#題材', '消した語']]));
    sqlite.exec(`INSERT INTO stage_override(stage_id,themes,updated_at) VALUES('901','["手で入れた題材","運命"]','2026-10-24'),('904','[]','2026-10-24')`);
    sqlite.exec(`INSERT OR REPLACE INTO rec_meta(k,v) VALUES('rec_card','c1')`);
    sqlite.exec(`INSERT INTO rec_card(ver,stage_id,html,ws) VALUES('c1','903','<article></article>','カードの題材\nｍｕｓｉｃ')`);
    for (const [title, sid] of [['過去の芝居', '900'], ['直した芝居', '901'], ['無い芝居', '902'], ['カードの芝居', '903'], ['題材なしの芝居', '904']]) {
      await step(env, a, {post: '/api/add_work', body: {title, date: '2025-08-20', stage_id: sid}});
    }
    const html = (await step(env, a, {get: '/api/screen/records'})).body.body_html;
    assert.match(html, /<div data-fig="words"><\/div>/);
    const src = JSON.parse(/<script id="figs-src" type="application\/json">([\s\S]*?)<\/script>/.exec(html)[1]);
    assert.deepEqual(src.tags.map(t => t.join('・')).sort(), ['カードの題材・ｍｕｓｉｃ', '手で入れた題材・運命', '戦争・家族'].sort());
    assert.equal(src.syn, undefined);   // あらすじの本文はもう送らない
    assert.equal(src.nSeen, 5);
  } finally { sqlite.close(); }
});
