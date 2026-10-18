// あらすじのハッシュタグ（題材の語）の付いた、これから観られる公演の一覧（/recommend/tag?w=語）。
// 起案者の指示（2026-10-18）「あらすじのハッシュタグ押したらそれがついてる公演一覧が出るようにして」。
//
// カードの「#語」は、作り置きのカード（rec_card）のあらすじの枠の題材（build_cards.py の c["themes"]＝themes.jsonl の
// elements の word）と、管理者が手で入れた題材（stage_override.themes）から出ている。ここでも同じ 2 つから引く:
// - rec_card.ws（題材の語を 1 行に 1 つ、recommend2.nz でそろえたもの。migration 0018）に、その語の行がある公演
// - 手で入れた題材がある公演は、手で入れた方で決める（カードの札も手で入れた方に差し替わるため。override.applySynopsis）
// 索引の #題材（rec_credit）は 1 公演 6 語まで・2 文字以上なので、カードに出ている札と食い違う。使わない。
//
// 無料枠（D1 の読み取り。1 日 500 万行）: 1 回開くごとに
//   rec_card のいまの版のうち終わっていない行を 1 回なめる（いまは約 1,350 行。索引が無いので行数ぶん読む）
//   ＋ stage_override（手で直した公演だけ。TAG_OVERRIDE_ROWS 行まで）
//   ＋ 出すカード TAG_SHOW 件ぶんの rec_card・poster・stage_override・catalogue・rec_stage（1 件あたり数行）
//   ＋ 本人の答え（reaction、本人の行だけ）
// で、合わせて 2,000 行ほど（〔impl-hashtag-list〕）。公演を並べる行は TAG_ROWS 件で打ち切る。
import {E} from './py.js';
import {ico} from './icons.js';
import {compose, cardTemplates, posterHtml} from './cards.js';
import {stageInfo, fallbackTemplate} from './fallback.js';
import {tourBlock} from './schedule.js';
import {withTour} from './recommend.js';
import {nz, reactionsOf} from './lists.js';

