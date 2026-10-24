// Four descriptive comparisons, not an average of other users' preferences.
import {E} from './py.js';
import {peopleByKey} from './diary.js';
import {isDay} from '../client/import-parse.js';

export const ROLES = ['翻訳', '原作', '作曲', '振付'];
export const DURATIONS = ['1日', '2〜7日', '8〜14日', '15〜30日', '31日以上'];
const REGIONS = {
  北海道: ['北海道'], 東北: ['青森県','岩手県','宮城県','秋田県','山形県','福島県'],
  関東: ['茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県'],
  中部: ['新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県','静岡県','愛知県'],
  近畿: ['三重県','滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県'],
  中国: ['鳥取県','島根県','岡山県','広島県','山口県'], 四国: ['徳島県','香川県','愛媛県','高知県'],
  '九州・沖縄': ['福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県'],
};
export const regionOf = pref => Object.keys(REGIONS).find(k => REGIONS[k].includes(pref)) || '';
const parse = (s, fallback) => { try { return JSON.parse(s); } catch { return fallback; } };
const pairs = s => { const a = typeof s === 'string' ? parse(s, []) : s; return Array.isArray(a) ? a.filter(p => Array.isArray(p) && p.length >= 2 && typeof p[0] === 'string' && typeof p[1] === 'string') : []; };
const getCount = (o,k) => Object.hasOwn(o,k) ? o[k] : 0;
const inc = (o, k, n = 1) => { if (k) Object.defineProperty(o,k,{value:getCount(o,k)+n,writable:true,enumerable:true,configurable:true}); };
const emptyAxis = () => ({n: 0, counts: {}});
export const emptyCounts = () => ({total: 0, craft: emptyAxis(), theme: emptyAxis(), region: emptyAxis(), duration: emptyAxis()});
export function durationOf(start, end) {
  if (!isDay(start) || !isDay(end) || end < start) return '';
  const n = (Date.parse(end) - Date.parse(start)) / 86400000 + 1;
  return DURATIONS[n === 1 ? 0 : n <= 7 ? 1 : n <= 14 ? 2 : n <= 30 ? 3 : 4];
}

// Count one saved work once, irrespective of its attendance count or rating.
export function personalCounts(works, meta, credits) {
  const out = emptyCounts(), seen = new Set();
  for (const w of works) {
    if (w.unseen || seen.has(w.work_key)) continue;
    seen.add(w.work_key); out.total++;
    const m = meta[w.stage_id] || {}, ps = pairs(credits[w.work_key]);
    const roles = new Set(ps.filter(p => p[0].trim() && p[1].trim() && !p[0].startsWith('#')).map(p => p[0]));
    if (roles.size) { out.craft.n++; for (const role of ROLES) if (roles.has(role)) inc(out.craft.counts, role); }
    const tags = new Set(pairs(m.people).filter(p => p[0] === '#題材' && p[1].trim()).map(p => p[1].trim()));
    if (tags.size) { out.theme.n++; for (const tag of tags) inc(out.theme.counts, tag); }
    const region = regionOf(m.pref);
    if (region) { out.region.n++; inc(out.region.counts, region); }
    const duration = durationOf(m.start, m.end);
    if (duration) { out.duration.n++; inc(out.duration.counts, duration); }
  }
  return out;
}

