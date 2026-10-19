// 推薦理由の太字（人物・形式）を押すと開く、その人・その形式の画面（起案者の指示 2026-10-19「おすすめ理由になってる項目の黒太字
// 押したら、各個別ページに飛ぶようにして。たとえば出演者なら飛んだ先に取得できる経歴やプロフィール、たぐり内にある過去の公演と
// 今後の公演が見られる」）。
// - 人物（/recommend/person?n=名前&r=役職）: たぐりにある、これから観られる公演（索引 rec_credit の (役職, 名前)。主な役職をまとめて
//   主キーで引く）・過去の公演（探すと同じ。名前の索引 pastidx と題名）・自分の観た記録。経歴・プロフィールは、たぐりでは
//   集めていないので、外のサイトで調べる道（Wikipedia・Google の検索）を置く（その場で外のサイトは読まない）
// - 形式（/recommend/kind?a=#形式&w=ミュージカル）: その形式の付いた、これから観られる公演（rec_credit の (#形式, 語)）
// どちらも、これから観られる公演はカードで 1 ページ ENT_PER 件（探すと同じ）。
// 無料枠（D1 の読み取り）: 1 回開くごとに、索引の当たった行（主キーで引く。数十行）＋ 出すカード 5 件ぶんの行＋本人の答え・記録
import {E} from './py.js';
import {compose, cardTemplates, posterHtml} from './cards.js';
import {stageInfo, fallbackTemplate} from './fallback.js';
import {tourBlock} from './schedule.js';
import {withTour} from './recommend.js';
import {reactionsOf} from './lists.js';
import {loadWorks} from './works.js';
import {pastHits, pagerHtml, UP_PER} from './search.js';
import {peopleByKey} from './diary.js';
import {SEED_ROLES, FAV_SPREAD_W} from '../recommend.js';

const ENT_ROWS = 300;   // 当たった公演（会場ごと）をここまでで打ち切る
// 人の画面で引く役職（推薦の種・関わりのある人の広げ方に出てくるもの）。リンクの役職は必ず入れる
const PERSON_ROLES = [...new Set([...SEED_ROLES, ...Object.keys(FAV_SPREAD_W)])];
const STATE = s => s.owned ? '観る予定です（すでに持っていると答えました）' : s.interest === 1 ? '追いかけています（興味ありと答えました）'
  : s.interest === 0 ? '興味なしと答えました' : s.interest === 2 ? '行けないと答えました' : s.interest === 3 || s.interest === 4 ? '候補から消しました' : '';
