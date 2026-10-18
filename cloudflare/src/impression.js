// 感想で明示された特徴への好みを、本人の推薦に効かせる（issue #104、起案者の指示 2026-10-18「感想で書いた内容を
// 推薦に反映させるところまで」）。tools/review/impression_preferences.py の移植で、同じ入力に同じ結果を返す
// （test/impression.test.js が Python と突き合わせる）。規則だけで動き、感想を外部に送らない（LLM を呼ばない）。
//
// 特徴は、観た公演に付いている種類の言葉（rec_people の '#題材' などの行）に限る。作品全体の ◎○△× から
// 全部の特徴への好き嫌いを推し量らない。プロフィールは今の記録から毎回作り直すので、編集・削除がすぐ効く。

export const PRIOR = 3, WEIGHT = 0.75, TOP_N = 3;

// 同じ特徴に限って表記を揃える。「恋愛」と「恋愛が多い」などは統合しない
export const ALIASES = [
  ['コメディ', '喜劇', 'コメディー'],
  ['恋愛', 'ラブストーリー'],
  ['会話の掛け合い', '会話劇', '会話中心', '会話の応酬'],
  ['身体表現', 'フィジカルシアター'],
  ['観客参加', '観客参加型'],
  ['解釈を観客に委ねる結末', '解釈を観客に委ねる', '開かれた結末'],
];

const normOf = text => String(text || '').normalize('NFKC').replace(/\s+/gu, '').toLowerCase();
// 候補の公演の言葉は同じものが何度も出るので、正規化した結果を覚えておく（Worker の CPU、#104）。上限で捨てる
const NORMED = new Map();
export const norm = text => {
  const key = String(text || '');
  let w = NORMED.get(key);
  if (w === undefined) { if (NORMED.size >= 20000) NORMED.clear(); w = normOf(key); NORMED.set(key, w); }
  return w;
};
// 同義語の表は 1 度だけ作る: 正規化した表記 → 代表の表記、代表の表記 → 正規化した全表記
const CANONICAL = new Map(), FORMS = new Map();
for (const aliases of ALIASES) {
  const head = normOf(aliases[0]), forms = aliases.map(normOf);
  for (const f of forms) if (!CANONICAL.has(f)) CANONICAL.set(f, head);
  if (!FORMS.has(head)) FORMS.set(head, forms);
}

export function canonical(word) {
  const w = norm(word);
  return CANONICAL.has(w) ? CANONICAL.get(w) : w;
}

/** 正規化した特徴 → 公演に付いた表示名（最初のもの）。2 字未満は使わない */
export function features(elements) {
  const out = new Map();
  for (const e of elements || []) {
    const word = (e && typeof e === 'object') ? (e.word ?? '') : e;
    if (typeof word === 'string' && [...norm(word)].length >= 2) {
      const k = canonical(word);
      if (!out.has(k)) out.set(k, word);
    }
  }
  return out;
}

// 否定された肯定語を先に取ることで、「面白くない」の「面白」を加点しない
const EVALUATION = new RegExp(
  '(?<negative>好き(?:では|じゃ|で)?な(?:い|かった)|'
  + '好み(?:では|じゃ)な(?:い|かった)|'
  + '面白くな(?:い|かった)|楽しくな(?:い|かった)|楽しめな(?:い|かった)|'
  + 'よくな(?:い|かった)|良くな(?:い|かった)|'
  + '苦手(?:だった|です)?|嫌い(?:だった|です)?|つまらな(?:い|かった)|'
  + '退屈(?:だった|です)?|合わな(?:い|かった)|多すぎ(?:る|た)|'
  + '物足りな(?:い|かった))'
  + '|(?<weak>悪くな(?:い|かった))'
  + '|(?<positive>好き(?:だった|です)?|好み(?:だった|です)?|'
  + '面白(?:い|かった)|楽し(?:い|かった|めた)|よかった|良かった|'
  + '最高(?:だった|です)?|魅力的|心地よ(?:い|かった)|刺さ(?:る|った))', 'gu');
const HAS_EVALUATION = new RegExp(EVALUATION.source, 'u');
const SPLIT = /[。！？!?\n、,;；]|けれど(?:も)?|けど|しかし|でも|一方(?:で)?|だが|ですが/u;
const UNCERTAIN = /かもしれ|とは(?:言え|いえ|限ら)|わけ(?:では|じゃ)|ではなく|じゃなく|とは思わ/u;
const REPORTED = /[」』](?:と|って)(?:言|話|語|叫)|(?:という|と言う)(?:台詞|セリフ)/u;
// 他の対象の評価が途中に入っていたら結び付けない（「家族の話で演技がよかった」等）
const BRIDGE = new RegExp('^(?:は|が|を|も|に|の|って|という|として|ところ|'
  + '描写|描き方|描かれ方|物語|話|テーマ|題材|表現|関係|要素|部分|'
  + 'とても|すごく|凄く|本当に|とにかく|かなり|特に|非常に|'
  + '多くて|多く|中心で|中心の|あって|ある|描かれていて)*$', 'u');
