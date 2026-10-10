import {discover} from './discovery.js';
const $ = s => document.querySelector(s);
let data = {records:[],favourites:[],reactions:[]};
let catalogue=null;
const status = text => {$('#status').textContent=text;};
async function api(path,value) {
  const response = await fetch(`/api/${path}`,value === undefined ? {cache:'no-store'} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
  const result = await response.json();
  if(!response.ok) throw Object.assign(new Error(result.error),{status:response.status});
  return result;
}
function node(tag,text) {const n=document.createElement(tag);if(text)n.textContent=text;return n;}
function button(text,action) {const b=node('button',text);b.type='button';b.onclick=()=>run(b,action);return b;}
async function run(control,action) {control.disabled=true;try{await action();}catch(e){status(e.message);}finally{control.disabled=false;}}
function render() {
  $('#account').hidden=true;$('#content').hidden=false;
  $('#count').textContent=`${data.records.length}件`;
  $('#list').replaceChildren(...data.records.map(r=>{
    const a=node('article');a.append(node('h3',r.title),node('p',`${r.date} ${r.time} ${r.venue}`));
    const label=node('label','評価');const rating=node('select');for(const v of ['','◎','○','△','×']){const o=node('option',v||'未評価');o.value=v;rating.append(o);}rating.value=r.rating;label.append(rating);
    const nl=node('label','感想');const note=node('textarea');note.maxLength=4000;note.value=r.note;nl.append(note);
    a.append(label,nl,button('評価・感想を保存',async()=>{const saved=await api('record',{...r,rating:rating.value,note:note.value});Object.assign(r,saved.record);status('保存しました。');}),button('削除',async()=>{if(!confirm(`「${r.title}」を削除しますか？`))return;await api('record/delete',{id:r.id});data.records=data.records.filter(x=>x.id!==r.id);render();status('削除しました。');}));return a;
  }));
  $('#favs').replaceChildren(...data.favourites.map(f=>{const li=node('li',`${f.kind}：${f.name}`);li.append(button('解除',async()=>{await api('favourite',{...f,remove:true});data.favourites=data.favourites.filter(x=>x!==f);render();}));return li;}));
  renderDiscovery();
}
function renderDiscovery() {
  $('#shows').replaceChildren();
  if(catalogue===null){$('#catalogue-status').textContent='候補を読み込んでいます。';return;}
  if(!catalogue.length){$('#catalogue-status').textContent='公演候補データはまだ引き継がれていません。記録の保存は利用できます。';return;}
  const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo'}).format(new Date());
  const buckets=discover(catalogue,data.favourites,data.reactions??[],today);
  $('#catalogue-status').textContent=`${catalogue.length}件の候補から、お気に入りの名前・題材を照合しています。評価に基づく順位付けは準備中です。`;
  for(const [key,label] of Object.entries({favourites:'これからの公演',tracking:'興味あり',owned:'購入済み',started:'上演中',others:'興味なし'})) {
    const rows=buckets[key];if(!rows.length)continue;
    const section=node('div');section.append(node('h3',label));
    for(const c of rows.slice(0,50)) {
      const article=node('article');article.append(node('h4',c.title),node('p',`${c.date} ${c.venue}`),node('p',c.reasons.join('・')));
      if(c.url?.startsWith('https://')){const a=node('a','公演情報を開く');a.href=c.url;a.target='_blank';a.rel='noopener noreferrer';article.append(a);}
      for(const [signal,text] of [['interest','興味あり'],['no','興味なし'],['owned','購入済み']])article.append(button(text,async()=>{await api('reaction',{stage_id:c.id,status:signal});data.reactions=(data.reactions??[]).filter(r=>r.stage_id!==c.id);data.reactions.push({stage_id:c.id,status:signal});renderDiscovery();status('保存しました。');}));
      if((data.reactions??[]).some(r=>r.stage_id===c.id))article.append(button('選択を戻す',async()=>{const r=data.reactions.find(r=>r.stage_id===c.id);await api('reaction',{...r,remove:true});data.reactions=data.reactions.filter(r=>r.stage_id!==c.id);renderDiscovery();}));
      section.append(article);
    }
    if(rows.length>50)section.append(node('p',`先頭50件を表示しています（全${rows.length}件）。`));
    $('#shows').append(section);
  }
  if(!Object.values(buckets).some(rows=>rows.length))$('#shows').append(node('p','一致する公演はありません。お気に入りを追加してください。'));
}
async function refresh(){data=await api('state');render();if(catalogue===null)api('catalogue').then(r=>{catalogue=r.items;renderDiscovery();}).catch(e=>{$('#catalogue-status').textContent=e.message;});}
$('#register').onclick=()=>run($('#register'),async()=>{const result=await api('register',{});$('#code').textContent=result.recovery_code;$('#recovery').hidden=false;await refresh();status('保存先を作りました。復旧コードを控えてください。');});
$('#copy').onclick=()=>run($('#copy'),async()=>{await navigator.clipboard.writeText($('#code').textContent);status('復旧コードをコピーしました。');});
$('#recover').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{await api('recover',Object.fromEntries(new FormData(e.target)));$('#recovery').hidden=true;$('#code').textContent='';await refresh();status('記録を復旧しました。');});};
$('#add').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{const result=await api('record',Object.fromEntries(new FormData(e.target)));data.records.push(result.record);data.records.sort((a,b)=>b.date.localeCompare(a.date));render();e.target.reset();status('追加しました。');});};
$('#favourite').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{const f=Object.fromEntries(new FormData(e.target));await api('favourite',f);if(!data.favourites.some(x=>x.name===f.name&&x.kind===f.kind))data.favourites.push(f);render();e.target.reset();status('登録しました。');});};
$('#export').onclick=()=>run($('#export'),async()=>{const backup=await api('export');const url=URL.createObjectURL(new Blob([JSON.stringify(backup,null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download='taguri-backup.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('#import').onchange=e=>run(e.target,async()=>{
  const file=e.target.files[0];if(!file)return;if(file.size>10_000_000)throw new Error('10MBまでのファイルを選んでください。');
  const backup=JSON.parse(await file.text());backup.reactions??=[];if(![1,2].includes(backup.version)||!Array.isArray(backup.records)||!Array.isArray(backup.favourites)||!Array.isArray(backup.reactions)||backup.records.length>500||backup.favourites.length>200||backup.reactions.length>500)throw new Error('移行用JSONの形式を確認してください。');
  if(!confirm(`${backup.records.length}件の記録を取り込みますか？同じIDの記録は更新します。`))return;
  let done=0;
  try {for(let i=0;i<Math.max(backup.records.length,backup.favourites.length,backup.reactions.length,1);i+=10){await api('import',{version:2,records:backup.records.slice(i,i+10),favourites:backup.favourites.slice(i,i+10),reactions:backup.reactions.slice(i,i+10)});done+=backup.records.slice(i,i+10).length;}await refresh();status(`${done}件の記録とお気に入り・公演への反応を取り込みました。`);}catch(error){await refresh();throw new Error(`${done}件を取り込み済みです。残りの取り込みに失敗しました：${error.message}`);}finally{e.target.value='';}
});
$('#logout').onclick=()=>run($('#logout'),async()=>{await api('logout',{});data={records:[],favourites:[],reactions:[]};$('#content').hidden=true;$('#recovery').hidden=true;$('#code').textContent='';$('#list').replaceChildren();$('#favs').replaceChildren();$('#shows').replaceChildren();$('#account').hidden=false;status('ログアウトしました。');});
refresh().catch(e=>{if(e.status!==401)status(e.message);});
