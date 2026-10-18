// 記録の無いアカウントを片付ける（起案者の指示 2026-10-18「1ヶ月で消してほしい」、issue #73）。
// Worker の定期実行（wrangler.jsonc の triggers.crons、1 日 1 回）が呼ぶ。消すのは次の 3 つが全部そろうもの:
// - 作ってから EMPTY_ACCOUNT_DAYS 日たった
// - 記録が 1 件も無い（RECORD_TABLES のどの表にも行が無い。設定・表示の控えだけは記録に数えない）
// - EMPTY_ACCOUNT_DAYS 日のあいだログインしていない（いま使っている人を消さない）
// 消し方はアカウントの削除（worker.js の deleteAccount）と同じ表を消す。Google 側（Firebase Authentication）の
// ログインの記録はサーバーからは消せないので残る（privacy.html の 6）。
import {SCREEN_TABLES} from './screens/index.js';

export const EMPTY_ACCOUNT_DAYS = 30;
// 1 回に消す数の上限（D1 の書き込みと、定期実行の CPU を小さく保つ。残りは次の日）
export const SWEEP_LIMIT = 50;
// 利用者が自分で足した記録の表
export const RECORD_TABLES = ['records', 'favourites', 'reactions', 'works', 'reaction', 'ticket', 'visit_note', 'hand_credits',
  'missed', 'search_request', 'merges', 'excluded'];
// アカウントの削除で消す表（users のほか）
export const ACCOUNT_TABLES = ['records', 'favourites', 'reactions', 'passkeys', 'webauthn_challenges', 'rec_cache', 'rec_shown',
  ...SCREEN_TABLES, 'sessions'];

/** 1 人分を消す文（users の行は最後） */
export function deleteAccountStatements(db, uid) {
  return ACCOUNT_TABLES.map(t => db.prepare(`DELETE FROM ${t} WHERE user_id=?`).bind(uid))
    .concat(db.prepare('DELETE FROM users WHERE id=?').bind(uid));
}

/** 片付けの対象を消して、消した数を返す */
export async function sweepEmptyAccounts(db, nowSec = Math.floor(Date.now() / 1000)) {
  const edge = nowSec - EMPTY_ACCOUNT_DAYS * 86400;
  const none = RECORD_TABLES.map(t => `NOT EXISTS (SELECT 1 FROM ${t} WHERE user_id=u.id)`).join(' AND ');
  const {results} = await db.prepare(`SELECT id FROM users u WHERE created_at<?1
    AND NOT EXISTS (SELECT 1 FROM sessions s WHERE s.user_id=u.id AND COALESCE(s.created_at, 0)>=?1) AND ${none} LIMIT ${SWEEP_LIMIT}`)
    .bind(edge).all();
  for (const {id} of results) await db.batch(deleteAccountStatements(db, id));
  return results.length;
}
