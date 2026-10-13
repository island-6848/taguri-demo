// Isolated operator-only import worker. Never add this endpoint to the public UI.
const INSERT_ACCOUNT='INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)';
const INSERT_SNAPSHOT="INSERT INTO legacy_accounts(user_id,revision,write_token) VALUES(?,0,'')";
const INSERT_SCHEMAS="INSERT INTO legacy_schemas(user_id,table_name,schema_sql,columns_json,primary_key_json) SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.schema'),json_extract(value,'$.columns'),json_extract(value,'$.pk') FROM json_each(?)";
const INSERT_ROWS="INSERT INTO legacy_rows(user_id,table_name,row_key,row_json) SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.key'),json_extract(value,'$.row') FROM json_each(?)";
const MAX_BODY=32*1024*1024;
const reply=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
async function equalSecret(actual,expected) {
 const encoder=new TextEncoder();
 const digest=async value=>new Uint8Array(await crypto.subtle.digest('SHA-256',encoder.encode(value)));
 const [a,b]=await Promise.all([digest(actual),digest(expected)]);
 let difference=0;for(let i=0;i<a.length;i++)difference|=a[i]^b[i];return difference===0;
}
export function validateManifest(value) {
 if(value?.format!=='taguri-protected-d1-batch'||value.version!==1||typeof value.user_id!=='string'||!value.user_id||value.user_id==='local'||!Array.isArray(value.commands)||value.commands.length<2||value.commands.length>40)throw new Error('invalid manifest');
 const uid=value.user_id;
 if(value.owner_identity_transfer!==undefined&&typeof value.owner_identity_transfer!=='boolean')throw new Error('invalid transfer');
 if(value.owner_identity_transfer===true&&(value.source_user_id!=='local'||value.owner_recovery_issued!==true))throw new Error('invalid owner transfer');
 if(value.source_user_id==='local'&&value.owner_identity_transfer!==true)throw new Error('owner transfer requires explicit opt-in');
 if(value.owner_identity_transfer===false&&value.source_user_id!==uid)throw new Error('guest identity must remain unchanged');
 for(let index=0;index<value.commands.length;index++) {
  const {sql,params}=value.commands[index];
  const allowed=index===0?INSERT_ACCOUNT:index===1?INSERT_SNAPSHOT:[INSERT_SCHEMAS,INSERT_ROWS];
  if(!(Array.isArray(allowed)?allowed.includes(sql):sql===allowed)||!Array.isArray(params)||params[0]!==uid||params.length!==(index===0?3:index===1?1:2))throw new Error('invalid command');
  if(index===0&&(!/^[a-f0-9]{64}$/.test(params[1])||!Number.isInteger(params[2])))throw new Error('invalid account');
  if(index>=2) {
   if(typeof params[1]!=='string'||new TextEncoder().encode(params[1]).length>900000)throw new Error('invalid binding');
   const block=JSON.parse(params[1]);if(!Array.isArray(block))throw new Error('invalid block');
   for(const row of block) {
    if(typeof row.table!=='string'||!row.table||row.table.length>200)throw new Error('invalid table');
    if(sql===INSERT_ROWS&&(typeof row.key!=='string'||typeof row.row!=='string'||JSON.parse(row.row).user_id!==uid))throw new Error('invalid ownership');
    if(sql===INSERT_SCHEMAS&&(typeof row.schema!=='string'||!Array.isArray(JSON.parse(row.columns))||!JSON.parse(row.columns).includes('user_id')||!Array.isArray(JSON.parse(row.pk))))throw new Error('invalid schema');
   }
  }
 }
 return value;
}
export function authCommands(value) {
 if(value?.format!=='taguri-legacy-auth'||value.version!==1||!Array.isArray(value.mappings)||!value.mappings.length||!Array.isArray(value.sessions))throw new Error('invalid auth manifest');
 const source=new Set(),targets=new Set();
 for(const row of value.mappings){
  if(typeof row.old_user_id!=='string'||typeof row.user_id!=='string'||!row.user_id||row.user_id==='local'||source.has(row.old_user_id)||targets.has(row.user_id))throw new Error('invalid mapping');
  source.add(row.old_user_id);targets.add(row.user_id);
 }
 const tokens=new Set();
 for(const row of value.sessions){
  if(!targets.has(row.user_id)||typeof row.token_hash!=='string'||!/^[a-f0-9]{64}$/.test(row.token_hash)||tokens.has(row.token_hash)||!Number.isInteger(row.expires_at))throw new Error('invalid session');
  tokens.add(row.token_hash);
 }
 const block=list=>{
  const chunks=[];let part=[];let size=2;
  for(const row of list){const amount=new TextEncoder().encode(JSON.stringify(row)).length+1;if(amount>900000)throw new Error('binding too large');if(part.length&&size+amount>900000){chunks.push(JSON.stringify(part));part=[];size=2;}part.push(row);size+=amount;}
  if(part.length)chunks.push(JSON.stringify(part));return chunks;
 };
 const mapSQL="INSERT INTO legacy_user_map(old_user_id,user_id) SELECT json_extract(item.value,'$.old_user_id'),(SELECT users.id FROM users JOIN legacy_accounts ON legacy_accounts.user_id=users.id WHERE users.id=json_extract(item.value,'$.user_id')) FROM json_each(?) AS item WHERE 1 ON CONFLICT(old_user_id) DO UPDATE SET user_id=CASE WHEN legacy_user_map.user_id=excluded.user_id THEN legacy_user_map.user_id ELSE NULL END";
 const sessionSQL="INSERT INTO legacy_sessions(token_hash,user_id,expires_at) SELECT json_extract(item.value,'$.token_hash'),(SELECT user_id FROM legacy_user_map WHERE user_id=json_extract(item.value,'$.user_id')),json_extract(item.value,'$.expires_at') FROM json_each(?) AS item WHERE 1 ON CONFLICT(token_hash) DO UPDATE SET user_id=CASE WHEN legacy_sessions.user_id=excluded.user_id THEN legacy_sessions.user_id ELSE NULL END,expires_at=MAX(legacy_sessions.expires_at,excluded.expires_at)";
 const commands=[...block(value.mappings).map(payload=>({sql:mapSQL,params:[payload]})),...block(value.sessions).map(payload=>({sql:sessionSQL,params:[payload]}))];
 if(commands.length>40)throw new Error('query budget exceeded');return commands;
}
export default {
 async fetch(request,env) {
  // No configured secret means no endpoint, even in an accidental deployment.
  if(typeof env.MIGRATION_ADMIN_KEY!=='string'||env.MIGRATION_ADMIN_KEY.length<32)return reply({error:'not found'},404);
  if(request.method!=='POST'||!['/import-account','/import-auth'].includes(new URL(request.url).pathname))return reply({error:'not found'},404);
  if(!await equalSecret(request.headers.get('authorization')??'',`Bearer ${env.MIGRATION_ADMIN_KEY}`))return reply({error:'unauthorized'},401);
  if(!request.headers.get('content-type')?.startsWith('application/json'))return reply({error:'JSON required'},415);
  try {
   const reader=request.body?.getReader();let size=0;const parts=[];
   if(reader)while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>MAX_BODY){await reader.cancel();return reply({error:'manifest too large'},413);}parts.push(value);}
   const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
   const raw=JSON.parse(new TextDecoder().decode(bytes));
   const auth=new URL(request.url).pathname==='/import-auth';
   const value=auth?raw:validateManifest(raw);
   const commands=auth?authCommands(value):value.commands;
   // D1 batch is one atomic transaction. Unique conflicts roll back the account
   // and all its rows: no implicit merge, overwrite or partial file execution.
   await env.DB.batch(commands.map(({sql,params})=>env.DB.prepare(sql).bind(...params)));
   return reply({ok:true,tables:auth?0:Object.keys(value.counts??{}).length});
  } catch {return reply({error:'Import failed; invalid manifest or existing account. No batch changes were committed.'},409);}
 }
};
