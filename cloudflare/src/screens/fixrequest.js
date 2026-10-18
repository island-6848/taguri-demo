// 公演修正依頼（起案者の指示 2026-10-17「ユーザーが『公演修正依頼』を送ってきたら私に通知が来て、この管理画面から
// 編集できるようにしたい」→ 通知はメール）。カードの「情報の誤りを知らせる」（web/app.js）から届き、fix_request
// （migration 0030）に保存して、起案者にメールで知らせる。対応は手元の管理画面（tools/admin）で。
//
// メール: 独自ドメインを使わない約束なので Cloudflare のメール送信（Email Routing のドメインが要る）は使えない。
// 起案者の Gmail に SMTP（smtp.gmail.com:465、TLS）でつなぎ、自分宛てに送る。鍵は Worker の秘密の設定にだけ置く:
//   SMTP_USER（Gmail のアドレス）・SMTP_PASS（Google の「アプリ パスワード」）・NOTIFY_TO（届け先。無ければ SMTP_USER）
// 設定が無い・送れないときも依頼は保存する（管理画面で見られる）。
import {ValueError} from './py.js';
import {FIX_REQUESTS_PER_USER_DAY, FIX_MAILS_PER_DAY, FIX_OPEN_PER_USER, FIX_STORED_PER_USER, FIX_STORED_TOTAL,
  FIX_RESOLVED_BODY_DAYS, FIX_RESOLVED_ROW_DAYS} from '../free-tier.js';

export const KINDS = ['日程', '料金', '会場', 'あらすじ', '出演・スタッフ', 'ポスター', 'その他'];
const MAX_MESSAGE = 1000;
export const PURGED = '（対応済みのため消去）';   // 対応済みの依頼の本文を消したあとに置く文

