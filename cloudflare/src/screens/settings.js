// 設定・はじめる・観劇記録を追加, and their writes (pref_setting, missed), answered by the
// Worker from D1 (起案者の指示 2026-10-14「残りの画面も順に移して」).
//
// Same layout and words as app._settings_body / _start_body / _register_body, except where
// the Python text speaks of the Render server: the アカウント card (recovery codes on Render)
// points to the account page, the mail import is the owner's only, and 「観ればよかった」 is
// looked up in the stages already in D1 instead of fetching the web.
import {registerDialogHtml} from './register-dialog.js';
import {scaleOf, scaleCardHtml, SCALE_LABEL, frac} from './grade.js';
import {FAV_SEED_W} from '../recommend.js';
import {nextCrawl, crawlLabel, crawlSearch} from '../crawl-time.js';
import {E, ValueError} from './py.js';
import {ico, h2} from './icons.js';
import {PREFS, readPrefSetting, regionsHtml, regionCounts, prefSettingAction} from './prefs.js';
import {rankedGroups, prefCounts} from './recommend.js';
import {KINDS, loadDeclared, favRoleBox, reactionsOf} from './lists.js';
import {stageInfo} from './fallback.js';
import {loadWorks, titleKey, DROP_KEEP_DAYS, expiredKeys} from './works.js';
import {dateParts} from './row.js';
import {splitNames} from './cast.js';
import {optedOut, optoutCardHtml, optoutAction} from './evalrec.js';

const cardH2 = (name, text, extra = '') => `<summary>${h2(name, text, extra)}</summary>`;

// ---------------------------------------------------------------- 設定
async function droppedRows(ctx) {
  const {results} = await ctx.db.prepare('SELECT uid, program, updated_at FROM excluded WHERE user_id = ? ORDER BY uid, program').bind(ctx.uid).all();
  const ex = results.map(r => [r.uid, r.program]);
  // 30 日たって消すのを待っている記録（works.expireDropped の上限で、まだ消していない分）は、戻せるように並べない
  const expired = expiredKeys(ctx, results);
  const marks = new Map(ex.filter(([u]) => u.startsWith('work:') && !expired.has(u.slice(5))).map(([u, p]) => [u.slice(5), p]));
  const purged = new Set(ex.filter(([u]) => u.startsWith('purged:')).map(([u]) => u.slice(7)));
  const purgedLegacy = new Set(ex.filter(([u]) => u.startsWith('purged-legacy:')).map(([, p]) => p));
  const rows = [...marks].filter(([k]) => !purged.has(k)).map(([k, t]) => ({key: k, title: t, n: 1, legacy: false}));
  const legacy = new Map();
  for (const [uid, program] of ex) {
    if (uid.startsWith('work:') || uid.startsWith('purged:') || uid.startsWith('purged-legacy:') || purgedLegacy.has(program)) continue;
    legacy.set(program, (legacy.get(program) || 0) + 1);
  }
  rows.push(...[...legacy].map(([p, n]) => ({key: p, title: p, n, legacy: true})));
  return rows.sort((a, b) => (a.title < b.title ? -1 : a.title > b.title ? 1 : 0));
}

function droppedHtml(rows) {
  if (!rows.length) return `<details class="card">${cardH2('check', '取り消した記録')}
<p class="lead">取り消した記録はありません。<b>まちがって入った記録は、
各行の「記録を直す」を開いて「この記録を取り消す」から外せます。</b>
外した記録はここに並び、${DROP_KEEP_DAYS} 日のあいだは戻せます。</p></details>`;
  const body = rows.map(r => {
    const how = r.legacy ? `以前に外した分・${r.n} 件` : '記録 1 件';
    return `<div class="drop-row"><span class="dt">${E(r.title)}</span><span class="dm">${E(how)}</span>`
      + `<div class="drop-btns"><button data-restore="${E(r.key)}">戻す</button>`
      + `<button class="danger" data-purge="${E(r.key)}">いますぐ消す</button></div><span class="said"></span></div>`;
  }).join('');
  return `<details class="card">${cardH2('check', '取り消した記録', `<span class="badge part">${rows.length} 件</span>`)}
<p class="lead">一覧・評価待ち・おすすめの材料から外してあります。「戻す」を押せばもとに戻ります。
<b>取り消してから ${DROP_KEEP_DAYS} 日たっても戻さなかった記録は、自動で消します。</b>
「いますぐ消す」を押すと、待たずにその場で消します。消した記録は戻せません。</p>
${body}</details>`;
}

function skippedHtml(rows) {
  if (!rows.length) return `<details class="card">${cardH2('check', '行かなかった公演')}
<p class="lead">「行かなかった」と答えた公演はありません。<b>評価待ちや日記帳の
各行で「行かなかった」を押すと、ここに並びます。</b></p></details>`;
  const body = rows.map(w => {
    const [y, md] = dateParts(w.first_date || '');
    const when = md ? `${y}年${md.split('.')[0]}月${Number(md.split('.')[1])}日` : '上演日が分かりません';
    return `<div class="drop-row"><span class="dt">${E(w.title)}</span><span class="dm">${E(when)}</span>`
      + `<div class="drop-btns"><button data-seen="${E(w.work_key)}">やはり観た</button><span class="said"></span></div></div>`;
  }).join('');
  return `<details class="card">${cardH2('check', '行かなかった公演', `<span class="badge part">${rows.length} 件</span>`)}
<p class="lead">券を買ったが「行かなかった」と答えた公演です。件数と図には数えていません。
<b>「やはり観た」を押すと、観た記録に戻ります。</b></p>
${body}</details>`;
}

