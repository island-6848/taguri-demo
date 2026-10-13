// "公演に結び付ける": links a record to a stage in the catalogue, so the
// person-score recommendations know who was in it (GET /migration-api/stages).
// Everything from the server is set with textContent.
const names = new Map();        // stage_id -> display fields (or null: not in the index)
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n; };
const day = iso => iso ? iso.replaceAll('-', '/') : '';
const describe = s => [s.group, [s.theater, s.pref].filter(Boolean).join('・'), [day(s.start), day(s.end)].filter(Boolean).join('〜')].filter(Boolean).join('　');

async function stages(query) {
  const res = await fetch(`/migration-api/stages?${query}`, {cache: 'no-store'});
  const data = await res.json();
  if (!res.ok) throw new Error(data.error);
  return data;
}

/** Look up names of linked stages not seen yet (100 per request). */
export async function loadNames(records) {
  const ids = [...new Set(records.map(r => r.stage_id).filter(id => id && !names.has(id)))];
  for (let i = 0; i < ids.length; i += 100) {
    const chunk = ids.slice(i, i + 100), data = await stages('ids=' + chunk.map(encodeURIComponent).join(','));
    for (const id of chunk) names.set(id, null);
    for (const s of data.items) names.set(s.stage_id, s);
  }
}

/**
 * The link block of one record. save(stage_id) stores the record and resolves
 * to the saved record; the block redraws itself only, so unsaved edits to the
 * rating or note of the same record stay on screen.
 */
export function linkBlock(r, save) {
  const box = el('div', '', 'stage-link');
  const draw = () => {
    box.replaceChildren();
    if (r.stage_id) {
      const s = names.get(r.stage_id);
      const p = el('p', '', 'linked');
      p.append(el('strong', '公演：'), s ? s.title : `ID ${r.stage_id}（公演の一覧にありません）`);
      if (s && describe(s)) p.append(el('span', '　' + describe(s), 'meta'));
      box.append(p, button('結び付けを外す', async () => { Object.assign(r, await save('')); draw(); }));
    } else {
      box.append(el('p', 'どの公演の記録かを選ぶと、出演者やスタッフからおすすめを出せるようになります。', 'hint'),
        button('公演を探して結び付ける', async () => openSearch()));
    }
  };
  const openSearch = () => {
    box.replaceChildren();
    const label = el('label', '題名で探す'), input = el('input');
    input.type = 'search'; input.maxLength = 100; input.value = r.title; input.autocomplete = 'off';
    label.append(input);
    const note = el('p', '', 'status'), list = el('ul', '', 'stage-results');
    note.setAttribute('role', 'status');
    box.append(label, note, list, button('閉じる', async () => draw()));
    let timer, seq = 0;
    const search = async () => {
      const mine = ++seq, q = input.value.trim();
      list.replaceChildren();
      if ([...q].length < 2) { note.textContent = '2文字以上入力してください。'; return; }
      note.textContent = '探しています。';
      let data;
      try { data = await stages(new URLSearchParams({q, date: r.date || ''}).toString()); }
      catch (e) { if (mine === seq) note.textContent = e.message; return; }
      if (mine !== seq) return;            // a newer search is under way
      if (!data.ready) { note.textContent = '公演の一覧がまだ用意されていません。'; return; }
      if (!data.items.length) { note.textContent = '見つかりませんでした。副題や団体名を外して、短くすると見つかることがあります。'; return; }
      note.textContent = `${data.items.length}件。観劇日（${day(r.date)}）に上演していた公演を先に並べています。`;
      for (const s of data.items) {
        const li = el('li');
        li.append(el('span', s.title, 'title'), el('span', describe(s), 'meta'));
        if (s.url?.startsWith('https://')) { const a = el('a', '公演情報'); a.href = s.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; li.append(a); }
        li.append(button('この公演にする', async () => { names.set(s.stage_id, s); Object.assign(r, await save(s.stage_id)); draw(); }));
        list.append(li);
      }
    };
    input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(search, 300); });
    input.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); clearTimeout(timer); search(); } });
    input.focus();
    search();
  };
  const button = (text, action) => {
    const b = el('button', text); b.type = 'button';
    b.onclick = async () => { b.disabled = true; try { await action(); } catch (e) { box.append(el('p', e.message, 'status bad')); } finally { b.disabled = false; } };
    return b;
  };
  draw();
  return box;
}
