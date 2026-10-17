// 公演修正依頼（起案者の指示 2026-10-17「ユーザーが『公演修正依頼』を送ってきたら私に通知が来て、この管理画面から
// 編集できるようにしたい」→ 通知はメール）。カードの「情報の誤りを知らせる」（web/app.js）から届き、fix_request
// （migration 0030）に保存して、起案者にメールで知らせる。対応は手元の管理画面（tools/admin）で。
//
// メール: 独自ドメインを使わない約束なので Cloudflare のメール送信（Email Routing のドメインが要る）は使えない。
// 起案者の Gmail に SMTP（smtp.gmail.com:465、TLS）でつなぎ、自分宛てに送る。鍵は Worker の秘密の設定にだけ置く:
//   SMTP_USER（Gmail のアドレス）・SMTP_PASS（Google の「アプリ パスワード」）・NOTIFY_TO（届け先。無ければ SMTP_USER）
// 設定が無い・送れないときも依頼は保存する（管理画面で見られる）。
import {ValueError} from './py.js';
import {FIX_REQUESTS_PER_USER_DAY, FIX_MAILS_PER_DAY} from '../free-tier.js';

export const KINDS = ['日程', '料金', '会場', 'あらすじ', '出演・スタッフ', 'ポスター', 'その他'];
const MAX_MESSAGE = 1000;

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
  const n = (await ctx.db.prepare('SELECT count(*) AS n FROM fix_request WHERE user_id=? AND created_at>=?').bind(ctx.uid, since).first())?.n || 0;
  if (n >= FIX_REQUESTS_PER_USER_DAY) throw new ValueError(`1 日に送れる依頼は ${FIX_REQUESTS_PER_USER_DAY} 件までです。明日またお願いします`);
  const st = await ctx.db.prepare("SELECT title FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id=?").bind(stageId).first()
    || await ctx.db.prepare('SELECT title FROM catalogue WHERE id=?').bind(stageId).first();
  const title = st?.title || '';
  const at = new Date(ctx.now).toISOString();
  const row = await ctx.db.prepare('INSERT INTO fix_request(stage_id,user_id,kind,message,created_at) VALUES(?,?,?,?,?) RETURNING id')
    .bind(stageId, ctx.uid, kind, message, at).first();
  const open = (await ctx.db.prepare("SELECT count(*) AS n FROM fix_request WHERE status='open'").first())?.n || 0;
  const text = `たぐりに公演修正依頼が届きました（依頼 #${row.id}）。\n\n公演: ${title || '（題名不明）'}（#${stageId}）\n`
    + `違うところ: ${kind}\n内容:\n${message}\n\n${/^\d+$/.test(stageId) ? `公演のページ: https://stage.corich.jp/stage/${stageId}\n` : ''}`
    + `\n手元の管理画面（tools/admin/open-admin）の「公演修正依頼」から開いて直せます。まだ対応していない依頼: ${open} 件\n`
    + 'このメールは、たぐりの Worker が起案者の Gmail から自分宛てに送っています。依頼した人の名前やアドレスは入れていません。';
  const mailed = await notifyOwner(ctx, `【たぐり】公演修正依頼: ${title || stageId}（${kind}）`, text, ctx.env?.SMTP_OPEN);
  if (mailed) await ctx.db.prepare('UPDATE fix_request SET mailed=1 WHERE id=?').bind(row.id).run();
  return {body: {ok: true, id: row.id, said: '送りました。ありがとうございます。確かめて直します。直すまで少し時間がかかることがあります'}};
}

export const fixRequestScreens = {actions: {fix_request: fixRequestAction}};