const EXPORT_LABEL = {works: '観た公演の記録（作品ごと）', ratings: '観た回ごとの評価と感想', attendance: '観に行ったかどうかの答え',
  reaction: 'おすすめへの答え（持っている・興味あり・興味なし）', ticket: '券の日にち', presented: 'これまでに表示したおすすめの一覧',
  splits: '1 通のメールを複数の公演に分けた指定', excluded: '取り込みから外した公演', missed: '「行けばよかった」の登録', declared: 'お気に入りに登録した名前と題材',
  hand_credits: '手で入れた出演・スタッフとポスター', work_piece: '作品ごとに分けた評価と感想', merges: '1 つにまとめた記録', visit_note: '観た回ごとのメモ',
  rank_weight: 'おすすめの選び方（効かせ方）', favourites: 'お気に入り（以前の登録）', settings: '設定（評価の付け方・都道府県・表示名など）',
  search_request: '探した言葉', fix_request: '公演情報の誤りの知らせ', records: '以前の形式の観劇記録', reactions: '以前の形式のおすすめへの答え'};
// 書き出しの形の版（#192）。鍵を足す・意味を変えるときに上げる。1: 本人の私的な表をすべて入れた最初の版。
// 2: 作品ごとに分けた評価と感想（work_piece）を足した（dec-split-pieces）
export const EXPORT_SCHEMA_VERSION = 2;
// 本人の行を user_id でそのまま持ち出す表（Python 版と同じ鍵の表と、サービス版で足した表）。
// 入れないもの: sessions・passkeys・webauthn_challenges・users（ログインの秘密: セッション・復旧コード・パスキー・
// Firebase UID）と rec_cache（ほかの表から作り直せる計算の控え）。fix_request は運用者のメモ（note・mailed）を除く。
// rec_shown・viewed（おすすめに出した・開いた公演の計測の控え）も入れない。issue #192 は計測用の表の扱いを
// 別に決めるとしているので、本人が付けた記録だけにした
const EXPORT_TABLES = ['works', 'reaction', 'ticket', 'excluded', 'missed', 'hand_credits', 'merges', 'visit_note', 'rank_weight',
  'favourites', 'search_request', 'records', 'reactions', 'work_piece'];
const EXPORT_SQL = {settings: 'SELECT key, value, updated_at FROM app_setting WHERE user_id=?',
  fix_request: 'SELECT id, stage_id, kind, message, created_at, status, resolved_at FROM fix_request WHERE user_id=?'};

/**
 * app.export_payload for one user: the same keys (tables the service never fills are empty), and every
 * other private table of the user (#192), all scoped to ctx.uid. declared は画面の控え（app_setting）と
 * favourites の表を合わせたもの（lists.loadDeclared と同じ。上限を付けずに全部）。
 */
export async function exportPayload(ctx) {
  const out = {schema_version: EXPORT_SCHEMA_VERSION, exported_at: new Date(ctx.now ?? Date.now()).toISOString()};
  for (const t of ['works', 'ratings', 'attendance', 'reaction', 'ticket', 'presented', 'splits', 'excluded', 'missed']) {
    out[t] = EXPORT_TABLES.includes(t) ? (await ctx.db.prepare(`SELECT * FROM ${t} WHERE user_id=?`).bind(ctx.uid).all()).results : [];
  }
  for (const t of EXPORT_TABLES.filter(t => !(t in out))) out[t] = (await ctx.db.prepare(`SELECT * FROM ${t} WHERE user_id=?`).bind(ctx.uid).all()).results;
  for (const [k, sql] of Object.entries(EXPORT_SQL)) out[k] = (await ctx.db.prepare(sql).bind(ctx.uid).all()).results;
  let dec = {};
  try { dec = JSON.parse(out.settings.find(r => r.key === 'declared')?.value || '{}') || {}; } catch { dec = {}; }
  out.declared = Object.fromEntries(KINDS.map(k => [k, (Array.isArray(dec[k]) ? dec[k] : []).filter(x => typeof x === 'string')]));
  for (const f of out.favourites) if (out.declared[f.kind] && !out.declared[f.kind].includes(f.name)) out.declared[f.kind].push(f.name);
  return out;
}