const NOT_AFTER = /^(?:では|じゃ|で)な(?:い|かった)/u;

// Python の re.split と同じく、区切りのたびに切る（JS の split は捕まえない区切りでも同じ）
const splitClauses = note => String(note || '').split(new RegExp(SPLIT.source, 'gu'));
// 字数は Python と合わせて「文字（コードポイント）」で数える
const cp = s => [...s].length;

/** 同じ節で、特徴に続く明確な評価だけを結び付ける。曖昧な文は保留する */
export function extract(note, elements) {
  const vocabulary = features(elements);
  const signals = [];
  if (!vocabulary.size) return signals;
  // 特徴ごとに探す表記（同義語と、公演に付いた表示名）は、節ごとでなく感想ごとに 1 度だけ作る
  const lookFor = [...vocabulary].map(([key, label]) => [key, [...new Set([...(FORMS.get(key) || [normOf(label)]), normOf(label)])]]);
  for (const raw of splitClauses(note)) {
    const clause = normOf(raw);
    // 評価の言葉が無い節からは何も取れない（ほとんどの節はここで終わる）
    if (!clause || !HAS_EVALUATION.test(clause) || REPORTED.test(clause)) continue;
    const mentions = [];
    for (const [key, forms] of lookFor) {
      for (const alias of forms) {
        if (!alias) continue;
        // re.finditer と同じく、重ならない出現だけを左から拾う（indexOf は速いので、評価のたびに全員分を回しても軽い）
        for (let i = clause.indexOf(alias); i >= 0; i = clause.indexOf(alias, i + alias.length)) mentions.push([i, i + alias.length, key]);
      }
    }
    // 同じ箇所の「観客参加」と「観客参加型」などは、最長の一致だけを採る
    mentions.sort((x, y) => (x[0] - y[0]) || ((y[1] - y[0]) - (x[1] - x[0])) || (x[2] < y[2] ? -1 : x[2] > y[2] ? 1 : 0));
    const chosen = [];
    for (const m of mentions) if (!chosen.some(c => m[0] < c[1] && c[0] < m[1])) chosen.push(m);
    chosen.forEach(([, end, key], i) => {
      const stop = i + 1 < chosen.length ? chosen[i + 1][0] : clause.length;
      const tail = clause.slice(end, stop);
      if (UNCERTAIN.test(tail)) return;                       // 遠くの評価や推量を好みと決めつけない
      const evaluations = [...tail.matchAll(EVALUATION)];
      if (!evaluations.length) return;
      const first = evaluations[0];
      const firstAt = cp(tail.slice(0, first.index));
      if (firstAt > 16) return;
      if (!BRIDGE.test(tail.slice(0, first.index))) return;
      // 「苦手ではない」「最高ではない」は好みの方向を保留する
      if (evaluations.some(m => NOT_AFTER.test(tail.slice(m.index + m[0].length)))) return;
      const values = new Set(evaluations.map(m => (m.groups.negative ? -1.0 : m.groups.weak ? 0.5 : 1.0)));
      if (values.size !== 1) return;
      let quote = raw.trim();
      if (cp(quote) > 160) quote = [...quote].slice(0, 160).join('') + '…';
      signals.push({feature: key, label: vocabulary.get(key), value: [...values][0], quote});
    });
  }
  return signals;
}

/**
 * 1 作品・1 特徴につき 1 票。works は {work_key, title, first_date, note_impression, unseen, elements}
 * （elements はその作品の公演に付いた種類の言葉）。見ていない・未来の記録は呼び出し側で除く
 */
