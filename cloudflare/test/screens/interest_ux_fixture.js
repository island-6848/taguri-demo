import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {SORTS, sortRows, monthPick} from '../../src/screens/lists.js';
import {compose, buttons} from '../../src/screens/cards.js';
import {gradeButtons, gradeText} from '../../src/screens/grade.js';
import {E} from '../../src/screens/py.js';

const source = readFileSync(new URL('../../src/screens/lists.js', import.meta.url), 'utf8');
const template = `<article class="ticket recommend" data-stage="101" data-tours="101,102" data-yen="4000-4000">
<div class="stub"><!--mark--></div><div class="perf"></div><div class="body"><div class="main">
<h3>気になる舞台・長い題名でも選び直せる公演</h3><div class="meta"><span class="grp">劇団甲</span>劇場甲</div>
<div class="when">2026年11月1日〜8日<span class="price">一般 4,000円</span></div><div class="sale">発売済み</div>
<div class="cast">出演：俳優甲</div><div class="syn"><span class="txt">小さな劇場の物語です。</span></div>
<div class="whyh"><!--whyh--></div><ul class="why"><!--why--></ul>
<div class="act"><!--btns--></div><!--why_note--><!--no_note--></div></div></article>`;
const rows = [
  {stage_id: '101', title: '舞台甲', start: '2026-11-01', end: '2026-11-08', note: '演出が気になって保存しました。\nあの出演者の新しい役も楽しみです。', src: ''},
  {stage_id: '201', title: '舞台乙', start: '2026-12-01', end: '2026-12-08', note: '', src: ''},
];
const interest = (sid, note = '') => compose(template.replaceAll('101', sid), sid, 'interest', {note, why: '<li>出演者が好みに一致</li>'});
const sort = source.slice(source.indexOf('function sortForm('), source.indexOf('const monthKey'));
const screen = source.slice(source.indexOf('export async function interestScreen('), source.indexOf('const KIND_OFF_LABEL'))
  .replace('export async function', 'async function');
const sandbox = vm.createContext({E, SORTS, sortRows, monthPick, sortOf: p => p.get('s') || 'start', qInt: () => 1,
  buckets: async () => ({tracking: rows}), interestWhy: async () => new Map(), ORIGIN: {},
  cards: async (_ctx, show) => show.map(r => interest(r.stage_id, r.note)),
  params: new URLSearchParams('m=2026-11'), ctx: {}});
const scene = await vm.runInContext(sort + '\n' + screen + '\ninterestScreen(params,ctx)', sandbox);
const recommend = compose(template, '101', 'recommend', {rank: 1});
const owned = compose(template, '101', 'owned');
const favourite = compose(template, '101', 'favourite', {owned: true});
const reminder = '<div class="dgli"><span class="btns" data-stage="101">' + buttons('101') + '</span></div>';
const rating = (scale, current = '') => `<article class="rec-row"><span class="stamp" data-stamp>${current ? gradeText(current) : '未評価'}</span><span class="rb" data-work="work-1">${gradeButtons(scale,current)}</span></article>`;
console.log(JSON.stringify({scene, recommend, owned, favourite, interest: interest('101'),
  ratings: Object.fromEntries(['stars5','stars11','marks2','marks3','marks4'].map(s => [s, rating(s)])),
  savedRatings: [['stars5','4/5'],['stars11','8/11'],['marks2','2/2'],['marks3','2/3'],['marks4','◎']].map(([scale,value]) => ({html:rating(scale,value),value}))}));
