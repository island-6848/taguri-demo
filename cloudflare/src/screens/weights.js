// おすすめの効かせ方（起案者の指示 2026-08-24、Worker へ 2026-10-14「おすすめの画面を移して」）:
// app.WEIGHT_STEPS / ROLE_GROUPS / read_weights / save_weights / weight_form. The
// form is checked against Python (test/weights.test.js); web/app.js already drives the
// sliders (.wsl) and posts {weights} to /api/weight on 確定.
import {E, ValueError, localNow} from './py.js';
import {ico} from './icons.js';

export const WEIGHT_STEPS = [['off', '効かせない', 0.0], ['weak', 'あまり効かせない', 0.5], ['mid', 'ふつう', 1.0],
  ['strong', '少し強く', 2.0], ['max', 'とても強く', 4.0]];
export const STEP_MUL = Object.fromEntries(WEIGHT_STEPS.map(([k, , m]) => [k, m]));
export const DEFAULT_STEP = 'mid';
export const ROLE_GROUPS = [['cast', '出演者'], ['author', '演出・脚本・翻訳'], ['craft', 'つくり（美術・照明・音響・映像・衣裳・振付など）'],
  ['stage', '進行（舞台監督・技術監督・演出助手など）'], ['produce', '制作・宣伝（製作・プロデューサー・宣伝・票券など）'],
  ['other', 'その他の役職（上のどれにも入らないもの）'], ['theme', '作品の内容（あらすじの題材）']];
const GROUP_LABEL = Object.fromEntries(ROLE_GROUPS);
const GROUP_SHORT = {cast: '出演者', author: '演出・脚本・翻訳', craft: 'つくり', stage: '進行', produce: '制作・宣伝', other: 'その他の役職', theme: '作品の内容'};

/** app.read_weights: every group's step, "mid" unless saved. */
export async function readWeights(ctx) {
  const {results} = await ctx.db.prepare('SELECT grp, step FROM rank_weight WHERE user_id=?').bind(ctx.uid).all();
  const rows = Object.fromEntries(results.map(r => [r.grp, r.step]));
  return Object.fromEntries(ROLE_GROUPS.map(([k]) => [k, Object.hasOwn(STEP_MUL, rows[k]) ? rows[k] : DEFAULT_STEP]));
}

/** The multipliers the ranking uses (only the groups not at "ふつう"). */
export const multipliersOf = w => Object.fromEntries(Object.entries(w).filter(([, v]) => v !== DEFAULT_STEP).map(([k, v]) => [k, STEP_MUL[v]]));

/** serve.on_weight + app.save_weights / save_weight: checked as a whole, then written in one batch. */
export async function weightAction(b, ctx) {
  const ws = b && b.weights;
  let rows;
  if (ws && typeof ws === 'object' && !Array.isArray(ws)) {
    const entries = Object.entries(ws);
    if (!entries.length || entries.length > 32) throw new ValueError('weights の件数が範囲外');
    rows = entries.map(([k, v]) => {
      k = String(k); v = String(v);
      if (!Object.hasOwn(GROUP_LABEL, k)) throw new ValueError(`その項目は無い: ${k}`);
      if (!Object.hasOwn(STEP_MUL, v)) throw new ValueError(`その段階は無い: ${v}`);
      return [k, v];
    });
  } else {
    const k = String(b?.group ?? ''), v = String(b?.step ?? '');
    if (!Object.hasOwn(GROUP_LABEL, k)) throw new ValueError('その項目は無い');
    if (!Object.hasOwn(STEP_MUL, v)) throw new ValueError('その段階は無い');
    rows = [[k, v]];
  }
  const at = localNow(ctx.now);
  // The saved ranking is dropped too (serve.invalidate_user_cache): its stamp has the
  // time to the second only, so two saves within a second would keep the old one.
  await ctx.db.batch([...rows.map(([k, v]) => ctx.db.prepare('INSERT INTO rank_weight(user_id,grp,step,updated_at) VALUES(?,?,?,?)'
    + ' ON CONFLICT(user_id,grp) DO UPDATE SET step=excluded.step, updated_at=excluded.updated_at').bind(ctx.uid, k, v, at)),
  ctx.db.prepare('DELETE FROM rec_cache WHERE user_id=?').bind(ctx.uid)]);
  if (rows.length === 1 && !(ws && typeof ws === 'object')) {
    const [k, v] = rows[0];
    return {body: {ok: true, grp: k, label: GROUP_LABEL[k], step: v}};
  }
  return {body: {ok: true, weights: Object.fromEntries(rows)}};
}

/** app.weight_form(user_id, d) with d.weights, d.w_counts, d.w_dropped. */
export function weightForm(w, cnt = {}, drop = 0) {
  const keys = WEIGHT_STEPS.map(s => s[0]);
  const labels = Object.fromEntries(WEIGHT_STEPS.map(([k, l]) => [k, l]));
  const changed = ROLE_GROUPS.map(([k]) => [k, w[k] || DEFAULT_STEP]).filter(([, v]) => v !== DEFAULT_STEP)
    .map(([k, v]) => `${GROUP_SHORT[k]}を${labels[v]}`);
  const now = !changed.length ? 'すべて「ふつう」（これまでと同じ効き方）' : changed.join('／');
  const rows = ROLE_GROUPS.map(([k, label]) => {
    const cur = w[k] || DEFAULT_STEP, i = keys.indexOf(cur), n = cnt[k] || 0;
    return `<div class="wrow${cur === 'off' ? ' off' : ''}" data-grp="${k}">`
      + `<span class="wl">${E(label)}</span>`
      + `<span class="wn">おすすめの候補 ${n} 件で一致</span>`
      + `<input class="wsl" type="range" min="0" max="${keys.length - 1}" step="1"`
      + ` value="${i}" data-weight="${k}"`
      + ` aria-label="${E(label)}の効かせ方">`
      + `<span class="wv">${E(labels[cur])}</span></div>`;
  }).join('');
  const dropped = !drop ? '' : `<p class="lead">いまの設定で、おすすめに出なくなった公演が ${drop} 件あります。`
    + '「すべて「ふつう」に戻す」を押すと戻ります。</p>';
  const scale = '<div class="wscale"><span>← ' + E(labels.off) + '</span>'
    + `<span class="wmid">${E(labels[DEFAULT_STEP])}（既定）</span>`
    + '<span>' + E(labels.max) + ' →</span></div>';
  return `<div class="wfil">
<details class="pbox wbox" id="weights">
<summary>${ico('light', 15)}おすすめの効かせ方を変える ── いまは<b>${E(now)}</b></summary>
<p class="lead">おすすめの順位に、どの情報をどれくらい効かせるかを決められます。
つまみを動かして「この効かせ方でおすすめを読み込む」を押すと、一覧を作り直します。
押すまでは変わりません。既定は「ふつう」です。
いちばん左の「効かせない」にすると、その情報は順位からも理由からも消えます。
件数は、おすすめの候補のうち、その情報が一致している公演の数です。
件数が少ない項目は、動かしても一覧はあまり変わりません。</p>
${scale}
${rows}
<div class="pfoot"><button data-wsave="1">${ico('light')}この効かせ方でおすすめを読み込む</button>
 <button class="pall-btn" data-wreset="1">すべて「ふつう」に戻す</button>
 <span class="wsaid"></span></div>
${dropped}
<p class="lead">お気に入りに登録した名前の公演は、この設定に関係なく出ます。</p>
</details></div>`;
}
