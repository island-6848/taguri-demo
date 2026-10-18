// The prefecture filter shared by おすすめ・開幕リマインド・設定 (render_recommend.pref_form,
// prefmap.regions_html / region_counts, app.read_pref_setting, serve.get_prefs).
// The map itself (prefmap.map_html) is not drawn: its outlines are not in D1.
import {E, ValueError} from './py.js';
import {ico} from './icons.js';

export const PREFS = ['北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
  '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
  '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県',
  '岐阜県', '静岡県', '愛知県', '三重県',
  '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県',
  '鳥取県', '島根県', '岡山県', '広島県', '山口県',
  '徳島県', '香川県', '愛媛県', '高知県',
  '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'];
export const REGIONS = [['北海道', ['北海道']], ['東北', ['青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県']],
  ['関東', ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県']],
  ['中部', ['新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県']],
  ['近畿', ['三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県']],
  ['中国', ['鳥取県', '島根県', '岡山県', '広島県', '山口県']], ['四国', ['徳島県', '香川県', '愛媛県', '高知県']],
  ['九州・沖縄', ['福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']]];
export const TOP = 15;
export const SETTING_KEY = 'pref_filter';     // the default chosen in 設定 (app.PREF_SETTING_KEY)

/** prefmap.region_counts: productions (not venues) per region. items: [{key, prefs: [...]}] */
export function regionCounts(items) {
  const where = new Map(REGIONS.flatMap(([r, ps]) => ps.map(p => [p, r])));
  const n = Object.fromEntries(REGIONS.map(([r]) => [r, new Set()]));
  for (const it of items) for (const p of new Set(it.prefs.filter(Boolean))) if (where.has(p)) n[where.get(p)].add(it.key);
  return Object.fromEntries(Object.entries(n).map(([r, v]) => [r, v.size]));
}
/** prefmap.regions_html */
export function regionsHtml(counts, rcounts, all = false) {
  const out = REGIONS.map(([r, ps]) => {
    const live = all ? ps : ps.filter(p => counts[p]);
    return live.length ? `<button type="button" class="prg" data-prefs="${live.join(' ')}">${r}地方<span class="pn">${rcounts[r] || 0}件</span></button>` : '';
  }).join('');
  return `<div class="prgs" role="group" aria-label="地方でまとめて選ぶ"><span class="prgl">地方でまとめて選ぶ</span>${out}<button type="button" class="prg clr">選択を消す</button></div>`;
}

// どのページでも同じ「場所」の説明（起案者の指示 2026-10-18。絞り込みはそのページの中だけ、いつも使う県は設定に保存する）
export const PAGE_PREF_NOTE = '他ページでもこの絞り込みを適用したい場合は、<a href="/settings?t=__TAGURI_TOKEN__">設定</a>から表示する都道府県の規定を設定してください。';
const PREF_NOTE = `都道府県は<b>いくつでも同時に選べます</b>。選んだ県で観られる公演を、好みに合いそうな順に <b>${TOP} 件</b>まで表示します。数字はその県で観られる件数です。<b>選ばなければ全国です。</b>ツアーで来る公演も入ります。本拠地が他県でも、選んだ県の会場に来る公演は、その会場の日程で表示します。`;
/** render_recommend.pref_form, with the region buttons above the chips (prefmap.panel without the map). */
export function prefForm(counts, prefs, action = '/recommend', note = '', hidden = {}, rcounts = null) {
  const keep = new Set(prefs);
  const chips = PREFS.filter(p => counts[p]).map(p => `<label class="pchip${keep.has(p) ? ' on' : ''}">`
    + `<input type="checkbox" name="pref" value="${E(p)}"${keep.has(p) ? ' checked' : ''}>`
    + `<span class="pl">${E(p)}</span><span class="pn">${counts[p]}件</span></label>`).join('');
  const now = !keep.size ? '全国' : PREFS.filter(p => keep.has(p)).join('・') + `（${keep.size} 県）`;
  const hiddenIn = Object.entries(hidden).map(([k, v]) => `<input type="hidden" name="${E(k)}" value="${E(v)}">`).join('');
  const hiddenQs = Object.entries(hidden).map(([k, v]) => `&amp;${E(k)}=${E(v)}`).join('');
  return `<form class="pfil" method="get" action="${E(action)}">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<input type="hidden" name="f" value="1">
${hiddenIn}
<details class="pbox">
<summary>${ico('search', 15)}観に行ける場所で絞り込む　いまは<b>${E(now)}</b></summary>
<p class="lead">${note || PREF_NOTE}</p>
${rcounts ? regionsHtml(counts, rcounts) : ''}
<div class="pchw"><span class="prgl">個別で選ぶ</span><div class="pchips">${chips}</div></div>
<div class="pfoot"><button type="submit">${ico('search')}この都道府県で絞り込む</button>
<a class="pall" href="${E(action)}?t=__TAGURI_TOKEN__&amp;f=1${hiddenQs}">全国に戻す</a></div>
</details></form>`;
}

async function readPrefs(ctx, key) {
  const row = await ctx.db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, key).first();
  if (!row) return null;
  try { const v = JSON.parse(row.value); return Array.isArray(v) ? PREFS.filter(p => v.includes(p)) : []; } catch { return []; }
}
async function writePrefs(ctx, key, prefs) {
  await ctx.db.prepare('INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at')
    .bind(ctx.uid, key, JSON.stringify(prefs), new Date(ctx.now).toISOString()).run();
}
/** app.read_pref_setting */
export const readPrefSetting = async ctx => (await readPrefs(ctx, SETTING_KEY)) || [];

/**
 * The filter of this page: a submitted form (?f=1&pref=…) holds it in the page's URL only, otherwise the
 * default chosen in 設定. 起案者の指示 2026-10-17「絞り込んだ都道府県は、そのページ内でのみ維持されるように。
 * 全部の共通の絞り込みは設定で保存しているので」── 以前はページで絞ると保存し（recommend_prefs）、
 * おすすめ・開幕リマインド・開幕の帯のどれにも効いていた。いまは保存しない（D1 の書き込みも減る）。
 */
export async function prefsFor(params, ctx) {
  if (params.has('f')) return PREFS.filter(p => params.getAll('pref').includes(p));
  return readPrefSetting(ctx);
}
/** The page's filter carried on its own links and forms ('' when the page uses the 設定 default). */
export function prefQs(params) {
  if (!params.has('f')) return '';
  return '&amp;f=1' + PREFS.filter(p => params.getAll('pref').includes(p)).map(p => `&amp;pref=${encodeURIComponent(p)}`).join('');
}

export function prefHidden(params) {
  if (!params.has('f')) return '';
  return '<input type="hidden" name="f" value="1">' + PREFS.filter(p => params.getAll('pref').includes(p)).map(p => `<input type="hidden" name="pref" value="${E(p)}">`).join('');
}

/** serve.on_pref_setting: save the default and use it now. */
export async function prefSettingAction(b, ctx) {
  const prefs = b.prefs;
  if (!Array.isArray(prefs) || prefs.length > 47) throw new ValueError('都道府県の並びがおかしい');
  const keep = PREFS.filter(p => prefs.includes(p));
  await writePrefs(ctx, SETTING_KEY, keep);
  return {body: {ok: true, prefs: keep}};
}
