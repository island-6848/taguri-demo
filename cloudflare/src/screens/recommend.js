// 今週のおすすめ: the recommend screen and the three-choice writes (react), answered by
// the Worker from D1 (起案者の指示 2026-10-14「おすすめの画面を移して」).
//
// Not a byte-for-byte port of app._recommend_body. The ranking is the Worker's
// (src/recommend.js, checked against user_recommender by test_recommend_index.py),
// computed from the user's works / favourites / reactions in D1. The cards are
// rendered once a day by the Python screen itself (scripts/build_cards.py,
// render_recommend.ticket) and stored in rec_card; here only the rank, the
// reasons (reason_rows) and the poster are filled in. The 効かせ方 sliders are
// weights.js. Left out for now: the map above the prefecture chips (no outlines in
// D1), the count of shows a setting hid (w_dropped); the impression preferences (感想の好み, #104) are applied in rankedGroups.
import {frac} from './grade.js';
import {scoreFromIndex, d1Access, seedsFromFavourites, gradeOf, MAX_SEED_STAGES, droppedKind, GENRE_AXIS, CONTENT_AXES, favSpread, ratingCount} from '../recommend.js';
import {stageInfo} from './fallback.js';
import {tourBlock} from './schedule.js';
import {parseCredits, isGuide} from './credits.js';
import {chooseVariant, groupOf, VARIANTS} from '../reco-gate.js';
import {readWeights, multipliersOf, weightForm, weightAction, tunedWeights} from './weights.js';
import {impressionAdjust, round6} from '../impression.js';
import {E, ValueError} from './py.js';
import {answerSnapshot, recordShown} from './evalrec.js';
import {ico} from './icons.js';
import {loadWorks, pieceCast} from './works.js';
import {castOffOf} from './diary.js';
import {compose, cardTemplates, posterHtml} from './cards.js';
import {PREFS, prefForm, prefsFor, regionCounts, PAGE_PREF_NOTE} from './prefs.js';
export {prefForm, prefsFor};
import {loadDeclared, loadDeclined, loadKindOff, loadRoles, rolesAllowed, nameHits, KINDS, reactionsOf, declinedBox, kindOffBox, nz as nzName} from './lists.js';

