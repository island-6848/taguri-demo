const $ = s => document.querySelector(s);
let data = {records:[],favourites:[]};
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
}
async function refresh(){data=await api('state');render();}
$('#register').onclick=()=>run($('#register'),async()=>{const result=await api('register',{});$('#code').textContent=result.recovery_code;$('#recovery').hidden=false;await refresh();status('保存先を作りました。復旧コードを控えてください。');});
$('#copy').onclick=()=>run($('#copy'),async()=>{await navigator.clipboard.writeText($('#code').textContent);status('復旧コードをコピーしました。');});
$('#recover').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{await api('recover',Object.fromEntries(new FormData(e.target)));$('#recovery').hidden=true;$('#code').textContent='';await refresh();status('記録を復旧しました。');});};
$('#add').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{const result=await api('record',Object.fromEntries(new FormData(e.target)));data.records.push(result.record);data.records.sort((a,b)=>b.date.localeCompare(a.date));render();e.target.reset();status('追加しました。');});};
$('#favourite').onsubmit=e=>{e.preventDefault();run(e.submitter,async()=>{const f=Object.fromEntries(new FormData(e.target));await api('favourite',f);if(!data.favourites.some(x=>x.name===f.name&&x.kind===f.kind))data.favourites.push(f);render();e.target.reset();status('登録しました。');});};
$('#export').onclick=()=>run($('#export'),async()=>{const backup=await api('export');const url=URL.createObjectURL(new Blob([JSON.stringify(backup,null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download='taguri-backup.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('#import').onchange=e=>run(e.target,async()=>{
  const file=e.target.files[0];if(!file)return;if(file.size>2_000_000)throw new Error('2MBまでのファイルを選んでください。');
  const backup=JSON.parse(await file.text());if(backup.version!==1||!Array.isArray(backup.records)||!Array.isArray(backup.favourites)||backup.records.length>500||backup.favourites.length>200)throw new Error('移行用JSONの形式を確認してください。');
  if(!confirm(`${backup.records.length}件の記録を取り込みますか？同じIDの記録は更新します。`))return;
  let done=0;
  try {for(let i=0;i<Math.max(backup.records.length,backup.favourites.length,1);i+=20){await api('import',{version:1,records:backup.records.slice(i,i+20),favourites:backup.favourites.slice(i,i+20)});done+=backup.records.slice(i,i+20).length;}await refresh();status(`${done}件を取り込みました。`);}catch(error){await refresh();throw new Error(`${done}件を取り込み済みです。残りの取り込みに失敗しました：${error.message}`);}finally{e.target.value='';}
});
$('#logout').onclick=()=>run($('#logout'),async()=>{await api('logout',{});data={records:[],favourites:[]};$('#content').hidden=true;$('#recovery').hidden=true;$('#code').textContent='';$('#list').replaceChildren();$('#favs').replaceChildren();$('#account').hidden=false;status('ログアウトしました。');});
refresh().catch(e=>{if(e.status!==401)status(e.message);});