export const TAG_SHOW = 20;            // 1 ページに出すカード（公演ごと）
export const TAG_ROWS = 300;           // 当たった公演（会場ごと）をここまでで打ち切る
export const TAG_OVERRIDE_ROWS = 500;  // 手で入れた題材を読む行の上限
const MAX_WORD = 30;
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/** The word of ?w= (a leading # dropped, at most MAX_WORD characters). */
export function tagWord(raw) {
  const w = String(raw || '').replace(/^[#＃]+/, '').trim();
  return Array.from(w).slice(0, MAX_WORD).join('');
}

/**
 * The coming stages whose subject words include this word: [{stage_id, title, tour, start, end, pref, hit}],
 * every coming venue of a production that has a hit (hit: the venue itself has the word).
 */
export async function taggedStages(ctx, word) {
  const key = nz(word);
  if (!key) return [];
  // 終わっていない行を 1 回なめ、当たりの印（hit）を付けて返す。ツアーのほかの会場（同じ tour）も同じ 1 回で拾う
  const {results} = await ctx.db.prepare(`SELECT stage_id,title,tour,start,end,pref,instr(char(10)||ws||char(10),?)>0 AS hit FROM rec_card
    WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND (end='' OR end>=?)`).bind('\n' + key + '\n', ctx.today).all();
  const rows = new Map(results.map(r => [String(r.stage_id), {...r, stage_id: String(r.stage_id), hit: Boolean(r.hit)}]));
  // 手で入れた題材（管理画面）。入っている公演は、カードの札もそれに差し替わるので、そちらで当たりを決め直す
  let ovs = [];
  try {
    ({results: ovs} = await ctx.db.prepare('SELECT stage_id,themes FROM stage_override WHERE themes IS NOT NULL LIMIT ?').bind(TAG_OVERRIDE_ROWS).all());
  } catch { ovs = []; }   // migration 0028 not applied yet
  for (const o of ovs) {
    let ts = null;
    try { ts = JSON.parse(o.themes); } catch { ts = null; }
    if (!Array.isArray(ts)) continue;
    const r = rows.get(String(o.stage_id));
    if (r) r.hit = ts.some(t => nz(t) === key);
  }
  const hitTours = new Set(), out = [];
  for (const r of rows.values()) if (r.hit && r.tour) hitTours.add(r.tour);
  for (const r of rows.values()) if (r.hit || (r.tour && hitTours.has(r.tour))) out.push(r);
  return out;
}

/** One row per production (the tour key, or the stage alone): {stage_id: the earliest venue with the word, sids, start}. */
export function byProduction(stages) {
  const groups = new Map();
  for (const r of stages) {
    const g = r.tour || 'stage:' + r.stage_id;
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(r);
  }
  const out = [];
  for (const vs of groups.values()) {
    const hits = vs.filter(v => v.hit);
    if (!hits.length) continue;
    const first = hits.reduce((a, b) => (cmp(b.start || '9999', a.start || '9999') < 0 ? b : a));
    vs.sort((a, b) => cmp(a.start || '9999', b.start || '9999') || cmp(a.stage_id, b.stage_id));
    out.push({stage_id: first.stage_id, title: first.title, start: first.start || '', sids: vs.map(v => v.stage_id)});
  }
  return out.sort((a, b) => cmp(a.start || '9999', b.start || '9999') || cmp(a.stage_id, b.stage_id));
}

const STATE = [['owned', '観る予定です（すでに持っていると答えました）'], ['interest', '追いかけています（興味ありと答えました）']];

export async function taggedScreen(params, ctx) {
  const word = tagWord(params.get('w'));
  const page = Math.max(1, Number.parseInt(params.get('p') || '1', 10) || 1);
  const back = '<p class="lede"><a href="/recommend?t=__TAGURI_TOKEN__">← 今週のおすすめに戻る</a></p>';
  if (!word) {
    return {title: '題材の公演', body_html: `<h1>題材の公演</h1>${back}<p class="empty">題材の語がありません。カードのあらすじの下のハッシュタグを押すと、その題材の公演がここに並びます。</p>`};
  }
  const prods = byProduction((await taggedStages(ctx, word)).slice(0, TAG_ROWS));
  const last = Math.max(1, Math.ceil(prods.length / TAG_SHOW));
  const p = Math.min(page, last);
  const show = prods.slice((p - 1) * TAG_SHOW, p * TAG_SHOW);
  const react = show.length ? await reactionsOf(ctx) : new Map();
  const {html, posters} = await cardTemplates(ctx.db, show.map(r => r.stage_id));
  // カードが作り置きに無い公演はここには出ない（rec_card から引いているため）。念のため一覧と索引から描く
  const bare = show.map(r => r.stage_id).filter(sid => !html.has(sid));
  if (bare.length) for (const [sid, s] of await stageInfo(ctx.db, bare)) html.set(sid, fallbackTemplate(s));
  const info = await stageInfo(ctx.db, show.flatMap(r => r.sids));
  const cards = show.filter(r => html.has(r.stage_id)).map(r => {
    const ans = r.sids.map(s => react.get(s)).filter(Boolean);
    const owned = ans.some(a => a.owned === 1), interest = ans.find(a => a.interest !== undefined)?.interest;
    const st = owned ? STATE[0][1] : interest === 1 ? STATE[1][1] : interest === 0 ? '興味なしと答えました' : interest === 2 ? '行けないと答えました' : '';
    const top = `<li class="rs found"><span class="net">題材</span>#${E(word)}</li>` + (st ? `<li class="rs state">${E(st)}</li>` : '');
    const pic = posters.get(r.stage_id) || r.sids.map(s => posters.get(s)).find(Boolean);
    const card = compose(html.get(r.stage_id), r.stage_id, interest === 1 && !owned ? 'interest' : 'recommend', {top, poster: pic ? posterHtml(pic) : ''});
    return withTour(card, tourBlock(r.sids.map(s => info.get(s)).filter(Boolean), r.stage_id, ctx.today));
  });
  const q = `t=__TAGURI_TOKEN__&amp;w=${encodeURIComponent(word)}`;
  const pager = last <= 1 ? '' : `<div class="mfoot">${p > 1 ? `<a class="mpage" href="/recommend/tag?${q}&amp;p=${p - 1}">← 前の ${TAG_SHOW} 件</a>` : '<span class="mpage off">最初のページです</span>'}`
    + `<span class="mp">${p} / ${last} ページ</span>`
    + `${p < last ? `<a class="mpage" href="/recommend/tag?${q}&amp;p=${p + 1}">次の ${Math.min(TAG_SHOW, prods.length - p * TAG_SHOW)} 件 →</a>` : '<span class="mpage off">これで最後です</span>'}</div>`;
  const body = `<h1><span class="ftag big">#${E(word)}</span> の公演</h1>
${back}
<p class="lead">あらすじから読み取った題材に <b>#${E(word)}</b> が付いている、これから観られる公演です。上演日の近い順に並べています。順位は付けていません。<b>ここから「興味あり」を押すと、「興味あり」の一覧に入ります。</b>
題材は、あらすじが読めた公演にだけ付いています。人名・団体・題名でも探したいときは<a href="/search?t=__TAGURI_TOKEN__&amp;q=${encodeURIComponent(word)}">探す</a>を使ってください。</p>
${prods.length ? `<p class="rcount">全 ${prods.length} 件${last > 1 ? `中 ${(p - 1) * TAG_SHOW + 1}〜${(p - 1) * TAG_SHOW + show.length} 件目を表示中` : ''}</p>` : ''}
${cards.length ? `<div class="tickets">${cards.join('')}</div>` : `<p class="empty">いま、題材に「${E(word)}」が付いている、これから観られる公演はありません。</p>`}
${pager}`;
  return {title: `#${word}`, body_html: body};
}

export const taggedScreens = {screens: {tagged: taggedScreen}, actions: {}};
