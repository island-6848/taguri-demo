// Transitional transport for the unchanged Python-rendered UI.
// Only the fixed existing application can be contacted; this is not a public proxy.
const UPSTREAM = 'https://taguri-demo.onrender.com';
const GET_PATHS = new Set(['/auth/start','/recover','/link','/api/suggest','/api/suggest_web','/api/import_status','/api/mail_hints']);
const SCREENS = new Set(['recommend','reminder','interest','favourites','calendar','tickets','rate','unrated','notes','register','records','trace','chronicle','works','search','settings','start']);
const POST_PATHS = new Set(['react','rate','note','favourite','missed','add_work','import_mail','fix_work','merge_work','drop_work','restore_work','purge_work','unseen','ticket','chronicle','people_read','weight','pref_setting','hand_credits','hand_poster','link_stage','hand_theme','hand_theme_refresh','decline','visit_note','recover','link/create','link/redeem','close'].map(p=>'/api/'+p));
// /api/auth/* (Firebase sign-in) is answered by this Worker, never the old server.
export function isOriginalRoute(path) {
 return (path.startsWith('/api/') && !path.startsWith('/api/auth/')) || path.startsWith('/img/') || GET_PATHS.has(path) || path==='/export.json' || path==='/data.zip';
}
const error = (status,message)=>Response.json({ok:false,error:message},{status,headers:{'Cache-Control':'no-store'}});
export async function originalUI(request, transport=fetch) {
 const url=new URL(request.url),path=url.pathname;
 if(['/export.json','/data.zip'].includes(path))return error(503,'利用者ごとの記録の書き出しを移行中です。元の記録は保持されています。');
 const allowedGet=GET_PATHS.has(path)||(/^\/img\/[A-Za-z0-9_.-]+$/.test(path))||(path.startsWith('/api/screen/')&&SCREENS.has(path.slice('/api/screen/'.length)));
 if(!((request.method==='GET'&&allowedGet)||(request.method==='POST'&&POST_PATHS.has(path))))return error(404,'この操作は見つかりませんでした。');
 if(request.method==='POST'&&request.headers.get('origin')!==url.origin)return error(403,'同じサイトから操作してください。');
 const headers=new Headers();
 for(const name of ['content-type','accept'])if(request.headers.has(name))headers.set(name,request.headers.get(name));
 // Do not send the D1 account's session or any unrelated cookie to the old server.
 const session=request.headers.get('cookie')?.match(/(?:^|;\s*)tg_session=([A-Za-z0-9_-]{32,128})(?:;|$)/)?.[1];
 if(session)headers.set('Cookie',`tg_session=${session}`);
 if(request.method==='POST')headers.set('Origin',UPSTREAM);
 let body;
 if(request.method==='POST') {
  // Match the existing server's 8 KiB limit without buffering arbitrary uploads.
  const reader=request.body?.getReader();const chunks=[];let size=0;
  if(reader)while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>8192){await reader.cancel();return error(413,'入力が大きすぎます。');}chunks.push(value);}
  body=new Uint8Array(size);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.length;}
 }
 try {
  const response=await transport(UPSTREAM+path+url.search,{method:request.method,headers,body,redirect:'manual',signal:AbortSignal.timeout(180000)});
  const out=new Headers();
  for(const name of ['content-type','content-disposition'])if(response.headers.has(name))out.set(name,response.headers.get(name));
  out.set('Cache-Control','private, no-store');out.set('X-Content-Type-Options','nosniff');
  const location=response.headers.get('location');if(location){const next=new URL(location,UPSTREAM);if(next.origin===UPSTREAM)out.set('Location',next.pathname+next.search);else return error(502,'移動先を確認できませんでした。');}
  const cookie=response.headers.get('set-cookie');
  if(cookie?.startsWith('tg_session='))out.set('Set-Cookie',cookie.replace(/;\s*Domain=[^;]+/gi,'').replace(/;\s*SameSite=[^;]+/gi,'')+'; SameSite=Strict; Secure');
  return new Response(response.body,{status:response.status,headers:out});
 } catch {return error(503,'画面を読み込めませんでした。少し時間を置いて再度お試しください。');}
}
