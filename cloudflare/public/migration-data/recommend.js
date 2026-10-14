// "あなたへのおすすめ（試験版）": person-score recommendations computed by the
// Worker from the user's own ratings (GET /migration-api/recommend). Shown
// only when signed in. Everything from the server is set with textContent.
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
    note.textContent = data.n_linked ? 'いまの記録からは、おすすめできる公演が見つかりませんでした。◎の記録が増えると出やすくなります。'
      : '記録が公演に結び付いていないため、まだおすすめを出せません。下の「観劇記録」で、記録ごとに「公演を探して結び付ける」を押してください。';
    return;
  }
  note.textContent = `あなたの評価で良かった作品に関わった人が出る、これからの公演です（評価${data.n_rated}件・公演に結び付いた記録${data.n_linked}件から）。`;
  for (const item of data.items) {
    const a = el('article');
    const h = el('h3');
    if (item.url) { const link = el('a', item.title); link.href = item.url; link.rel = 'noopener noreferrer'; link.target = '_blank'; h.append(link); }
    else h.textContent = item.title;
    a.append(h, el('p', [item.group, [item.theater, item.pref].filter(Boolean).join('・'), [day(item.start), day(item.end)].filter(Boolean).join('〜')].filter(Boolean).join('　')));
    // A tour's other venues (one slot per production).
    if ((item.tours || []).length) a.append(el('p', 'ほかの会場：' + item.tours.map(t =>
      [t.theater || '会場未定', [day(t.start), day(t.end)].filter(Boolean).join('〜')].filter(Boolean).join(' ')).join('／'), 'tours'));
    a.append(el('p', '理由：' + item.reasons.map(r => `${r.role} ${r.person}（${r.n ? r.n + '作品' : 'お気に入りから'}）`).join('、'), 'why'));
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
