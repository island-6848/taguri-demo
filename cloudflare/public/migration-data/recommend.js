// "あなたへのおすすめ（試験版）": the 今週のおすすめ ranking (GET /migration-api/recommend
// answers with the screen's own recommendations since #119: the 日記帳 / 評価 / 興味あり /
// お気に入り of the service, not the records on this page). Shown only when signed in.
// Everything from the server is set with textContent.
const $ = s => document.querySelector(s);
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n; };
const day = iso => iso ? iso.replaceAll('-', '/') : '';

async function load() {
  const box = $('#rec-list'), note = $('#rec-status');
  let data;
  try {
    const res = await fetch('/migration-api/recommend', {cache: 'no-store'});
    if (!res.ok) { $('#recommend').hidden = true; return; }
    data = await res.json();
  } catch { note.textContent = 'おすすめを読み込めませんでした。'; return; }
  $('#recommend').hidden = false;
  box.replaceChildren();
  if (!data.ready) { note.textContent = '公演の索引がまだ作られていません。'; return; }
  if (!data.items.length) {
    note.textContent = data.n_linked ? 'いまの記録からは、おすすめできる公演が見つかりませんでした。評価が増えると出やすくなります。'
      : 'まだおすすめを出せません。日記帳の記録を公演に結び付けて評価するか、お気に入り・興味ありを登録してください。';
    return;
  }
  note.textContent = `「今週のおすすめ」と同じ、全国の上位です（日記帳の評価${data.n_rated}件・公演に結び付いた記録${data.n_linked}件ほかから）。`;
  for (const item of data.items) {
    const a = el('article');
    const h = el('h3');
    if (item.url) { const link = el('a', item.title); link.href = item.url; link.rel = 'noopener noreferrer'; link.target = '_blank'; h.append(link); }
    else h.textContent = item.title;
    a.append(h, el('p', [item.group, [item.theater, item.pref].filter(Boolean).join('・'), [day(item.start), day(item.end)].filter(Boolean).join('〜')].filter(Boolean).join('　')));
    // A tour's other venues (one slot per production).
    if ((item.tours || []).length) a.append(el('p', 'ほかの会場：' + item.tours.map(t =>
      [t.theater || '会場未定', [day(t.start), day(t.end)].filter(Boolean).join('〜')].filter(Boolean).join(' ')).join('／'), 'tours'));
    a.append(el('p', '理由：' + item.reasons.map(r => `${r.role} ${r.person}（${r.n ? r.n + '作品' : 'お気に入り・興味ありから'}）`).join('、'), 'why'));
    box.append(a);
  }
}

const content = $('#content');
if (content) {
  if (!content.hidden) load();
  new MutationObserver(() => { if (!content.hidden) load(); else $('#recommend').hidden = true; })
    .observe(content, {attributes: true, attributeFilter: ['hidden']});
  document.addEventListener('taguri:records-changed', () => { if (!content.hidden) load(); });
}
