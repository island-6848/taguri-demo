// Real screen HTML and controls, with ranking/database calls replaced by a tiny catalogue.
// Used by tools/taguri/check_recommend_ux.py; no production account or external calls.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {weightForm, tunedWeights, GROUP_DEFAULT} from '../../src/screens/weights.js';
import {prefForm, regionCounts, PAGE_PREF_NOTE} from '../../src/screens/prefs.js';
import {buttons, whyNote, noNote} from '../../src/screens/cards.js';
import {E} from '../../src/screens/py.js';
import {ico} from '../../src/screens/icons.js';

const source = readFileSync(new URL('../../src/screens/recommend.js', import.meta.url), 'utf8');
const card = sid => `<article class="ticket recommend" data-stage="${sid}" data-yen="4000-4000">
<div class="stub"><span class="sn">No.01</span><div class="sd"><b>11/1</b></div></div><div class="perf"></div>
<div class="body"><div class="main"><h3>公演${sid}・長い題名でも回答を直せる舞台</h3>
<div class="meta"><span class="grp">劇団甲</span><span class="sep">／</span>劇場甲（東京都）</div>
<div class="when">2026/11/1〜11/8<span class="price">一般 4,000円</span></div>
<div class="sale"><span class="pill">発売済み</span></div><div class="cast">出演：俳優甲</div>
<div class="syn"><span class="txt">小さな劇場から始まる物語です。</span></div>
<div class="whyh">おすすめ理由</div><ul class="why"><li>好きな公演の出演者が参加しています</li></ul>
<div class="act">${buttons(sid)}</div>${whyNote(sid)}${noNote(sid, '', true)}</div></div></article>`;

const screen = source.slice(source.indexOf('export async function recommendScreen('), source.indexOf('// ---------------------------------------------------------------- react'))
  .replace('export async function', 'async function');
const tips = source.slice(source.indexOf('const TIP_ART ='), source.indexOf('// Groups kept'));
async function scene({empty = false, prefs = [], tuned = false} = {}) {
  const groups = empty ? [] : [{stage_id: '101', venues: [{pref: '東京都'}]}, {stage_id: '102', venues: [{pref: '東京都'}]}];
  const sandbox = vm.createContext({E, ico, weightForm, tunedWeights, prefForm, regionCounts, PAGE_PREF_NOTE,
    VERSION: 'ux-test', KINDS: [],
    prefsFor: async () => prefs,
    rankedGroups: async () => ({groups, weights: GROUP_DEFAULT, titles: new Map(), n_scored: groups.length, diag: {}}),
    filtered: gs => ({rows: prefs.includes('大阪府') ? [] : gs, hit: gs.length}),
    cardsHtml: async (_, rows) => rows.map(r => card(r.stage_id)),
    prefCounts: () => ({'東京都': groups.length}),
    loadDeclared: async () => ({}), loadDeclined: async () => tuned ? ['使わない語'] : [], loadKindOff: async () => [],
    declinedBox: () => '<details class="pbox" id="declined"><summary>使わない言葉 <b>なし</b></summary></details>',
    kindOffBox: () => '<details class="pbox" id="kind-off"><summary>使わない理由 <b>なし</b></summary></details>',
    unratedEnds: async () => [],
    params: new URLSearchParams(),
    ctx: {db: {prepare: () => ({first: async () => ({n: 0, v: 2}), bind() { return this; }})}},
  });
  return vm.runInContext(tips + '\n' + screen + '\nrecommendScreen(params, ctx)', sandbox);
}
const scenes = {normal: await scene(), empty: await scene({empty: true}), filtered: await scene({prefs: ['大阪府']}),
  tuned: await scene({tuned: true})};
console.log(JSON.stringify({scenes, fill: card('103')}));