export function buildProfile(works) {
  const votes = new Map();
  const seen = new Set();
  for (const work of works) {
    const key = String(work.work_key || work.key || '');
    if (!key || seen.has(key) || work.unseen) continue;
    seen.add(key);
    const note = work.note_impression || '';
    if (!note.trim()) continue;
    const perWork = new Map();
    for (const s of extract(note, work.elements || [])) {
      if (!perWork.has(s.feature)) perWork.set(s.feature, []);
      perWork.get(s.feature).push(s);
    }
    for (const [feature, signals] of perWork) {
      const values = [...new Set(signals.map(s => s.value))];
      if (values.some(v => v > 0) && values.some(v => v < 0)) continue;   // 同じ作品で好評と不評が混在するものは保留
      const signal = signals[signals.length - 1];
      if (!votes.has(feature)) votes.set(feature, []);
      votes.get(feature).push({...signal, value: values.reduce((a, b) => a + b, 0) / values.length, work_key: key,
        title: work.title || '', date: work.first_date || ''});
    }
  }
  const profile = new Map();
  for (const [feature, evidence] of votes) {
    evidence.sort((a, b) => (a.date === b.date ? (a.work_key < b.work_key ? 1 : a.work_key > b.work_key ? -1 : 0) : (a.date < b.date ? 1 : -1)));
    profile.set(feature, {weight: evidence.reduce((a, e) => a + e.value, 0) / (evidence.length + PRIOR), count: evidence.length, evidence});
  }
  return profile;
}

export const round6 = x => Number(x.toFixed(6));

/** 候補の種類の言葉と好みから、補正値と理由（上位 TOP_N の特徴）を返す */
export function score(elements, profile) {
  let parts = [];
  for (const [feature, label] of features(elements)) {
    const p = profile.get(feature);
    if (!p || !p.weight) continue;
    const sign = p.weight > 0 ? 1 : -1;
    const evidence = p.evidence.find(e => e.value * sign > 0);
    parts.push({feature, label, value: p.weight, count: p.count, evidence: {...evidence}});
  }
  parts.sort((a, b) => (Math.abs(b.value) - Math.abs(a.value)) || (a.feature < b.feature ? -1 : a.feature > b.feature ? 1 : 0));
  parts = parts.slice(0, TOP_N);
  // 特徴が多い公演が有利にならないよう、固定の上限で平均して補正を抑える
  return [round6(WEIGHT * parts.reduce((a, p) => a + p.value, 0) / TOP_N), parts];
}

/**
 * 推薦の候補に効かせる補正（rankedGroups から呼ぶ）。rated は ratedWorks の行（note に感想、people に公演の
 * 種類の言葉 ['#題材', '家族'] などを含む）。感想の書かれた作品が無ければ何も読まずに null。
 * 候補の種類の言葉は、好みのある言葉だけを索引から 1 回引く（候補全部を回さない。Worker の CPU を増やさない）。
 * 戻り値は {profile, adjust: Map(stage_id → [補正, 理由])}
 */
export async function impressionAdjust({postingsFor}, rated, axes) {
  const works = [];
  const axesOf = new Map();                         // 特徴 → 観た公演でその言葉が付いていた軸（'#題材' など）
  for (const r of rated) {
    if (!r.note || !String(r.note).trim()) continue;
    const kinds = (r.people || []).filter(([role]) => role.startsWith('#') && axes.includes(role));
    for (const [role, word] of kinds) {
      const k = canonical(word);
      if (!axesOf.has(k)) axesOf.set(k, new Set());
      axesOf.get(k).add(role);
    }
    works.push({work_key: r.key, title: r.title, first_date: r.date || '', note_impression: r.note,
      elements: kinds.map(([, word]) => ({word}))});
  }
  if (!works.length) return null;
  const profile = buildProfile(works);
  if (!profile.size) return null;
  // 好みのある特徴の表記（同義語・作品に付いていた表記）を、その特徴が付いていた軸だけで引く（全部の軸で引くと
  // 問い合わせが軸の数だけ増える）
  const seen = new Set(), keys = [];
  for (const [feature, p] of profile) {
    const forms = new Set([...(ALIASES.find(a => canonical(a[0]) === feature) || []), ...p.evidence.map(e => e.label)]);
    for (const axis of axesOf.get(feature) || []) for (const w of forms) {
      const k = axis + '\u0000' + w;
      if (!seen.has(k)) { seen.add(k); keys.push([axis, w]); }
    }
  }
  keys.sort((a, b) => (a[0] + '\u0000' + a[1] < b[0] + '\u0000' + b[1] ? -1 : 1));
  const words = new Map();                          // stage_id → その公演に付いた、好みのある言葉
  for (const [, word, sid] of await postingsFor(keys)) {
    if (!words.has(sid)) words.set(sid, []);
    words.get(sid).push({word});
  }
  const adjust = new Map();
  for (const [sid, el] of words) {
    const [value, parts] = score(el, profile);
    if (value) adjust.set(String(sid), [value, parts]);
  }
  return {profile, adjust};
}