const BASE = `FROM rec_stage s LEFT JOIN rec_people p ON p.ver=s.ver AND p.stage_id=s.stage_id WHERE s.ver=?1`;
const PEOPLE = `CASE WHEN json_valid(p.people) AND json_type(p.people)='array' THEN p.people ELSE '[]' END`;
// A fixed-size shared snapshot. Do not scan the historical corpus on page views.
// Read ceiling before aggregation: 5,000 stages / 100,000 credit/tag pairs.
export async function comparisonPopulation(db, today) {
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  if (!ver) return {...emptyCounts(), unavailable: true};
  const stamp = `four-v1|${ver}|${today}`;
  const kept = await db.prepare("SELECT v FROM rec_meta WHERE k='compare_four'").first();
  const cached = parse(kept?.v, null);
  if (cached?.stamp === stamp) return cached;
  const size = await db.prepare(`SELECT count(*) n, coalesce(sum(json_array_length(${PEOPLE})),0) pairs ${BASE}`).bind(ver).first();
  const out = {...emptyCounts(), stamp, total: size.n, updated: today, first: '', last: ''};
  if (size.n > 5000 || size.pairs > 100000) out.unavailable = true;
  else {
    // Per-stage DISTINCT prevents duplicate roles/names/tags from inflating percentages.
    const credit = await db.prepare(`WITH x AS (
      SELECT DISTINCT s.stage_id, json_extract(j.value,'$[0]') role, trim(json_extract(j.value,'$[1]')) name
      FROM rec_stage s JOIN rec_people p ON p.ver=s.ver AND p.stage_id=s.stage_id,
      json_each(${PEOPLE}) j WHERE s.ver=?1 AND j.type='array'
    ) SELECT 'craft' axis, role label, count(DISTINCT stage_id) n FROM x WHERE role IN ('翻訳','原作','作曲','振付') AND name<>'' GROUP BY role
      UNION ALL SELECT 'craft_n','',count(DISTINCT stage_id) FROM x WHERE role NOT LIKE '#%' AND role<>'' AND name<>''
      UNION ALL SELECT 'theme',name,n FROM (SELECT name,count(DISTINCT stage_id) n FROM x WHERE role='#題材' AND name<>'' AND length(name)<=80 GROUP BY name ORDER BY n DESC,name LIMIT 12)
      UNION ALL SELECT 'theme_n','',count(DISTINCT stage_id) FROM x WHERE role='#題材' AND name<>''`).bind(ver).all();
    const themes = [];
    for (const r of credit.results) {
      if (r.axis === 'theme') themes.push(r);
      else if (r.axis === 'craft') out.craft.counts[r.label] = r.n;
      else out[r.axis === 'craft_n' ? 'craft' : 'theme'].n = r.n;
    }
    // Keep the same 12 most frequent DB tags for everyone; no personal cache keys.
    themes.sort((a,b) => b.n-a.n || (a.label < b.label ? -1 : a.label > b.label ? 1 : 0));
    for (const r of themes.slice(0,12)) inc(out.theme.counts,r.label,r.n);
    const regions = await db.prepare(`SELECT json_extract(CASE WHEN json_valid(entry) THEN entry ELSE '{}' END,'$.pref') label,count(*) n FROM rec_stage WHERE ver=? GROUP BY label`).bind(ver).all();
    for (const r of regions.results) { const k = regionOf(r.label); if (k) { inc(out.region.counts,k,r.n); out.region.n += r.n; } }
    const durations = await db.prepare(`WITH d AS (SELECT julianday(end)-julianday(start)+1 days FROM rec_stage WHERE ver=?
      AND start GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND end GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
      AND date(start,'+0 days')=start AND date(end,'+0 days')=end AND end>=start)
      SELECT CASE WHEN days=1 THEN 0 WHEN days<=7 THEN 1 WHEN days<=14 THEN 2 WHEN days<=30 THEN 3 ELSE 4 END bucket,count(*) n FROM d GROUP BY bucket`).bind(ver).all();
    for (const r of durations.results) { out.duration.n += r.n; out.duration.counts[DURATIONS[r.bucket]] = r.n; }
    const span = await db.prepare("SELECT min(nullif(start,'')) first,max(nullif(end,'')) last FROM rec_stage WHERE ver=?").bind(ver).first();
    out.first = span?.first || ''; out.last = span?.last || '';
  }
  // One bounded row replaces the old value on the next version/day, never per-user rows.
  const value = JSON.stringify(out);
  if (new TextEncoder().encode(value).length <= 12000) await db.prepare("INSERT INTO rec_meta(k,v) VALUES('compare_four',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(value).run();
  return out;
}

export async function personalComparison(ctx, works) {
  const credits = await peopleByKey(ctx, works), meta = {};
  const ids = [...new Set(works.map(w => w.stage_id).filter(Boolean))];
  for (let i=0;i<ids.length;i+=90) {
    const part=ids.slice(i,i+90), marks=part.map(()=>'?').join(',');
    const current = await ctx.db.prepare(`SELECT s.stage_id,s.start,s.end,s.entry,p.people FROM rec_stage s LEFT JOIN rec_people p ON p.ver=s.ver AND p.stage_id=s.stage_id WHERE s.ver=(SELECT v FROM rec_meta WHERE k='current') AND s.stage_id IN (${marks})`).bind(...part).all();
    for (const r of current.results) meta[r.stage_id] = {...r,pref:parse(r.entry,{}).pref || ''};
    const missing=part.filter(id=>!meta[id]);
    if (missing.length) {
      const past=await ctx.db.prepare(`SELECT stage_id,start,end,pref,people FROM past_stage WHERE stage_id IN (${missing.map(()=>'?').join(',')})`).bind(...missing).all();
      for (const r of past.results) meta[r.stage_id]=r;
    }
  }
  return personalCounts(works,meta,credits);
}

const AXES = [
  ['craft','クレジットの特徴','翻訳・原作・作曲・振付の記載率です。作曲の記載があることだけで音楽劇とは断定しません。',ROLES],
  ['theme','題材・テーマ','掲載公演で多い上位12題材を比較します。複数の題材を持つ作品があるため、合計は100%になりません。',null],
  ['region','地域の広がり','公演会場の都道府県を8地域にまとめています。住まいや移動の機会にも左右されます。',Object.keys(REGIONS)],
  ['duration','公演期間','初日から千秋楽までの日数（両端を含む）です。休演日も含み、上演時間や観劇回数ではありません。',DURATIONS],
];
export function fourPanels(mine, world) {
  const note = `<section class="card wide"><h3>比べる相手は何か</h3><p>取得済みのCoRich掲載公演 <b>${world.total} 件</b>と、あなたが観た <b>${mine.total} 作品</b>を比べます。一般の観客の平均や、日本の演劇全体ではありません。</p>
<p class="note">掲載公演の日程：${E(world.first || '不明')}〜${E(world.last || '不明')}。集計日：${E(world.updated || '不明')}。<b>今回は同じ時期・地域に条件をそろえていません。</b>過去の観劇と主に現在・今後の掲載公演の差も含まれるため、好みの優劣を示すものではありません。自分は保存された作品ごとに1件、掲載公演は公演ページごとに1件です。ツアーの別会場は別件になる場合があります。</p></section>`;
  if (world.unavailable) return note + '<p class="empty">比較対象を集計できませんでした。無料枠を守るため、データ量が上限を超えた場合も集計を止めています。</p>';
  return note + AXES.map(([key,title,why,fixed]) => {
    const a=mine[key],b=world[key],labels=fixed || Object.keys(b.counts);
    const cards = !a.n || !b.n || !labels.length ? '<p class="empty">この項目は、比較に使えるデータがまだ足りません。</p>' : labels.map(label=>{
      const an=getCount(a.counts,label),bn=getCount(b.counts,label),pa=an/a.n*100,pb=bn/b.n*100,diff=pa-pb;
      return `<li class="cf-item"><h4>${E(label)}</h4><dl><div><dt>自分</dt><dd>${pa.toFixed(1)}% <small>（${an}/${a.n}作品）</small></dd></div><div><dt>掲載公演</dt><dd>${pb.toFixed(1)}% <small>（${bn}/${b.n}件）</small></dd></div></dl><p class="cf-diff">割合の差：${diff>0?'+':''}${diff.toFixed(1)}ポイント</p>${a.n<5 || b.n<5 ? '<p class="note">比較できる件数が少ないため参考値です。</p>' : ''}</li>`;
    }).join('');
    return `<section class="card wide cf-axis" data-compare-axis="${key}"><h3>${title}</h3><p>${why}</p><p class="note">比較に使えたデータ：自分 ${a.n}/${mine.total}作品、掲載公演 ${b.n}/${world.total}件。不明で除外：自分 ${mine.total-a.n}作品、掲載公演 ${world.total-b.n}件。評価なしの観劇も含み、同じ保存作品の繰り返し観劇は1件です。</p><ul class="cf-items">${cards.startsWith('<li')?cards:''}</ul>${cards.startsWith('<li')?'':cards}</section>`;
  }).join('');
}