const clip = (v, n) => Array.from(String(v || '').trim()).slice(0, n).join('');
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/** (key [role, person]...) -> the coming stages, one per production: [{stage_id, sids, start, roles}] */
async function comingStages(ctx, keys) {
  if (!keys.length) return [];
  const hits = new Map();
  for (let i = 0; i < keys.length; i += 45) {
    const part = keys.slice(i, i + 45);
    const {results} = await ctx.db.prepare(`SELECT role, stage_id FROM rec_credit WHERE ver=(SELECT v FROM rec_meta WHERE k='current')
      AND (role,person) IN (VALUES ${part.map(() => '(?,?)').join(',')}) LIMIT ${ENT_ROWS}`).bind(...part.flat()).all();
    for (const r of results) {
      const sid = String(r.stage_id);
      if (!hits.has(sid)) hits.set(sid, new Set());
      hits.get(sid).add(r.role);
    }
  }
  const sids = [...hits.keys()];
  const rows = [];
  for (let i = 0; i < sids.length; i += 90) {
    const part = sids.slice(i, i + 90);
    const {results} = await ctx.db.prepare(`SELECT stage_id, tour, start, end FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) if (!r.end || String(r.end).replaceAll('/', '-') >= ctx.today) rows.push({...r, stage_id: String(r.stage_id), start: String(r.start || '').replaceAll('/', '-')});
  }
  const byTour = new Map();
  for (const r of rows) {
    const g = r.tour || 'stage:' + r.stage_id;
    if (!byTour.has(g)) byTour.set(g, []);
    byTour.get(g).push(r);
  }
  return [...byTour.values()].map(vs => {
    vs.sort((a, b) => cmp(a.start || '9999', b.start || '9999'));
    return {stage_id: vs[0].stage_id, start: vs[0].start, sids: vs.map(v => v.stage_id), roles: [...new Set(vs.flatMap(v => [...hits.get(v.stage_id)]))]};
  }).sort((a, b) => cmp(a.start || '9999', b.start || '9999'));
}

/** The cards of one page of productions, with the user's answer and the line `top(prod)` at the head. */
async function cards(ctx, show, top) {
  if (!show.length) return [];
  const react = await reactionsOf(ctx);
  const {html, posters} = await cardTemplates(ctx.db, show.map(r => r.stage_id));
  const bare = show.map(r => r.stage_id).filter(sid => !html.has(sid));
  if (bare.length) for (const [sid, s] of await stageInfo(ctx.db, bare)) html.set(sid, fallbackTemplate(s));
  const info = await stageInfo(ctx.db, show.flatMap(r => r.sids));
  return show.filter(r => html.has(r.stage_id)).map(r => {
    const ans = r.sids.map(s => react.get(s)).filter(Boolean);
    const st = {owned: ans.some(a => a.owned === 1), interest: ans.find(a => a.interest !== undefined)?.interest};
    const line = top(r) + (STATE(st) ? `<li class="rs state">${E(STATE(st))}</li>` : '');
    const pic = posters.get(r.stage_id) || r.sids.map(s => posters.get(s)).find(Boolean);
    const card = compose(html.get(r.stage_id), r.stage_id, st.interest === 1 && !st.owned ? 'interest' : 'recommend', {top: line, poster: pic ? posterHtml(pic) : ''});
    return withTour(card, tourBlock(r.sids.map(s => info.get(s)).filter(Boolean), r.stage_id, ctx.today));
  });
}

const pageOf = (params, k) => Math.max(1, Number.parseInt(params.get(k) || '1', 10) || 1);
const hrefOf = (path, params, key, anchor) => n => {
  const u = new URLSearchParams(params);
  u.delete('t'); u.set(key, String(n));
  return `${path}?t=__TAGURI_TOKEN__&amp;${E(u.toString())}#${anchor}`;
};
function upcomingBlock(prods, shown, page, href, empty) {
  const last = Math.max(1, Math.ceil(prods.length / UP_PER));
  return `<h2 id="ent-up">これから観られる公演 ${prods.length} 件</h2>`
    + (shown.length ? `<p class="lead">上演日の近い順に並べています。順位は付けていません。<b>ここから「興味あり」を押すと、「興味あり」の一覧に入ります。</b></p>`
      + `<div class="tickets">${shown.join('')}</div>${pagerHtml(prods.length, UP_PER, Math.min(page, last), href)}` : `<p class="empty">${empty}</p>`);
}

export async function personScreen(params, ctx) {
  const name = clip(params.get('n'), 60), role = clip(params.get('r'), 20);
  if (!name) return {title: '人物', body_html: '<h1>人物</h1><p class="empty">名前がありません。おすすめ理由の名前を押すと、その人の公演がここに並びます。</p>'};
  const roles = [...new Set([role, ...PERSON_ROLES].filter(Boolean))];
  const prods = await comingStages(ctx, roles.map(r => [r, name]));
  const up = pageOf(params, 'up'), last = Math.max(1, Math.ceil(prods.length / UP_PER)), p = Math.min(up, last);
  const shown = await cards(ctx, prods.slice((p - 1) * UP_PER, p * UP_PER),
    r => `<li class="rs found"><span class="net">人物</span>${E(r.roles.join('・'))} <b>${E(name)}</b></li>`);
  // 過去の公演（探すと同じ。観た・観ればよかったをこの場で押せる）
  const ws = await loadWorks(ctx);
  const [pastHtml] = await pastHits(ctx, name, ws, pageOf(params, 'pp'), hrefOf('/recommend/person', params, 'pp', 'past-hits'));
  // 自分の観た記録のうち、この人の名前がある作品
  const people = await peopleByKey(ctx, ws);
  const key = name.normalize('NFKC').replace(/[\s　]+/gu, '');
  const mine = ws.filter(w => !w.unseen && (people[w.work_key] || []).some(([, n]) => String(n).normalize('NFKC').replace(/[\s　]+/gu, '') === key))
    .sort((a, b) => cmp(b.first_date || '', a.first_date || ''));
  const mineHtml = `<h2>観た記録 ${mine.length} 件</h2>` + (mine.length
    ? `<ul class="entmine">${mine.map(w => `<li><a href="/records/works?t=__TAGURI_TOKEN__#w-${E(encodeURIComponent(w.work_key))}">${E(w.title)}</a><span>${E(w.first_date || '')}${w.verdict ? '・' + E(w.verdict) : ''}</span></li>`).join('')}</ul>`
    : '<p class="empty">観た記録の中には、この名前のある作品はありません（出演者が分かっている記録だけを見ています）。</p>');
  const q = encodeURIComponent(name);
  const profile = `<section class="card entprof"><h2>経歴・プロフィール</h2>
<p class="lead">たぐりでは、人の経歴やプロフィールは集めていません。<b>同じ名前の別の人がいることもあるので</b>、外のサイトで確かめてください（新しいタブで開きます）。</p>
<p class="entext"><a href="https://ja.wikipedia.org/w/index.php?search=${q}" target="_blank" rel="noopener noreferrer">Wikipedia で調べる ↗</a>
<a href="https://www.google.com/search?q=${q}" target="_blank" rel="noopener noreferrer">Google で調べる ↗</a></p></section>`;
  const body = `<h1>${E(name)}</h1>
<p class="hsub">${role ? E(role) + 'として、' : ''}たぐりにある公演と、あなたの観た記録です。</p>
${profile}
${upcomingBlock(prods, shown, up, hrefOf('/recommend/person', params, 'up', 'ent-up'), 'いま、たぐりにある、これから観られる公演の中には見つかりませんでした。')}
${pastHtml || '<h2>過去の公演（2019 年〜）</h2><p class="empty">たぐりにある過去の公演の中には見つかりませんでした。</p>'}
${mineHtml}`;
  return {title: name, body_html: body};
}

export async function kindScreen(params, ctx) {
  const axis = clip(params.get('a'), 20), word = clip(params.get('w'), 30);
  if (!axis.startsWith('#') || !word) return {title: '形式', body_html: '<h1>形式</h1><p class="empty">形式がありません。おすすめ理由の形式を押すと、その形式の公演がここに並びます。</p>'};
  const label = axis.replace(/^#+/, '');
  const prods = await comingStages(ctx, [[axis, word]]);
  const up = pageOf(params, 'up'), last = Math.max(1, Math.ceil(prods.length / UP_PER)), p = Math.min(up, last);
  const shown = await cards(ctx, prods.slice((p - 1) * UP_PER, p * UP_PER), () => `<li class="rs found"><span class="net">形式</span>${E(label)} <b>${E(word)}</b></li>`);
  const body = `<h1>${E(label)}「${E(word)}」の公演</h1>
<p class="hsub">${E(label)}が「${E(word)}」の、たぐりにある公演です。</p>
${upcomingBlock(prods, shown, up, hrefOf('/recommend/kind', params, 'up', 'ent-up'), `いま、${E(label)}が「${E(word)}」の、これから観られる公演はありません。`)}`;
  return {title: `${label}「${word}」`, body_html: body};
}

export const entityScreens = {screens: {person: personScreen, kind: kindScreen}, actions: {}};