const b64 = s => btoa(String.fromCharCode(...new TextEncoder().encode(s)));
const wrap76 = s => s.replace(/.{1,76}/g, m => m + '\r\n');
/** The mail as SMTP DATA (UTF-8 subject and body, base64). */
export function mailData({from, to, subject, text, date = new Date()}) {
  return [`From: たぐり <${from}>`, `To: ${to}`, `Subject: =?UTF-8?B?${b64(subject)}?=`, `Date: ${date.toUTCString()}`,
    'MIME-Version: 1.0', 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: base64', '', wrap76(b64(text))].join('\r\n');
}

/** Talks SMTP over an open socket-like {readable, writable}. Throws on any unexpected reply. */
export async function smtpSend(sock, {user, pass, from, to, data, host = 'taguri.workers.dev'}) {
  const reader = sock.readable.getReader(), writer = sock.writable.getWriter();
  const enc = new TextEncoder(), dec = new TextDecoder();
  let buf = '';
  const reply = async () => {
    for (;;) {
      const lines = buf.split('\r\n');
      for (let i = 0; i < lines.length - 1; i++) {
        if (/^\d{3} /.test(lines[i])) { buf = lines.slice(i + 1).join('\r\n'); return Number(lines[i].slice(0, 3)); }
      }
      const {value, done} = await reader.read();
      if (done) throw new Error('SMTP: closed');
      buf += dec.decode(value, {stream: true});
    }
  };
  const step = async (line, want) => {
    if (line !== null) await writer.write(enc.encode(line + '\r\n'));
    const code = await reply();
    if (code !== want) throw new Error(`SMTP: ${code} (wanted ${want})`);
  };
  await step(null, 220);
  await step(`EHLO ${host}`, 250);
  await step(`AUTH PLAIN ${btoa(`\0${user}\0${pass}`)}`, 235);
  await step(`MAIL FROM:<${from}>`, 250);
  await step(`RCPT TO:<${to}>`, 250);
  await step('DATA', 354);
  await step(data.replace(/\r\n\./g, '\r\n..') + '\r\n.', 250);
  try { await writer.write(enc.encode('QUIT\r\n')); } catch { /* closing anyway */ }
}

async function gmailSocket() {
  const {connect} = await import('cloudflare:sockets');
  return connect({hostname: 'smtp.gmail.com', port: 465}, {secureTransport: 'on'});
}

/** Mails the owner. true when sent; false when not configured, over the day's cap or failed. */
export async function notifyOwner(ctx, subject, text, open = gmailSocket) {
  const env = ctx.env || {};
  const user = env.SMTP_USER, pass = env.SMTP_PASS, to = env.NOTIFY_TO || env.SMTP_USER;
  if (!user || !pass || !to) return false;
  const key = `fix_mail:${ctx.today}`;
  const n = (await ctx.db.prepare('INSERT INTO usage(k, n) VALUES (?, 1) ON CONFLICT(k) DO UPDATE SET n = n + 1 RETURNING n').bind(key).first())?.n || 0;
  if (n > (Number(env.FIX_MAILS_PER_DAY) || FIX_MAILS_PER_DAY)) return false;     // 数えてから送る（送れなかった分も数える）
  let sock;
  try {
    sock = await open();
    await smtpSend(sock, {user, pass, from: user, to, data: mailData({from: user, to, subject, text})});
    return true;
  } catch (e) {
    console.log('fix_request mail failed:', String(e && e.message || e));
    return false;
  } finally {
    try { await sock?.close(); } catch { /* already closed */ }
  }
}

async function fixRequestAction(b, ctx) {
  const stageId = String(b.stage_id ?? ''), kind = String(b.kind ?? ''), message = String(b.message ?? '').trim();
  if (!/^[A-Za-z0-9_-]{1,40}$/.test(stageId)) throw new ValueError('公演が分かりません');
  if (!KINDS.includes(kind)) throw new ValueError('どこが違うかを選んでください');
  if (!message) throw new ValueError('どう違うかを書いてください（正しい情報や、載っているページの URL など）');
  if (message.length > MAX_MESSAGE) throw new ValueError(`${MAX_MESSAGE} 字までにしてください`);
  const since = new Date(Date.parse(ctx.today + 'T00:00:00+09:00')).toISOString();
  const st = await ctx.db.prepare("SELECT title FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id=?").bind(stageId).first()
    || await ctx.db.prepare('SELECT title FROM catalogue WHERE id=?').bind(stageId).first();
  const title = st?.title || '';
  const at = new Date(ctx.now).toISOString();
  // 上限は INSERT の条件に入れる（数えてから入れるまでのあいだに別の依頼が入っても越えない。issue #129）
  const row = await ctx.db.prepare(`INSERT INTO fix_request(stage_id,user_id,kind,message,created_at)
    SELECT ?1,?2,?3,?4,?5 WHERE (SELECT count(*) FROM fix_request WHERE user_id=?2 AND created_at>=?6)<?7
      AND (SELECT count(*) FROM fix_request WHERE user_id=?2 AND status='open')<?8
      AND (SELECT count(*) FROM fix_request WHERE user_id=?2)<?9
      AND (SELECT count(*) FROM fix_request)<?10 RETURNING id`)
    .bind(stageId, ctx.uid, kind, message, at, since, FIX_REQUESTS_PER_USER_DAY, FIX_OPEN_PER_USER, FIX_STORED_PER_USER,
      FIX_STORED_TOTAL).first();
  if (!row) throw new ValueError(await refusal(ctx, since));
  const open = (await ctx.db.prepare("SELECT count(*) AS n FROM fix_request WHERE status='open'").first())?.n || 0;
  const text = `たぐりに公演修正依頼が届きました（依頼 #${row.id}）。\n\n公演: ${title || '（題名不明）'}（#${stageId}）\n`
    + `違うところ: ${kind}\n内容:\n${message}\n\n${/^\d+$/.test(stageId) ? `公演のページ: https://stage.corich.jp/stage/${stageId}\n` : ''}`
    + `\n手元の管理画面（tools/admin/open-admin）の「公演修正依頼」から開いて直せます。まだ対応していない依頼: ${open} 件\n`
    + 'このメールは、たぐりの Worker が起案者の Gmail から自分宛てに送っています。依頼した人の名前やアドレスは入れていません。';
  const mailed = await notifyOwner(ctx, `【たぐり】公演修正依頼: ${title || stageId}（${kind}）`, text, ctx.env?.SMTP_OPEN);
  if (mailed) await ctx.db.prepare('UPDATE fix_request SET mailed=1 WHERE id=?').bind(row.id).run();
  return {body: {ok: true, id: row.id, said: '送りました。ありがとうございます。確かめて直します。直すまで少し時間がかかることがあります'}};
}

/** Why the conditional INSERT added nothing (the first limit that is reached). */
async function refusal(ctx, since) {
  const c = await ctx.db.prepare(`SELECT
      (SELECT count(*) FROM fix_request WHERE user_id=?1 AND created_at>=?2) AS today,
      (SELECT count(*) FROM fix_request WHERE user_id=?1 AND status='open') AS open,
      (SELECT count(*) FROM fix_request WHERE user_id=?1) AS mine`).bind(ctx.uid, since).first() || {};
  if (c.today >= FIX_REQUESTS_PER_USER_DAY) return `1 日に送れる依頼は ${FIX_REQUESTS_PER_USER_DAY} 件までです。明日またお願いします`;
  if (c.open >= FIX_OPEN_PER_USER) return `まだ確かめていない依頼が ${FIX_OPEN_PER_USER} 件あります。確かめ終わるまで、少し待ってください`;
  if (c.mine >= FIX_STORED_PER_USER) return `送れる依頼は ${FIX_STORED_PER_USER} 件までです。古い依頼が片付くまで、少し待ってください`;
  return 'いまは依頼を受け付けられません。しばらくしてから送ってください';
}

/**
 * 対応済みの依頼を片付ける（Worker の定期実行が 1 日 1 回呼ぶ。issue #129）。
 * 直してから FIX_RESOLVED_BODY_DAYS 日たった依頼は本文を消し、FIX_RESOLVED_ROW_DAYS 日たった依頼は行ごと消す。
 * 未対応の依頼は消さない（数は FIX_OPEN_PER_USER・FIX_STORED_TOTAL で抑える）。D1 の書き込みは 1 日 2 文と、変えた行の数。
 */
export async function purgeFixRequests(db, nowMs = Date.now()) {
  const before = days => new Date(nowMs - days * 86400_000).toISOString();
  const cleared = await db.prepare(`UPDATE fix_request SET message=?1 WHERE status!='open' AND resolved_at IS NOT NULL
    AND resolved_at<?2 AND message!=?1`).bind(PURGED, before(FIX_RESOLVED_BODY_DAYS)).run();
  const removed = await db.prepare(`DELETE FROM fix_request WHERE status!='open' AND resolved_at IS NOT NULL AND resolved_at<?`)
    .bind(before(FIX_RESOLVED_ROW_DAYS)).run();
  return {cleared: cleared?.meta?.changes ?? cleared?.changes ?? 0, removed: removed?.meta?.changes ?? removed?.changes ?? 0};
}

export const fixRequestScreens = {actions: {fix_request: fixRequestAction}};
