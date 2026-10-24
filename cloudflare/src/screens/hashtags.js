// 感想のハッシュタグ。tools/taguri/hashtags.py と app._hashtags_html / app.note_tags の移植
// （起案者の指示 2026-10-14「感想を書くとき、ハッシュタグをユーザーが独自で作って検索できるようにして」）。
import {gradeText} from './grade.js';
import {E, quote} from './py.js';
import {splitMark} from '../x-post.js';
import {xSource} from './row.js';

const TAG = /[#＃]([^\s#＃、。，,．.!！?？「」『』（）()\[\]【】<>＜＞]{1,30})/gu;

/** hashtags.tags_in */
export function tagsIn(text) {
  const out = [];
  for (const m of String(text || '').matchAll(TAG)) {
    const t = m[1].normalize('NFKC');
    if (t && !out.includes(t)) out.push(t);
  }
  return out;
}

/** hashtags.counts: [tag, n] by count desc, then name (code point order like Python) */
export function tagCounts(texts) {
  const n = new Map();
  for (const t of texts) for (const tag of tagsIn(t)) n.set(tag, (n.get(tag) || 0) + 1);
  const cp = s => Array.from(s).map(c => c.codePointAt(0));
  const byName = (a, b) => { const x = cp(a), y = cp(b); for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i] - y[i]; return x.length - y.length; };
  return [...n.entries()].sort((a, b) => (b[1] - a[1]) || byName(a[0], b[0]));
}

/** app.note_tags */
export const noteTags = works => tagCounts(works.map(w => w.note_impression || '')).map(([t]) => t).slice(0, 40);

/** app._hashtags_html */
export function hashtagsHtml(all, tag = '') {
  tag = String(tag || '').replace(/^[#＃]+/, '').trim().normalize('NFKC');
  tag = Array.from(tag).slice(0, 30).join('');
  const cnt = tagCounts(all.map(w => w.note_impression || ''));
  const head = '<p class="lede">感想の中に <b>#タグ</b> と書くと、タグがここに並びます。押すと、そのタグの感想をまとめて見られます'
    + '（例: #泣いた #また観たい #会場がよかった）。</p>';
  if (!cnt.length) return '<section class="htags">' + head + '</section>';
  const chips = cnt.map(([t, n]) =>
    `<a class="htag${t === tag ? ' on' : ''}" href="/rate/notes?tag=${quote(t)}&amp;t=__TAGURI_TOKEN__">`
    + `#${E(t)}<span class="hn">${n}</span></a>`).join('');
  const out = [`<section class="htags">${head}<div class="htl">${chips}</div>`];
  if (tag) {
    const key = w => w.last_date || w.first_date || '';
    // Python: list.sort(key=..., reverse=True) is stable
    const hit = all.filter(w => tagsIn(w.note_impression || '').includes(tag))
      .map((w, i) => [w, i]).sort((a, b) => (key(a[0]) < key(b[0]) ? 1 : key(a[0]) > key(b[0]) ? -1 : a[1] - b[1])).map(x => x[0]);
    const rows = hit.map(w =>
      `<li><span class="hd">${E(w.last_date || w.first_date || '')}</span>`
      + `<b>${E(w.title || '')}</b>${w.verdict ? ' ' + E(gradeText(w.verdict)) : ''}`
      + `<p class="int">${E(splitMark(w.note_impression).body)}</p>${xSource(splitMark(w.note_impression))}</li>`).join('');
    out.push(`<h2>#${E(tag)} の感想 ── ${hit.length} 件</h2>`
      + `<p><a href="/rate/notes?t=__TAGURI_TOKEN__">タグの選択をやめる</a></p>`
      + `<ul class="htagged">${rows}</ul>`);
  }
  out.push('</section>');
  return out.join('');
}