/** 書き出しの件数だけ（設定の画面を開くたびに全部の行を読み解かない。1 回の問い合わせで数える） */
async function exportCounts(ctx) {
  const tables = ['works', 'reaction', 'ticket', 'excluded', 'missed', ...EXPORT_TABLES.slice(5)];
  const cols = [...tables, 'app_setting', 'fix_request'].map(t => `(SELECT count(*) FROM ${t} WHERE user_id=?1) AS ${t}`).join(', ');
  const n = await ctx.db.prepare(`SELECT ${cols}`).bind(ctx.uid).first() || {};
  const d = await exportPayloadDeclared(ctx);
  const out = {};
  for (const t of ['works', 'ratings', 'attendance', 'reaction', 'ticket', 'presented', 'splits', 'excluded', 'missed']) out[t] = Number(n[t] || 0);
  for (const t of EXPORT_TABLES.slice(5)) out[t] = Number(n[t] || 0);
  out.settings = Number(n.app_setting || 0);
  out.fix_request = Number(n.fix_request || 0);
  out.declared = Object.values(d).reduce((s, x) => s + x.length, 0);
  return out;
}

/** declared だけ（exportPayload と同じ合わせ方） */
async function exportPayloadDeclared(ctx) {
  const row = await ctx.db.prepare("SELECT value FROM app_setting WHERE user_id=? AND key='declared'").bind(ctx.uid).first();
  let dec = {};
  try { dec = JSON.parse(row?.value || '{}') || {}; } catch { dec = {}; }
  const out = Object.fromEntries(KINDS.map(k => [k, (Array.isArray(dec[k]) ? dec[k] : []).filter(x => typeof x === 'string')]));
  const {results} = await ctx.db.prepare('SELECT name, kind FROM favourites WHERE user_id=?').bind(ctx.uid).all();
  for (const f of results) if (out[f.kind] && !out[f.kind].includes(f.name)) out[f.kind].push(f.name);
  return out;
}

async function exportCardHtml(ctx) {
  const d = await exportCounts(ctx);
  const li = Object.entries(d).map(([k, n]) => `<li>${E(EXPORT_LABEL[k] || k)} <b>${n} 件</b><span class="xk">${E(k)}</span></li>`).join('');
  return `<details class="card">${cardH2('download', '書き出す')}
<p class="lead">記録・評価・感想・お気に入りを、1 つのファイルにまとめて保存できます。
中身は下のとおりで、ほかのアプリでも読める形式（JSON）です。</p>
<ul class="lead">${li}</ul>
<a class="dl" href="/export.json?t=__TAGURI_TOKEN__" download="taguri-export.json">
 taguri-export.json を保存する</a>
<p class="note"><b>ポスターと、半券の写真は入りません。</b>
ポスターは外部サイトの画像を保存したものなので、書き出しには含めていません。</p></details>`;
}

export async function settingsScreen(_params, ctx) {
  const prefs = await readPrefSetting(ctx);
  const data = await rankedGroups(ctx);
  const counts = prefCounts(data.groups);
  const rcounts = regionCounts(data.groups.map(g => ({key: g.stage_id, prefs: g.venues.map(v => v.pref)})));
  const keep = new Set(prefs);
  // Every prefecture can be chosen as the default, also ones with nothing to recommend now
  // (起案者の指摘 2026-10-14「地方選ぶ機能が使えなくなってる」: a new account had no chips at all).
  const chips = PREFS.map(p => `<label class="pchip${keep.has(p) ? ' on' : ''}">`
    + `<input type="checkbox" name="pref" value="${E(p)}"${keep.has(p) ? ' checked' : ''}>`
    + `<span class="pl">${E(p)}</span><span class="pn">${counts[p] || 0}</span></label>`).join('');
  const now = !prefs.length ? '全国' : prefs.join('・') + `（${prefs.length} 県）`;
  const works = await loadWorks(ctx);
  const body = `<h1>設定</h1>
<p class="lede">ここで決めたことは、おすすめ全体に反映されます。<b>内容をまとめて確かめてから保存します。</b></p>
<details class="card">${cardH2('gear', '観に行ける場所を決めておく', `<span class="badge part">いまは${E(now)}</span>`)}
<p class="lead">都道府県を選んで保存すると、<b>「今週のおすすめ」と「公演カレンダー」を
開くたびに、その都道府県で絞り込んだ状態になります。</b>選ばなければ全国です。
<b>いくつでも同時に選べます。</b><br>
<b>すでに「興味あり」を押した公演・お気に入り・買った券には影響しません。</b>
一度決めたことを、この設定で見えなくすることはありません。</p>
<form class="pfil" id="pref-setting" onsubmit="return false">
${regionsHtml(counts, rcounts, true)}
<div class="pchips">${chips}</div>
<div class="pfoot"><button type="button" data-set-pref="1">${ico('gear')}この都道府県を既定にする</button>
<button type="button" class="pall-btn" data-set-pref-all="1">全国に戻す</button>
<span class="said"></span></div>
</form></details>
${await (async () => { const sc = await scaleOf(ctx); return scaleCardHtml(sc, cardH2('star', '評価の付け方', `<span class="badge part">いまは${E(SCALE_LABEL[sc])}</span>`)); })()}
<details class="card">${cardH2('gear', 'アカウント')}
<p class="lead">表示名・ログインの方法・パスキー・ログアウト・アカウントの削除は、<a href="/account">アカウント</a>の画面にまとめてあります。</p></details>
${await (async () => { const off = await optedOut(ctx); return optoutCardHtml(off, cardH2('gear', '推薦の改善の分析', `<span class="badge part">いまは${off ? '分析に使わない' : '分析に使ってよい'}</span>`)); })()}
${await exportCardHtml(ctx)}
${droppedHtml(await droppedRows(ctx))}
${skippedHtml(works.filter(w => w.unseen))}`;
  return {title: '設定', body_html: body};
}

