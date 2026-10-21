// X のポストの URL を貼ると、その本文を感想に入れる（起案者の指示 2026-10-21「リンク貼る方式にしましょう」）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {postUrl, parseEmbed, readPost, splitMark, mark} from '../src/x-post.js';
import {impressionParts} from '../src/screens/row.js';
import {setup, signIn, step} from './screens/harness.js';

// publish.twitter.com/oembed が返す html の形（omit_script=1）
const HTML = '<blockquote class="twitter-tweet" data-lang="ja" data-dnt="true"><p lang="ja" dir="ltr">二幕の照明が忘れられない。<br>主演の声がよく通っていた &amp; 客席も温かかった <a href="https://twitter.com/hashtag/%E8%88%9E%E5%8F%B0?src=hash&amp;ref_src=twsrc%5Etfw">#舞台</a> <a href="https://t.co/AbC">pic.twitter.com/AbC</a></p>&mdash; 観劇の人 (@kangeki) <a href="https://twitter.com/kangeki/status/1847000000000000001?ref_src=twsrc%5Etfw">October 8, 2026</a></blockquote>';

test('postUrl: x.com / twitter.com のポストの URL だけを x.com の形にそろえる', () => {
  assert.equal(postUrl('https://twitter.com/kangeki/status/1847000000000000001?s=20'), 'https://x.com/kangeki/status/1847000000000000001');
  assert.equal(postUrl(' https://x.com/kangeki/status/12/photo/1 '), 'https://x.com/kangeki/status/12');
  assert.equal(postUrl('https://mobile.twitter.com/a_b/statuses/99'), 'https://x.com/a_b/status/99');
  for (const bad of ['https://x.com/kangeki', 'https://example.com/a/status/1', 'x.com/a/status/1', 'https://x.com/a/status/1 と書いた'])
    assert.equal(postUrl(bad), '', bad);
});

test('parseEmbed: 本文（改行・記号・ハッシュタグを残し、画像のリンクは外す）と日付', () => {
  assert.deepEqual(parseEmbed(HTML), {text: '二幕の照明が忘れられない。\n主演の声がよく通っていた & 客席も温かかった #舞台', date: '2026-10-08'});
});

test('readPost: 読めたら本文と出どころの行、読めなければ理由', async () => {
  let asked = '';
  const ok = await readPost('https://x.com/kangeki/status/1847000000000000001', async u => { asked = u; return new Response(JSON.stringify({html: HTML})); });
  assert.match(asked, /^https:\/\/publish\.twitter\.com\/oembed\?url=https%3A%2F%2Ftwitter\.com%2Fkangeki%2Fstatus%2F1847000000000000001&omit_script=1&dnt=true/);
  assert.equal(ok.status, 200);
  assert.equal(ok.body.mark, '[X 2026-10-08] https://x.com/kangeki/status/1847000000000000001');
  assert.equal((await readPost('https://x.com/k/status/1', async () => new Response('', {status: 404}))).status, 404);
  assert.equal((await readPost('https://x.com/k/status/1', async () => { throw new Error('down'); })).status, 502);
  let called = false;
  assert.equal((await readPost('https://example.com/', async () => { called = true; })).status, 400);
  assert.equal(called, false);                                     // URL でなければ外に問い合わせない
});

test('splitMark と画面: 出どころの行は文から外し、「X で見る」の行にする。書き直しのために data-xsrc に残す', () => {
  const note = '照明がよかった\n\n' + mark('2026-10-08', 'https://x.com/kangeki/status/12');
  assert.deepEqual(splitMark(note), {body: '照明がよかった', date: '2026-10-08', url: 'https://x.com/kangeki/status/12'});
  assert.deepEqual(splitMark('ふつうの感想 https://x.com/a/status/1'), {body: 'ふつうの感想 https://x.com/a/status/1', date: '', url: ''});
  const [, html] = impressionParts({work_key: 'w1', note_impression: note});
  assert.match(html, /<span class="int" data-xsrc="\[X 2026-10-08\] https:\/\/x\.com\/kangeki\/status\/12">照明がよかった<\/span>/);
  assert.match(html, /<span class="xsrc">2026\/10\/08 の X のポストから · <a href="https:\/\/x\.com\/kangeki\/status\/12" target="_blank" rel="noopener noreferrer">X で見る ↗<\/a><\/span>/);
  assert.doesNotMatch(impressionParts({work_key: 'w2', note_impression: '照明がよかった'})[1], /xsrc/);
});

test('/api/x_post はログインした人だけ', async () => {
  const {env, sqlite} = setup();
  try {
    const res = await step(env, '', {get: '/api/x_post?url=' + encodeURIComponent('https://x.com/a/status/1')});
    assert.equal(res.status, 401);
    const a = await signIn(env);
    assert.equal((await step(env, a, {get: '/api/x_post?url=' + encodeURIComponent('https://example.com/')})).status, 400);
  } finally { sqlite.close(); }
});
