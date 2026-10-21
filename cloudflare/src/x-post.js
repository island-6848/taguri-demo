// X のポストを感想に取り込む（起案者 2026-10-21「Xと連携して、ツイートを感想として紐付けられると便利そう」
// 「リンク貼る方式にしましょう」）。感想の欄にポストの URL を貼ると、その本文を感想に入れ、最後の行に出どころを残す。
// X の API は 2026-02 から読むたびに有料なので使わない（自分のポストの一覧から選ぶ形は、その一覧を読むのが有料で見送った）。
// 埋め込み用の oEmbed（publish.twitter.com、鍵も回数の上限も無い）で、公開のポスト 1 件の本文と日付だけを読む。
// 非公開・削除済みのポストは読めない。誰のポストかは確かめない（記録は本人にしか見えない）

/** 貼られた文がポストの URL なら x.com の形にそろえて返す。違えば ''。 */
const POST_URL = /^https?:\/\/(?:www\.|mobile\.)?(?:x|twitter)\.com\/([A-Za-z0-9_]{1,15})\/status(?:es)?\/(\d{1,25})(?:[/?#]\S*)?$/;
export function postUrl(text) {
  const m = String(text || '').trim().match(POST_URL);
  return m ? `https://x.com/${m[1]}/status/${m[2]}` : '';
}

// 感想の最後の行に置く出どころ: 「[X 2026-10-18] https://x.com/…/status/…」。画面はこの行を
// 「2026/10/18 の X のポストから · X で見る」に変えて出す（row.noteParts）
const MARK = /\n*\[X (\d{4}-\d{2}-\d{2})?\] (https:\/\/x\.com\/[A-Za-z0-9_]{1,15}\/status\/\d{1,25})\s*$/;
export const mark = (date, url) => `[X ${date || ''}] ${url}`;
/** 感想の文を、本文と出どころ（無ければ null）に分ける。 */
export function splitMark(note) {
  const s = String(note || ''), m = s.match(MARK);
  return m ? {body: s.slice(0, m.index).trimEnd(), date: m[1] || '', url: m[2]} : {body: s, date: '', url: ''};
}

const ENT = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '—'};
const decode = s => s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
  if (e[0] !== '#') return ENT[e.toLowerCase()] ?? m;
  const n = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
  return n > 0 && n <= 0x10ffff ? String.fromCodePoint(n) : m;
});
const MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];

/**
 * oEmbed の html（<blockquote class="twitter-tweet"><p …>本文</p>&mdash; 名前 (@id) <a …>October 18, 2026</a></blockquote>）
 * から本文と日付を取る。画像のリンク（pic.twitter.com/…）は外す。ハッシュタグは文のまま残る（感想の #タグ になる）
 */
export function parseEmbed(html) {
  const s = String(html || '');
  const p = s.match(/<p\b[^>]*>([\s\S]*?)<\/p>/i);
  const text = p ? decode(p[1].replace(/<br\s*\/?>/gi, '\n').replace(/<a\b[^>]*>\s*pic\.(?:twitter|x)\.com\/\S*?<\/a>/gi, '').replace(/<[^>]+>/g, ''))
    .replace(/[ \t]+\n/g, '\n').trim() : '';
  const d = [...s.matchAll(/<a\b[^>]*>([A-Za-z]+) (\d{1,2}), (\d{4})<\/a>/g)].pop();
  const mi = d ? MONTHS.indexOf(d[1].toLowerCase()) : -1;
  const date = mi >= 0 ? `${d[3]}-${String(mi + 1).padStart(2, '0')}-${d[2].padStart(2, '0')}` : '';
  return {text, date};
}

const OEMBED = 'https://publish.twitter.com/oembed';
/** GET /api/x_post?url=… の中身。fetchImpl は試験で差し替える。 */
export async function readPost(raw, fetchImpl = fetch) {
  const url = postUrl(raw);
  if (!url) return {status: 400, body: {ok: false, error: 'X のポストの URL ではありません。'}};
  const q = new URLSearchParams({url: url.replace('https://x.com/', 'https://twitter.com/'), omit_script: '1', dnt: 'true', lang: 'ja'});
  let res;
  try { res = await fetchImpl(`${OEMBED}?${q}`, {headers: {accept: 'application/json'}, signal: AbortSignal.timeout(8000)}); } catch {
    return {status: 502, body: {ok: false, error: 'X につながりませんでした。少し待ってから、もう一度貼ってください。'}};
  }
  if (!res.ok) return {status: 404, body: {ok: false, error: 'このポストは読めませんでした（鍵のかかったポスト・消されたポストは読めません）。'}};
  let data;
  try { data = await res.json(); } catch { data = {}; }
  const {text, date} = parseEmbed(data.html);
  if (!text) return {status: 404, body: {ok: false, error: 'このポストには文がありませんでした。'}};
  return {status: 200, body: {ok: true, text: text.slice(0, 3000), date, url, mark: mark(date, url)}};
}