export const TOP = 15;
// 初めて使ったとき（おすすめがまだ無いとき）の案内（起案者の指示 2026-10-18 の文面。使い方ガイドのような小さな絵を添える）。
// 絵の色は画面の色（--ink2・--curtain・--wax）なので、暗い画面でもそのまま読める
const TIP_ART = {
  // 1. 観劇記録を足す: 日記帳のページと「＋」
  record: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<rect x="12" y="8" width="34" height="46" rx="4" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<path d="M12 16h-3M12 26h-3M12 36h-3M12 46h-3" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round"/>
<path d="M19 19h20M19 26h20M19 33h13" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round" opacity=".55"/>
<circle cx="46" cy="46" r="11" fill="var(--curtain)"/><path d="M46 40v12M40 46h12" stroke="var(--surf)" stroke-width="2.6" stroke-linecap="round"/></svg>`,
  // 2. お気に入りに登録する: 人と星
  favourite: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<circle cx="26" cy="22" r="9" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<path d="M9 54c1-11 8-18 17-18s16 7 17 18z" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2" stroke-linejoin="round"/>
<path d="M47 8l3.6 7.4 8.1 1.2-5.9 5.7 1.4 8.1L47 26.6l-7.2 3.8 1.4-8.1-5.9-5.7 8.1-1.2z" fill="var(--wax)" stroke="var(--wax)" stroke-width="1.2" stroke-linejoin="round"/></svg>`,
  // 3. 開幕リマインドで答える: 暦と旗
  reminder: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<rect x="8" y="12" width="40" height="40" rx="4" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<path d="M8 22h40M18 8v8M38 8v8" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round"/>
<path d="M15 30h5M24 30h5M33 30h5M15 38h5M24 38h5M15 46h5" stroke="var(--ink2)" stroke-width="2.4" stroke-linecap="round" opacity=".45"/>
<rect x="31" y="35" width="9" height="9" rx="1.5" fill="var(--curtain)" opacity=".85"/>
<path d="M48 30v26" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round"/>
<path d="M48 30h11l-3 5 3 5H48z" fill="var(--curtain)"/></svg>`,
};
// 番号は見出しの頭。文は上の見出し（おすすめを出すためのワンポイント）と同じ左端から書き始め、絵は右に、文の高さの
// 真ん中に置く（起案者の指示 2026-10-18）
const tip = (n, art, head, body) => `<div class="tip"><div class="tip-t"><p class="tip-h"><span class="tip-n">${n}</span><b>${head}</b></p>${body}</div>${TIP_ART[art]}</div>`;
const TIPS = `<section class="card tips">
<h2>おすすめを出すためのワンポイント</h2>
${tip(1, 'record', '過去の観劇記録を2件以上追加する',
  '<p>「<a href="/register?t=__TAGURI_TOKEN__">観劇記録を追加</a>」から、追加してください。<br>「<a href="/search?t=__TAGURI_TOKEN__">探す</a>」から公演名などで検索して追加することもできます。</p>')}
<p class="tip-or">または</p>
${tip(2, 'favourite', '好きな俳優・劇団・作品を「お気に入り」に登録する',
  '<p>「<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>」に好きな要素を追加してください。<br>共演者や題材などが推薦に反映されます。</p>')}
<p class="tip-or">または</p>
${tip(3, 'reminder', '「開幕リマインド」で興味あり・なしを回答する',
  '<p>「<a href="/recommend/reminder?t=__TAGURI_TOKEN__">開幕リマインド</a>」では、あなたへのおすすめ関係なく、今後開催の全ての公演が表示されます。<br>その中から、気になる作品を選んで、回答してください。</p>')}
</section>
`;
// 出せる候補にすべて答え終えたとき（起案者の指示 2026-10-17「本当に全部回答しきってオススメに出せるものが
// なくなったときは、『回答ありがとうございました』のイラストを出して。その下にワンポイントアドバイス」）。
// 幕の下りた舞台に花束。色は画面の色（--curtain など）なので、暗い画面でもそのまま読める
const THANKS_ART = `<svg class="thx-art" viewBox="0 0 240 132" width="240" height="132" role="img" aria-label="幕の下りた舞台と花束">
<rect x="8" y="10" width="224" height="10" rx="3" fill="var(--curtain)"/>
<path d="M14 20h106v94c-18 6-40 6-58 0-18 6-34 6-48 0z" fill="var(--curtain)" opacity=".85"/>
<path d="M120 20h106v94c-14 6-30 6-48 0-18 6-40 6-58 0z" fill="var(--curtain)" opacity=".85"/>
<path d="M120 20v94" stroke="var(--surf)" stroke-width="2" opacity=".6"/>
<path d="M40 20v90M66 20v94M92 20v92M148 20v92M174 20v94M200 20v90" stroke="var(--surf)" stroke-width="1.2" opacity=".25"/>
<rect x="4" y="114" width="232" height="12" rx="3" fill="var(--ink2)" opacity=".5"/>
<ellipse cx="120" cy="121" rx="46" ry="5" fill="var(--acc)" opacity=".18"/>
<g transform="translate(120 122)">
<path d="M-4 -24l-6 -12M0 -24v-16M4 -24l6 -12" stroke="var(--mute)" stroke-width="2"/>
<circle cx="-12" cy="-38" r="7" fill="var(--acc)"/><circle cx="-12" cy="-38" r="2.5" fill="var(--surf)"/>
<circle cx="12" cy="-38" r="7" fill="var(--acc)"/><circle cx="12" cy="-38" r="2.5" fill="var(--surf)"/>
<circle cx="0" cy="-44" r="8" fill="var(--acc)"/><circle cx="0" cy="-44" r="3" fill="var(--surf)"/>
<path d="M-13 -26h26l-13 26z" fill="var(--surf)" stroke="var(--ink2)" stroke-width="1.5"/>
<path d="M-6 -14q6 5 12 0" stroke="var(--acc)" stroke-width="2.5" fill="none"/>
</g>
</svg>`;
const THANKS = `<section class="card thx" id="rec-thanks">
${THANKS_ART}
<p class="thx-h">回答ありがとうございました</p>
<p class="thx-s">いまおすすめできる公演には、すべて答えていただきました。</p>
<h2>また おすすめが出るようにするには</h2>
<ol>
<li><b>過去の観劇記録を足す</b>：<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>に観た公演を足すと、その出演者・作り手の公演が候補に入ります。</li>
<li><b>観た公演を評価する</b>：<a href="/rate?t=__TAGURI_TOKEN__">評価</a>が増えるほど、好みに合う公演を見つけやすくなります。</li>
<li><b>お気に入りを登録する</b>：好きな俳優・劇団・作品を<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に入れると、その人たちの公演が出ます。</li>
<li><b>「探す」で興味ありを押す</b>：<a href="/search?t=__TAGURI_TOKEN__">探す</a>で見つけた公演に押した興味ありも、次のおすすめの手がかりになります。</li>
<li><b>使わない言葉・都道府県の設定を見直す</b>：絞り込みを外すと、隠れていた候補が出ます。</li>
<li><b>少し待つ</b>：新しい公演は毎日取り込んでいます。日をおいて開くと、新しい候補が出ていることがあります。</li>
</ol>
</section>
`;
// Groups kept per user between requests: enough to fill 15 cards in any one prefecture.
const KEEP = 400;
// 評価がこれより少ないと答え合わせは 1 ms もかからないので、前の控え（数十 KB）を読み解くほうが重い
const GATE_REUSE_MIN = 30;
// 再生（H5）で 1 つずつ外す部品: 興味ありの配り分け・1 段広げる・並べ直し（spreadLeads）・裏の答え合わせ（chooseVariant）・感想の好み（#104）
export const REPLAY_ABLATIONS = ['split', 'expand', 'spread', 'gate', 'impression', 'rollup'];
const VERSION = 'screen-v38';   // v38: a record split into pieces (work_piece) is rated per piece, each person counted once per visit with the pieces they were in shrunk by PIECE_RHO (dec-split-pieces, 2026-10-19); v37: a troupe's reason has no 主催, a production already on お気に入り under another id stays off (2026-10-18); v36: a favourite's reason names its role, the work and this person's role there, rows without an explanation are left out (2026-10-18); the ✕ (dismiss) and role-narrowed favourites (declared_roles) change the seeds (2026-10-18); v35: fine subject likes roll up the vocabulary to broader concepts (SF) across 3+ branches, and the reason names them (rolledThemeWords, 2026-10-18); v34: 作曲・音楽 spread from favourites too (FAV_SPREAD_W, 2026-10-18); v33: favourites' own stages (お気に入りの一覧) seed too, spread by role (FAV_SPREAD_W), reasons name the favourite, the 効かせ方 defaults per group (2026-10-18); v32: the reasons name the newest and oldest works, favourites' works too (2026-10-18); v31: 感想で書いた特徴への好みが順位と理由に効く（#104）; v30: the hidden check's choice is reused while the ratings are unchanged (CPU, #138); v29: the cache keeps only the reasons the screens show (CPU, #138); v28: the hidden check leaves out the dropped kinds as the ranking does (#115); v27: a rating of a record dated after today is not learnt from (#116); v26: ratings ordered by when they were rated (works.rated_at), not by the last edit (#112); v25: a name in the 興味あり note counts only when not denied or compared against (#111); v24: a 興味あり copied to the tour's other venues counts once (#110); v23: 興味なし weakens after the split, not before (#109); v22: favourite seeds weigh FAV_SEED_W (お気に入り＞興味あり); v21: credits read only where needed (CPU); v20: a production answered under another stage id stays out; v19: same title + (group / venue / a shared person) is one card; v18: one card per title+group (sameProduction); v17: no 出典 on the reasons; v16: #会場 dropped, 行けない (interest=2) as a liked seed; v15: 出さない語 also hits the kind tags; v14: #ジャンル (a genre turned off hides its stages); v13: no 原作「原作もの」 (DROPPED_KEYS); v12: no #値段 (DROPPED_AXES); v11: reasons of answered stages (answered_why); v2: the user's 効かせ方 (rank_weight) and the per-group counts; v3: 興味あり as seeds; v4: diag; v5: 興味あり split (impl-interest-split); v6: by part importance; v7: tiers + トメ; v8: two tiers only; v9: トメ joins the main roles; v10: spread leads + one-step partners
export {PREFS} from './prefs.js';
const KIND_LABEL = {'#形式': '形式', '#原作': '原作', '#翻訳': '', '#原作の国': '原作の国', '#会場': '劇場', '#題材': '題材', '#ジャンル': 'ジャンル'};
// 理由に添える作品名は、いちばん新しい公演といちばん古い公演の 2 つまで（起案者の指示 2026-10-18「公演タイトルすでに
// 書けているものも、最大2件だけ表示。一番最近の公演と一番古い公演から計2個」）
const WORKS_SHOWN = 2;
// Every scale sorts with the marks by its place: the top (◎, ★5, ○ of ○×) first, the bottom last
// (grade.js). 興味あり comes after every rating.
const MARK_ORDER = {'◎': 0, '○': 1, '△': 2, '×': 3, '興味あり': 4};
const markRank = v => (Object.hasOwn(MARK_ORDER, v) ? MARK_ORDER[v] : frac(v) === null ? null : 3 * (1 - frac(v)));

const pad2 = n => String(n).padStart(2, '0');
const chunks = (xs, n) => Array.from({length: Math.ceil(xs.length / n)}, (_, i) => xs.slice(i * n, i * n + n));

/** The user's rated works as the recommender reads them, with their linked stage's credits. */
async function ratedWorks(ctx, access) {
  // 作品ごとに分けた記録（work_piece、dec-split-pieces）。評価した作品があれば、記録そのものの評価の代わりに作品ごとの行にする
  const ratedPieces = w => (w.pieces || []).filter(p => gradeOf(p.verdict));
  // 観た日がまだ来ていない記録（先の予定・日付の打ち間違い）の評価は、観たあとの好みとして学ばない（#116。
  // docs/impression-preferences.md「未来の記録…は学習に含めない」、感想の補正 app._apply_impression_preferences と同じ
  // first_date <= 今日。日付の無い記録は数える）。日付を直せば、次の計算から入る（控えの印に works の更新日時と今日がある）
  const works = (await loadWorks(ctx)).filter(w => !w.unseen && w.stage_id && (gradeOf(w.verdict) || ratedPieces(w).length) && (w.first_date || '') <= ctx.today);
  // 評価した順は、評価を付けた（直した）時刻（rated_at、#112）。updated_at は感想・日付の編集でも進むので、
  // rated_at の無い行（移行の前に書いた行）だけ updated_at で代える
  const {results} = await ctx.db.prepare("SELECT work_key, COALESCE(rated_at, updated_at) AS rated_at FROM works WHERE user_id=? AND verdict IS NOT NULL AND verdict<>''").bind(ctx.uid).all();
  const updated = new Map(results.map(r => [r.work_key, r.rated_at]));
  const people = await access.peopleFor([...new Set(works.map(w => w.stage_id))]);
  // 観た回に出ていなかった出演者（Wキャスト・休演、works.cast_off）は、この記録の材料から外す。
  return works.flatMap(w => {
    const off = new Set(castOffOf(w));
    const row = {key: w.work_key, title: w.title, stage_id: w.stage_id, verdict: w.verdict, cast_off: [...off],
      date: w.last_date || w.first_date || '', aspects: w.aspects || '', rated_at: updated.get(w.work_key) || '', note: w.note_impression || '',
      people: (people.get(w.stage_id) || []).filter(([role, person]) => !(role === '出演' && off.has(person)))};
    const ps = ratedPieces(w);
    if (!ps.length) return [row];
    // 作品ごとの行: 出演はその作品に出ていた人だけ（cast_in。空なら全員）、スタッフ・公演の種類は公演のまま。
    // whole は分ける前の 1 公演の行（裏の答え合わせ・感想の好みは 1 公演を 1 件で数える。wholeStages）
    const notes = [w.note_impression || '', ...(w.pieces || []).map(p => p.note || '')].filter(n => n.trim());
    const whole = {...row, note: notes.join('\n')};
    return ps.map(p => {
      const cast = pieceCast(p);
      return {...row, key: `${w.work_key}\u0000${p.idx}`, occasion: w.work_key, share: 1 / ps.length, whole,
        verdict: p.verdict, aspects: p.aspects || '', rated_at: p.rated_at || row.rated_at, note: p.note || '',
        people: cast ? row.people.filter(([role, person]) => role !== '出演' || cast.has(person)) : row.people};
    });
  });
}

/**
 * 作品ごとに分けた行を、分ける前の 1 公演の行に戻す。裏の答え合わせ（評価の付いた 1 公演だけ）と感想の好み
 * （作品ごとの感想をまとめた 1 件）は、同じ晩の作品を別々に数えると、作品どうしで答えが漏れ、票が重なるため
 */
export function wholeStages(rated, {graded = false} = {}) {
  const out = [], seen = new Set();
  for (const r of rated) {
    if (!r.occasion) { out.push(r); continue; }
    if (seen.has(r.occasion)) continue;
    seen.add(r.occasion);
    if (!graded || gradeOf(r.whole.verdict)) out.push(r.whole);
  }
  return out;
}

/**
 * 興味ありを押した公演（新しい順に MAX_SEED_STAGES まで）を、お気に入りと同じ仮の ◎（seeds）にする。
 * 起案者の指示（2026-10-15）「一回その案にしてみて」（q-interest-seed）。重みはお気に入りと同じで、
 * 評価が増えるほど薄まる（recommend.personValues の SEED_K / (SEED_K + 評価の数)）。
 * 索引に人物の無い公演（一覧 catalogue にだけある開幕リマインドの公演など）は、出演欄から人物を読む。
 */
async function interestSeeds(ctx, access, ratedSids = new Set()) {
  // reaction は日ごとの行（label = その日）なので、公演ごとに新しい答えで上書きしてから選ぶ（lists.reactionsOf と同じ）。
  // 購入済み（owned=1）は興味ありと同じ手がかりにする。購入済みを押しても interest は前の答えのまま（REACT.owned）なので、
  // 興味ありを押さずに買った公演が種にならず、興味ありを押してから買った公演とで重さが違っていた（起案者の指示 2026-10-19
  // 「興味あり押さずにいきなり購入済みに入れた作品でも、興味あり分加算してあげないとだめじゃない？」）
  const {results} = await ctx.db.prepare('SELECT stage_id,interest,owned,source,updated_at FROM reaction WHERE user_id=? AND (interest IS NOT NULL OR owned=1) ORDER BY updated_at')
    .bind(ctx.uid).all();
  const last = new Map();
  for (const r of results) { last.delete(r.stage_id); last.set(r.stage_id, [Number(r.owned) === 1 ? 1 : Number(r.interest), String(r.source || '')]); }
  // 評価を付けた公演（ratedWorks に入る記録）は、評価 1 回分だけを数え、ここの種からは外す。興味あり→観て評価、の順に
  // 付けた公演だけが 2 回分になり、評価だけの過去の記録と重さが揃わなかった（同上 2026-10-19）。観た日が先の記録は
  // 評価を学ばないので、種のまま残る
  for (const s of ratedSids) last.delete(String(s));
  // ツアーのほかの会場へ写した答え（reactAction の siblings、source が '…_tour'）は、押した 1 回と同じ答えなので
  // 手がかりに数えない（#110）。数えると 1 回の興味ありが会場の数だけの重さになり、MAX_SEED_STAGES も写しで埋まる。
  // 会場の行は、答えた公演をおすすめから外すため（answered）と一覧のためにそのまま残す。いちばん新しい答えが写しの
  // 会場だけを外すので、あとでその会場を直接押し直した答えは数える
  const newest = (...vs) => [...last].filter(([, [x, src]]) => vs.includes(x) && !src.endsWith('_tour')).map(([s]) => String(s)).reverse().slice(0, MAX_SEED_STAGES);
  // 行けない（2）も、気になった公演として興味ありと同じ向きの手がかりにする
  // 興味ありの画面で ✕ を押した公演（4、dismiss_strong）は強い負の手がかり（recommend.REJECT_W）。おすすめ・お気に入りなどで
  // ✕ を押した公演（3、dismiss）は「候補から消す」だけで、好みの手がかりにはしない（起案者の指示 2026-10-18）
  const sids = newest(1, 2), noes = newest(0), rejects = newest(4);
  if (!sids.length && !rejects.length) return {seeds: [], disliked: [], n: 0};
  const all = [...sids, ...noes, ...rejects];
  const [people, info] = await Promise.all([access.peopleFor(all), stageInfo(ctx.db, all)]);
  for (const s of all) {
    if (people.get(s)?.length) continue;
    const p = parseCredits(info.get(s)?.fields || {});
    if (p.length) people.set(s, p);
  }
  // 「なぜ気になったか」（reaction.note、任意）。書いてあれば、そこに名前のある人に多めに配る。
  const notes = await reactionsOf(ctx);
  // 出演欄の文（書かれた順・役名・アンサンブルの見出しが残っている）。役柄の重さに使う（recommend.castImportance）。
  const one = s => ({stage_id: s, title: info.get(s)?.title || '', date: info.get(s)?.start || '', note: notes.get(s)?.note || '',
    cast_text: String(info.get(s)?.fields?.['出演'] || ''), people: people.get(s)});
  return {n: sids.length, seeds: sids.filter(s => people.get(s)?.length).map(one),
    disliked: [...noes.filter(s => people.get(s)?.length).map(one), ...rejects.filter(s => people.get(s)?.length).map(s => ({...one(s), strong: true}))]};
}

/**
 * お気に入りの一覧に出る公演（lists.nameHits の hits）を、索引から引いた種（seedsFromFavourites）に足す。
 * 多くて MAX_SEED_STAGES まで。人物は索引（rec_people）から、無ければ出演欄から読む（interestSeeds と同じ）。
 * 控えが古いときだけ動き、D1 の読み取りは足す公演の数の行（多くて 60 行 × 2 表）。
 */
const FAV_LABEL = /^[^「]+「(.*)」$/u;
async function hitSeeds(ctx, access, hits, seeds) {
  const have = new Set(seeds.map(s => String(s.stage_id)));
  const room = MAX_SEED_STAGES - seeds.length;
  const add = [...hits.keys()].map(String).filter(s => !have.has(s)).sort().slice(0, Math.max(0, room));
  if (!add.length) return seeds;
  const people = await access.peopleFor(add);
  const miss = add.filter(s => !people.get(s)?.length);
  if (miss.length) {
    const info = await stageInfo(ctx.db, miss);
    for (const s of miss) { const p = parseCredits(info.get(s)?.fields || {}); if (p.length) people.set(s, p); }
  }
  const favOf = sid => [...new Set((hits.get(sid)?.a || []).map(x => (FAV_LABEL.exec(x) || [])[1]).filter(Boolean))].sort();
  return [...seeds, ...add.filter(s => people.get(s)?.length).map(s => ({stage_id: s, people: people.get(s), fav: favOf(s)}))];
}

/**
 * 理由の人のうち、評価の履歴が無く、お気に入りの公演にいたことで上がった人 -> 登録した名前（理由に書く）。
 * 同じ人が何人ものお気に入りの公演にいれば、いっしょの公演が多い名前（同じ数なら名前の順で先）。
 */
export function favOrigins(seeds, skip = new Set()) {
  const count = new Map();                     // "role\tperson" -> Map(fav -> 公演の数)
  for (const s of seeds) for (const [role, p] of new Map((s.people || []).map(x => [x[0] + '\t' + x[1], x])).values()) {
    if (role.startsWith('#') || skip.has(p) || !favSpread(role)) continue;
    const k = role + '\t' + p;
    if (!count.has(k)) count.set(k, new Map());
    for (const f of s.fav || []) count.get(k).set(f, (count.get(k).get(f) || 0) + 1);
  }
  const out = new Map();
  for (const [k, m] of count) {
    const best = [...m].sort((a, b) => (b[1] - a[1]) || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))[0];
    if (best) out.set(k, best[0]);
  }
  return out;
}

/**
 * お気に入りから広げた人の理由に書く作品: (role, person) -> [登録した名前, その種類, [[登録した名前のその作品での役職, 作品名, この人のその作品での役職]...]]。
 * 作品は新しい初日から（いちばん新しい・いちばん古いを出す。worksText と同じ）。登録した名前の役職は、人・原作者ならその公演の
 * 名簿で同じ名前（空白を詰めて NFKC）の役職。団体・主催・作品・題材には付けない（団体は主催とは限らない）。名簿に無ければ空（役職を書かない）。
 * 起案者の指示 2026-10-18「『お気に入りの横山拓也と同じ公演に関わる人：『雉はじめて鳴く』』→『横山拓也 演出『雉はじめて鳴く』出演』」
 */
const ROLE_RANK = role => -favSpread(role);
const rolesText = roles => [...new Set(roles)].sort((a, b) => (ROLE_RANK(a) - ROLE_RANK(b)) || (a < b ? -1 : a > b ? 1 : 0)).join('・');
const FAV_WORKS_KEPT = 8;
export function favDetails(seeds, origins, info, kindOf) {
  const out = new Map();
  for (const [k, name] of origins) {
    const [role, person] = k.split('\t');
    const kind = kindOf.get(name) || '人';
    const works = [];
    for (const s of seeds) {
      if (!(s.fav || []).includes(name) || !(s.people || []).some(([r, p]) => r === role && p === person)) continue;
      const st = info.get(String(s.stage_id)) || {};
      if (!st.title) continue;
      const mine = (s.people || []).filter(([r, p]) => p === person && !r.startsWith('#')).map(([r]) => r);
      // 団体を登録しても、その団体が主催とは限らないので役職は書かない（起案者の指示 2026-10-18「団体は必ずしも主催じゃない」）
      const favRole = ['団体', '主催', '作品', '題材'].includes(kind) ? ''
        : rolesText((s.people || []).filter(([r, p]) => !r.startsWith('#') && nzName(p) === nzName(name)).map(([r]) => r));
      works.push([String(st.start || ''), favRole, st.title, rolesText(mine)]);
    }
    works.sort((a, b) => (!a[0] - !b[0]) || (a[0] < b[0] ? 1 : a[0] > b[0] ? -1 : 0) || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
    const seen = new Set();
    const uniq = works.filter(w => !seen.has(w[2]) && seen.add(w[2])).slice(0, FAV_WORKS_KEPT).map(w => w.slice(1));
    out.set(k, [name, kind, uniq]);
  }
  return out;
}

/**
 * お気に入りから広げた人の括弧の中（起案者の指示 2026-10-18）。人・原作者「横山拓也 演出『雉はじめて鳴く』出演」、
 * 団体「劇団乙の『舞台ふたつめ』出演」（主催とは限らないので役職は書かない）、作品「『舞台ふたつめ』出演」、題材「題材「科学」の『舞台』出演」。
 * 役職の分からない登録名は役職を書かない（「横山拓也『雉はじめて鳴く』出演」）。作品が 2 つで役職が同じなら
 * 「演出『A』・『B』出演」、役職が違えば「演出『A』出演、脚本『B』出演」。3 つ以上は新旧 2 つと「ほか n 本」。
 * このカードの公演そのもの（own）は作品に数えない。作品を書けないとき（題名の引けない古い控え）は「（○○と同じ公演）」
 */
export function favText(name, kind, works, own = '') {
  const ws = (works || []).filter(w => w[1] && w[1] !== own);
  if (!ws.length) return `（${E(name)}と同じ公演）`;
  const shown = ws.length > WORKS_SHOWN ? [ws[0], ws[ws.length - 1]] : ws;
  const rest = ws.length - shown.length;
  const groups = [];
  for (const [fr, t, pr] of shown) {
    const g = groups.find(x => x.fr === fr && x.pr === pr);
    if (g) g.t.push(t); else groups.push({fr, pr, t: [t]});
  }
  const head = kind === '作品' ? '' : kind === '題材' ? `題材「${E(name)}」の` : kind === '団体' || kind === '主催' ? `${E(name)}の` : E(name);
  const body = groups.map((g, i) => (g.fr ? (i || !head ? '' : ' ') + E(g.fr) : '') + g.t.map(t => `『${E(t)}』`).join('・') + E(g.pr)).join('、');
  return `（${head}${body}${rest > 0 ? ` ほか ${rest} 本` : ''}）`;
}

/** 観た回に出ていなかったと本人が外した出演者（works.cast_off）。1 段広げるときにも戻さない。 */
const castOffKeys = rated => new Set(rated.flatMap(r => (r.cast_off || []).map(n => '出演\u0000' + n)));

/**
 * (role, person) -> 作品名。理由の行に具体的な作品名を出す（measure_nets.person_titles）。
 * 材料は評価した記録（観た日）・興味ありを押した公演・お気に入りの名前から引いた公演（どちらも初日）。
 * 並びは新しい日付から（同じ日付は印の順）。日付の無いものは後ろ。worksText は先頭（いちばん新しい）と
 * 末尾（いちばん古い）だけを出す（起案者の指示 2026-10-18）。
 * 前はお気に入りから引いた公演を入れていなかったので、お気に入りだけで上がった人が「（お気に入り・興味ありの公演から）」
 * になっていた（同じ日の指示「ちゃんと公演タイトル書いて」）。
 */
function personTitles(rated, liked = [], favs = []) {
  const acc = new Map();
  const rows = [...rated, ...liked.map(s => ({verdict: '興味あり', date: s.date || '', title: s.title, people: s.people})),
    ...favs.map(s => ({verdict: 'お気に入り', date: s.date || '', title: s.title, people: s.people}))];
  for (const r of rows) {
    const mark = r.verdict === 'お気に入り' ? 5 : markRank(r.verdict);
    if (mark === null || !r.title) continue;
    for (const [role, person] of r.people || []) {
      const k = role + '\t' + person;
      if (!acc.has(k)) acc.set(k, []);
      acc.get(k).push([mark, String(r.date || ''), r.title]);
    }
  }
  const out = new Map();
  for (const [k, rows] of acc) {
    rows.sort((a, b) => (!a[1] - !b[1]) || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0) || (a[0] - b[0]));
    out.set(k, [...new Set(rows.map(r => r[2]))]);
  }
  return out;
}

const worksText = (titles, n) => {
  // 作品名の引けない人は本数で書く。本数も 0（評価の無い人）なら何も添えない（「履歴 0 本」「（お気に入り・興味ありの
  // 公演から）」とは書かない。起案者の指示 2026-10-18「おすすめ理由に『（お気に入り・興味ありの公演から）』って書くのやめて」）
  if (!titles?.length) return Math.trunc(n) ? `（履歴 ${Math.trunc(n)} 本）` : '';
  // いちばん新しい公演（先頭）といちばん古い公演（末尾）の 2 つ。残りは本数だけ
  const shown = titles.length > WORKS_SHOWN ? [titles[0], titles[titles.length - 1]] : titles;
  const rest = titles.length - shown.length;
  return '（' + shown.map(t => `『${E(t)}』`).join('・') + (rest > 0 ? ` ほか ${rest} 本` : '') + '）';
};

/**
 * render_recommend.reason_rows for the Worker's reasons (people, then kinds of show).
 * 括弧の説明（作品名・履歴の本数・好きな人・お気に入りの名前）を書けない行は出さない（起案者の問い 2026-10-18「括弧で
 * おすすめ理由がついてないものがおすすめ理由に出ちゃってる。なぜ？」、fix-reason-no-paren）。評価の無い人・形式
 * （興味あり・お気に入りの公演だけで上がったもの）の作品名が、このカードの公演そのものしか無い（cardsHtml が除く）か、
 * 引けなかったときに、名前だけの行になっていた。`own` はこのカードの公演の題名（お気に入りの作品から除く）
 */
export function reasonRows(group, titles, own = '') {
  const out = [];
  // 1 段広げて来た人（scoreFromIndex の via）: 「○○とよく組む人」と書く
  const via = new Map(group.via || []);
  // お気に入りの公演にいたことで上がった人（rankedGroups の fav）: 登録した名前と、その公演の題名で書く
  // （起案者の指示 2026-10-18「理由の文は、登録した名前（ここでは堂本光一）を書く」）
  // 控えの形は [鍵, 登録した名前, 種類, 作品]（v35）。前の形（[鍵, 登録した名前]、興味ありに残した理由）は作品なしで書く
  const fav = new Map((group.fav || []).map(([k, ...rest]) => [k, rest]));
  for (const [, role, person, n] of group.parts.slice(0, 4)) {
    // 案内の文（「スタッフ欄をご覧ください。」）は人ではない。索引が入れ替わるまで残る行も出さない（fix-credit-guide-text）
    if (isGuide(person)) continue;
    const k = role + '\t' + person, w = via.get(k), f = fav.get(k);
    const why = w ? `（好きな${E(w)}と同じ公演に関わる人）` : f ? favText(f[0], f[1], f[2], own) : worksText(titles.get(k), n);
    if (!why) continue;
    // 太字の名前は、その人の画面へ（起案者の指示 2026-10-19「おすすめ理由になってる項目の黒太字押したら、各個別ページに飛ぶように」）
    out.push(`<li class="rs b"><span class="net">人物</span>${E(role)} <a class="rsl" href="/recommend/person?t=__TAGURI_TOKEN__&amp;n=${encodeURIComponent(person)}&amp;r=${encodeURIComponent(role)}"><b>${E(person)}</b></a>`
      + `<span class="n">${why}</span>`
      + `<button class="rsx" data-word="${E(person)}" title="この人物を理由に出さない">✕</button></li>`);
  }
  for (const [, axis, tag, n] of group.kinds.filter(k => !droppedKind(k[1], k[2])).slice(0, 2)) {
    const why = worksText(titles.get(axis + '\t' + tag), n);
    if (!why) continue;
    // 「漫画原作」のように中身が見出しを含むときは見出しを出さない（「原作 漫画原作」にしない）
    const label0 = Object.hasOwn(KIND_LABEL, axis) ? KIND_LABEL[axis] : axis.replace(/^#+/, '');
    const label = label0 && tag.endsWith(label0) ? '' : label0;
    // 札の表示は「形式」（起案者の指示 2026-10-18「『種類』ってよりは形式？って表現近いと思う」。人物・形式でそろえる）。
    // 札と同じ見出し（#形式）は重ねて書かない（「形式 形式 ミュージカル」にしない）
    out.push(`<li class="rs c k"><span class="net">形式</span>${label && label !== '形式' ? E(label) + ' ' : ''}<a class="rsl" href="/recommend/kind?t=__TAGURI_TOKEN__&amp;a=${encodeURIComponent(axis)}&amp;w=${encodeURIComponent(tag)}"><b>${E(tag)}</b></a>`
      + `<span class="n">${why}</span>`
      + `<button class="rsx" data-kindoff="${E(axis + '\t' + tag)}" title="この理由をおすすめに使わない（公演は消さない）">✕</button></li>`);
  }
  // 感想で書いた好み（#104）: 特徴と、その根拠にした自分の感想の一文
  for (const [label, sign, title, quote] of group.imp || []) {
    out.push(`<li class="rs c i"><span class="net">感想</span><b>${E(label)}</b>`
      + `<span class="n">（${title ? `『${E(title)}』の` : ''}感想「${E(quote)}」${sign < 0 ? 'で合わないと書いた' : ''}）</span></li>`);
  }
  return out.length ? out.join('') : '<li class="rs none">理由を出せていません</li>';
}

const IMP_EXTRA = 40;
/** impression.score の理由を控えに残す形にする: [表示名, 向き, 作品名, 感想の一文（短く）]。画面に出す 2 つだけ（控えを軽くする、#138） */
const IMP_QUOTE = 40;
export function impWhy(parts) {
  return parts.slice(0, 2).map(p => {
    const q = [...String(p.evidence?.quote || '')];
    return [p.label, p.value > 0 ? 1 : -1, p.evidence?.title || '', q.length > IMP_QUOTE ? q.slice(0, IMP_QUOTE).join('') + '…' : q.join('')];
  });
}

/** Each item's people without the kind keys the user turned off ('#原作\tオリジナル'; q-kind-reason-off). */
export function withoutKinds(items, off) {
  if (!off.size) return items;
  const keep = people => (people || []).filter(([role, p]) => !(role.startsWith('#') && off.has(role + '\t' + p)));
  return items.map(r => ({...r, people: keep(r.people), ...(r.whole ? {whole: {...r.whole, people: keep(r.whole.people)}} : {})}));
}

/** Stages the user has answered (interest / not interested / owned): out of the recommendations. */
async function answered(ctx) {
  const {results} = await ctx.db.prepare('SELECT DISTINCT stage_id FROM reaction WHERE user_id=? AND (interest IS NOT NULL OR owned=1)').bind(ctx.uid).all();
  return new Set(results.map(r => r.stage_id));
}

/**
 * Ranked productions for the user, one slot each, with every venue of the production
 * (stage_id, pref, start) so a prefecture filter can pick the venue. Cached in rec_cache
 * until the index, the date, or the user's works / favourites / reactions change.
 */
export async function rankedGroups(ctx) {
  const db = ctx.db;
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  if (!ver) return {ready: false, groups: [], titles: new Map()};
  const st = await db.prepare(`SELECT (SELECT count(*) FROM works WHERE user_id=?1) AS wn, (SELECT max(updated_at) FROM works WHERE user_id=?1) AS wm,
    (SELECT count(*) FROM reaction WHERE user_id=?1) AS an, (SELECT max(updated_at) FROM reaction WHERE user_id=?1) AS am,
    (SELECT count(*) FROM favourites WHERE user_id=?1) AS fn, (SELECT count(*) FROM merges WHERE user_id=?1) AS mn,
    (SELECT count(*) FROM excluded WHERE user_id=?1) AS xn,
    (SELECT max(updated_at) FROM app_setting WHERE user_id=?1 AND key IN ('declared','declined','declared_roles')) AS dm,
    (SELECT max(updated_at) FROM rank_weight WHERE user_id=?1) AS km,
    (SELECT v FROM rec_meta WHERE k='rec_card') AS cv,
    (SELECT v FROM rec_meta WHERE k='index_rev') AS ir, (SELECT rec_rev FROM users WHERE id=?1) AS rr, (SELECT works_rev FROM users WHERE id=?1) AS wr`).bind(ctx.uid).first();
  // 索引は差分で入れ、版（ver）は 'live' のまま変わらないので、中身が変わった合図は index_rev（q-index-incremental）。
  // 「使わない」にした種類の理由は中身ごと控えの印に入れる（同じ秒に外して戻しても、控えが古いまま残らない）
  // 出さない語も中身ごと（同じ秒に足して外すと、更新日時だけでは控えが古いまま残る）
  const off = new Set(await loadKindOff(ctx));
  const words = await loadDeclined(ctx);
  // rec_rev は材料の表に書くたびに進む（migrations/0035 のトリガー、#189）。件数と更新時刻（秒）だけでは、同じ秒の
  // 付け直しで印が変わらなかった
  const stamp = [VERSION, ver, st.ir || '', ctx.today, st.rr ?? '', st.wn, st.wm, st.an, st.am, st.fn, st.mn, st.xn, st.dm, st.cv, st.km, [...off].sort().join(','),
    [...words].sort().join('\n')].join('|');
  const access = d1Access(db, ver);
  // 部品を外した計算（ctx.ablate）は控えと印が同じなので、控えを読まず、書かない
  // 控えは印に関係なく 1 行読む（印が違っても、裏の答え合わせの結果だけは使えることがある。下の gateKey）
  const prev = ctx.ablate ? null : await db.prepare('SELECT stamp,body FROM rec_cache WHERE user_id=?').bind(ctx.uid).first();
  if (prev && prev.stamp === stamp) {
    const body = JSON.parse(prev.body);
    return {...body, titles: new Map(body.titles), cached: true};
  }
  // 「使わない」にした種類の理由（q-kind-reason-off）は、評価・興味あり・お気に入りのどこからも値を持たせない
  const rated = withoutKinds(await ratedWorks(ctx, access), off);
  // 部品を外した計算（手元の再生 replay_eval.py の H5 だけが ctx.ablate を渡す。本番は渡さないので動きは変わらない）
  const ablate = ctx.ablate || {};
  // 裏の答え合わせ（chooseVariant）は評価だけで決まる（評価の数・最後の更新・今日・使わない種類）。興味ありを押しただけで
  // 控えが捨てられたときは、前の控えに残した結果をそのまま使う。評価が多いと計算の 2〜4 割をここで使っていた（#138）
  const gateKey = [VERSION, ctx.today, st.wr ?? '', st.wn, st.wm, [...off].sort().join(',')].join('|');
  let gate = null;
  if (!ablate.gate && prev && ratingCount(rated) >= GATE_REUSE_MIN) {
    try { const g = JSON.parse(prev.body).gate; if (g && g.key === gateKey) gate = g.choice; } catch { /* recompute */ }
  }
  if (!gate) gate = ablate.gate ? {multipliers: VARIANTS.base, aspects: true} : chooseVariant(wholeStages(rated, {graded: true}));
  // 効かせ方（本人が決めた段）は、裏の答え合わせが選んだ倍率に掛け合わせる。
  // 「効かせない」（0）にした項目は、順位からも理由からも消える（scoreFromIndex は 0 の寄与を捨てる）
  const weights = await readWeights(ctx), own = multipliersOf(weights);
  const multipliers = {...gate.multipliers};
  for (const [g, m] of Object.entries(own)) multipliers[g] = (Object.hasOwn(multipliers, g) ? multipliers[g] : 1.0) * m;
  const declared = await loadDeclared(ctx);
  // 役職で絞った人（q-favourite-homonym）は、その役職の索引だけを引く（同姓同名の別の人の公演を種にしない）
  const roleOf = await loadRoles(ctx);
  const favourites = KINDS.flatMap(kind => (declared[kind] || []).map(name => ({name, kind,
    ...(kind === '人' && roleOf[name] ? {roles: rolesAllowed(roleOf[name])} : {})}))).slice(0, 200);
  const fav = await seedsFromFavourites(access, favourites), skip = fav.skip;
  // Stages of a registered name are お気に入り, stages of a word not to show are left out
  // (app._rebucket): neither is ranked here.
  const {hits, declined} = await nameHits(ctx, declared, words);
  // お気に入りの一覧に出る公演（名前を空白を詰めて本文で当てた公演）も種にする（起案者の問い 2026-10-18「お気に入りに
  // 登録するとおすすめが出る、って書いてあるのに、何もでないときがある」、fix-fav-only-no-reco）。種は索引の役職
  // （SEED_ROLES）で名前そのままを引くだけだったので、一覧には公演が出るのに種が 0 件で、おすすめも 0 件になることがあった
  const favSeeds = await hitSeeds(ctx, access, hits, fav.seeds);
  // 登録した人の名前は、索引の書き方（空白なし・NFKC）でも理由に出さない（その人の公演はお気に入りの一覧に出る）
  const favNames = new Set(KINDS.filter(k => k === '人' || k === '原作者').flatMap(k => declared[k] || []).map(nzName));
  for (const s of favSeeds) for (const [role, p] of s.people || []) if (!role.startsWith('#') && favNames.has(nzName(p))) skip.add(p);
  const interest = await interestSeeds(ctx, access, new Set(rated.map(r => String(r.stage_id)))), nLiked = interest.n;
  const liked = withoutKinds(interest.seeds, off), disliked = withoutKinds(interest.disliked, off);
  const seeds = withoutKinds(favSeeds, off);
  const ranked = await scoreFromIndex({...access, rated: gate.aspects ? rated : rated.map(r => ({...r, aspects: []})),
    multipliers, today: ctx.today, seeds, skip, liked, disliked, expand: {peopleFor: access.peopleFor, exclude: castOffKeys(rated)}, ablate});
  // 感想で書いた特徴への好み（#104、起案者の指示 2026-10-18「感想で書いた内容を推薦に反映させるところまで」）。
  // app._apply_impression_preferences と同じく「作品の内容」（theme）の効かせ方を掛け、点の付いた候補は
  // 上げ下げし、点の無い公演は好みが正のときだけ加える。規則だけで動き、好みのある言葉だけを索引から引く
  const themeMul = Object.hasOwn(multipliers, 'theme') ? multipliers.theme : 1.0;
  const imp = themeMul > 0 && !ablate.impression ? await impressionAdjust(access, wholeStages(rated), CONTENT_AXES) : null;
  if (imp?.adjust.size) {
    const inRanked = new Set(ranked.map(c => String(c.stage_id)));
    for (const c of ranked) {
      const a = imp.adjust.get(String(c.stage_id));
      if (a) { c.strong = round6(c.strong + a[0] * themeMul); c.imp = impWhy(a[1]); }
    }
    const seeded = new Set(seeds.map(r => String(r.stage_id)));
    // 感想だけが理由の公演は手がかりが弱いので、補正の大きい順に IMP_EXTRA まで（索引には終わった公演も入っているので、
    // その数倍だけ日付を引く）。全部を加えると、感想を多く書く人で後の束ねる計算が数百件ぶん重くなる
    const extra = [...imp.adjust].filter(([sid, [v]]) => v > 0 && !inRanked.has(sid) && !seeded.has(sid))
      .sort((x, y) => (y[1][0] - x[1][0]) || (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0)).slice(0, IMP_EXTRA * 5);
    if (extra.length) {
      const stages = await access.stagesFor(extra.map(([sid]) => sid));
      let added = 0;
      for (const [sid, [v, parts]] of extra) {
        const s = stages.get(sid);
        if (!s || (s.end && s.end < ctx.today) || (s.start && s.start <= ctx.today)) continue;
        ranked.push({stage_id: sid, b: 0, strong: round6(v * themeMul), tour: s.tour || '', parts: [], kinds: [], imp: impWhy(parts)});
        if (++added >= IMP_EXTRA) break;
      }
    }
    ranked.sort((x, y) => (y.strong - x.strong) || (y.b - x.b) || (String(x.stage_id) < String(y.stage_id) ? -1 : String(x.stage_id) > String(y.stage_id) ? 1 : 0));
  }
  // app._weight_counts: per group, the candidates it matches (the people and kinds that raised them).
  const wCounts = {};
  for (const c of ranked) {
    const seen = new Set([...c.parts, ...c.kinds].map(p => groupOf(p[1])));
    for (const g of seen) wCounts[g] = (wCounts[g] || 0) + 1;
  }
  const done = await answered(ctx);
  // 理由の ✕ で外したジャンル（2.5次元・宝塚）は、その公演ごと出さない（起案者の指示 2026-10-16
  // 「おすすめ理由に2.5次元として出してほしい。いらない人はそれ✕押せばいい」）。索引の 1 回の読み出しで引く
  const offGenres = [...off].map(k => k.split('\t')).filter(([axis]) => axis === GENRE_AXIS);
  const genreOff = new Set(offGenres.length ? (await access.postingsFor(offGenres)).map(p => String(p[2])) : []);
  // One slot per production (collapse_tours), after answered stages are left out.
  // 評価の履歴が無く、お気に入りの公演にいたことで上がった人は、理由に登録した名前を書く（起案者の指示 2026-10-18
  // 「理由の文は、登録した名前を書く」）。理由に出る上位 4 人だけ
  // お気に入りの名前から引いた公演の題名と初日（理由の作品名に使う）。控えが古いときだけ読む（公演は MAX_SEED_STAGES まで、
  // rec_stage と catalogue を 1 回ずつ。D1 の読み取りは多くて 120 行）
  const favInfo = seeds.length ? await stageInfo(db, seeds.map(r => r.stage_id)) : new Map();
  // 同じ名前を別の種類でも登録していれば、人・原作者として書く
  const kindOf = new Map();
  for (const f of [...favourites].sort((a, b) => ['人', '原作者'].includes(b.kind) - ['人', '原作者'].includes(a.kind))) if (!kindOf.has(f.name)) kindOf.set(f.name, f.kind);
  const origins = favDetails(seeds, favOrigins(seeds, skip), favInfo, kindOf);
  const favWhy = c => {
    const via = new Map(c.via || []);
    const w = c.parts.slice(0, 4).filter(p => !p[3]).map(p => p[1] + '\t' + p[2]).filter(k => !via.has(k) && origins.has(k)).map(k => [k, ...origins.get(k)]);
    return w.length ? {fav: w} : {};
  };
  const byTour = new Map();
  for (const c of ranked) {
    if (done.has(c.stage_id) || hits.has(c.stage_id) || declined.has(c.stage_id) || genreOff.has(String(c.stage_id))) continue;
    const key = c.tour || 'stage:' + c.stage_id;
    if (!byTour.has(key)) byTour.set(key, {stage_id: c.stage_id, tour: c.tour || '', parts: c.parts, kinds: c.kinds, b: c.b, ...(c.via ? {via: c.via} : {}), ...favWhy(c), ...(c.imp ? {imp: c.imp} : {})});
  }
  // お気に入りの一覧に出る公演（hits）と同じ公演が別の番号で載っていても、おすすめには出さない（起案者の答え 2026-10-18「おすすめから外して」、
  // q-fav-same-production）。お気に入りの一覧で見られるため。読むのは rec_stage の主キーの行を多くて FAV_SAME_MAX 行（控えを作り直すときだけ）
  const groups = await sameProduction(db, ver, ablate.spread ? [...byTour.values()] : spreadLeads([...byTour.values()]), undefined,
    [...done, ...[...hits.keys()].slice(0, FAV_SAME_MAX)]);
  const kept = groups.slice(0, KEEP);
  // Every venue of the kept productions (the index groups a tour by rec_stage.tour).
  const venues = new Map();
  // 同じ公演としてまとめた別の束（sameProduction の aliases）の会場も、残した束の会場に入れる
  const primary = new Map();
  for (const g of kept) for (const t of [g.tour, ...(g.aliases || [])]) if (t && g.tour) primary.set(t, g.tour);
  const tours = [...primary.keys()];
  for (const part of chunks(tours, 90)) {
    const {results} = await db.prepare(`SELECT stage_id,tour,start,end,json_extract(entry,'$.pref') AS pref FROM rec_stage WHERE ver=? AND tour IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all();
    for (const r of results) {
      if (r.end && r.end < ctx.today) continue;
      const t = primary.get(r.tour) || r.tour;
      if (!venues.has(t)) venues.set(t, []);
      venues.get(t).push({stage_id: r.stage_id, pref: r.pref || '', start: r.start || ''});
    }
  }
  // 束の鍵の無い公演と、同じ公演としてまとめた束の鍵の無い公演（aliasStages）の会場
  const lone = [...new Set(kept.flatMap(g => [...(g.tour ? [] : [g.stage_id]), ...(g.aliasStages || [])]))];
  const prefOf = new Map();
  for (const part of chunks(lone, 90)) {
    const {results} = await db.prepare(`SELECT stage_id,start,json_extract(entry,'$.pref') AS pref FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all();
    for (const r of results) prefOf.set(r.stage_id, {stage_id: r.stage_id, pref: r.pref || '', start: r.start || ''});
  }
  for (const g of kept) {
    const vs = [...(g.tour ? (venues.get(g.tour) || []) : [prefOf.get(g.stage_id)]), ...(g.aliasStages || []).map(sid => prefOf.get(sid))]
      .filter((v, i, all) => v && all.findIndex(w => w && w.stage_id === v.stage_id) === i);
    g.venues = vs.length ? vs : [{stage_id: g.stage_id, pref: '', start: ''}];
    // Answered venues of the production stay out too (the answer is copied to the tour).
    g.venues = g.venues.filter(v => v.stage_id === g.stage_id || !done.has(v.stage_id));
  }
  const favWorks = seeds.map(r => ({...r, title: favInfo.get(String(r.stage_id))?.title || '', date: favInfo.get(String(r.stage_id))?.start || ''}));
  const titles = personTitles(rated, liked, favWorks);
  // 答えた公演の理由（理由を残す前に押した興味ありのため。lists.interestScreen が reaction.why の無い行に使う）。
  // 興味ありの公演は自分自身も種になっているので、作品名からは自分を除いて出す（lists.ownlessWhy）。
  const answeredWhy = ranked.filter(c => done.has(c.stage_id)).slice(0, 200).map(c => [c.stage_id, whyOf({...c, ...favWhy(c)}, titles)]);
  // 推薦が出ないときに本番で何が足りないかを見るための数（画面には出さない。/api/screen/recommend の JSON の diag）。
  const diag = {rated: wholeStages(rated).length, rated_linked: wholeStages(rated).filter(r => r.people.length).length,
    interest: nLiked, interest_with_people: liked.length, favourite_seeds: fav.seeds.length,
    ranked: ranked.length, after_answered: groups.length};
  // 控え（rec_cache）に残す理由は、画面が使う分だけにする: 人は上位 4 人（reasonRows・whyOf）、種類は使う種類の上位 3 つ
  // （reasonRows は 2 つ、地域の 1 行は人と合わせて 3 つ）。前は全員分を残していて、控えを書くときの JSON.stringify と
  // 読むたびの JSON.parse が重かった（#138）
  for (const g of kept) { g.parts = g.parts.slice(0, 4); g.kinds = g.kinds.filter(k => !droppedKind(k[1], k[2])).slice(0, 3); }
  // 理由に出す人・種類（各束の上位 4 人・2 種類）の鍵を先に集める。前は titles の全件 × 残した束（最大 400）を
  // 比べていて、本番の大きさの索引でこれだけで数十 ms かかっていた（#138、Workers Free の CPU は 10 ms）
  const shownKeys = new Set(kept.flatMap(g => [...g.parts.slice(0, 4), ...g.kinds.slice(0, 2)].map(p => p[1] + '\t' + p[2])));
  const body = {ready: true, gate: ablate.gate ? null : {key: gateKey, choice: gate}, ver, n_rated: wholeStages(rated).length, n_scored: groups.length, groups: kept, weights, w_counts: wCounts, diag, answered_why: answeredWhy,
    titles: [...titles].filter(([k]) => shownKeys.has(k))};
  if (!ctx.ablate) await db.prepare('INSERT INTO rec_cache(user_id,stamp,body,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET stamp=excluded.stamp,body=excluded.body,created_at=excluded.created_at')
    .bind(ctx.uid, stamp, JSON.stringify(body), Math.floor(ctx.now / 1000)).run();
  return {...body, titles: new Map(body.titles), cached: false};
}

/**
 * 同じ公演が 2 枚出ないよう、同じ題名（正規化した tkey）の束を 1 つにまとめる（起案者の指摘 2026-10-18
 * 「同じ公演が重複して2個あるときがある」「ラブ演劇博が2回出る」）。束の鍵（rec_stage.tour）は題名・団体・作り手の
 * 全部から作るので、会場ごとに出演の行が少し違う、団体名の書き方が違う・片方に無い、などで同じ公演が別の束になる。
 * 題名が同じだけでは、同じ時期に別の団体が同じ題名を上演する場合（『ハムレット』など）まで 1 つにしてしまうので、
 * 次のどれかが合うときだけ同じ公演とみなす: 団体が同じか片方に無い・会場が同じ・作り手に同じ人がいる。
 * 先に来た（点の高い）束を残し、後の束の鍵は aliases に入れて会場を合わせる。読むのは残す分（KEEP）の少し先までの主キーの行だけ。
 */
const NO_NAMES = new Set();
const FAV_SAME_MAX = 120;   // お気に入りの一覧の公演のうち、同じ公演を照らす数（D1 の読み取りの上限）
const looseVenue = v => String(v || '').normalize('NFKC').replace(/[\s　]+/gu, '');
export function sameStage(a, b) {
  if (a.g === b.g || !a.g || !b.g) return true;
  if (a.th && a.th === b.th) return true;
  for (const n of a.names) if (b.names.has(n)) return true;
  return false;
}
export async function sameProduction(db, ver, groups, limit = Math.ceil(KEEP * 1.5), answered = []) {
  const head = groups.slice(0, limit);
  const info = new Map();
  const want = [...new Set([...head.map(g => String(g.stage_id)), ...answered.map(String)])];
  // まず題名・団体・会場だけを読む。作り手の一覧（credits）は大きく、全部を読んで解くと Worker の CPU の上限
  // （無料枠は 1 回 10 ミリ秒）を越えて画面が読み込めなくなった（起案者の報告 2026-10-18「読み込めませんでした
  // SyntaxError: Unexpected token '<'」）。作り手は、題名が同じで団体も会場も決め手にならない組だけ、あとで読む
  for (const part of chunks(want, 90)) {
    let results = [];
    try {
      ({results} = await db.prepare(`SELECT stage_id,tkey,gkey,json_extract(entry,'$.theater') AS th FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all());
    } catch { return groups; }
    for (const r of results) if (r.tkey) info.set(String(r.stage_id), {t: r.tkey, g: r.gkey || '', th: r.th || '', names: NO_NAMES});
  }
  const perTitle = new Map();
  for (const [sid, me] of info) { if (!perTitle.has(me.t)) perTitle.set(me.t, []); perTitle.get(me.t).push([sid, me]); }
  const needNames = [];
  for (const list of perTitle.values()) {
    if (list.length < 2) continue;
    for (const [, me] of list) me.th = looseVenue(me.th);   // 会場名の表記ゆれ寄せは、同じ題名が 2 つ以上ある組だけ（重い）
    for (const [sid, me] of list) if (me.g && list.some(([o, x]) => o !== sid && x.g && x.g !== me.g && !(me.th && me.th === x.th))) needNames.push(sid);
  }
  for (const part of chunks(needNames, 90)) {
    let results = [];
    try {
      ({results} = await db.prepare(`SELECT stage_id,credits FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all());
    } catch { break; }
    for (const r of results) {
      let cr = [];
      try { cr = JSON.parse(r.credits || '[]'); } catch { /* no credits */ }
      info.get(String(r.stage_id)).names = new Set(cr.filter(c => Array.isArray(c) && !String(c[0]).startsWith('#')).map(c => String(c[1])).filter(Boolean));
    }
  }
  const byTitle = new Map(), out = [];
  // 答えた公演（興味あり・興味なし・購入済・行けない）と同じ公演は出さない（起案者の指摘 2026-10-18「1個だけ興味ありにしたら、
  // もう片方がおすすめに出てきた」── 同じ公演が別の番号で 2 つ載っていると、答えた番号だけが外れていた）
  for (const sid of answered) {
    const me = info.get(String(sid));
    if (!me) continue;
    const kept = byTitle.get(me.t) || [];
    kept.push({g: null, me}); byTitle.set(me.t, kept);
  }
  for (const g of head) {
    const me = info.get(String(g.stage_id));
    if (!me) { out.push(g); continue; }
    const kept = byTitle.get(me.t) || [];
    const keep = kept.find(k => sameStage(me, k.me));
    if (keep && !keep.g) continue;      // 答えた公演と同じ公演
    if (keep) {
      if (g.tour && g.tour !== keep.g.tour) keep.g.aliases = [...new Set([...(keep.g.aliases || []), g.tour])];
      if (!g.tour) keep.g.aliasStages = [...new Set([...(keep.g.aliasStages || []), String(g.stage_id)])];
      continue;
    }
    kept.push({g, me}); byTitle.set(me.t, kept);
    out.push(g);
  }
  return [...out, ...groups.slice(limit)];
}

/**
 * 同じ人が理由の公演が並びすぎないよう並べ直す（起案者の指示 2026-10-15、lit-topic-diversification・
 * lit-popularity-bias）。表示の 1 ページ（TOP 件）ごとに、いちばん強い理由の人が同じ公演は LEAD_CAP 件まで。
 * 越えた分は次のページ以降へ回す（消さない）。理由の人がいない公演（種類だけ）は数えない。
 */
export const LEAD_CAP = 2;
export function spreadLeads(groups, top = TOP, cap = LEAD_CAP) {
  const lead = g => (g.parts[0] ? g.parts[0][1] + '\t' + g.parts[0][2] : '');
  const rest = [...groups], out = [];
  let count = new Map();
  while (rest.length) {
    if (out.length % top === 0) count = new Map();
    let i = rest.findIndex(g => !lead(g) || (count.get(lead(g)) || 0) < cap);
    if (i < 0) i = 0;                                   // every one left is capped: keep the order
    const [g] = rest.splice(i, 1);
    if (lead(g)) count.set(lead(g), (count.get(lead(g)) || 0) + 1);
    out.push(g);
  }
  return out;
}

/** render_recommend.filtered: the shown venue of each production, and how many matched. */
export function filtered(groups, prefs, top = TOP) {
  if (!prefs.length) return {rows: groups.slice(0, top).map(g => ({...g, shown: g.stage_id})), hit: groups.length};
  const keep = new Set(prefs);
  const out = [];
  for (const g of groups) {
    const hit = g.venues.filter(v => keep.has(v.pref));
    if (!hit.length) continue;
    const v = hit.reduce((a, b) => ((b.start || '9999') < (a.start || '9999') ? b : a));
    out.push({...g, shown: v.stage_id});
  }
  return {rows: out.slice(0, top), hit: out.length};
}

export function prefCounts(groups) {
  const n = {};
  for (const g of groups) for (const p of new Set(g.venues.map(v => v.pref).filter(Boolean))) n[p] = (n[p] || 0) + 1;
  return n;
}

/** The cards of these rows, rank from `first`; rows without a card yet are left out. */
export async function cardsHtml(ctx, rows, titles, first = 1) {
  const {html, posters} = await cardTemplates(ctx.db, rows.flatMap(r => [r.shown, r.stage_id]));
  // 日程（会場ごとの行と公演日時の暦、会場で違う料金）は、会場ごとの公演の情報から組み直す（schedule.js）
  const info = await stageInfo(ctx.db, rows.flatMap(r => [r.shown, ...(r.venues || []).map(v => v.stage_id)]));
  const out = [];
  let rank = first;
  for (const r of rows) {
    const card = html.get(r.shown);
    if (!card) continue;
    const pic = posters.get(r.shown) || posters.get(r.stage_id);
    const sids = [...new Set([r.shown, ...(r.venues || []).map(v => v.stage_id)].map(String))];
    const tour = tourBlock(sids.map(s => info.get(s)).filter(Boolean), r.shown, ctx.today, ctx.prefs || []);
    // 理由の作品名からこの公演そのものは除く（お気に入りの名前から引いた公演に、この公演が入っていることがある）
    const own = info.get(String(r.shown))?.title || '';
    const mine = own ? new Map([...(r.parts || []), ...(r.kinds || [])].map(p => p[1] + '\t' + p[2]).filter(k => titles.has(k))
      .map(k => [k, titles.get(k).filter(t => t !== own)])) : titles;
    out.push(withTour(compose(card, r.shown, 'recommend', {rank: rank++, why: reasonRows(r, mine, own), poster: pic ? posterHtml(pic) : ''}), tour));
  }
  return out;
}

/** The card with its tour block replaced (or put after the run line when the card had none). */
export function withTour(card, {html, perVenuePrice}) {
  if (!html) return card;
  const old = /<div class="tourfull">(?:<div class="tf-row[^"]*">[\s\S]*?<\/div>)*<\/div>/;
  let out = old.test(card) ? card.replace(old, () => html) : card.replace(/(<div class="when">[\s\S]*?<\/div>)/, (m) => m + html);
  // 会場ごとに料金を書いたカードは、販売の札の横の料金（おすすめに出ている会場の分）を重ねない
  if (perVenuePrice) out = out.replace(/<article class="ticket (\w+)"/, (m) => m + ' data-tourprice="1"');
  return out;
}

/**
 * GET /api/recommend（#119）: 今週のおすすめの画面と同じ計算・同じ控え（rankedGroups）を、データとして返す。
 * 前は旧い移行用の表（records・reactions）から別の計算（person-ordinal-v3+fav3+asp1+tour1+why1）をしていて、
 * 画面で付けた評価・興味ありが届かず、同じ rec_cache の行を画面と取り合って毎回計算し直させていた。
 * 都道府県では絞らない（全国の上位 TOP 件）。表示に使う列は rec_stage から、出す分（最大 TOP 件の会場）だけ読む。
 */
export async function recommendApi(ctx, top = TOP) {
  const data = await rankedGroups(ctx);
  if (!data.ready) return {ready: false, items: []};
  const {rows} = filtered(data.groups, [], top);
  const ids = [...new Set(rows.flatMap(g => [g.stage_id, ...(g.venues || []).map(v => v.stage_id)]).map(String))];
  const entries = new Map();
  for (const part of chunks(ids, 90)) {
    const {results} = await ctx.db.prepare(`SELECT stage_id,title,grp,start,end,entry FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(data.ver, ...part).all();
    for (const r of results) entries.set(String(r.stage_id), r);
  }
  const venue = id => {
    const e = entries.get(String(id)) || {};
    let entry = {};
    try { entry = JSON.parse(e.entry || '{}') || {}; } catch { /* no entry */ }
    return {stage_id: String(id), start: e.start || '', end: e.end || '', theater: entry.theater || '', pref: entry.pref || '', url: entry.url || ''};
  };
  const diag = data.diag || {};
  return {ready: true, recommender: `${VERSION}|${data.ver}`, cached: Boolean(data.cached), n_rated: diag.rated || 0, n_linked: diag.rated_linked || 0,
    n_seeds: (diag.favourite_seeds || 0) + (diag.interest_with_people || 0), n_scored: data.n_scored || 0,
    items: rows.map(g => {
      const e = entries.get(String(g.stage_id)) || {};
      // 理由は画面と同じ（reasonRows）: 人を先に、空きを種類で埋めて 3 つまで。使わなくなった種類は出さない
      const reasons = [...g.parts.slice(0, 3), ...g.kinds.filter(k => !droppedKind(k[1], k[2]))].slice(0, 3);
      return {...venue(g.stage_id), title: e.title || '', group: e.grp || '', score: g.b,
        reasons: reasons.map(([, role, person, n]) => ({role, person, n})),
        tours: (g.venues || []).filter(v => String(v.stage_id) !== String(g.stage_id)).map(v => venue(v.stage_id))};
    })};
}

/** app.unrated_ends: the dates unrated works ended (no titles), for the nudge in app.js. */
async function unratedEnds(ctx) {
  return (await loadWorks(ctx)).filter(w => !w.verdict && !w.unseen && w.last_date && w.last_date <= ctx.today)
    .map(w => w.last_date).sort();
}

export async function recommendScreen(params, ctx) {
  const prefs = await prefsFor(params, ctx);
  ctx.prefs = prefs;   // ツアーの日程で、絞り込んだ県の会場に ★（schedule.tourBlock）
  const data = await rankedGroups(ctx);
  const nCand = Number((await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='catalogue_upcoming'").first())?.v || 0);
  const {rows, hit} = filtered(data.groups, prefs);
  const cards = await cardsHtml(ctx, rows, data.titles);
  // その日に出した公演（測るための記録 rec_shown。新しく出した公演があるときだけ書く）
  if (data.ready) await recordShown(ctx, 'recommend', rows.map(r => r.shown), `${VERSION}|${data.ver || ''}`);
  const where = prefs.length <= 3 ? prefs.join('・') : `${prefs[0]}ほか ${prefs.length - 1} 県`;
  // 見出しは「あなたへのおすすめ」（起案者の指示 2026-10-18「『今週のおすすめ15件』→『今週のあなたへのおすすめ15件』」。
  // 0 件・答え終えた・県で絞ったときも同じ言い方に合わせる）
  let head, lede;
  // 候補はあったが、すべて答え終えた（新しく使い始めた人の「まだ候補が無い」とは分ける）
  const allAnswered = !cards.length && !data.groups.length && (data.diag?.ranked || 0) > 0;
  if (!prefs.length && allAnswered) {
    head = '今週のあなたへのおすすめにはすべて答えました';
    lede = '';
  } else if (!prefs.length && !cards.length) {
    head = '今週のあなたへのおすすめはありません';
    // お気に入りを登録しているのに 0 件のときだけ、一文添える（起案者の答え 2026-10-18「C」。q-fav-reco-running-shows）。
    // 関わりのある人のほかの公演が、本人の公演だけ・終わった・もう始まっている、のどれかだと候補が無い
    const declared = await loadDeclared(ctx);
    lede = KINDS.some(kind => (declared[kind] || []).length)
      ? '<p class="rcount favnone">お気に入りに登録した名前と関わりのある人の、これから観られる公演はまだ見つかっていません。'
        + '登録した名前の公演は「<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>」に出ます。新しい公演は毎日取り込んでいます。</p>'
      : '';
  } else if (!prefs.length) {
    head = `今週のあなたへのおすすめ ${cards.length} 件`;
    // 件数は 1 行で（起案者の指示 2026-10-17「『埼玉県ほか 3 県／◯件中上位◯件を表示中』に変えて」。全国も同じ形）
    lede = `<p class="rcount"><b>全国</b>／${data.n_scored} 件中 上位 ${cards.length} 件を表示中</p>`;
  } else if (!cards.length) {
    head = `${where}でのあなたへのおすすめはありません`;
    lede = `<p class="rcount">これから観られる公演 ${nCand} 件のうち、<b>${E(where)}</b>で観られるものはありませんでした。ほかの都道府県を選ぶか、全国に戻してください。</p>`;
  } else {
    head = `${where}でのあなたへのおすすめ ${cards.length} 件`;
    lede = `<p class="rcount"><b>${E(where)}</b>／${hit} 件中 上位 ${cards.length} 件を表示中</p>`;
  }
  // 推薦を出すためのワンポイント（起案者の指示 2026-10-14「なにがしたら出るか、使うユーザーが
  // わかりやすい文章で（技術的なことは書かないで）おすすめの初期画面に追加して」）。
  // 条件は new-user-reco-threshold: 公演とつながった記録が 2 件以上で、評価が 2 種類以上。
  // 一覧の途中で答え終えたときは、画面（app.js）がこの控えを最後のカードの下に出す
  const tips = prefs.length ? '' : allAnswered ? THANKS : !cards.length ? TIPS : `<template id="rec-thanks-t">${THANKS}</template>`;
  // 使い始めでおすすめがまだ無いときは、選び方・絞り込み・興味ありへの案内を出さない（起案者の指示 2026-10-18
  // 「使い始めの人で、おすすめがないときは選び方や絞り込みは表示させないで。一件以上ある時のみ表示」）。
  // 県で絞って 0 件になったとき、使わない言葉・効かせ方・出さない種類を変えて 0 件になったときは、戻せるよう出したまま
  const [declined, kindOff] = await Promise.all([loadDeclined(ctx), loadKindOff(ctx)]);
  const tuned = declined.length > 0 || kindOff.length > 0 || tunedWeights(data.weights || {});   // 初めの設定（群ごとの既定、weights.GROUP_DEFAULT）と比べる
  const starting = !prefs.length && !allAnswered && !cards.length && !tuned;
  const nInterest = (await ctx.db.prepare('SELECT count(DISTINCT stage_id) AS n FROM reaction WHERE user_id=? AND interest=1 AND COALESCE(owned,0)=0').bind(ctx.uid).first())?.n || 0;
  const nSyn = cards.filter(h => /<div class="syn( doubt)?"/.test(h)).length;
  const limits = cards.length ? `<p class="note toinfo"><b>この ${cards.length} 件で、出せていない情報です。</b><br>
・<b>チケットの販売期限と、販売終了・完売</b>：手元に情報がないので表示できません。
チケットが残っているかどうかは公式サイトで確認してください<br>
・<b>あらすじ</b>：${nSyn}/${cards.length} 件で表示できました。残りは、まだ読み取りが済んでいないか、公演のページに載っていませんでした<br>
・<b>まだ答えていない公演は、次回も候補に残ります。</b>
評価・公演情報・設定が変わると、順位も変わることがあります</p>` : '';
  // 件数の 1 行は枠に入れず地の文で、「表示の絞り込み」の下に少し空けて置く（起案者の指示 2026-10-18）
  const body = `<h1>${E(head)}</h1>
${lede.includes('favnone') ? lede : ''}${tips}${starting ? '' : `<details class="rec-controls">
<summary><b>地域・調整</b><span>${E(where || '全国')}${tuned ? '／選び方を調整中' : ''}</span><span class="rec-budget"></span></summary>
<p class="fgh">${ico('light', 15)}<b>おすすめの選び方</b><span>おすすめに表示される結果自体が変わります。</span></p>
<div class="fil2 tune">${weightForm(data.weights || {}, data.w_counts || {})}${declinedBox(declined)}${kindOffBox(kindOff)}</div>
<p class="fgh">${ico('search', 15)}<b>表示の絞り込み</b><span>おすすめの候補の中から、表示する項目を設定できます。</span></p>
<div class="fil2 narrow">${prefForm(prefCounts(data.groups), prefs, '/recommend', PAGE_PREF_NOTE, {}, regionCounts(data.groups.map(g => ({key: g.stage_id, prefs: g.venues.map(v => v.pref)}))))}</div>
</details>
`}${lede.includes('favnone') ? '' : lede}
${cards.length ? '<p class="rec-answer-help">「興味なし」は今後のおすすめに反映します。右上の×は候補を非表示にするだけで、好みには反映しません。</p>' : ''}
${cards.join('')}
${starting ? '' : `<p class="lede">気になった公演で「興味あり」を押すと、
<a href="/recommend/interest?t=__TAGURI_TOKEN__">「興味あり」（いま ${nInterest} 件）</a>に移ります。</p>
`}${limits}`;
  return {title: '今週のあなたへのおすすめ', body_html: body, unrated_ends: await unratedEnds(ctx), diag: data.diag || null};
}

// ---------------------------------------------------------------- react (serve.on_react)
// cantgo（行けない）は interest=2: 答えた公演としておすすめから外し、興味ありの一覧には出さず、好みの手がかりには使う
// 押し間違いをその場で直せるように（起案者の指示 2026-10-17）、購入済み以外を押したら購入済みの印を外す（owned=0）
// dismiss（カードの右上の ✕「候補から消す」）は interest=3: おすすめ・お気に入り・一覧から外すだけで、好みの手がかりにはしない。
// 興味ありの画面で押した ✕（dismiss_strong）は interest=4: 一覧から外し、強い負の手がかりにする（起案者の指示 2026-10-18
// 「これいらんなってときがある。その時候補から消したい。興味の画面でバツを押された場合は…結構マイナスと判断できる」）
const REACT = {owned: {owned: 1}, interest: {interest: 1, owned: 0}, nointerest: {interest: 0, owned: 0}, cantgo: {interest: 2, owned: 0},
  dismiss: {interest: 3, owned: 0}, dismiss_strong: {interest: 4, owned: 0}};
const FROM = {reminder: 'reminder', search: 'search', favourites: 'favourites'};

// 答えを 1 行書く文（実行はしない）。押した公演とほかの会場の分を 1 つの batch で書くため（#196）
function reactRow(ctx, stageId, cols, source) {
  const label = ctx.today;
  const v = {interest: null, owned: null, note: null, note_no: null, note_pre: null, why: null, rank: null, score: null, ver: null, arm: null, ...cols};
  return ctx.db.prepare(`INSERT INTO reaction(user_id,label,stage_id,interest,owned,note,note_no,note_pre,why,source,updated_at,rank,score,ver,arm) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(user_id,label,stage_id) DO UPDATE SET interest=COALESCE(excluded.interest,reaction.interest), owned=COALESCE(excluded.owned,reaction.owned),
    note=COALESCE(excluded.note,reaction.note), note_no=COALESCE(excluded.note_no,reaction.note_no), note_pre=COALESCE(excluded.note_pre,reaction.note_pre),
    why=COALESCE(excluded.why,reaction.why),
    rank=CASE WHEN excluded.ver IS NOT NULL THEN excluded.rank ELSE reaction.rank END, score=CASE WHEN excluded.ver IS NOT NULL THEN excluded.score ELSE reaction.score END,
    ver=COALESCE(excluded.ver,reaction.ver), arm=COALESCE(excluded.arm,reaction.arm),
    source=CASE WHEN excluded.interest IS NOT NULL OR excluded.owned IS NOT NULL THEN excluded.source ELSE reaction.source END, updated_at=excluded.updated_at`)
    .bind(ctx.uid, label, stageId, v.interest, v.owned, v.note, v.note_no, v.note_pre, v.why, source, new Date(ctx.now).toISOString(), v.rank, v.score, v.ver, v.arm);
}

/** The reasons of one ranked production, small enough to keep (the 4 people and 2 kinds reasonRows shows, and their titles). */
export function whyOf(g, titles) {
  const parts = g.parts.slice(0, 4), kinds = g.kinds.slice(0, 2);
  const keys = [...parts, ...kinds].map(p => p[1] + '\t' + p[2]);
  return {parts, kinds, ...(g.via ? {via: g.via} : {}), ...(g.fav ? {fav: g.fav} : {}), ...(g.imp ? {imp: g.imp} : {}), titles: keys.filter(k => titles.has(k)).map(k => [k, titles.get(k)])};
}

/**
 * 興味ありを押したときに見えていた理由（reaction.why）。押す前のおすすめの控え（rec_cache）は、その画面を
 * 出したときのものなので、印を確かめずに読む（D1 の読み取り 1 行。ticker.js と同じ）。無ければ残さない。
 */
function whySnapshot(body, stageId) {
  if (!body) return null;
  const g = (body.groups || []).find(x => x.stage_id === stageId || (x.venues || []).some(v => v.stage_id === stageId));
  return g ? JSON.stringify(whyOf(g, new Map(body.titles || []))) : null;
}

/** serve.fill_slot: the next card in place of the one answered, honouring the saved prefectures. */
async function fillSlot(ctx, shown, pressed, page = null) {
  if (!shown.length) return {html: '', left: 0, said: ''};
  // そのページで絞った県（画面が URL から送る）。無ければ設定の県
  const prefs = await prefsFor(page ? new URLSearchParams([['f', '1'], ...page.map(p => ['pref', p])]) : new URLSearchParams(), ctx);
  ctx.prefs = prefs;
  const data = await rankedGroups(ctx);
  const {rows} = filtered(data.groups, prefs, 1e6);
  const seen = new Set([...shown.map(String), String(pressed)]);
  // 画面に出ている公演は、どの会場の番号で出ていても足さない（束の代表の会場は、答えるたびの並べ直しで変わる）
  const onScreen = r => [r.stage_id, r.shown, ...(r.venues || []).map(v => v.stage_id)].some(x => seen.has(String(x)));
  const rest = rows.filter(r => !onScreen(r));
  if (!rest.length) return {html: '', left: 0, said: '記録しました。入れ替える候補はもうありません。好みに合いそうだと判断できた分は出し切りました。'};
  const [card] = await cardsHtml(ctx, rest.slice(0, 1), data.titles, shown.length + 1);
  return {html: card || '', left: rest.length,
    said: `記録しました。入れ替わりに 1 件を下に足しました。まだ出していない候補が ${rest.length - 1} 件あります。`};
}

export async function reactAction(b, ctx) {
  const stageId = String(b.stage_id ?? ''), value = String(b.value ?? '');
  if (b.clear === true) {
    if (!/^[A-Za-z0-9_-]{1,40}$/.test(stageId) || value) throw new ValueError('解除する公演だけを指定してください');
    const ids = [...new Set([stageId, ...(Array.isArray(b.siblings) ? b.siblings.slice(0, 40).map(String)
      .filter(s => /^\d+$/.test(s)) : [])])];
    // 日ごとの古い回答も解除する。最新の行だけ消すと、前日の回答が再び有効になってしまう。
    // 本人のメモ・券・観劇記録は残す。再送しても結果の変わらない明示的な解除にする。
    await ctx.db.batch([...ids.map(sid => ctx.db.prepare(`UPDATE reaction SET interest=NULL,owned=NULL,why=NULL,
      rank=NULL,score=NULL,ver=NULL,arm=NULL,updated_at=? WHERE user_id=? AND stage_id=?
      AND (interest IS NOT NULL OR owned IS NOT NULL)`).bind(new Date(ctx.now).toISOString(), ctx.uid, sid)),
    ctx.db.prepare('DELETE FROM rec_cache WHERE user_id=?').bind(ctx.uid)]);
    return {body: {ok: true, saved: true, stage_id: stageId, value: '', cleared: true}};
  }
  if (b.fill_only) {
    if (!stageId) throw new ValueError('stage_id が要る');
    const shown = (Array.isArray(b.shown) ? b.shown : []).slice(0, 120).map(x => String(x).slice(0, 20));
    const page = Array.isArray(b.prefs) ? b.prefs.slice(0, 47).map(x => String(x).slice(0, 8)) : null;
    return {body: {ok: true, stage_id: stageId, fill: await fillSlot(ctx, shown, stageId, page)}};
  }
  const given = {};
  for (const k of ['note', 'note_no', 'note_pre']) if (b[k] !== undefined && b[k] !== null) given[k] = String(b[k]).slice(0, 2000);
  if (!stageId || !/^[A-Za-z0-9_-]{1,40}$/.test(stageId) || (!Object.hasOwn(REACT, value) && !Object.keys(given).length))
    throw new ValueError('stage_id と、value（owned / interest / nointerest / cantgo / dismiss / dismiss_strong）か理由が要る');
  // どの画面で答えたか（起案者の指示 2026-10-15: 開幕リマインドから足した興味ありは、おすすめ理由の欄ではなく
  // 「開幕リマインドからの追加」と出す）。画面（app.js）が from を送る。無ければこれまでどおり 'screen'。
  const source = Object.hasOwn(FROM, String(b.from ?? '')) ? FROM[String(b.from)] : 'screen';
  // おすすめの画面で押した興味ありは、そのとき見えていた理由も残す（興味ありの画面で出す。答えた公演は
  // おすすめの計算から外れるので、あとからは作れない）
  // 答えたときの順位・点・版（測るための記録。real-data-eval-plan §5）も、同じ控えの 1 回の読み出しから取る。
  // どの画面で答えても残す（開幕リマインドの答えにも、そのときの点が要る）。理由だけを書き足す行には付けない
  const snap = Object.hasOwn(REACT, value) ? await answerSnapshot(ctx, stageId, VERSION) : {body: null, eval: null};
  const ev = snap.eval || {};
  const why = value === 'interest' && source === 'screen' ? whySnapshot(snap.body, stageId) : null;
  const writes = [reactRow(ctx, stageId, {...(REACT[value] || {}), ...given, ...(why ? {why} : {}), ...ev}, source)];
  if (Object.hasOwn(REACT, value) && Array.isArray(b.siblings)) {
    // The same answer for the production's other venues (the card's data-tours); notes stay on the pressed one.
    for (const sid of b.siblings.slice(0, 40).map(String).filter(s => /^\d+$/.test(s) && s !== stageId))
      writes.push(reactRow(ctx, sid, {...REACT[value], ...(why ? {why} : {}), ...ev}, source + '_tour'));
  }
  // 押した公演とほかの会場の答えは 1 つの batch で書く（#196）。途中の会場で失敗すると、前は先に書いた分が
  // 残ったまま要求全体が失敗し、画面からは保存できたか分からなかった。いまは全部書けるか、どれも書かないか
  await ctx.db.batch(writes);
  const out = {ok: true, saved: true, stage_id: stageId, value, note: 'note' in given, note_no: 'note_no' in given};
  if (Object.hasOwn(REACT, value) && !b.nofill) {
    // 入れ替わりの 1 枚は保存のあとの別の処理。作れなくても答えは保存できているので、失敗にはしない。
    // fill: null と fill_status: 'retry_available' を返し、画面は fill_only で取り直せる（app.js は fill が無ければ足さない）
    const shown = (Array.isArray(b.shown) ? b.shown : []).slice(0, 120).map(x => String(x).slice(0, 20));
    try { out.fill = await fillSlot(ctx, shown, stageId); }
    catch (e) { console.log('react fill failed after save:', String(e && e.message || e)); out.fill = null; out.fill_status = 'retry_available'; }
  }
  return {body: out};
}

// serve._exposure_event with no exposure store (the public service keeps no telemetry:
// it would spend D1 writes on every card shown). web/recommendation-exposure.js reads
// ok:false as "not recording" and stops posting for that card.
const exposureOff = async () => ({body: {ok: false, disabled: true}});
// serve.on_hand_theme on the public service: stage material is shared, so not editable here.
const handThemeAction = async () => { throw new ValueError('公開版では公演情報の編集はできません'); };

export const recommendScreens = {
  screens: {recommend: recommendScreen},
  actions: {react: reactAction, weight: weightAction, 'recommendation/visit': exposureOff, 'recommendation/contact': exposureOff, hand_theme: handThemeAction},
};
