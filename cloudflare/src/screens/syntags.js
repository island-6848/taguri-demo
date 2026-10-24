// 観た公演の、あらすじから読み取ったタグ（カードのあらすじの下のハッシュタグと同じ語）。眺めるのことばの雲（records.tagsFor）と、
// 評価一覧・未評価・日記帳の 1 件のあらすじの下のハッシュタグ（rowinfo.rowInfos）で使う
import {loadOverrides} from './override.js';

const TAG_STAGES = 300;
const tagKey = w => String(w ?? '').normalize('NFKC').replace(/[\s　]+/gu, '').toLowerCase();   // recommend2.nz と同じ
/**
 * 観た公演ごとの、あらすじから読み取ったタグ（カードのあらすじの下のハッシュタグと同じ語）。stage_id -> 語の並び（タグのある公演だけ）。
 * 起案者の指示 2026-10-24「ワードクラウドはあらすじ抽出でタグに出ている単語リストから構成してほしい」。引く順は札と同じ:
 * - 管理者が手で入れた題材（stage_override.themes）がある公演は、それ（カードの札もそれに差し替わる。override.applySynopsis）
 * - 無ければ、作り置きのカードの題材（rec_card.ws。1 行に 1 語。tagged.js がハッシュタグの当たりを引くのと同じ列）
 * - それも無ければ、過去の公演の #題材（past_stage.people。過去の公演の読み取りの結果）
 * 1 公演の中で同じ語（nz でそろえて同じもの）は 1 つにする。読むのは観た公演の行だけ（主キー）
 */
export async function synTagMap(ctx, sids) {
  const want = [...new Set(sids.filter(Boolean).map(String))].slice(0, TAG_STAGES), out = new Map();
  const put = (sid, words) => {
    const seen = new Set(), list = [];
    for (const w of words || []) {
      const t = String(w ?? '').trim(), k = tagKey(t);
      if (k && !seen.has(k)) { seen.add(k); list.push(t); }
    }
    if (list.length) out.set(sid, list);
  };
  const ovs = await loadOverrides(ctx.db, want);
  for (const sid of want) { const t = ovs.get(sid)?.themes; if (Array.isArray(t)) put(sid, t); }
  const done = sid => out.has(sid) || Array.isArray(ovs.get(sid)?.themes);   // 手で「題材なし」にした公演は、ほかから足さない
  const ask = async (sql, rest, row) => {
    for (let i = 0; i < rest.length; i += 90) {
      const part = rest.slice(i, i + 90);
      try {
        const {results} = await ctx.db.prepare(sql.replace('%', part.map(() => '?').join(','))).bind(...part).all();
        for (const r of results) row(r);
      } catch { return; }   // 表が無い（試験の小さな D1）ときは、ある分だけで描く
    }
  };
  await ask(`SELECT stage_id, ws FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND stage_id IN (%) AND ws<>''`,
    want.filter(s => !done(s)), r => put(String(r.stage_id), String(r.ws).split('\n')));
  await ask(`SELECT stage_id, people FROM past_stage WHERE stage_id IN (%)`, want.filter(s => !done(s)), r => {
    try { put(String(r.stage_id), JSON.parse(r.people || '[]').filter(p => p[0] === '#題材').map(p => p[1])); } catch { /* broken row */ }
  });
  return out;
}