// ---------------------------------------------------------------- はじめる
const stepCard = (n, title, done, lead, inner = '') => `<div class="card start-step${done ? ' done' : ''}">`
  + `${h2(done ? 'check' : 'plus', `${n} ${title}`, done ? '<span class="badge part">済んでいます</span>' : '<span class="badge">これからです</span>')}`
  + `<p class="lead">${lead}</p>${inner}</div>`;

// 評価の段階ごとの書き方（例は本人がいま使っている段階で出す。#93）
const SCALE_WORDS = {
  marks2: {marks: '○×', top: '○', low: '×'}, marks3: {marks: '○△×', top: '○', low: '×'},
  marks4: {marks: '◎○△×', top: '◎', low: '×'}, stars5: {marks: '★1〜★5', top: '★5', low: '★1'},
  stars11: {marks: '★0.5〜★5（0.5 きざみ）', top: '★5', low: '★0.5'},
};
/**
 * おすすめの材料の説明（いまの決まり: recommend.js）。評価は本人の中での高い・低い（gradeOf）、
 * お気に入りは評価の代わりの種で、興味ありより強い（FAV_SEED_W）。どちらの種も評価が増えるほど薄まる（SEED_K）
 */
function recoInputs(w) {
  const fav = FAV_SEED_W > 1 ? '<b>興味ありより強く効きます</b>' : '興味ありと同じくらい効きます';
  return `<b>おすすめの材料は 3 つです。</b>`
    + `① 観た公演に付けた評価：あなたが付けた評価の中で高いか低いかを見ます（${E(w.top)} を付けた公演の出演者・作り手は上がり、${E(w.low)} の公演の人は下がります）。`
    + `② お気に入りに登録した名前：観たことが無くても材料になり、${fav}。`
    + `③ 「興味あり」を押した公演：その公演の人・種類に少しずつ効きます。`
    + `評価が増えるほど、②③ の効き方は控えめになります。`;
}

