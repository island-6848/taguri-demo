// Allowlisted operational metadata only. Never log cookies, request bodies,
// exception messages, recovery codes, URLs, user IDs, titles or notes.
const ROUTES = new Set(['register','recover','state','export','record','record/delete','favourite','reaction','import','logout','catalogue','screen','bridge','static','unknown']);
export function operationRoute(path) {
  if(path.startsWith('/migration-api/'))path=path.replace('/migration-api/','/api/');
  if(path.startsWith('/api/screen/'))return 'screen';
  const route=path.startsWith('/api/')?path.slice(5):'bridge';
  return ROUTES.has(route)?route:'unknown';
}
export function logOperation({route,method,status,durationMs,backend}, sink=console) {
  const entry={event:'taguri.operation',route:ROUTES.has(route)?route:'unknown',method:['GET','POST','HEAD'].includes(method)?method:'OTHER',status:Number.isInteger(status)&&status>=100&&status<=599?status:500,duration_ms:Math.max(0,Math.min(300000,Math.round(Number(durationMs)||0))),backend:['d1','render','assets'].includes(backend)?backend:'unknown'};
  const output=JSON.stringify(entry);
  if(entry.status>=500)sink.error(output);else sink.log(output);
  return entry;
}
export async function observeOperation(request,env,handler,sink=console) {
  const started=Date.now(), path=new URL(request.url).pathname;
  const native=path.startsWith('/migration-api/') || (path.startsWith('/api/') && env.ORIGINAL_UI_BRIDGE!=='true');
  const backend=native?'d1':(/^(\/api\/|\/auth\/|\/recover$|\/link$|\/img\/|\/export.json$|\/data.zip$)/.test(path)?'render':'assets');
  try {
    const response=await handler();
    // Static assets do not produce logs; account/API operations and failures do.
    if(backend!=='assets'||response.status>=500)logOperation({route:operationRoute(path),method:request.method,status:response.status,durationMs:Date.now()-started,backend},sink);
    return response;
  } catch(error) {
    logOperation({route:operationRoute(path),method:request.method,status:503,durationMs:Date.now()-started,backend},sink);
    return Response.json({error:"処理できませんでした。時間を置いてもう一度お試しください。"},{status:503,headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
  }
}
