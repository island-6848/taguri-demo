// 利用規約・プライバシーの説明への同意（起案者の指示 2026-10-17「規約は新規登録の際に、規約に同意して始める、に
// チェックボックスいれてもらってから登録できるようにする」）。民法 548 条の 2（定型約款の組入れ）の「契約の内容とする
// 旨の合意」を、登録のときのチェックで取る。画面（login.html）のチェックが送る版と、ここの版が同じときだけ登録する。
// 文面は public/terms.html・public/privacy.html。変えたら版を上げる（古い画面のまま押した人は読み込み直しになる）
import {ValueError} from './screens/py.js';

export const TERMS_VERSION = '2026-10-18-2';

/** 新しいアカウントを作る前に呼ぶ。同意が無い・版が古いときは fail で止める */
export function requireAgreement(input, fail) {
  const v = input?.agree;
  if (v === TERMS_VERSION) return;
  if (typeof v === 'string' && v) fail(409, '利用規約が新しくなりました。画面を読み込み直して、内容を確かめてから始めてください。');
  fail(400, 'はじめての方は利用規約とプライバシーの説明を読んで、「同意して始める」にチェックを入れてください。');
}

// 版が上がったあと、それより前に同意した（または同意の記録が無い）人に、次に開いたときに同意し直してもらう
// （起案者の回答 2026-10-17「規約も含める」＝ 文言を yomiyasu で書き直し、登録済みの人にも同意し直してもらう）。
// 画面の答え（/api/screen/*）に terms_update を付け、画面（web/app.js agreeAgain）が同意を求める。押すとここに来る
export async function agreeAction(b, ctx) {
  if (b?.agree !== TERMS_VERSION) throw new ValueError('利用規約が新しくなりました。画面を読み込み直して、内容を確かめてから同意してください。');
  await ctx.db.prepare('UPDATE users SET terms_version=?, terms_at=? WHERE id=?').bind(TERMS_VERSION, Math.floor(ctx.now / 1000), ctx.uid).run();
  return {body: {ok: true, terms_version: TERMS_VERSION}};
}
/** The version the user has agreed to is older (or none): the screens ask again. */
export async function needsAgreement(db, uid) {
  const v = (await db.prepare('SELECT terms_version FROM users WHERE id=?').bind(uid).first())?.terms_version;
  return v !== TERMS_VERSION;
}