export async function startScreen(_params, ctx) {
  const dec = await loadDeclared(ctx);
  const nDec = KINDS.reduce((s, k) => s + (dec[k] || []).length, 0);
  const nCand = Number((await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='catalogue_upcoming'").first())?.v || 0);
  const works = await loadWorks(ctx);
  const nWorks = works.length;
  const nRated = works.filter(w => !w.unseen && frac(w.verdict) !== null).length;
  const nWait = works.filter(w => !w.unseen && !w.verdict && w.last_date && w.last_date <= ctx.today).length;
  const words = SCALE_WORDS[await scaleOf(ctx)] || SCALE_WORDS.stars5;
  const kinds = KINDS.map(k => `<option value="${E(k)}">${E(k)}</option>`).join('');
  const tags = KINDS.flatMap(k => (dec[k] || []).map(n => `<span class="tag" data-kind="${E(k)}" data-name="${E(n)}">${E(k)}「${E(n)}」<button data-fav="remove">✕</button></span>`)).join('');
  const form = `<div class="fav-add"><label class="fld" for="fav-kind"><span class="fl">種類<small class="req">必須</small></span><select id="fav-kind">${kinds}</select></label> <label class="fld" for="fav-name"><span class="fl">名前<small class="req">必須</small></span><input id="fav-name" type="text" placeholder="例：劇団四季・シェイクスピア・家族" size="26"></label>`
    + ` <button data-fav="add">${ico('star')}登録する</button>${favRoleBox()}<span class="said"></span></div>` + (tags ? `<div class="tags">${tags}</div>` : '');
  const step1 = stepCard(1, `見逃したくない名前を登録する（いま ${nDec} 件）`, nDec > 0,
    '劇団・俳優・演出家・作品・原作者・題材のどれでも登録できます。<b>登録した名前の公演は、内容を問わず、件数の制限も付けずに「お気に入り」に出します。</b>1 件登録するだけで動き始めます。<br>あとから「おすすめ ▸ お気に入り」で足すことも外すこともできます。', form);
  const step2 = stepCard(2, '公演の情報を取り寄せる', nCand > 0, nCand > 0
    ? `手元に今後の公演を ${nCand} 件持っています。毎日取り直しています。`
    : 'まだ公演の情報が届いていません。毎日の取得のあとに、ここに件数が出ます。');
  const rateLink = nWait
    ? `<a href="/rate/unrated?t=__TAGURI_TOKEN__">未評価の記録（いま ${nWait} 件）</a>で ${E(words.marks)} を付けてください`
    : `観た公演には <a href="/rate?t=__TAGURI_TOKEN__">観た公演の評価</a> で ${E(words.marks)} を付けてください`;
  const step3 = stepCard(3, `観た公演を入れて評価する（いま記録 ${nWorks} 件・評価 ${nRated} 件・任意です）`, nRated > 0,
    (nRated ? '' : '<b>評価が 1 件もないうちは、観た記録から好みを読み取ったおすすめは出ません。</b><b>1 段目で登録した名前の公演は、記録が無くても出ます。</b><br>')
    + recoInputs(words)
    + `<br><a href="/register?t=__TAGURI_TOKEN__">観劇記録を追加</a> から、手で追加できます。${rateLink}（評価の形は「設定」の「評価の付け方」で変えられます）。`);
  // いまの状態で見出しと次の一歩を変える（#93）: 何も無い／名前か記録だけ（評価なし）／評価した記録がある
  const done = [nDec > 0 && `名前の登録（${nDec} 件）`, nCand > 0 && '公演の情報', nWorks > 0 && `観た記録（${nWorks} 件）`, nRated > 0 && `評価（${nRated} 件）`].filter(Boolean);
  const doneLine = done.length ? `<p class="lede">済んでいること：${done.map(E).join('・')}</p>` : '';
  let h1, lede, foot;
  if (nRated > 0) {
    h1 = '準備はできています';
    lede = `評価した記録 ${nRated} 件${nDec ? `と、登録した名前 ${nDec} 件` : ''}をもとに、おすすめを作っています。<b>次は「今週のおすすめ」を見て、気になる公演に「興味あり」を押してください。</b>評価や名前を足すほど、おすすめが合っていきます。`;
    foot = '<p class="lede"><a href="/recommend?t=__TAGURI_TOKEN__">今週のおすすめを見る</a></p>';
  } else if (nDec > 0 || nWorks > 0) {
    h1 = nDec > 0 ? '名前を登録しました。次は観た公演を評価してください' : '記録を入れました。次は評価して、見逃したくない名前も登録してください';
    const next = nWait ? `<b>次は、未評価の記録 ${nWait} 件に ${E(words.marks)} を付けてください。</b>`
      : nWorks ? '<b>記録した公演は、上演が終わると評価できるようになります。</b>' : '<b>次は、観た公演を記録して評価してください（3 段目）。</b>';
    lede = (nDec ? `登録した名前 ${nDec} 件の公演は、もう「お気に入り」に出ています。` : 'まだ名前が無いので、1 段目で見逃したくない名前を 1 つ登録すると、その公演がすぐ「お気に入り」に出ます。')
      + `${next}評価が付くと、好みに合わせたおすすめも出るようになります。`;
    foot = nDec ? '<p class="lede"><a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入りの公演を見る</a></p>' : '';
  } else {
    h1 = 'はじめに、見逃したくない名前を 1 つ登録してください';
    lede = 'まだ登録も記録もないので、届けられるものがありません。<b>下の3つのうち、1つ目だけで始められます。</b>';
    foot = '<p class="lede">ナビゲーションから、各画面を先に見ることもできます。<b>どの画面もまだ0件です。</b></p>';
  }
  const body = `<h1>${h1}</h1>
<p class="lede">たぐりは<b>今後の公演の中から、見逃したくない舞台を毎週届けるアプリ</b>です。${lede}</p>
${doneLine}
${step1}
${step2}
${step3}
${foot}`;
  return {title: 'はじめる', body_html: body};
}

// ---------------------------------------------------------------- 観劇記録を追加
const MISSED_WHERE = {
  pool: ['一覧にはあったが、表示する枠に入らなかった', '取り込んだ公演の中にはありましたが、順位が足りず 15 件の枠に入りませんでした。「設定」の「おすすめの効かせ方」で重視する情報を変えると、入ることがあります。'],
  none: ['取り込んだ公演の中に無かった', '取り込んだ公演の一覧に、そもそも入っていませんでした。順位をどう変えても出てきません。出すには、公演情報の取得元を増やす必要があります。'],
};

async function missedRows(ctx) {
  const {results} = await ctx.db.prepare('SELECT title, created_at, note, stage_id, fields_json, synopsis, lookup_note, looked_up_at FROM missed WHERE user_id=? ORDER BY created_at DESC').bind(ctx.uid).all();
  return results.map(r => {
    let fields = {};
    try { fields = r.fields_json ? JSON.parse(r.fields_json) : {}; } catch { fields = {}; }
    return {title: r.title, at: String(r.created_at || '').slice(0, 10), stage_id: r.stage_id || '', fields, synopsis: r.synopsis || '',
      lookup_note: r.lookup_note || '', looked_up: r.looked_up_at !== null && r.looked_up_at !== undefined,
      where: r.stage_id ? 'pool' : 'none'};
  });
}

/**
 * 興味ありにしたまま、購入済みにならずに終わった公演（起案者の指示 2026-10-20「興味ありにしたけど購入済みにならなかったら自動的に
 * 行けばよかった扱いにすれば良い」）。保存はせず、開くたびに答え（reaction）と公演の終わりの日から数える。観た記録のある公演・
 * 自分で登録した題名は除く。ツアーは題名と団体で 1 行にまとめる（いちばん遅い終わりの日）
 */
async function autoMissed(ctx, works, manual) {
  const reacts = await reactionsOf(ctx);
  const sids = [...reacts].filter(([, d]) => (d.interest === 1 || d.interest === 2) && d.owned !== 1).map(([sid]) => String(sid));
  if (!sids.length) return [];
  const info = await stageInfo(ctx.db, sids);
  const seen = new Set(works.filter(w => !w.unseen).flatMap(w => [w.stage_id ? 'sid:' + w.stage_id : '', 'key:' + titleKey(w.title || '')]).filter(Boolean));
  const mine = new Set(manual.map(m => titleKey(m.title)));
  const out = new Map();
  for (const sid of sids) {
    const st = info.get(sid);
    if (!st || !st.end || st.end >= ctx.today) continue;
    const key = titleKey(st.title || '');
    if (seen.has('sid:' + sid) || seen.has('key:' + key) || mine.has(key)) continue;
    const g = key + '\u0000' + (st.group || '');
    const had = out.get(g);
    if (!had || st.end > had.end) out.set(g, {title: st.title, venue: st.venue || '', end: st.end, stage_id: sid, at: String(reacts.get(sid)?.at || '').slice(0, 10)});
  }
  return [...out.values()].sort((x, y) => (x.end < y.end ? 1 : x.end > y.end ? -1 : 0));
}

const ymd = d => (/^\d{4}-\d{2}-\d{2}/.test(d || '') ? `${d.slice(0, 4)}/${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}` : '');

/** 行けばよかった（自動で入った分と、自分で登録した分）。題名を 1 行に並べ、くわしくは畳む */
function missedHtml(rows, auto = []) {
  if (!rows.length && !auto.length) return '<p class="empty">まだありません。「興味あり」にしたまま購入済みにならずに終わった公演は、ここに自動で入ります。</p>';
  const autoLi = auto.map(r => `<li class="miss-row"><b class="mt">${E(r.title)}</b><span class="mw">${E([r.venue, r.end ? ymd(r.end) + ' まで' : ''].filter(Boolean).join('・'))}</span>`
    + `<span class="mk auto">興味ありのまま終わった</span></li>`).join('');
  const handLi = rows.map(r => {
    const [, why] = MISSED_WHERE[r.where];
    let look;
    if (!r.looked_up) look = '<p class="empty">演者とあらすじを調べています…</p>';
    else if (!r.stage_id) look = `<p class="empty">${E(r.lookup_note || 'この題名の公演ページが見つかりませんでした')}</p>`;
    else {
      look = castBlock(r.fields) + (r.synopsis ? `<div class="syn"><p class="txt">${E(r.synopsis)}</p><span class="src">［出典: CoRich の公演ページ］</span></div>`
        : '<p class="empty">あらすじを取れませんでした（公演ページに内容の記載がありません）。</p>') + (r.lookup_note ? `<p class="empty">${E(r.lookup_note)}</p>` : '');
    }
    return `<li class="miss-row"><b class="mt">${E(r.title)}</b><span class="mk">${E(r.at)} に登録</span>`
      + `<details class="miss-more"><summary>くわしく</summary><p class="note">${why}</p>${look}</details></li>`;
  }).join('');
  return `<ul class="miss-list">${autoLi}${handLi}</ul>`;
}

/** render_recommend.cast_block */
const MAKER_ROLES = ['演出', '脚本', '作', '原作', '翻訳', '音楽', '作曲', '振付', '演出・振付'];
const CAST_SHOWN = 12;
export function castBlock(f) {
  const cast = splitNames(f['出演'] || '');
  const makers = MAKER_ROLES.filter(r => f[r]).map(r => [r, splitNames(f[r])]).filter(([, ns]) => ns.length);
  if (!cast.length && !makers.length) return '<div class="cast none">出演者のクレジットを取れませんでした（公演ページに欄がありません）</div>';
  const rows = [];
  if (cast.length) {
    const head = cast.slice(0, CAST_SHOWN).map(E).join('、');
    const rest = cast.slice(CAST_SHOWN);
    const more = rest.length ? `<span class="rest">、${rest.map(E).join('、')}</span><button class="mrb" data-more="1">ほか ${rest.length} 名を見る</button>` : '';
    rows.push(`<div class="cr"><span class="cl">出演</span><span class="cv">${head}${more}</span></div>`);
  }
  for (const [role, ns] of makers) rows.push(`<div class="cr"><span class="cl">${E(role)}</span><span class="cv">${ns.slice(0, 6).map(E).join('、')}${ns.length > 6 ? `ほか ${ns.length - 6} 名` : ''}</span></div>`);
  return `<div class="cast">${rows.join('')}<span class="src">［出典: 公演ページのクレジット］</span></div>`;
}

export async function registerScreen(_params, ctx) {
  const works = await loadWorks(ctx);
  const wait = works.filter(w => !w.verdict && !w.unseen && w.last_date && w.last_date <= ctx.today);
  const missed = await missedRows(ctx);
  const autoMiss = await autoMissed(ctx, works, missed);
  const body = `<h1>観劇記録を追加</h1>
<p class="lede">公演名だけでも保存できます。日付や評価はあとから追加できます。</p>
<div class="card register-single">${h2('plus', '観た公演を1件追加')}
<div class="add-work" data-register-single="1">
 <div class="register-search"><label class="fld" for="w-title"><span class="fl">公演の題名<small class="req">必須</small></span><input id="w-title" type="text" placeholder="例：夜の果て" size="26" autocomplete="off" aria-describedby="register-title-help"></label><input id="w-stage" type="hidden" value="">
 <button type="button" data-register-search="1" data-open-dialog="register-search-dialog">${ico('search')}詳細検索</button></div>
 <p class="note" id="register-title-help">題名を2文字入れると候補が出ます。劇場と上演期間を見て選んでください。見つからなくても、入力した名前で記録できます。</p>
 <div id="sug" class="sug"></div>
 <div class="register-dates"><label class="fld" for="w-date"><span class="fl">観た日<small class="opt">任意</small></span><input id="w-date" type="date"></label>
 <label class="fld" for="w-time"><span class="fl">開演時刻<small class="opt">任意</small></span><input id="w-time" type="time"></label></div>
 <label class="fld" for="w-venue"><span class="fl">劇場<small class="opt">任意</small></span><input id="w-venue" type="text" placeholder="例：本多劇場" size="26"></label>
 <div class="register-save"><button type="button" class="primary" data-add-work="1">${ico('plus')}観劇記録を保存</button><span class="said" role="status" aria-live="polite"></span></div>
</div>
<div class="register-result" data-register-result="1" hidden></div>
<details class="register-help"><summary>公演の候補について</summary>
<p class="note">たぐりの公演一覧とあなたの記録から候補を出します。候補を選ぶと公演情報も記録に結び付き、次のおすすめの材料になります。すでに記録にあるものは「記録あり」と表示します。<br>
「詳細検索」では、公演名に団体名・劇場・上演日程を加えて絞り込めます。上演日程の年・月・日は任意入力で、入力した項目だけで絞り込めます。その場で外のサイト（CoRich など）は探しません。<br>
一覧に無い公演は「次の更新で探してもらう」から依頼できます。${crawlSearch.requests ? `次の更新（次回は${crawlLabel(nextCrawl(ctx.now))}）で探します。` : '依頼された題名を毎日の更新で探す段はまだ準備中で、いまは探されません。'}待たずに保存することもできます。あとで同じ題名・日付の公演が集まると、自動で結び付きます。</p>
</details>
</div>

<div class="card imx" data-import>${h2('mail', 'まとめて取り込む')}
<p class="lead">カレンダーや購入確認メールから、複数の公演をまとめて追加できます。読み込んだあと、保存する公演を選べます。</p>

<details class="imx-src"><summary>Google カレンダーから</summary>
<p class="note">押すと Google の画面で「カレンダーの閲覧」を許可するか聞かれます。許可すると、過去 5 年の予定を<b>この端末のブラウザが Google から直接読みます</b>。
<b>予定の中身も許可の鍵も、たぐりのサーバーには送らず、保存もしません。</b>題名の候補と日付は、公演と照合するためにたぐりに送ります（照合に使うだけで、保存しません）。</p>
<div class="imx-row"><button type="button" class="primary" data-imx-google="1">Google カレンダーから取り込む</button></div>
<details class="imx-alt"><summary>アドレスやファイルから読み込む</summary>
<p class="note"><b>.ics ファイルを選ぶとき</b>：ファイルはこの端末の中だけで読み、たぐりには送りません。</p>
<p class="note"><b>非公開アドレスを貼るとき</b>：Google はブラウザから直接このアドレスを読ませないので、<b>アドレスをたぐりのサーバーに送り、サーバーが Google からカレンダー全体を取ってきて、この端末に渡します</b>。
アドレスもカレンダーも、たぐりには保存しません（読むのはこの 1 回だけです）。アドレスを送りたくないときは、.ics ファイルを書き出して選んでください。<br>
アドレスは、パソコンの Google カレンダーで、設定 → 取り込むカレンダー → 「カレンダーの統合」にある
<b>「iCal 形式の非公開アドレス」</b>です。コピーして貼ってください。</p>
<div class="imx-row"><input id="imx-url" type="url" inputmode="url" autocomplete="off" aria-label="iCal 形式の非公開アドレス" aria-describedby="imx-url-note" placeholder="https://calendar.google.com/calendar/ical/…/basic.ics" size="40">
<button type="button" data-imx-cal="1">読み込む</button></div>
<p class="note imx-url-note" id="imx-url-note">このアドレスはたぐりのサーバーを通ります（保存はしません）。</p>
<p class="note">書き出した .ics ファイルを選ぶ（この端末の中だけで読みます）：<input id="imx-ics" type="file" accept=".ics,text/calendar"></p>
</details>
</details>
<details class="imx-src"><summary>購入確認メールから</summary>
<p class="note">ぴあ・ローチケ・おけぴ・東宝ナビザーブ・劇団のチケットサービスの書式を読めます（ほかのサイトもできるだけ読みます）。
メールの本文をコピーして貼るか、メールを .eml ファイルで保存してまとめて選んでください。Gmail では、メールの「︙」→「メッセージをダウンロード」で保存できます。<br>
<b>貼った本文もファイルも、この端末の中だけで読み、たぐりには送りません。</b>たぐりに送るのは、読み取った題名と日付だけです。</p>
<textarea id="imx-text" rows="6" placeholder="購入確認メールの本文を貼る（何通分でも、続けて貼れます）"></textarea>
<div class="imx-row"><button type="button" data-imx-mail="1">読み取る</button>
<span class="note">または <input id="imx-eml" type="file" accept=".eml,message/rfc822" multiple></span></div>
</details>
<details class="imx-src"><summary>取り込み時のデータの扱い</summary>
<p class="note">カレンダーの予定や購入確認メールから、観た公演を見つけて足します。
<b>読み方によって、たぐりのサーバーを通るものが違います。</b>それぞれの欄に書きました。
どの読み方でも、予定やメールの本文・カレンダーのアドレスは、たぐりに保存しません。
予定やメールから取り出した<b>題名の候補と日付は、公演と照合するためにたぐりに送ります</b>（照合に使うだけで、保存しません）。
記録として保存するのは、一覧で選んで足した公演の題名・日付・開演時刻・劇場だけです。</p>
</details>
<p class="said" role="status" aria-live="polite"></p>
<div class="imx-found" hidden><p class="imx-head"></p><ul class="imx-list"></ul>
<div class="imx-row"><button type="button" class="primary" data-imx-add="1">選んだものを記録に足す</button></div></div>
</div>

<details class="card register-missed"><summary>${h2('flag', '行けばよかった', missed.length + autoMiss.length ? `<span class="badge part">${missed.length + autoMiss.length} 件</span>` : '')}</summary>
<p class="lead">行きたかったのに行けなかった公演です。<b>「興味あり」にしたまま購入済みにならずに終わった公演は、自動でここに入ります。</b>
ほかの公演は題名で足せます（探す画面の過去の公演からも足せます）。観た本数・評価には入りません。</p>
<div class="miss-add"><label class="fld" for="miss-title"><span class="fl">公演の題名<small class="req">必須</small></span><input id="miss-title" type="text" placeholder="例：夜の果て" size="30"></label>
 <button data-miss="1">${ico('flag')}足す</button><span class="said"></span></div>
${missedHtml(missed, autoMiss)}</details>

${registerDialogHtml()}
<p class="note">保存した記録の評価・感想は、<a href="/rate?t=__TAGURI_TOKEN__">「観た公演の評価」（未評価 ${wait.length} 件）</a>で追加できます。</p>`;
  return {title: '観劇記録を追加', body_html: body};
}

/** serve.on_missed, looked up in D1 at once: the current stage, else a past one, whose title key matches. */
async function missedAction(b, ctx) {
  const title = String(b.title ?? '').trim().slice(0, 200);
  if (!title) throw new ValueError('題名を入れてください');
  const k = titleKey(title);
  let sid = '', fields = {}, note = '';
  // 探す画面の過去の公演から押したときは、その公演を指して来る（同じ題名の別の公演に取り違えない）
  const want = String(b.stage_id ?? '').trim();
  if (/^\d{1,12}$/.test(want)) {
    const past = await ctx.db.prepare('SELECT stage_id, people FROM past_stage WHERE stage_id=?').bind(want).first();
    if (past) {
      sid = past.stage_id;
      try { for (const [role, person] of JSON.parse(past.people || '[]')) if (!String(role).startsWith('#')) fields[role] = fields[role] ? `${fields[role]}、${person}` : person; } catch { fields = {}; }
      note = '過去の公演の一覧から、出演者と作り手だけを拾いました。';
    }
  }
  if (k && !sid) {
    const cur = await ctx.db.prepare("SELECT stage_id, entry FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND tkey=? ORDER BY start DESC LIMIT 1").bind(k).first();
    if (cur) { sid = cur.stage_id; try { fields = JSON.parse(cur.entry || '{}').fields || {}; } catch { fields = {}; } }
    else {
      const past = await ctx.db.prepare('SELECT stage_id, people FROM past_stage WHERE tkey=? ORDER BY start DESC LIMIT 1').bind(k).first();
      if (past) {
        sid = past.stage_id;
        try { for (const [role, person] of JSON.parse(past.people || '[]')) if (!String(role).startsWith('#')) fields[role] = fields[role] ? `${fields[role]}、${person}` : person; } catch { fields = {}; }
        note = '過去の公演の一覧から、出演者と作り手だけを拾いました。';
      }
    }
  }
  if (!sid) note = 'この題名の公演は、手元の公演一覧に見当たりませんでした。';
  const at = new Date(ctx.now + 9 * 3600 * 1000).toISOString().slice(0, 19).replace('T', ' ');
  await ctx.db.prepare(`INSERT INTO missed(user_id,title,created_at,note,stage_id,fields_json,synopsis,lookup_note,looked_up_at) VALUES(?,?,?,?,?,?,?,?,?)
    ON CONFLICT(user_id,title) DO UPDATE SET created_at=excluded.created_at, stage_id=excluded.stage_id, fields_json=excluded.fields_json, lookup_note=excluded.lookup_note, looked_up_at=excluded.looked_up_at`)
    .bind(ctx.uid, title, at, String(b.note ?? '').slice(0, 1000), sid || null, JSON.stringify(fields), '', note, at).run();
  return {body: {ok: true, title}};
}

export const settingsScreens = {
  screens: {settings: settingsScreen, start: startScreen, register: registerScreen},
  actions: {pref_setting: prefSettingAction, missed: missedAction, analysis_optout: optoutAction},
};



